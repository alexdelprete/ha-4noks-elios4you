"""Tests for the ConnectionManager state machine.

Covers:
* state transitions (DISCONNECTED ↔ CONNECTING ↔ READY ↔ BACKOFF, terminal CLOSED)
* connection reuse within the reuse window
* RST close on error paths, FIN close on graceful unload
* retry logic on silent timeouts
* backoff behavior after consecutive failures, including exponential growth
* metrics_snapshot() exposing the data we surface as diagnostic sensors
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.fournoks_elios4you.connection_manager import (
    RESPONSE_SEPARATOR,
    ConnectionManager,
    ConnectionState,
    ConnectionUnavailableError,
    TelnetCommandError,
    TelnetConnectionError,
    _RetryableError,
)
import pytest

TEST_HOST = "192.168.1.100"
TEST_PORT = 5001


def _make_writer() -> MagicMock:
    """Return a MagicMock that quacks like a telnetlib3 writer."""
    writer = MagicMock()
    writer.is_closing = MagicMock(return_value=False)
    transport = MagicMock()
    transport.is_closing = MagicMock(return_value=False)
    transport.abort = MagicMock()
    writer.get_extra_info = MagicMock(return_value=transport)
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    return writer


def _make_reader(chunks: list[str]) -> MagicMock:
    """Return a reader that emits each chunk on successive ``read()`` calls."""
    reader = MagicMock()
    iterator = iter(chunks)

    async def _read(_size: int) -> str:
        try:
            return next(iterator)
        except StopIteration:
            return ""  # EOF

    reader.read = _read
    return reader


# ---------------------------------------------------------------------- #
# Construction / initial state
# ---------------------------------------------------------------------- #


def test_initial_state_is_disconnected() -> None:
    """A fresh manager starts DISCONNECTED with zeroed counters."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    assert mgr.state is ConnectionState.DISCONNECTED
    snap = mgr.metrics_snapshot()
    assert snap["state"] == "disconnected"
    assert snap["commands_sent"] == 0
    assert snap["consecutive_failures"] == 0


def test_metrics_snapshot_includes_derived_fields() -> None:
    """``backoff_seconds_remaining`` and ``state_age_seconds`` are derived."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    snap = mgr.metrics_snapshot()
    assert "backoff_seconds_remaining" in snap
    assert "state_age_seconds" in snap


# ---------------------------------------------------------------------- #
# execute() happy path
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_execute_opens_connection_and_returns_response() -> None:
    """First execute() opens the connection and returns the raw response."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    reader = _make_reader([f"@dat\n0;key;val\n\n{RESPONSE_SEPARATOR}"])
    writer = _make_writer()

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        return_value=(reader, writer),
    ):
        raw = await mgr.execute("@dat")

    assert RESPONSE_SEPARATOR in raw
    assert mgr.state is ConnectionState.READY
    assert mgr.metrics.connects_succeeded == 1
    assert mgr.metrics.commands_sent == 1
    assert mgr.metrics.consecutive_failures == 0


@pytest.mark.asyncio
async def test_execute_reuses_connection_within_window() -> None:
    """A second execute() within the reuse window does not re-open."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, reuse_window=60.0)
    reader = _make_reader(
        [
            f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}",
            f"@sta\n0;b;2\n\n{RESPONSE_SEPARATOR}",
        ]
    )
    writer = _make_writer()

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        return_value=(reader, writer),
    ) as open_conn:
        await mgr.execute("@dat")
        await mgr.execute("@sta")

    assert open_conn.call_count == 1
    assert mgr.metrics.reuse_hits == 1
    assert mgr.metrics.connects_succeeded == 1


# ---------------------------------------------------------------------- #
# Error paths: silent timeout + retries
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_silent_timeout_triggers_retry_then_succeeds() -> None:
    """First attempt returns no separator → RST + reconnect → second succeeds."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, max_retries=1, retry_delay=0.0)

    # First reader returns garbage without separator, second returns valid.
    reader_bad = _make_reader(["garbage_no_separator"])
    reader_good = _make_reader([f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}"])
    writer1 = _make_writer()
    writer2 = _make_writer()

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        side_effect=[(reader_bad, writer1), (reader_good, writer2)],
    ) as open_conn:
        raw = await mgr.execute("@dat")

    assert RESPONSE_SEPARATOR in raw
    assert open_conn.call_count == 2
    assert mgr.metrics.silent_timeouts == 1
    assert mgr.metrics.forced_aborts == 1
    assert mgr.metrics.commands_retried == 1
    # First writer's transport got aborted (RST) — that's the device-friendly fix
    writer1.get_extra_info.return_value.abort.assert_called_once()
    assert mgr.state is ConnectionState.READY


@pytest.mark.asyncio
async def test_silent_timeout_all_retries_fail_raises() -> None:
    """If every attempt silently times out, raise TelnetCommandError."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, max_retries=1, retry_delay=0.0)

    reader1 = _make_reader(["garbage"])
    reader2 = _make_reader(["more garbage"])
    writer1 = _make_writer()
    writer2 = _make_writer()

    with (
        patch(
            "telnetlib3.open_connection",
            new_callable=AsyncMock,
            side_effect=[(reader1, writer1), (reader2, writer2)],
        ),
        pytest.raises(TelnetCommandError),
    ):
        await mgr.execute("@dat")

    assert mgr.metrics.silent_timeouts == 2
    assert mgr.metrics.commands_failed == 1
    assert mgr.metrics.consecutive_failures == 1


@pytest.mark.asyncio
async def test_transport_error_during_send_is_retried() -> None:
    """Drain raising OSError on first attempt is a retryable failure."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, max_retries=1, retry_delay=0.0)

    reader = _make_reader([f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}"])
    writer_bad = _make_writer()
    writer_bad.drain = AsyncMock(side_effect=OSError("broken pipe"))
    writer_good = _make_writer()

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        side_effect=[(reader, writer_bad), (reader, writer_good)],
    ):
        raw = await mgr.execute("@dat")

    assert RESPONSE_SEPARATOR in raw
    assert mgr.metrics.commands_retried == 1
    assert mgr.metrics.forced_aborts == 1


# ---------------------------------------------------------------------- #
# Connect failures
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_connect_timeout_raises_telnet_connection_error() -> None:
    """All connect attempts timing out raises TelnetConnectionError."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, max_retries=0, retry_delay=0.0)

    with (
        patch(
            "telnetlib3.open_connection",
            new_callable=AsyncMock,
            side_effect=TimeoutError("timed out"),
        ),
        pytest.raises(TelnetConnectionError),
    ):
        await mgr.execute("@dat")

    assert mgr.metrics.connect_failures == 1
    assert mgr.metrics.consecutive_failures == 1
    assert mgr.state is ConnectionState.DISCONNECTED


# ---------------------------------------------------------------------- #
# Backoff behavior
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_consecutive_failures_enter_backoff() -> None:
    """Reaching the threshold transitions to BACKOFF and refuses new calls."""
    mgr = ConnectionManager(
        TEST_HOST,
        TEST_PORT,
        max_retries=0,
        retry_delay=0.0,
        backoff_threshold=3,
        backoff_initial=10.0,
        backoff_max=10.0,
    )

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        side_effect=TimeoutError("nope"),
    ):
        for _ in range(3):
            with pytest.raises(TelnetConnectionError):
                await mgr.execute("@dat")

    assert mgr.state is ConnectionState.BACKOFF
    assert mgr.metrics.consecutive_failures == 3
    assert mgr.metrics.backoff_entries == 1

    # Fourth call should be rejected immediately without touching the network
    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
    ) as open_conn:
        with pytest.raises(ConnectionUnavailableError):
            await mgr.execute("@dat")
        open_conn.assert_not_called()


@pytest.mark.asyncio
async def test_backoff_expires_and_allows_trial() -> None:
    """Once the backoff window passes, the next execute() is allowed through."""
    mgr = ConnectionManager(
        TEST_HOST,
        TEST_PORT,
        max_retries=0,
        retry_delay=0.0,
        backoff_threshold=1,
        backoff_initial=0.01,
        backoff_max=0.01,
    )

    # One failure -> immediate BACKOFF (threshold=1)
    with (
        patch(
            "telnetlib3.open_connection",
            new_callable=AsyncMock,
            side_effect=TimeoutError("nope"),
        ),
        pytest.raises(TelnetConnectionError),
    ):
        await mgr.execute("@dat")
    assert mgr.state is ConnectionState.BACKOFF

    # Wait for the (very short) backoff to expire
    await asyncio.sleep(0.02)

    # Next call should be allowed and succeed
    reader = _make_reader([f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}"])
    writer = _make_writer()
    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        return_value=(reader, writer),
    ):
        raw = await mgr.execute("@dat")

    assert RESPONSE_SEPARATOR in raw
    assert mgr.state is ConnectionState.READY
    assert mgr.metrics.consecutive_failures == 0  # reset on success


@pytest.mark.asyncio
async def test_backoff_duration_grows_exponentially() -> None:
    """Each failure past the threshold doubles the backoff window, capped at max."""
    mgr = ConnectionManager(
        TEST_HOST,
        TEST_PORT,
        max_retries=0,
        retry_delay=0.0,
        backoff_threshold=1,
        backoff_initial=1.0,
        backoff_max=8.0,
    )

    durations: list[float] = []
    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        side_effect=TimeoutError("nope"),
    ):
        for _ in range(5):
            # Reset backoff_until each iteration so we always proceed
            mgr.metrics.backoff_until = 0.0
            with pytest.raises(TelnetConnectionError):
                await mgr.execute("@dat")
            durations.append(mgr.metrics.current_backoff_duration)

    # 1, 2, 4, 8, 8 (capped)
    assert durations == [1.0, 2.0, 4.0, 8.0, 8.0]


# ---------------------------------------------------------------------- #
# Closing
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_close_transitions_to_terminal_state() -> None:
    """close() transitions to CLOSED and uses graceful FIN."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    reader = _make_reader([f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}"])
    writer = _make_writer()

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        return_value=(reader, writer),
    ):
        await mgr.execute("@dat")

    await mgr.close()

    assert mgr.state is ConnectionState.CLOSED
    # Graceful FIN was used (close + wait_closed), not abort
    writer.close.assert_called()
    writer.wait_closed.assert_awaited()
    assert mgr.metrics.graceful_closes == 1
    assert mgr.metrics.forced_aborts == 0


@pytest.mark.asyncio
async def test_close_then_execute_raises() -> None:
    """A closed manager refuses further work."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    await mgr.close()

    with pytest.raises(ConnectionUnavailableError):
        await mgr.execute("@dat")


@pytest.mark.asyncio
async def test_close_handles_missing_writer() -> None:
    """Closing without ever connecting is a no-op."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    await mgr.close()  # should not raise
    assert mgr.state is ConnectionState.CLOSED


@pytest.mark.asyncio
async def test_close_wait_closed_timeout_does_not_hang() -> None:
    """A hung wait_closed() is bounded by close_timeout and does not block."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, close_timeout=0.05)
    reader = _make_reader([f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}"])
    writer = _make_writer()

    async def _never_closes() -> None:
        await asyncio.sleep(60)

    writer.wait_closed = AsyncMock(side_effect=_never_closes)

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        return_value=(reader, writer),
    ):
        await mgr.execute("@dat")

    # If this returns at all (within the test timeout), the bound worked.
    await asyncio.wait_for(mgr.close(), timeout=1.0)
    assert mgr.state is ConnectionState.CLOSED


# ---------------------------------------------------------------------- #
# _RetryableError sanity (internal type)
# ---------------------------------------------------------------------- #


def test_retryable_error_keeps_reason() -> None:
    """The internal _RetryableError preserves its reason."""
    err = _RetryableError("some reason")
    assert err.reason == "some reason"
    assert str(err) == "some reason"


# ---------------------------------------------------------------------- #
# State machine internals (_transition)
# ---------------------------------------------------------------------- #


def test_transition_to_same_state_is_noop() -> None:
    """Transitioning to the current state should not bump state_since."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    before = mgr.metrics.state_since
    mgr._transition(ConnectionState.DISCONNECTED, reason="self-loop")
    assert mgr.metrics.state_since == before


# ---------------------------------------------------------------------- #
# _can_reuse() branches
# ---------------------------------------------------------------------- #


def test_can_reuse_false_when_writer_is_closing() -> None:
    """A closing writer means we cannot reuse the connection."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    writer = _make_writer()
    writer.is_closing = MagicMock(return_value=True)
    mgr._writer = writer
    mgr._last_activity = __import__("time").time()
    assert mgr._can_reuse() is False


def test_can_reuse_false_when_transport_is_closing() -> None:
    """A writer that's open but whose transport is closing is not reusable."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    writer = _make_writer()
    writer.get_extra_info.return_value.is_closing = MagicMock(return_value=True)
    mgr._writer = writer
    mgr._last_activity = __import__("time").time()
    assert mgr._can_reuse() is False


def test_can_reuse_false_on_exception_during_check() -> None:
    """OSError while inspecting the writer means we should not trust it."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    writer = MagicMock()
    writer.is_closing = MagicMock(side_effect=OSError("boom"))
    mgr._writer = writer
    assert mgr._can_reuse() is False


def test_can_reuse_false_when_age_exceeds_reuse_window() -> None:
    """A writer older than reuse_window is dropped (logs and returns False)."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, reuse_window=1.0)
    mgr._writer = _make_writer()
    mgr._last_activity = 0.0  # epoch — definitely older than 1 second
    assert mgr._can_reuse() is False


@pytest.mark.asyncio
async def test_ensure_connected_closes_stale_writer_first() -> None:
    """When the reuse window has expired, the old socket is aborted before reconnect."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT, reuse_window=1.0)
    stale = _make_writer()
    mgr._writer = stale
    mgr._reader = _make_reader([])
    mgr._last_activity = 0.0  # forces _can_reuse() → False via age check

    new_reader = _make_reader([f"@dat\n0;a;1\n\n{RESPONSE_SEPARATOR}"])
    new_writer = _make_writer()

    with patch(
        "telnetlib3.open_connection",
        new_callable=AsyncMock,
        return_value=(new_reader, new_writer),
    ):
        await mgr.execute("@dat")

    # Stale writer's transport was aborted (RST), then a new connection opened.
    stale.get_extra_info.return_value.abort.assert_called_once()
    assert mgr._writer is new_writer


# ---------------------------------------------------------------------- #
# _close_safely fallback
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_close_safely_force_abort_without_transport_falls_back_to_close() -> None:
    """If there's no underlying transport, abort falls back to writer.close()."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    writer = _make_writer()
    writer.get_extra_info = MagicMock(return_value=None)  # no transport
    mgr._writer = writer
    mgr._reader = _make_reader([])

    await mgr._close_safely(force_abort=True)

    # No transport to abort → writer.close() called as fallback.
    writer.close.assert_called_once()
    assert mgr._writer is None
    assert mgr.metrics.forced_aborts == 1


# ---------------------------------------------------------------------- #
# _read_until edge cases
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_read_until_returns_partial_on_zero_remaining() -> None:
    """If the read budget is already exhausted before the first read, return what we have."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)
    mgr._reader = _make_reader(["never read"])
    # Negative timeout → remaining <= 0 on first iteration → bail out
    result = await mgr._read_until(RESPONSE_SEPARATOR, timeout=-1.0)
    assert result == ""


@pytest.mark.asyncio
async def test_read_until_handles_timeout_error_from_wait_for() -> None:
    """A TimeoutError from asyncio.wait_for inside the loop returns the partial buffer."""
    mgr = ConnectionManager(TEST_HOST, TEST_PORT)

    async def _slow_read(_size: int) -> str:
        await asyncio.sleep(60)
        return "should not get here"

    reader = MagicMock()
    reader.read = _slow_read
    mgr._reader = reader

    result = await mgr._read_until(RESPONSE_SEPARATOR, timeout=0.05)
    assert RESPONSE_SEPARATOR not in result
