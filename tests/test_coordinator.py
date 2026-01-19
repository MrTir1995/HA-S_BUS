"""Tests for SAIA S-Bus coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.sbus.coordinator import SBusDataUpdateCoordinator
from custom_components.sbus.sbus_protocol import SBusProtocolError
from custom_components.sbus.sbus_protocol import SBusTimeoutError

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_coordinator_update_success(
    hass: HomeAssistant,
    mock_sbus_protocol: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful coordinator update."""
    mock_config_entry.add_to_hass(hass)
    coordinator = SBusDataUpdateCoordinator(
        hass,
        mock_sbus_protocol,
        30,
    )

    mock_sbus_protocol.read_registers.return_value = [100, 200, 300]
    mock_sbus_protocol.read_flags.return_value = [True, False, True, False]

    await coordinator.async_refresh()

    assert coordinator.data is not None
    assert "registers" in coordinator.data
    assert "flags" in coordinator.data
    assert coordinator.data["registers"] == {0: 100, 1: 200, 2: 300}
    assert coordinator.data["flags"] == {0: True, 1: False, 2: True, 3: False}


async def test_coordinator_update_timeout(
    hass: HomeAssistant,
    mock_sbus_protocol: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator handles timeout."""
    mock_config_entry.add_to_hass(hass)
    coordinator = SBusDataUpdateCoordinator(
        hass,
        mock_sbus_protocol,
        30,
    )

    mock_sbus_protocol.read_registers.side_effect = SBusTimeoutError("Timeout")

    await coordinator.async_refresh()

    # After timeout, coordinator should mark update as failed
    assert not coordinator.last_update_success


async def test_coordinator_update_protocol_error(
    hass: HomeAssistant,
    mock_sbus_protocol: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator handles protocol errors gracefully."""
    mock_config_entry.add_to_hass(hass)
    coordinator = SBusDataUpdateCoordinator(
        hass,
        mock_sbus_protocol,
        30,
    )

    # Protocol error on registers, but flags succeed
    mock_sbus_protocol.read_registers.side_effect = SBusProtocolError("Error")
    mock_sbus_protocol.read_flags.return_value = [True, False]

    await coordinator.async_refresh()

    # Even with partial failure, coordinator should succeed if some data was read
    assert coordinator.last_update_success
    assert coordinator.data is not None
    assert "flags" in coordinator.data


async def test_coordinator_partial_data(
    hass: HomeAssistant,
    mock_sbus_protocol: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator continues with partial data if flags fail."""
    mock_config_entry.add_to_hass(hass)
    coordinator = SBusDataUpdateCoordinator(
        hass,
        mock_sbus_protocol,
        30,
    )

    mock_sbus_protocol.read_registers.return_value = [100, 200, 300]
    mock_sbus_protocol.read_flags.side_effect = SBusProtocolError("Flag read failed")

    await coordinator.async_refresh()

    assert coordinator.data is not None
    assert "registers" in coordinator.data
    assert coordinator.data["registers"] == {0: 100, 1: 200, 2: 300}
    # Flags should still be present but empty/default
    assert "flags" in coordinator.data
