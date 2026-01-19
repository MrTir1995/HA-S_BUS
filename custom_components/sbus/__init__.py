"""The SAIA S-Bus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.core import ServiceCall

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
from .sbus_protocol import SBusProtocol
from .sbus_protocol import SBusProtocolError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SAIA S-Bus from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    station = entry.data.get(CONF_STATION, DEFAULT_STATION)
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Create S-Bus protocol instance
    protocol = SBusProtocol(host, port, station)

    try:
        # Connect to device
        await protocol.connect()

        # Verify connection by reading device info
        device_info = await protocol.get_device_info()

        _LOGGER.info(
            "Connected to S-Bus device: %s (S/N: %s)",
            device_info.get("product_type", "Unknown"),
            device_info.get("serial_number", "Unknown"),
        )

    except SBusProtocolError as err:
        await protocol.disconnect()
        msg = f"Failed to connect to S-Bus device at {host}:{port}"
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
    async def handle_read_register(call: ServiceCall) -> None:
        """Handle read_register service call."""
        call.data["device_id"]
        start_address = call.data[ATTR_START_ADDRESS]
        count = call.data.get(ATTR_COUNT, 1)

        # Find the protocol for this device
        for entry_data in hass.data[DOMAIN].values():
            if isinstance(entry_data, dict):
                protocol_instance = entry_data.get("protocol")
                if protocol_instance:
                    try:
                        values = await protocol_instance.read_registers(
                            start_address,
                            count,
                        )
                        _LOGGER.info(
                            "Read registers R%d-%d: %s",
                            start_address,
                            start_address + count - 1,
                            values,
                        )
                    except SBusProtocolError:
                        _LOGGER.exception("Failed to read registers")
                    break

    async def handle_write_register(call: ServiceCall) -> None:
        """Handle write_register service call."""
        call.data["device_id"]
        address = call.data[ATTR_ADDRESS]
        value = call.data[ATTR_VALUE]

        # Find the protocol for this device
        for entry_data in hass.data[DOMAIN].values():
            if isinstance(entry_data, dict):
                protocol_instance = entry_data.get("protocol")
                if protocol_instance:
                    try:
                        await protocol_instance.write_register(address, value)
                        _LOGGER.info("Wrote register R%d = %d", address, value)
                    except SBusProtocolError:
                        _LOGGER.exception("Failed to write register")
                    break

    async def handle_read_flag(call: ServiceCall) -> None:
        """Handle read_flag service call."""
        call.data["device_id"]
        start_address = call.data[ATTR_START_ADDRESS]
        count = call.data.get(ATTR_COUNT, 1)

        # Find the protocol for this device
        for entry_data in hass.data[DOMAIN].values():
            if isinstance(entry_data, dict):
                protocol_instance = entry_data.get("protocol")
                if protocol_instance:
                    try:
                        values = await protocol_instance.read_flags(
                            start_address, count
                        )
                        _LOGGER.info(
                            "Read flags F%d-%d: %s",
                            start_address,
                            start_address + count - 1,
                            values,
                        )
                    except SBusProtocolError:
                        _LOGGER.exception("Failed to read flags")
                    break

    async def handle_write_flag(call: ServiceCall) -> None:
        """Handle write_flag service call."""
        call.data["device_id"]
        address = call.data[ATTR_ADDRESS]
        value = call.data[ATTR_VALUE]

        # Find the protocol for this device
        for entry_data in hass.data[DOMAIN].values():
            if isinstance(entry_data, dict):
                protocol_instance = entry_data.get("protocol")
                if protocol_instance:
                    try:
                        await protocol_instance.write_flag(address, value)
                        _LOGGER.info("Wrote flag F%d = %s", address, value)
                    except SBusProtocolError:
                        _LOGGER.exception("Failed to write flag")
                    break

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_READ_REGISTER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_READ_REGISTER,
            handle_read_register,
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
        # Disconnect protocol
        data = hass.data[DOMAIN].pop(entry.entry_id)
        protocol = data["protocol"]
        await protocol.disconnect()

        _LOGGER.info("Disconnected from S-Bus device")

    return unload_ok
