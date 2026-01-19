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

from .const import CONF_SCAN_INTERVAL
from .const import CONF_STATION
from .const import DEFAULT_PORT
from .const import DEFAULT_SCAN_INTERVAL
from .const import DEFAULT_STATION
from .const import DOMAIN
from .const import ERROR_CANNOT_CONNECT
from .const import ERROR_TIMEOUT
from .const import ERROR_UNKNOWN
from .sbus_protocol import SBusProtocol
from .sbus_protocol import SBusProtocolError
from .sbus_protocol import SBusTimeoutError

_LOGGER = logging.getLogger(__name__)


async def validate_connection(
    hass: HomeAssistant,
    host: str,
    port: int,
    station: int,
) -> dict[str, Any]:
    """Validate the connection to the S-Bus device.

    Args:
        hass: Home Assistant instance
        host: Device hostname or IP
        port: UDP port
        station: Station address

    Returns:
        Dictionary with device information

    Raises:
        SBusTimeoutError: If connection times out
        SBusProtocolError: For other protocol errors

    """
    protocol = SBusProtocol(host, port, station)

    try:
        await protocol.connect()

        # Try to read device information to verify connection
        return await protocol.get_device_info()

    finally:
        await protocol.disconnect()


class SBusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SAIA S-Bus."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            station = user_input[CONF_STATION]

            try:
                device_info = await validate_connection(
                    self.hass,
                    host,
                    port,
                    station,
                )

                # Create unique ID from serial number
                await self.async_set_unique_id(device_info["serial_number"])
                self._abort_if_unique_id_configured()

                # Create the config entry
                title = f"{device_info.get('product_type', 'SAIA PCD')} ({host})"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_STATION: station,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL,
                        ),
                    },
                )

            except data_entry_flow.AbortFlow:
                # Re-raise abort flows (like already_configured)
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

        # Show the form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
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
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            station = user_input[CONF_STATION]

            try:
                await validate_connection(
                    self.hass,
                    host,
                    port,
                    station,
                )

                # Update the entry
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_STATION: station,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL,
                        ),
                    },
                )

                await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reconfigure_successful")

            except SBusTimeoutError:
                _LOGGER.exception("Timeout connecting to S-Bus device")
                errors["base"] = ERROR_TIMEOUT
            except SBusProtocolError:
                _LOGGER.exception("Error connecting to S-Bus device")
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception:
                _LOGGER.exception("Unexpected error during S-Bus reconfiguration")
                errors["base"] = ERROR_UNKNOWN

        # Pre-fill form with current values
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=entry.data.get(CONF_HOST),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=entry.data.get(CONF_PORT, DEFAULT_PORT),
                ): cv.port,
                vol.Required(
                    CONF_STATION,
                    default=entry.data.get(CONF_STATION, DEFAULT_STATION),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=0, max=253),
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=5, max=3600),
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
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
            # Return options (not data) - the integration will handle the reload
            return self.async_create_entry(title="", data=user_input)

        # Show options form
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
