"""Config flow for Yarbo integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import dhcp
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from yarbo import YarboLocalClient
from yarbo.exceptions import YarboConnectionError

from .const import (
    CONF_BROKER_HOST,
    CONF_BROKER_MAC,
    CONF_BROKER_PORT,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    DEFAULT_ACTIVITY_PERSONALITY,
    DEFAULT_AUTO_CONTROLLER,
    DEFAULT_BROKER_PORT,
    DEFAULT_CLOUD_ENABLED,
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    OPT_ACTIVITY_PERSONALITY,
    OPT_AUTO_CONTROLLER,
    OPT_CLOUD_ENABLED,
    OPT_TELEMETRY_THROTTLE,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BROKER_HOST): str,
        vol.Optional(CONF_BROKER_PORT, default=DEFAULT_BROKER_PORT): int,
    }
)


class YarboConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yarbo.

    Supports:
    - Manual IP entry (async_step_user)
    - DHCP auto-discovery (async_step_dhcp)
    - MQTT connection validation (async_step_mqtt_test)
    - Reconfigure flow (async_step_reconfigure)
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_mac: str | None = None
        self._robot_serial: str | None = None
        self._broker_host: str | None = None
        self._broker_port: int = DEFAULT_BROKER_PORT
        self._reconfigure_entry: ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step — manual IP entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._broker_host = user_input[CONF_BROKER_HOST]
            self._broker_port = int(user_input.get(CONF_BROKER_PORT) or DEFAULT_BROKER_PORT)
            return await self.async_step_mqtt_test()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle DHCP discovery.

        Triggered when a device with MAC OUI C8:FE:0F:* appears on the network.
        This is the Yarbo Data Center (base station).
        """
        _LOGGER.debug(
            "DHCP discovery: IP=%s MAC=%s hostname=%s",
            discovery_info.ip,
            discovery_info.macaddress,
            discovery_info.hostname,
        )

        # Check by MAC address for IP changes (reconfigure)
        existing_entry = next(
            (
                entry
                for entry in self._async_current_entries()
                if entry.data.get(CONF_BROKER_MAC) == discovery_info.macaddress
            ),
            None,
        )
        if existing_entry is not None:
            if existing_entry.data.get(CONF_BROKER_HOST) != discovery_info.ip:
                self._reconfigure_entry = existing_entry
                self._broker_host = discovery_info.ip
                self._broker_port = int(
                    existing_entry.data.get(CONF_BROKER_PORT) or DEFAULT_BROKER_PORT
                )
                return await self.async_step_reconfigure()
            return self.async_abort(reason="already_configured")

        self._discovered_host = discovery_info.ip
        self._discovered_mac = discovery_info.macaddress

        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm DHCP-discovered device."""
        if user_input is not None:
            self._broker_host = self._discovered_host
            return await self.async_step_mqtt_test()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"host": self._discovered_host or "unknown"},
        )

    async def async_step_mqtt_test(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Validate MQTT connection and extract robot serial number."""
        errors: dict[str, str] = {}
        if self._broker_host is None:
            return self.async_abort(reason="cannot_connect")

        client = YarboLocalClient(host=self._broker_host, port=self._broker_port)
        telemetry = None
        async_gen = None
        try:
            await client.connect()
            async_gen = client.watch_telemetry()
            telemetry = await asyncio.wait_for(async_gen.__anext__(), timeout=10.0)
            self._robot_serial = (
                telemetry.serial_number
                if telemetry and telemetry.serial_number
                else client.serial_number
            )
        except YarboConnectionError:
            errors["base"] = "cannot_connect"
        except TimeoutError:
            errors["base"] = "no_telemetry"
        except Exception:
            _LOGGER.exception("Failed to decode Yarbo telemetry")
            errors["base"] = "decode_error"
        finally:
            if async_gen is not None:
                await async_gen.aclose()
            await client.disconnect()

        if errors:
            return self.async_show_form(
                step_id="mqtt_test",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        if not self._robot_serial:
            return self.async_show_form(
                step_id="mqtt_test",
                data_schema=vol.Schema({}),
                errors={"base": "no_telemetry"},
            )

        if self._reconfigure_entry is not None:
            if self._robot_serial != self._reconfigure_entry.data.get(CONF_ROBOT_SERIAL):
                return self.async_abort(reason="wrong_device")

            data = dict(self._reconfigure_entry.data)
            data[CONF_BROKER_HOST] = self._broker_host
            data[CONF_BROKER_PORT] = self._broker_port
            if self._discovered_mac:
                data[CONF_BROKER_MAC] = self._discovered_mac
            self.hass.config_entries.async_update_entry(self._reconfigure_entry, data=data)
            await self.hass.config_entries.async_reload(self._reconfigure_entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")

        return await self.async_step_name()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle reconfiguration to update the broker host."""
        if self._reconfigure_entry is None and "entry_id" in self.context:
            entry_id = self.context["entry_id"]
            self._reconfigure_entry = self.hass.config_entries.async_get_entry(entry_id)

        if self._reconfigure_entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is not None:
            self._broker_host = user_input[CONF_BROKER_HOST]
            self._broker_port = int(user_input.get(CONF_BROKER_PORT) or DEFAULT_BROKER_PORT)
            return await self.async_step_mqtt_test()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BROKER_HOST,
                    default=self._broker_host
                    or self._reconfigure_entry.data.get(CONF_BROKER_HOST, ""),
                ): str,
                vol.Optional(
                    CONF_BROKER_PORT,
                    default=int(
                        (
                            self._broker_port
                            if self._broker_host is not None
                            else self._reconfigure_entry.data.get(CONF_BROKER_PORT)
                        )
                        or DEFAULT_BROKER_PORT
                    ),
                ): int,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    async def async_step_name(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Prompt for an optional friendly name."""
        if not self._robot_serial:
            return self.async_abort(reason="no_telemetry")

        default_name = f"Yarbo {self._robot_serial[-4:]}"
        if user_input is not None:
            # Use robot serial as unique ID and abort if already configured
            await self.async_set_unique_id(self._robot_serial)
            self._abort_if_unique_id_configured()  # Fixed: was _async_abort_entries_match (wrong)

            name = user_input.get(CONF_ROBOT_NAME, default_name)
            data: dict[str, Any] = {
                CONF_BROKER_HOST: self._broker_host,
                CONF_BROKER_PORT: self._broker_port,
                CONF_ROBOT_SERIAL: self._robot_serial,
                CONF_ROBOT_NAME: name,
            }
            if self._discovered_mac:
                data[CONF_BROKER_MAC] = self._discovered_mac

            return self.async_create_entry(title=name, data=data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_ROBOT_NAME, default=default_name): str,
            }
        )
        return self.async_show_form(step_id="name", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return YarboOptionsFlow(config_entry)


class YarboOptionsFlow(OptionsFlow):
    """Handle options for the Yarbo integration.

    Options:
    - telemetry_throttle: debounce interval (seconds)
    - auto_controller: auto-acquire controller before commands
    - cloud_enabled: enable cloud REST features
    - activity_personality: fun personality descriptions (boolean toggle)
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    OPT_TELEMETRY_THROTTLE,
                    default=self._config_entry.options.get(
                        OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=10.0)),
                vol.Optional(
                    OPT_AUTO_CONTROLLER,
                    default=self._config_entry.options.get(
                        OPT_AUTO_CONTROLLER, DEFAULT_AUTO_CONTROLLER
                    ),
                ): bool,
                vol.Optional(
                    OPT_CLOUD_ENABLED,
                    default=self._config_entry.options.get(
                        OPT_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED
                    ),
                ): bool,
                # Fixed: activity_personality is a boolean toggle, not an enum string
                vol.Optional(
                    OPT_ACTIVITY_PERSONALITY,
                    default=self._config_entry.options.get(
                        OPT_ACTIVITY_PERSONALITY, DEFAULT_ACTIVITY_PERSONALITY
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
