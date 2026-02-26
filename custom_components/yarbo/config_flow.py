"""Config flow for Yarbo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BROKER_HOST,
    CONF_BROKER_MAC,
    CONF_BROKER_PORT,
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    DEFAULT_BROKER_PORT,
    DEFAULT_AUTO_CONTROLLER,
    DEFAULT_CLOUD_ENABLED,
    DEFAULT_ACTIVITY_PERSONALITY,
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
    - Optional cloud auth (async_step_cloud)
    - Reconfigure flow (async_step_reconfigure)

    TODO: Implement each step in v0.1.0
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_mac: str | None = None
        self._robot_serial: str | None = None
        self._broker_host: str | None = None
        self._broker_port: int = DEFAULT_BROKER_PORT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step — manual IP entry.

        TODO: Implement in v0.1.0
        - Show form for broker IP and port
        - On submit, proceed to async_step_mqtt_test
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._broker_host = user_input[CONF_BROKER_HOST]
            self._broker_port = user_input.get(CONF_BROKER_PORT, DEFAULT_BROKER_PORT)
            # TODO: Proceed to MQTT validation
            # return await self.async_step_mqtt_test()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: dhcp.DhcpServiceInfo
    ) -> FlowResult:
        """Handle DHCP discovery.

        Triggered when a device with MAC OUI C8:FE:0F:* appears on the network.
        This is the Yarbo Data Center (base station).

        TODO: Implement in v0.1.0
        - Check if this DC's robot is already configured (abort_already_configured)
        - Store discovered IP and MAC
        - Show confirmation form (async_step_confirm)
        """
        _LOGGER.debug(
            "DHCP discovery: IP=%s MAC=%s hostname=%s",
            discovery_info.ip,
            discovery_info.macaddress,
            discovery_info.hostname,
        )

        self._discovered_host = discovery_info.ip
        self._discovered_mac = discovery_info.macaddress

        # TODO: Check for existing config entries with this MAC
        # await self.async_set_unique_id(discovery_info.macaddress)
        # self._abort_if_unique_id_configured()

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm DHCP-discovered device.

        TODO: Implement in v0.1.0
        - Show discovered IP to user
        - On confirm, proceed to async_step_mqtt_test
        """
        if user_input is not None:
            self._broker_host = self._discovered_host
            # TODO: Proceed to MQTT validation
            # return await self.async_step_mqtt_test()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"host": self._discovered_host or "unknown"},
        )

    async def async_step_mqtt_test(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate MQTT connection and extract robot serial number.

        TODO: Implement in v0.1.0
        Steps:
        1. Connect to broker:1883 via python-yarbo
        2. Subscribe to snowbot/+/device/DeviceMSG
        3. Wait up to 10s for first telemetry
        4. Extract SN from topic: snowbot/{SN}/device/...
        5. Decode DeviceMSG to confirm zlib works
        6. Abort if: cannot_connect, no_telemetry, decode_error, already_configured

        Error keys: cannot_connect, no_telemetry, decode_error
        """
        # TODO: Implement MQTT validation
        # try:
        #     from yarbo import YarboLocalClient, YarboConnectionError, YarboTimeoutError
        #     client = YarboLocalClient(broker=self._broker_host, port=self._broker_port)
        #     sn = await client.probe(timeout=10.0)
        #     self._robot_serial = sn
        # except YarboConnectionError:
        #     errors["base"] = "cannot_connect"
        # except YarboTimeoutError:
        #     errors["base"] = "no_telemetry"

        return self.async_abort(reason="not_implemented")

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
    - activity_personality: personality phrases in activity sensor

    TODO: Implement in v0.1.0
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options.

        TODO: Implement in v0.1.0
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    OPT_TELEMETRY_THROTTLE,
                    default=self._config_entry.options.get(
                        OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE
                    ),
                ): vol.Coerce(float),
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
                vol.Optional(
                    OPT_ACTIVITY_PERSONALITY,
                    default=self._config_entry.options.get(
                        OPT_ACTIVITY_PERSONALITY, DEFAULT_ACTIVITY_PERSONALITY
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
