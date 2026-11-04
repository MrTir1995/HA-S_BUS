"""Configured S-Bus data points (registers and flags).

Registers and flags are stored in the config entry options. As long as the
user has not configured anything, the legacy defaults (R 0-9, F 0-31,
switches on F 0-7) are used so existing installations keep their entities.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass

from .const import CONF_ADDRESS
from .const import CONF_DATA_TYPE
from .const import CONF_FACTOR
from .const import CONF_FLAGS
from .const import CONF_NAME
from .const import CONF_REGISTERS
from .const import CONF_UNIT
from .const import CONF_WRITABLE
from .const import DATA_TYPE_FLOAT
from .const import DATA_TYPE_SIGNED
from .const import DATA_TYPE_UNSIGNED
from .const import LEGACY_FLAGS
from .const import LEGACY_REGISTERS
from .const import LEGACY_SWITCHES

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_UNIT_CLASSES: dict[str, tuple[SensorDeviceClass | None, SensorStateClass]] = {
    "°C": (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "bar": (SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    "Pa": (SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    "kWh": (SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "Wh": (SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "kW": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "W": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "m³": (SensorDeviceClass.VOLUME, SensorStateClass.TOTAL_INCREASING),
    "m³/h": (SensorDeviceClass.VOLUME_FLOW_RATE, SensorStateClass.MEASUREMENT),
    "V": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "A": (SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "h": (SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING),
}


def is_configured(entry: ConfigEntry) -> bool:
    """Return True once the user has configured data points."""
    return CONF_REGISTERS in entry.options or CONF_FLAGS in entry.options


def get_registers(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Return the register configurations, sorted by address."""
    if not is_configured(entry):
        return [
            {
                CONF_ADDRESS: address,
                CONF_NAME: f"Register {address}",
                CONF_DATA_TYPE: DATA_TYPE_UNSIGNED,
                CONF_FACTOR: 1.0,
                CONF_UNIT: None,
            }
            for address in LEGACY_REGISTERS
        ]
    return sorted(entry.options.get(CONF_REGISTERS, []), key=lambda r: r[CONF_ADDRESS])


def get_flags(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Return the flag configurations, sorted by address.

    In legacy mode every flag gets a binary sensor and the first eight
    flags additionally a switch, as before.
    """
    if not is_configured(entry):
        return [
            {
                CONF_ADDRESS: address,
                CONF_NAME: f"Flag {address}",
                CONF_WRITABLE: False,
            }
            for address in LEGACY_FLAGS
        ] + [
            {
                CONF_ADDRESS: address,
                CONF_NAME: f"Flag Switch {address}",
                CONF_WRITABLE: True,
            }
            for address in LEGACY_SWITCHES
        ]
    return sorted(entry.options.get(CONF_FLAGS, []), key=lambda f: f[CONF_ADDRESS])


def unit_classes(unit: str | None) -> tuple[SensorDeviceClass | None, SensorStateClass]:
    """Return device class and state class for a unit."""
    return _UNIT_CLASSES.get(unit or "", (None, SensorStateClass.MEASUREMENT))


def convert_register(raw: int, data_type: str, factor: float) -> float | int:
    """Convert a raw 32 bit register value."""
    if data_type == DATA_TYPE_FLOAT:
        value: float | int = struct.unpack("!f", struct.pack("!I", raw & 0xFFFFFFFF))[0]
    elif data_type == DATA_TYPE_SIGNED:
        value = raw - 0x100000000 if raw & 0x80000000 else raw
    else:
        value = raw
    if factor != 1:
        return value * factor
    return value


def decimals_for_factor(factor: float) -> int:
    """Return the number of decimals a factor implies (0.1 -> 1, 0.01 -> 2)."""
    text = f"{factor:.6f}".rstrip("0").rstrip(".")
    return len(text.split(".")[1]) if "." in text else 0


def build_blocks(
    addresses: list[int] | set[int], max_size: int, max_gap: int
) -> list[tuple[int, int]]:
    """Group addresses into read blocks ``(start, count)``.

    Neighbouring addresses are read with one telegram as long as the block
    does not exceed ``max_size`` and the gap between them is at most
    ``max_gap`` (reading a few unused addresses is cheaper than an extra
    round trip).
    """
    blocks: list[tuple[int, int]] = []
    for address in sorted(set(addresses)):
        if blocks:
            start, count = blocks[-1]
            end = start + count - 1
            if address - end - 1 <= max_gap and address - start + 1 <= max_size:
                blocks[-1] = (start, address - start + 1)
                continue
        blocks.append((address, 1))
    return blocks
