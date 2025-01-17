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


async def async_setup_entry(hass: HomeAssistant, config_entry: Elios4YouConfigEntry):
    """Set up integration from a config entry."""

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)
    _LOGGER.debug(f"Setup config_entry for {DOMAIN}")

    # Initialise the coordinator that manages data updates from your api.
    # This is defined in coordinator.py
    coordinator = Elios4YouCoordinator(hass, config_entry)

    # If the refresh fails, async_config_entry_first_refresh() will
    # raise ConfigEntryNotReady and setup will try again later
    # ref.: https://developers.home-assistant.io/docs/integration_setup_failures
    await coordinator.async_config_entry_first_refresh()

    # Test to see if api initialised correctly, else raise ConfigNotReady to make HA retry setup
    # Change this to match how your api will know if connected or successful update
    if not coordinator.api.data["sn"]:
        raise ConfigEntryNotReady(
            f"Timeout connecting to {config_entry.data.get(CONF_NAME)}"
        )

    # Initialise a listener for config flow options changes.
    # See config_flow for defining an options setting that shows up as configure on the integration.
    update_listener = config_entry.add_update_listener(async_reload_entry)

    # Register an update listener to the config entry that will be called when the entry is updated
    # ref.: https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates
    config_entry.async_on_unload(update_listener)

    # Add the coordinator and update listener to hass data to make
    # accessible throughout your integration
    # Note: this will change on HA2024.6 to save on the config entry.
    config_entry.runtime_data = RuntimeData(coordinator, update_listener)

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Regiser device
    await async_update_device_registry(hass, config_entry)

    # Return true to denote a successful setup.
    return True


async def async_update_device_registry(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
):
    """Manual device registration."""
    # This gets the data update coordinator from hass.data
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
    hass: HomeAssistant, config_entry, device_entry
) -> bool:
    """Delete device if selected from UI."""
    # Adding this function shows the delete device option in the UI.
    # Remove this function if you do not want that option.
    # You may need to do some checks here before allowing devices to be removed.
    if DOMAIN in device_entry.identifiers:
        _LOGGER.error(
            "You cannot delete the device using device delete. Remove the integration instead."
        )
        return False
    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
) -> bool:
    """Unload a config entry."""
    # This is called when you remove your integration or shutdown HA.
    # If you have created any custom services, they need to be removed here too.

    _LOGGER.debug("Unload config_entry: started")

    # Unload platforms and cleanup resources
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        try:
            # Close API connection if exists
            # coordinator = getattr(config_entry.runtime_data, 'coordinator', None)
            coordinator = config_entry.runtime_data.coordinator
            if coordinator.api:
                coordinator.api.close()
                _LOGGER.debug("Closed API connection")

            # Remove update listener if exists
            if config_entry.entry_id in hass.data[DOMAIN]:
                update_listener = config_entry.runtime_data.update_listener
                if update_listener:
                    update_listener()
                _LOGGER.debug("Removed update listener")

                # Remove config entry from hass data
                hass.data[DOMAIN].pop(config_entry.entry_id)
                _LOGGER.debug("Removed config entry from hass data")
        except Exception as ex:
            _LOGGER.error(f"Error during unload: {str(ex)}")
            return False
    else:
        _LOGGER.debug("Failed to unload platforms")

    _LOGGER.debug("Unload config_entry: completed")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: Elios4YouConfigEntry):
    """Reload the config entry."""
    await hass.config_entries.async_schedule_reload(config_entry.entry_id)


# Sample migration code in case it's needed
# async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
#     """Migrate an old config_entry."""
#     version = config_entry.version

#     # 1-> 2: Migration format
#     if version == 1:
#         # Get handler to coordinator from config
#         coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA]
#         _LOGGER.debug("Migrating from version %s", version)
#         old_uid = config_entry.unique_id
#         new_uid = coordinator.api.data["sn"]
#         if old_uid != new_uid:
#             hass.config_entries.async_update_entry(
#                 config_entry, unique_id=new_uid
#             )
#             _LOGGER.debug("Migration to version %s complete: OLD_UID: %s - NEW_UID: %s", config_entry.version, old_uid, new_uid)
#         if config_entry.unique_id == new_uid:
#             config_entry.version = 2
#             _LOGGER.debug("Migration to version %s complete: NEW_UID: %s", config_entry.version, config_entry.unique_id)
#     return True
