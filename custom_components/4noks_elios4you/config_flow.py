"""Config Flow for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

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
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import Elios4YouAPI, TelnetCommandError, TelnetConnectionError
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_HOST,
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
from .helpers import host_valid, log_debug, log_error

_LOGGER = logging.getLogger(__name__)


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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "Elios4YouOptionsFlow":
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
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        CONF_ENABLE_REPAIR_NOTIFICATION,
                        default=enable_repair,
                    ): cv.boolean,
                    vol.Required(
                        CONF_FAILURES_THRESHOLD,
                        default=failures_threshold,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Clamp(min=MIN_FAILURES_THRESHOLD, max=MAX_FAILURES_THRESHOLD),
                    ),
                    vol.Optional(
                        CONF_RECOVERY_SCRIPT,
                        default=recovery_script,
                    ): EntitySelector(
                        EntitySelectorConfig(domain="script"),
                    ),
                },
            ),
        )
