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
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
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

STEP_CLOUD_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CLOUD_USERNAME, default=""): str,
        vol.Optional("cloud_password", default=""): str,
    }
)

STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required("cloud_password"): str,
    }
)


class YarboConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yarbo.

    Supports:
    - Manual IP entry (async_step_user)
    - DHCP auto-discovery (async_step_dhcp)
    - MQTT connection validation (async_step_mqtt_test)
    - Optional cloud authentication (async_step_cloud)
    - Reconfigure flow (async_step_reconfigure)
    - Re-authentication when cloud token expires (async_step_reauth)
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
        self._pending_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step — manual IP entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._broker_host = user_input[CONF_BROKER_HOST]
            port = user_input.get(CONF_BROKER_PORT)
            self._broker_port = DEFAULT_BROKER_PORT if port in (None, "") else int(port)
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
                port = existing_entry.data.get(CONF_BROKER_PORT)
                self._broker_port = DEFAULT_BROKER_PORT if port in (None, "") else int(port)
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
            port = user_input.get(CONF_BROKER_PORT)
            self._broker_port = DEFAULT_BROKER_PORT if port in (None, "") else int(port)
            return await self.async_step_mqtt_test()

        port = (
            self._broker_port
            if self._broker_host is not None
            else self._reconfigure_entry.data.get(CONF_BROKER_PORT)
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BROKER_HOST,
                    default=self._broker_host
                    or self._reconfigure_entry.data.get(CONF_BROKER_HOST, ""),
                ): str,
                vol.Optional(
                    CONF_BROKER_PORT,
                    default=int(port if port is not None else DEFAULT_BROKER_PORT),
                ): int,
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    async def async_step_name(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Prompt for an optional friendly name, then proceed to cloud step."""
        if not self._robot_serial:
            return self.async_abort(reason="no_telemetry")

        default_name = f"Yarbo {self._robot_serial[-4:]}"
        if user_input is not None:
            # Use robot serial as unique ID and abort if already configured
            await self.async_set_unique_id(self._robot_serial)
            self._abort_if_unique_id_configured()

            name = user_input.get(CONF_ROBOT_NAME, default_name)
            self._pending_data = {
                CONF_BROKER_HOST: self._broker_host,
                CONF_BROKER_PORT: self._broker_port,
                CONF_ROBOT_SERIAL: self._robot_serial,
                CONF_ROBOT_NAME: name,
            }
            if self._discovered_mac:
                self._pending_data[CONF_BROKER_MAC] = self._discovered_mac

            # Proceed to optional cloud authentication step
            return await self.async_step_cloud()

        schema = vol.Schema(
            {
                vol.Optional(CONF_ROBOT_NAME, default=default_name): str,
            }
        )
        return self.async_show_form(step_id="name", data_schema=schema)

    async def async_step_cloud(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Optional cloud credentials step.

        Users can skip this step by submitting empty email/password.
        On success, stores only the refresh_token (never the password).
        Local operation is fully functional without cloud credentials.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            username = (user_input.get(CONF_CLOUD_USERNAME) or "").strip()
            password = (user_input.get("cloud_password") or "").strip()

            if not username or not password:
                # User skipped cloud — create entry without cloud credentials
                return self.async_create_entry(
                    title=self._pending_data[CONF_ROBOT_NAME],
                    data=self._pending_data,
                )

            # Attempt Auth0 login via python-yarbo cloud client
            try:
                from yarbo.cloud import YarboCloudClient  # noqa: PLC0415

                cloud_client = YarboCloudClient()
                token_data: dict[str, Any] = await cloud_client.login(
                    username=username,
                    password=password,
                )
                self._pending_data[CONF_CLOUD_USERNAME] = username
                self._pending_data[CONF_CLOUD_REFRESH_TOKEN] = token_data["refresh_token"]
                _LOGGER.debug("Cloud auth succeeded for %s", username)
            except ImportError:
                _LOGGER.warning("python-yarbo cloud client not available")
                errors["base"] = "cloud_not_available"
            except Exception:
                _LOGGER.exception("Cloud authentication failed for %s", username)
                errors["base"] = "cloud_auth_failed"

            if not errors:
                return self.async_create_entry(
                    title=self._pending_data[CONF_ROBOT_NAME],
                    data=self._pending_data,
                )

        return self.async_show_form(
            step_id="cloud",
            data_schema=STEP_CLOUD_SCHEMA,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any] | None = None) -> FlowResult:
        """Handle re-authentication when the cloud token has expired."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show re-authentication form and refresh the cloud token."""
        errors: dict[str, str] = {}

        reauth_entry = self._get_reauth_entry()
        username = reauth_entry.data.get(CONF_CLOUD_USERNAME, "")

        if user_input is not None:
            password = user_input.get("cloud_password", "")
            try:
                from yarbo.cloud import YarboCloudClient  # noqa: PLC0415

                cloud_client = YarboCloudClient()
                token_data: dict[str, Any] = await cloud_client.login(
                    username=username,
                    password=password,
                )
                new_data = dict(reauth_entry.data)
                new_data[CONF_CLOUD_REFRESH_TOKEN] = token_data["refresh_token"]
                self.hass.config_entries.async_update_entry(reauth_entry, data=new_data)
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except ImportError:
                errors["base"] = "cloud_not_available"
            except Exception:
                _LOGGER.exception("Re-authentication failed for %s", username)
                errors["base"] = "cloud_auth_failed"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"username": username},
        )

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
