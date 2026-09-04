"""Tests for the thin Elios4you API layer.

The API is now a parser/orchestrator on top of ConnectionManager. These
tests verify:

* exception classes (re-exported from ``connection_manager``)
* response parsing per command flavor
* the ``async_get_data`` read cycle: assembles ``@dat`` + ``@sta`` + ``@inf``
  and computes derived sensors
* the ``telnet_set_relay`` set + verify cycle
* diagnostic metrics get copied into ``api.data`` after every call

ConnectionManager itself is covered in test_connection_manager.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.api import (
    Elios4YouAPI,
    TelnetCommandError,
    TelnetConnectionError,
)
from custom_components.fournoks_elios4you.const import CONN_TIMEOUT, MANUFACTURER, MODEL

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SERIAL_NUMBER


class TestTelnetExceptions:
    """Re-exported exception classes still work for callers."""

    def test_telnet_connection_error_init(self) -> None:
        """TelnetConnectionError stores host/port/timeout and formats a message."""
        error = TelnetConnectionError(TEST_HOST, TEST_PORT, CONN_TIMEOUT)
        assert error.host == TEST_HOST
        assert error.port == TEST_PORT
        assert error.timeout == CONN_TIMEOUT
        assert TEST_HOST in str(error)
        assert str(TEST_PORT) in str(error)

    def test_telnet_connection_error_custom_message(self) -> None:
        """Custom message overrides the default."""
        error = TelnetConnectionError(TEST_HOST, TEST_PORT, CONN_TIMEOUT, "boom")
        assert str(error) == "boom"

    def test_telnet_command_error_init(self) -> None:
        """TelnetCommandError stores the command."""
        error = TelnetCommandError("@dat")
        assert error.command == "@dat"
        assert "@dat" in str(error)

    def test_telnet_command_error_custom_message(self) -> None:
        """Custom message overrides the default."""
        error = TelnetCommandError("@sta", "nope")
        assert str(error) == "nope"


class TestApiInit:
    """API construction seeds expected data keys and creates a manager."""

    def test_init_basic_attributes(self, mock_hass) -> None:
        """Constructor sets name, host, and creates a ConnectionManager."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        assert api.name == TEST_NAME
        assert api.host == TEST_HOST
        assert api._port == TEST_PORT
        assert api.connection_manager is not None
        assert api.data["manufact"] == MANUFACTURER
        assert api.data["model"] == MODEL

    def test_init_seeds_power_keys(self, mock_hass) -> None:
        """Power/energy keys are seeded with 1 so sensor setup doesn't skip them."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        for key in (
            "produced_power",
            "consumed_power",
            "produced_energy",
            "sold_energy",
            "relay_state",
        ):
            assert api.data[key] == 1

    def test_init_seeds_diagnostic_keys(self, mock_hass) -> None:
        """ConnectionManager metrics are copied to api.data on construction."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        assert api.data["cm_state"] == "disconnected"
        assert api.data["cm_consecutive_failures"] == 0
        assert api.data["cm_commands_sent"] == 0


class TestParsing:
    """Static response parser covers both line formats and the awkward LF cases."""

    def test_parse_dat_semicolon_format(self) -> None:
        """@dat uses ``index;key;value`` lines."""
        raw = "@dat\n0;produced_power;1.5\n1;consumed_power;2.0\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        assert out == {"produced_power": "1.5", "consumed_power": "2.0"}

    def test_parse_inf_equals_format(self) -> None:
        """@inf uses ``key=value`` lines."""
        raw = "@inf\nsn=ABC123\nhwver=1.0\n\nready..."
        out = Elios4YouAPI._parse("@inf", raw)
        assert out == {"sn": "ABC123", "hwver": "1.0"}

    def test_parse_rel_equals_format(self) -> None:
        """@rel uses the same ``key=value`` format as @inf."""
        raw = "@rel\nrel=1\nmode=0\n\nready..."
        out = Elios4YouAPI._parse("@rel", raw)
        assert out["rel"] == "1"

    def test_parse_hwr_equals_format(self) -> None:
        """@hwr uses the same ``key=value`` format as @inf."""
        raw = "@hwr\nhwver=1.0\nbtver=2.0\n\nready..."
        out = Elios4YouAPI._parse("@hwr", raw)
        assert out["hwver"] == "1.0"

    def test_parse_skips_leading_linefeed(self) -> None:
        """Device sometimes prepends a stray LF before the echoed command."""
        raw = "\n@dat\n0;produced_power;1.5\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        assert out == {"produced_power": "1.5"}

    def test_parse_normalizes_keys(self) -> None:
        """Keys are lowercased and spaces become underscores."""
        raw = "@dat\n0;Produced Power;1.5\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        assert "produced_power" in out

    def test_parse_dat_devha_unpacks_accessory_fields(self) -> None:
        """A Smart RC accessory row carries ten fields, not a single value."""
        raw = "@dat\n;DEVHA0;1;1;15;1;1;23;1;-59;81;PRESA_1;;\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        assert out["devha0_online"] == "1"
        assert out["devha0_relay"] == "1"
        assert out["devha0_power"] == "23"
        assert out["devha0_energy"] == "1"
        assert out["devha0_rssi"] == "-59"
        assert out["devha0_devid"] == "81"
        assert out["devha0_name"] == "PRESA_1"

    def test_parse_dat_devha_keeps_legacy_key(self) -> None:
        """``devha<n>`` keeps its historical value, so nothing downstream breaks."""
        raw = "@dat\n;DEVHA1;1;0;15;1;1;0;0;-67;81;PRESA_2;;\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        assert out["devha1"] == "1"

    def test_parse_dat_devha_offline_row_drops_measurements(self) -> None:
        """An offline accessory reports zeros, and the measurements are dropped.

        The zeros are a valid reading of "not joined", not measurements. Publishing
        them would be actively harmful: ``devha<n>_energy`` is TOTAL_INCREASING, so a
        0 is read as a meter reset and the whole counter is re-added to the Energy
        dashboard on every offline/online cycle; RSSI 0 misleads the other way, as
        0 dBm reads as a very strong signal. Omitting the keys leaves the last known
        values in place, since ``data`` is merged into and never rebuilt.
        """
        raw = "@dat\n;DEVHA0;1;1;15;0;0;0;0;0;81;PRESA_1;;\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        # State is still reported: this is what tells the user it is offline.
        assert out["devha0_online"] == "0"
        assert out["devha0_relay"] == "0"
        assert out["devha0_name"] == "PRESA_1"
        # Measurements are absent, not zero.
        assert "devha0_power" not in out
        assert "devha0_energy" not in out
        assert "devha0_rssi" not in out

    def test_parse_dat_devha_online_row_keeps_measurements(self) -> None:
        """The guard is conditional: a joined accessory reports everything."""
        raw = "@dat\n;DEVHA0;1;1;15;1;1;23;1;-59;81;PRESA_1;;\n\nready..."
        out = Elios4YouAPI._parse("@dat", raw)
        assert out["devha0_online"] == "1"
        assert out["devha0_power"] == "23"
        assert out["devha0_energy"] == "1"
        assert out["devha0_rssi"] == "-59"

    def test_parse_dat_mixes_devha_and_plain_rows(self) -> None:
        """Accessory rows do not disturb the ordinary ``key;value`` rows."""
        raw = (
            "@dat\n"
            "0;produced_power;1.5\n"
            ";DEVHA0;1;1;15;1;1;23;1;-59;81;PRESA_1;;\n"
            "2;consumed_power;2.0\n"
            "\nready..."
        )
        out = Elios4YouAPI._parse("@dat", raw)
        assert out["produced_power"] == "1.5"
        assert out["consumed_power"] == "2.0"
        assert out["devha0_power"] == "23"


class TestAsyncGetData:
    """The read cycle composes three commands and computes derived sensors."""

    @pytest.mark.asyncio
    async def test_full_cycle_success(self, mock_hass) -> None:
        """A successful cycle merges all three responses + derived sensors."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        dat_raw = (
            "@dat\n"
            "0;produced_power;2.5\n"
            "1;consumed_power;1.8\n"
            "2;sold_power;0.7\n"
            "3;produced_energy;100\n"
            "4;sold_energy;30\n"
            "5;produced_energy_f1;50\n"
            "6;produced_energy_f2;30\n"
            "7;produced_energy_f3;20\n"
            "8;sold_energy_f1;15\n"
            "9;sold_energy_f2;10\n"
            "10;sold_energy_f3;5\n"
            "\nready..."
        )
        sta_raw = "@sta\n0;daily_peak;3.2\n1;monthly_peak;4.5\n\nready..."
        inf_raw = f"@inf\nsn={TEST_SERIAL_NUMBER}\nfwtop=1.0\nfwbtm=2.0\nhwver=3.0\n\nready..."

        api.connection_manager.execute = AsyncMock(side_effect=[dat_raw, sta_raw, inf_raw])

        assert await api.async_get_data() is True

        assert api.data["produced_power"] == 2.5
        assert api.data["sn"] == TEST_SERIAL_NUMBER
        assert api.data["swver"] == "1.0 / 2.0"
        # self_consumed_power = produced - sold
        assert api.data["self_consumed_power"] == pytest.approx(1.8)
        # diagnostic snapshot was refreshed
        assert api.data["cm_state"] in ("disconnected", "ready", "connecting", "backoff", "closed")

    @pytest.mark.asyncio
    async def test_dat_failure_propagates(self, mock_hass) -> None:
        """If @dat fails, the cycle raises and diagnostics still get refreshed."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock(side_effect=TelnetCommandError("@dat", "boom"))

        with pytest.raises(TelnetCommandError):
            await api.async_get_data()

        # Diagnostic snapshot updated even on failure (because of try/finally).
        assert "cm_state" in api.data

    @pytest.mark.asyncio
    async def test_connection_failure_propagates(self, mock_hass) -> None:
        """A TelnetConnectionError from the manager bubbles up."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock(
            side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, CONN_TIMEOUT)
        )

        with pytest.raises(TelnetConnectionError):
            await api.async_get_data()

    @pytest.mark.asyncio
    async def test_bad_value_is_skipped(self, mock_hass) -> None:
        """A non-numeric @dat value is logged and skipped, not raised."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        dat_raw = (
            "@dat\n"
            "0;produced_power;not_a_number\n"
            "1;consumed_power;1.8\n"
            "2;sold_power;0.7\n"
            "3;produced_energy;100\n"
            "4;sold_energy;30\n"
            "5;produced_energy_f1;50\n"
            "6;produced_energy_f2;30\n"
            "7;produced_energy_f3;20\n"
            "8;sold_energy_f1;15\n"
            "9;sold_energy_f2;10\n"
            "10;sold_energy_f3;5\n"
            "\nready..."
        )
        sta_raw = "@sta\n0;daily_peak;3.2\n1;monthly_peak;4.5\n\nready..."
        inf_raw = f"@inf\nsn={TEST_SERIAL_NUMBER}\nfwtop=1.0\nfwbtm=2.0\nhwver=3.0\n\nready..."

        api.connection_manager.execute = AsyncMock(side_effect=[dat_raw, sta_raw, inf_raw])

        assert await api.async_get_data() is True
        # produced_power keeps its seeded value (1) because parse was skipped
        assert api.data["produced_power"] == 1
        # consumed_power was parsed normally
        assert api.data["consumed_power"] == 1.8


class TestSetRelay:
    """Relay set + verify cycle."""

    @pytest.mark.asyncio
    async def test_set_relay_on_success(self, mock_hass) -> None:
        """When the device echoes the requested state, return True and update data."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock(
            side_effect=["@rel\nrel=1\n\nready...", "@rel\nrel=1\n\nready..."]
        )

        assert await api.telnet_set_relay("on") is True
        assert api.data["relay_state"] == 1

    @pytest.mark.asyncio
    async def test_set_relay_off_success(self, mock_hass) -> None:
        """OFF case mirrors ON."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock(
            side_effect=["@rel\nrel=0\n\nready...", "@rel\nrel=0\n\nready..."]
        )

        assert await api.telnet_set_relay("off") is True
        assert api.data["relay_state"] == 0

    @pytest.mark.asyncio
    async def test_set_relay_invalid_state(self, mock_hass) -> None:
        """Unknown state is rejected without touching the device."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock()

        assert await api.telnet_set_relay("invalid") is False
        api.connection_manager.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_relay_command_error_returns_false(self, mock_hass) -> None:
        """Manager error is swallowed and reported as False."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock(side_effect=TelnetCommandError("@rel", "boom"))

        assert await api.telnet_set_relay("on") is False

    @pytest.mark.asyncio
    async def test_set_relay_state_mismatch(self, mock_hass) -> None:
        """When the device reports a different state than requested, return False."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.execute = AsyncMock(
            side_effect=["@rel\nrel=0\n\nready...", "@rel\nrel=0\n\nready..."]
        )

        # Asked for ON, device reports OFF
        assert await api.telnet_set_relay("on") is False

    @pytest.mark.asyncio
    async def test_set_relay_malformed_response_returns_false(self, mock_hass) -> None:
        """Non-integer rel value yields False (parse_error swallowed)."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        # First call (set) succeeds; second (read) parses but value is non-int.
        api.connection_manager.execute = AsyncMock(
            side_effect=["@rel\nrel=1\n\nready...", "@rel\nrel=abc\n\nready..."]
        )

        assert await api.telnet_set_relay("on") is False


class TestClose:
    """Public close delegates to the manager."""

    @pytest.mark.asyncio
    async def test_close_delegates(self, mock_hass) -> None:
        """API.close calls manager.close and refreshes diagnostic data."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.connection_manager.close = AsyncMock()

        await api.close()

        api.connection_manager.close.assert_awaited_once()
        # Diagnostic snapshot was refreshed (cm_state present)
        assert "cm_state" in api.data


class TestCommandParseError:
    """A malformed manager response surfaces as TelnetCommandError(parse_error)."""

    @pytest.mark.asyncio
    async def test_parse_error_raises_telnet_command_error(self, mock_hass) -> None:
        """If _parse can't split a line, _command should raise TelnetCommandError."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        # Response is well-framed but the data line is broken (no separator).
        api.connection_manager.execute = AsyncMock(
            return_value="@inf\nsn ABC123_no_equals_sign\n\nready..."
        )

        with pytest.raises(TelnetCommandError) as exc:
            await api._command("@inf")
        assert "parse_error" in exc.value.message


class TestMergeBranches:
    """Cover the @dat utc_time / int branches and the @sta value-error branch."""

    def test_merge_dat_prunes_unpaired_accessory_slots(self, mock_hass) -> None:
        """Keys of a slot that stopped appearing in @dat are removed.

        An un-paired accessory stops emitting its DEVHA row entirely; since
        ``self.data`` is merged into and never rebuilt, its keys must be pruned
        or they would survive forever with frozen values.
        """
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.data.update(
            {
                "devha0": 1,
                "devha0_power": 23.0,
                "devha0_name": "PRESA_1",
                "devha1": 1,
                "devha1_power": 40.0,
                "devha1_name": "PRESA_2",
            }
        )

        # devha1 was un-paired: only devha0's row appears in the new parse.
        api._merge_dat({"devha0": "1", "devha0_power": "25", "devha0_name": "PRESA_1"})

        assert api.data["devha0_power"] == 25.0
        assert not any(k.startswith("devha1") for k in api.data)

    def test_merge_dat_offline_row_does_not_prune_measurements(self, mock_hass) -> None:
        """An offline accessory still emits its row: its slot must survive.

        The offline guard omits power/energy/rssi from the parsed row, but the
        bare ``devha<n>`` key is still present — so the prune must keep the
        last-known measurement values the guard deliberately preserves.
        """
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api.data.update({"devha0": 1, "devha0_online": 1, "devha0_power": 82.0})

        # Offline parse: slot present, measurements absent.
        api._merge_dat({"devha0": "1", "devha0_online": "0", "devha0_relay": "0"})

        assert api.data["devha0_online"] == 0
        assert api.data["devha0_power"] == 82.0

    @pytest.mark.asyncio
    async def test_merge_dat_skips_utc_time_and_parses_ints(self, mock_hass) -> None:
        """@dat: utc_time is skipped, non-energy/power values are parsed as int."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        dat_raw = (
            "@dat\n"
            "0;produced_power;2.5\n"
            "1;consumed_power;1.8\n"
            "2;sold_power;0.7\n"
            "3;produced_energy;100\n"
            "4;sold_energy;30\n"
            "5;produced_energy_f1;50\n"
            "6;produced_energy_f2;30\n"
            "7;produced_energy_f3;20\n"
            "8;sold_energy_f1;15\n"
            "9;sold_energy_f2;10\n"
            "10;sold_energy_f3;5\n"
            "11;utc_time;2026-05-27T10:00:00\n"
            "12;alarm_1;0\n"
            "\nready..."
        )
        sta_raw = "@sta\n0;daily_peak;3.2\n\nready..."
        inf_raw = f"@inf\nsn={TEST_SERIAL_NUMBER}\nfwtop=1.0\nfwbtm=2.0\nhwver=3.0\n\nready..."

        api.connection_manager.execute = AsyncMock(side_effect=[dat_raw, sta_raw, inf_raw])
        assert await api.async_get_data() is True
        # utc_time should be ignored (stays as the seeded empty string)
        assert api.data["utc_time"] == ""
        # alarm_1 should be parsed as int through the else-branch
        assert api.data["alarm_1"] == 0
        assert isinstance(api.data["alarm_1"], int)

    @pytest.mark.asyncio
    async def test_merge_dat_keeps_accessory_name_as_text(self, mock_hass) -> None:
        """@dat: the accessory name is free text and must survive int parsing."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        dat_raw = "@dat\n0;produced_power;2.5\n;DEVHA0;1;1;15;1;1;23;2;-59;81;PRESA_1;;\n\nready..."
        sta_raw = "@sta\n0;daily_peak;3.2\n\nready..."
        inf_raw = f"@inf\nsn={TEST_SERIAL_NUMBER}\nfwtop=1.0\nfwbtm=2.0\nhwver=3.0\n\nready..."

        api.connection_manager.execute = AsyncMock(side_effect=[dat_raw, sta_raw, inf_raw])
        assert await api.async_get_data() is True
        assert api.data["devha0_name"] == "PRESA_1"
        assert api.data["devha0_power"] == 23.0
        assert api.data["devha0_energy"] == 2.0
        assert api.data["devha0_rssi"] == -59
        assert isinstance(api.data["devha0_rssi"], int)

    @pytest.mark.asyncio
    async def test_merge_sta_skips_bad_value(self, mock_hass) -> None:
        """@sta: a non-float value is logged and skipped, not raised."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        dat_raw = (
            "@dat\n"
            "0;produced_power;2.5\n"
            "1;consumed_power;1.8\n"
            "2;sold_power;0.7\n"
            "3;produced_energy;100\n"
            "4;sold_energy;30\n"
            "5;produced_energy_f1;50\n"
            "6;produced_energy_f2;30\n"
            "7;produced_energy_f3;20\n"
            "8;sold_energy_f1;15\n"
            "9;sold_energy_f2;10\n"
            "10;sold_energy_f3;5\n"
            "\nready..."
        )
        # daily_peak deliberately unparseable as float; monthly_peak is fine.
        sta_raw = "@sta\n0;daily_peak;not_a_float\n1;monthly_peak;4.5\n\nready..."
        inf_raw = f"@inf\nsn={TEST_SERIAL_NUMBER}\nfwtop=1.0\nfwbtm=2.0\nhwver=3.0\n\nready..."

        api.connection_manager.execute = AsyncMock(side_effect=[dat_raw, sta_raw, inf_raw])
        assert await api.async_get_data() is True
        assert api.data["monthly_peak"] == 4.5
