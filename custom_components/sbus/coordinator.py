"""Coordinator for SAIA S-Bus integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .sbus_protocol import SBusProtocolBase
from .sbus_protocol import SBusProtocolError
from .sbus_protocol import SBusTimeoutError

_LOGGER = logging.getLogger(__name__)

# Connection health monitoring
MAX_CONSECUTIVE_ERRORS = 3
RECONNECT_DELAY = 5  # seconds


class SBusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching S-Bus data from the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        protocol: SBusProtocolBase,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            protocol: S-Bus protocol handler (any protocol variant)
            scan_interval: Update interval in seconds

        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.protocol = protocol
        self._device_info: dict[str, Any] | None = None
        self._consecutive_errors = 0
        self._is_connected = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from S-Bus device.

        Returns:
            Dictionary with all data points

        Raises:
            UpdateFailed: If communication fails

        """
        try:
            # Check if we need to reconnect
            if not self._is_connected or self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                _LOGGER.info("Attempting to reconnect to S-Bus device...")
                await self._async_reconnect()

            data: dict[str, Any] = {
                "registers": {},
                "flags": {},
                "timers": {},
                "counters": {},
            }

            # Example: Read first 10 registers
            # In a real implementation, this should be configurable
            # or dynamically determined based on configured entities
            try:
                registers = await self.protocol.read_registers(0, 10)
                for i, value in enumerate(registers):
                    data["registers"][i] = value
            except SBusTimeoutError:
                # Timeout is critical, re-raise
                raise
            except SBusProtocolError as err:
                _LOGGER.debug("Could not read registers: %s", err)

            # Example: Read first 32 flags
            try:
                flags = await self.protocol.read_flags(0, 32)
                for i, value in enumerate(flags):
                    data["flags"][i] = value
            except SBusTimeoutError:
                # Timeout is critical, re-raise
                raise
            except SBusProtocolError as err:
                _LOGGER.debug("Could not read flags: %s", err)

            # Reset error counter on success
            self._consecutive_errors = 0
            self._is_connected = True

            return data

        except SBusTimeoutError as err:
            self._consecutive_errors += 1
            msg = f"Timeout communicating with S-Bus device: {err}"
            _LOGGER.warning(
                "%s (consecutive errors: %d/%d)",
                msg,
                self._consecutive_errors,
                MAX_CONSECUTIVE_ERRORS,
            )
            raise UpdateFailed(msg) from err
        except SBusProtocolError as err:
            self._consecutive_errors += 1
            msg = f"Error communicating with S-Bus device: {err}"
            _LOGGER.warning(
                "%s (consecutive errors: %d/%d)",
                msg,
                self._consecutive_errors,
                MAX_CONSECUTIVE_ERRORS,
            )
            raise UpdateFailed(msg) from err

    async def _async_reconnect(self) -> None:
        """Attempt to reconnect to the device.

        Raises:
            UpdateFailed: If reconnection fails

        """
        try:
            # Close existing connection
            await self.protocol.disconnect()

            # Wait before reconnecting
            await asyncio.sleep(RECONNECT_DELAY)

            # Attempt to reconnect
            await self.protocol.connect()
            _LOGGER.info("Successfully reconnected to S-Bus device")

            # Clear cached device info to refresh it
            self._device_info = None
            self._consecutive_errors = 0
            self._is_connected = True

        except Exception as err:
            self._is_connected = False
            _LOGGER.error("Failed to reconnect to S-Bus device: %s", err)
            raise UpdateFailed(f"Reconnection failed: {err}") from err

    async def async_get_device_info(self) -> dict[str, Any]:
        """Get device information (cached).

        Returns:
            Dictionary with device information

        """
        if self._device_info is None:
            self._device_info = await self.protocol.get_device_info()
        return self._device_info

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and close connections."""
        _LOGGER.debug("Shutting down S-Bus coordinator")
        try:
            await self.protocol.disconnect()
        except Exception as err:
            _LOGGER.error("Error disconnecting protocol: %s", err)
        self._is_connected = False
