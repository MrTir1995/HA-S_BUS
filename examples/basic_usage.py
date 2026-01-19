"""Example script showing how to use the S-Bus protocol directly."""

from __future__ import annotations

import asyncio
import logging

from custom_components.sbus.sbus_protocol import SBusProtocol
from custom_components.sbus.sbus_protocol import SBusProtocolError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

_LOGGER = logging.getLogger(__name__)


async def main() -> None:
    """Run example S-Bus operations."""
    # Connection parameters
    host = "192.168.1.100"  # Replace with your PCD IP
    port = 5050
    station = 0

    # Create protocol instance
    protocol = SBusProtocol(host, port, station)

    try:
        # Connect to device
        _LOGGER.info("Connecting to S-Bus device at %s:%d...", host, port)
        await protocol.connect()

        # Read device information
        _LOGGER.info("Reading device information...")
        device_info = await protocol.get_device_info()
        _LOGGER.info("Device Type: %s", device_info["product_type"])
        _LOGGER.info("Serial Number: %s", device_info["serial_number"])
        _LOGGER.info("Firmware Version: %d", device_info["firmware_version"])
        _LOGGER.info("HW Version: %d", device_info["hw_version"])

        # Read registers
        _LOGGER.info("\nReading registers 0-9...")
        registers = await protocol.read_registers(0, 10)
        for i, value in enumerate(registers):
            _LOGGER.info("  Register %d: %d (0x%08X)", i, value, value)

        # Read flags
        _LOGGER.info("\nReading flags 0-15...")
        flags = await protocol.read_flags(0, 16)
        for i, value in enumerate(flags):
            _LOGGER.info("  Flag %d: %s", i, value)

        # Write example (uncomment to test)
        # _LOGGER.info("\nWriting register 100...")
        # await protocol.write_register(100, 12345)
        # _LOGGER.info("Register 100 written successfully")

        # # Verify write
        # value = await protocol.read_registers(100, 1)
        # _LOGGER.info("Register 100 value: %d", value[0])

        # Write flag example (uncomment to test)
        # _LOGGER.info("\nWriting flag 0...")
        # await protocol.write_flag(0, True)
        # _LOGGER.info("Flag 0 set to True")

        # # Verify write
        # flags = await protocol.read_flags(0, 1)
        # _LOGGER.info("Flag 0 value: %s", flags[0])

    except SBusProtocolError as err:
        _LOGGER.exception("S-Bus protocol error: %s", err)
    except Exception as err:
        _LOGGER.exception("Unexpected error: %s", err)
    finally:
        # Always disconnect
        await protocol.disconnect()
        _LOGGER.info("Disconnected from S-Bus device")


if __name__ == "__main__":
    asyncio.run(main())
