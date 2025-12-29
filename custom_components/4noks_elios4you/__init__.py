"""4-noks Elios4You integration.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_NAME, CONF_SCAN_INTERVAL, DOMAIN, STARTUP_MESSAGE
from .coordinator import Elios4YouCoordinator
from .helpers import log_debug, log_error, log_info

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

# The type alias needs to be suffixed with 'ConfigEntry'
type Elios4YouConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: Elios4YouConfigEntry) -> bool:
    """Set up this integration using UI."""
    log_info(_LOGGER, "async_setup_entry", STARTUP_MESSAGE)
    log_debug(_LOGGER, "async_setup_entry", "Setup config_entry", domain=DOMAIN)

    # Initialise the coordinator that manages data updates from the API
    coordinator = Elios4YouCoordinator(hass, config_entry)

    # If the refresh fails, async_config_entry_first_refresh() will
    # raise ConfigEntryNotReady and setup will try again later
    # ref.: https://developers.home-assistant.io/docs/integration_setup_failures
    await coordinator.async_config_entry_first_refresh()

    # Test to see if api initialised correctly, else raise ConfigNotReady to make HA retry setup
    if not coordinator.api.data["sn"]:
        raise ConfigEntryNotReady(f"Timeout connecting to {config_entry.data.get(CONF_NAME)}")

    # Store coordinator in runtime_data to make it accessible throughout the integration
    config_entry.runtime_data = RuntimeData(coordinator)

    # Note: No manual update listener needed - OptionsFlowWithReload handles reload automatically

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Register device
    async_update_device_registry(hass, config_entry)

    # Return true to denote a successful setup
    return True


@callback
def async_update_device_registry(hass: HomeAssistant, config_entry: Elios4YouConfigEntry) -> None:
    """Manual device registration."""
    coordinator: Elios4YouCoordinator = config_entry.runtime_data.coordinator
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        hw_version=coordinator.api.data["hwver"],
        identifiers={(DOMAIN, coordinator.api.data["sn"])},
        manufacturer=coordinator.api.data["manufact"],
        model=coordinator.api.data["model"],
        name=config_entry.data.get(CONF_NAME),
        serial_number=coordinator.api.data["sn"],
        sw_version=coordinator.api.data["swver"],
        configuration_url=None,
        via_device=None,
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry
) -> bool:
    """Delete device if not entities."""
    if DOMAIN in device_entry.identifiers:
        log_error(
            _LOGGER,
            "async_remove_config_entry_device",
            "You cannot delete the device using device delete. Remove the integration instead.",
        )
        return False
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: Elios4YouConfigEntry) -> bool:
    """Unload a config entry."""
    log_debug(_LOGGER, "async_unload_entry", "Unload config_entry: started")

    # Unload platforms - only cleanup runtime_data if successful
    # ref.: https://developers.home-assistant.io/blog/2025/02/19/new-config-entry-states/
    if unload_ok := await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        log_debug(_LOGGER, "async_unload_entry", "Platforms unloaded successfully")
        # Cleanup per-entry resources only if unload succeeded
        config_entry.runtime_data.coordinator.api.close()
        log_debug(_LOGGER, "async_unload_entry", "Closed API connection")
    else:
        log_debug(_LOGGER, "async_unload_entry", "Platform unload failed, skipping cleanup")

    log_debug(
        _LOGGER,
        "async_unload_entry",
        "Unload config_entry: completed",
        unload_ok=unload_ok,
    )
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries.

    This function handles migration of config entries when the schema version changes.
    """
    log_debug(
        _LOGGER,
        "async_migrate_entry",
        "Migrating config entry",
        version=config_entry.version,
    )

    if config_entry.version == 1:
        # Migrate from v1 to v2: move scan_interval from data to options
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}

        # Move scan_interval to options if present in data
        if CONF_SCAN_INTERVAL in new_data:
            new_options[CONF_SCAN_INTERVAL] = new_data.pop(CONF_SCAN_INTERVAL)

        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options=new_options,
            version=2,
        )
        log_info(_LOGGER, "async_migrate_entry", "Migration to version 2 complete")

    return True
