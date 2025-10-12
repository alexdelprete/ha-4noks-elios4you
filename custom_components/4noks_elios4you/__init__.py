"""4-noks Elios4You integration.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_NAME,
    DOMAIN,
    STARTUP_MESSAGE,
)
from .coordinator import Elios4YouCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

# The type alias needs to be suffixed with 'ConfigEntry'
type Elios4YouConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator
    update_listener: Callable


async def async_setup_entry(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
) -> bool:
    """Set up integration from a config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)
    _LOGGER.debug("Setting up config_entry for %s", DOMAIN)

    # Initialise the coordinator that manages data updates from the API
    coordinator = Elios4YouCoordinator(hass, config_entry)

    # If the refresh fails, async_config_entry_first_refresh() will
    # raise ConfigEntryNotReady and setup will try again later
    await coordinator.async_config_entry_first_refresh()

    # Test to see if api initialised correctly, else raise ConfigNotReady to make HA retry setup
    if not coordinator.api.data["sn"]:
        raise ConfigEntryNotReady(
            f"Timeout connecting to {config_entry.data.get(CONF_NAME)}"
        )

    # Initialise a listener for config flow options changes
    update_listener = config_entry.add_update_listener(async_reload_entry)
    config_entry.async_on_unload(update_listener)

    # Add the coordinator and update listener to runtime data
    config_entry.runtime_data = RuntimeData(coordinator, update_listener)

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Register device
    await async_update_device_registry(hass, config_entry)

    return True


async def async_update_device_registry(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
) -> None:
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
    """Delete device if selected from UI."""
    # Adding this function shows the delete device option in the UI.
    if DOMAIN in device_entry.identifiers:
        _LOGGER.error(
            "Cannot delete the device using device delete. Remove the integration instead."
        )
        return False
    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        # Close API connection
        try:
            coordinator = config_entry.runtime_data.coordinator
            if coordinator and coordinator.api:
                coordinator.api.close()
                _LOGGER.debug("Closed API connection")
        except Exception as err:
            _LOGGER.error("Error closing API connection: %s", err)

    _LOGGER.debug("Config entry unload %s", "successful" if unload_ok else "failed")
    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
) -> None:
    """Reload the config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)
