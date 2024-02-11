"""Switch Platform Device for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""
import asyncio
import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA, DOMAIN, SWITCH_ENTITIES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Switch Platform setup."""

    # Get handler to coordinator from config
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA]

    # Add defined switches
    switches = []
    for switch in SWITCH_ENTITIES:
        if coordinator.api.data[switch["key"]] is not None:
            switches.append(
                Elios4YouSwitch(
                    coordinator,
                    switch["name"],
                    switch["key"],
                    switch["icon"],
                    switch["device_class"],
                )
            )

    async_add_entities(switches)

    return True


class Elios4YouSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to set the status of the Wiser Operation Mode (Away/Normal)."""

    def __init__(self, coordinator, name, key, icon, device_class) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._name = name
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._is_on = self._coordinator.api.data["relay_state"]
        self._device_name = self._coordinator.api.name
        self._device_host = self._coordinator.api.host
        self._device_model = self._coordinator.api.data["model"]
        self._device_manufact = self._coordinator.api.data["manufact"]
        self._device_sn = self._coordinator.api.data["sn"]
        self._device_swver = self._coordinator.api.data["swver"]
        self._device_hwver = self._coordinator.api.data["hwver"]
        _LOGGER.debug(f"{self._coordinator.api.data.name} {self.name} init")

    async def async_force_update(self, delay: int = 0):
        """Force Switch State Update."""
        _LOGGER.debug(f"Coordinator update initiated by {self.name}")
        if delay:
            await asyncio.sleep(delay)
        await self._coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._coordinator.api.data["relay_state"]
        self.async_write_ha_state()
        _LOGGER.debug(f"{self.name} switch update requested")

    @property
    def name(self):
        """Return the name of the Device."""
        return f"{self._name}"

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def device_class(self):
        """Return the switch device_class."""
        return self._device_class

    @property
    def entity_category(self):
        """Return the switch entity_category."""
        if self._state_class is SwitchDeviceClass.SWITCH:
            return EntityCategory.CONFIG
        else:
            return None

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        set_response = await self._coordinator.api.telnet_set_relay("on")
        if set_response:
            _LOGGER.debug("switch async_turn_on: turned on")
        else:
            _LOGGER.debug("switch async_turn_on: error turning on")
        await self.async_force_update()
        return set_response

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        set_response = await self._coordinator.api.telnet_set_relay("off")
        if set_response:
            _LOGGER.debug("switch async_turn_on: turned off")
        else:
            _LOGGER.debug("switch async_turn_on: error turning off")
        await self.async_force_update()
        return set_response

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "configuration_url": None,
            "hw_version": self._device_hwver,
            "identifiers": {(DOMAIN, self._device_sn)},
            "manufacturer": self._device_manufact,
            "model": self._device_model,
            "name": self._device_name,
            "serial_number": self._device_sn,
            "sw_version": self._device_swver,
            "via_device": None,
        }
