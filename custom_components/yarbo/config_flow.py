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

try:
    from yarbo.cloud import YarboCloudClient
except ImportError:  # pragma: no cover
    YarboCloudClient = None

from .const import (
    CONF_ALTERNATE_BROKER_HOST,
    CONF_BROKER_ENDPOINTS,
    CONF_BROKER_HOST,
    CONF_BROKER_MAC,
    CONF_BROKER_PORT,
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    CONF_CONNECTION_PATH,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    CONF_ROVER_IP,
    DEFAULT_ACTIVITY_PERSONALITY,
    DEFAULT_AUTO_CONTROLLER,
    DEFAULT_BROKER_PORT,
    DEFAULT_CLOUD_ENABLED,
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    ENDPOINT_TYPE_ROVER,
    ENDPOINT_TYPE_UNKNOWN,
    OPT_ACTIVITY_PERSONALITY,
    OPT_AUTO_CONTROLLER,
    OPT_CLOUD_ENABLED,
    OPT_TELEMETRY_THROTTLE,
)
from .discovery import YarboEndpoint, async_discover_endpoints
from .repairs import async_delete_cloud_token_expired_issue

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
    - Manual IP entry (async_step_user) + MQTT validation (async_step_mqtt_test) — see #1
    - DHCP auto-discovery (async_step_dhcp) — see #2
    - Optional cloud authentication (async_step_cloud)
    - Reconfigure flow (async_step_reconfigure)
    - Re-authentication when cloud token expires (async_step_reauth)
    """

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_mac: str | None = None
        self._discovered_endpoints: list[YarboEndpoint] = []
        self._connection_path: str = ""
        self._alternate_host: str | None = None
        self._rover_ip: str | None = None
        self._robot_serial: str | None = None
        self._robot_name: str | None = None
        self._broker_host: str | None = None
        self._broker_port: int = DEFAULT_BROKER_PORT
        self._reconfigure_entry: ConfigEntry | None = None
        self._pending_data: dict[str, Any] = {}
        # Ordered list from python-yarbo discovery (Primary first, then Secondary, ...)
        self._broker_endpoints_ordered: list[str] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step — try discovery first, then manual IP/port if needed."""
        # Defensive: HA may call async_step_user with form data in edge cases
        if user_input is not None:
            self._broker_host = user_input[CONF_BROKER_HOST]
            port = user_input.get(CONF_BROKER_PORT)
            self._broker_port = DEFAULT_BROKER_PORT if port in (None, "") else int(port)
            # Discover other endpoints (e.g. YARBO hostname); if multiple, show selection
            self._discovered_endpoints = await async_discover_endpoints(
                seed_host=self._broker_host,
                port=self._broker_port,
            )
            if len(self._discovered_endpoints) > 1:
                return await self.async_step_select_endpoint()
            if self._discovered_endpoints:
                ep = self._discovered_endpoints[0]
                self._broker_host = ep.host
                self._broker_port = ep.port
                self._connection_path = ep.endpoint_type
                self._rover_ip = ep.host if ep.endpoint_type == ENDPOINT_TYPE_ROVER else None
                self._alternate_host = None
                self._broker_endpoints_ordered = [e.host for e in self._discovered_endpoints]
            return await self.async_step_mqtt_test()

        # No user input yet: try python-yarbo discovery (no seed)
        self._discovered_endpoints = await async_discover_endpoints(
            seed_host=None,
            port=DEFAULT_BROKER_PORT,
        )
        if len(self._discovered_endpoints) == 0:
            # No devices found — offer manual IP/port entry
            return await self.async_step_manual()
        if len(self._discovered_endpoints) == 1:
            ep = self._discovered_endpoints[0]
            self._broker_host = ep.host
            self._broker_port = ep.port
            self._connection_path = ep.endpoint_type
            self._rover_ip = ep.host if ep.endpoint_type == ENDPOINT_TYPE_ROVER else None
            self._alternate_host = None
            self._broker_endpoints_ordered = [ep.host]
            return await self.async_step_mqtt_test()
        # Multiple endpoints — preserve library order (Primary, Secondary, ...)
        self._broker_endpoints_ordered = [ep.host for ep in self._discovered_endpoints]
        return await self.async_step_select_endpoint()

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manual IP/port entry when discovery found no devices."""
        errors: dict[str, str] = {}
        # Defensive: HA may call async_step_user with form data in edge cases
        if user_input is not None:
            self._broker_host = user_input[CONF_BROKER_HOST]
            port = user_input.get(CONF_BROKER_PORT)
            self._broker_port = DEFAULT_BROKER_PORT if port in (None, "") else int(port)
            self._connection_path = ""
            self._alternate_host = None
            self._rover_ip = None
            self._broker_endpoints_ordered = [self._broker_host]
            return await self.async_step_mqtt_test()
        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def _probe_robot_identity(
        self, host: str, port: int, timeout: float = 8.0
    ) -> tuple[str | None, str | None]:
        """Quick MQTT probe to discover the robot serial number and name.

        Uses a synchronous paho-mqtt client in a thread executor to avoid
        blocking-call warnings from HA's event loop detector (paho's import
        and connect trigger synchronous file I/O).

        Returns (serial_number, bot_name) — either may be None.
        """

        def _sync_probe() -> tuple[str | None, str | None]:
            """Run entirely in a thread — no async, no event loop interaction."""
            import json as _json
            import threading

            import paho.mqtt.client as mqtt

            result: dict[str, str | None] = {"sn": None, "name": None}
            got_telemetry = threading.Event()

            def on_connect(
                client: Any, userdata: Any, flags: Any, rc: Any, props: Any = None
            ) -> None:
                rc_val = getattr(rc, "value", rc)
                if rc_val == 0:
                    client.subscribe("snowbot/+/device/DeviceMSG")
                    client.subscribe("snowbot/+/device/heart_beat")

            def on_message(client: Any, userdata: Any, msg: Any) -> None:
                parts = msg.topic.split("/")
                if len(parts) >= 2 and parts[0] == "snowbot" and parts[1]:
                    result["sn"] = parts[1]
                try:
                    import zlib

                    try:
                        raw = zlib.decompress(msg.payload)
                    except zlib.error:
                        raw = msg.payload
                    payload = _json.loads(raw)
                    if not result["name"]:
                        result["name"] = (
                            payload.get("name")
                            or payload.get("robotName")
                            or payload.get("snowbotName")
                        )
                except Exception:
                    pass
                if result["sn"]:
                    got_telemetry.set()

            c = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"yarbo-ha-probe-{int(__import__('time').time())}",
            )
            c.on_connect = on_connect
            c.on_message = on_message
            try:
                c.connect(host, port, keepalive=10)
                c.loop_start()
                got_telemetry.wait(timeout=timeout)
                c.loop_stop()
                c.disconnect()
            except Exception:
                pass
            return (result["sn"], result["name"])

        try:
            return await asyncio.get_running_loop().run_in_executor(None, _sync_probe)
        except Exception:
            _LOGGER.debug("Robot identity probe failed for %s:%d", host, port)
            return (None, None)

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle DHCP discovery (issue #2).

        Triggered when a device with MAC OUI C8:FE:0F:* appears on the network,
        or by our ARP startup scan via async_setup.
        """
        # Support both DhcpServiceInfo and plain dict (from ARP discovery trigger)
        if isinstance(discovery_info, dict):
            ip = discovery_info["ip"]
            mac = discovery_info.get("macaddress", "")
            hostname = discovery_info.get("hostname", "")
        else:
            ip = discovery_info.ip
            mac = discovery_info.macaddress
            hostname = discovery_info.hostname

        _LOGGER.debug(
            "DHCP discovery: IP=%s MAC=%s hostname=%s",
            ip,
            mac,
            hostname,
        )

        # Probe MQTT to discover the robot serial number for unique identification
        sn, bot_name = await self._probe_robot_identity(ip, DEFAULT_BROKER_PORT, timeout=8.0)
        if sn:
            self._robot_serial = sn
            self._robot_name = bot_name
            self.context["title_placeholders"] = {"name": sn}
            await self.async_set_unique_id(sn)
            self._abort_if_unique_id_configured(updates={CONF_BROKER_HOST: ip})
        else:
            # Fallback: use MAC as unique_id if MQTT probe fails (robot sleeping)
            self.context["title_placeholders"] = {"name": ip}
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured(updates={CONF_BROKER_HOST: ip})

        # Check by MAC address for IP changes (reconfigure)
        existing_entry = next(
            (
                entry
                for entry in self._async_current_entries()
                if entry.data.get(CONF_BROKER_MAC) == mac
            ),
            None,
        )
        if existing_entry is not None:
            if existing_entry.data.get(CONF_BROKER_HOST) != ip:
                self._reconfigure_entry = existing_entry
                self._broker_host = ip
                port = existing_entry.data.get(CONF_BROKER_PORT)
                self._broker_port = DEFAULT_BROKER_PORT if port in (None, "") else int(port)
                return await self.async_step_reconfigure()
            return self.async_abort(reason="already_configured")

        self._discovered_host = ip
        self._discovered_mac = mac

        # Discover all endpoints (this + e.g. YARBO); if multiple, show selection
        self._discovered_endpoints = await async_discover_endpoints(
            seed_host=ip,
            seed_mac=mac,
            port=DEFAULT_BROKER_PORT,
        )
        if not self._discovered_endpoints:
            # Fallback: single endpoint from DHCP (type/recommended from library only)
            self._discovered_endpoints = [
                YarboEndpoint(
                    host=ip,
                    port=DEFAULT_BROKER_PORT,
                    mac=mac,
                    endpoint_type=ENDPOINT_TYPE_UNKNOWN,
                    recommended=False,
                )
            ]

        if len(self._discovered_endpoints) > 1:
            self._broker_endpoints_ordered = [ep.host for ep in self._discovered_endpoints]
            return await self.async_step_select_endpoint()

        # Single endpoint
        ep = self._discovered_endpoints[0]
        self._broker_host = ep.host
        self._broker_port = ep.port
        self._connection_path = ep.endpoint_type
        self._rover_ip = ep.host if ep.endpoint_type == ENDPOINT_TYPE_ROVER else None
        self._alternate_host = None
        self._broker_endpoints_ordered = [ep.host]

        return await self.async_step_confirm()

    async def async_step_select_endpoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let user choose initial endpoint. Order is from python-yarbo (Primary, Secondary)."""
        # Defensive: HA may call async_step_user with form data in edge cases
        if user_input is not None:
            chosen_host = user_input.get("selected_endpoint")
            chosen: YarboEndpoint | None = None
            for ep in self._discovered_endpoints:
                if ep.host == chosen_host:
                    chosen = ep
                    break
            if chosen:
                self._broker_host = chosen.host
                self._broker_port = chosen.port
                self._connection_path = chosen.endpoint_type
                others = [e for e in self._discovered_endpoints if e.host != chosen.host]
                self._alternate_host = others[0].host if others else None
                self._rover_ip = next(
                    (
                        e.host
                        for e in self._discovered_endpoints
                        if e.endpoint_type == ENDPOINT_TYPE_ROVER
                    ),
                    None,
                )
                # Keep discovery order for failover (Primary → Secondary → Primary …)
                self._broker_endpoints_ordered = [ep.host for ep in self._discovered_endpoints]
            return await self.async_step_mqtt_test()

        # Build options in library order; label first as Primary, second as Secondary (like DNS)
        options: dict[str, str] = {}
        for i, ep in enumerate(self._discovered_endpoints):
            role = "Primary" if i == 0 else "Secondary" if i == 1 else f"Endpoint {i + 1}"
            options[ep.host] = f"{ep.host} — {ep.label} ({role})"
        default = self._discovered_endpoints[0].host if self._discovered_endpoints else None

        schema = vol.Schema(
            {
                vol.Required(
                    "selected_endpoint",
                    default=default,
                ): vol.In(options),
            }
        )
        return self.async_show_form(
            step_id="select_endpoint",
            data_schema=schema,
            description_placeholders={
                "count": str(len(self._discovered_endpoints)),
            },
        )

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm DHCP-discovered device.

        If the serial number was already discovered via MQTT probe, the user
        just clicks 'Add' to create the entry — no further MQTT test needed.
        If SN is unknown (robot sleeping), falls through to mqtt_test.
        """
        if user_input is not None:
            self._broker_host = self._broker_host or self._discovered_host
            if self._robot_serial:
                # SN already known — skip MQTT test, go to name step
                return await self.async_step_name()
            return await self.async_step_mqtt_test()

        display_name = self._robot_serial or "unknown"
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "host": self._broker_host or self._discovered_host or "unknown",
                "name": display_name,
            },
        )

    async def async_step_mqtt_test(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Validate MQTT connection and extract robot serial number."""
        errors: dict[str, str] = {}
        if self._broker_host is None:
            return self.async_abort(reason="cannot_connect")

        client = YarboLocalClient(broker=self._broker_host, port=self._broker_port)
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
            if self._broker_endpoints_ordered:
                data[CONF_BROKER_ENDPOINTS] = self._broker_endpoints_ordered
            else:
                # Preserve existing endpoints, updating the primary host
                existing = list(data.get(CONF_BROKER_ENDPOINTS, []))
                old_host = self._reconfigure_entry.data.get(CONF_BROKER_HOST)
                if old_host in existing:
                    existing[existing.index(old_host)] = self._broker_host
                elif existing:
                    existing[0] = self._broker_host
                else:
                    existing = [self._broker_host]
                data[CONF_BROKER_ENDPOINTS] = existing
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

        # Defensive: HA may call async_step_user with form data in edge cases
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

        default_name = self._robot_name or f"Yarbo {self._robot_serial[-4:]}"
        # Defensive: HA may call async_step_user with form data in edge cases
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
            if self._connection_path:
                self._pending_data[CONF_CONNECTION_PATH] = self._connection_path
            if self._alternate_host:
                self._pending_data[CONF_ALTERNATE_BROKER_HOST] = self._alternate_host
            if self._rover_ip:
                self._pending_data[CONF_ROVER_IP] = self._rover_ip
            # Ordered list from discovery for Primary/Secondary failover (library order)
            endpoints_ordered = getattr(self, "_broker_endpoints_ordered", None) or (
                [self._broker_host] + ([self._alternate_host] if self._alternate_host else [])
            )
            self._pending_data[CONF_BROKER_ENDPOINTS] = endpoints_ordered

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

        # Defensive: HA may call async_step_user with form data in edge cases
        if user_input is not None:
            username = (user_input.get(CONF_CLOUD_USERNAME) or "").strip()
            password = (user_input.get("cloud_password") or "").strip()

            if not username or not password:
                # User skipped cloud — create entry without cloud credentials
                entry_data, self._pending_data = self._pending_data, {}
                return self.async_create_entry(
                    title=entry_data[CONF_ROBOT_NAME],
                    data=entry_data,
                )

            # Attempt login via python-yarbo cloud client
            if YarboCloudClient is None:
                _LOGGER.warning("python-yarbo cloud client not available")
                errors["base"] = "cloud_not_available"
            else:
                cloud_client = YarboCloudClient(username=username, password=password)
                try:
                    await cloud_client.connect()
                    refresh_token = cloud_client.auth.refresh_token
                    self._pending_data[CONF_CLOUD_USERNAME] = username
                    self._pending_data[CONF_CLOUD_REFRESH_TOKEN] = refresh_token
                    _LOGGER.debug("Cloud auth succeeded for %s", username)
                except Exception as err:
                    _LOGGER.exception("Cloud authentication failed for %s: %s", username, err)
                    errors["base"] = "cloud_auth_failed"
                finally:
                    await cloud_client.disconnect()

            if not errors:
                entry_data, self._pending_data = self._pending_data, {}
                return self.async_create_entry(
                    title=entry_data[CONF_ROBOT_NAME],
                    data=entry_data,
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

        # Defensive: HA may call async_step_user with form data in edge cases
        if user_input is not None:
            password = user_input.get("cloud_password", "")
            if YarboCloudClient is None:
                errors["base"] = "cloud_not_available"
            else:
                cloud_client = YarboCloudClient(username=username, password=password)
                try:
                    await cloud_client.connect()
                    refresh_token = cloud_client.auth.refresh_token
                    new_data = dict(reauth_entry.data)
                    new_data[CONF_CLOUD_REFRESH_TOKEN] = refresh_token
                    self.hass.config_entries.async_update_entry(reauth_entry, data=new_data)
                    async_delete_cloud_token_expired_issue(self.hass, reauth_entry.entry_id)
                    await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
                except Exception as err:
                    _LOGGER.exception("Re-authentication failed for %s: %s", username, err)
                    errors["base"] = "cloud_auth_failed"
                finally:
                    await cloud_client.disconnect()

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
    """Handle options for the Yarbo integration (issue #26).

    Options: telemetry_throttle (float, 1.0s default), auto_controller (bool),
    cloud_enabled (bool), activity_personality (bool). Applied without restart.
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        # Defensive: HA may call async_step_user with form data in edge cases
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
