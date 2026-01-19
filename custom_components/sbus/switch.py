"""Switch platform for SAIA S-Bus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SBusDataUpdateCoordinator
from .sbus_protocol import SBusProtocol
from .sbus_protocol import SBusProtocolError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up S-Bus switch entities."""
    coordinator: SBusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device_info: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]["device_info"]
    protocol: SBusProtocol = hass.data[DOMAIN][entry.entry_id]["protocol"]

    entities: list[SwitchEntity] = []

    # Create switch entities for writable flags
    # In a real implementation, this should be configurable
    for address in range(8):  # Example: First 8 flags as switches
        entities.append(
            SBusFlagSwitch(
                coordinator=coordinator,
                protocol=protocol,
                device_info=device_info,
                address=address,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)


class SBusFlagSwitch(CoordinatorEntity[SBusDataUpdateCoordinator], SwitchEntity):
    """Representation of an S-Bus flag switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SBusDataUpdateCoordinator,
        protocol: SBusProtocol,
        device_info: dict[str, Any],
        address: int,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)

        self._protocol = protocol
        self._address = address
        self._attr_unique_id = f"{device_info['serial_number']}_flag_switch_{address}"
        self._attr_name = f"Flag Switch {address}"

        # Device info for grouping entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_info["serial_number"])},
            "name": device_info.get("product_type", "SAIA PCD"),
            "manufacturer": "SAIA-Burgess Controls",
            "model": device_info.get("product_type"),
            "sw_version": str(device_info.get("firmware_version")),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self.coordinator.data and "flags" in self.coordinator.data:
            return self.coordinator.data["flags"].get(self._address)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self._protocol.write_flag(self._address, True)
            # Request immediate coordinator refresh
            await self.coordinator.async_request_refresh()
        except SBusProtocolError:
            _LOGGER.exception("Failed to turn on flag %d", self._address)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self._protocol.write_flag(self._address, False)
            # Request immediate coordinator refresh
            await self.coordinator.async_request_refresh()
        except SBusProtocolError:
            _LOGGER.exception("Failed to turn off flag %d", self._address)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {
            "address": self._address,
            "type": "flag",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._address in self.coordinator.data.get("flags", {})
        )
