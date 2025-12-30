# ruff: noqa: INP001
"""Elios4you Test Client.

Standalone test client aligned with the main integration's api.py implementation.
Uses telnetlib3 for fully async I/O.

Usage:
    python e4u.py
"""

import asyncio
from contextlib import suppress

import telnetlib3

# Configuration
HOST = "elios4u.axel.dom"  # IP or hostname
PORT = 5001  # Elios4You default port
TIMEOUT = 5  # Connection and read timeout in seconds


async def async_read_until(
    reader: telnetlib3.TelnetReaderUnicode,
    separator: str,
    timeout: float,
) -> str:
    """Async read until separator found or timeout.

    Aligned with api.py _async_read_until() implementation.

    Args:
        reader: telnetlib3 reader stream
        separator: String sequence to wait for (e.g., "ready...")
        timeout: Maximum seconds to wait

    Returns:
        Buffer containing data up to and including separator,
        or partial data if timeout/EOF occurs.
    """
    buffer = ""
    loop = asyncio.get_event_loop()
    end_time = loop.time() + timeout

    while separator not in buffer:
        remaining = end_time - loop.time()
        if remaining <= 0:
            print(f"Timeout waiting for separator, buffer_len={len(buffer)}")  # noqa: T201
            return buffer  # Timeout - return partial

        try:
            chunk = await asyncio.wait_for(
                reader.read(1024),
                timeout=remaining,
            )
            if not chunk:
                print(f"EOF received, buffer_len={len(buffer)}")  # noqa: T201
                return buffer  # EOF
            buffer += chunk
        except TimeoutError:
            print(f"asyncio.TimeoutError during read, buffer_len={len(buffer)}")  # noqa: T201
            return buffer

    return buffer


async def send_command(
    cmd: str,
    reader: telnetlib3.TelnetReaderUnicode,
    writer: telnetlib3.TelnetWriterUnicode,
) -> dict:
    """Send command and read response asynchronously.

    Aligned with api.py _async_send_command() implementation.

    Args:
        cmd: Command to send (e.g., "@dat", "@sta", "@inf", "@rel", "@hwr")
        reader: telnetlib3 reader stream
        writer: telnetlib3 writer stream

    Returns:
        Parsed response dict
    """
    data = {}
    separator = "ready..."
    cmd_main = cmd[0:4].lower()
    cmd_send = cmd.lower()

    # Send command with newline
    writer.write(cmd_send + "\n")
    await writer.drain()

    # Read until separator
    response = await async_read_until(reader, separator, TIMEOUT)

    if not response:
        print("Response empty")  # noqa: T201
        return data

    # Check for silent timeout - incomplete response without separator
    if separator not in response:
        print(f"Silent timeout - incomplete response (len={len(response)})")  # noqa: T201
        return data

    # Parse response
    lines = response.splitlines()

    # Sometimes the first line is not the command but a line-feed
    lines_start = 1 if lines[0].lower() in ["@dat", "@sta", "@inf", "@rel", "@hwr"] else 2

    # Skip last two lines (line-feed and read_until separator)
    lines_end = -2

    # Parse key-value pairs
    for line in lines[lines_start:lines_end]:
        try:
            if cmd_main in ["@inf", "@rel", "@hwr"]:
                # @inf/@rel/@hwr data uses "=" separator
                key, value = line.split("=")
            else:
                # @dat and @sta share the same data format with ";" separator
                key, value = line.split(";")[1:3]
            data[key.lower().replace(" ", "_")] = value.strip()
        except ValueError:
            print(f"Error parsing line: {line}")  # noqa: T201

    return data


async def main() -> None:
    """Main entry point."""
    reader: telnetlib3.TelnetReaderUnicode | None = None
    writer: telnetlib3.TelnetWriterUnicode | None = None

    try:
        print(f"Connecting to {HOST}:{PORT}...")  # noqa: T201

        # Open connection with same options as api.py
        reader, writer = await asyncio.wait_for(
            telnetlib3.open_connection(
                host=HOST,
                port=PORT,
                encoding="utf-8",
                encoding_errors="replace",
                connect_minwait=0.1,  # Don't wait for telnet negotiation
                connect_maxwait=0.5,  # Quick timeout on negotiation
            ),
            timeout=TIMEOUT,
        )

        print("Connected!\n")  # noqa: T201

        # Fetch all data types
        commands = ["@dat", "@sta", "@inf", "@rel", "@hwr"]
        for cmd in commands:
            parsed = await send_command(cmd, reader, writer)
            print(f"\n -= {cmd.upper()[1:]} =-")  # noqa: T201
            for key, value in parsed.items():
                print(f"  {key}: {value}")  # noqa: T201

        print("\n")  # noqa: T201

    except TimeoutError:
        print("Connection or operation timed out")  # noqa: T201

    except Exception as e:  # noqa: BLE001
        print(f"An error occurred: {e!s}")  # noqa: T201

    finally:
        # Proper close handling aligned with api.py _safe_close()
        if writer is not None:
            with suppress(Exception):
                writer.close()
                await writer.wait_closed()
            print("Connection closed")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
