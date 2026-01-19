"""Tests for SAIA S-Bus switch platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import patch

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_OFF
from homeassistant.const import STATE_ON

from custom_components.sbus.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_switch_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test switch platform setup."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = []

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Check that switch entities exist
        entities = hass.states.async_entity_ids("switch")
        assert len(entities) > 0


async def test_switch_turn_on(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test turning switch on."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [True] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get the first switch entity
        entities = hass.states.async_entity_ids("switch")
        assert len(entities) > 0

        # Turn on switch
        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_on",
            {"entity_id": entities[0]},
            blocking=True,
        )

        # Verify write_flag was called
        assert mock_sbus_protocol.write_flag.called


async def test_switch_turn_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test turning switch off."""
    mock_config_entry.add_to_hass(hass)

    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [False] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get the first switch entity
        entities = hass.states.async_entity_ids("switch")
        assert len(entities) > 0

        # Turn off switch
        await hass.services.async_call(
            SWITCH_DOMAIN,
            "turn_off",
            {"entity_id": entities[0]},
            blocking=True,
        )

        # Verify write_flag was called
        assert mock_sbus_protocol.write_flag.called


async def test_switch_state_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test switch state updates from coordinator."""
    mock_config_entry.add_to_hass(hass)

    # Initially off
    mock_sbus_protocol.read_registers.return_value = []
    mock_sbus_protocol.read_flags.return_value = [False] * 32

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        entities = hass.states.async_entity_ids("switch")
        assert len(entities) > 0

        # All should be OFF
        for entity_id in entities:
            state = hass.states.get(entity_id)
            assert state.state == STATE_OFF

        # Update to on
        mock_sbus_protocol.read_flags.return_value = [True] * 32
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # All should be ON
        for entity_id in entities:
            state = hass.states.get(entity_id)
            assert state.state == STATE_ON
