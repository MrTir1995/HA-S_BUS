"""Serial-S-Bus over a real (pseudo) serial port using serialx."""

from __future__ import annotations

import asyncio
import os
import pty
import struct
import tty

import pytest

from custom_components.sbus.const import ATTR_RESPONSE
from custom_components.sbus.const import SBUS_FRAME_START
from custom_components.sbus.sbus_protocol_base import SBusConnectionError
from custom_components.sbus.serial_sbus import SerialSBusProtocol

pytest.importorskip("serialx")

STATION = 10


async def test_read_register_over_pty() -> None:
    """A register read goes out as data mode frame and the reply is decoded."""
    master, slave = pty.openpty()
    tty.setraw(slave)
    port = os.ttyname(slave)
    loop = asyncio.get_running_loop()
    received = bytearray()

    def on_request() -> None:
        received.extend(os.read(master, 1024))
        # Request: B5 00 <station> 06 <count-1> <addr hi> <addr lo> <crc>
        if len(received) >= 9 and received[0] == SBUS_FRAME_START:
            reply = SerialSBusProtocol.build_serial_frame(
                struct.pack("!I", 0xB5), ATTR_RESPONSE  # forces byte stuffing
            )
            os.write(master, reply)
            received.clear()

    loop.add_reader(master, on_request)
    protocol = SerialSBusProtocol(port, STATION, baudrate=38400, timeout=2)
    try:
        await protocol.connect()
        assert await protocol.read_registers(3219, 1) == [0xB5]
    finally:
        loop.remove_reader(master)
        await protocol.disconnect()
        os.close(master)
        os.close(slave)


async def test_missing_port_is_connection_error() -> None:
    """A serial port that does not exist raises SBusConnectionError."""
    protocol = SerialSBusProtocol("/dev/does-not-exist", STATION)
    with pytest.raises(SBusConnectionError):
        await protocol.connect()
