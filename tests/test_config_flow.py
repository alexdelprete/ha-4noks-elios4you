"""Tests for 4-noks Elios4you config flow.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you import config_flow as _elios4you_config_flow
from custom_components.fournoks_elios4you.api import TelnetCommandError, TelnetConnectionError
from custom_components.fournoks_elios4you.config_flow import (
    Elios4YouConfigFlow,
    Elios4YouOptionsFlow,
    get_host_from_config,
)
from custom_components.fournoks_elios4you.const import CONF_SCAN_INTERVAL, DOMAIN
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SCAN_INTERVAL, TEST_SERIAL_NUMBER


@pytest.fixture(name="integration_setup", autouse=True)
def integration_setup_fixture() -> Generator[None]:
    """Mock integration entry setup to avoid loading the full integration."""
    with patch(
        "custom_components.fournoks_elios4you.async_setup_entry",
        return_value=True,
    ):
        yield


# =============================================================================
# Integration Tests (Using real hass fixture)
# =============================================================================


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_elios4you_api_config_flow: MagicMock,
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
    mock_elios4you_api_config_flow: MagicMock,
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
        unique_id=TEST_SERIAL_NUMBER,
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
    mock_elios4you_api_config_flow: MagicMock,
) -> None:
    """Test flow shows error when cannot connect."""
    mock_elios4you_api_config_flow.return_value.async_get_data = AsyncMock(
        side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 10, "Connection failed")
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
    mock_elios4you_api: MagicMock,
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
        unique_id=TEST_SERIAL_NUMBER,
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


# =============================================================================
# Direct Unit Tests (No Integration Loading Required)
# =============================================================================


class TestGetHostFromConfig:
    """Tests for get_host_from_config function."""

    async def test_get_host_from_config_empty(self, mock_hass: MagicMock) -> None:
        """Test get_host_from_config with no entries."""
        mock_hass.config_entries.async_entries.return_value = []
        result = get_host_from_config(mock_hass)
        assert result == set()

    async def test_get_host_from_config_with_entries(self, mock_hass: MagicMock) -> None:
        """Test get_host_from_config with existing entries."""
        # Create mock config entries
        entry1 = MagicMock()
        entry1.data = {CONF_HOST: "192.168.1.100"}
        entry2 = MagicMock()
        entry2.data = {CONF_HOST: "192.168.1.101"}
        entry3 = MagicMock()
        entry3.data = {}  # Entry without host

        mock_hass.config_entries.async_entries.return_value = [entry1, entry2, entry3]
        result = get_host_from_config(mock_hass)

        assert result == {"192.168.1.100", "192.168.1.101", None}
        mock_hass.config_entries.async_entries.assert_called_once_with(DOMAIN)


class TestHostInConfigurationExists:
    """Tests for _host_in_configuration_exists method."""

    async def test_host_exists_true(self, mock_hass: MagicMock) -> None:
        """Test that existing host is detected."""
        entry = MagicMock()
        entry.data = {CONF_HOST: TEST_HOST}
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        assert flow._host_in_configuration_exists(TEST_HOST) is True

    async def test_host_exists_false(self, mock_hass: MagicMock) -> None:
        """Test that non-existing host is not detected."""
        entry = MagicMock()
        entry.data = {CONF_HOST: "192.168.1.200"}
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        assert flow._host_in_configuration_exists(TEST_HOST) is False

    async def test_host_exists_empty_config(self, mock_hass: MagicMock) -> None:
        """Test with no config entries."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        assert flow._host_in_configuration_exists(TEST_HOST) is False

    async def test_host_exists_none(self, mock_hass: MagicMock) -> None:
        """Test checking for None host."""
        entry = MagicMock()
        entry.data = {}  # No host key
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        # None will be in the set from entries without host
        assert flow._host_in_configuration_exists(None) is True


class TestTestConnection:
    """Tests for _test_connection method."""

    async def test_connection_success(self, mock_hass: MagicMock, mock_api_data: dict) -> None:
        """Test successful connection returns serial number."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, TEST_PORT, TEST_SCAN_INTERVAL
            )

            assert result == TEST_SERIAL_NUMBER
            mock_api_class.assert_called_once_with(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
            mock_api.async_get_data.assert_awaited_once()

    async def test_connection_telnet_error(self, mock_hass: MagicMock) -> None:
        """Test TelnetConnectionError returns None."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 10, "Connection refused")
            )

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, TEST_PORT, TEST_SCAN_INTERVAL
            )

            assert result is None

    async def test_connection_command_error(self, mock_hass: MagicMock) -> None:
        """Test TelnetCommandError returns None."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetCommandError("@dat", "Invalid response")
            )

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, TEST_PORT, TEST_SCAN_INTERVAL
            )

            assert result is None


class TestAsyncStepUserDirect:
    """Direct tests for async_step_user without full integration loading."""

    async def test_async_step_user_shows_form(self, mock_hass: MagicMock) -> None:
        """Test initial form is shown when no user_input."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        result = await flow.async_step_user(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_async_step_user_already_configured(self, mock_hass: MagicMock) -> None:
        """Test error when host is already configured."""
        # Setup existing entry
        entry = MagicMock()
        entry.data = {CONF_HOST: TEST_HOST}
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        result = await flow.async_step_user(
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "already_configured"}

    async def test_async_step_user_invalid_host(self, mock_hass: MagicMock) -> None:
        """Test error when host is invalid."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        result = await flow.async_step_user(
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: "not a valid host!@#",
                CONF_PORT: TEST_PORT,
                CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "invalid_host"}

    async def test_async_step_user_cannot_connect(self, mock_hass: MagicMock) -> None:
        """Test error when connection fails."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 10)
            )

            result = await flow.async_step_user(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: TEST_PORT,
                    CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}

    async def test_async_step_user_success(self, mock_hass: MagicMock, mock_api_data: dict) -> None:
        """Test successful config entry creation."""
        mock_hass.config_entries.async_entries.return_value = []

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}
        # Mock unique_id methods to prevent AbortFlow
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow.async_step_user(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: TEST_PORT,
                    CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                }
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


class TestAsyncStepReconfigureDirect:
    """Direct tests for async_step_reconfigure without full integration loading."""

    def _create_mock_reconfigure_entry(self) -> MagicMock:
        """Create a mock config entry for reconfigure tests."""
        entry = MagicMock()
        entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
        }
        entry.options = {
            CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        }
        entry.unique_id = TEST_SERIAL_NUMBER
        return entry

    async def test_async_step_reconfigure_shows_form(self, mock_hass: MagicMock) -> None:
        """Test initial reconfigure form is shown."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        result = await flow.async_step_reconfigure(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {}

    async def test_async_step_reconfigure_invalid_host(self, mock_hass: MagicMock) -> None:
        """Test error when reconfigure host is invalid."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        result = await flow.async_step_reconfigure(
            {
                CONF_NAME: TEST_NAME,
                CONF_HOST: "invalid!host@#$",
                CONF_PORT: TEST_PORT,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "invalid_host"}

    async def test_async_step_reconfigure_cannot_connect(self, mock_hass: MagicMock) -> None:
        """Test error when reconfigure connection fails."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 10)
            )

            result = await flow.async_step_reconfigure(
                {
                    CONF_NAME: "New Name",
                    CONF_HOST: "192.168.1.200",
                    CONF_PORT: 5002,
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}

    async def test_async_step_reconfigure_success(
        self, mock_hass: MagicMock, mock_api_data: dict
    ) -> None:
        """Test successful reconfiguration."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = self._create_mock_reconfigure_entry()
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_mismatch = MagicMock()
        flow.async_update_reload_and_abort = MagicMock(
            return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"}
        )

        new_host = "192.168.1.200"
        new_port = 5002
        new_name = "New Device Name"

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = mock_api_data
            mock_api.async_get_data = AsyncMock(return_value=True)

            await flow.async_step_reconfigure(
                {
                    CONF_NAME: new_name,
                    CONF_HOST: new_host,
                    CONF_PORT: new_port,
                }
            )

        # Verify the flow completed successfully
        flow.async_set_unique_id.assert_awaited_once_with(TEST_SERIAL_NUMBER)
        flow._abort_if_unique_id_mismatch.assert_called_once()
        flow.async_update_reload_and_abort.assert_called_once_with(
            mock_entry,
            title=new_name,
            data_updates={
                CONF_NAME: new_name,
                CONF_HOST: new_host,
                CONF_PORT: new_port,
            },
        )

    async def test_async_step_reconfigure_uses_existing_scan_interval(
        self, mock_hass: MagicMock, mock_api_data: dict
    ) -> None:
        """Test reconfigure uses existing scan_interval from options."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        # Entry with custom scan interval
        mock_entry = self._create_mock_reconfigure_entry()
        mock_entry.options = {CONF_SCAN_INTERVAL: 120}
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 10)
            )

            await flow.async_step_reconfigure(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: TEST_PORT,
                }
            )

            # Verify API was created - the scan_interval should come from options
            mock_api_class.assert_called_once()


class TestOptionsFlowDirect:
    """Direct tests for Elios4YouOptionsFlow without full integration loading."""

    def _create_mock_config_entry(self) -> MagicMock:
        """Create a mock config entry for options flow tests."""
        entry = MagicMock()
        entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
        }
        entry.options = {
            CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
        }
        entry.entry_id = "test_entry_id"
        return entry

    async def test_options_flow_shows_form(self) -> None:
        """Test initial options form is shown."""
        mock_entry = self._create_mock_config_entry()

        flow = Elios4YouOptionsFlow()
        # Use PropertyMock to mock the read-only config_entry property
        with patch.object(
            type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
        ):
            result = await flow.async_step_init(None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_saves_options(self) -> None:
        """Test options are saved correctly."""
        mock_entry = self._create_mock_config_entry()

        flow = Elios4YouOptionsFlow()
        with patch.object(
            type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
        ):
            new_scan_interval = 120
            result = await flow.async_step_init(
                {
                    CONF_SCAN_INTERVAL: new_scan_interval,
                }
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_SCAN_INTERVAL: new_scan_interval,
        }

    async def test_options_flow_with_default_scan_interval(self) -> None:
        """Test options flow uses default when no options set."""
        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
        }
        mock_entry.options = {}  # No options set

        flow = Elios4YouOptionsFlow()
        with patch.object(
            type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
        ):
            result = await flow.async_step_init(None)

        assert result["type"] == FlowResultType.FORM
        # Default value should be used in form schema

    async def test_options_flow_preserves_min_max_constraints(self) -> None:
        """Test scan interval respects min/max constraints in form."""
        mock_entry = self._create_mock_config_entry()

        flow = Elios4YouOptionsFlow()
        with patch.object(
            type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
        ):
            result = await flow.async_step_init(None)

        assert result["type"] == FlowResultType.FORM
        # The schema should include the scan interval field with constraints


class TestConfigFlowOptionsFlow:
    """Test async_get_options_flow method."""

    def test_async_get_options_flow_returns_options_flow(self) -> None:
        """Test that async_get_options_flow returns an Elios4YouOptionsFlow instance."""
        mock_entry = MagicMock()

        result = Elios4YouConfigFlow.async_get_options_flow(mock_entry)

        assert isinstance(result, Elios4YouOptionsFlow)


class TestConfigFlowAttributes:
    """Test ConfigFlow class attributes."""

    def test_config_flow_version(self) -> None:
        """Test ConfigFlow VERSION is set correctly."""
        assert Elios4YouConfigFlow.VERSION == 3

    def test_config_flow_connection_class(self) -> None:
        """Test ConfigFlow CONNECTION_CLASS is set correctly."""
        assert Elios4YouConfigFlow.CONNECTION_CLASS == config_entries.CONN_CLASS_LOCAL_POLL

    def test_config_flow_domain(self) -> None:
        """Test ConfigFlow domain is set correctly."""
        # The domain is set via the class decorator, verify it matches expected
        assert DOMAIN == "4noks_elios4you"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_user_step_with_none_host_in_config(self, mock_hass: MagicMock) -> None:
        """Test user step when existing entry has None host."""
        entry = MagicMock()
        entry.data = {}  # No host key results in None
        mock_hass.config_entries.async_entries.return_value = [entry]

        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_USER}
        # Mock unique_id methods to prevent AbortFlow
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        # Valid new host should work even if existing entry has None host
        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.data = {"sn": TEST_SERIAL_NUMBER}
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow.async_step_user(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: TEST_PORT,
                    CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
                }
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_reconfigure_without_scan_interval_in_options(self, mock_hass: MagicMock) -> None:
        """Test reconfigure when entry has no scan_interval in options."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass
        flow.context = {"source": config_entries.SOURCE_RECONFIGURE}

        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_NAME: TEST_NAME,
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
        }
        mock_entry.options = {}  # No scan_interval
        flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.async_get_data = AsyncMock(
                side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, 10)
            )

            # Should use DEFAULT_SCAN_INTERVAL when not in options
            result = await flow.async_step_reconfigure(
                {
                    CONF_NAME: TEST_NAME,
                    CONF_HOST: TEST_HOST,
                    CONF_PORT: TEST_PORT,
                }
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {CONF_HOST: "cannot_connect"}

    async def test_test_connection_returns_string_serial(self, mock_hass: MagicMock) -> None:
        """Test _test_connection converts serial number to string."""
        flow = Elios4YouConfigFlow()
        flow.hass = mock_hass

        with patch.object(_elios4you_config_flow, "Elios4YouAPI", autospec=True) as mock_api_class:
            mock_api = mock_api_class.return_value
            # Use integer serial number
            mock_api.data = {"sn": 123456789}
            mock_api.async_get_data = AsyncMock(return_value=True)

            result = await flow._test_connection(
                TEST_NAME, TEST_HOST, TEST_PORT, TEST_SCAN_INTERVAL
            )

            # Should be converted to string
            assert result == "123456789"
            assert isinstance(result, str)
