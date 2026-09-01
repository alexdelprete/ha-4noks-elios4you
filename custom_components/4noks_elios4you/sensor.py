"""Sensor Platform Device for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import logging
from typing import Any, cast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Elios4YouConfigEntry
from .const import CONF_NAME, DEVHA_SENSOR_TEMPLATE, DOMAIN, SENSOR_ENTITIES
from .coordinator import Elios4YouCoordinator
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Elios4YouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensor Platform setup."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator = config_entry.runtime_data.coordinator

    log_debug(
        _LOGGER,
        "async_setup_entry",
        "Setting up sensors",
        name=config_entry.data.get(CONF_NAME),
        manufacturer=coordinator.api.data["manufact"],
        model=coordinator.api.data["model"],
        hw_version=coordinator.api.data["hwver"],
        sw_version=coordinator.api.data["swver"],
        serial_number=coordinator.api.data["sn"],
    )

    sensors = []
    for sensor in SENSOR_ENTITIES:
        sensor_def = cast(dict[str, Any], sensor)
        # ``.get()``: optional keys — such as the Smart RC accessory fields,
        # which only exist when a Red Cap module with paired accessories is
        # present — must not break setup on devices that never report them.
        if coordinator.api.data.get(sensor_def["key"]) is not None:
            sensors.append(
                Elios4YouSensor(
                    coordinator,
                    sensor_def["name"],
                    sensor_def["key"],
                    sensor_def["icon"],
                    sensor_def["device_class"],
                    sensor_def["state_class"],
                    sensor_def["unit"],
                    sensor_def["enabled_default"],
                )
            )

    # Smart RC wireless accessories: one set of sensors per slot actually
    # reported by the device, so a third or fourth paired accessory is exposed
    # without touching the code. Slots are discovered from the parsed data --
    # ``devha0``, ``devha1``, ... -- and numbered from 1 for the user.
    #
    # ``.get() is not None`` matters here beyond the usual "optional key" case:
    # power, energy and RSSI are deliberately not published while an accessory
    # is offline (see ``_parse_devha_row``), so on a cold start with an offline
    # accessory those three entities appear only after its first reading.
    for slot in sorted(
        {k.split("_", 1)[0] for k in coordinator.api.data if k.startswith("devha") and "_" in k}
    ):
        number = int(slot.removeprefix("devha")) + 1
        for template in DEVHA_SENSOR_TEMPLATE:
            key = f"{slot}{template['suffix']}"
            if coordinator.api.data.get(key) is None:
                continue
            sensors.append(
                Elios4YouSensor(
                    coordinator,
                    key,
                    key,
                    template["icon"],
                    template["device_class"],
                    template["state_class"],
                    template["unit"],
                    template["enabled_default"],
                    translation_key=template["translation_key"],
                    translation_placeholders={"slot": str(number)},
                )
            )

    async_add_entities(sensors)


class Elios4YouSensor(CoordinatorEntity[Elios4YouCoordinator], SensorEntity):
    """Representation of an Elios4You sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Elios4YouCoordinator,
        name: str,
        key: str,
        icon: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        unit: str | None,
        enabled_default: bool,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Class Initializitation."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._unit_of_measurement = unit
        self._device_name: str = self._coordinator.api.name
        self._device_host: str = self._coordinator.api.host
        self._device_model: str = str(self._coordinator.api.data.get("model", ""))
        self._device_manufact: str = str(self._coordinator.api.data.get("manufact", ""))
        self._device_sn: str = str(self._coordinator.api.data.get("sn", ""))
        self._device_swver: str = str(self._coordinator.api.data.get("swver", ""))
        self._device_hwver: str = str(self._coordinator.api.data.get("hwver", ""))
        # Use translation key for entity name (translations in translations/*.json).
        # Accessory sensors share one key per sensor type and pass the slot
        # number as a placeholder, so the translations don't have to be
        # duplicated for every paired accessory.
        self._attr_translation_key = translation_key or key
        if translation_placeholders:
            self._attr_translation_placeholders = translation_placeholders
        # No ``_attr_entity_category`` here on purpose: the ``entity_category``
        # property below already classifies as DIAGNOSTIC every sensor without a
        # state_class, which covers Online, Relay, Name and Device ID. Setting
        # the attribute would be dead code — an explicit property always wins.
        # Entity registry enabled default (False = disabled by default in UI)
        self._attr_entity_registry_enabled_default = enabled_default

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._state = self._coordinator.api.data[self._key]
        self.async_write_ha_state()
        # write debug log only on first sensor to avoid spamming the log
        if self._key == "rcap":
            log_debug(
                _LOGGER,
                "_handle_coordinator_update",
                "Sensors state written to state machine",
            )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self) -> str:
        """Return the sensor icon."""
        return self._icon

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the sensor device_class."""
        return self._device_class

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the sensor state_class."""
        return self._state_class

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the sensor entity_category."""
        if self._state_class is None:
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def native_value(self) -> int | float | str | None:
        """Return the state of the sensor."""
        if self._key in self._coordinator.api.data:
            return self._coordinator.api.data[self._key]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the extra state attributes."""
        return None

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

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
