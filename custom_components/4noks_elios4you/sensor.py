"""Sensor Platform Device for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_NAME,
    DATA,
    DOMAIN,
    SENSOR_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Sensor Platform setup."""

    # Get handler to coordinator from config
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA]

    _LOGGER.debug("(sensor) Name: %s", config_entry.data.get(CONF_NAME))
    _LOGGER.debug("(sensor) Manufacturer: %s", coordinator.api.data["manufact"])
    _LOGGER.debug("(sensor) Model: %s", coordinator.api.data["model"])
    _LOGGER.debug("(sensor) HW Version: %s", coordinator.api.data["hwver"])
    _LOGGER.debug("(sensor) SW Version: %s", coordinator.api.data["swver"])
    _LOGGER.debug("(sensor) Serial#: %s", coordinator.api.data["sn"])

    sensors = []
    for sensor in SENSOR_ENTITIES:
        if coordinator.api.data[sensor["key"]] is not None:
            sensors.append(
                Elios4YouSensor(
                    coordinator,
                    sensor["name"],
                    sensor["key"],
                    sensor["icon"],
                    sensor["device_class"],
                    sensor["state_class"],
                    sensor["unit"],
                )
            )

    async_add_entities(sensors)

    return True


class Elios4YouSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Elios4You sensor."""

    def __init__(self, coordinator, name, key, icon, device_class, state_class, unit):
        """Class Initializitation."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._name = name
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._unit_of_measurement = unit
        self._device_name = self._coordinator.api.name
        self._device_host = self._coordinator.api.host
        self._device_model = self._coordinator.api.data["model"]
        self._device_manufact = self._coordinator.api.data["manufact"]
        self._device_sn = self._coordinator.api.data["sn"]
        self._device_swver = self._coordinator.api.data["swver"]
        self._device_hwver = self._coordinator.api.data["hwver"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._state = self._coordinator.api.data[self._key]
        self.async_write_ha_state()
        # write debug log only on first sensor to avoid spamming the log
        if self.name == "RedCap":
            _LOGGER.debug(
                "_handle_coordinator_update: sensors state written to state machine"
            )

    @property
    def has_entity_name(self):
        """Return the name state."""
        return True

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

    @property
    def device_class(self):
        """Return the sensor device_class."""
        return self._device_class

    @property
    def state_class(self):
        """Return the sensor state_class."""
        return self._state_class

    @property
    def entity_category(self):
        """Return the sensor entity_category."""
        if self._state_class is None:
            return EntityCategory.DIAGNOSTIC
        else:
            return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._key in self._coordinator.api.data:
            return self._coordinator.api.data[self._key]

    @property
    def state_attributes(self) -> dict[str, Any] | None:
        """Return the attributes."""
        return None

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

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
