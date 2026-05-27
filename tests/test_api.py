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
