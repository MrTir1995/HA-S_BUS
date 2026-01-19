"""S-Bus Protocol implementation for SAIA PCD controllers.

This module implements the SAIA S-Bus protocol (Data Mode SM2) for
communication with PCD controllers over Ether-S-Bus (UDP).
"""

from __future__ import annotations

import asyncio
import logging
import struct
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

if TYPE_CHECKING:
    from homeassistant.exceptions import HomeAssistantError
else:
    from homeassistant.exceptions import HomeAssistantError

from .const import ATTR_ACK
from .const import ATTR_REQUEST
from .const import ATTR_RESPONSE
from .const import CMD_READ_FLAG
from .const import CMD_READ_REGISTER
from .const import CMD_WRITE_FLAG
from .const import CMD_WRITE_REGISTER
from .const import DEFAULT_TIMEOUT
from .const import MAX_REGISTER_ADDRESS
from .const import MAX_REGISTER_COUNT
from .const import MAX_REGISTER_VALUE
from .const import MIN_TELEGRAM_SIZE

_LOGGER = logging.getLogger(__name__)


class SBusProtocolError(HomeAssistantError):
    """Base exception for S-Bus protocol errors."""


class SBusTimeoutError(SBusProtocolError):
    """Timeout during S-Bus communication."""


class SBusCRCError(SBusProtocolError):
    """CRC validation error."""


class SBusProtocol:
    """S-Bus Protocol implementation for Ether-S-Bus (UDP).

    This class implements the Data Mode (SM2) of the S-Bus protocol
    for communication over UDP (Ether-S-Bus).
    """

    # CRC-16-CCITT lookup table
    CRC16_TABLE: ClassVar[list[int]] = [
        0x0000,
        0x1021,
        0x2042,
        0x3063,
        0x4084,
        0x50A5,
        0x60C6,
        0x70E7,
        0x8108,
        0x9129,
        0xA14A,
        0xB16B,
        0xC18C,
        0xD1AD,
        0xE1CE,
        0xF1EF,
        0x1231,
        0x0210,
        0x3273,
        0x2252,
        0x52B5,
        0x4294,
        0x72F7,
        0x62D6,
        0x9339,
        0x8318,
        0xB37B,
        0xA35A,
        0xD3BD,
        0xC39C,
        0xF3FF,
        0xE3DE,
        0x2462,
        0x3443,
        0x0420,
        0x1401,
        0x64E6,
        0x74C7,
        0x44A4,
        0x5485,
        0xA56A,
        0xB54B,
        0x8528,
        0x9509,
        0xE5EE,
        0xF5CF,
        0xC5AC,
        0xD58D,
        0x3653,
        0x2672,
        0x1611,
        0x0630,
        0x76D7,
        0x66F6,
        0x5695,
        0x46B4,
        0xB75B,
        0xA77A,
        0x9719,
        0x8738,
        0xF7DF,
        0xE7FE,
        0xD79D,
        0xC7BC,
        0x48C4,
        0x58E5,
        0x6886,
        0x78A7,
        0x0840,
        0x1861,
        0x2802,
        0x3823,
        0xC9CC,
        0xD9ED,
        0xE98E,
        0xF9AF,
        0x8948,
        0x9969,
        0xA90A,
        0xB92B,
        0x5AF5,
        0x4AD4,
        0x7AB7,
        0x6A96,
        0x1A71,
        0x0A50,
        0x3A33,
        0x2A12,
        0xDBFD,
        0xCBDC,
        0xFBBF,
        0xEB9E,
        0x9B79,
        0x8B58,
        0xBB3B,
        0xAB1A,
        0x6CA6,
        0x7C87,
        0x4CE4,
        0x5CC5,
        0x2C22,
        0x3C03,
        0x0C60,
        0x1C41,
        0xEDAE,
        0xFD8F,
        0xCDEC,
        0xDDCD,
        0xAD2A,
        0xBD0B,
        0x8D68,
        0x9D49,
        0x7E97,
        0x6EB6,
        0x5ED5,
        0x4EF4,
        0x3E13,
        0x2E32,
        0x1E51,
        0x0E70,
        0xFF9F,
        0xEFBE,
        0xDFDD,
        0xCFFC,
        0xBF1B,
        0xAF3A,
        0x9F59,
        0x8F78,
        0x9188,
        0x81A9,
        0xB1CA,
        0xA1EB,
        0xD10C,
        0xC12D,
        0xF14E,
        0xE16F,
        0x1080,
        0x00A1,
        0x30C2,
        0x20E3,
        0x5004,
        0x4025,
        0x7046,
        0x6067,
        0x83B9,
        0x9398,
        0xA3FB,
        0xB3DA,
        0xC33D,
        0xD31C,
        0xE37F,
        0xF35E,
        0x02B1,
        0x1290,
        0x22F3,
        0x32D2,
        0x4235,
        0x5214,
        0x6277,
        0x7256,
        0xB5EA,
        0xA5CB,
        0x95A8,
        0x8589,
        0xF56E,
        0xE54F,
        0xD52C,
        0xC50D,
        0x34E2,
        0x24C3,
        0x14A0,
        0x0481,
        0x7466,
        0x6447,
        0x5424,
        0x4405,
        0xA7DB,
        0xB7FA,
        0x8799,
        0x97B8,
        0xE75F,
        0xF77E,
        0xC71D,
        0xD73C,
        0x26D3,
        0x36F2,
        0x0691,
        0x16B0,
        0x6657,
        0x7676,
        0x4615,
        0x5634,
        0xD94C,
        0xC96D,
        0xF90E,
        0xE92F,
        0x99C8,
        0x89E9,
        0xB98A,
        0xA9AB,
        0x5844,
        0x4865,
        0x7806,
        0x6827,
        0x18C0,
        0x08E1,
        0x3882,
        0x28A3,
        0xCB7D,
        0xDB5C,
        0xEB3F,
        0xFB1E,
        0x8BF9,
        0x9BD8,
        0xABBB,
        0xBB9A,
        0x4A75,
        0x5A54,
        0x6A37,
        0x7A16,
        0x0AF1,
        0x1AD0,
        0x2AB3,
        0x3A92,
        0xFD2E,
        0xED0F,
        0xDD6C,
        0xCD4D,
        0xBDAA,
        0xAD8B,
        0x9DE8,
        0x8DC9,
        0x7C26,
        0x6C07,
        0x5C64,
        0x4C45,
        0x3CA2,
        0x2C83,
        0x1CE0,
        0x0CC1,
        0xEF1F,
        0xFF3E,
        0xCF5D,
        0xDF7C,
        0xAF9B,
        0xBFBA,
        0x8FD9,
        0x9FF8,
        0x6E17,
        0x7E36,
        0x4E55,
        0x5E74,
        0x2E93,
        0x3EB2,
        0x0ED1,
        0x1EF0,
    ]

    def __init__(
        self, host: str, port: int, station: int, timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        """Initialize the S-Bus protocol handler.

        Args:
            host: IP address or hostname of the PCD controller
            port: UDP port (typically 5050)
            station: S-Bus station address (0-253)
            timeout: Communication timeout in seconds

        """
        self.host = host
        self.port = port
        self.station = station
        self.timeout = timeout
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._transport: asyncio.DatagramTransport | None = None
        self._protocol: _SBusDatagramProtocol | None = None

    async def connect(self) -> None:
        """Establish UDP connection to the S-Bus device."""
        loop = asyncio.get_event_loop()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: _SBusDatagramProtocol(),
            remote_addr=(self.host, self.port),
        )
        _LOGGER.debug("Connected to S-Bus device at %s:%d", self.host, self.port)

    async def disconnect(self) -> None:
        """Close the UDP connection."""
        if self._transport:
            self._transport.close()
            self._transport = None
            self._protocol = None
            _LOGGER.debug("Disconnected from S-Bus device")

    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC-16-CCITT for the given data.

        Args:
            data: Byte array to calculate CRC for

        Returns:
            16-bit CRC value

        """
        crc = 0x0000
        for byte in data:
            index = (crc >> 8) ^ byte
            crc = ((crc << 8) ^ self.CRC16_TABLE[index]) & 0xFFFF
        return crc

    def _get_next_sequence(self) -> int:
        """Get next sequence number for request tracking.

        Returns:
            Sequence number (0-65535)

        """
        self._sequence = (self._sequence + 1) & 0xFFFF
        return self._sequence

    def _build_telegram(
        self,
        command: int,
        data: bytes = b"",
        attribute: int = ATTR_REQUEST,
    ) -> bytes:
        """Build an Ether-S-Bus telegram.

        Args:
            command: S-Bus command opcode
            data: Command-specific data payload
            attribute: Telegram attribute (request/response/ack)

        Returns:
            Complete telegram ready to send

        """
        sequence = self._get_next_sequence()

        # Build the PDU (without length field)
        pdu = struct.pack(
            "!BHBBB",
            0x01,  # Version
            0x00,  # Type
            sequence,  # Sequence number
            attribute,  # Attribute
            self.station,  # Station address
        )
        pdu += struct.pack("!B", command)  # Command
        pdu += data  # Data payload

        # Calculate total length (including length field itself)
        total_length = 4 + len(pdu) + 2  # Length(4) + PDU + CRC(2)

        # Build complete telegram with length prefix
        telegram = struct.pack("!I", total_length)
        telegram += pdu

        # Calculate and append CRC over entire telegram
        crc = self._calculate_crc(telegram)
        telegram += struct.pack("!H", crc)

        return telegram

    def _validate_response(self, response: bytes, expected_sequence: int) -> bytes:
        """Validate received telegram and extract data.

        Args:
            response: Raw telegram received from device
            expected_sequence: Expected sequence number

        Returns:
            Data payload from response

        Raises:
            SBusCRCError: If CRC validation fails
            SBusProtocolError: If response structure is invalid

        """
        if len(response) < MIN_TELEGRAM_SIZE:
            msg = f"Response too short: {len(response)} bytes (minimum {MIN_TELEGRAM_SIZE})"
            raise SBusProtocolError(msg)

        # Extract length
        length = struct.unpack("!I", response[0:4])[0]
        if len(response) != length:
            msg = f"Length mismatch: expected {length}, got {len(response)}"
            raise SBusProtocolError(msg)

        # Validate CRC
        received_crc = struct.unpack("!H", response[-2:])[0]
        calculated_crc = self._calculate_crc(response[:-2])

        if received_crc != calculated_crc:
            msg = (
                f"CRC error: expected 0x{calculated_crc:04X}, got 0x{received_crc:04X}"
            )
            raise SBusCRCError(msg)

        # Parse header
        _version, _prot_type, sequence, attribute, _station = struct.unpack(
            "!BHBBB", response[4:10]
        )

        if sequence != expected_sequence:
            msg = f"Sequence mismatch: expected {expected_sequence}, got {sequence}"
            raise SBusProtocolError(msg)

        if attribute not in (ATTR_RESPONSE, ATTR_ACK):
            msg = f"Invalid response attribute: 0x{attribute:02X}"
            raise SBusProtocolError(msg)

        # Extract command and data
        command = response[10]
        data = response[11:-2]

        _LOGGER.debug(
            "Received response: seq=%d, cmd=0x%02X, data_len=%d",
            sequence,
            command,
            len(data),
        )

        return data

    async def _send_and_receive(self, telegram: bytes, expected_sequence: int) -> bytes:
        """Send telegram and wait for response.

        Args:
            telegram: Complete telegram to send
            expected_sequence: Sequence number to match in response

        Returns:
            Data payload from response

        Raises:
            SBusTimeoutError: If no response received within timeout
            SBusCRCError: If CRC validation fails
            SBusProtocolError: For other protocol errors

        """
        if not self._transport or not self._protocol:
            msg = "Not connected to S-Bus device"
            raise SBusProtocolError(msg)

        async with self._lock:
            # Clear any pending responses
            self._protocol.clear_response()

            # Send telegram
            self._transport.sendto(telegram)
            _LOGGER.debug("Sent telegram: %s", telegram.hex())

            # Wait for response
            try:
                response = await asyncio.wait_for(
                    self._protocol.get_response(),
                    timeout=self.timeout,
                )
            except TimeoutError as err:
                msg = f"Timeout waiting for response from {self.host}:{self.port}"
                raise SBusTimeoutError(msg) from err

            # Validate and extract data
            return self._validate_response(response, expected_sequence)

    async def read_registers(
        self,
        start_address: int,
        count: int = 1,
    ) -> list[int]:
        """Read one or more registers from the device.

        Args:
            start_address: Starting register address (0-9999)
            count: Number of registers to read (1-32)

        Returns:
            List of register values (32-bit integers)

        Raises:
            ValueError: If parameters are out of range
            SBusProtocolError: For protocol errors

        """
        if not 0 <= start_address <= MAX_REGISTER_ADDRESS:
            msg = f"Register address out of range: {start_address} (max {MAX_REGISTER_ADDRESS})"
            raise ValueError(msg)

        if not 1 <= count <= MAX_REGISTER_COUNT:
            msg = f"Count out of range: {count} (max {MAX_REGISTER_COUNT})"
            raise ValueError(msg)

        # Build request data: start address (2 bytes) + count (1 byte)
        data = struct.pack("!HB", start_address, count)

        # Build and send telegram
        sequence = self._get_next_sequence()
        telegram = self._build_telegram(CMD_READ_REGISTER, data)
        response_data = await self._send_and_receive(telegram, sequence)

        # Parse response: each register is 4 bytes (32-bit)
        expected_len = count * 4
        if len(response_data) != expected_len:
            msg = f"Unexpected response length: expected {expected_len}, got {len(response_data)}"
            raise SBusProtocolError(msg)

        # Unpack registers (big-endian 32-bit integers)
        registers = []
        for i in range(count):
            offset = i * 4
            value = struct.unpack("!I", response_data[offset : offset + 4])[0]
            registers.append(value)

        _LOGGER.debug(
            "Read %d register(s) from R%d: %s",
            count,
            start_address,
            registers,
        )

        return registers

    async def write_register(self, address: int, value: int) -> None:
        """Write a value to a register.

        Args:
            address: Register address (0-9999)
            value: Value to write (32-bit integer)

        Raises:
            ValueError: If parameters are out of range
            SBusProtocolError: For protocol errors

        """
        if not 0 <= address <= MAX_REGISTER_ADDRESS:
            msg = (
                f"Register address out of range: {address} (max {MAX_REGISTER_ADDRESS})"
            )
            raise ValueError(msg)

        if not 0 <= value <= MAX_REGISTER_VALUE:
            msg = f"Value out of range: {value} (max 0x{MAX_REGISTER_VALUE:X})"
            raise ValueError(msg)

        # Build request data: address (2 bytes) + value (4 bytes)
        data = struct.pack("!HI", address, value)

        # Build and send telegram
        sequence = self._get_next_sequence()
        telegram = self._build_telegram(CMD_WRITE_REGISTER, data)
        await self._send_and_receive(telegram, sequence)

        _LOGGER.debug("Wrote R%d = %d", address, value)

    async def read_flags(self, start_address: int, count: int = 1) -> list[bool]:
        """Read flag (bit) values from the device.

        Args:
            start_address: Starting flag address
            count: Number of flags to read

        Returns:
            List of boolean flag states

        Raises:
            ValueError: If parameters are out of range
            SBusProtocolError: For protocol errors

        """
        if not start_address >= 0:
            msg = f"Flag address out of range: {start_address}"
            raise ValueError(msg)

        if not count >= 1:
            msg = f"Count out of range: {count}"
            raise ValueError(msg)

        # Build request data
        data = struct.pack("!HH", start_address, count)

        # Build and send telegram
        sequence = self._get_next_sequence()
        telegram = self._build_telegram(CMD_READ_FLAG, data)
        response_data = await self._send_and_receive(telegram, sequence)

        # Parse response: flags are packed into bytes (8 flags per byte)
        flags = []
        for byte in response_data:
            for bit_pos in range(8):
                if len(flags) >= count:
                    break
                flags.append(bool(byte & (1 << bit_pos)))

        return flags[:count]

    async def write_flag(self, address: int, value: bool) -> None:
        """Write a flag (bit) value.

        Args:
            address: Flag address
            value: Boolean value to write

        Raises:
            ValueError: If address is out of range
            SBusProtocolError: For protocol errors

        """
        if not address >= 0:
            msg = f"Flag address out of range: {address}"
            raise ValueError(msg)

        # Build request data: address (2 bytes) + value (1 byte: 0 or 1)
        data = struct.pack("!HB", address, 1 if value else 0)

        # Build and send telegram
        sequence = self._get_next_sequence()
        telegram = self._build_telegram(CMD_WRITE_FLAG, data)
        await self._send_and_receive(telegram, sequence)

        _LOGGER.debug("Wrote Flag %d = %s", address, value)

    async def get_device_info(self) -> dict[str, Any]:
        """Read device identification from system registers.

        Returns:
            Dictionary with device information

        Raises:
            SBusProtocolError: For protocol errors

        """
        from .const import SYSREG_FIRMWARE
        from .const import SYSREG_HW_VERSION
        from .const import SYSREG_PRODUCT_TYPE_END
        from .const import SYSREG_PRODUCT_TYPE_START
        from .const import SYSREG_SERIAL_END
        from .const import SYSREG_SERIAL_START

        # Read firmware version
        firmware_raw = await self.read_registers(SYSREG_FIRMWARE, 1)
        firmware_version = firmware_raw[0]

        # Read product type (4 registers, ASCII string)
        product_type_raw = await self.read_registers(
            SYSREG_PRODUCT_TYPE_START,
            SYSREG_PRODUCT_TYPE_END - SYSREG_PRODUCT_TYPE_START + 1,
        )
        product_type_bytes = b"".join(
            struct.pack("!I", reg) for reg in product_type_raw
        )
        product_type = product_type_bytes.decode("ascii").strip("\x00")

        # Read hardware version
        hw_version_raw = await self.read_registers(SYSREG_HW_VERSION, 1)
        hw_version = hw_version_raw[0]

        # Read serial number (2 registers)
        serial_raw = await self.read_registers(
            SYSREG_SERIAL_START,
            SYSREG_SERIAL_END - SYSREG_SERIAL_START + 1,
        )
        serial_number = f"{serial_raw[0]:08X}{serial_raw[1]:08X}"

        return {
            "firmware_version": firmware_version,
            "product_type": product_type,
            "hw_version": hw_version,
            "serial_number": serial_number,
        }


class _SBusDatagramProtocol(asyncio.DatagramProtocol):
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
