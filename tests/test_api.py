"""Tests for 4-noks Elios4you API module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import importlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import modules with numeric prefix using importlib
_elios4you_api = importlib.import_module("custom_components.4noks_elios4you.api")
_elios4you_const = importlib.import_module("custom_components.4noks_elios4you.const")

Elios4YouAPI = _elios4you_api.Elios4YouAPI
TelnetConnectionError = _elios4you_api.TelnetConnectionError
TelnetCommandError = _elios4you_api.TelnetCommandError

CONN_TIMEOUT = _elios4you_const.CONN_TIMEOUT
MANUFACTURER = _elios4you_const.MANUFACTURER
MODEL = _elios4you_const.MODEL

from .conftest import TEST_HOST, TEST_NAME, TEST_PORT, TEST_SERIAL_NUMBER


class TestTelnetExceptions:
    """Tests for custom telnet exceptions."""

    def test_telnet_connection_error_init(self) -> None:
        """Test TelnetConnectionError initialization."""
        error = TelnetConnectionError(TEST_HOST, TEST_PORT, CONN_TIMEOUT)
        assert error.host == TEST_HOST
        assert error.port == TEST_PORT
        assert error.timeout == CONN_TIMEOUT
        assert TEST_HOST in str(error)
        assert str(TEST_PORT) in str(error)

    def test_telnet_connection_error_custom_message(self) -> None:
        """Test TelnetConnectionError with custom message."""
        custom_msg = "Custom error message"
        error = TelnetConnectionError(TEST_HOST, TEST_PORT, CONN_TIMEOUT, custom_msg)
        assert error.message == custom_msg
        assert str(error) == custom_msg

    def test_telnet_command_error_init(self) -> None:
        """Test TelnetCommandError initialization."""
        error = TelnetCommandError("@dat")
        assert error.command == "@dat"
        assert "@dat" in str(error)

    def test_telnet_command_error_custom_message(self) -> None:
        """Test TelnetCommandError with custom message."""
        custom_msg = "Command failed badly"
        error = TelnetCommandError("@sta", custom_msg)
        assert error.message == custom_msg
        assert str(error) == custom_msg


class TestElios4YouAPIInit:
    """Tests for Elios4YouAPI initialization."""

    def test_api_init(self, mock_hass) -> None:
        """Test API initialization with default values."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        assert api.name == TEST_NAME
        assert api.host == TEST_HOST
        assert api._port == TEST_PORT
        assert api._timeout == CONN_TIMEOUT
        assert api._reader is None
        assert api._writer is None
        assert api._last_activity == 0.0
        assert api.data["manufact"] == MANUFACTURER
        assert api.data["model"] == MODEL

    def test_api_data_structure_initialized(self, mock_hass) -> None:
        """Test that all expected data keys are initialized."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        # Check power/energy keys
        assert "produced_power" in api.data
        assert "consumed_power" in api.data
        assert "self_consumed_power" in api.data
        assert "bought_power" in api.data
        assert "sold_power" in api.data

        # Check energy keys
        assert "produced_energy" in api.data
        assert "consumed_energy" in api.data
        assert "bought_energy" in api.data
        assert "sold_energy" in api.data

        # Check info keys
        assert "sn" in api.data
        assert "fwtop" in api.data
        assert "fwbtm" in api.data
        assert "hwver" in api.data

        # Check relay key
        assert "relay_state" in api.data


class TestConnectionValidation:
    """Tests for connection validation."""

    def test_is_connection_valid_no_writer(self, mock_hass) -> None:
        """Test connection is invalid when writer is None."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        assert api._is_connection_valid() is False

    def test_is_connection_valid_writer_closing(self, mock_hass) -> None:
        """Test connection is invalid when writer is closing."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = True
        api._writer = mock_writer
        assert api._is_connection_valid() is False

    def test_is_connection_valid_transport_closing(self, mock_hass) -> None:
        """Test connection is invalid when transport is closing."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_transport = MagicMock()
        mock_transport.is_closing.return_value = True
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.get_extra_info.return_value = mock_transport
        api._writer = mock_writer
        assert api._is_connection_valid() is False

    def test_is_connection_valid_expired(self, mock_hass) -> None:
        """Test connection is invalid when expired."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.get_extra_info.return_value = None
        api._writer = mock_writer
        api._last_activity = 0.0  # Very old
        assert api._is_connection_valid() is False

    def test_is_connection_valid_active(self, mock_hass) -> None:
        """Test connection is valid when active."""

        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.is_closing.return_value = False
        mock_writer.get_extra_info.return_value = None
        api._writer = mock_writer
        api._last_activity = time.time()  # Just now
        assert api._is_connection_valid() is True


class TestSafeClose:
    """Tests for safe close functionality."""

    @pytest.mark.asyncio
    async def test_safe_close_with_writer(self, mock_hass) -> None:
        """Test safe close when writer exists."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        api._writer = mock_writer
        api._reader = MagicMock()
        api._last_activity = 100.0

        await api._safe_close()

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        assert api._writer is None
        assert api._reader is None
        assert api._last_activity == 0.0

    @pytest.mark.asyncio
    async def test_safe_close_without_writer(self, mock_hass) -> None:
        """Test safe close when no writer exists."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        # Should not raise
        await api._safe_close()
        assert api._writer is None

    @pytest.mark.asyncio
    async def test_safe_close_handles_exception(self, mock_hass) -> None:
        """Test safe close handles exceptions gracefully."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.close.side_effect = Exception("Close failed")
        api._writer = mock_writer

        # Should not raise
        await api._safe_close()
        assert api._writer is None

    @pytest.mark.asyncio
    async def test_close_calls_safe_close(self, mock_hass) -> None:
        """Test public close method calls _safe_close."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._safe_close = AsyncMock()

        await api.close()

        api._safe_close.assert_called_once()


class TestEnsureConnected:
    """Tests for ensure connected functionality."""

    @pytest.mark.asyncio
    async def test_ensure_connected_reuses_valid(self, mock_hass) -> None:
        """Test ensure connected reuses valid connection."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._is_connection_valid = MagicMock(return_value=True)
        initial_activity = api._last_activity

        await api._ensure_connected()

        # Should update last activity but not open new connection
        assert api._last_activity >= initial_activity

    @pytest.mark.asyncio
    async def test_ensure_connected_opens_new(self, mock_hass) -> None:
        """Test ensure connected opens new connection when needed."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_reader = MagicMock()
        mock_writer = MagicMock()

        with patch(
            "custom_components.4noks_elios4you.api.telnetlib3.open_connection",
            new_callable=AsyncMock,
            return_value=(mock_reader, mock_writer),
        ):
            await api._ensure_connected()

        assert api._reader == mock_reader
        assert api._writer == mock_writer
        assert api._last_activity > 0

    @pytest.mark.asyncio
    async def test_ensure_connected_timeout_error(self, mock_hass) -> None:
        """Test ensure connected raises on timeout."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        with (
            patch(
                "custom_components.4noks_elios4you.api.telnetlib3.open_connection",
                new_callable=AsyncMock,
                side_effect=TimeoutError("Connection timed out"),
            ),
            pytest.raises(TelnetConnectionError) as exc_info,
        ):
            await api._ensure_connected()

        assert exc_info.value.host == TEST_HOST
        assert exc_info.value.port == TEST_PORT

    @pytest.mark.asyncio
    async def test_ensure_connected_os_error(self, mock_hass) -> None:
        """Test ensure connected raises on OS error."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        with (
            patch(
                "custom_components.4noks_elios4you.api.telnetlib3.open_connection",
                new_callable=AsyncMock,
                side_effect=OSError("Network unreachable"),
            ),
            pytest.raises(TelnetConnectionError),
        ):
            await api._ensure_connected()


class TestAsyncReadUntil:
    """Tests for async read until functionality."""

    @pytest.mark.asyncio
    async def test_async_read_until_success(self, mock_hass) -> None:
        """Test successful read until separator."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value="data\nready...")
        api._reader = mock_reader

        result = await api._async_read_until("ready...", 5.0)

        assert "ready..." in result
        assert "data" in result

    @pytest.mark.asyncio
    async def test_async_read_until_timeout(self, mock_hass) -> None:
        """Test read until returns partial on timeout."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(side_effect=TimeoutError())
        api._reader = mock_reader

        result = await api._async_read_until("ready...", 0.1)

        # Should return empty or partial buffer
        assert "ready..." not in result

    @pytest.mark.asyncio
    async def test_async_read_until_eof(self, mock_hass) -> None:
        """Test read until returns on EOF."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value="")  # EOF
        api._reader = mock_reader

        result = await api._async_read_until("ready...", 5.0)

        assert result == ""


class TestAsyncSendCommand:
    """Tests for async send command functionality."""

    @pytest.mark.asyncio
    async def test_async_send_command_success(self, mock_hass) -> None:
        """Test successful command send and parse."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        api._writer = mock_writer

        # Mock response for @dat command
        response = "@dat\n0;produced_power;1.5\n0;consumed_power;2.0\n\nready..."
        api._async_read_until = AsyncMock(return_value=response)

        result = await api._async_send_command("@dat")

        assert result is not None
        assert "produced_power" in result
        mock_writer.write.assert_called()

    @pytest.mark.asyncio
    async def test_async_send_command_silent_timeout(self, mock_hass) -> None:
        """Test command returns None on silent timeout."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        api._writer = mock_writer

        # Response without separator
        api._async_read_until = AsyncMock(return_value="partial data")

        result = await api._async_send_command("@dat")

        assert result is None

    @pytest.mark.asyncio
    async def test_async_send_command_empty_response(self, mock_hass) -> None:
        """Test command returns None on empty response."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        api._writer = mock_writer

        api._async_read_until = AsyncMock(return_value="")

        result = await api._async_send_command("@dat")

        assert result is None

    @pytest.mark.asyncio
    async def test_async_send_command_inf_format(self, mock_hass) -> None:
        """Test @inf command uses = separator."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        api._writer = mock_writer

        # @inf format uses = separator
        response = "@inf\nsn=ABC123\nhwver=1.0\n\nready..."
        api._async_read_until = AsyncMock(return_value=response)

        result = await api._async_send_command("@inf")

        assert result is not None
        assert "sn" in result
        assert result["sn"] == "ABC123"


class TestGetDataWithRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_get_data_with_retry_success_first(self, mock_hass) -> None:
        """Test retry returns on first success."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._async_send_command = AsyncMock(return_value={"key": "value"})

        result = await api._get_data_with_retry("@dat")

        assert result == {"key": "value"}
        assert api._async_send_command.call_count == 1

    @pytest.mark.asyncio
    async def test_get_data_with_retry_success_after_retry(self, mock_hass) -> None:
        """Test retry succeeds after initial failure."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._async_send_command = AsyncMock(side_effect=[None, {"key": "value"}])
        api._safe_close = AsyncMock()
        api._ensure_connected = AsyncMock()

        result = await api._get_data_with_retry("@dat", max_retries=2)

        assert result == {"key": "value"}
        assert api._async_send_command.call_count == 2
        api._safe_close.assert_called()
        api._ensure_connected.assert_called()

    @pytest.mark.asyncio
    async def test_get_data_with_retry_all_fail(self, mock_hass) -> None:
        """Test retry returns None when all attempts fail."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._async_send_command = AsyncMock(return_value=None)
        api._safe_close = AsyncMock()
        api._ensure_connected = AsyncMock()

        result = await api._get_data_with_retry("@dat", max_retries=2)

        assert result is None
        assert api._async_send_command.call_count == 3  # Initial + 2 retries


class TestCheckPort:
    """Tests for check_port functionality."""

    def test_check_port_open(self, mock_hass) -> None:
        """Test check_port returns True when port is open."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_socket

            result = api.check_port()

        assert result is True
        mock_socket.settimeout.assert_called()
        mock_socket.close.assert_called()

    def test_check_port_closed(self, mock_hass) -> None:
        """Test check_port returns False when port is closed."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 111  # Connection refused
            mock_socket_class.return_value = mock_socket

            result = api.check_port()

        assert result is False


class TestAsyncGetData:
    """Tests for async_get_data functionality."""

    @pytest.mark.asyncio
    async def test_async_get_data_success(self, mock_hass) -> None:
        """Test successful data retrieval."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()

        # Mock successful responses
        dat_data = {
            "produced_power": "2.5",
            "consumed_power": "1.8",
            "sold_power": "0.7",
            "produced_energy": "100",
            "sold_energy": "30",
            "produced_energy_f1": "50",
            "produced_energy_f2": "30",
            "produced_energy_f3": "20",
            "sold_energy_f1": "15",
            "sold_energy_f2": "10",
            "sold_energy_f3": "5",
        }
        sta_data = {"daily_peak": "3.2", "monthly_peak": "4.5"}
        inf_data = {"sn": TEST_SERIAL_NUMBER, "fwtop": "1.0", "fwbtm": "2.0", "hwver": "3.0"}

        api._get_data_with_retry = AsyncMock(side_effect=[dat_data, sta_data, inf_data])

        result = await api.async_get_data()

        assert result is True
        assert api.data["produced_power"] == 2.5
        assert api.data["consumed_power"] == 1.8
        assert api.data["sn"] == TEST_SERIAL_NUMBER
        # Check calculated fields
        assert api.data["swver"] == "1.0 / 2.0"
        assert api.data["self_consumed_power"] == 1.8  # 2.5 - 0.7

    @pytest.mark.asyncio
    async def test_async_get_data_dat_fails(self, mock_hass) -> None:
        """Test data retrieval fails when @dat fails."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(return_value=None)

        with pytest.raises(TelnetCommandError) as exc_info:
            await api.async_get_data()

        assert "@dat" in exc_info.value.command

    @pytest.mark.asyncio
    async def test_async_get_data_sta_fails(self, mock_hass) -> None:
        """Test data retrieval fails when @sta fails."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(side_effect=[{"key": "1"}, None])

        with pytest.raises(TelnetCommandError) as exc_info:
            await api.async_get_data()

        assert "@sta" in exc_info.value.command

    @pytest.mark.asyncio
    async def test_async_get_data_inf_fails(self, mock_hass) -> None:
        """Test data retrieval fails when @inf fails."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(side_effect=[{"key": "1"}, {"key": "2"}, None])

        with pytest.raises(TelnetCommandError) as exc_info:
            await api.async_get_data()

        assert "@inf" in exc_info.value.command

    @pytest.mark.asyncio
    async def test_async_get_data_connection_error(self, mock_hass) -> None:
        """Test data retrieval fails on connection error."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock(side_effect=TimeoutError("Connection failed"))
        api._safe_close = AsyncMock()

        with pytest.raises(TelnetConnectionError):
            await api.async_get_data()

    @pytest.mark.asyncio
    async def test_async_get_data_uses_lock(self, mock_hass) -> None:
        """Test that async_get_data uses connection lock."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(
            side_effect=[
                {"produced_power": "1"},
                {"daily_peak": "2"},
                {"sn": "123", "fwtop": "1", "fwbtm": "2"},
            ]
        )

        # Lock should be acquired during operation
        assert not api._connection_lock.locked()
        await api.async_get_data()
        assert not api._connection_lock.locked()


class TestTelnetSetRelay:
    """Tests for telnet_set_relay functionality."""

    @pytest.mark.asyncio
    async def test_set_relay_on_success(self, mock_hass) -> None:
        """Test successful relay ON."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(
            side_effect=[{"status": "ok"}, {"rel": "1"}]  # Set command  # Read state
        )

        result = await api.telnet_set_relay("on")

        assert result is True
        assert api.data["relay_state"] == 1

    @pytest.mark.asyncio
    async def test_set_relay_off_success(self, mock_hass) -> None:
        """Test successful relay OFF."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(side_effect=[{"status": "ok"}, {"rel": "0"}])

        result = await api.telnet_set_relay("off")

        assert result is True
        assert api.data["relay_state"] == 0

    @pytest.mark.asyncio
    async def test_set_relay_invalid_state(self, mock_hass) -> None:
        """Test relay with invalid state returns False."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)

        result = await api.telnet_set_relay("invalid")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_relay_command_fails(self, mock_hass) -> None:
        """Test relay returns False when command fails."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(return_value=None)

        result = await api.telnet_set_relay("on")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_relay_read_fails(self, mock_hass) -> None:
        """Test relay handles read failure."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(
            side_effect=[{"status": "ok"}, None]  # Set works  # Read fails
        )

        result = await api.telnet_set_relay("on")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_relay_state_mismatch(self, mock_hass) -> None:
        """Test relay returns False when state doesn't match."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._safe_close = AsyncMock()
        api._get_data_with_retry = AsyncMock(
            side_effect=[{"status": "ok"}, {"rel": "0"}]  # Set command  # But relay is off
        )

        result = await api.telnet_set_relay("on")  # Wanted on

        assert result is False

    @pytest.mark.asyncio
    async def test_set_relay_connection_error(self, mock_hass) -> None:
        """Test relay handles connection error."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock(
            side_effect=TelnetConnectionError(TEST_HOST, TEST_PORT, CONN_TIMEOUT)
        )
        api._safe_close = AsyncMock()

        result = await api.telnet_set_relay("on")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_relay_timeout_error(self, mock_hass) -> None:
        """Test relay handles timeout error."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._get_data_with_retry = AsyncMock(side_effect=TimeoutError("Timed out"))
        api._safe_close = AsyncMock()

        result = await api.telnet_set_relay("on")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_relay_generic_exception(self, mock_hass) -> None:
        """Test relay handles generic exception."""
        api = Elios4YouAPI(mock_hass, TEST_NAME, TEST_HOST, TEST_PORT)
        api._ensure_connected = AsyncMock()
        api._get_data_with_retry = AsyncMock(side_effect=Exception("Unexpected error"))
        api._safe_close = AsyncMock()

        result = await api.telnet_set_relay("on")

        assert result is False
