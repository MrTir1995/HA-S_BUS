"""Ether-S-Bus protocol implementation for SAIA PCD controllers.

This module implements Ether-S-Bus (UDP/TCP) communication.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .const import DEFAULT_TIMEOUT
from .sbus_protocol_base import SBusProtocolBase
from .sbus_protocol_base import SBusTimeoutError

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class EtherSBusProtocol(SBusProtocolBase):
    """Ether-S-Bus Protocol implementation (UDP/TCP).

    Implements S-Bus communication over Ether-S-Bus using UDP or TCP transport.
    """

    def __init__(
        self,
        host: str,
        port: int,
        station: int,
        use_tcp: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Ether-S-Bus protocol.

        Args:
            host: Device hostname or IP address
            port: UDP/TCP port number
            station: Station address (0-253)
            use_tcp: Use TCP instead of UDP
            timeout: Communication timeout in seconds

        """
        super().__init__(station, timeout)
        self.host = host
        self.port = port
        self.use_tcp = use_tcp
        self._transport: asyncio.DatagramTransport | asyncio.Transport | None = None
        self._protocol: _EtherSBusDatagramProtocol | _EtherSBusStreamProtocol | None = (
            None
        )
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Establish connection to the S-Bus device via Ether-S-Bus."""
        if self.use_tcp:
            await self._connect_tcp()
        else:
            await self._connect_udp()

    async def _connect_udp(self) -> None:
        """Establish UDP connection."""
        loop = asyncio.get_event_loop()

        def protocol_factory() -> _EtherSBusDatagramProtocol:
            """Create protocol instance."""
            self._protocol = _EtherSBusDatagramProtocol()
            return self._protocol

        transport, _ = await loop.create_datagram_endpoint(
            protocol_factory,
            remote_addr=(self.host, self.port),
        )
        self._transport = transport  # type: ignore[assignment]

        _LOGGER.debug(
            "Connected to %s:%d via UDP (station %d)",
            self.host,
            self.port,
            self.station,
        )

    async def _connect_tcp(self) -> None:
        """Establish TCP connection."""
        self._reader, self._writer = await asyncio.open_connection(
            self.host,
            self.port,
        )

        _LOGGER.debug(
            "Connected to %s:%d via TCP (station %d)",
            self.host,
            self.port,
            self.station,
        )

    async def disconnect(self) -> None:
        """Close connection to the S-Bus device."""
        if self.use_tcp and self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None
        elif self._transport:
            self._transport.close()
            self._transport = None
            self._protocol = None

        _LOGGER.debug(
            "Disconnected from %s:%d (station %d)",
            self.host,
            self.port,
            self.station,
        )

    async def _send_and_receive(self, telegram: bytes) -> bytes:
        """Send telegram and receive response via Ether-S-Bus.

        Args:
            telegram: The telegram to send

        Returns:
            The response telegram

        Raises:
            SBusTimeoutError: If communication times out

        """
        if self.use_tcp:
            return await self._send_and_receive_tcp(telegram)
        return await self._send_and_receive_udp(telegram)

    async def _send_and_receive_udp(self, telegram: bytes) -> bytes:
        """Send and receive via UDP."""
        if not self._transport or not self._protocol:
            msg = "Not connected to device"
            raise SBusTimeoutError(msg)

        _LOGGER.debug("Sending UDP telegram: %s", telegram.hex())

        # Clear any pending responses
        self._protocol.clear_response()

        # Send telegram (type ignore for DatagramTransport)
        if isinstance(self._transport, asyncio.DatagramTransport):
            self._transport.sendto(telegram)  # type: ignore[attr-defined]
        else:
            msg = "Transport is not a DatagramTransport"
            raise SBusTimeoutError(msg)

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                self._protocol.get_response(),
                timeout=self.timeout,
            )
            _LOGGER.debug("Received UDP response: %s", response.hex())
            return response

        except TimeoutError as err:
            msg = f"Timeout waiting for response from {self.host}:{self.port}"
            raise SBusTimeoutError(msg) from err

    async def _send_and_receive_tcp(self, telegram: bytes) -> bytes:
        """Send and receive via TCP."""
        if not self._reader or not self._writer:
            msg = "Not connected to device"
            raise SBusTimeoutError(msg)

        _LOGGER.debug("Sending TCP telegram: %s", telegram.hex())

        # Send telegram
        self._writer.write(telegram)
        await self._writer.drain()

        # Wait for response with timeout
        try:
            # Read at least minimum telegram size
            response = await asyncio.wait_for(
                self._reader.read(1024),
                timeout=self.timeout,
            )
            _LOGGER.debug("Received TCP response: %s", response.hex())
            return response

        except TimeoutError as err:
            msg = f"Timeout waiting for response from {self.host}:{self.port}"
            raise SBusTimeoutError(msg) from err


class _EtherSBusDatagramProtocol(asyncio.DatagramProtocol):
    """Internal protocol handler for UDP communication."""

    def __init__(self) -> None:
        """Initialize the protocol handler."""
        self._response_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when connection is established."""
        self._transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Called when a datagram is received."""
        _LOGGER.debug("Received datagram from %s:%d: %s", addr[0], addr[1], data.hex())
        self._response_queue.put_nowait(data)

    def error_received(self, exc: Exception) -> None:
        """Called when an error is received."""
        _LOGGER.error("Datagram error received: %s", exc)

    async def get_response(self) -> bytes:
        """Wait for and return the next response."""
        return await self._response_queue.get()

    def clear_response(self) -> None:
        """Clear any pending responses in the queue."""
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class _EtherSBusStreamProtocol(asyncio.Protocol):
    """Internal protocol handler for TCP communication."""

    def __init__(self) -> None:
        """Initialize the protocol handler."""
        self._response_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._transport: asyncio.Transport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when connection is established."""
        self._transport = transport  # type: ignore[assignment]

    def data_received(self, data: bytes) -> None:
        """Called when data is received."""
        _LOGGER.debug("Received data: %s", data.hex())
        self._response_queue.put_nowait(data)

    def error_received(self, exc: Exception) -> None:
        """Called when an error is received."""
        _LOGGER.error("Stream error received: %s", exc)

    async def get_response(self) -> bytes:
        """Wait for and return the next response."""
        return await self._response_queue.get()

    def clear_response(self) -> None:
        """Clear any pending responses in the queue."""
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
