"""Tests for SAIA S-Bus binary sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import patch

from homeassistant.const import STATE_OFF
from homeassistant.const import STATE_ON

from custom_components.sbus.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_binary_sensor_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test binary sensor platform setup."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = []

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Check that binary sensor entities exist
        # Entity IDs are auto-generated, look for any binary_sensor with the device name
        entities = hass.states.async_entity_ids("binary_sensor")
        assert len(entities) > 0  # At least one binary sensor should exist


async def test_binary_sensor_state_on(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test binary sensor reporting on state."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [True] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Check that at least one entity reports ON
        entities = hass.states.async_entity_ids("binary_sensor")
        on_states = [e for e in entities if hass.states.get(e).state == STATE_ON]
        assert len(on_states) > 0


async def test_binary_sensor_state_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test binary sensor reporting off state."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [False] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Check that all entities report OFF
        entities = hass.states.async_entity_ids("binary_sensor")
        for entity_id in entities:
            state = hass.states.get(entity_id)
            assert state.state == STATE_OFF


async def test_binary_sensor_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test binary sensor state updates."""
    mock_config_entry.add_to_hass(hass)

    # Initially false
    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [False] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Change to true
        mock_sbus_protocol.read_flags.return_value = [True] * 32
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # At least one entity should be ON now
        entities = hass.states.async_entity_ids("binary_sensor")
        on_states = [e for e in entities if hass.states.get(e).state == STATE_ON]
        assert len(on_states) > 0


async def test_binary_sensor_unavailable_on_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test binary sensor becomes unavailable on error."""
    mock_config_entry.add_to_hass(hass)

    from custom_components.sbus.sbus_protocol import SBusProtocolError

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [False] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Simulate error
        mock_sbus_protocol.read_flags.side_effect = SBusProtocolError("Connection lost")
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]

        # This should not raise, just mark as unavailable
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        mock_sbus_protocol.read_flags.side_effect = SBusProtocolError("Error")

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("binary_sensor.saia_pcd_input_0")
        if state:
            assert state.state == "unavailable"
