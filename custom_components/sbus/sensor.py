"""Sensor platform for SAIA S-Bus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SBusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up S-Bus sensor entities."""
    coordinator: SBusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device_info: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities: list[SensorEntity] = []

    # Create sensor entities for registers
    # In a real implementation, this should be configurable
    for address in range(10):  # Example: First 10 registers
        entities.append(
            SBusRegisterSensor(
                coordinator=coordinator,
                device_info=device_info,
                address=address,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)


class SBusRegisterSensor(CoordinatorEntity[SBusDataUpdateCoordinator], SensorEntity):
    """Representation of an S-Bus register sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: SBusDataUpdateCoordinator,
        device_info: dict[str, Any],
        address: int,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._address = address
        self._attr_unique_id = f"{device_info['serial_number']}_register_{address}"
        self._attr_name = f"Register {address}"

        # Device info for grouping entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_info["serial_number"])},
            "name": device_info.get("product_type", "SAIA PCD"),
            "manufacturer": "SAIA-Burgess Controls",
            "model": device_info.get("product_type"),
            "sw_version": str(device_info.get("firmware_version")),
        }

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data and "registers" in self.coordinator.data:
            return self.coordinator.data["registers"].get(self._address)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {
            "address": self._address,
            "type": "register",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._address in self.coordinator.data.get("registers", {})
        )
