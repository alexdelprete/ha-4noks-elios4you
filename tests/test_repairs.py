"""Tests for 4-noks Elios4you repairs module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from unittest.mock import patch

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.const import DOMAIN
from custom_components.fournoks_elios4you.repairs import (
    ISSUE_CONNECTION_FAILED,
    ISSUE_RECOVERY_SUCCESS,
    ISSUE_RECOVERY_SUCCESS_NO_SCRIPT,
    async_create_fix_flow,
    create_connection_issue,
    create_recovery_notification,
    delete_connection_issue,
)
import pytest

from homeassistant.components.repairs import ConfirmRepairFlow
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

    def test_issue_recovery_success_value(self) -> None:
        """Test ISSUE_RECOVERY_SUCCESS constant value."""
        assert ISSUE_RECOVERY_SUCCESS == "recovery_success"

    def test_issue_recovery_success_no_script_value(self) -> None:
        """Test ISSUE_RECOVERY_SUCCESS_NO_SCRIPT constant value."""
        assert ISSUE_RECOVERY_SUCCESS_NO_SCRIPT == "recovery_success_no_script"

    def test_issue_id_format(self) -> None:
        """Test issue ID format is correct."""
        entry_id = "test_123"
        expected = f"{ISSUE_CONNECTION_FAILED}_{entry_id}"
        assert expected == "connection_failed_test_123"


class TestAsyncCreateFixFlow:
    """Tests for async_create_fix_flow function."""

    @pytest.mark.asyncio
    async def test_create_fix_flow_recovery_success(self, hass: HomeAssistant) -> None:
        """Test fix flow returns ConfirmRepairFlow for recovery_success."""
        issue_id = f"{ISSUE_RECOVERY_SUCCESS}_entry_123"
        data = None

        flow = await async_create_fix_flow(hass, issue_id, data)

        assert isinstance(flow, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_recovery_success_no_script(self, hass: HomeAssistant) -> None:
        """Test fix flow returns ConfirmRepairFlow for recovery_success_no_script."""
        issue_id = f"{ISSUE_RECOVERY_SUCCESS_NO_SCRIPT}_entry_456"
        data = None

        flow = await async_create_fix_flow(hass, issue_id, data)

        assert isinstance(flow, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_other_issue(self, hass: HomeAssistant) -> None:
        """Test fix flow returns ConfirmRepairFlow for other issues."""
        issue_id = "some_other_issue_789"
        data = None

        flow = await async_create_fix_flow(hass, issue_id, data)

        # Falls back to ConfirmRepairFlow
        assert isinstance(flow, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_with_data(self, hass: HomeAssistant) -> None:
        """Test fix flow works when data is provided."""
        issue_id = f"{ISSUE_RECOVERY_SUCCESS}_entry_abc"
        data = {"device_name": "Test Device", "downtime": "5m 23s"}

        flow = await async_create_fix_flow(hass, issue_id, data)

        assert isinstance(flow, ConfirmRepairFlow)


class TestCreateRecoveryNotification:
    """Tests for create_recovery_notification function."""

    def test_create_recovery_notification_with_script(self, hass: HomeAssistant) -> None:
        """Test creating recovery notification with script info."""
        entry_id = "test_entry_recovery"

        with patch.object(ir, "async_create_issue") as mock_create:
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

            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Check domain and issue ID
            assert call_args[0][0] == hass
            assert call_args[0][1] == DOMAIN
            expected_issue_id = f"{ISSUE_RECOVERY_SUCCESS}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

            # Check keyword arguments
            kwargs = call_args[1]
            assert kwargs["is_fixable"] is True
            assert kwargs["is_persistent"] is True
            assert kwargs["severity"] == ir.IssueSeverity.WARNING
            assert kwargs["translation_key"] == ISSUE_RECOVERY_SUCCESS

            # Check placeholders include script info
            placeholders = kwargs["translation_placeholders"]
            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["started_at"] == "10:30:00"
            assert placeholders["ended_at"] == "10:35:23"
            assert placeholders["downtime"] == "5m 23s"
            assert placeholders["script_name"] == "script.restart_wifi"
            assert placeholders["script_executed_at"] == "10:31:00"

    def test_create_recovery_notification_without_script(self, hass: HomeAssistant) -> None:
        """Test creating recovery notification without script info."""
        entry_id = "test_entry_no_script"

        with patch.object(ir, "async_create_issue") as mock_create:
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

            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Check issue ID uses no_script variant
            expected_issue_id = f"{ISSUE_RECOVERY_SUCCESS_NO_SCRIPT}_{entry_id}"
            assert call_args[0][2] == expected_issue_id

            kwargs = call_args[1]
            assert kwargs["translation_key"] == ISSUE_RECOVERY_SUCCESS_NO_SCRIPT

            # Check placeholders don't include script info
            placeholders = kwargs["translation_placeholders"]
            assert placeholders["device_name"] == TEST_NAME
            assert placeholders["started_at"] == "14:00:00"
            assert placeholders["ended_at"] == "14:02:30"
            assert placeholders["downtime"] == "2m 30s"
            assert "script_name" not in placeholders
            assert "script_executed_at" not in placeholders

    def test_create_recovery_notification_unique_per_entry(self, hass: HomeAssistant) -> None:
        """Test each entry gets unique recovery notification ID."""
        entry_id_1 = "entry_aaa"
        entry_id_2 = "entry_bbb"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_recovery_notification(hass, entry_id_1, TEST_NAME, "10:00:00", "10:05:00", "5m")
            create_recovery_notification(hass, entry_id_2, TEST_NAME, "11:00:00", "11:03:00", "3m")

            # Should have 2 different issue IDs
            issue_id_1 = mock_create.call_args_list[0][0][2]
            issue_id_2 = mock_create.call_args_list[1][0][2]

            assert issue_id_1 != issue_id_2
            assert entry_id_1 in issue_id_1
            assert entry_id_2 in issue_id_2

    def test_create_recovery_notification_is_fixable(self, hass: HomeAssistant) -> None:
        """Test recovery notification is fixable (user can dismiss)."""
        entry_id = "fixable_entry"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_recovery_notification(hass, entry_id, TEST_NAME, "09:00:00", "09:01:00", "1m")

            kwargs = mock_create.call_args[1]
            assert kwargs["is_fixable"] is True

    def test_create_recovery_notification_is_persistent(self, hass: HomeAssistant) -> None:
        """Test recovery notification survives HA restart."""
        entry_id = "persistent_entry"

        with patch.object(ir, "async_create_issue") as mock_create:
            create_recovery_notification(hass, entry_id, TEST_NAME, "08:00:00", "08:10:00", "10m")

            kwargs = mock_create.call_args[1]
            assert kwargs["is_persistent"] is True
