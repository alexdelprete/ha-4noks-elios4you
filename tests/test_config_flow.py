"""Tests for 4-noks Elios4you config flow.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

# Import modules with numeric prefix using importlib
_elios4you_config_flow = importlib.import_module("custom_components.4noks_elios4you.config_flow")
_elios4you_const = importlib.import_module("custom_components.4noks_elios4you.const")

Elios4YouConfigFlow = _elios4you_config_flow.Elios4YouConfigFlow
CONF_SCAN_INTERVAL = _elios4you_const.CONF_SCAN_INTERVAL
DEFAULT_NAME = _elios4you_const.DEFAULT_NAME
DEFAULT_PORT = _elios4you_const.DEFAULT_PORT
DEFAULT_SCAN_INTERVAL = _elios4you_const.DEFAULT_SCAN_INTERVAL
DOMAIN = _elios4you_const.DOMAIN

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_SERIAL_NUMBER


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_elios4you_api_config_flow,
    mock_setup_entry,
) -> None:
    """Test successful user flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_NAME: TEST_NAME,
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
    }
    assert result["options"] == {
        CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
    }


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_elios4you_api_config_flow,
) -> None:
    """Test flow aborts when host already configured."""
    # Create existing entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "already_configured"}


async def test_user_flow_invalid_host(
    hass: HomeAssistant,
) -> None:
    """Test flow shows error for invalid host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: "not a valid host!@#",
            CONF_PORT: TEST_PORT,
            CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "invalid_host"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    mock_elios4you_api_config_flow,
) -> None:
    """Test flow shows error when cannot connect."""
    mock_elios4you_api_config_flow.return_value.async_get_data = AsyncMock(
        side_effect=Exception("Connection failed")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_options_flow(
    hass: HomeAssistant,
    mock_elios4you_api,
) -> None:
    """Test options flow allows changing scan interval."""
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

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 120,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SCAN_INTERVAL: 120,
    }


async def test_config_flow_version() -> None:
    """Test ConfigFlow VERSION is set correctly."""
    assert Elios4YouConfigFlow.VERSION == 2


# Helper class for tests
class MockConfigEntry(config_entries.ConfigEntry):
    """Mock ConfigEntry for testing."""

    def __init__(
        self,
        domain: str,
        data: dict,
        options: dict | None = None,
        unique_id: str | None = None,
        entry_id: str = "test",
        version: int = 2,
    ) -> None:
        """Initialize mock config entry."""
        super().__init__(
            data=data,
            disabled_by=None,
            discovery_keys={},
            domain=domain,
            entry_id=entry_id,
            minor_version=1,
            options=options or {},
            pref_disable_new_entities=False,
            pref_disable_polling=False,
            source=config_entries.SOURCE_USER,
            subentries_data={},  # Required for HA 2025.10+
            title=data.get(CONF_NAME, "Test"),
            unique_id=unique_id or TEST_SERIAL_NUMBER,
            version=version,
        )
        self._hass = None

    def add_to_hass(self, hass) -> None:
        """Add config entry to Home Assistant."""
        self._hass = hass
        hass.config_entries._entries[self.entry_id] = self
        if self.domain not in hass.data:
            hass.data[self.domain] = {}

    @property
    def runtime_data(self):
        """Return runtime data."""
        return getattr(self, "_runtime_data", None)

    @runtime_data.setter
    def runtime_data(self, value):
        """Set runtime data."""
        self._runtime_data = value
