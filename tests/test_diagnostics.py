"""Tests for 4-noks Elios4you diagnostics module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.const import CONF_SCAN_INTERVAL, DOMAIN, VERSION
from custom_components.fournoks_elios4you.diagnostics import async_get_config_entry_diagnostics
import pytest

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_SERIAL_NUMBER
from .test_config_flow import MockConfigEntry


@pytest.fixture
def mock_coordinator(mock_api_data):
    """Create a mock coordinator with API data."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    coordinator.api.data = mock_api_data
    coordinator.api.data["sn"] = TEST_SERIAL_NUMBER
    coordinator.api.data["manufact"] = "4-noks"
    coordinator.api.data["model"] = "Elios4you"
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(seconds=60)
    return coordinator


class TestDiagnostics:
    """Tests for diagnostics functionality."""

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics returns expected structure."""
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

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        # Check structure
        assert "config" in result
        assert "device" in result
        assert "coordinator" in result
        assert "sensors" in result

    @pytest.mark.asyncio
    async def test_diagnostics_config_section(self, hass: HomeAssistant, mock_coordinator) -> None:
        """Test diagnostics config section content."""
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

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        config = result["config"]
        assert config["entry_id"] == entry.entry_id
        assert config["version"] == entry.version
        assert config["domain"] == DOMAIN
        assert config["integration_version"] == VERSION
        assert config["options"][CONF_SCAN_INTERVAL] == TEST_SCAN_INTERVAL

    @pytest.mark.asyncio
    async def test_diagnostics_device_section(self, hass: HomeAssistant, mock_coordinator) -> None:
        """Test diagnostics device section content."""
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

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        device = result["device"]
        assert device["name"] == TEST_NAME
        assert device["port"] == TEST_PORT
        assert device["manufacturer"] == "4-noks"
        assert device["model"] == "Elios4you"
        # Serial number should be redacted
        assert device["serial_number"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_coordinator_section(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics coordinator section content."""
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

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        coordinator = result["coordinator"]
        assert coordinator["last_update_success"] is True
        assert coordinator["update_interval_seconds"] == 60.0

    @pytest.mark.asyncio
    async def test_diagnostics_redacts_sensitive_data(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics redacts sensitive data."""
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

        # Add sensitive data to API data
        mock_coordinator.api.data["sn"] = "SENSITIVE123"
        mock_coordinator.api.data["host"] = "192.168.1.100"

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        sensors = result["sensors"]
        # Serial number should be redacted
        assert sensors["sn"] == "**REDACTED**"
        # Host should be redacted if in data
        if "host" in sensors:
            assert sensors["host"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_includes_sensor_data(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics includes sensor data."""
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

        # Set some sensor values
        mock_coordinator.api.data["produced_power"] = 2.5
        mock_coordinator.api.data["consumed_power"] = 1.8

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        sensors = result["sensors"]
        assert sensors["produced_power"] == 2.5
        assert sensors["consumed_power"] == 1.8

    @pytest.mark.asyncio
    async def test_diagnostics_config_data_redacted(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics redacts host from config data."""
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

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        config_data = result["config"]["data"]
        # Host should be redacted
        assert config_data.get(CONF_HOST) == "**REDACTED**"
        # Name should NOT be redacted
        assert config_data.get(CONF_NAME) == TEST_NAME

    @pytest.mark.asyncio
    async def test_diagnostics_with_no_update_interval(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test diagnostics handles None update_interval."""
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

        mock_coordinator.update_interval = None

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        result = await async_get_config_entry_diagnostics(hass, entry)

        coordinator = result["coordinator"]
        assert coordinator["update_interval_seconds"] is None
