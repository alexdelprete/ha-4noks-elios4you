"""Tests for 4-noks Elios4you UDP discovery module.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you import discovery as _discovery
from custom_components.fournoks_elios4you.const import CONF_MAC, DOMAIN
from custom_components.fournoks_elios4you.discovery import (
    BROADCAST_ADDR,
    DISCOVERY_INTERVAL,
    DISCOVERY_PAYLOAD,
    DISCOVERY_PORT,
    DISCOVERY_SERIAL,
    PROBE_ATTEMPTS,
    _DiscoveryProtocol,
    _ProbeProtocol,
    async_discover_devices,
    async_probe_device,
    async_start_discovery,
    async_trigger_discovery,
)
from homeassistant import config_entries
from homeassistant.const import CONF_HOST


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


class TestTriggerDiscovery:
    """Broadcast results become integration-discovery flows."""

    @pytest.mark.asyncio
    async def test_configured_device_gets_flow_only_to_learn_mac(self, hass) -> None:
        """A configured device is re-offered to the flow only when its MAC is new."""
        MockConfigEntry(
            domain=DOMAIN, unique_id="NOMAC", data={CONF_HOST: "192.168.1.20"}
        ).add_to_hass(hass)
        MockConfigEntry(
            domain=DOMAIN,
            unique_id="HASMAC",
            data={CONF_HOST: "192.168.1.21", CONF_MAC: "20:f8:5e:00:00:21"},
        ).add_to_hass(hass)
        MockConfigEntry(
            domain=DOMAIN, unique_id="NOARP", data={CONF_HOST: "192.168.1.22"}
        ).add_to_hass(hass)
        with patch.object(_discovery.discovery_flow, "async_create_flow") as create_flow:
            async_trigger_discovery(
                hass,
                {"192.168.1.20": "NOMAC", "192.168.1.21": "HASMAC", "192.168.1.22": "NOARP"},
                {"192.168.1.20": "20:f8:5e:00:00:20", "192.168.1.21": "20:f8:5e:00:00:21"},
            )

        create_flow.assert_called_once()
        assert create_flow.call_args.kwargs["data"] == {
            CONF_HOST: "192.168.1.20",
            DISCOVERY_SERIAL: "NOMAC",
            CONF_MAC: "20:f8:5e:00:00:20",
        }

    @pytest.mark.asyncio
    async def test_new_and_moved_devices_get_flows(self, hass) -> None:
        """Unknown serials and known serials at a new IP are handed to the flow."""
        MockConfigEntry(
            domain=DOMAIN, unique_id="KNOWN", data={CONF_HOST: "192.168.1.10"}
        ).add_to_hass(hass)
        with patch.object(_discovery.discovery_flow, "async_create_flow") as create_flow:
            async_trigger_discovery(
                hass,
                {
                    "192.168.1.10": "KNOWN",  # configured, same host: skipped
                    "192.168.1.11": "KNOWN",  # configured, moved: flow updates host
                    "192.168.1.12": "NEW",  # new device
                    "192.168.1.13": "",  # no serial: cannot deduplicate
                },
            )

        hosts = [c.kwargs["data"][CONF_HOST] for c in create_flow.call_args_list]
        assert hosts == ["192.168.1.11", "192.168.1.12"]
        assert create_flow.call_args.kwargs["context"] == {
            "source": config_entries.SOURCE_INTEGRATION_DISCOVERY
        }
        assert create_flow.call_args.kwargs["data"][DISCOVERY_SERIAL] == "NEW"


class TestStartDiscovery:
    """A loaded integration broadcasts at startup and on an interval."""

    @pytest.mark.asyncio
    async def test_broadcasts_now_and_schedules(self, hass) -> None:
        """One immediate broadcast, then every DISCOVERY_INTERVAL."""
        with (
            patch.object(
                _discovery, "async_discover_devices", AsyncMock(return_value={"1.2.3.4": "SN"})
            ),
            patch.object(
                _discovery, "async_lookup_macs", AsyncMock(return_value={"1.2.3.4": "aa:bb"})
            ) as lookup,
            patch.object(_discovery, "async_trigger_discovery") as trigger,
            patch.object(_discovery, "async_track_time_interval") as track,
        ):
            async_start_discovery(hass)
            await hass.async_block_till_done()

        lookup.assert_awaited_once_with(hass, ["1.2.3.4"])
        trigger.assert_called_once_with(hass, {"1.2.3.4": "SN"}, {"1.2.3.4": "aa:bb"})
        assert track.call_args.args[2] == DISCOVERY_INTERVAL
        assert track.call_args.kwargs == {"cancel_on_shutdown": True}


ARP_SAMPLE = """IP address       HW type     Flags       HW address            Mask     Device
10.1.10.120      0x1         0x2         20:F8:5E:A2:75:46     *        eth0
10.1.10.99       0x1         0x0         00:00:00:00:00:00     *        eth0
garbage
10.1.10.98       0x1         zz          20:f8:5e:00:00:98     *        eth0
"""


class TestReadArpTable:
    """Only complete, well-formed ARP entries are trusted."""

    def test_parses_complete_entries(self, tmp_path, monkeypatch) -> None:
        """Incomplete (0x0) and malformed rows are dropped; MACs are normalised."""
        arp = tmp_path / "arp"
        arp.write_text(ARP_SAMPLE)
        monkeypatch.setattr(_discovery, "ARP_TABLE", str(arp))

        assert _discovery._read_arp_table() == {"10.1.10.120": "20:f8:5e:a2:75:46"}

    def test_missing_table_is_empty(self, tmp_path, monkeypatch) -> None:
        """No /proc/net/arp (non-Linux, sandbox): no MAC, no error."""
        monkeypatch.setattr(_discovery, "ARP_TABLE", str(tmp_path / "missing"))

        assert _discovery._read_arp_table() == {}


class TestLookupMacs:
    """MACs come from the ARP table, probing first when an entry is missing."""

    @pytest.mark.asyncio
    async def test_found_without_probe(self, hass) -> None:
        """A host already in the table is resolved without any traffic."""
        with (
            patch.object(_discovery, "_read_arp_table", return_value={"1.1.1.1": "aa:bb"}),
            patch.object(_discovery, "async_probe_device", AsyncMock()) as probe,
        ):
            assert await _discovery.async_lookup_macs(hass, ["1.1.1.1"]) == {"1.1.1.1": "aa:bb"}

        probe.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_host_probed_then_reread(self, hass) -> None:
        """A missing host gets one probe; hosts that never resolve are left out."""
        with (
            patch.object(
                _discovery,
                "_read_arp_table",
                side_effect=[{}, {"1.1.1.1": "aa:bb"}],
            ),
            patch.object(_discovery, "async_probe_device", AsyncMock()) as probe,
        ):
            macs = await _discovery.async_lookup_macs(hass, ["1.1.1.1", "2.2.2.2"])

        assert macs == {"1.1.1.1": "aa:bb"}
        assert probe.await_count == 2
        probe.assert_any_await("2.2.2.2", attempts=1)
