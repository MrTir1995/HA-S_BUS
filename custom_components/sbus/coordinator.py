"""Coordinator for SAIA S-Bus integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .sbus_protocol import SBusProtocol
from .sbus_protocol import SBusProtocolError
from .sbus_protocol import SBusTimeoutError

_LOGGER = logging.getLogger(__name__)


class SBusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching S-Bus data from the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        protocol: SBusProtocol,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            protocol: S-Bus protocol handler
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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from S-Bus device.

        Returns:
            Dictionary with all data points

        Raises:
            UpdateFailed: If communication fails

        """
        try:
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

            return data

        except SBusTimeoutError as err:
            msg = f"Timeout communicating with S-Bus device: {err}"
            raise UpdateFailed(msg) from err
        except SBusProtocolError as err:
            msg = f"Error communicating with S-Bus device: {err}"
            raise UpdateFailed(msg) from err

    async def async_get_device_info(self) -> dict[str, Any]:
        """Get device information (cached).

        Returns:
            Dictionary with device information

        """
        if self._device_info is None:
            self._device_info = await self.protocol.get_device_info()
        return self._device_info
