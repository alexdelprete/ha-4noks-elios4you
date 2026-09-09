"""Tests for 4-noks Elios4you UDP discovery module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.discovery import (
    BROADCAST_ADDR,
    DISCOVERY_PAYLOAD,
    DISCOVERY_PORT,
    _DiscoveryProtocol,
    async_discover_devices,
)


class TestDiscoveryProtocol:
    """The datagram protocol collects HELLO replies and ignores noise."""

    def _transport(self) -> MagicMock:
        return MagicMock(spec=asyncio.DatagramTransport)

    def test_broadcast_sent_on_connection(self) -> None:
        """The probe payload goes out as soon as the socket is ready."""
        protocol = _DiscoveryProtocol()
        transport = self._transport()

        protocol.connection_made(transport)

        transport.sendto.assert_called_once_with(
            DISCOVERY_PAYLOAD, (BROADCAST_ADDR, DISCOVERY_PORT)
        )

    def test_hello_reply_is_recorded_with_serial(self) -> None:
        """``HELLO <serial>`` maps the sender IP to the serial."""
        protocol = _DiscoveryProtocol()

        protocol.datagram_received(b"HELLO 5ED47C7F", ("192.168.1.50", DISCOVERY_PORT))

        assert protocol.devices == {"192.168.1.50": "5ED47C7F"}

    def test_bare_hello_is_recorded_without_serial(self) -> None:
        """A HELLO without serial still counts as a discovered device."""
        protocol = _DiscoveryProtocol()

        protocol.datagram_received(b"HELLO", ("192.168.1.51", DISCOVERY_PORT))

        assert protocol.devices == {"192.168.1.51": ""}

    def test_non_hello_traffic_is_ignored(self) -> None:
        """Anything that is not a HELLO reply is dropped."""
        protocol = _DiscoveryProtocol()

        protocol.datagram_received(b"@dat", ("192.168.1.52", DISCOVERY_PORT))
        protocol.datagram_received(b"\xff\xfe", ("192.168.1.53", DISCOVERY_PORT))

        assert protocol.devices == {}


class TestAsyncDiscoverDevices:
    """The discovery coroutine wraps the protocol in a broadcast endpoint."""

    @pytest.mark.asyncio
    async def test_discovery_collects_responders(self, monkeypatch) -> None:
        """Devices answering within the window are returned as ip->serial."""
        transport = MagicMock(spec=asyncio.DatagramTransport)

        async def fake_endpoint(factory, **kwargs):
            protocol = factory()
            protocol.connection_made(transport)
            protocol.datagram_received(b"HELLO 5ED47C7F", ("192.168.1.50", DISCOVERY_PORT))
            return transport, protocol

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "create_datagram_endpoint", fake_endpoint)

        devices = await async_discover_devices(timeout=0)

        assert devices == {"192.168.1.50": "5ED47C7F"}
        transport.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovery_returns_empty_when_broadcast_unavailable(self, monkeypatch) -> None:
        """No network / sandboxed environment: best-effort empty result."""

        async def fake_endpoint(factory, **kwargs):
            raise OSError("Network is unreachable")

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "create_datagram_endpoint", fake_endpoint)

        assert await async_discover_devices(timeout=0) == {}
