"""Tests for 4-noks Elios4you sensor module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.const import CONF_SCAN_INTERVAL, DOMAIN, SENSOR_ENTITIES
from custom_components.fournoks_elios4you.sensor import Elios4YouSensor, async_setup_entry
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_SERIAL_NUMBER
from .test_config_flow import MockConfigEntry


@pytest.fixture
def mock_coordinator(mock_api_data):
    """Create a mock coordinator with API data."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    coordinator.api.name = TEST_NAME
    coordinator.api.host = TEST_HOST
    coordinator.api.data = mock_api_data
    coordinator.api.data["model"] = "Elios4you"
    coordinator.api.data["manufact"] = "4-noks"
    coordinator.api.data["sn"] = TEST_SERIAL_NUMBER
    coordinator.api.data["swver"] = "1.0 / 2.0"
    coordinator.api.data["hwver"] = "3.0"
    # Add all required sensor keys
    for sensor in SENSOR_ENTITIES:
        if sensor["key"] not in coordinator.api.data:
            coordinator.api.data[sensor["key"]] = 1.0
    return coordinator


class TestSensorSetup:
    """Tests for sensor platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_sensors(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test that setup creates sensor entities."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
            },
        )
        entry.add_to_hass(hass)

        # Create runtime_data structure
        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        entities = []

        def async_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, entry, async_add_entities)

        # async_setup_entry returns None (HA pattern), just verify entities were created
        assert len(entities) > 0
        # Should create sensors for all defined sensor entities
        assert len(entities) == len(SENSOR_ENTITIES)

    async def _setup(self, hass: HomeAssistant, coordinator) -> list:
        """Run the platform setup and collect the entities it creates."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )
        entry.add_to_hass(hass)
        runtime_data = MagicMock()
        runtime_data.coordinator = coordinator
        entry.runtime_data = runtime_data

        entities: list = []
        await async_setup_entry(hass, entry, entities.extend)
        return entities

    @pytest.mark.asyncio
    async def test_setup_creates_one_sensor_set_per_accessory_slot(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """A joined accessory gets the full set of five sensors.

        Online and Relay live on the binary_sensor platform, so the sensor
        platform contributes Power, Energy, Signal, Name and Device ID. Slots
        are discovered from the parsed data rather than hardcoded, so this also
        guards the case that motivated the change: a third accessory must be
        exposed without touching the code.
        """
        mock_coordinator.api.data.update(
            {
                "devha0": "1",
                "devha0_online": "1",
                "devha0_relay": "1",
                "devha0_power": "23",
                "devha0_energy": "1",
                "devha0_rssi": "-59",
                "devha0_devid": "81",
                "devha0_name": "PRESA_1",
            }
        )

        entities = await self._setup(hass, mock_coordinator)
        accessory = [e for e in entities if e._key.startswith("devha0_")]

        assert {e._key for e in accessory} == {
            "devha0_power",
            "devha0_energy",
            "devha0_rssi",
            "devha0_name",
            "devha0_devid",
        }
        assert len(entities) == len(SENSOR_ENTITIES) + 5

        # One translation key per sensor *type*, with the slot injected as a
        # placeholder: that is what keeps the translations at one string per
        # sensor type per language instead of one per accessory.
        power = next(e for e in accessory if e._key == "devha0_power")
        assert power._attr_translation_key == "devha_power"
        assert power._attr_translation_placeholders == {"slot": "1"}

    @pytest.mark.asyncio
    async def test_setup_skips_measurements_of_accessory_offline_at_first_poll(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """An accessory offline at the first poll gets only its state sensors.

        The offline guard in ``_parse_devha_row`` omits power, energy and RSSI, so
        on a cold start those keys have never existed and the entities are not
        created until the accessory reports. Deliberate: an entity showing 0 W for
        an accessory nobody has ever heard from would be a fabricated measurement.
        (Online and Relay are binary sensors, not sensors, so only Name and
        Device ID remain here.)
        """
        mock_coordinator.api.data.update(
            {
                "devha0": "1",
                "devha0_online": "0",
                "devha0_relay": "0",
                "devha0_devid": "81",
                "devha0_name": "PRESA_1",
            }
        )

        entities = await self._setup(hass, mock_coordinator)
        accessory = {e._key for e in entities if e._key.startswith("devha0_")}

        assert accessory == {
            "devha0_devid",
            "devha0_name",
        }

    @pytest.mark.asyncio
    async def test_accessory_sensors_are_added_dynamically_at_runtime(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Accessory sensors appear on a coordinator refresh, without a reload.

        Covers both dynamic cases: an accessory paired after HA starts, and an
        accessory that was offline at the first poll coming online (its
        measurement keys appear only then). Also asserts idempotency: a refresh
        with no new keys must not create duplicate entities.
        """
        entities = await self._setup(hass, mock_coordinator)
        assert not [e for e in entities if e._key.startswith("devha")]

        # The platform registered exactly one listener on the coordinator.
        listener = mock_coordinator.async_add_listener.call_args[0][0]

        # Accessory paired later, offline at its first appearance.
        mock_coordinator.api.data.update(
            {
                "devha0": 1,
                "devha0_online": 0,
                "devha0_relay": 0,
                "devha0_devid": 81,
                "devha0_name": "PRESA_1",
            }
        )
        listener()
        assert {e._key for e in entities if e._key.startswith("devha")} == {
            "devha0_devid",
            "devha0_name",
        }

        # Refresh without new keys: no duplicates.
        listener()
        assert len([e for e in entities if e._key.startswith("devha")]) == 2

        # The accessory comes online: measurement sensors appear on that poll.
        mock_coordinator.api.data.update(
            {"devha0_online": 1, "devha0_power": 23.0, "devha0_energy": 1.0, "devha0_rssi": -59}
        )
        listener()
        assert {e._key for e in entities if e._key.startswith("devha")} == {
            "devha0_devid",
            "devha0_name",
            "devha0_power",
            "devha0_energy",
            "devha0_rssi",
        }

    @pytest.mark.asyncio
    async def test_unpaired_accessory_entities_are_removed(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Un-pairing an accessory removes its entities from the registry.

        The API prunes the slot's keys from the data; the platform listener
        must then drop the registry entries (slot-level: an offline accessory
        keeps its row, so this never fires for a merely offline one) and
        forget the keys, so a re-paired accessory is recreated cleanly.
        """
        mock_coordinator.api.data.update(
            {"devha0": 1, "devha0_power": 23.0, "devha0_name": "PRESA_1"}
        )
        entities = await self._setup(hass, mock_coordinator)
        assert {e._key for e in entities if e._key.startswith("devha")} == {
            "devha0_power",
            "devha0_name",
        }
        listener = mock_coordinator.async_add_listener.call_args[0][0]

        # Register one of the two as the platform would have.
        entity_registry = er.async_get(hass)
        registered = entity_registry.async_get_or_create(
            "sensor", DOMAIN, f"{DOMAIN}_{TEST_SERIAL_NUMBER}_devha0_power"
        )

        # The accessory is un-paired: the API pruned every devha0 key.
        for key in list(mock_coordinator.api.data):
            if key.startswith("devha0"):
                del mock_coordinator.api.data[key]
        listener()

        assert entity_registry.async_get(registered.entity_id) is None

        # Re-pairing recreates the entities (created_keys was forgotten).
        mock_coordinator.api.data.update({"devha0": 1, "devha0_power": 30.0})
        listener()
        assert [e._key for e in entities if e._key.startswith("devha")].count("devha0_power") == 2

    @pytest.mark.asyncio
    async def test_async_setup_entry_skips_none_values(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test that setup skips sensors with None values."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
            },
        )
        entry.add_to_hass(hass)

        # Set one sensor key to None
        mock_coordinator.api.data["produced_power"] = None

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        entities = []

        def async_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, entry, async_add_entities)

        # Should have one less sensor
        assert len(entities) == len(SENSOR_ENTITIES) - 1


class TestSensorEntity:
    """Tests for sensor entity."""

    def test_sensor_init(self, mock_coordinator) -> None:
        """Test sensor initialization."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor._key == "produced_power"
        assert sensor._icon == "mdi:solar-power-variant-outline"
        assert sensor._device_class == SensorDeviceClass.POWER
        assert sensor._state_class == SensorStateClass.MEASUREMENT
        assert sensor._unit_of_measurement == UnitOfPower.KILO_WATT
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "produced_power"

    def test_sensor_unique_id(self, mock_coordinator) -> None:
        """Test sensor unique_id format."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        expected_id = f"{DOMAIN}_{TEST_SERIAL_NUMBER}_produced_power"
        assert sensor.unique_id == expected_id

    def test_sensor_native_value(self, mock_coordinator) -> None:
        """Test sensor native_value property."""
        mock_coordinator.api.data["produced_power"] = 2.5

        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.native_value == 2.5

    def test_sensor_native_value_missing_key(self, mock_coordinator) -> None:
        """Test sensor native_value returns None for missing key."""
        # Remove the key from data
        del mock_coordinator.api.data["produced_power"]

        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.native_value is None

    def test_sensor_native_unit_of_measurement(self, mock_coordinator) -> None:
        """Test sensor unit of measurement."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT

    def test_sensor_icon(self, mock_coordinator) -> None:
        """Test sensor icon property."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.icon == "mdi:solar-power-variant-outline"

    def test_sensor_device_class(self, mock_coordinator) -> None:
        """Test sensor device_class property."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.device_class == SensorDeviceClass.POWER

    def test_sensor_state_class(self, mock_coordinator) -> None:
        """Test sensor state_class property."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.state_class == SensorStateClass.MEASUREMENT

    def test_sensor_entity_category_none_for_measurement(self, mock_coordinator) -> None:
        """Test sensor entity_category is None for measurement sensors."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.entity_category is None

    def test_sensor_entity_category_diagnostic_for_no_state_class(self, mock_coordinator) -> None:
        """Test sensor entity_category is DIAGNOSTIC when no state_class."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Serial Number",
            "sn",
            "mdi:information-outline",
            None,  # No device_class
            None,  # No state_class
            None,  # No unit
            True,  # enabled_default
        )

        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_sensor_should_poll_false(self, mock_coordinator) -> None:
        """Test sensor should_poll is False (coordinator handles updates)."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.should_poll is False

    def test_sensor_state_attributes_none(self, mock_coordinator) -> None:
        """Test sensor state_attributes returns None."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        assert sensor.state_attributes is None

    def test_sensor_device_info(self, mock_coordinator) -> None:
        """Test sensor device_info property."""
        sensor = Elios4YouSensor(
            mock_coordinator,
            "Produced Power",
            "produced_power",
            "mdi:solar-power-variant-outline",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.KILO_WATT,
            True,  # enabled_default
        )

        device_info = sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, TEST_SERIAL_NUMBER)}
        assert device_info["manufacturer"] == "4-noks"
        assert device_info["model"] == "Elios4you"
        assert device_info["name"] == TEST_NAME
        assert device_info["serial_number"] == TEST_SERIAL_NUMBER
        assert device_info["sw_version"] == "1.0 / 2.0"
        assert device_info["hw_version"] == "3.0"

    def test_sensor_handle_coordinator_update(self, mock_coordinator) -> None:
        """Test sensor handles coordinator updates."""
        mock_coordinator.api.data["rcap"] = 42

        sensor = Elios4YouSensor(
            mock_coordinator,
            "RedCap",
            "rcap",
            "mdi:information-outline",
            None,
            None,
            None,
            True,  # enabled_default
        )
        sensor.async_write_ha_state = MagicMock()

        sensor._handle_coordinator_update()

        assert sensor._state == 42
        sensor.async_write_ha_state.assert_called_once()


class TestSensorTypes:
    """Tests for different sensor types."""

    def test_power_sensor(self, mock_coordinator) -> None:
        """Test power sensor configuration."""
        sensor_def = next(s for s in SENSOR_ENTITIES if s["key"] == "produced_power")

        sensor = Elios4YouSensor(
            mock_coordinator,
            sensor_def["name"],
            sensor_def["key"],
            sensor_def["icon"],
            sensor_def["device_class"],
            sensor_def["state_class"],
            sensor_def["unit"],
            sensor_def.get("enabled_default", True),
        )

        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT

    def test_energy_sensor(self, mock_coordinator) -> None:
        """Test energy sensor configuration."""
        sensor_def = next(s for s in SENSOR_ENTITIES if s["key"] == "produced_energy")

        sensor = Elios4YouSensor(
            mock_coordinator,
            sensor_def["name"],
            sensor_def["key"],
            sensor_def["icon"],
            sensor_def["device_class"],
            sensor_def["state_class"],
            sensor_def["unit"],
            sensor_def.get("enabled_default", True),
        )

        assert sensor.device_class == SensorDeviceClass.ENERGY
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR

    def test_diagnostic_sensor(self, mock_coordinator) -> None:
        """Test diagnostic sensor configuration."""
        sensor_def = next(s for s in SENSOR_ENTITIES if s["key"] == "sn")

        sensor = Elios4YouSensor(
            mock_coordinator,
            sensor_def["name"],
            sensor_def["key"],
            sensor_def["icon"],
            sensor_def["device_class"],
            sensor_def["state_class"],
            sensor_def["unit"],
            sensor_def.get("enabled_default", True),
        )

        assert sensor.device_class is None
        assert sensor.state_class is None
        assert sensor.native_unit_of_measurement is None
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
