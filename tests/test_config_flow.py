"""Tests for SAIA S-Bus config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant import data_entry_flow
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sbus.const import CONF_SCAN_INTERVAL
from custom_components.sbus.const import CONF_STATION
from custom_components.sbus.const import DEFAULT_PORT
from custom_components.sbus.const import DEFAULT_SCAN_INTERVAL
from custom_components.sbus.const import DEFAULT_STATION
from custom_components.sbus.const import DOMAIN
from custom_components.sbus.const import ERROR_CANNOT_CONNECT
from custom_components.sbus.const import ERROR_TIMEOUT
from custom_components.sbus.sbus_protocol import SBusProtocolError
from custom_components.sbus.sbus_protocol import SBusTimeoutError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_device_info():
    """Return mock device info."""
    return {
        "firmware_version": 100,
        "product_type": "PCD1.M2120",
        "hw_version": 1,
        "serial_number": "12345678ABCDEF12",
    }


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_device_info: dict,
) -> None:
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.sbus.config_flow.validate_connection",
        return_value=mock_device_info,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: DEFAULT_PORT,
                CONF_STATION: DEFAULT_STATION,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "PCD1.M2120 (192.168.1.100)"
    assert result["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: DEFAULT_PORT,
        CONF_STATION: DEFAULT_STATION,
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    }


async def test_user_flow_timeout_error(hass: HomeAssistant) -> None:
    """Test user flow with timeout error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    with patch(
        "custom_components.sbus.config_flow.validate_connection",
        side_effect=SBusTimeoutError("Timeout"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: DEFAULT_PORT,
                CONF_STATION: DEFAULT_STATION,
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": ERROR_TIMEOUT}


async def test_user_flow_connection_error(hass: HomeAssistant) -> None:
    """Test user flow with connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    with patch(
        "custom_components.sbus.config_flow.validate_connection",
        side_effect=SBusProtocolError("Connection failed"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: DEFAULT_PORT,
                CONF_STATION: DEFAULT_STATION,
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": ERROR_CANNOT_CONNECT}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_device_info: dict,
) -> None:
    """Test user flow when device is already configured."""
    # Create existing config entry
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=mock_device_info["serial_number"],
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: DEFAULT_PORT,
            CONF_STATION: DEFAULT_STATION,
        },
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    with patch(
        "custom_components.sbus.config_flow.validate_connection",
        return_value=mock_device_info,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.200",  # Different IP, same device
                CONF_PORT: DEFAULT_PORT,
                CONF_STATION: DEFAULT_STATION,
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 60},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # The options flow returns user_input as data
    assert result["data"] == {CONF_SCAN_INTERVAL: 60}


async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_device_info: dict,
) -> None:
    """Test reconfigure flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.sbus.config_flow.validate_connection",
        return_value=mock_device_info,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.200",
                CONF_PORT: 5051,
                CONF_STATION: 1,
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
