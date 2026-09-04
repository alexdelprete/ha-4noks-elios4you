"""Binary Sensor Platform Device for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you

Smart RC wireless accessories report two genuinely binary states — Online
(joined/not joined) and Relay (contact closed/open, a real physical contact in
the accessory) — which live here rather than as 0/1 numeric sensors. Relay is
read-only until the ``@rel <n>`` accessory-addressing hypothesis is confirmed
on real hardware; if it holds, it graduates to a switch entity.
"""

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Elios4YouConfigEntry
from .const import CONF_NAME, DEVHA_BINARY_SENSOR_TEMPLATE, DOMAIN
from .coordinator import Elios4YouCoordinator
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Elios4YouConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary Sensor Platform setup."""
    coordinator = config_entry.runtime_data.coordinator

    log_debug(
        _LOGGER,
        "async_setup_entry",
        "Setting up binary sensors",
        name=config_entry.data.get(CONF_NAME),
    )

    # Accessory slots are discovered dynamically, exactly as on the sensor
    # platform: the tracked-keys set plus a coordinator listener means an
    # accessory paired after HA starts gets its entities on the next poll,
    # with no integration reload needed.
    created_keys: set[str] = set()

    @callback
    def _async_add_new_accessory_binary_sensors() -> None:
        new_entities = _build_accessory_binary_sensors(coordinator, created_keys)
        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_accessory_binary_sensors()
    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_accessory_binary_sensors)
    )


def _build_accessory_binary_sensors(
    coordinator: Elios4YouCoordinator, created_keys: set[str]
) -> list[Elios4YouBinarySensor]:
    """Build binary sensors for accessory keys not yet turned into entities.

    ``created_keys`` is updated in place so repeated calls (initial setup, then
    every coordinator refresh) only create each entity once. Online and Relay
    survive the offline guard in ``_parse_devha_row``, so both appear as soon
    as their slot does.
    """
    new_entities: list[Elios4YouBinarySensor] = []
    for slot in sorted(
        {k.split("_", 1)[0] for k in coordinator.api.data if k.startswith("devha") and "_" in k}
    ):
        number = int(slot.removeprefix("devha")) + 1
        for template in DEVHA_BINARY_SENSOR_TEMPLATE:
            key = f"{slot}{template['suffix']}"
            if key in created_keys or coordinator.api.data.get(key) is None:
                continue
            created_keys.add(key)
            new_entities.append(
                Elios4YouBinarySensor(
                    coordinator,
                    key,
                    template["icon"],
                    template["device_class"],
                    template["enabled_default"],
                    template["translation_key"],
                    {"slot": str(number)},
                )
            )
    return new_entities


class Elios4YouBinarySensor(CoordinatorEntity[Elios4YouCoordinator], BinarySensorEntity):
    """Representation of an Elios4You accessory binary sensor."""

    _attr_has_entity_name = True
    # Both accessory states describe the accessory itself, not a measurement.
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: Elios4YouCoordinator,
        key: str,
        icon: str,
        device_class: BinarySensorDeviceClass | None,
        enabled_default: bool,
        translation_key: str,
        translation_placeholders: dict[str, str],
    ) -> None:
        """Class Initialization."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._key = key
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_translation_key = translation_key
        self._attr_translation_placeholders = translation_placeholders
        self._device_name: str = self._coordinator.api.name
        self._device_model: str = str(self._coordinator.api.data.get("model", ""))
        self._device_manufact: str = str(self._coordinator.api.data.get("manufact", ""))
        self._device_sn: str = str(self._coordinator.api.data.get("sn", ""))
        self._device_swver: str = str(self._coordinator.api.data.get("swver", ""))
        self._device_hwver: str = str(self._coordinator.api.data.get("hwver", ""))

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write new state on coordinator refresh."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return True when the state value is 1 (joined / contact closed)."""
        value = self._coordinator.api.data.get(self._key)
        if value is None:
            return None
        return bool(int(value))

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
