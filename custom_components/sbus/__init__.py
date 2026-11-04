"""The SAIA S-Bus integration."""

from __future__ import annotations

import logging
import struct
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.const import Platform
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.core import ServiceCall
    from homeassistant.core import ServiceResponse

from .const import ATTR_ADDRESS
from .const import ATTR_COUNT
from .const import ATTR_START_ADDRESS
from .const import ATTR_VALUE
from .const import CONF_SCAN_INTERVAL
from .const import CONF_STATION
from .const import DEFAULT_SCAN_INTERVAL
from .const import DEFAULT_STATION
from .const import DOMAIN
from .const import SERVICE_READ_FLAG
from .const import SERVICE_READ_REGISTER
from .const import SERVICE_WRITE_FLAG
from .const import SERVICE_WRITE_REGISTER
from .coordinator import SBusDataUpdateCoordinator
from .sbus_protocol import SBusProtocolError
from .sbus_protocol import create_sbus_protocol

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SAIA S-Bus from a config entry."""
    # Get scan interval from entry data
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Create S-Bus protocol instance using factory
    protocol = create_sbus_protocol(entry.data)

    try:
        # Connect to device
        await protocol.connect()

        # Verify connection by reading device info
        device_info = await protocol.get_device_info()

        _LOGGER.info(
            "Connected to S-Bus device: %s (S/N: %s) via %s",
            device_info.get("product_type", "Unknown"),
            device_info.get("serial_number", "Unknown"),
            entry.data.get("protocol_type", "Ether-S-Bus"),
        )

    except SBusProtocolError as err:
        await protocol.disconnect()
        protocol_info = entry.data.get("protocol_type", "S-Bus")
        connection_info = entry.data.get(CONF_HOST, entry.data.get("serial_port", "device"))
        msg = f"Failed to connect to {protocol_info} device at {connection_info}"
        raise ConfigEntryNotReady(msg) from err

    # Create data update coordinator
    coordinator = SBusDataUpdateCoordinator(
        hass,
        protocol,
        scan_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and protocol
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "protocol": protocol,
        "device_info": device_info,
    }

    # Register device in device registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device_info["serial_number"])},
        name=device_info.get("product_type", "SAIA PCD"),
        manufacturer="SAIA-Burgess Controls",
        model=device_info.get("product_type"),
        sw_version=str(device_info.get("firmware_version")),
        serial_number=device_info.get("serial_number"),
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    def _get_protocols(call: ServiceCall) -> list:
        """Return the protocol instances targeted by a service call."""
        device_ids = call.data.get("device_id") or []
        if isinstance(device_ids, str):
            device_ids = [device_ids]
        registry = dr.async_get(hass)
        entry_ids = {
            entry_id
            for device_id in device_ids
            if (device := registry.async_get(device_id))
            for entry_id in device.config_entries
        }
        protocols = [
            data["protocol"]
            for entry_id, data in hass.data[DOMAIN].items()
            if isinstance(data, dict)
            and "protocol" in data
            and (not entry_ids or entry_id in entry_ids)
        ]
        if not protocols:
            msg = "No S-Bus device found for this action"
            raise HomeAssistantError(msg)
        return protocols

    async def handle_read_register(call: ServiceCall) -> ServiceResponse:
        """Handle read_register service call."""
        start_address = int(call.data[ATTR_START_ADDRESS])
        count = int(call.data.get(ATTR_COUNT, 1))
        protocol_instance = _get_protocols(call)[0]
        try:
            values = await protocol_instance.read_registers(start_address, count)
        except SBusProtocolError as err:
            msg = f"Failed to read registers R{start_address}: {err}"
            raise HomeAssistantError(msg) from err
        _LOGGER.debug("Read registers R%d+%d: %s", start_address, count, values)
        return {
            "registers": {
                f"R{start_address + i}": {
                    "value": value,
                    "signed": value - 0x100000000 if value & 0x80000000 else value,
                    "hex": f"0x{value:08X}",
                    "float_ieee": round(struct.unpack("!f", struct.pack("!I", value))[0], 6),
                }
                for i, value in enumerate(values)
            }
        }

    async def handle_write_register(call: ServiceCall) -> None:
        """Handle write_register service call."""
        address = int(call.data[ATTR_ADDRESS])
        value = int(call.data[ATTR_VALUE])
        try:
            for protocol_instance in _get_protocols(call):
                await protocol_instance.write_register(address, value)
        except SBusProtocolError as err:
            msg = f"Failed to write register R{address}: {err}"
            raise HomeAssistantError(msg) from err

    async def handle_read_flag(call: ServiceCall) -> ServiceResponse:
        """Handle read_flag service call."""
        start_address = int(call.data[ATTR_START_ADDRESS])
        count = int(call.data.get(ATTR_COUNT, 1))
        protocol_instance = _get_protocols(call)[0]
        try:
            values = await protocol_instance.read_flags(start_address, count)
        except SBusProtocolError as err:
            msg = f"Failed to read flags F{start_address}: {err}"
            raise HomeAssistantError(msg) from err
        return {"flags": {f"F{start_address + i}": v for i, v in enumerate(values)}}

    async def handle_write_flag(call: ServiceCall) -> None:
        """Handle write_flag service call."""
        address = int(call.data[ATTR_ADDRESS])
        value = bool(call.data[ATTR_VALUE])
        try:
            for protocol_instance in _get_protocols(call):
                await protocol_instance.write_flag(address, value)
        except SBusProtocolError as err:
            msg = f"Failed to write flag F{address}: {err}"
            raise HomeAssistantError(msg) from err

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_READ_REGISTER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_READ_REGISTER,
            handle_read_register,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_WRITE_REGISTER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_WRITE_REGISTER,
            handle_write_register,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_READ_FLAG):
        hass.services.async_register(
            DOMAIN,
            SERVICE_READ_FLAG,
            handle_read_flag,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_WRITE_FLAG):
        hass.services.async_register(
            DOMAIN,
            SERVICE_WRITE_FLAG,
            handle_write_flag,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Shutdown coordinator and disconnect protocol
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator = data["coordinator"]
        await coordinator.async_shutdown()

        _LOGGER.info("Disconnected from S-Bus device")

    return unload_ok
