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
from .const import MAX_REGISTER_COUNT
from .datapoints import build_blocks
from .sbus_protocol import SBusProtocolBase
from .sbus_protocol import SBusProtocolError
from .sbus_protocol import SBusTimeoutError
from .sbus_protocol_base import MAX_FLAGS_PER_TELEGRAM

_LOGGER = logging.getLogger(__name__)

# Connection health monitoring
MAX_CONSECUTIVE_ERRORS = 3
RECONNECT_DELAY = 5  # seconds

# Unused addresses that may be read along to save a telegram
REGISTER_GAP = 4
FLAG_GAP = 32


class SBusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching S-Bus data from the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        protocol: SBusProtocolBase,
        scan_interval: int,
        register_addresses: list[int] | None = None,
        flag_addresses: list[int] | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            protocol: S-Bus protocol handler (any protocol variant)
            scan_interval: Update interval in seconds
            register_addresses: Registers to poll
            flag_addresses: Flags to poll

        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.protocol = protocol
        self._register_blocks = build_blocks(
            register_addresses or [], MAX_REGISTER_COUNT, REGISTER_GAP
        )
        self._flag_blocks = build_blocks(
            flag_addresses or [], MAX_FLAGS_PER_TELEGRAM, FLAG_GAP
        )
        self._device_info: dict[str, Any] | None = None
        self._consecutive_errors = 0
        # The coordinator is created after the connection has been established
        self._is_connected = True

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
                _LOGGER.debug("Attempting to reconnect to S-Bus device")
                await self._async_reconnect()

            data: dict[str, Any] = {
                "registers": {},
                "flags": {},
                "timers": {},
                "counters": {},
            }

            for start, count in self._register_blocks:
                try:
                    values = await self.protocol.read_registers(start, count)
                except SBusTimeoutError:
                    raise
                except SBusProtocolError as err:
                    _LOGGER.debug("Could not read R%d+%d: %s", start, count, err)
                    continue
                for i, value in enumerate(values):
                    data["registers"][start + i] = value

            for start, count in self._flag_blocks:
                try:
                    flags = await self.protocol.read_flags(start, count)
                except SBusTimeoutError:
                    raise
                except SBusProtocolError as err:
                    _LOGGER.debug("Could not read F%d+%d: %s", start, count, err)
                    continue
                for i, value in enumerate(flags):
                    data["flags"][start + i] = value

            # Reset error counter on success
            self._consecutive_errors = 0
            self._is_connected = True

            return data

        except SBusTimeoutError as err:
            self._consecutive_errors += 1
            # The DataUpdateCoordinator logs this once when the PCD becomes
            # unavailable and once when it recovers, so no per-poll logging.
            msg = (
                f"{err}. Check IP, port, S-Bus station number and that "
                "Ether-S-Bus is enabled on the PCD"
            )
            _LOGGER.debug(
                "%s (consecutive errors: %d/%d)",
                msg,
                self._consecutive_errors,
                MAX_CONSECUTIVE_ERRORS,
            )
            raise UpdateFailed(msg) from err
        except SBusProtocolError as err:
            self._consecutive_errors += 1
            msg = f"Error communicating with S-Bus device: {err}"
            _LOGGER.debug(
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
            _LOGGER.debug("Reconnected to S-Bus device")

            # Clear cached device info to refresh it
            self._device_info = None
            self._consecutive_errors = 0
            self._is_connected = True

        except Exception as err:
            self._is_connected = False
            _LOGGER.debug("Failed to reconnect to S-Bus device: %s", err)
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
