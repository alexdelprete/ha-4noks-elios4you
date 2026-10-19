"""Config Flow for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .api import Elios4YouAPI, TelnetCommandError, TelnetConnectionError
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_RECOVERY_SCRIPT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_FAILURES_THRESHOLD,
    MAX_PORT,
    MAX_SCAN_INTERVAL,
    MIN_FAILURES_THRESHOLD,
    MIN_PORT,
    MIN_SCAN_INTERVAL,
)
from .discovery import DISCOVERY_SERIAL, async_discover_devices, async_probe_device
from .helpers import host_valid, log_debug, log_error

_LOGGER = logging.getLogger(__name__)


def _is_ip_address(host: str) -> bool:
    """Return True if ``host`` is an IP literal rather than a hostname."""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


@callback
def get_host_from_config(hass: HomeAssistant) -> set[str | None]:
    """Return the hosts already configured."""
    return {
        config_entry.data.get(CONF_HOST)
        for config_entry in hass.config_entries.async_entries(DOMAIN)
    }


class Elios4YouConfigFlow(ConfigFlow, domain=DOMAIN):
    """4-noks Elios4You config flow."""

    VERSION = 3
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str = ""
        self._discovered_serial: str = ""
        self._discovered_mac: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> Elios4YouOptionsFlow:
        """Initiate Options Flow Instance."""
        return Elios4YouOptionsFlow()

    def _host_in_configuration_exists(self, host: str | None) -> bool:
        """Return True if host exists in configuration."""
        return host in get_host_from_config(self.hass)

    async def _test_connection(
        self,
        name: str,
        host: str,
        port: int,
        scan_interval: int,
    ) -> str | None:
        """Test connection and return serial number or None on failure."""
        log_debug(_LOGGER, "_test_connection", "Testing connection", host=host, port=port)
        try:
            log_debug(_LOGGER, "_test_connection", "Creating API Client")
            api = Elios4YouAPI(self.hass, name, host, port)
            log_debug(_LOGGER, "_test_connection", "Fetching device data")
            await api.async_get_data()
            log_debug(_LOGGER, "_test_connection", "Successfully retrieved device data")
            return str(api.data["sn"])
        except (TelnetConnectionError, TelnetCommandError) as err:
            log_error(
                _LOGGER,
                "_test_connection",
                "Failed to connect",
                host=host,
                port=port,
                error=err,
            )
            return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            scan_interval = user_input[CONF_SCAN_INTERVAL]

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                uid = await self._test_connection(name, host, port, scan_interval)
                if uid is not None:
                    log_debug(_LOGGER, "async_step_user", "Device unique ID", uid=uid)
                    await self.async_set_unique_id(uid)
                    self._abort_if_unique_id_configured()

                    # Separate data (initial config) and options (runtime tuning)
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_NAME: name,
                            CONF_HOST: host,
                            CONF_PORT: port,
                        },
                        options={
                            CONF_SCAN_INTERVAL: scan_interval,
                        },
                    )

                errors[CONF_HOST] = "cannot_connect"

        # Best-effort UDP discovery (port 5002, non-exclusive so it cannot
        # disturb a running integration): pre-fill the host with the first
        # device that answers. Only on the initial form display — re-shows
        # after a validation error keep whatever the user typed.
        suggested_host: str | None = None
        if user_input is None:
            discovered = self._unconfigured(await async_discover_devices())
            if discovered:
                suggested_host = next(iter(discovered))
                log_debug(
                    _LOGGER,
                    "async_step_user",
                    "Discovered device(s) via UDP broadcast",
                    found=len(discovered),
                    suggested=suggested_host,
                )
        else:
            suggested_host = user_input.get(CONF_HOST)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=DEFAULT_NAME,
                    ): cv.string,
                    vol.Required(
                        CONF_HOST,
                        description={"suggested_value": suggested_host},
                    ): cv.string,
                    vol.Required(
                        CONF_PORT,
                        default=DEFAULT_PORT,
                    ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_PORT, max=MAX_PORT)),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                },
            ),
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/alexdelprete/ha-4noks-elios4you",
            },
        )

    @callback
    def _unconfigured(self, devices: dict[str, str]) -> dict[str, str]:
        """Drop devices whose host or serial already has a config entry."""
        hosts = get_host_from_config(self.hass)
        serials = {entry.unique_id for entry in self._async_current_entries(include_ignore=False)}
        return {
            host: serial
            for host, serial in devices.items()
            if host not in hosts and (not serial or serial not in serials)
        }

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """Handle a device seen by HA's DHCP watcher.

        The manifest matches the hostname the device sends (``E4U-<serial>``)
        or its WiFi module's MAC prefix, which other products share, so the
        device must prove it is an Elios4you by answering the UDP 5002 probe
        with its serial.
        """
        serial = await async_probe_device(discovery_info.ip)
        if not serial:
            return self.async_abort(reason="not_elios4you_device")
        return await self._async_handle_discovery(
            discovery_info.ip, serial, format_mac(discovery_info.macaddress)
        )

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle a device found by the integration's periodic UDP broadcast.

        The MAC, when present, comes from the HA host's ARP table.
        """
        serial = str(discovery_info.get(DISCOVERY_SERIAL, ""))
        if not serial:
            return self.async_abort(reason="not_elios4you_device")
        return await self._async_handle_discovery(
            str(discovery_info[CONF_HOST]), serial, discovery_info.get(CONF_MAC)
        )

    async def _async_handle_discovery(
        self, host: str, serial: str, mac: str | None = None
    ) -> ConfigFlowResult:
        """Deduplicate by serial, refresh a known device's IP/MAC, else ask to confirm."""
        await self.async_set_unique_id(serial)
        entry = self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, serial)
        updates: dict[str, str] = {}
        if entry is not None and _is_ip_address(str(entry.data.get(CONF_HOST, ""))):
            # Configured by IP and the device moved: follow it. A configured
            # hostname is left alone -- the user chose name resolution.
            updates[CONF_HOST] = host
        if mac:
            # The only source of the MAC: the device never reports it itself.
            updates[CONF_MAC] = mac
        self._abort_if_unique_id_configured(updates=updates or None)
        if self._host_in_configuration_exists(host):
            return self.async_abort(reason="already_configured")

        self._discovered_host = host
        self._discovered_serial = serial
        self._discovered_mac = mac
        self.context["title_placeholders"] = {"name": f"{DEFAULT_NAME} ({serial})"}
        log_debug(
            _LOGGER, "_async_handle_discovery", "Discovered new device", host=host, serial=serial
        )
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device and verify it over telnet."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            uid = await self._test_connection(
                name, self._discovered_host, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL
            )
            if uid is not None:
                if uid != self._discovered_serial:
                    # Telnet is authoritative for the entry's unique_id.
                    await self.async_set_unique_id(uid)
                    self._abort_if_unique_id_configured()
                data = {
                    CONF_NAME: name,
                    CONF_HOST: self._discovered_host,
                    CONF_PORT: DEFAULT_PORT,
                }
                if self._discovered_mac:
                    data[CONF_MAC] = self._discovered_mac
                return self.async_create_entry(
                    title=name,
                    data=data,
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string},
            ),
            errors=errors,
            description_placeholders={
                "host": self._discovered_host,
                "serial": self._discovered_serial,
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME]
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            log_debug(
                _LOGGER,
                "async_step_reconfigure",
                "Reconfigure requested",
                name=name,
                host=host,
                port=port,
            )

            if not host_valid(host):
                log_debug(_LOGGER, "async_step_reconfigure", "Invalid host", host=host)
                errors[CONF_HOST] = "invalid_host"
            else:
                # Test connection with new settings (use existing options for scan_interval)
                scan_interval = reconfigure_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )

                uid = await self._test_connection(name, host, port, scan_interval)
                if uid is not None:
                    # Verify unique ID matches before updating
                    await self.async_set_unique_id(uid)
                    self._abort_if_unique_id_mismatch()

                    log_debug(
                        _LOGGER,
                        "async_step_reconfigure",
                        "Connection test passed, applying reconfigure",
                        uid=uid,
                    )
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        title=name,
                        data_updates={
                            CONF_NAME: name,
                            CONF_HOST: host,
                            CONF_PORT: port,
                        },
                    )

                log_debug(_LOGGER, "async_step_reconfigure", "Connection test failed")
                errors[CONF_HOST] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=reconfigure_entry.data.get(CONF_NAME, DEFAULT_NAME),
                    ): cv.string,
                    vol.Required(
                        CONF_HOST,
                        default=reconfigure_entry.data.get(CONF_HOST),
                    ): cv.string,
                    vol.Required(
                        CONF_PORT,
                        default=reconfigure_entry.data.get(CONF_PORT, DEFAULT_PORT),
                    ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_PORT, max=MAX_PORT)),
                },
            ),
            errors=errors,
        )


class Elios4YouOptionsFlow(OptionsFlowWithReload):
    """Config flow options handler with auto-reload."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            log_debug(
                _LOGGER,
                "async_step_init",
                "Options updated",
                scan_interval=user_input.get(CONF_SCAN_INTERVAL),
                enable_repair_notification=user_input.get(CONF_ENABLE_REPAIR_NOTIFICATION),
                failures_threshold=user_input.get(CONF_FAILURES_THRESHOLD),
                recovery_script=user_input.get(CONF_RECOVERY_SCRIPT),
            )
            return self.async_create_entry(data=user_input)

        # Get current options with defaults
        current_options = self.config_entry.options
        enable_repair = current_options.get(
            CONF_ENABLE_REPAIR_NOTIFICATION, DEFAULT_ENABLE_REPAIR_NOTIFICATION
        )
        failures_threshold = current_options.get(
            CONF_FAILURES_THRESHOLD, DEFAULT_FAILURES_THRESHOLD
        )
        recovery_script = current_options.get(CONF_RECOVERY_SCRIPT, DEFAULT_RECOVERY_SCRIPT)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    # 1. Recovery script (right after variables description).
                    # ``description={"suggested_value": ...}`` pre-fills the
                    # form with the saved value but lets the user clear it.
                    # Using ``default=`` here would resurrect the old value on
                    # any submission where the field is empty — making the
                    # script impossible to remove via the UI.
                    vol.Optional(
                        CONF_RECOVERY_SCRIPT,
                        description={"suggested_value": recovery_script},
                    ): EntitySelector(
                        EntitySelectorConfig(domain="script"),
                    ),
                    # 2. Enable repair notifications checkbox
                    vol.Required(
                        CONF_ENABLE_REPAIR_NOTIFICATION,
                        default=enable_repair,
                    ): cv.boolean,
                    # 3. Failures threshold as input box (not slider)
                    vol.Required(
                        CONF_FAILURES_THRESHOLD,
                        default=failures_threshold,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_FAILURES_THRESHOLD,
                            max=MAX_FAILURES_THRESHOLD,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    # 4. Polling period at bottom
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="seconds",
                        )
                    ),
                },
            ),
        )
