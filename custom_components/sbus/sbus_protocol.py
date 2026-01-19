"""S-Bus Protocol implementation for SAIA PCD controllers.

This module provides a factory function and imports for all S-Bus protocol variants:
- Ether-S-Bus (UDP/TCP)
- Serial-S-Bus (USB or TCP serial bridges)
- Profi-S-Bus (Profibus)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    pass

from .const import CONNECTION_TYPE_TCP
from .const import CONNECTION_TYPE_TCP_SERIAL
from .const import CONNECTION_TYPE_UDP
from .const import CONNECTION_TYPE_USB
from .const import PROTOCOL_ETHER_SBUS
from .const import PROTOCOL_PROFI_SBUS
from .const import PROTOCOL_SERIAL_SBUS
from .ether_sbus import EtherSBusProtocol
from .profi_sbus import ProfiSBusProtocol
from .sbus_protocol_base import SBusCRCError
from .sbus_protocol_base import SBusProtocolBase
from .sbus_protocol_base import SBusProtocolError
from .sbus_protocol_base import SBusTimeoutError
from .serial_sbus import SerialSBusProtocol

__all__ = [
    "SBusProtocol",
    "EtherSBusProtocol",
    "SerialSBusProtocol",
    "ProfiSBusProtocol",
    "SBusProtocolBase",
    "SBusProtocolError",
    "SBusTimeoutError",
    "SBusCRCError",
    "create_sbus_protocol",
]

# Legacy alias for backward compatibility
SBusProtocol = EtherSBusProtocol


def create_sbus_protocol(config: dict[str, Any]) -> SBusProtocolBase:
    """Create appropriate S-Bus protocol instance based on configuration.

    Args:
        config: Configuration dictionary containing protocol type and parameters

    Returns:
        Instance of appropriate S-Bus protocol class

    Raises:
        ValueError: If protocol type is invalid or required parameters are missing

    """
    protocol_type = config.get("protocol_type", PROTOCOL_ETHER_SBUS)
    station = config.get("station", 0)
    timeout = config.get("timeout", 5)

    if protocol_type == PROTOCOL_ETHER_SBUS:
        # Ether-S-Bus (UDP or TCP)
        host = config.get("host")
        port = config.get("port", 5050)
        connection_type = config.get("connection_type", CONNECTION_TYPE_UDP)

        if not host:
            msg = "Host is required for Ether-S-Bus"
            raise ValueError(msg)

        use_tcp = connection_type == CONNECTION_TYPE_TCP

        return EtherSBusProtocol(
            host=host,
            port=port,
            station=station,
            use_tcp=use_tcp,
            timeout=timeout,
        )

    if protocol_type == PROTOCOL_SERIAL_SBUS:
        # Serial-S-Bus (USB or TCP serial bridge)
        serial_port = config.get("serial_port")
        baudrate = config.get("baudrate", 9600)
        connection_type = config.get("connection_type", CONNECTION_TYPE_USB)

        if not serial_port:
            msg = "Serial port is required for Serial-S-Bus"
            raise ValueError(msg)

        use_tcp = connection_type == CONNECTION_TYPE_TCP_SERIAL

        return SerialSBusProtocol(
            port=serial_port,
            station=station,
            baudrate=baudrate,
            use_tcp=use_tcp,
            timeout=timeout,
        )

    if protocol_type == PROTOCOL_PROFI_SBUS:
        # Profi-S-Bus (Profibus)
        host = config.get("host")
        port = config.get("port", 5050)
        profibus_address = config.get("profibus_address", 0)

        if not host:
            msg = "Host is required for Profi-S-Bus"
            raise ValueError(msg)

        return ProfiSBusProtocol(
            host=host,
            port=port,
            station=station,
            profibus_address=profibus_address,
            timeout=timeout,
        )

    msg = f"Unknown protocol type: {protocol_type}"
    raise ValueError(msg)
