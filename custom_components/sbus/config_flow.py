"""Config flow for SAIA S-Bus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant import data_entry_flow
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult

from .const import BAUDRATES
from .const import CONF_BAUDRATE
from .const import CONF_CONNECTION_TYPE
from .const import CONF_PROTOCOL_TYPE
from .const import CONF_SCAN_INTERVAL
from .const import CONF_SERIAL_PORT
from .const import CONF_STATION
from .const import CONNECTION_TYPE_TCP
from .const import CONNECTION_TYPE_TCP_SERIAL
from .const import CONNECTION_TYPE_UDP
from .const import CONNECTION_TYPE_USB
from .const import DEFAULT_BAUDRATE
from .const import DEFAULT_PORT_TCP
from .const import DEFAULT_PORT_UDP
from .const import DEFAULT_SCAN_INTERVAL
from .const import DEFAULT_STATION
from .const import DOMAIN
from .const import ERROR_CANNOT_CONNECT
from .const import ERROR_SERIAL_PORT_NOT_FOUND
from .const import ERROR_TIMEOUT
from .const import ERROR_UNKNOWN
from .const import PROTOCOL_ETHER_SBUS
from .const import PROTOCOL_PROFI_SBUS
from .const import PROTOCOL_SERIAL_SBUS
from .sbus_protocol import SBusProtocolError
from .sbus_protocol import SBusTimeoutError
from .sbus_protocol import create_sbus_protocol

_LOGGER = logging.getLogger(__name__)


async def validate_connection(
    hass: HomeAssistant,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Validate the connection to the S-Bus device.

    Args:
        hass: Home Assistant instance
        config: Configuration dictionary

    Returns:
        Dictionary with device information

    Raises:
        SBusTimeoutError: If connection times out
        SBusProtocolError: For other protocol errors

    """
    protocol = create_sbus_protocol(config)

    try:
        await protocol.connect()
        return await protocol.get_device_info()
    finally:
        await protocol.disconnect()


class SBusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SAIA S-Bus."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._protocol_type: str | None = None
        self._connection_type: str | None = None
        self._config_data: dict[str, Any] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step - protocol selection."""
        if user_input is not None:
            self._protocol_type = user_input[CONF_PROTOCOL_TYPE]
            self._config_data[CONF_PROTOCOL_TYPE] = self._protocol_type

            # Route to appropriate configuration step
            if self._protocol_type == PROTOCOL_ETHER_SBUS:
                return await self.async_step_ether_sbus()
            if self._protocol_type == PROTOCOL_SERIAL_SBUS:
                return await self.async_step_serial_sbus()
            if self._protocol_type == PROTOCOL_PROFI_SBUS:
                return await self.async_step_profi_sbus()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PROTOCOL_TYPE, default=PROTOCOL_ETHER_SBUS): vol.In(
                    {
                        PROTOCOL_ETHER_SBUS: "Ether-S-Bus (UDP/TCP)",
                        PROTOCOL_SERIAL_SBUS: "Serial-S-Bus (USB/TCP Serial)",
                        PROTOCOL_PROFI_SBUS: "Profi-S-Bus (Profibus)",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    async def async_step_ether_sbus(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Ether-S-Bus configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config_data.update(user_input)

            try:
                device_info = await validate_connection(
                    self.hass,
                    self._config_data,
                )

                await self.async_set_unique_id(device_info["serial_number"])
                self._abort_if_unique_id_configured()

                host = user_input[CONF_HOST]
                title = f"{device_info.get('product_type', 'SAIA PCD')} ({host})"

                return self.async_create_entry(
                    title=title,
                    data=self._config_data,
                )

            except data_entry_flow.AbortFlow:
                raise
            except SBusTimeoutError:
                _LOGGER.exception("Timeout connecting to S-Bus device")
                errors["base"] = ERROR_TIMEOUT
            except SBusProtocolError:
                _LOGGER.exception("Error connecting to S-Bus device")
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception:
                _LOGGER.exception("Unexpected error during S-Bus setup")
                errors["base"] = ERROR_UNKNOWN

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CONNECTION_TYPE, default=CONNECTION_TYPE_UDP): vol.In(
                    {
                        CONNECTION_TYPE_UDP: "UDP",
                        CONNECTION_TYPE_TCP: "TCP",
                    }
                ),
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT_UDP): cv.port,
                vol.Required(CONF_STATION, default=DEFAULT_STATION): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0, max=253),
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=3600),
                ),
            }
        )

        return self.async_show_form(
            step_id="ether_sbus",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "protocol_type": "Ether-S-Bus",
            },
        )

    async def async_step_serial_sbus(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Serial-S-Bus configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config_data.update(user_input)

            try:
                device_info = await validate_connection(
                    self.hass,
                    self._config_data,
                )

                await self.async_set_unique_id(device_info["serial_number"])
                self._abort_if_unique_id_configured()

                serial_port = user_input[CONF_SERIAL_PORT]
                title = f"{device_info.get('product_type', 'SAIA PCD')} ({serial_port})"

                return self.async_create_entry(
                    title=title,
                    data=self._config_data,
                )

            except data_entry_flow.AbortFlow:
                raise
            except SBusTimeoutError:
                _LOGGER.exception("Timeout connecting to S-Bus device")
                errors["base"] = ERROR_TIMEOUT
            except SBusProtocolError:
                _LOGGER.exception("Error connecting to S-Bus device")
                errors["base"] = ERROR_CANNOT_CONNECT
            except FileNotFoundError:
                _LOGGER.exception("Serial port not found")
                errors["base"] = ERROR_SERIAL_PORT_NOT_FOUND
            except Exception:
                _LOGGER.exception("Unexpected error during S-Bus setup")
                errors["base"] = ERROR_UNKNOWN

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CONNECTION_TYPE, default=CONNECTION_TYPE_USB
                ): vol.In(
                    {
                        CONNECTION_TYPE_USB: "USB/Serial",
                        CONNECTION_TYPE_TCP_SERIAL: "TCP Serial Bridge",
                    }
                ),
                vol.Required(CONF_SERIAL_PORT): str,
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In(
                    {rate: str(rate) for rate in BAUDRATES}
                ),
                vol.Required(CONF_STATION, default=DEFAULT_STATION): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0, max=253),
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=3600),
                ),
            }
        )

        return self.async_show_form(
            step_id="serial_sbus",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "protocol_type": "Serial-S-Bus",
                "serial_port_example": "/dev/ttyUSB0 or 192.168.1.100:5050",
            },
        )

    async def async_step_profi_sbus(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Profi-S-Bus configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config_data.update(user_input)

            try:
                device_info = await validate_connection(
                    self.hass,
                    self._config_data,
                )

                await self.async_set_unique_id(device_info["serial_number"])
                self._abort_if_unique_id_configured()

                host = user_input[CONF_HOST]
                title = f"{device_info.get('product_type', 'SAIA PCD')} (Profibus @ {host})"

                return self.async_create_entry(
                    title=title,
                    data=self._config_data,
                )

            except data_entry_flow.AbortFlow:
                raise
            except SBusTimeoutError:
                _LOGGER.exception("Timeout connecting to S-Bus device")
                errors["base"] = ERROR_TIMEOUT
            except SBusProtocolError:
                _LOGGER.exception("Error connecting to S-Bus device")
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception:
                _LOGGER.exception("Unexpected error during S-Bus setup")
                errors["base"] = ERROR_UNKNOWN

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT_TCP): cv.port,
                vol.Required(CONF_STATION, default=DEFAULT_STATION): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0, max=253),
                ),
                vol.Optional(
                    "profibus_address",
                    default=0,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0, max=126),
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=3600),
                ),
            }
        )

        return self.async_show_form(
            step_id="profi_sbus",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "protocol_type": "Profi-S-Bus",
            },
        )

    async def async_step_zeroconf(
        self,
        discovery_info: dict[str, Any],
    ) -> FlowResult:
        """Handle zeroconf discovery of SAIA PCD devices.

        Args:
            discovery_info: Discovery information from zeroconf

        Returns:
            Flow result

        """
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Extract host and port from discovery info
        host = discovery_info.get("host")
        port = discovery_info.get("port", DEFAULT_PORT_UDP)
        name = discovery_info.get("name", "")

        if not host:
            return self.async_abort(reason="cannot_connect")

        # Set protocol type to Ether-S-Bus for network discovery
        self._protocol_type = PROTOCOL_ETHER_SBUS
        self._config_data[CONF_PROTOCOL_TYPE] = PROTOCOL_ETHER_SBUS
        self._config_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_UDP
        self._config_data[CONF_HOST] = host
        self._config_data[CONF_PORT] = port
        self._config_data[CONF_STATION] = DEFAULT_STATION
        self._config_data[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

        # Try to get device info for unique ID
        try:
            device_info = await validate_connection(self.hass, self._config_data)
            await self.async_set_unique_id(device_info["serial_number"])
            self._abort_if_unique_id_configured(
                updates={
                    CONF_HOST: host,
                    CONF_PORT: port,
                }
            )

            # Show confirmation dialog
            self.context["title_placeholders"] = {
                "name": device_info.get("product_type", name or "SAIA PCD"),
                "host": host,
            }
            return await self.async_step_discovery_confirm()

        except Exception as err:
            _LOGGER.debug("Discovery validation failed: %s", err)
            return self.async_abort(reason="cannot_connect")

    async def async_step_ssdp(
        self,
        discovery_info: dict[str, Any],
    ) -> FlowResult:
        """Handle SSDP discovery of SAIA PCD devices.

        Args:
            discovery_info: Discovery information from SSDP

        Returns:
            Flow result

        """
        _LOGGER.debug("SSDP discovery: %s", discovery_info)

        # Extract host from SSDP location URL
        location = discovery_info.get("ssdp_location", "")
        if not location:
            return self.async_abort(reason="cannot_connect")

        # Parse host from URL (e.g., http://192.168.1.100:8080/...)
        try:
            from urllib.parse import urlparse

            parsed = urlparse(location)
            host = parsed.hostname
            if not host:
                return self.async_abort(reason="cannot_connect")
        except Exception as err:
            _LOGGER.error("Failed to parse SSDP location: %s", err)
            return self.async_abort(reason="cannot_connect")

        # Similar to zeroconf discovery
        self._protocol_type = PROTOCOL_ETHER_SBUS
        self._config_data[CONF_PROTOCOL_TYPE] = PROTOCOL_ETHER_SBUS
        self._config_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_UDP
        self._config_data[CONF_HOST] = host
        self._config_data[CONF_PORT] = DEFAULT_PORT_UDP
        self._config_data[CONF_STATION] = DEFAULT_STATION
        self._config_data[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

        try:
            device_info = await validate_connection(self.hass, self._config_data)
            await self.async_set_unique_id(device_info["serial_number"])
            self._abort_if_unique_id_configured(
                updates={
                    CONF_HOST: host,
                }
            )

            self.context["title_placeholders"] = {
                "name": device_info.get("product_type", "SAIA PCD"),
                "host": host,
            }
            return await self.async_step_discovery_confirm()

        except Exception as err:
            _LOGGER.debug("SSDP validation failed: %s", err)
            return self.async_abort(reason="cannot_connect")

    async def async_step_discovery_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Confirm discovery and create entry.

        Args:
            user_input: User input from confirmation dialog

        Returns:
            Flow result

        """
        if user_input is not None:
            # User confirmed, create the entry
            title = self.context["title_placeholders"]["name"]
            return self.async_create_entry(
                title=title,
                data=self._config_data,
            )

        # Show confirmation form
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders=self.context.get("title_placeholders", {}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return SBusOptionsFlow()


class SBusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SAIA S-Bus."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.data.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=3600),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
