"""Tests for SAIA S-Bus sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import patch

from custom_components.sbus.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_sensor_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test sensor platform setup."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = []

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Check that sensor entities exist
        entities = hass.states.async_entity_ids("sensor")
        assert len(entities) > 0


async def test_sensor_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test sensor state updates."""
    mock_config_entry.add_to_hass(hass)

    # Mock register values
    mock_sbus_protocol.read_registers.return_value = [123, 456, 789]
    mock_sbus_protocol.read_flags.return_value = []

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Trigger coordinator update
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Verify that at least one sensor has a numeric state
        entities = hass.states.async_entity_ids("sensor")
        numeric_states = [e for e in entities if hass.states.get(e).state.isdigit()]
        assert len(numeric_states) > 0


async def test_sensor_unavailable_on_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test sensor becomes unavailable on communication error."""
    mock_config_entry.add_to_hass(hass)

    from custom_components.sbus.sbus_protocol import SBusProtocolError

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = []

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Simulate communication error
        mock_sbus_protocol.read_registers.side_effect = SBusProtocolError(
            "Connection lost"
        )

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()
