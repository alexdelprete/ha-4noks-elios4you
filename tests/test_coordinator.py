"""Tests for 4-noks Elios4you coordinator module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you import coordinator as _elios4you_coordinator
from custom_components.fournoks_elios4you.api import TelnetCommandError, TelnetConnectionError
from custom_components.fournoks_elios4you.const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_MAC,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from custom_components.fournoks_elios4you.coordinator import Elios4YouCoordinator
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_SERIAL_NUMBER
from .test_config_flow import MockConfigEntry


@pytest.fixture(autouse=True)
def mock_udp_probe():
    """Keep the threshold-time UDP liveness probe off the network.

    Defaults to a silent device, which leaves the telnet-based failure
    classification unchanged.
    """
    with patch.object(
        _elios4you_coordinator, "async_probe_device", AsyncMock(return_value=None)
    ) as probe:
        yield probe


class TestCoordinatorInit:
    """Tests for coordinator initialization."""

    def test_coordinator_init_from_options(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator.conf_name == TEST_NAME
        assert coordinator.conf_host == TEST_HOST
        assert coordinator.conf_port == TEST_PORT
        assert coordinator.scan_interval == 120
        assert coordinator.update_interval == timedelta(seconds=120)

    def test_coordinator_init_from_data_fallback(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator.scan_interval == 90

    def test_coordinator_init_enforces_min_interval(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator.scan_interval == MIN_SCAN_INTERVAL

    def test_coordinator_init_default_interval(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator.scan_interval == DEFAULT_SCAN_INTERVAL

    def test_coordinator_creates_api(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        mock_api_class.assert_called_once_with(
            mock_hass,
            TEST_NAME,
            TEST_HOST,
            TEST_PORT,
        )
        assert coordinator.api == mock_api_class.return_value


class TestCoordinatorUpdate:
    """Tests for coordinator update functionality."""

    @pytest.mark.asyncio
    async def test_async_update_data_success(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(return_value=True)

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            result = await coordinator.async_update_data()

        assert result is True
        assert coordinator.last_update_status is True
        mock_api.async_get_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_update_data_failure(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

        assert coordinator.last_update_status is False

    @pytest.mark.asyncio
    async def test_async_update_data_command_error(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=TelnetCommandError("@dat"))

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_generic_exception(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=Exception("Unknown error"))

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_updates_timestamp(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(return_value=True)

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            initial_time = coordinator.last_update_time

            await coordinator.async_update_data()

        assert coordinator.last_update_time >= initial_time


class TestCoordinatorName:
    """Tests for coordinator naming."""

    def test_coordinator_name_includes_unique_id(self, mock_hass) -> None:
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

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert DOMAIN in coordinator.name
        assert TEST_SERIAL_NUMBER in coordinator.name


class TestCoordinatorFormatDowntime:
    """Tests for _format_downtime method."""

    def test_format_downtime_seconds_only(self, mock_hass) -> None:
        """Test formatting downtime less than a minute."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator._format_downtime(0) == "0s"
        assert coordinator._format_downtime(30) == "30s"
        assert coordinator._format_downtime(59) == "59s"

    def test_format_downtime_minutes_and_seconds(self, mock_hass) -> None:
        """Test formatting downtime with minutes and seconds."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator._format_downtime(60) == "1m"
        assert coordinator._format_downtime(90) == "1m 30s"
        assert coordinator._format_downtime(125) == "2m 5s"
        assert coordinator._format_downtime(3599) == "59m 59s"

    def test_format_downtime_hours(self, mock_hass) -> None:
        """Test formatting downtime with hours."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator._format_downtime(3600) == "1h"
        assert coordinator._format_downtime(3660) == "1h 1m"
        assert coordinator._format_downtime(7200) == "2h"
        assert coordinator._format_downtime(7320) == "2h 2m"


class TestCoordinatorFailureTracking:
    """Tests for failure tracking and repair issue creation."""

    @pytest.mark.asyncio
    async def test_consecutive_failures_increment(self, mock_hass) -> None:
        """Test consecutive failures counter increments on each failure."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            assert coordinator._consecutive_failures == 0

            # First failure
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()
            assert coordinator._consecutive_failures == 1

            # Second failure
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()
            assert coordinator._consecutive_failures == 2

    @pytest.mark.asyncio
    async def test_failures_reset_on_success(self, mock_hass) -> None:
        """Test consecutive failures counter resets on successful update."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = {}

            # First call fails, second succeeds
            mock_api.async_get_data = AsyncMock(
                side_effect=[TelnetConnectionError(TEST_HOST, TEST_PORT, 5), True]
            )

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            # First call - failure
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()
            assert coordinator._consecutive_failures == 1

            # Second call - success
            await coordinator.async_update_data()
            assert coordinator._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_repair_issue_created_after_threshold(self, mock_hass) -> None:
        """Test repair issue is created after failures threshold is reached."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue") as mock_create_issue,
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            # Default threshold is 3
            threshold = coordinator._failures_threshold

            # Fail up to threshold
            for _ in range(threshold):
                with pytest.raises(UpdateFailed):
                    await coordinator.async_update_data()

            # Issue should be created after reaching threshold
            assert coordinator._repair_issue_created is True
            mock_create_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_repair_issue_not_created_when_disabled(self, mock_hass) -> None:
        """Test repair issue is not created when notifications are disabled."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_ENABLE_REPAIR_NOTIFICATION: False,
                CONF_FAILURES_THRESHOLD: 1,
            },
        )

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue") as mock_create_issue,
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            # Trigger failure beyond threshold
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            # repair_issue_created flag is set (for recovery tracking)
            assert coordinator._repair_issue_created is True
            # But the actual issue is NOT created
            mock_create_issue.assert_not_called()


class TestCoordinatorDeviceEvents:
    """Tests for device event firing."""

    @pytest.mark.asyncio
    async def test_fire_device_event_without_device_id(self, mock_hass) -> None:
        """Test device event is not fired when device_id is not set."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            coordinator.device_id = None  # Not set

            coordinator._fire_device_event("device_unreachable", {"error": "test"})

            # Event should not be fired
            mock_hass.bus.async_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_fire_device_event_with_device_id(self, mock_hass) -> None:
        """Test device event is fired when device_id is set."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            coordinator.device_id = "device_123"

            coordinator._fire_device_event("device_unreachable", {"error": "Connection failed"})

            mock_hass.bus.async_fire.assert_called_once()
            call_args = mock_hass.bus.async_fire.call_args
            assert call_args[0][0] == f"{DOMAIN}_event"
            event_data = call_args[0][1]
            assert event_data["device_id"] == "device_123"
            assert event_data["type"] == "device_unreachable"
            assert event_data["device_name"] == TEST_NAME
            assert event_data["error"] == "Connection failed"


class TestCoordinatorRecoveryScript:
    """Tests for recovery script execution."""

    @pytest.mark.asyncio
    async def test_execute_recovery_script_success(self, mock_hass) -> None:
        """Test recovery script execution on success."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_RECOVERY_SCRIPT: "script.restart_wifi",
                CONF_FAILURES_THRESHOLD: 1,
            },
        )

        mock_hass.services = MagicMock()
        mock_hass.services.async_call = AsyncMock()

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            # Script should be executed
            mock_hass.services.async_call.assert_called_once()
            call_args = mock_hass.services.async_call.call_args
            assert call_args[1]["domain"] == "script"
            assert call_args[1]["service"] == "restart_wifi"
            assert coordinator._recovery_script_executed is True

    @pytest.mark.asyncio
    async def test_execute_recovery_script_not_configured(self, mock_hass) -> None:
        """Test no script execution when not configured."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_FAILURES_THRESHOLD: 1,
                # No CONF_RECOVERY_SCRIPT
            },
        )

        mock_hass.services = MagicMock()
        mock_hass.services.async_call = AsyncMock()

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            # No script call
            mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_recovery_script_error_handling(self, mock_hass) -> None:
        """Test recovery script handles errors gracefully."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_RECOVERY_SCRIPT: "script.nonexistent",
                CONF_FAILURES_THRESHOLD: 1,
            },
        )

        mock_hass.services = MagicMock()
        mock_hass.services.async_call = AsyncMock(
            side_effect=HomeAssistantError("Script not found")
        )

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            # Should not raise - error is caught internally
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            # Script was attempted but failed
            assert coordinator._recovery_script_executed is False


class TestCoordinatorRecoveryFlow:
    """Tests for the full recovery flow."""

    @pytest.mark.asyncio
    async def test_recovery_deletes_issue_and_creates_notification(self, mock_hass) -> None:
        """Test recovery flow deletes issue and creates notification."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_FAILURES_THRESHOLD: 1,
            },
        )

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue") as mock_create_issue,
            patch.object(_elios4you_coordinator, "delete_connection_issue") as mock_delete_issue,
            patch.object(
                _elios4you_coordinator, "create_recovery_notification"
            ) as mock_recovery_notification,
        ):
            mock_api = mock_api_class.return_value
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}

            # First fails, then succeeds
            mock_api.async_get_data = AsyncMock(
                side_effect=[TelnetConnectionError(TEST_HOST, TEST_PORT, 5), True]
            )

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            coordinator.device_id = "device_123"

            # First update - failure, creates issue
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._repair_issue_created is True
            mock_create_issue.assert_called_once()

            # Second update - success, triggers recovery
            await coordinator.async_update_data()

            # Issue deleted and notification created
            mock_delete_issue.assert_called_once()
            mock_recovery_notification.assert_called_once()

            # Tracking reset
            assert coordinator._repair_issue_created is False
            assert coordinator._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_recovery_fires_device_recovered_event(self, mock_hass) -> None:
        """Test recovery fires device_recovered event."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_FAILURES_THRESHOLD: 1,
            },
        )

        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
            patch.object(_elios4you_coordinator, "delete_connection_issue"),
            patch.object(_elios4you_coordinator, "create_recovery_notification"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}
            mock_api.async_get_data = AsyncMock(
                side_effect=[TelnetConnectionError(TEST_HOST, TEST_PORT, 5), True]
            )

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            coordinator.device_id = "device_123"

            # Failure
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            mock_hass.bus.async_fire.reset_mock()

            # Recovery
            await coordinator.async_update_data()

            # Check device_recovered event was fired
            calls = mock_hass.bus.async_fire.call_args_list
            recovered_events = [c for c in calls if c[0][1].get("type") == "device_recovered"]
            assert len(recovered_events) == 1
            event_data = recovered_events[0][0][1]
            assert event_data["device_id"] == "device_123"
            assert "previous_failures" in event_data
            assert "downtime_seconds" in event_data


class TestCoordinatorErrorTypes:
    """Tests for error type classification."""

    @pytest.mark.asyncio
    async def test_telnet_connection_error_type(self, mock_hass) -> None:
        """Test TelnetConnectionError is classified as device_unreachable."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._last_error_type == "device_unreachable"

    @pytest.mark.asyncio
    async def test_telnet_command_error_type(self, mock_hass) -> None:
        """Test TelnetCommandError is classified as device_not_responding."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=TelnetCommandError("@dat"))
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._last_error_type == "device_not_responding"

    @pytest.mark.asyncio
    async def test_generic_error_defaults_to_unreachable(self, mock_hass) -> None:
        """Test generic exceptions default to device_unreachable."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )

        with patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=RuntimeError("Unexpected"))
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, entry)

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._last_error_type == "device_unreachable"


class TestCoordinatorUdpLivenessProbe:
    """Tests for the UDP 5002 probe run when the failure threshold is hit."""

    def _entry(self, **options):
        return MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_FAILURES_THRESHOLD: 1,
                **options,
            },
        )

    @pytest.mark.asyncio
    async def test_probe_runs_once_per_outage(self, mock_hass, mock_udp_probe) -> None:
        """The probe fires at the threshold, not on every failed poll."""
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, self._entry())
            for _ in range(3):
                with pytest.raises(UpdateFailed):
                    await coordinator.async_update_data()

            mock_udp_probe.assert_awaited_once_with(TEST_HOST)

    @pytest.mark.asyncio
    async def test_script_runs_when_device_off_network(self, mock_hass) -> None:
        """The script is never gated: it runs and decides via failure_type itself."""
        mock_hass.services.async_call = AsyncMock()
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(
                mock_hass, self._entry(**{CONF_RECOVERY_SCRIPT: "script.restart_wifi"})
            )
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            service_data = mock_hass.services.async_call.call_args.kwargs["service_data"]
            assert service_data["failure_type"] == "device_unreachable"
            assert service_data["udp_reachable"] is False

    @pytest.mark.asyncio
    async def test_udp_answer_upgrades_unreachable(self, mock_hass, mock_udp_probe) -> None:
        """Telnet connect failure + UDP reply = alive but telnet wedged."""
        mock_udp_probe.return_value = TEST_SERIAL_NUMBER
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue") as mock_create_issue,
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, self._entry())
            coordinator.device_id = "test_device_id"

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._last_error_type == "device_not_responding"
            assert coordinator._udp_reachable is True
            assert coordinator.last_udp_probe is not None
            assert coordinator.last_udp_probe["reachable"] is True
            assert mock_create_issue.call_args.kwargs["udp_reachable"] is True
            event_data = mock_hass.bus.async_fire.call_args[0][1]
            assert event_data["type"] == "device_not_responding"
            assert event_data["udp_reachable"] is True

    @pytest.mark.asyncio
    async def test_udp_silence_keeps_unreachable(self, mock_hass) -> None:
        """Telnet connect failure + UDP silence stays device_unreachable."""
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue") as mock_create_issue,
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, self._entry())

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._last_error_type == "device_unreachable"
            assert coordinator._udp_reachable is False
            assert mock_create_issue.call_args.kwargs["udp_reachable"] is False

    @pytest.mark.asyncio
    async def test_udp_silence_never_downgrades(self, mock_hass) -> None:
        """A telnet command error stays device_not_responding even if UDP is silent.

        Silence is not proof of absence (a firewall may drop UDP), so the
        probe never overrides what the telnet error already established.
        """
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(side_effect=TelnetCommandError("@dat"))
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, self._entry())

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            assert coordinator._last_error_type == "device_not_responding"
            assert coordinator._udp_reachable is False

    @pytest.mark.asyncio
    async def test_recovery_script_receives_probe_result(self, mock_hass, mock_udp_probe) -> None:
        """The recovery script gets failure_type and udp_reachable variables."""
        mock_udp_probe.return_value = TEST_SERIAL_NUMBER
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {}
            mock_hass.services.async_call = AsyncMock()

            coordinator = Elios4YouCoordinator(
                mock_hass, self._entry(**{CONF_RECOVERY_SCRIPT: "script.restart_wifi"})
            )

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

            service_data = mock_hass.services.async_call.call_args.kwargs["service_data"]
            assert service_data["failure_type"] == "device_not_responding"
            assert service_data["udp_reachable"] is True

    @pytest.mark.asyncio
    async def test_recovery_resets_probe_result(self, mock_hass, mock_udp_probe) -> None:
        """A successful poll after an outage clears the per-outage probe result."""
        mock_udp_probe.return_value = TEST_SERIAL_NUMBER
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
            patch.object(_elios4you_coordinator, "delete_connection_issue"),
            patch.object(_elios4you_coordinator, "create_recovery_notification"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=[TelnetConnectionError(TEST_HOST, TEST_PORT, 5), True]
            )
            mock_api.data = {}

            coordinator = Elios4YouCoordinator(mock_hass, self._entry())

            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()
            assert coordinator._udp_reachable is True

            await coordinator.async_update_data()
            assert coordinator._udp_reachable is None
            # The last probe stays available for diagnostics
            assert coordinator.last_udp_probe is not None


class TestCoordinatorMacAddress:
    """The MAC comes from the config entry (DHCP discovery), not the device."""

    @pytest.mark.asyncio
    async def test_mac_from_entry_reaches_script_and_event(self, mock_hass) -> None:
        """A MAC learned by discovery is passed to the script and the event."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_MAC: "20:f8:5e:a2:75:46",
            },
            options={
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                CONF_FAILURES_THRESHOLD: 1,
                CONF_RECOVERY_SCRIPT: "script.kick",
            },
        )
        mock_hass.services.async_call = AsyncMock()
        with (
            patch.object(_elios4you_coordinator, "Elios4YouAPI") as mock_api_class,
            patch.object(_elios4you_coordinator, "create_connection_issue"),
        ):
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 5)
            )
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}

            coordinator = Elios4YouCoordinator(mock_hass, entry)
            coordinator.device_id = "test_device_id"
            with pytest.raises(UpdateFailed):
                await coordinator.async_update_data()

        service_data = mock_hass.services.async_call.call_args.kwargs["service_data"]
        assert service_data["mac_address"] == "20:f8:5e:a2:75:46"
        assert mock_hass.bus.async_fire.call_args[0][1]["mac_address"] == "20:f8:5e:a2:75:46"

    def test_mac_empty_until_learned(self, mock_hass) -> None:
        """Without a DHCP sighting the MAC is an empty string, never a guess."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_NAME: TEST_NAME, CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT},
            options={CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL},
        )
        with patch.object(_elios4you_coordinator, "Elios4YouAPI"):
            coordinator = Elios4YouCoordinator(mock_hass, entry)

        assert coordinator.conf_mac == ""
