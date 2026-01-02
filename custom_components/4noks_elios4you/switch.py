"""Switch Platform Device for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Elios4YouConfigEntry
from .const import DOMAIN, SWITCH_ENTITIES
from .coordinator import Elios4YouCoordinator
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Elios4YouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Switch Platform setup."""

    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator = config_entry.runtime_data.coordinator

    # Add defined switches using list comprehension
    switches = [
        Elios4YouSwitch(
            coordinator,
            switch["name"],
            switch["key"],
            switch["icon"],
            switch["device_class"],
        )
        for switch in SWITCH_ENTITIES
        if coordinator.api.data[switch["key"]] is not None
    ]

    async_add_entities(switches)

    return True


class Elios4YouSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to set the status of the Wiser Operation Mode (Away/Normal)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Elios4YouCoordinator,
        name: str,
        key: str,
        icon: str,
        device_class: SwitchDeviceClass | str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._is_on = self._coordinator.api.data["relay_state"]
        self._device_name: str = str(self._coordinator.api.name)
        self._device_host = self._coordinator.api.host
        self._device_model: str = str(self._coordinator.api.data["model"])
        self._device_manufact: str = str(self._coordinator.api.data["manufact"])
        self._device_sn: str = str(self._coordinator.api.data["sn"])
        self._device_swver: str = str(self._coordinator.api.data["swver"])
        self._device_hwver: str = str(self._coordinator.api.data["hwver"])
        # Use translation key for entity name (translations in translations/*.json)
        self._attr_translation_key = key
        log_debug(
            _LOGGER,
            "__init__",
            "Switch initialized",
            device=self._coordinator.api.name,
            key=self._key,
        )

    async def async_force_update(self, delay: int = 0) -> None:
        """Force Switch State Update."""
        log_debug(
            _LOGGER,
            "async_force_update",
            "Coordinator forced update initiated",
            key=self._key,
        )
        if delay:
            await asyncio.sleep(delay)
        await self._coordinator.async_update_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._coordinator.api.data["relay_state"]
        self.async_write_ha_state()
        log_debug(
            _LOGGER,
            "_handle_coordinator_update",
            "Switch coordinator update requested",
            key=self._key,
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return self._icon

    @property
    def device_class(self) -> SwitchDeviceClass:
        """Return the switch device_class."""
        return self._device_class  # type: ignore[return-value]

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the switch entity_category."""
        if self._device_class is SwitchDeviceClass.SWITCH:
            return EntityCategory.CONFIG
        return None

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        set_response = await self._coordinator.api.telnet_set_relay("on")
        if set_response:
            log_debug(_LOGGER, "async_turn_on", "Switch turned on")
        else:
            log_debug(_LOGGER, "async_turn_on", "Error turning switch on")
        # call coord update for immediate refresh state
        self._handle_coordinator_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        set_response = await self._coordinator.api.telnet_set_relay("off")
        if set_response:
            log_debug(_LOGGER, "async_turn_off", "Switch turned off")
        else:
            log_debug(_LOGGER, "async_turn_off", "Error turning switch off")
        # call coord update for immediate refresh state
        self._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            hw_version=self._device_hwver,
            identifiers={(DOMAIN, self._device_sn)},
            manufacturer=self._device_manufact,
            model=self._device_model,
            name=self._device_name,
            serial_number=self._device_sn,
            sw_version=self._device_swver,
        )
