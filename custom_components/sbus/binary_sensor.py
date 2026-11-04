"""Binary sensor platform for SAIA S-Bus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import CONF_WRITABLE
from .const import DOMAIN
from .datapoints import get_flags
from .entity import SBusEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up read-only flags as binary sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SBusFlagBinarySensor(data["coordinator"], data["device_info"], config)
        for config in get_flags(entry)
        if not config.get(CONF_WRITABLE)
    )


class SBusFlagBinarySensor(SBusEntity, BinarySensorEntity):
    """A read-only PCD flag."""

    _data_key = "flags"
    _unique_prefix = "flag"

    @property
    def is_on(self) -> bool | None:
        """Return true if the flag is set."""
        return self._raw
