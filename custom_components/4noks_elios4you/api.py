"""API layer for 4-noks Elios4you.

This module is a thin protocol wrapper over the :class:`ConnectionManager`.
It owns no sockets and no retry/backoff logic — that all lives in the
manager. What lives here:

* The well-known set of commands (``@dat``, ``@sta``, ``@inf``, ``@rel``)
  and how to parse each one.
* The high-level read cycle (``async_get_data``) and the relay setter
  (``telnet_set_relay``) used by the coordinator and the switch entity.
* The data dictionary that backs every sensor entity in the integration.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .connection_manager import (
    ConnectionManager,
    ConnectionUnavailableError,
    TelnetCommandError,
    TelnetConnectionError,
)
from .const import MANUFACTURER, MODEL
from .helpers import log_debug

# Re-export the exception types so existing callers
# (``coordinator``, ``config_flow``, tests) don't need to change imports.
__all__ = [
    "ConnectionUnavailableError",
    "Elios4YouAPI",
    "TelnetCommandError",
    "TelnetConnectionError",
]

_LOGGER = logging.getLogger(__name__)


class Elios4YouAPI:
    """Protocol-level API for an Elios4you device.

    Connection lifecycle, serialization, retries, and backoff are owned by
    :class:`ConnectionManager`; this class only formats commands and parses
    the device's responses.
    """

    def __init__(self, hass: HomeAssistant, name: str, host: str, port: int) -> None:
        """Initialize the API."""
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self.data: dict[str, int | float | str] = {}

        self.connection_manager = ConnectionManager(host=host, port=port)

        self._init_data_keys()

    # ------------------------------------------------------------------ #
    # Properties used by entities / device registry
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._name

    @property
    def host(self) -> str:
        """Return the device host."""
        return self._host

    # ------------------------------------------------------------------ #
    # Public API used by coordinator and switch
    # ------------------------------------------------------------------ #

    async def close(self) -> None:
        """Close the underlying connection (called on integration unload)."""
        await self.connection_manager.close()
        self._update_diagnostic_data()

    async def async_get_data(self) -> bool:
        """Run one full read cycle: ``@dat`` + ``@sta`` + ``@inf``.

        Raises:
            TelnetConnectionError: device unreachable.
            TelnetCommandError: a command failed after retries.
            ConnectionUnavailableError: manager is in backoff.

        """
        log_debug(_LOGGER, "async_get_data", "========== READ CYCLE START ==========")

        try:
            dat = await self._command("@dat")
            self._merge_dat(dat)

            sta = await self._command("@sta")
            self._merge_sta(sta)

            inf = await self._command("@inf")
            self._merge_inf(inf)

            self._update_calculated()
        finally:
            self._update_diagnostic_data()

        log_debug(_LOGGER, "async_get_data", "========== READ CYCLE END (success) ==========")
        return True

    async def telnet_set_relay(self, state: str) -> bool:
        """Set the device relay to ``"on"`` or ``"off"``.

        Returns True if the device confirms the requested state, False
        otherwise. Never raises — caller wants a boolean for the UI.
        """
        if state.lower() == "on":
            to_state = 1
        elif state.lower() == "off":
            to_state = 0
        else:
            return False

        try:
            log_debug(
                _LOGGER,
                "telnet_set_relay",
                "Sending relay command",
                to_state=to_state,
            )
            await self._command(f"@rel 0 {to_state}")
            rel_parsed = await self._command("@rel")
            out_mode = int(rel_parsed["rel"])
        except (TelnetConnectionError, TelnetCommandError, ConnectionUnavailableError) as err:
            log_debug(_LOGGER, "telnet_set_relay", "Relay command failed", error=str(err))
            self._update_diagnostic_data()
            return False
        except (ValueError, KeyError) as err:
            # Malformed / unexpected response — fail the service call rather
            # than crash the caller.
            log_debug(_LOGGER, "telnet_set_relay", "Relay response malformed", error=str(err))
            self._update_diagnostic_data()
            return False

        success = out_mode == to_state
        if success:
            # Refresh relay_state immediately to avoid waiting for the next poll.
            self.data["relay_state"] = out_mode
        log_debug(
            _LOGGER,
            "telnet_set_relay",
            "Set relay result",
            to_state=to_state,
            actual=out_mode,
            success=success,
        )
        self._update_diagnostic_data()
        return success

    # ------------------------------------------------------------------ #
    # Internal: command + parse
    # ------------------------------------------------------------------ #

    async def _command(self, cmd: str) -> dict[str, str]:
        """Send ``cmd`` and parse its response into a key/value dict.

        Raises:
            TelnetConnectionError, TelnetCommandError, ConnectionUnavailableError:
                propagated from the manager.
            TelnetCommandError: when the response cannot be parsed.

        """
        raw = await self.connection_manager.execute(cmd)
        try:
            return self._parse(cmd, raw)
        except (ValueError, IndexError) as err:
            log_debug(
                _LOGGER,
                "_command",
                "Failed to parse response",
                cmd=cmd,
                error=str(err),
            )
            raise TelnetCommandError(cmd, f"parse_error: {err}") from err

    @staticmethod
    def _parse(cmd: str, raw: str) -> dict[str, str]:
        """Parse a raw device response into a dict.

        The device emits one record per line. Format depends on the command:

        * ``@dat`` / ``@sta``: ``index;key;value;...`` — semicolon-separated
        * ``@inf`` / ``@rel`` / ``@hwr``: ``key=value`` — equals-separated

        The response ends with a line containing ``RESPONSE_SEPARATOR``
        (preceded by a blank line). The first line is often the echoed
        command, but sometimes a stray line-feed precedes it.
        """
        cmd_main = cmd[0:4].lower()
        lines = raw.splitlines()

        # First useful line index — skip the echoed command, or one extra if
        # the device prepended a LF.
        if lines and lines[0].lower() in ("@dat", "@sta", "@inf", "@rel", "@hwr"):
            lines_start = 1
        else:
            lines_start = 2

        # Last two lines are the blank line and the separator marker.
        lines_end = -2

        output: dict[str, str] = {}
        for line in lines[lines_start:lines_end]:
            if cmd_main in ("@inf", "@rel", "@hwr"):
                key, value = line.split("=")
            else:
                key, value = line.split(";")[1:3]
            output[key.lower().replace(" ", "_")] = value.strip()
        return output

    # ------------------------------------------------------------------ #
    # Internal: data merging
    # ------------------------------------------------------------------ #

    def _merge_dat(self, parsed: dict[str, str]) -> None:
        """Merge a parsed ``@dat`` response into ``self.data``."""
        for key, value in parsed.items():
            try:
                if "energy" in key or "power" in key:
                    self.data[key] = round(float(value), 2)
                elif key == "utc_time":
                    continue
                else:
                    self.data[key] = int(value)
            except ValueError:
                log_debug(
                    _LOGGER,
                    "_merge_dat",
                    "Value could not be parsed",
                    key=key,
                    value=value,
                )

    def _merge_sta(self, parsed: dict[str, str]) -> None:
        """Merge a parsed ``@sta`` response into ``self.data``."""
        for key, value in parsed.items():
            try:
                self.data[key] = round(float(value), 2)
            except ValueError:
                log_debug(
                    _LOGGER,
                    "_merge_sta",
                    "Value could not be parsed",
                    key=key,
                    value=value,
                )

    def _merge_inf(self, parsed: dict[str, str]) -> None:
        """Merge a parsed ``@inf`` response into ``self.data``."""
        for key, value in parsed.items():
            self.data[key] = str(value)

    def _update_calculated(self) -> None:
        """Recompute derived sensors (self-consumption, software version)."""
        self.data["swver"] = f"{self.data['fwtop']} / {self.data['fwbtm']}"

        self.data["self_consumed_power"] = round(
            float(self.data["produced_power"]) - float(self.data["sold_power"]),
            2,
        )
        self.data["self_consumed_energy"] = round(
            float(self.data["produced_energy"]) - float(self.data["sold_energy"]),
            2,
        )
        for tariff in ("f1", "f2", "f3"):
            self.data[f"self_consumed_energy_{tariff}"] = round(
                float(self.data[f"produced_energy_{tariff}"])
                - float(self.data[f"sold_energy_{tariff}"]),
                2,
            )

    def _update_diagnostic_data(self) -> None:
        """Copy current ConnectionManager metrics into ``self.data``.

        Sensors read straight from ``api.data``, so exposing diagnostics is
        as simple as making sure every metric we want visible lives there
        under the ``cm_`` prefix.
        """
        snapshot = self.connection_manager.metrics_snapshot()
        for key, value in snapshot.items():
            self.data[f"cm_{key}"] = value

    # ------------------------------------------------------------------ #
    # Initialization
    # ------------------------------------------------------------------ #

    def _init_data_keys(self) -> None:
        """Seed ``self.data`` so entities can be created before the first poll."""
        # Power & energy sensors are seeded to 1 (not 0) so that the existing
        # sensor.py guard ``if coordinator.api.data[key] is not None`` accepts
        # them at platform setup time. The first real poll overwrites these.
        numeric_keys = (
            "produced_power",
            "consumed_power",
            "self_consumed_power",
            "bought_power",
            "sold_power",
            "daily_peak",
            "monthly_peak",
            "produced_energy",
            "produced_energy_f1",
            "produced_energy_f2",
            "produced_energy_f3",
            "consumed_energy",
            "consumed_energy_f1",
            "consumed_energy_f2",
            "consumed_energy_f3",
            "self_consumed_energy",
            "self_consumed_energy_f1",
            "self_consumed_energy_f2",
            "self_consumed_energy_f3",
            "bought_energy",
            "bought_energy_f1",
            "bought_energy_f2",
            "bought_energy_f3",
            "sold_energy",
            "sold_energy_f1",
            "sold_energy_f2",
            "sold_energy_f3",
            "alarm_1",
            "alarm_2",
            "power_alarm",
            "relay_state",
            "pwm_mode",
            "pr_ssv",
            "rel_ssv",
            "rel_mode",
            "rel_warning",
            "rcap",
        )
        for key in numeric_keys:
            self.data[key] = 1

        string_keys = (
            "utc_time",
            "fwtop",
            "fwbtm",
            "sn",
            "hwver",
            "btver",
            "hw_wifi",
            "s2w_app_version",
            "s2w_geps_version",
            "s2w_wlan_version",
        )
        for key in string_keys:
            self.data[key] = ""

        self.data["manufact"] = MANUFACTURER
        self.data["model"] = MODEL

        # Initial diagnostic snapshot so sensors created at startup have values.
        self._update_diagnostic_data()
