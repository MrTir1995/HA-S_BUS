"""The integration recovers on its own after the PCD was unreachable."""

from __future__ import annotations

import asyncio
import logging

import pytest

import custom_components.sbus.coordinator as coordinator_module
from custom_components.sbus.coordinator import SBusDataUpdateCoordinator
from custom_components.sbus.ether_sbus import EtherSBusProtocol

from .test_sbus_protocol import STATION
from .test_sbus_protocol import FakePCD


async def _start_pcd(port: int = 0):
    loop = asyncio.get_running_loop()
    transport, pcd = await loop.create_datagram_endpoint(
        FakePCD, local_addr=("127.0.0.1", port)
    )
    pcd.registers[3219] = 325
    return transport, pcd


@pytest.mark.parametrize("outage", ["silent", "restart"])
async def test_recovers_after_outage(
    hass,
    socket_enabled,  # noqa: ARG001
    monkeypatch,
    caplog,
    outage: str,
) -> None:
    """PCD stops answering (or restarts), then comes back; one log entry each."""
    monkeypatch.setattr(coordinator_module, "RECONNECT_DELAY", 0)
    transport, pcd = await _start_pcd()
    port = transport.get_extra_info("sockname")[1]
    protocol = EtherSBusProtocol("127.0.0.1", port, STATION, timeout=0.2)
    protocol._max_retries = 2  # noqa: SLF001
    await protocol.connect()
    coordinator = SBusDataUpdateCoordinator(
        hass, protocol, 30, register_addresses=[3219]
    )
    caplog.set_level(logging.DEBUG, logger="custom_components.sbus")

    results = []

    async def poll() -> None:
        await coordinator.async_refresh()
        results.append(coordinator.last_update_success)

    await poll()
    if outage == "silent":
        pcd.silent = True
    else:
        transport.close()
        await asyncio.sleep(0.05)
    for _ in range(5):  # includes a reconnect after 3 failures
        await poll()
    if outage == "silent":
        pcd.silent = False
    else:
        transport, pcd = await _start_pcd(port)
    await poll()

    try:
        assert results == [True, False, False, False, False, False, True]
        assert coordinator.data["registers"][3219] == 325
        problems = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(problems) == 1
        assert "No answer from 127.0.0.1" in problems[0].getMessage()
        assert any("recovered" in r.getMessage() for r in caplog.records)
    finally:
        await protocol.disconnect()
        transport.close()
