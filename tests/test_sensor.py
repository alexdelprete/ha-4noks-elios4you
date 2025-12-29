"""Tests for 4-noks Elios4you sensor module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock

import pytest

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

# Import modules with numeric prefix using importlib
_elios4you_sensor = importlib.import_module("custom_components.4noks_elios4you.sensor")
_elios4you_const = importlib.import_module("custom_components.4noks_elios4you.const")

async_setup_entry = _elios4you_sensor.async_setup_entry
Elios4YouSensor = _elios4you_sensor.Elios4YouSensor
CONF_SCAN_INTERVAL = _elios4you_const.CONF_SCAN_INTERVAL
DOMAIN = _elios4you_const.DOMAIN
SENSOR_ENTITIES = _elios4you_const.SENSOR_ENTITIES

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

        result = await async_setup_entry(hass, entry, async_add_entities)

        assert result is True
        assert len(entities) > 0
        # Should create sensors for all defined sensor entities
        assert len(entities) == len(SENSOR_ENTITIES)

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
