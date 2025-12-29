"""Tests for 4-noks Elios4you integration setup.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import importlib
from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

# Import modules with numeric prefix using importlib
_elios4you_init = importlib.import_module("custom_components.4noks_elios4you")
_elios4you_const = importlib.import_module("custom_components.4noks_elios4you.const")
_elios4you_coordinator = importlib.import_module("custom_components.4noks_elios4you.coordinator")

async_migrate_entry = _elios4you_init.async_migrate_entry
async_setup_entry = _elios4you_init.async_setup_entry
async_unload_entry = _elios4you_init.async_unload_entry

CONF_SCAN_INTERVAL = _elios4you_const.CONF_SCAN_INTERVAL
DEFAULT_SCAN_INTERVAL = _elios4you_const.DEFAULT_SCAN_INTERVAL
DOMAIN = _elios4you_const.DOMAIN

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL
from .test_config_flow import MockConfigEntry


async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_elios4you_api,
    mock_api_data,
) -> None:
    """Test successful setup of config entry."""
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

    with patch.object(
        _elios4you_coordinator,
        "Elios4YouAPI",
        return_value=mock_elios4you_api.return_value,
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    assert entry.runtime_data is not None


async def test_async_unload_entry(
    hass: HomeAssistant,
    mock_elios4you_api,
) -> None:
    """Test successful unload of config entry."""
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

    with patch.object(
        _elios4you_coordinator,
        "Elios4YouAPI",
        return_value=mock_elios4you_api.return_value,
    ):
        await async_setup_entry(hass, entry)
        result = await async_unload_entry(hass, entry)

    assert result is True


async def test_migration_v1_to_v2(
    hass: HomeAssistant,
) -> None:
    """Test migration from v1 to v2 moves scan_interval to options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_SCAN_INTERVAL: 90,  # v1 had scan_interval in data
        },
        options={},
        version=1,
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == 2
    assert CONF_SCAN_INTERVAL not in entry.data
    assert entry.options.get(CONF_SCAN_INTERVAL) == 90


async def test_migration_v1_to_v2_no_scan_interval(
    hass: HomeAssistant,
) -> None:
    """Test migration from v1 to v2 when scan_interval not in data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
        },
        options={},
        version=1,
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == 2
    # Options should not have scan_interval if it wasn't in data
    assert CONF_SCAN_INTERVAL not in entry.options
