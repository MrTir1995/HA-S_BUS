"""Binary sensor platform for SAIA S-Bus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up S-Bus binary sensor entities."""
    coordinator: SBusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device_info: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities: list[BinarySensorEntity] = []

    # Create binary sensor entities for flags
    # In a real implementation, this should be configurable
    for address in range(32):  # Example: First 32 flags
        entities.append(
            SBusFlagBinarySensor(
                coordinator=coordinator,
                device_info=device_info,
                address=address,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)


class SBusFlagBinarySensor(
    CoordinatorEntity[SBusDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Representation of an S-Bus flag binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SBusDataUpdateCoordinator,
        device_info: dict[str, Any],
        address: int,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self._address = address
        self._attr_unique_id = f"{device_info['serial_number']}_flag_{address}"
        self._attr_name = f"Flag {address}"

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
        """Return true if the binary sensor is on."""
        if self.coordinator.data and "flags" in self.coordinator.data:
            return self.coordinator.data["flags"].get(self._address)
        return None

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
