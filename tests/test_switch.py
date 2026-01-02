"""Tests for 4-noks Elios4you switch module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.const import CONF_SCAN_INTERVAL, DOMAIN, SWITCH_ENTITIES
from custom_components.fournoks_elios4you.switch import Elios4YouSwitch, async_setup_entry
import pytest

from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
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
    coordinator.api.data["relay_state"] = 0
    coordinator.api.telnet_set_relay = AsyncMock(return_value=True)
    coordinator.async_update_data = AsyncMock()
    return coordinator


class TestSwitchSetup:
    """Tests for switch platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_switches(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test that setup creates switch entities."""
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

        entities = []

        def async_add_entities(new_entities):
            entities.extend(new_entities)

        result = await async_setup_entry(hass, entry, async_add_entities)

        assert result is True
        assert len(entities) == len(SWITCH_ENTITIES)

    @pytest.mark.asyncio
    async def test_async_setup_entry_skips_none_values(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Test that setup skips switches with None values."""
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

        # Set relay_state to None
        mock_coordinator.api.data["relay_state"] = None

        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        entities = []

        def async_add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, entry, async_add_entities)

        # Should have no switches
        assert len(entities) == 0


class TestSwitchEntity:
    """Tests for switch entity."""

    def test_switch_init(self, mock_coordinator) -> None:
        """Test switch initialization."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        assert switch._key == "relay_state"
        assert switch._icon == "mdi:toggle-switch-outline"
        assert switch._device_class == SwitchDeviceClass.SWITCH
        assert switch._attr_has_entity_name is True
        assert switch._attr_translation_key == "relay_state"

    def test_switch_unique_id(self, mock_coordinator) -> None:
        """Test switch unique_id format."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        expected_id = f"{DOMAIN}_{TEST_SERIAL_NUMBER}_relay_state"
        assert switch.unique_id == expected_id

    def test_switch_icon(self, mock_coordinator) -> None:
        """Test switch icon property."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        assert switch.icon == "mdi:toggle-switch-outline"

    def test_switch_device_class(self, mock_coordinator) -> None:
        """Test switch device_class property."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        assert switch.device_class == SwitchDeviceClass.SWITCH

    def test_switch_entity_category_config_for_switch(self, mock_coordinator) -> None:
        """Test switch entity_category is CONFIG for switch device class."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        assert switch.entity_category == EntityCategory.CONFIG

    def test_switch_entity_category_none_for_other(self, mock_coordinator) -> None:
        """Test switch entity_category is None for non-switch device class."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            None,  # No device class
        )

        assert switch.entity_category is None

    def test_switch_is_on_true(self, mock_coordinator) -> None:
        """Test switch is_on returns True when state is 1."""
        mock_coordinator.api.data["relay_state"] = 1

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        assert switch.is_on is True

    def test_switch_is_on_false(self, mock_coordinator) -> None:
        """Test switch is_on returns False when state is 0."""
        mock_coordinator.api.data["relay_state"] = 0

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        assert switch.is_on is False

    def test_switch_device_info(self, mock_coordinator) -> None:
        """Test switch device_info property."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        device_info = switch.device_info

        assert device_info["identifiers"] == {(DOMAIN, TEST_SERIAL_NUMBER)}
        assert device_info["manufacturer"] == "4-noks"
        assert device_info["model"] == "Elios4you"
        assert device_info["name"] == TEST_NAME
        assert device_info["serial_number"] == TEST_SERIAL_NUMBER
        assert device_info["sw_version"] == "1.0 / 2.0"
        assert device_info["hw_version"] == "3.0"


class TestSwitchTurnOnOff:
    """Tests for switch turn on/off functionality."""

    @pytest.mark.asyncio
    async def test_async_turn_on_success(self, mock_coordinator) -> None:
        """Test turning switch on successfully."""
        mock_coordinator.api.telnet_set_relay = AsyncMock(return_value=True)

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_on()

        # async_turn_on returns None (SwitchEntity pattern), verify API was called
        mock_coordinator.api.telnet_set_relay.assert_called_once_with("on")

    @pytest.mark.asyncio
    async def test_async_turn_on_failure(self, mock_coordinator) -> None:
        """Test turning switch on fails."""
        mock_coordinator.api.telnet_set_relay = AsyncMock(return_value=False)

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_on()

        # async_turn_on returns None (SwitchEntity pattern), verify API was called
        mock_coordinator.api.telnet_set_relay.assert_called_once_with("on")

    @pytest.mark.asyncio
    async def test_async_turn_off_success(self, mock_coordinator) -> None:
        """Test turning switch off successfully."""
        mock_coordinator.api.telnet_set_relay = AsyncMock(return_value=True)

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_off()

        # async_turn_off returns None (SwitchEntity pattern), verify API was called
        mock_coordinator.api.telnet_set_relay.assert_called_once_with("off")

    @pytest.mark.asyncio
    async def test_async_turn_off_failure(self, mock_coordinator) -> None:
        """Test turning switch off fails."""
        mock_coordinator.api.telnet_set_relay = AsyncMock(return_value=False)

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_off()

        # async_turn_off returns None (SwitchEntity pattern), verify API was called
        mock_coordinator.api.telnet_set_relay.assert_called_once_with("off")

    @pytest.mark.asyncio
    async def test_turn_on_calls_coordinator_update(self, mock_coordinator) -> None:
        """Test that turn on triggers coordinator update."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_on()

        # Should call async_write_ha_state via _handle_coordinator_update
        switch.async_write_ha_state.assert_called()

    @pytest.mark.asyncio
    async def test_turn_off_calls_coordinator_update(self, mock_coordinator) -> None:
        """Test that turn off triggers coordinator update."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_off()

        # Should call async_write_ha_state via _handle_coordinator_update
        switch.async_write_ha_state.assert_called()


class TestSwitchForceUpdate:
    """Tests for switch force update functionality."""

    @pytest.mark.asyncio
    async def test_async_force_update_no_delay(self, mock_coordinator) -> None:
        """Test force update without delay."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        await switch.async_force_update()

        mock_coordinator.async_update_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_force_update_with_delay(self, mock_coordinator) -> None:
        """Test force update with delay."""
        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )

        # Use small delay for test speed
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await switch.async_force_update(delay=1)

            mock_sleep.assert_called_once_with(1)
            mock_coordinator.async_update_data.assert_called_once()


class TestSwitchCoordinatorUpdate:
    """Tests for switch coordinator update handling."""

    def test_handle_coordinator_update(self, mock_coordinator) -> None:
        """Test switch handles coordinator updates."""
        mock_coordinator.api.data["relay_state"] = 1

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        assert switch._is_on == 1
        switch.async_write_ha_state.assert_called_once()

    def test_handle_coordinator_update_changes_state(self, mock_coordinator) -> None:
        """Test switch state changes on coordinator update."""
        mock_coordinator.api.data["relay_state"] = 0

        switch = Elios4YouSwitch(
            mock_coordinator,
            "Relay",
            "relay_state",
            "mdi:toggle-switch-outline",
            SwitchDeviceClass.SWITCH,
        )
        switch.async_write_ha_state = MagicMock()

        # Initial state is 0
        assert switch._is_on == 0
        assert switch.is_on is False

        # Update to 1
        mock_coordinator.api.data["relay_state"] = 1
        switch._handle_coordinator_update()

        assert switch._is_on == 1
        assert switch.is_on is True
