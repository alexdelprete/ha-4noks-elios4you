"""API Platform for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import asyncio
from contextlib import suppress
import logging
import socket
import time

import telnetlib3

from .const import COMMAND_RETRY_COUNT, COMMAND_RETRY_DELAY, CONN_TIMEOUT, MANUFACTURER, MODEL
from .helpers import log_debug, log_error

_LOGGER = logging.getLogger(__name__)


class TelnetConnectionError(Exception):
    """Exception raised when telnet connection fails."""

    def __init__(self, host: str, port: int, timeout: int, message: str = "") -> None:
        """Initialize the exception."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.message = message or f"Failed to connect to {host}:{port} (timeout: {timeout}s)"
        super().__init__(self.message)


class TelnetCommandError(Exception):
    """Exception raised when telnet command fails."""

    def __init__(self, command: str, message: str = "") -> None:
        """Initialize the exception."""
        self.command = command
        self.message = message or f"Command '{command}' failed"
        super().__init__(self.message)


class Elios4YouAPI:
    """Wrapper class for Elios4You telnet communication.

    Uses telnetlib3 for fully async I/O to avoid blocking the Home Assistant event loop.
    """

    # Connection reuse timeout in seconds - reuse connection if last activity within this window
    CONNECTION_REUSE_TIMEOUT: float = 25.0

    def __init__(self, hass, name, host, port):
        """Initialize the Elios4You API Client."""
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._timeout = CONN_TIMEOUT
        self._sensors = []
        self.data = {}

        # Async telnetlib3 reader/writer streams
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        # Connection pooling: prevent socket exhaustion on embedded device
        self._connection_lock = asyncio.Lock()
        self._last_activity: float = 0.0

        # Initialize Elios4You data structure before first read
        self.data["produced_power"] = 1
        self.data["consumed_power"] = 1
        self.data["self_consumed_power"] = 1
        self.data["bought_power"] = 1
        self.data["sold_power"] = 1
        self.data["daily_peak"] = 1
        self.data["monthly_peak"] = 1
        self.data["produced_energy"] = 1
        self.data["produced_energy_f1"] = 1
        self.data["produced_energy_f2"] = 1
        self.data["produced_energy_f3"] = 1
        self.data["consumed_energy"] = 1
        self.data["consumed_energy_f1"] = 1
        self.data["consumed_energy_f2"] = 1
        self.data["consumed_energy_f3"] = 1
        self.data["self_consumed_energy"] = 1
        self.data["self_consumed_energy_f1"] = 1
        self.data["self_consumed_energy_f2"] = 1
        self.data["self_consumed_energy_f3"] = 1
        self.data["bought_energy"] = 1
        self.data["bought_energy_f1"] = 1
        self.data["bought_energy_f2"] = 1
        self.data["bought_energy_f3"] = 1
        self.data["sold_energy"] = 1
        self.data["sold_energy_f1"] = 1
        self.data["sold_energy_f2"] = 1
        self.data["sold_energy_f3"] = 1
        self.data["alarm_1"] = 1
        self.data["alarm_2"] = 1
        self.data["power_alarm"] = 1
        self.data["relay_state"] = 1
        self.data["pwm_mode"] = 1
        self.data["pr_ssv"] = 1
        self.data["rel_ssv"] = 1
        self.data["rel_mode"] = 1
        self.data["rel_warning"] = 1
        self.data["rcap"] = 1
        self.data["utc_time"] = ""
        self.data["fwtop"] = ""
        self.data["fwbtm"] = ""
        self.data["sn"] = ""
        self.data["hwver"] = ""
        self.data["btver"] = ""
        self.data["hw_wifi"] = ""
        self.data["s2w_app_version"] = ""
        self.data["s2w_geps_version"] = ""
        self.data["s2w_wlan_version"] = ""
        # custom fields to reuse code structure
        self.data["manufact"] = MANUFACTURER
        self.data["model"] = MODEL

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def host(self):
        """Return the device name."""
        return self._host

    async def close(self) -> None:
        """Close the telnet connection."""
        await self._safe_close()

    def _is_connection_valid(self) -> bool:
        """Check if existing connection can be reused.

        Returns True if:
        - Writer stream is open
        - Last activity was within CONNECTION_REUSE_TIMEOUT seconds
        """
        if self._writer is None or self._writer.is_closing():
            return False
        if time.time() - self._last_activity > self.CONNECTION_REUSE_TIMEOUT:
            log_debug(
                _LOGGER,
                "_is_connection_valid",
                "Connection expired, will reconnect",
                idle_seconds=round(time.time() - self._last_activity, 1),
            )
            return False
        return True

    async def _safe_close(self) -> None:
        """Safely close connection with proper cleanup.

        This method:
        - Closes the writer stream gracefully
        - Waits for connection to fully close
        - Resets connection state
        """
        if self._writer is not None:
            with suppress(Exception):
                self._writer.close()
                await self._writer.wait_closed()
            self._writer = None
            self._reader = None
            self._last_activity = 0.0
            log_debug(_LOGGER, "_safe_close", "Connection closed and cleaned up")
        else:
            log_debug(_LOGGER, "_safe_close", "No connection to close")

    async def _ensure_connected(self) -> None:
        """Open connection only if needed, reusing existing connection if valid.

        This method implements connection pooling to prevent socket exhaustion
        on the embedded Elios4You device.

        Raises:
            TelnetConnectionError: If connection cannot be established.
        """
        if self._is_connection_valid():
            log_debug(
                _LOGGER,
                "_ensure_connected",
                "Reusing existing connection",
                idle_seconds=round(time.time() - self._last_activity, 1),
            )
            self._last_activity = time.time()
            return

        # Close any stale connection before opening new one
        await self._safe_close()

        try:
            log_debug(
                _LOGGER,
                "_ensure_connected",
                "Opening new connection",
                host=self._host,
                port=self._port,
            )
            self._reader, self._writer = await asyncio.wait_for(
                telnetlib3.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
            self._last_activity = time.time()
            log_debug(_LOGGER, "_ensure_connected", "Connection established")
        except (TimeoutError, OSError) as err:
            log_debug(
                _LOGGER,
                "_ensure_connected",
                "Connection failed",
                error=str(err),
            )
            raise TelnetConnectionError(
                self._host, self._port, self._timeout, f"Connection failed: {err}"
            ) from err

    async def _async_read_until(
        self,
        separator: bytes,
        timeout: float,
    ) -> bytes:
        """Async read until separator found or timeout.

        telnetlib3 provides stream-based I/O without built-in read_until,
        so we implement our own async version.

        Args:
            separator: Bytes sequence to wait for (e.g., b"ready...")
            timeout: Maximum seconds to wait

        Returns:
            Buffer containing data up to and including separator,
            or partial data if timeout/EOF occurs.
        """
        buffer = b""
        loop = asyncio.get_event_loop()
        end_time = loop.time() + timeout

        while separator not in buffer:
            remaining = end_time - loop.time()
            if remaining <= 0:
                log_debug(
                    _LOGGER,
                    "_async_read_until",
                    "Timeout waiting for separator",
                    buffer_len=len(buffer),
                )
                return buffer  # Timeout - return partial

            try:
                chunk = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=remaining,
                )
                if not chunk:
                    log_debug(
                        _LOGGER,
                        "_async_read_until",
                        "EOF received",
                        buffer_len=len(buffer),
                    )
                    return buffer  # EOF
                buffer += chunk
            except TimeoutError:
                log_debug(
                    _LOGGER,
                    "_async_read_until",
                    "asyncio.TimeoutError during read",
                    buffer_len=len(buffer),
                )
                return buffer

        return buffer

    async def _async_send_command(self, cmd: str) -> dict | None:
        """Send command and read response asynchronously.

        This replaces the synchronous telnet_get_data() method.

        Args:
            cmd: Command to send (e.g., "@dat", "@sta", "@inf", "@rel")

        Returns:
            Parsed response dict or None if failed
        """
        try:
            cmd_main = cmd[0:4].lower()
            separator = b"ready..."

            log_debug(_LOGGER, "_async_send_command", "Sending command", cmd=cmd)

            # Send command with newline
            cmd_bytes = (cmd.lower() + "\n").encode("utf-8")
            self._writer.write(cmd_bytes)
            await self._writer.drain()

            # Read until separator
            log_debug(_LOGGER, "_async_send_command", "Waiting for response")
            response_bytes = await self._async_read_until(separator, self._timeout)

            # Decode response
            response = response_bytes.decode("utf-8", errors="replace")
            log_debug(
                _LOGGER,
                "_async_send_command",
                "Response received",
                response_len=len(response),
            )

            # Check for silent timeout - incomplete response without separator
            if not response or "ready..." not in response:
                log_debug(
                    _LOGGER,
                    "_async_send_command",
                    "Silent timeout - incomplete response",
                    has_response=bool(response),
                    has_separator="ready..." in response if response else False,
                )
                return None

            # Valid response - process data
            output = {}
            lines = response.splitlines()

            # Sometimes the first line is not the command but a line-feed
            if lines[0].lower() in ["@dat", "@sta", "@inf", "@rel", "@hwr"]:
                lines_start = 1
            else:
                # Skip the possible LF in first line
                lines_start = 2

            # Skip last two lines (line-feed and read_until separator)
            lines_end = -2

            # Parse key-value pairs
            for line in lines[lines_start:lines_end]:
                if cmd_main in ["@inf", "@rel", "@hwr"]:
                    # @inf data uses a different separator
                    key, value = line.split("=")
                else:
                    # @dat and @sta share the same data format
                    key, value = line.split(";")[1:3]
                # Lower case and replace space with underscore
                output[key.lower().replace(" ", "_")] = value.strip()

            log_debug(
                _LOGGER,
                "_async_send_command",
                "Success",
                output_keys=list(output.keys()),
            )
            return output

        except TimeoutError:
            log_debug(_LOGGER, "_async_send_command", "Operation timed out")
            return None
        except Exception as ex:
            log_debug(_LOGGER, "_async_send_command", "Failed with error", error=ex)
            return None

    async def _get_data_with_retry(
        self,
        cmd: str,
        max_retries: int = COMMAND_RETRY_COUNT,
    ) -> dict | None:
        """Execute telnet command with retry logic for transient failures.

        If command fails (returns None due to silent timeout or error),
        closes connection, reconnects, and retries up to max_retries times.

        Args:
            cmd: Telnet command to execute (@dat, @sta, @inf, @rel)
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed response dict or None if all attempts fail
        """
        for attempt in range(max_retries + 1):
            result = await self._async_send_command(cmd)
            if result is not None:
                return result

            if attempt < max_retries:
                log_debug(
                    _LOGGER,
                    "_get_data_with_retry",
                    "Command failed, retrying",
                    cmd=cmd,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                await asyncio.sleep(COMMAND_RETRY_DELAY)
                # Close stale connection and reconnect for retry
                await self._safe_close()
                await self._ensure_connected()

        return None

    def check_port(self) -> bool:
        """Check if port is available.

        Note: This method is kept for backwards compatibility with tests.
        The main code now uses _ensure_connected() for connection management.
        """
        sock_timeout = 3.0
        log_debug(
            _LOGGER,
            "check_port",
            "Opening socket",
            host=self._host,
            port=self._port,
            timeout=sock_timeout,
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Use socket-specific timeout instead of global (prevents thread-safety issues)
            sock.settimeout(sock_timeout)
            sock_res = sock.connect_ex((self._host, self._port))
            # True if open, False if not
            is_open = sock_res == 0
            if is_open:
                with suppress(Exception):
                    sock.shutdown(socket.SHUT_RDWR)
                log_debug(
                    _LOGGER,
                    "check_port",
                    "Port open",
                    host=self._host,
                    port=self._port,
                )
            else:
                log_debug(
                    _LOGGER,
                    "check_port",
                    "Port not available",
                    host=self._host,
                    port=self._port,
                    error=sock_res,
                )
            return is_open
        finally:
            sock.close()

    async def async_get_data(self) -> bool:
        """Read Data Function.

        Uses connection pooling to prevent socket exhaustion on embedded device.
        Connection is reused if last activity was within CONNECTION_REUSE_TIMEOUT.

        All I/O operations are fully async - no event loop blocking.
        """
        # Use lock to prevent race conditions between polling and switch commands
        async with self._connection_lock:
            log_debug(
                _LOGGER,
                "async_get_data",
                "========== READ CYCLE START ==========",
            )
            try:
                # Use connection pooling - reuse existing connection if valid
                await self._ensure_connected()

                log_debug(_LOGGER, "async_get_data", "Fetching device data")
                dat_parsed = await self._get_data_with_retry("@dat")
                if dat_parsed is None:
                    # Force reconnect on next attempt
                    await self._safe_close()
                    raise TelnetCommandError("@dat", "Failed to retrieve @dat data")

                log_debug(_LOGGER, "async_get_data", "Parsing @dat data")
                for key, value in dat_parsed.items():
                    # @dat returns only numbers as strings
                    # power/energy as float all others as int
                    try:
                        if ("energy" in key) or ("power" in key):
                            self.data[key] = round(float(value), 2)
                        elif key == "utc_time":
                            pass
                        else:
                            self.data[key] = int(value)
                    except ValueError:
                        log_debug(
                            _LOGGER,
                            "async_get_data",
                            "Value could not be parsed",
                            key=key,
                            value=value,
                        )
                        continue

                sta_parsed = await self._get_data_with_retry("@sta")
                if sta_parsed is None:
                    await self._safe_close()
                    raise TelnetCommandError("@sta", "Failed to retrieve @sta data")

                log_debug(_LOGGER, "async_get_data", "Parsing @sta data")
                for key, value in sta_parsed.items():
                    # @sta returns only float numbers as strings
                    try:
                        self.data[key] = round(float(value), 2)
                    except ValueError:
                        log_debug(
                            _LOGGER,
                            "async_get_data",
                            "Value could not be parsed",
                            key=key,
                            value=value,
                        )

                inf_parsed = await self._get_data_with_retry("@inf")
                if inf_parsed is None:
                    await self._safe_close()
                    raise TelnetCommandError("@inf", "Failed to retrieve @inf data")

                log_debug(_LOGGER, "async_get_data", "Parsing @inf data")
                for key, value in inf_parsed.items():
                    # @inf returns only strings
                    self.data[key] = str(value)

                # Calculated sensor to combine TOP/BOTTOM fw versions
                self.data["swver"] = f"{self.data['fwtop']} / {self.data['fwbtm']}"

                # Calculated sensors for self-consumption sensors
                self.data["self_consumed_power"] = round(
                    (self.data["produced_power"] - self.data["sold_power"]), 2
                )

                self.data["self_consumed_energy"] = round(
                    (self.data["produced_energy"] - self.data["sold_energy"]), 2
                )

                self.data["self_consumed_energy_f1"] = round(
                    (self.data["produced_energy_f1"] - self.data["sold_energy_f1"]),
                    2,
                )
                self.data["self_consumed_energy_f2"] = round(
                    (self.data["produced_energy_f2"] - self.data["sold_energy_f2"]),
                    2,
                )
                self.data["self_consumed_energy_f3"] = round(
                    (self.data["produced_energy_f3"] - self.data["sold_energy_f3"]),
                    2,
                )

                # Update last activity time for connection reuse
                self._last_activity = time.time()
                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "========== READ CYCLE END (success) ==========",
                )
                return True

            except (TimeoutError, OSError) as err:
                # Connection error - close and force reconnect on next attempt
                await self._safe_close()
                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "Connection or operation timed out",
                    error=err,
                )
                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "========== READ CYCLE END (timeout) ==========",
                )
                raise TelnetConnectionError(
                    self._host, self._port, self._timeout, f"Connection error: {err}"
                ) from err
            except (TelnetConnectionError, TelnetCommandError):
                # Close on error to force fresh connection next time
                await self._safe_close()
                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "========== READ CYCLE END (command error) ==========",
                )
                raise
            except Exception as err:
                # Close on any error
                await self._safe_close()
                log_error(
                    _LOGGER,
                    "async_get_data",
                    "Unexpected error during data fetch",
                    error=err,
                )
                log_debug(
                    _LOGGER,
                    "async_get_data",
                    "========== READ CYCLE END (unexpected error) ==========",
                )
                raise TelnetCommandError("async_get_data", f"Unexpected error: {err}") from err

    async def telnet_set_relay(self, state) -> bool:
        """Send Telnet Commands and process output.

        Uses connection pooling to prevent socket exhaustion on embedded device.
        Uses same lock as async_get_data() to prevent race conditions.

        All I/O operations are fully async - no event loop blocking.
        """
        set_relay = False

        if state.lower() == "on":
            to_state: int = 1
        elif state.lower() == "off":
            to_state: int = 0
        else:
            return set_relay

        # Use lock to prevent race conditions between polling and switch commands
        async with self._connection_lock:
            try:
                # Use connection pooling - reuse existing connection if valid
                await self._ensure_connected()

                log_debug(
                    _LOGGER,
                    "telnet_set_relay",
                    "Sending relay command",
                    to_state=to_state,
                )

                # Send set relay command with retry
                set_result = await self._get_data_with_retry(f"@rel 0 {to_state}")
                if set_result is None:
                    log_debug(
                        _LOGGER,
                        "telnet_set_relay",
                        "Set relay command failed after retries",
                    )
                    await self._safe_close()
                    return set_relay

                # Read relay state with retry
                rel_parsed = await self._get_data_with_retry("@rel")

                # if we had a valid response we process data
                if rel_parsed:
                    rel_output = {}
                    for key, value in rel_parsed.items():
                        rel_output[key] = value
                    log_debug(
                        _LOGGER,
                        "telnet_set_relay",
                        "Relay output",
                        rel_output=rel_output,
                    )
                    out_mode = int(rel_output["rel"])
                    log_debug(
                        _LOGGER,
                        "telnet_set_relay",
                        "Sent telnet command",
                        command=f"@rel 0 {to_state}",
                        rel=out_mode,
                    )
                    if out_mode == to_state:
                        set_relay = True
                        # refresh relay_state value to avoid waiting for poll cycle
                        self.data["relay_state"] = out_mode
                        log_debug(
                            _LOGGER,
                            "telnet_set_relay",
                            "Set relay success",
                            to_state=to_state,
                            rel=out_mode,
                            relay_state=self.data["relay_state"],
                        )
                    else:
                        set_relay = False
                        log_debug(
                            _LOGGER,
                            "telnet_set_relay",
                            "Set relay failure",
                            to_state=to_state,
                            rel=out_mode,
                            relay_state=self.data["relay_state"],
                        )
                else:
                    log_debug(_LOGGER, "telnet_set_relay", "rel_parsed is None")
                    # Force reconnect on next attempt
                    await self._safe_close()

                # Update last activity time for connection reuse
                self._last_activity = time.time()

            except TimeoutError:
                await self._safe_close()
                log_debug(_LOGGER, "telnet_set_relay", "Connection or operation timed out")
                set_relay = False
            except TelnetConnectionError:
                # Already closed by _ensure_connected failure
                log_debug(_LOGGER, "telnet_set_relay", "Connection failed")
                set_relay = False
            except Exception as ex:
                await self._safe_close()
                log_debug(_LOGGER, "telnet_set_relay", "Failed with error", error=ex)
                set_relay = False

        log_debug(_LOGGER, "telnet_set_relay", "End telnet_set_relay", result=set_relay)
        return set_relay
