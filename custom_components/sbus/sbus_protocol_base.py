"""Base S-Bus Protocol implementation for SAIA PCD controllers.

This module provides the base class and common functionality for all
S-Bus protocol variants (Serial-S-Bus, Ether-S-Bus, Profi-S-Bus).
"""

from __future__ import annotations

import asyncio
import logging
import struct
from abc import ABC
from abc import abstractmethod
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
from .const import SYSREG_FIRMWARE
from .const import SYSREG_HW_VERSION
from .const import SYSREG_PRODUCT_TYPE_END
from .const import SYSREG_PRODUCT_TYPE_START
from .const import SYSREG_SERIAL_END
from .const import SYSREG_SERIAL_START

_LOGGER = logging.getLogger(__name__)


class SBusProtocolError(HomeAssistantError):
    """Base exception for S-Bus protocol errors."""


class SBusTimeoutError(SBusProtocolError):
    """Timeout during S-Bus communication."""


class SBusCRCError(SBusProtocolError):
    """CRC validation error."""


class SBusProtocolBase(ABC):
    """Base class for S-Bus Protocol implementations.

    This abstract class provides common functionality for all S-Bus
    protocol variants: Serial-S-Bus, Ether-S-Bus, and Profi-S-Bus.
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

    def __init__(self, station: int, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize the S-Bus protocol.

        Args:
            station: Station address (0-253)
            timeout: Communication timeout in seconds

        """
        self.station = station
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._telegram_counter = 0

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the S-Bus device.

        Must be implemented by subclasses for specific transport.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the S-Bus device.

        Must be implemented by subclasses for specific transport.
        """

    @abstractmethod
    async def _send_and_receive(self, telegram: bytes) -> bytes:
        """Send telegram and receive response.

        Args:
            telegram: The telegram to send

        Returns:
            The response telegram

        Must be implemented by subclasses for specific transport.
        """

    @staticmethod
    def calculate_crc(data: bytes) -> int:
        """Calculate CRC-16-CCITT checksum for S-Bus.

        Uses CRC-16-CCITT with polynomial 0x1021 and initial value 0x0000
        as specified in the S-Bus protocol documentation.

        Args:
            data: Data to calculate CRC for

        Returns:
            CRC-16 checksum

        """
        crc = 0x0000  # S-Bus uses 0x0000 as initial value, not 0xFFFF

        for byte in data:
            crc = ((crc << 8) & 0xFFFF) ^ SBusProtocolBase.CRC16_TABLE[
                (crc >> 8) ^ byte
            ]

        return crc

    def _build_telegram(
        self,
        cmd: int,
        address: int,
        count: int,
        data: bytes = b"",
    ) -> bytes:
        """Build an S-Bus telegram.

        Args:
            cmd: Command opcode
            address: Register or flag address
            count: Number of registers/flags
            data: Optional data payload

        Returns:
            Complete telegram with CRC

        """
        self._telegram_counter = (self._telegram_counter + 1) % 256

        # Build header: telegram_nr, dest_addr, attr, opcode
        header = struct.pack(
            "BBBB",
            self._telegram_counter,
            self.station,
            ATTR_REQUEST,
            cmd,
        )

        # Build address and count fields
        addr_count = struct.pack("!HH", address, count)

        # Combine all parts
        telegram_body = header + addr_count + data

        # Calculate and append CRC
        crc = self.calculate_crc(telegram_body)
        telegram = telegram_body + struct.pack("!H", crc)

        return telegram

    def _validate_telegram(self, telegram: bytes) -> None:
        """Validate received telegram.

        Args:
            telegram: The received telegram

        Raises:
            SBusCRCError: If CRC validation fails
            SBusProtocolError: For other validation errors

        """
        if len(telegram) < MIN_TELEGRAM_SIZE:
            msg = f"Telegram too short: {len(telegram)} bytes"
            raise SBusProtocolError(msg)

        # Extract and verify CRC
        data = telegram[:-2]
        received_crc = struct.unpack("!H", telegram[-2:])[0]
        calculated_crc = self.calculate_crc(data)

        if received_crc != calculated_crc:
            msg = f"CRC mismatch: expected {calculated_crc:04X}, got {received_crc:04X}"
            raise SBusCRCError(msg)

        # Verify it's a response
        attr = telegram[2]
        if attr not in (ATTR_RESPONSE, ATTR_ACK):
            msg = f"Invalid attribute byte: {attr:02X}"
            raise SBusProtocolError(msg)

    async def read_registers(
        self,
        address: int,
        count: int = 1,
    ) -> list[int]:
        """Read PCD registers.

        Args:
            address: Starting register address (0-9999)
            count: Number of registers to read (1-32)

        Returns:
            List of register values

        Raises:
            ValueError: If parameters are out of range
            SBusTimeoutError: If communication times out
            SBusProtocolError: For protocol errors

        """
        if not 0 <= address <= MAX_REGISTER_ADDRESS:
            msg = f"Address {address} out of range (0-{MAX_REGISTER_ADDRESS})"
            raise ValueError(msg)

        if not 1 <= count <= MAX_REGISTER_COUNT:
            msg = f"Count {count} out of range (1-{MAX_REGISTER_COUNT})"
            raise ValueError(msg)

        telegram = self._build_telegram(CMD_READ_REGISTER, address, count)

        async with self._lock:
            response = await self._send_and_receive(telegram)
            self._validate_telegram(response)

            # Parse response data (skip header and CRC)
            data = response[8:-2]

            # Each register is 4 bytes (32-bit)
            registers = []
            for i in range(count):
                reg_value = struct.unpack("!I", data[i * 4 : (i + 1) * 4])[0]
                registers.append(reg_value)

            return registers

    async def write_register(
        self,
        address: int,
        value: int,
    ) -> None:
        """Write a PCD register.

        Args:
            address: Register address (0-9999)
            value: Value to write (0-0xFFFFFFFF)

        Raises:
            ValueError: If parameters are out of range
            SBusTimeoutError: If communication times out
            SBusProtocolError: For protocol errors

        """
        if not 0 <= address <= MAX_REGISTER_ADDRESS:
            msg = f"Address {address} out of range (0-{MAX_REGISTER_ADDRESS})"
            raise ValueError(msg)

        if not 0 <= value <= MAX_REGISTER_VALUE:
            msg = f"Value {value} out of range (0-{MAX_REGISTER_VALUE})"
            raise ValueError(msg)

        data = struct.pack("!I", value)
        telegram = self._build_telegram(CMD_WRITE_REGISTER, address, 1, data)

        async with self._lock:
            response = await self._send_and_receive(telegram)
            self._validate_telegram(response)

    async def read_flags(
        self,
        address: int,
        count: int = 1,
    ) -> list[bool]:
        """Read PCD flags.

        Args:
            address: Starting flag address
            count: Number of flags to read

        Returns:
            List of flag states

        Raises:
            ValueError: If parameters are out of range
            SBusTimeoutError: If communication times out
            SBusProtocolError: For protocol errors

        """
        telegram = self._build_telegram(CMD_READ_FLAG, address, count)

        async with self._lock:
            response = await self._send_and_receive(telegram)
            self._validate_telegram(response)

            # Parse response data (skip header and CRC)
            data = response[8:-2]

            # Flags are packed as bits
            flags = []
            for byte in data:
                for bit in range(8):
                    if len(flags) < count:
                        flags.append(bool(byte & (1 << bit)))

            return flags[:count]

    async def write_flag(
        self,
        address: int,
        value: bool,
    ) -> None:
        """Write a PCD flag.

        Args:
            address: Flag address
            value: Flag state

        Raises:
            ValueError: If parameters are out of range
            SBusTimeoutError: If communication times out
            SBusProtocolError: For protocol errors

        """
        data = struct.pack("B", 1 if value else 0)
        telegram = self._build_telegram(CMD_WRITE_FLAG, address, 1, data)

        async with self._lock:
            response = await self._send_and_receive(telegram)
            self._validate_telegram(response)

    async def get_device_info(self) -> dict[str, Any]:
        """Get comprehensive device information.

        Returns:
            Dictionary with device information including:
            - firmware_version: Firmware version number
            - product_type: Product name (e.g., "PCD3.M5540")
            - hw_version: Hardware version number
            - serial_number: Device serial number
            - firmware_version_str: Formatted firmware version
            - hw_version_str: Formatted hardware version

        Raises:
            SBusTimeoutError: If communication times out
            SBusProtocolError: For protocol errors

        """
        try:
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
            product_type = product_type_bytes.decode("ascii", errors="ignore").strip("\x00")

            # Read hardware version
            hw_version_raw = await self.read_registers(SYSREG_HW_VERSION, 1)
            hw_version = hw_version_raw[0]

            # Read serial number (2 registers)
            serial_raw = await self.read_registers(
                SYSREG_SERIAL_START,
                SYSREG_SERIAL_END - SYSREG_SERIAL_START + 1,
            )
            serial_number = f"{serial_raw[0]:08X}{serial_raw[1]:08X}"

            # Format version strings for better readability
            firmware_version_str = self._format_version(firmware_version)
            hw_version_str = self._format_version(hw_version)

            return {
                "firmware_version": firmware_version,
                "product_type": product_type if product_type else "SAIA PCD",
                "hw_version": hw_version,
                "serial_number": serial_number,
                "firmware_version_str": firmware_version_str,
                "hw_version_str": hw_version_str,
            }
        except Exception as err:
            _LOGGER.error("Failed to read device information: %s", err)
            # Return minimal info if read fails
            return {
                "firmware_version": 0,
                "product_type": "SAIA PCD (Unknown)",
                "hw_version": 0,
                "serial_number": "UNKNOWN",
                "firmware_version_str": "Unknown",
                "hw_version_str": "Unknown",
            }

    @staticmethod
    def _format_version(version: int) -> str:
        """Format version number to readable string.

        Args:
            version: Raw version number

        Returns:
            Formatted version string (e.g., "1.23.45")

        """
        if version == 0:
            return "Unknown"
        # Version format: Major.Minor.Patch
        major = (version >> 16) & 0xFF
        minor = (version >> 8) & 0xFF
        patch = version & 0xFF
        return f"{major}.{minor}.{patch}"
