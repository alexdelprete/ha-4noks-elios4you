"""UDP discovery of Elios4you devices.

https://github.com/alexdelprete/ha-4noks-elios4you

The device answers an undocumented discovery protocol on UDP port 5002:
sending the payload ``Elios4you`` (optionally ``Elios4you <serial>``) makes it
reply ``HELLO <serial>``. It answers even while a telnet session is open, so
probing it never interferes with a running integration. (Telnet on TCP 5001
is not exclusive either: a second session connects while the integration is
polling -- 152 of 152 attempts on real hardware.) Discovered on real hardware
while capturing the official app's traffic (PR #182 discussion).
"""

import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any, cast

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_MAC, DOMAIN
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PORT = 5002
DISCOVERY_PAYLOAD = b"Elios4you"
DISCOVERY_TIMEOUT = 2.0
BROADCAST_ADDR = "255.255.255.255"

# Key carrying the serial in integration-discovery flow data.
DISCOVERY_SERIAL = "serial"
# How often a loaded integration re-broadcasts to find additional devices
# (and devices with a static IP, which the DHCP matcher never sees).
DISCOVERY_INTERVAL = timedelta(minutes=15)

# Kernel neighbour table: after a UDP exchange with a device on the same LAN
# segment it maps the device's IP to its MAC. A device behind a router (or HA
# in bridge-mode Docker) simply has no entry, so no MAC is ever guessed.
ARP_TABLE = "/proc/net/arp"
ARP_FLAG_COMPLETE = 0x2

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


def _read_arp_table() -> dict[str, str]:
    """Return ``{ip: mac}`` for the complete entries of the kernel ARP table."""
    try:
        lines = Path(ARP_TABLE).read_text(encoding="ascii").splitlines()[1:]  # skip header
    except OSError:
        return {}
    table: dict[str, str] = {}
    for line in lines:
        # IP address, HW type, Flags, HW address, Mask, Device
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            complete = int(parts[2], 16) & ARP_FLAG_COMPLETE
        except ValueError:
            continue
        if complete:
            table[parts[0]] = format_mac(parts[3])
    return table


async def async_lookup_macs(hass: HomeAssistant, hosts: list[str]) -> dict[str, str]:
    """Resolve each host's MAC from the ARP table; ``{ip: mac}`` for those found.

    A host missing from the table gets one unicast probe first, which makes the
    kernel resolve it if it is on the local segment.
    """
    table = await hass.async_add_executor_job(_read_arp_table)
    missing = [host for host in hosts if host not in table]
    if missing:
        await asyncio.gather(*(async_probe_device(host, attempts=1) for host in missing))
        table = await hass.async_add_executor_job(_read_arp_table)
    return {host: table[host] for host in hosts if host in table}


@callback
def async_trigger_discovery(
    hass: HomeAssistant, devices: dict[str, str], macs: dict[str, str] | None = None
) -> None:
    """Start an integration-discovery flow for each device not yet configured.

    A device already configured at the same host is skipped -- to avoid a flow
    per device every interval -- unless its entry still lacks the MAC that the
    ARP lookup just found. Everything else (new devices, known devices at a new
    IP) goes to the config flow, which deduplicates by serial.
    """
    macs = macs or {}
    entries = {
        (entry.unique_id, entry.data.get(CONF_HOST)): entry
        for entry in hass.config_entries.async_entries(DOMAIN)
    }
    for host, serial in devices.items():
        if not serial:
            continue
        entry = entries.get((serial, host))
        if entry is not None and (entry.data.get(CONF_MAC) or host not in macs):
            continue
        data = {CONF_HOST: host, DISCOVERY_SERIAL: serial}
        if host in macs:
            data[CONF_MAC] = macs[host]
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=data,
        )


@callback
def async_start_discovery(hass: HomeAssistant) -> None:
    """Broadcast now and every DISCOVERY_INTERVAL while HA runs."""

    async def _async_discover(*_: Any) -> None:
        devices = await async_discover_devices()
        macs = await async_lookup_macs(hass, list(devices)) if devices else {}
        async_trigger_discovery(hass, devices, macs)

    hass.async_create_background_task(_async_discover(), f"{DOMAIN}-discovery")
    async_track_time_interval(hass, _async_discover, DISCOVERY_INTERVAL, cancel_on_shutdown=True)
