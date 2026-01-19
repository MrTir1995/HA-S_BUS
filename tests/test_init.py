"""Tests for the SAIA S-Bus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import patch

from custom_components.sbus.const import DOMAIN
from custom_components.sbus.sbus_protocol import SBusProtocolError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test successful setup of the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify protocol methods were called
        mock_sbus_protocol.connect.assert_called_once()
        mock_sbus_protocol.get_device_info.assert_called_once()

        # Verify data is stored
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_connection_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup fails when connection fails."""
    mock_config_entry.add_to_hass(hass)

    mock_protocol = AsyncMock()
    mock_protocol.connect.side_effect = SBusProtocolError("Connection failed")

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_protocol,
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify disconnect was called
        mock_protocol.disconnect.assert_called_once()


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_sbus_protocol: AsyncMock,
) -> None:
    """Test unloading the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.sbus.SBusProtocol",
        return_value=mock_sbus_protocol,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Now unload
        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify protocol disconnect was called
        mock_sbus_protocol.disconnect.assert_called()
