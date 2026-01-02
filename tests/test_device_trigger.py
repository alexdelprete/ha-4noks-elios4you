"""Tests for 4-noks Elios4you device trigger module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.const import DOMAIN
from custom_components.fournoks_elios4you.device_trigger import (
    TRIGGER_SCHEMA,
    TRIGGER_TYPES,
    async_attach_trigger,
    async_get_triggers,
)
import pytest

from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import HomeAssistant


class TestTriggerConstants:
    """Tests for device trigger constants."""

    def test_trigger_types_defined(self) -> None:
        """Test that all expected trigger types are defined."""
        assert "device_unreachable" in TRIGGER_TYPES
        assert "device_not_responding" in TRIGGER_TYPES
        assert "device_recovered" in TRIGGER_TYPES
        assert len(TRIGGER_TYPES) == 3

    def test_trigger_schema_requires_type(self) -> None:
        """Test that trigger schema requires type field."""
        # Valid config
        valid_config = {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: "test_device_id",
            CONF_TYPE: "device_unreachable",
        }
        # Should not raise
        TRIGGER_SCHEMA(valid_config)

    def test_trigger_schema_rejects_invalid_type(self) -> None:
        """Test that trigger schema rejects invalid type."""
        import voluptuous as vol

        invalid_config = {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: "test_device_id",
            CONF_TYPE: "invalid_type",
        }
        with pytest.raises(vol.Invalid):
            TRIGGER_SCHEMA(invalid_config)


class TestAsyncGetTriggers:
    """Tests for async_get_triggers function."""

    @pytest.mark.asyncio
    async def test_get_triggers_returns_all_types(self, hass: HomeAssistant) -> None:
        """Test that get_triggers returns all trigger types for valid device."""
        device_id = "test_device_123"

        # Create mock device with our domain identifier
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "serial_123")}

        with patch(
            "custom_components.fournoks_elios4you.device_trigger.dr.async_get"
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = mock_device

            triggers = await async_get_triggers(hass, device_id)

        assert len(triggers) == 3
        trigger_types = {t[CONF_TYPE] for t in triggers}
        assert trigger_types == TRIGGER_TYPES

        # Check trigger structure
        for trigger in triggers:
            assert trigger[CONF_PLATFORM] == "device"
            assert trigger[CONF_DOMAIN] == DOMAIN
            assert trigger[CONF_DEVICE_ID] == device_id
            assert trigger[CONF_TYPE] in TRIGGER_TYPES

    @pytest.mark.asyncio
    async def test_get_triggers_returns_empty_for_unknown_device(self, hass: HomeAssistant) -> None:
        """Test that get_triggers returns empty list for unknown device."""
        device_id = "unknown_device"

        with patch(
            "custom_components.fournoks_elios4you.device_trigger.dr.async_get"
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = None

            triggers = await async_get_triggers(hass, device_id)

        assert triggers == []

    @pytest.mark.asyncio
    async def test_get_triggers_returns_empty_for_other_domain(self, hass: HomeAssistant) -> None:
        """Test that get_triggers returns empty for device from another domain."""
        device_id = "other_domain_device"

        # Create mock device with different domain identifier
        mock_device = MagicMock()
        mock_device.identifiers = {("other_domain", "serial_456")}

        with patch(
            "custom_components.fournoks_elios4you.device_trigger.dr.async_get"
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = mock_device

            triggers = await async_get_triggers(hass, device_id)

        assert triggers == []

    @pytest.mark.asyncio
    async def test_get_triggers_handles_multiple_identifiers(self, hass: HomeAssistant) -> None:
        """Test get_triggers works with device having multiple identifiers."""
        device_id = "multi_id_device"

        # Device with multiple identifiers including our domain
        mock_device = MagicMock()
        mock_device.identifiers = {
            ("other_domain", "id1"),
            (DOMAIN, "serial_789"),
            ("another_domain", "id2"),
        }

        with patch(
            "custom_components.fournoks_elios4you.device_trigger.dr.async_get"
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = mock_device

            triggers = await async_get_triggers(hass, device_id)

        # Should still return triggers since one identifier matches our domain
        assert len(triggers) == 3


class TestAsyncAttachTrigger:
    """Tests for async_attach_trigger function."""

    @pytest.mark.asyncio
    async def test_attach_trigger_creates_event_trigger(self, hass: HomeAssistant) -> None:
        """Test that attach_trigger creates proper event trigger."""
        config = {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: "device_123",
            CONF_TYPE: "device_unreachable",
        }
        action = MagicMock()
        trigger_info = MagicMock()

        with patch.object(
            event_trigger, "async_attach_trigger", new_callable=AsyncMock
        ) as mock_attach:
            mock_attach.return_value = MagicMock()

            result = await async_attach_trigger(hass, config, action, trigger_info)

            mock_attach.assert_called_once()
            call_args = mock_attach.call_args

            # Check event config
            event_config = call_args[0][1]
            assert event_config[event_trigger.CONF_EVENT_TYPE] == f"{DOMAIN}_event"
            assert event_config[event_trigger.CONF_EVENT_DATA][CONF_DEVICE_ID] == "device_123"
            assert event_config[event_trigger.CONF_EVENT_DATA][CONF_TYPE] == "device_unreachable"

            # Check other args
            assert call_args[0][2] == action
            assert call_args[0][3] == trigger_info
            assert call_args[1]["platform_type"] == "device"

            assert result is not None

    @pytest.mark.asyncio
    async def test_attach_trigger_for_each_type(self, hass: HomeAssistant) -> None:
        """Test attaching triggers for each trigger type."""
        for trigger_type in TRIGGER_TYPES:
            config = {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: "device_456",
                CONF_TYPE: trigger_type,
            }
            action = MagicMock()
            trigger_info = MagicMock()

            with patch.object(
                event_trigger, "async_attach_trigger", new_callable=AsyncMock
            ) as mock_attach:
                mock_attach.return_value = MagicMock()

                await async_attach_trigger(hass, config, action, trigger_info)

                event_config = mock_attach.call_args[0][1]
                assert event_config[event_trigger.CONF_EVENT_DATA][CONF_TYPE] == trigger_type

    @pytest.mark.asyncio
    async def test_attach_trigger_returns_unsubscribe(self, hass: HomeAssistant) -> None:
        """Test that attach_trigger returns unsubscribe callback."""
        config = {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: "device_789",
            CONF_TYPE: "device_recovered",
        }
        action = MagicMock()
        trigger_info = MagicMock()

        mock_unsubscribe = MagicMock()

        with patch.object(
            event_trigger, "async_attach_trigger", new_callable=AsyncMock
        ) as mock_attach:
            mock_attach.return_value = mock_unsubscribe

            result = await async_attach_trigger(hass, config, action, trigger_info)

            assert result == mock_unsubscribe
