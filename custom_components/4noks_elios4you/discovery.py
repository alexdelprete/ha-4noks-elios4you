"""UDP discovery of Elios4you devices.

https://github.com/alexdelprete/ha-4noks-elios4you

The device answers an undocumented discovery protocol on UDP port 5002:
sending the payload ``Elios4you`` (optionally ``Elios4you <serial>``) makes it
reply ``HELLO <serial>``. Unlike the telnet channel on TCP 5001, this endpoint
is NOT exclusive — it answers even while a telnet session is open, so probing
it never interferes with a running integration. Discovered on real hardware
while capturing the official app's traffic (PR #182 discussion).
"""

import asyncio
import logging
from typing import cast

from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PORT = 5002
DISCOVERY_PAYLOAD = b"Elios4you"
DISCOVERY_TIMEOUT = 2.0
BROADCAST_ADDR = "255.255.255.255"


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """Collect ``HELLO <serial>`` replies to a discovery broadcast."""

    def __init__(self) -> None:
        self.devices: dict[str, str] = {}  # ip -> serial

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Send the discovery broadcast as soon as the socket is ready."""
        cast(asyncio.DatagramTransport, transport).sendto(
            DISCOVERY_PAYLOAD, (BROADCAST_ADDR, DISCOVERY_PORT)
        )

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Record every device that answers with a HELLO."""
        text = data.decode(errors="replace").strip()
        if not text.startswith("HELLO"):
            return
        parts = text.split()
        self.devices[addr[0]] = parts[1] if len(parts) > 1 else ""


async def async_discover_devices(timeout: float = DISCOVERY_TIMEOUT) -> dict[str, str]:
    """Broadcast a discovery probe and return ``{ip: serial}`` of responders.

    The full timeout window is always waited, so multiple devices on the
    network are all collected. Returns an empty dict when broadcasting is not
    possible (no network, sandboxed environment) — discovery is best-effort
    and never blocks manual configuration.
    """
    loop = asyncio.get_running_loop()
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            _DiscoveryProtocol,
            local_addr=("0.0.0.0", 0),  # noqa: S104 - broadcast source socket
            allow_broadcast=True,
        )
    except OSError as err:
        log_debug(_LOGGER, "async_discover_devices", "Broadcast unavailable", error=str(err))
        return {}
    try:
        await asyncio.sleep(timeout)
    finally:
        transport.close()
    log_debug(
        _LOGGER,
        "async_discover_devices",
        "Discovery finished",
        found=len(protocol.devices),
    )
    return dict(protocol.devices)
