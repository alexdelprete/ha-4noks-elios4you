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
    PROBE_ATTEMPTS,
    _DiscoveryProtocol,
    _ProbeProtocol,
    async_discover_devices,
    async_probe_device,
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


class TestProbeProtocol:
    """The probe protocol resolves on the first HELLO reply."""

    @pytest.mark.asyncio
    async def test_hello_resolves_with_serial(self) -> None:
        """``HELLO <serial>`` resolves the reply future with the serial."""
        protocol = _ProbeProtocol()

        protocol.datagram_received(b"HELLO 5ED47C7F", ("192.168.1.50", DISCOVERY_PORT))

        assert protocol.reply.result() == "5ED47C7F"

    @pytest.mark.asyncio
    async def test_bare_hello_resolves_empty(self) -> None:
        """A HELLO without serial still proves the device is alive."""
        protocol = _ProbeProtocol()

        protocol.datagram_received(b"HELLO", ("192.168.1.50", DISCOVERY_PORT))

        assert protocol.reply.result() == ""

    @pytest.mark.asyncio
    async def test_noise_and_duplicates_are_ignored(self) -> None:
        """Non-HELLO traffic is dropped; a late duplicate reply does not raise."""
        protocol = _ProbeProtocol()

        protocol.datagram_received(b"@dat", ("192.168.1.50", DISCOVERY_PORT))
        assert not protocol.reply.done()

        protocol.datagram_received(b"HELLO A", ("192.168.1.50", DISCOVERY_PORT))
        protocol.datagram_received(b"HELLO B", ("192.168.1.50", DISCOVERY_PORT))
        assert protocol.reply.result() == "A"

    @pytest.mark.asyncio
    async def test_error_received_is_tolerated(self) -> None:
        """ICMP errors do not resolve or break the probe."""
        protocol = _ProbeProtocol()

        protocol.error_received(ConnectionRefusedError())

        assert not protocol.reply.done()


class TestAsyncProbeDevice:
    """The unicast liveness probe retries before giving up."""

    def _fake_endpoint(self, transport, answer_on_attempt: int | None):
        """Build an endpoint whose device answers on the given send (1-based)."""

        async def fake_endpoint(factory, **kwargs):
            assert kwargs["remote_addr"] == ("192.168.1.50", DISCOVERY_PORT)
            protocol = factory()
            sends = 0

            def sendto(data):
                nonlocal sends
                assert data == DISCOVERY_PAYLOAD
                sends += 1
                if sends == answer_on_attempt:
                    protocol.datagram_received(b"HELLO 5ED47C7F", ("192.168.1.50", DISCOVERY_PORT))

            transport.sendto.side_effect = sendto
            return transport, protocol

        return fake_endpoint

    @pytest.mark.asyncio
    @pytest.mark.parametrize("attempt", [1, 2, 3])
    async def test_answer_on_any_attempt(self, monkeypatch, attempt) -> None:
        """A reply on any of the attempts counts, including the last one."""
        transport = MagicMock(spec=asyncio.DatagramTransport)
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(
            loop, "create_datagram_endpoint", self._fake_endpoint(transport, attempt)
        )

        serial = await async_probe_device("192.168.1.50", timeout=0.01)

        assert serial == "5ED47C7F"
        assert transport.sendto.call_count == attempt
        transport.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_silence_after_all_attempts(self, monkeypatch) -> None:
        """No reply after every attempt returns None."""
        transport = MagicMock(spec=asyncio.DatagramTransport)
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "create_datagram_endpoint", self._fake_endpoint(transport, None))

        assert await async_probe_device("192.168.1.50", timeout=0.01) is None
        assert transport.sendto.call_count == PROBE_ATTEMPTS
        transport.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_endpoint_failure_returns_none(self, monkeypatch) -> None:
        """Unresolvable host / no network: the probe reports silence."""

        async def fake_endpoint(factory, **kwargs):
            raise OSError("Name or service not known")

        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "create_datagram_endpoint", fake_endpoint)

        assert await async_probe_device("192.168.1.50", timeout=0.01) is None

    def test_default_attempts(self) -> None:
        """Replies were seen on the 2nd attempt in the field: retry at least 3 times."""
        assert PROBE_ATTEMPTS >= 3
