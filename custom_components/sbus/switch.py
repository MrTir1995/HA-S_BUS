"""Switch platform for SAIA S-Bus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_WRITABLE
from .const import DOMAIN
from .datapoints import get_flags
from .entity import SBusEntity
from .sbus_protocol import SBusProtocolError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SBusDataUpdateCoordinator
    from .sbus_protocol import SBusProtocolBase


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable flags as switches."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SBusFlagSwitch(data["coordinator"], data["device_info"], config, data["protocol"])
        for config in get_flags(entry)
        if config.get(CONF_WRITABLE)
    )


class SBusFlagSwitch(SBusEntity, SwitchEntity):
    """A writable PCD flag."""

    _data_key = "flags"
    _unique_prefix = "flag_switch"

    def __init__(
        self,
        coordinator: SBusDataUpdateCoordinator,
        device_info: dict[str, Any],
        config: dict[str, Any],
        protocol: SBusProtocolBase,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_info, config)
        self._protocol = protocol

    @property
    def is_on(self) -> bool | None:
        """Return true if the flag is set."""
        return self._raw

    async def _async_write(self, value: bool) -> None:  # noqa: FBT001
        try:
            await self._protocol.write_flag(self._address, value)
        except SBusProtocolError as err:
            msg = f"Failed to write flag F{self._address}: {err}"
            raise HomeAssistantError(msg) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Set the flag."""
        await self._async_write(True)  # noqa: FBT003

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Reset the flag."""
        await self._async_write(False)  # noqa: FBT003
