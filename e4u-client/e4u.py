# ruff: noqa: INP001
"""Elios4you standalone test client.

This is a self-contained reference for the wire protocol the integration's
:mod:`connection_manager` speaks. It is **not** the manager — there is no
state machine, no reuse window, no backoff. The script is intentionally
one-shot: it opens one connection, runs five commands sequentially, then
tears the connection down. That is sufficient for "is my device reachable
and what does it say right now?" probing.

Patterns mirrored from ``connection_manager.py``:

* ``RESPONSE_SEPARATOR`` constant rather than inline string literals.
* ``_read_until`` / ``_send_raw`` helper shape and return semantics.
* ``open_connection`` is wrapped in ``asyncio.wait_for`` with a connect
  timeout so a slow / dead device cannot hang the script.
* ``wait_closed`` is bounded by ``CLOSE_TIMEOUT`` so a misbehaving device
  cannot hang the script during shutdown either.
* The error close path uses ``transport.abort()`` (TCP RST) so the device
  frees its socket slot immediately, exactly like the manager does. Only
  the normal end-of-script close goes through the graceful FIN path.

Usage::

    python e4u.py
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

import telnetlib3

# --- Configuration ---------------------------------------------------------
HOST = "elios4u.axel.dom"  # IP or hostname
PORT = 5001  # Elios4You default telnet port
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 5.0
CLOSE_TIMEOUT = 2.0
RESPONSE_SEPARATOR = "ready..."
# Aggressive negotiation timing — Elios4You doesn't really negotiate telnet
# options, so we don't wait long for it.
CONNECT_MINWAIT = 0.1
CONNECT_MAXWAIT = 0.5


# --- Wire helpers ----------------------------------------------------------


async def _read_until(
    reader: telnetlib3.TelnetReaderUnicode,
    separator: str,
    timeout: float,
) -> str:
    """Read chunks until ``separator`` appears in the buffer or timeout/EOF.

    Mirrors ``ConnectionManager._read_until``: returns the partial buffer
    on either timeout or EOF rather than raising.
    """
    buffer = ""
    loop = asyncio.get_event_loop()
    end_time = loop.time() + timeout

    while separator not in buffer:
        remaining = end_time - loop.time()
        if remaining <= 0:
            print(f"timeout waiting for separator (buffer_len={len(buffer)})")  # noqa: T201
            return buffer
        try:
            chunk = await asyncio.wait_for(reader.read(1024), timeout=remaining)
        except TimeoutError:
            print(f"read timed out (buffer_len={len(buffer)})")  # noqa: T201
            return buffer
        if not chunk:
            print(f"EOF received (buffer_len={len(buffer)})")  # noqa: T201
            return buffer
        buffer += chunk

    return buffer


async def _send_raw(
    cmd: str,
    reader: telnetlib3.TelnetReaderUnicode,
    writer: telnetlib3.TelnetWriterUnicode,
) -> str:
    """Write ``cmd`` and return the raw response (or empty string on failure).

    Mirrors ``ConnectionManager._send_raw``.
    """
    writer.write(cmd.lower() + "\n")
    await writer.drain()
    return await _read_until(reader, RESPONSE_SEPARATOR, READ_TIMEOUT)


def _parse(cmd: str, raw: str) -> dict[str, str]:
    """Parse the device's response.

    * ``@inf`` / ``@rel`` / ``@hwr`` use ``key=value`` lines
    * ``@dat`` / ``@sta`` use ``index;key;value;...`` lines

    Skips the echoed command, the trailing blank line, and the
    ``RESPONSE_SEPARATOR`` marker.
    """
    cmd_main = cmd[0:4].lower()
    lines = raw.splitlines()

    if lines and lines[0].lower() in ("@dat", "@sta", "@inf", "@rel", "@hwr"):
        lines_start = 1
    else:
        lines_start = 2
    lines_end = -2

    out: dict[str, str] = {}
    for line in lines[lines_start:lines_end]:
        try:
            if cmd_main in ("@inf", "@rel", "@hwr"):
                key, value = line.split("=")
            else:
                key, value = line.split(";")[1:3]
            out[key.lower().replace(" ", "_")] = value.strip()
        except ValueError:
            print(f"parse error: {line!r}")  # noqa: T201
    return out


async def send_command(
    cmd: str,
    reader: telnetlib3.TelnetReaderUnicode,
    writer: telnetlib3.TelnetWriterUnicode,
) -> dict[str, str]:
    """Send ``cmd`` and return the parsed response dict (empty on failure)."""
    response = await _send_raw(cmd, reader, writer)
    if not response or RESPONSE_SEPARATOR not in response:
        print(f"silent timeout for {cmd}")  # noqa: T201
        return {}
    return _parse(cmd, response)


# --- Connection lifecycle --------------------------------------------------


async def _close(
    writer: telnetlib3.TelnetWriterUnicode | None,
    *,
    force_abort: bool,
) -> None:
    """Close the connection. RST on error paths, FIN on normal exit.

    Mirrors ``ConnectionManager._close_safely``.
    """
    if writer is None:
        return
    if force_abort:
        transport = None
        with suppress(AttributeError, OSError):
            transport = writer.get_extra_info("transport")
        if transport is not None:
            with suppress(Exception):
                transport.abort()  # immediate TCP RST
            print("connection aborted (RST sent)")  # noqa: T201
            return
        # No transport to abort — fall back to writer.close()
    with suppress(Exception):
        writer.close()
    with suppress(Exception):
        await asyncio.wait_for(writer.wait_closed(), timeout=CLOSE_TIMEOUT)
    print("connection closed gracefully (FIN)")  # noqa: T201


async def main() -> None:
    """Open one connection, dump every command, close."""
    reader: telnetlib3.TelnetReaderUnicode | None = None
    writer: telnetlib3.TelnetWriterUnicode | None = None
    error_path = False

    try:
        print(f"connecting to {HOST}:{PORT}...")  # noqa: T201
        reader, writer = await asyncio.wait_for(
            telnetlib3.open_connection(
                host=HOST,
                port=PORT,
                encoding="utf-8",
                encoding_errors="replace",
                connect_minwait=CONNECT_MINWAIT,
                connect_maxwait=CONNECT_MAXWAIT,
            ),
            timeout=CONNECT_TIMEOUT,
        )
        print("connected\n")  # noqa: T201

        for cmd in ("@dat", "@sta", "@inf", "@rel", "@hwr"):
            parsed = await send_command(cmd, reader, writer)
            print(f"\n -= {cmd.upper()[1:]} =-")  # noqa: T201
            for key, value in parsed.items():
                print(f"  {key}: {value}")  # noqa: T201
        print()  # noqa: T201

    except TimeoutError:
        print("connection or operation timed out")  # noqa: T201
        error_path = True
    except Exception as e:  # noqa: BLE001
        print(f"unexpected error: {e!s}")  # noqa: T201
        error_path = True
    finally:
        await _close(writer, force_abort=error_path)


if __name__ == "__main__":
    asyncio.run(main())
