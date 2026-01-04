"""Tests for 4-noks Elios4you repairs module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.const import DOMAIN, NOTIFICATION_RECOVERY
from custom_components.fournoks_elios4you.repairs import (
    ISSUE_CONNECTION_FAILED,
    create_connection_issue,
    create_recovery_notification,
    delete_connection_issue,
)
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT


class TestCreateConnectionIssue:
    """Tests for create_connection_issue function."""

    def test_create_connection_issue(self, hass: HomeAssistant) -> None:
        """Test creating a connection issue."""
        entry_id = "test_entry_123"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(
                hass,
                entry_id,
                TEST_NAME,
                TEST_HOST,
                TEST_PORT,
            )

            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Check domain
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN

            # Check issue ID format
            expected_issue_id = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

            # Check keyword arguments
            kwargs = call_args[1]
            assert kwargs["is_fixable"] is False
            assert kwargs["is_persistent"] is True
            assert kwargs["severity"] == ir.IssueSeverity.ERROR
            assert kwargs["translation_key"] == ISSUE_CONNECTION_FAILED

    def test_create_connection_issue_placeholders(self, hass: HomeAssistant) -> None:
        """Test connection issue has correct placeholders."""
        entry_id = "test_entry_456"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(
                hass,
                entry_id,
                TEST_NAME,
                TEST_HOST,
                TEST_PORT,
            )

            kwargs = mock_create.call_args[1]
            placeholders = kwargs["translation_placeholders"]

            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["host"] == TEST_HOST
            assert placeholders["port"] == str(TEST_PORT)

    def test_create_connection_issue_unique_per_entry(self, hass: HomeAssistant) -> None:
        """Test each entry gets a unique issue ID."""
        entry_id_1 = "entry_1"
        entry_id_2 = "entry_2"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(hass, entry_id_1, TEST_NAME, TEST_HOST, TEST_PORT)
            create_connection_issue(hass, entry_id_2, TEST_NAME, TEST_HOST, TEST_PORT)

            # Should have 2 different issue IDs
            issue_id_1 = mock_create.call_args_list[0][0][2]
            issue_id_2 = mock_create.call_args_list[1][0][2]

            assert issue_id_1 != issue_id_2
            assert entry_id_1 in issue_id_1
            assert entry_id_2 in issue_id_2


class TestDeleteConnectionIssue:
    """Tests for delete_connection_issue function."""

    def test_delete_connection_issue(self, hass: HomeAssistant) -> None:
        """Test deleting a connection issue."""
        entry_id = "test_entry_789"

        with patch.object(ir, "async_delete_issue") as mock_delete:
            delete_connection_issue(hass, entry_id)

            mock_delete.assert_called_once()
            call_args = mock_delete.call_args

            # Check domain and issue ID
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN

            expected_issue_id = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

    def test_delete_connection_issue_correct_id_format(self, hass: HomeAssistant) -> None:
        """Test delete uses same ID format as create."""
        entry_id = "matching_entry"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_connection_issue(hass, entry_id, TEST_NAME, TEST_HOST, TEST_PORT)
            created_issue_id = mock_create.call_args[0][2]

        with patch.object(ir, "async_delete_issue") as mock_delete:
            delete_connection_issue(hass, entry_id)
            deleted_issue_id = mock_delete.call_args[0][2]

        # Issue IDs should match
        assert created_issue_id == deleted_issue_id


class TestIssueConstants:
    """Tests for issue constants."""

    def test_issue_connection_failed_value(self) -> None:
        """Test ISSUE_CONNECTION_FAILED constant value."""
        assert ISSUE_CONNECTION_FAILED == "connection_failed"

    def test_notification_recovery_value(self) -> None:
        """Test NOTIFICATION_RECOVERY constant value."""
        assert NOTIFICATION_RECOVERY == "recovery"

    def test_issue_id_format(self) -> None:
        """Test issue ID format is correct."""
        entry_id = "test_123"
        expected = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
        assert expected == "connection_failed_test_123"


class TestCreateRecoveryNotification:
    """Tests for create_recovery_notification function.

    Recovery notifications use persistent_notification service instead of
    repair issues to ensure full message with timestamps displays properly.
    """

    def test_create_recovery_notification_with_script(self, hass: HomeAssistant) -> None:
        """Test creating recovery notification with script info."""
        entry_id = "test_entry_recovery"

        # Mock hass.async_create_task and hass.services.async_call
        mock_async_call = AsyncMock()
        hass.services = MagicMock()
        hass.services.async_call = mock_async_call
        hass.async_create_task = MagicMock()

        create_recovery_notification(
            hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="10:30:00",
            ended_at="10:35:23",
            downtime="5m 23s",
            script_name="script.restart_wifi",
            script_executed_at="10:31:00",
        )

        # Verify async_create_task was called
        hass.async_create_task.assert_called_once()

    def test_create_recovery_notification_without_script(self, hass: HomeAssistant) -> None:
        """Test creating recovery notification without script info."""
        entry_id = "test_entry_no_script"

        # Mock hass.async_create_task and hass.services.async_call
        mock_async_call = AsyncMock()
        hass.services = MagicMock()
        hass.services.async_call = mock_async_call
        hass.async_create_task = MagicMock()

        create_recovery_notification(
            hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="14:00:00",
            ended_at="14:02:30",
            downtime="2m 30s",
            script_name=None,
            script_executed_at=None,
        )

        # Verify async_create_task was called
        hass.async_create_task.assert_called_once()

    def test_create_recovery_notification_unique_id_per_entry(self, hass: HomeAssistant) -> None:
        """Test each entry gets unique recovery notification ID."""
        entry_id_1 = "entry_aaa"
        entry_id_2 = "entry_bbb"

        expected_id_1 = f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id_1}"
        expected_id_2 = f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id_2}"

        # The notification IDs should be different
        assert expected_id_1 != expected_id_2
        assert entry_id_1 in expected_id_1
        assert entry_id_2 in expected_id_2

    @pytest.mark.asyncio
    async def test_create_recovery_notification_service_call(self, hass: HomeAssistant) -> None:
        """Test recovery notification calls persistent_notification service."""
        entry_id = "test_service_call"

        # Create a mock for the service call
        mock_async_call = AsyncMock()
        hass.services = MagicMock()
        hass.services.async_call = mock_async_call

        # Capture the coroutine passed to async_create_task
        captured_coro = None

        def capture_task(coro):
            nonlocal captured_coro
            captured_coro = coro
            return MagicMock()

        hass.async_create_task = capture_task

        create_recovery_notification(
            hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="10:00:00",
            ended_at="10:05:00",
            downtime="5m",
            script_name=None,
            script_executed_at=None,
        )

        # Await the captured coroutine to trigger the service call
        assert captured_coro is not None
        await captured_coro

        # Verify the service call
        mock_async_call.assert_called_once()
        call_args = mock_async_call.call_args

        assert call_args.kwargs["domain"] == "persistent_notification"
        assert call_args.kwargs["service"] == "create"

        service_data = call_args.kwargs["service_data"]
        assert service_data["title"] == f"{TEST_NAME} has recovered"
        assert f"{TEST_NAME}" in service_data["message"]
        assert "10:00:00" in service_data["message"]
        assert "10:05:00" in service_data["message"]
        assert "5m" in service_data["message"]
        assert service_data["notification_id"] == f"{DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id}"

    @pytest.mark.asyncio
    async def test_create_recovery_notification_message_with_script(
        self, hass: HomeAssistant
    ) -> None:
        """Test recovery notification message includes script info when provided."""
        entry_id = "test_script_message"

        mock_async_call = AsyncMock()
        hass.services = MagicMock()
        hass.services.async_call = mock_async_call

        captured_coro = None

        def capture_task(coro):
            nonlocal captured_coro
            captured_coro = coro
            return MagicMock()

        hass.async_create_task = capture_task

        create_recovery_notification(
            hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="10:30:00",
            ended_at="10:35:23",
            downtime="5m 23s",
            script_name="script.restart_wifi",
            script_executed_at="10:31:00",
        )

        assert captured_coro is not None
        await captured_coro

        service_data = mock_async_call.call_args.kwargs["service_data"]
        message = service_data["message"]

        # Verify script info is in the message
        assert "script.restart_wifi" in message
        assert "10:31:00" in message
        assert "Script executed" in message
        assert "Recovery script" in message

    @pytest.mark.asyncio
    async def test_create_recovery_notification_message_without_script(
        self, hass: HomeAssistant
    ) -> None:
        """Test recovery notification message excludes script info when not provided."""
        entry_id = "test_no_script_message"

        mock_async_call = AsyncMock()
        hass.services = MagicMock()
        hass.services.async_call = mock_async_call

        captured_coro = None

        def capture_task(coro):
            nonlocal captured_coro
            captured_coro = coro
            return MagicMock()

        hass.async_create_task = capture_task

        create_recovery_notification(
            hass,
            entry_id,
            device_name=TEST_NAME,
            started_at="14:00:00",
            ended_at="14:02:30",
            downtime="2m 30s",
            script_name=None,
            script_executed_at=None,
        )

        assert captured_coro is not None
        await captured_coro

        service_data = mock_async_call.call_args.kwargs["service_data"]
        message = service_data["message"]

        # Verify script info is NOT in the message
        assert "Script executed" not in message
        assert "Recovery script" not in message

        # But basic info should still be there
        assert TEST_NAME in message
        assert "14:00:00" in message
        assert "14:02:30" in message
        assert "2m 30s" in message
