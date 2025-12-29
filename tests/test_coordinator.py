"""Tests for 4-noks Elios4you coordinator module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from datetime import timedelta
import importlib
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

# Import modules with numeric prefix using importlib
_elios4you_coordinator = importlib.import_module("custom_components.4noks_elios4you.coordinator")
_elios4you_const = importlib.import_module("custom_components.4noks_elios4you.const")
_elios4you_api = importlib.import_module("custom_components.4noks_elios4you.api")

Elios4YouCoordinator = _elios4you_coordinator.Elios4YouCoordinator
CONF_SCAN_INTERVAL = _elios4you_const.CONF_SCAN_INTERVAL
DEFAULT_SCAN_INTERVAL = _elios4you_const.DEFAULT_SCAN_INTERVAL
MIN_SCAN_INTERVAL = _elios4you_const.MIN_SCAN_INTERVAL
DOMAIN = _elios4you_const.DOMAIN
TelnetConnectionError = _elios4you_api.TelnetConnectionError
TelnetCommandError = _elios4you_api.TelnetCommandError

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_SERIAL_NUMBER
from .test_config_flow import MockConfigEntry


class TestCoordinatorInit:
    """Tests for coordinator initialization."""

    def test_coordinator_init_from_options(self, hass: HomeAssistant) -> None:
        """Test coordinator initialization reads from options."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
            },
            options={
                CONF_SCAN_INTERVAL: 120,
            },
        )
        entry.add_to_hass(hass)

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(hass, entry)

        assert coordinator.conf_name == TEST_NAME
        assert coordinator.conf_host == TEST_HOST
        assert coordinator.conf_port == TEST_PORT
        assert coordinator.scan_interval == 120
        assert coordinator.update_interval == timedelta(seconds=120)

    def test_coordinator_init_from_data_fallback(self, hass: HomeAssistant) -> None:
        """Test coordinator falls back to data when options empty."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SCAN_INTERVAL: 90,  # v1 style in data
            },
            options={},
        )
        entry.add_to_hass(hass)

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(hass, entry)

        assert coordinator.scan_interval == 90

    def test_coordinator_init_enforces_min_interval(self, hass: HomeAssistant) -> None:
        """Test coordinator enforces minimum scan interval."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
            },
            options={
                CONF_SCAN_INTERVAL: 10,  # Below minimum
            },
        )
        entry.add_to_hass(hass)

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(hass, entry)

        assert coordinator.scan_interval == MIN_SCAN_INTERVAL

    def test_coordinator_init_default_interval(self, hass: HomeAssistant) -> None:
        """Test coordinator uses default interval when not specified."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
            },
            options={},
        )
        entry.add_to_hass(hass)

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(hass, entry)

        assert coordinator.scan_interval == DEFAULT_SCAN_INTERVAL

    def test_coordinator_creates_api(self, hass: HomeAssistant) -> None:
        """Test coordinator creates API instance."""
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

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI") as mock_api_class:
            coordinator = Elios4YouCoordinator(hass, entry)

        mock_api_class.assert_called_once_with(
            hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
        )
        assert coordinator.api == mock_api_class.return_value


class TestCoordinatorUpdate:
    """Tests for coordinator update functionality."""

    @pytest.mark.asyncio
    async def test_async_update_data_success(self, hass: HomeAssistant) -> None:
        """Test successful data update."""
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

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(return_value=True)

            coordinator = Elios4YouCoordinator(hass, entry)
            result = await coordinator.async_update_data()

        assert result is True
        assert coordinator.last_update_status is True
        mock_api.async_get_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_update_data_failure(self, hass: HomeAssistant) -> None:
        """Test data update failure raises UpdateFailed."""
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

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )

            coordinator = Elios4YouCoordinator(hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

        assert coordinator.last_update_status is False

    @pytest.mark.asyncio
    async def test_async_update_data_command_error(self, hass: HomeAssistant) -> None:
        """Test data update with command error raises UpdateFailed."""
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

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=TelnetCommandError("@dat"))

            coordinator = Elios4YouCoordinator(hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_generic_exception(self, hass: HomeAssistant) -> None:
        """Test data update with generic exception raises UpdateFailed."""
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

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=Exception("Unknown error"))

            coordinator = Elios4YouCoordinator(hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_updates_timestamp(self, hass: HomeAssistant) -> None:
        """Test data update updates last_update_time."""
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

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(return_value=True)

            coordinator = Elios4YouCoordinator(hass, entry)
            initial_time = coordinator.last_update_time

            await coordinator.async_update_data()

        assert coordinator.last_update_time >= initial_time


class TestCoordinatorName:
    """Tests for coordinator naming."""

    def test_coordinator_name_includes_unique_id(self, hass: HomeAssistant) -> None:
        """Test coordinator name includes unique_id."""
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
            unique_id=TEST_SERIAL_NUMBER,
        )
        entry.add_to_hass(hass)

        with patch("custom_components.4noks_elios4you.coordinator.Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(hass, entry)

        assert DOMAIN in coordinator.name
        assert TEST_SERIAL_NUMBER in coordinator.name
