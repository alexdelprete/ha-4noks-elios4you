"""Common fixtures for 4-noks Elios4you tests.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
import custom_components.fournoks_elios4you as _elios4you_init
from custom_components.fournoks_elios4you import (
    api as _elios4you_api,
    config_flow as _elios4you_config_flow,
)
from custom_components.fournoks_elios4you.const import CONF_SCAN_INTERVAL
import pytest

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

# Test constants
TEST_HOST = "192.168.1.100"
TEST_NAME = "Test Elios4you"
TEST_PORT = 5001
TEST_SCAN_INTERVAL = 60
TEST_SERIAL_NUMBER = "E4U123456789"


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance for unit tests that don't need real HA.

    Note: For integration tests, use the built-in `hass` fixture from
    pytest_homeassistant_custom_component instead.
    """
    mock = MagicMock(spec=HomeAssistant)
    mock.config_entries = MagicMock()
    mock.config_entries.async_entries = MagicMock(return_value=[])
    mock.data = {}  # Required for enable_custom_integrations fixture
    return mock


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
    }


@pytest.fixture
def mock_config_entry_options() -> dict:
    """Return mock config entry options."""
    return {
        CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
    }


@pytest.fixture
def mock_api_data() -> dict:
    """Return mock API data from Elios4you device."""
    return {
        "sn": TEST_SERIAL_NUMBER,
        "manufact": "4-noks",
        "model": "Elios4you",
        "swver": "1.0.0",
        "hwver": "2.0",
        "produced_power": 2.5,
        "consumed_power": 1.8,
        "self_consumed_power": 1.2,
        "bought_power": 0.6,
        "sold_power": 1.3,
        "daily_peak": 3.2,
        "monthly_peak": 4.5,
        "produced_energy": 1234.5,
        "consumed_energy": 987.6,
        "self_consumed_energy": 654.3,
        "bought_energy": 333.3,
        "sold_energy": 580.2,
        "relay_state": False,
        "alarm_1": "OK",
        "alarm_2": "OK",
        "power_alarm": "OK",
    }


@pytest.fixture
def mock_elios4you_api(mock_api_data: dict) -> Generator[MagicMock]:
    """Mock Elios4YouAPI for testing."""
    with patch.object(_elios4you_api, "Elios4YouAPI", autospec=True) as mock_api:
        api_instance = mock_api.return_value
        api_instance.data = mock_api_data
        api_instance.async_get_data = AsyncMock(return_value=True)
        api_instance.check_port = MagicMock(return_value=True)
        api_instance.close = AsyncMock()
        yield mock_api


@pytest.fixture
def mock_elios4you_api_config_flow(
    mock_api_data: dict,
) -> Generator[MagicMock]:
    """Mock Elios4YouAPI for config flow testing."""
    with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api:
        api_instance = mock_api.return_value
        api_instance.data = mock_api_data
        api_instance.async_get_data = AsyncMock(return_value=True)
        api_instance.check_port = MagicMock(return_value=True)
        yield mock_api


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock async_setup_entry."""
    with patch.object(
        _elios4you_init,
        "async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return
