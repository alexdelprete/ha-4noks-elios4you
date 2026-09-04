"""Tests for 4-noks Elios4you binary_sensor module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.binary_sensor import (
    Elios4YouBinarySensor,
    async_setup_entry,
)
from custom_components.fournoks_elios4you.const import CONF_SCAN_INTERVAL, DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
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
    return coordinator


class TestBinarySensorSetup:
    """Tests for binary_sensor platform setup."""

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
    async def test_setup_without_accessories_creates_nothing(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """A device with no Red Cap accessories gets no binary sensors."""
        entities = await self._setup(hass, mock_coordinator)
        assert entities == []

    @pytest.mark.asyncio
    async def test_setup_creates_online_and_relay_per_slot(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Each discovered accessory slot gets an Online and a Relay entity."""
        mock_coordinator.api.data.update(
            {
                "devha0": 1,
                "devha0_online": 1,
                "devha0_relay": 0,
                "devha1": 1,
                "devha1_online": 0,
                "devha1_relay": 0,
            }
        )

        entities = await self._setup(hass, mock_coordinator)

        assert {e._key for e in entities} == {
            "devha0_online",
            "devha0_relay",
            "devha1_online",
            "devha1_relay",
        }
        online = next(e for e in entities if e._key == "devha0_online")
        assert online._attr_translation_key == "devha_online"
        assert online._attr_translation_placeholders == {"slot": "1"}
        assert online.device_class == BinarySensorDeviceClass.CONNECTIVITY
        relay = next(e for e in entities if e._key == "devha1_relay")
        assert relay._attr_translation_placeholders == {"slot": "2"}
        assert relay.device_class is None

    @pytest.mark.asyncio
    async def test_binary_sensors_are_added_dynamically_at_runtime(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """A slot appearing on a later poll gets entities without a reload."""
        entities = await self._setup(hass, mock_coordinator)
        assert entities == []

        listener = mock_coordinator.async_add_listener.call_args[0][0]

        mock_coordinator.api.data.update({"devha0": 1, "devha0_online": 0, "devha0_relay": 0})
        listener()
        assert {e._key for e in entities} == {"devha0_online", "devha0_relay"}

        # Refresh without new slots: no duplicates.
        listener()
        assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_unpaired_accessory_binary_sensors_are_removed(
        self, hass: HomeAssistant, mock_coordinator
    ) -> None:
        """Un-pairing an accessory removes its binary sensors from the registry."""
        mock_coordinator.api.data.update({"devha0": 1, "devha0_online": 1, "devha0_relay": 0})
        entities = await self._setup(hass, mock_coordinator)
        assert {e._key for e in entities} == {"devha0_online", "devha0_relay"}
        listener = mock_coordinator.async_add_listener.call_args[0][0]

        entity_registry = er.async_get(hass)
        registered = entity_registry.async_get_or_create(
            "binary_sensor", DOMAIN, f"{DOMAIN}_{TEST_SERIAL_NUMBER}_devha0_online"
        )

        for key in list(mock_coordinator.api.data):
            if key.startswith("devha0"):
                del mock_coordinator.api.data[key]
        listener()

        assert entity_registry.async_get(registered.entity_id) is None


class TestBinarySensorEntity:
    """Tests for the binary sensor entity."""

    def _online(self, coordinator) -> Elios4YouBinarySensor:
        return Elios4YouBinarySensor(
            coordinator,
            "devha0_online",
            "mdi:access-point-network",
            BinarySensorDeviceClass.CONNECTIVITY,
            True,
            "devha_online",
            {"slot": "1"},
        )

    def test_is_on_true_and_false(self, mock_coordinator) -> None:
        """1 maps to on, 0 maps to off."""
        entity = self._online(mock_coordinator)
        mock_coordinator.api.data["devha0_online"] = 1
        assert entity.is_on is True
        mock_coordinator.api.data["devha0_online"] = 0
        assert entity.is_on is False

    def test_is_on_unknown_when_key_missing(self, mock_coordinator) -> None:
        """A missing key reads as unknown, not as off."""
        entity = self._online(mock_coordinator)
        mock_coordinator.api.data.pop("devha0_online", None)
        assert entity.is_on is None

    def test_entity_properties(self, mock_coordinator) -> None:
        """Diagnostic category, stable unique_id, no polling, device wiring."""
        mock_coordinator.api.data["devha0_online"] = 1
        entity = self._online(mock_coordinator)

        assert entity.entity_category == EntityCategory.DIAGNOSTIC
        assert entity.unique_id == f"{DOMAIN}_{TEST_SERIAL_NUMBER}_devha0_online"
        assert entity.should_poll is False
        assert entity._attr_has_entity_name is True
        assert entity.icon == "mdi:access-point-network"

        device_info = entity.device_info
        assert device_info["identifiers"] == {(DOMAIN, TEST_SERIAL_NUMBER)}
        assert device_info["manufacturer"] == "4-noks"
        assert device_info["serial_number"] == TEST_SERIAL_NUMBER

    def test_handle_coordinator_update_writes_state(self, mock_coordinator) -> None:
        """A coordinator refresh writes the entity state."""
        mock_coordinator.api.data["devha0_online"] = 1
        entity = self._online(mock_coordinator)
        entity.async_write_ha_state = MagicMock()

        entity._handle_coordinator_update()

        entity.async_write_ha_state.assert_called_once()
