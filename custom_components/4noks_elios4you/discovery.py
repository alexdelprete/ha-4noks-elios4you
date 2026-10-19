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

# Liveness probe tuning. Field data (PR #182): healthy replies take ~260 ms
# median / 764 ms max, but replies arriving only on the 2nd attempt were
# observed during telnet outages, so a single shot is not enough.
PROBE_ATTEMPTS = 3
PROBE_TIMEOUT = 1.5


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


class _ProbeProtocol(asyncio.DatagramProtocol):
    """Resolve a future with the serial of the first ``HELLO`` reply."""

    def __init__(self) -> None:
        self.reply: asyncio.Future[str] = asyncio.get_running_loop().create_future()

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Resolve on the first HELLO; ignore anything else."""
        text = data.decode(errors="replace").strip()
        if not text.startswith("HELLO") or self.reply.done():
            return
        parts = text.split()
        self.reply.set_result(parts[1] if len(parts) > 1 else "")

    def error_received(self, exc: Exception) -> None:
        """ICMP errors (e.g. port unreachable) just mean no reply this attempt."""
        log_debug(_LOGGER, "_ProbeProtocol.error_received", "Probe error", error=str(exc))


async def async_probe_device(
    host: str, attempts: int = PROBE_ATTEMPTS, timeout: float = PROBE_TIMEOUT
) -> str | None:
    """Ask a known device whether it is alive on UDP 5002.

    Sends the discovery payload unicast to ``host`` up to ``attempts`` times,
    waiting ``timeout`` seconds for a reply after each send. Returns the serial
    from the ``HELLO`` reply (``""`` if the reply carries none), or ``None``
    when the device stayed silent or the probe could not be sent at all.

    UDP 5002 keeps answering while the telnet service on TCP 5001 is wedged,
    so a reply here tells "alive but telnet deaf" apart from "off the
    network". ICMP is not a substitute: field captures showed ping timing out
    while UDP answered.
    """
    loop = asyncio.get_running_loop()
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            _ProbeProtocol, remote_addr=(host, DISCOVERY_PORT)
        )
    except OSError as err:
        log_debug(_LOGGER, "async_probe_device", "Probe unavailable", host=host, error=str(err))
        return None
    try:
        for attempt in range(1, attempts + 1):
            transport.sendto(DISCOVERY_PAYLOAD)
            try:
                serial = await asyncio.wait_for(asyncio.shield(protocol.reply), timeout)
            except TimeoutError:
                continue
            log_debug(_LOGGER, "async_probe_device", "Device answered", host=host, attempt=attempt)
            return serial
    finally:
        transport.close()
    log_debug(_LOGGER, "async_probe_device", "No answer", host=host, attempts=attempts)
    return None


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
