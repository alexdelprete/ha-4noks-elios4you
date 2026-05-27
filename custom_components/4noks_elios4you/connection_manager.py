"""Connection manager for 4-noks Elios4you telnet device.

Owns the single TCP/telnet connection to the device, serializes all command
execution, implements adaptive backoff to spare the fragile embedded device,
and exposes metrics for diagnostic entities.

The Elios4You has a small embedded TCP stack with very few socket slots
(typically 1-4). Hammering it with reconnects or retry storms causes the
device to become unresponsive ("deaf") until its WiFi stack is reset. This
manager exists to make connection handling deliberate, observable, and
gentle on the device.

State machine
-------------

    DISCONNECTED ──(execute)──► CONNECTING ──(open ok)──► READY ──(command)──┐
        ▲                           │                       ▲                │
        │                  (open fail, ≥ threshold)         │       (silent timeout │
        │                           ▼                       │        / transport    │
        │                       BACKOFF ──(window expires)──┘        error → RST)   │
        │                           ▲                                              │
        │                           └──────────────(record_failure on cmd error)───┘
        │
        └──(close on unload)────► CLOSED  (terminal)

Concurrency
-----------

A single asyncio.Lock serializes the entire send-and-receive cycle.
Polling, switch presses, and any future callers all queue on the same lock.
Within the lock, the connection may be reused if the previous activity is
within the reuse window — this avoids churning sockets at the device.

Failure handling
----------------

* Soft failures (silent timeout, transport error mid-command): close the
  socket with RST via `transport.abort()` so the device frees the slot
  immediately, then retry up to ``max_retries`` times.
* Hard failures (no response after all retries, or cannot open at all):
  raise an exception. Each hard failure increments ``consecutive_failures``.
  After ``backoff_threshold`` consecutive failures, the manager enters
  BACKOFF for an exponentially growing window capped at ``backoff_max``.
* While in BACKOFF, ``execute()`` raises ``ConnectionUnavailableError``
  immediately without touching the network. The coordinator's normal
  polling cadence then provides natural rate-limiting.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from enum import StrEnum
import logging
import time
from typing import cast

import telnetlib3

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .helpers import log_debug, log_info, log_warning

_LOGGER = logging.getLogger(__name__)

LOG_PREFIX = "ConnMgr"
RESPONSE_SEPARATOR = "ready..."


class ConnectionState(StrEnum):
    """Lifecycle states of the managed connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BACKOFF = "backoff"
    CLOSED = "closed"


class ConnectionManagerError(HomeAssistantError):
    """Base error from the connection manager."""


class ConnectionUnavailableError(ConnectionManagerError):
    """Raised when the manager refuses to talk to the device (backoff / closed)."""

    def __init__(self, reason: str, retry_after: float = 0.0) -> None:
        """Initialize with a human-readable reason and optional retry-after seconds."""
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(reason)


class TelnetConnectionError(ConnectionManagerError):
    """Exception raised when telnet connection fails."""

    def __init__(self, host: str, port: int, timeout: float, message: str = "") -> None:
        """Initialize the exception."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.message = message or f"Failed to connect to {host}:{port} (timeout: {timeout}s)"
        super().__init__(self.message)
        self.translation_domain = DOMAIN
        self.translation_key = "telnet_connection_error"
        self.translation_placeholders = {
            "host": host,
            "port": str(port),
            "timeout": str(timeout),
        }


class TelnetCommandError(ConnectionManagerError):
    """Exception raised when telnet command fails after retries."""

    def __init__(self, command: str, message: str = "") -> None:
        """Initialize the exception."""
        self.command = command
        self.message = message or f"Command '{command}' failed"
        super().__init__(self.message)
        self.translation_domain = DOMAIN
        self.translation_key = "telnet_command_error"
        self.translation_placeholders = {
            "command": command,
        }


class _RetryableError(Exception):
    """Internal: a soft failure that should trigger an in-execute retry."""

    def __init__(self, reason: str) -> None:
        """Store the human-readable reason."""
        self.reason = reason
        super().__init__(reason)


@dataclass
class ConnectionMetrics:
    """Cumulative + point-in-time diagnostics. Reset on integration reload."""

    state: ConnectionState = ConnectionState.DISCONNECTED
    state_since: float = field(default_factory=time.time)

    # Lifetime counters (since manager creation)
    connect_attempts: int = 0
    connect_failures: int = 0
    connects_succeeded: int = 0
    commands_sent: int = 0
    commands_failed: int = 0
    commands_retried: int = 0
    silent_timeouts: int = 0
    forced_aborts: int = 0
    graceful_closes: int = 0
    reuse_hits: int = 0
    backoff_entries: int = 0

    # Streak / current
    consecutive_failures: int = 0
    backoff_until: float = 0.0
    current_backoff_duration: float = 0.0

    # Last-event details
    last_command: str = ""
    last_error: str = ""
    last_connect_at: float = 0.0
    last_disconnect_at: float = 0.0
    last_success_at: float = 0.0
    last_failure_at: float = 0.0


class ConnectionManager:
    """Owns the single telnetlib3 connection to one Elios4you device."""

    # Defaults tuned for the Elios4You's fragile TCP stack and a 60 s scan
    # interval. See module docstring for rationale.
    DEFAULT_CONNECT_TIMEOUT: float = 5.0
    DEFAULT_READ_TIMEOUT: float = 5.0
    DEFAULT_CLOSE_TIMEOUT: float = 2.0
    DEFAULT_REUSE_WINDOW: float = 90.0
    DEFAULT_MAX_RETRIES: int = 1
    DEFAULT_RETRY_DELAY: float = 0.3
    DEFAULT_BACKOFF_THRESHOLD: int = 3
    DEFAULT_BACKOFF_INITIAL: float = 5.0
    DEFAULT_BACKOFF_MAX: float = 60.0

    # telnetlib3 negotiation timings — Elios4You doesn't really negotiate, so
    # keep these short to avoid adding latency to every connect.
    CONNECT_MINWAIT: float = 0.1
    CONNECT_MAXWAIT: float = 0.5

    def __init__(
        self,
        host: str,
        port: int,
        *,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        close_timeout: float = DEFAULT_CLOSE_TIMEOUT,
        reuse_window: float = DEFAULT_REUSE_WINDOW,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        backoff_threshold: int = DEFAULT_BACKOFF_THRESHOLD,
        backoff_initial: float = DEFAULT_BACKOFF_INITIAL,
        backoff_max: float = DEFAULT_BACKOFF_MAX,
    ) -> None:
        """Initialize the manager (does not open the connection)."""
        self._host = host
        self._port = port
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._close_timeout = close_timeout
        self._reuse_window = reuse_window
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._backoff_threshold = backoff_threshold
        self._backoff_initial = backoff_initial
        self._backoff_max = backoff_max

        # We pass ``encoding="utf-8"`` to ``open_connection`` so the runtime
        # types are the Unicode variants (str-based). ``open_connection`` is
        # typed to return the byte-based base classes, so we cast at the
        # assignment site (see ``_ensure_connected``).
        self._reader: telnetlib3.TelnetReaderUnicode | None = None
        self._writer: telnetlib3.TelnetWriterUnicode | None = None
        self._last_activity: float = 0.0

        self._lock = asyncio.Lock()
        self._metrics = ConnectionMetrics()

        log_debug(
            _LOGGER,
            f"{LOG_PREFIX}.__init__",
            "Manager created",
            host=host,
            port=port,
            reuse_window=reuse_window,
            max_retries=max_retries,
            backoff_threshold=backoff_threshold,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> ConnectionState:
        """Return the current state."""
        return self._metrics.state

    @property
    def metrics(self) -> ConnectionMetrics:
        """Return a live reference to the metrics dataclass."""
        return self._metrics

    def metrics_snapshot(self) -> dict[str, int | float | str]:
        """Return a dict suitable for exposing as diagnostic sensors.

        Timestamps are converted to seconds-since (float) so they're easy to
        render. Use ``backoff_seconds_remaining`` for the UI rather than the
        raw deadline.
        """
        now = time.time()
        m = asdict(self._metrics)
        # Replace enum with its value
        m["state"] = self._metrics.state.value
        m["backoff_seconds_remaining"] = max(0.0, round(self._metrics.backoff_until - now, 1))
        m["state_age_seconds"] = round(now - self._metrics.state_since, 1)
        return m

    async def execute(self, cmd: str) -> str:
        """Send a command and return the raw response string.

        The returned string is guaranteed to contain the response separator
        (``"ready..."``); callers can split on lines and parse from there.

        Raises:
            ConnectionUnavailableError: manager is in BACKOFF or CLOSED.
            TelnetConnectionError: cannot open the connection after retries.
            TelnetCommandError: command failed after all retries.

        """
        async with self._lock:
            self._enforce_availability()

            self._metrics.commands_sent += 1
            self._metrics.last_command = cmd

            log_debug(
                _LOGGER,
                f"{LOG_PREFIX}.execute",
                "Command requested",
                cmd=cmd,
                state=self._metrics.state.value,
                attempts=self._max_retries + 1,
            )

            last_reason = "unknown"
            for attempt in range(self._max_retries + 1):
                try:
                    raw = await self._attempt(cmd)
                except _RetryableError as err:
                    last_reason = err.reason
                    log_debug(
                        _LOGGER,
                        f"{LOG_PREFIX}.execute",
                        "Attempt failed (retryable)",
                        cmd=cmd,
                        attempt=attempt + 1,
                        max_attempts=self._max_retries + 1,
                        reason=err.reason,
                    )
                except TelnetConnectionError as err:
                    last_reason = f"connect_failed: {err.message}"
                    log_debug(
                        _LOGGER,
                        f"{LOG_PREFIX}.execute",
                        "Attempt failed (connect)",
                        cmd=cmd,
                        attempt=attempt + 1,
                        max_attempts=self._max_retries + 1,
                        reason=last_reason,
                    )
                else:
                    self._record_success()
                    return raw

                if attempt < self._max_retries:
                    self._metrics.commands_retried += 1
                    await asyncio.sleep(self._retry_delay)

            # All attempts exhausted
            self._metrics.commands_failed += 1
            self._record_failure(last_reason)
            log_warning(
                _LOGGER,
                f"{LOG_PREFIX}.execute",
                "Command failed after retries",
                cmd=cmd,
                attempts=self._max_retries + 1,
                reason=last_reason,
                consecutive_failures=self._metrics.consecutive_failures,
            )
            raise TelnetCommandError(cmd, last_reason)

    async def close(self) -> None:
        """Permanently close the connection (called on integration unload)."""
        async with self._lock:
            log_debug(
                _LOGGER,
                f"{LOG_PREFIX}.close",
                "Closing manager (terminal)",
                state=self._metrics.state.value,
            )
            await self._close_safely(force_abort=False)
            self._transition(ConnectionState.CLOSED, reason="unload")

    # ------------------------------------------------------------------ #
    # Internal: state machine
    # ------------------------------------------------------------------ #

    def _transition(self, new_state: ConnectionState, *, reason: str) -> None:
        """Move to a new state and log the transition (with the reason)."""
        old = self._metrics.state
        if old == new_state:
            return
        self._metrics.state = new_state
        self._metrics.state_since = time.time()
        log_debug(
            _LOGGER,
            f"{LOG_PREFIX}.transition",
            "State change",
            from_state=old.value,
            to_state=new_state.value,
            reason=reason,
        )

    def _enforce_availability(self) -> None:
        """Raise if the manager is currently refusing requests."""
        if self._metrics.state is ConnectionState.CLOSED:
            raise ConnectionUnavailableError("manager closed")

        if self._metrics.state is ConnectionState.BACKOFF:
            remaining = self._metrics.backoff_until - time.time()
            if remaining > 0:
                log_debug(
                    _LOGGER,
                    f"{LOG_PREFIX}._enforce_availability",
                    "Refusing call: in backoff",
                    remaining_seconds=round(remaining, 1),
                    consecutive_failures=self._metrics.consecutive_failures,
                )
                raise ConnectionUnavailableError(
                    f"in backoff ({remaining:.1f}s remaining)",
                    retry_after=remaining,
                )
            # Backoff expired — fall through to a fresh attempt.
            log_info(
                _LOGGER,
                f"{LOG_PREFIX}._enforce_availability",
                "Backoff expired, allowing one trial connection",
                consecutive_failures=self._metrics.consecutive_failures,
            )
            self._transition(ConnectionState.DISCONNECTED, reason="backoff_expired")

    def _record_success(self) -> None:
        """Reset failure streak and exit BACKOFF if applicable."""
        now = time.time()
        self._metrics.last_success_at = now
        if self._metrics.consecutive_failures > 0:
            log_info(
                _LOGGER,
                f"{LOG_PREFIX}._record_success",
                "Recovered from failure streak",
                previous_failures=self._metrics.consecutive_failures,
            )
        self._metrics.consecutive_failures = 0
        self._metrics.current_backoff_duration = 0.0
        self._metrics.backoff_until = 0.0

    def _record_failure(self, reason: str) -> None:
        """Increment failure streak; enter BACKOFF if threshold reached."""
        now = time.time()
        self._metrics.consecutive_failures += 1
        self._metrics.last_failure_at = now
        self._metrics.last_error = reason

        if self._metrics.consecutive_failures < self._backoff_threshold:
            return

        # Exponential backoff: initial, 2*initial, 4*initial, ... capped.
        over_threshold = self._metrics.consecutive_failures - self._backoff_threshold
        duration = min(self._backoff_initial * (2**over_threshold), self._backoff_max)
        self._metrics.current_backoff_duration = duration
        self._metrics.backoff_until = now + duration
        self._metrics.backoff_entries += 1

        self._transition(
            ConnectionState.BACKOFF, reason=f"failures={self._metrics.consecutive_failures}"
        )
        log_warning(
            _LOGGER,
            f"{LOG_PREFIX}._record_failure",
            "Entering BACKOFF",
            consecutive_failures=self._metrics.consecutive_failures,
            backoff_seconds=round(duration, 1),
            last_error=reason,
        )

    # ------------------------------------------------------------------ #
    # Internal: one command attempt
    # ------------------------------------------------------------------ #

    async def _attempt(self, cmd: str) -> str:
        """One full attempt: ensure connected, send, read response.

        Returns the raw response on success. Raises ``_RetryableError`` on
        recoverable failures (silent timeout, transport error mid-command)
        or ``TelnetConnectionError`` on a hard connect failure.
        """
        await self._ensure_connected()

        try:
            raw = await self._send_raw(cmd)
        except (TimeoutError, OSError) as err:
            await self._close_safely(force_abort=True)
            raise _RetryableError(f"transport_error: {err}") from err

        if not raw or RESPONSE_SEPARATOR not in raw:
            self._metrics.silent_timeouts += 1
            await self._close_safely(force_abort=True)
            raise _RetryableError("silent_timeout")

        self._last_activity = time.time()
        return raw

    # ------------------------------------------------------------------ #
    # Internal: connection lifecycle
    # ------------------------------------------------------------------ #

    async def _ensure_connected(self) -> None:
        """Open the connection if needed, or reuse a fresh one."""
        if self._can_reuse():
            self._metrics.reuse_hits += 1
            age = time.time() - self._last_activity
            log_debug(
                _LOGGER,
                f"{LOG_PREFIX}._ensure_connected",
                "Reusing connection",
                age_seconds=round(age, 1),
                reuse_window=self._reuse_window,
            )
            return

        # Drop any stale connection without ceremony before opening anew.
        if self._writer is not None:
            await self._close_safely(force_abort=True)

        self._transition(ConnectionState.CONNECTING, reason="open_new")
        self._metrics.connect_attempts += 1
        log_debug(
            _LOGGER,
            f"{LOG_PREFIX}._ensure_connected",
            "Opening new connection",
            host=self._host,
            port=self._port,
            timeout=self._connect_timeout,
        )

        try:
            reader, writer = await asyncio.wait_for(
                telnetlib3.open_connection(
                    host=self._host,
                    port=self._port,
                    encoding="utf-8",
                    encoding_errors="replace",
                    connect_minwait=self.CONNECT_MINWAIT,
                    connect_maxwait=self.CONNECT_MAXWAIT,
                ),
                timeout=self._connect_timeout,
            )
            # encoding="utf-8" guarantees the Unicode variants at runtime
            self._reader = cast(telnetlib3.TelnetReaderUnicode, reader)
            self._writer = cast(telnetlib3.TelnetWriterUnicode, writer)
        except (TimeoutError, OSError) as err:
            self._metrics.connect_failures += 1
            self._writer = None
            self._reader = None
            self._transition(ConnectionState.DISCONNECTED, reason=f"connect_failed: {err}")
            log_warning(
                _LOGGER,
                f"{LOG_PREFIX}._ensure_connected",
                "Connect failed",
                host=self._host,
                port=self._port,
                error=str(err),
            )
            raise TelnetConnectionError(
                self._host,
                self._port,
                self._connect_timeout,
                f"Connection failed: {err}",
            ) from err

        now = time.time()
        self._last_activity = now
        self._metrics.connects_succeeded += 1
        self._metrics.last_connect_at = now
        self._transition(ConnectionState.READY, reason="open_ok")
        log_info(
            _LOGGER,
            f"{LOG_PREFIX}._ensure_connected",
            "Connection established",
            host=self._host,
            port=self._port,
        )

    def _can_reuse(self) -> bool:
        """Return True if the current connection is healthy and within the reuse window."""
        if self._writer is None:
            return False
        try:
            if hasattr(self._writer, "is_closing") and self._writer.is_closing():
                return False
            transport = self._writer.get_extra_info("transport")
            if transport is not None and transport.is_closing():
                return False
        except (AttributeError, OSError):
            return False

        age = time.time() - self._last_activity
        if age > self._reuse_window:
            log_debug(
                _LOGGER,
                f"{LOG_PREFIX}._can_reuse",
                "Connection exceeded reuse window",
                age_seconds=round(age, 1),
                reuse_window=self._reuse_window,
            )
            return False
        return True

    async def _close_safely(self, *, force_abort: bool) -> None:
        """Close the connection. RST on error paths, FIN on graceful unload.

        ``force_abort=True`` calls ``transport.abort()`` which sends a TCP
        RST immediately — critical on the Elios4You because graceful FIN
        leaves the device's socket slot in CLOSE_WAIT for its (long) idle
        timeout, eventually exhausting the socket table.

        ``wait_closed()`` is always bounded by ``self._close_timeout`` so a
        misbehaving device can never hang the integration.
        """
        if self._writer is None:
            return

        writer = self._writer
        was_state = self._metrics.state
        try:
            if force_abort:
                self._metrics.forced_aborts += 1
                transport = None
                with suppress(AttributeError, OSError):
                    transport = writer.get_extra_info("transport")
                if transport is not None:
                    with suppress(Exception):
                        transport.abort()
                    log_debug(
                        _LOGGER,
                        f"{LOG_PREFIX}._close_safely",
                        "Connection aborted (RST sent)",
                        previous_state=was_state.value,
                    )
                else:
                    # No transport to abort — fall back to writer.close().
                    with suppress(Exception):
                        writer.close()
            else:
                self._metrics.graceful_closes += 1
                with suppress(Exception):
                    writer.close()
                with suppress(Exception):
                    await asyncio.wait_for(writer.wait_closed(), timeout=self._close_timeout)
                log_debug(
                    _LOGGER,
                    f"{LOG_PREFIX}._close_safely",
                    "Connection closed gracefully (FIN)",
                    previous_state=was_state.value,
                )
        finally:
            self._writer = None
            self._reader = None
            self._last_activity = 0.0
            self._metrics.last_disconnect_at = time.time()
            if self._metrics.state not in (ConnectionState.BACKOFF, ConnectionState.CLOSED):
                self._transition(ConnectionState.DISCONNECTED, reason="close")

    # ------------------------------------------------------------------ #
    # Internal: framed send / receive
    # ------------------------------------------------------------------ #

    async def _send_raw(self, cmd: str) -> str:
        """Write the command and read until the response separator."""
        assert self._writer is not None  # noqa: S101  # ensured by caller

        log_debug(
            _LOGGER,
            f"{LOG_PREFIX}._send_raw",
            "Writing command",
            cmd=cmd,
        )
        self._writer.write(cmd.lower() + "\n")
        await self._writer.drain()

        response = await self._read_until(RESPONSE_SEPARATOR, self._read_timeout)
        log_debug(
            _LOGGER,
            f"{LOG_PREFIX}._send_raw",
            "Response received",
            cmd=cmd,
            length=len(response),
            has_separator=RESPONSE_SEPARATOR in response,
        )
        return response

    async def _read_until(self, separator: str, timeout: float) -> str:
        """Read chunks until ``separator`` is in the buffer or timeout/EOF."""
        assert self._reader is not None  # noqa: S101  # ensured by caller

        buffer = ""
        loop = asyncio.get_event_loop()
        end_time = loop.time() + timeout

        while separator not in buffer:
            remaining = end_time - loop.time()
            if remaining <= 0:
                return buffer
            try:
                chunk = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=remaining,
                )
            except TimeoutError:
                return buffer
            if not chunk:
                return buffer  # EOF
            buffer += chunk

        return buffer
