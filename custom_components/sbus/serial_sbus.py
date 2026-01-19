"""Serial-S-Bus protocol implementation for SAIA PCD controllers.

This module implements Serial-S-Bus communication over USB or TCP serial bridges.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .const import DEFAULT_BAUDRATE
from .const import DEFAULT_TIMEOUT
from .sbus_protocol_base import SBusProtocolBase
from .sbus_protocol_base import SBusTimeoutError

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class SerialSBusProtocol(SBusProtocolBase):
    """Serial-S-Bus Protocol implementation.

    Implements S-Bus communication over serial connections (USB or TCP/IP serial bridges).
    """

    def __init__(
        self,
        port: str,
        station: int,
        baudrate: int = DEFAULT_BAUDRATE,
        use_tcp: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Serial-S-Bus protocol.

        Args:
            port: Serial port path (e.g., /dev/ttyUSB0) or host:port for TCP
            station: Station address (0-253)
            baudrate: Baud rate for serial communication
            use_tcp: Use TCP/IP serial bridge instead of direct serial
            timeout: Communication timeout in seconds

        """
        super().__init__(station, timeout)
        self.port = port
        self.baudrate = baudrate
        self.use_tcp = use_tcp
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._serial = None

    async def connect(self) -> None:
        """Establish connection to the S-Bus device via Serial-S-Bus."""
        if self.use_tcp:
            await self._connect_tcp_serial()
        else:
            await self._connect_serial()

    async def _connect_serial(self) -> None:
        """Establish direct serial connection."""
        try:
            import serial_asyncio
        except ImportError as err:
            msg = "pyserial-asyncio is required for serial connections"
            raise ImportError(msg) from err

        # Open serial port
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self.port,
            baudrate=self.baudrate,
            bytesize=8,
            parity="E",  # Even parity
            stopbits=1,
            timeout=self.timeout,
        )

        _LOGGER.debug(
            "Connected to %s at %d baud (station %d)",
            self.port,
            self.baudrate,
            self.station,
        )

    async def _connect_tcp_serial(self) -> None:
        """Establish TCP serial bridge connection."""
        # Parse host:port from port string
        if ":" in self.port:
            host, port_str = self.port.rsplit(":", 1)
            port = int(port_str)
        else:
            msg = f"Invalid TCP serial address: {self.port}. Expected format: host:port"
            raise ValueError(msg)

        self._reader, self._writer = await asyncio.open_connection(
            host,
            port,
        )

        _LOGGER.debug(
            "Connected to %s via TCP serial bridge (station %d)",
            self.port,
            self.station,
        )

    async def disconnect(self) -> None:
        """Close connection to the S-Bus device."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None

        _LOGGER.debug(
            "Disconnected from %s (station %d)",
            self.port,
            self.station,
        )

    async def _send_and_receive(self, telegram: bytes) -> bytes:
        """Send telegram and receive response via Serial-S-Bus.

        Args:
            telegram: The telegram to send

        Returns:
            The response telegram

        Raises:
            SBusTimeoutError: If communication times out

        """
        if not self._reader or not self._writer:
            msg = "Not connected to device"
            raise SBusTimeoutError(msg)

        _LOGGER.debug("Sending serial telegram: %s", telegram.hex())

        # Clear input buffer if possible
        try:
            if hasattr(self._reader, "_buffer") and hasattr(
                self._reader._buffer, "clear"  # type: ignore[attr-defined] # noqa: SLF001
            ):
                self._reader._buffer.clear()  # type: ignore[attr-defined] # noqa: SLF001
        except Exception:
            pass  # Ignore if buffer clearing fails

        # Send telegram
        self._writer.write(telegram)
        await self._writer.drain()

        # Wait for response with timeout
        try:
            # Read minimum telegram size first
            response = await asyncio.wait_for(
                self._reader.read(1024),
                timeout=self.timeout,
            )
            _LOGGER.debug("Received serial response: %s", response.hex())
            return response

        except TimeoutError as err:
            msg = f"Timeout waiting for response from {self.port}"
            raise SBusTimeoutError(msg) from err
