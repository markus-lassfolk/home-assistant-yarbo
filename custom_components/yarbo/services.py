"""Service registration for the Yarbo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from yarbo import YarboLightState

from .const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_AUTO_CONTROLLER,
    DOMAIN,
    OPT_AUTO_CONTROLLER,
    normalize_command_name,
    validate_head_type_for_command,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_COMMAND = "send_command"
SERVICE_START_PLAN = "start_plan"
SERVICE_PAUSE = "pause"
SERVICE_RESUME = "resume"
SERVICE_RETURN_TO_DOCK = "return_to_dock"
SERVICE_SET_LIGHTS = "set_lights"
SERVICE_SET_CHUTE_VELOCITY = "set_chute_velocity"
SERVICE_MANUAL_DRIVE = "manual_drive"
SERVICE_GO_TO_WAYPOINT = "go_to_waypoint"
SERVICE_DELETE_PLAN = "delete_plan"
SERVICE_DELETE_ALL_PLANS = "delete_all_plans"
SERVICE_ERASE_MAP = "erase_map"
SERVICE_MAP_RECOVERY = "map_recovery"
SERVICE_SAVE_CURRENT_MAP = "save_current_map"
SERVICE_SAVE_MAP_BACKUP = "save_map_backup_and_get_all_map_backup_nameandid"

SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("command"): str,
        vol.Optional("payload"): dict,
    }
)

SERVICE_START_PLAN_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("plan_id"): str,
        vol.Optional("percent"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)

SERVICE_DEVICE_ONLY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
    }
)

SERVICE_SET_LIGHTS_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Optional("brightness", default=255): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("led_head"): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("led_left_w"): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("led_right_w"): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("body_left_r"): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("body_right_r"): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("tail_left_r"): vol.All(int, vol.Range(min=0, max=255)),
        vol.Optional("tail_right_r"): vol.All(int, vol.Range(min=0, max=255)),
    }
)

SERVICE_SET_CHUTE_VELOCITY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("velocity"): vol.All(int, vol.Range(min=-2000, max=2000)),
    }
)

SERVICE_MANUAL_DRIVE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("linear"): vol.All(vol.Coerce(float), vol.Range(min=-1.0, max=1.0)),
        vol.Required("angular"): vol.All(vol.Coerce(float), vol.Range(min=-1.0, max=1.0)),
    }
)

SERVICE_GO_TO_WAYPOINT_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("index"): vol.Coerce(int),
    }
)

SERVICE_DELETE_PLAN_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("plan_id"): str,
    }
)

SERVICE_MAP_RECOVERY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Optional("map_id"): str,
    }
)


def _get_client_and_coordinator(hass: HomeAssistant, device_id: str) -> tuple[Any, Any]:
    """Resolve device_id to (client, coordinator) or raise ServiceValidationError."""
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device {device_id} not found")
    if not device.config_entries:
        raise ServiceValidationError(f"Device {device_id} has no config entry")
    entry_id = next(iter(device.config_entries))
    if entry_id not in hass.data.get(DOMAIN, {}):
        raise ServiceValidationError(f"Device {device_id} is not managed by the Yarbo integration")
    data = hass.data[DOMAIN][entry_id]
    return data[DATA_CLIENT], data[DATA_COORDINATOR]


async def _acquire_controller(client: Any, coordinator: Any) -> None:
    """Acquire controller with error handling and state reporting."""
    try:
        await client.get_controller(timeout=5.0)
    except Exception as err:
        _LOGGER.warning("Failed to acquire controller: %s", err)
        coordinator.report_controller_lost()
        raise
    coordinator.resolve_controller_lost()


def _should_auto_acquire_controller(coordinator: Any) -> bool:
    """Return True if options say to auto-acquire controller before commands (#26)."""
    return coordinator.entry.options.get(OPT_AUTO_CONTROLLER, DEFAULT_AUTO_CONTROLLER)


def async_register_services(hass: HomeAssistant) -> None:
    """Register all Yarbo services."""

    async def handle_send_command(call: ServiceCall) -> None:
        """Handle yarbo.send_command — publish an MQTT command."""
        device_id: str = call.data["device_id"]
        command: str = call.data["command"]
        payload: dict[str, Any] = call.data.get("payload") or {}

        # Reject commands with MQTT topic injection characters or suspiciously long names
        if (
            not command
            or len(command) > 64
            or not all(c.isalnum() or c in ("_", "-") for c in command)
        ):
            raise ServiceValidationError(f"Invalid command name: {command!r}")

        normalized_command = normalize_command_name(command)
        _LOGGER.debug(
            "yarbo.send_command: device=%s command=%s payload=%s",
            device_id,
            normalized_command,
            payload,
        )
        _, coordinator = _get_client_and_coordinator(hass, device_id)
        telemetry = getattr(coordinator, "data", None)
        current_head = getattr(telemetry, "head_type", None) if telemetry else None
        is_valid, error_message = validate_head_type_for_command(normalized_command, current_head)
        if not is_valid:
            raise ServiceValidationError(error_message)
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.publish_raw(normalized_command, payload)

    async def handle_start_plan(call: ServiceCall) -> None:
        """Handle yarbo.start_plan — start a saved work plan by ID."""
        device_id: str = call.data["device_id"]
        plan_id: str = call.data["plan_id"]
        _LOGGER.debug("yarbo.start_plan: device=%s plan_id=%s", device_id, plan_id)
        _, coordinator = _get_client_and_coordinator(hass, device_id)
        # Optional percent override; fall back to coordinator stored value
        percent: int = call.data.get("percent", coordinator.plan_start_percent)
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.start_plan(plan_id, percent=percent)

    async def handle_pause(call: ServiceCall) -> None:
        """Handle yarbo.pause — pause current job."""
        _, coordinator = _get_client_and_coordinator(hass, call.data["device_id"])
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.publish_raw("planning_paused", {})

    async def handle_resume(call: ServiceCall) -> None:
        """Handle yarbo.resume — resume paused job."""
        _, coordinator = _get_client_and_coordinator(hass, call.data["device_id"])
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.publish_raw("resume", {})

    async def handle_return_to_dock(call: ServiceCall) -> None:
        """Handle yarbo.return_to_dock — send robot to dock."""
        _, coordinator = _get_client_and_coordinator(hass, call.data["device_id"])
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.return_to_dock()

    async def handle_set_lights(call: ServiceCall) -> None:
        """Handle yarbo.set_lights — set 7 LED channel brightness values."""
        device_id: str = call.data["device_id"]
        brightness: int = call.data.get("brightness", 255)
        _LOGGER.debug("yarbo.set_lights: device=%s brightness=%s", device_id, brightness)
        _, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.set_lights(
                YarboLightState(
                    led_head=call.data.get("led_head", brightness),
                    led_left_w=call.data.get("led_left_w", brightness),
                    led_right_w=call.data.get("led_right_w", brightness),
                    body_left_r=call.data.get("body_left_r", brightness),
                    body_right_r=call.data.get("body_right_r", brightness),
                    tail_left_r=call.data.get("tail_left_r", brightness),
                    tail_right_r=call.data.get("tail_right_r", brightness),
                )
            )
            coordinator.light_state["led_head"] = call.data.get("led_head", brightness)
            coordinator.light_state["led_left_w"] = call.data.get("led_left_w", brightness)
            coordinator.light_state["led_right_w"] = call.data.get("led_right_w", brightness)
            coordinator.light_state["body_left_r"] = call.data.get("body_left_r", brightness)
            coordinator.light_state["body_right_r"] = call.data.get("body_right_r", brightness)
            coordinator.light_state["tail_left_r"] = call.data.get("tail_left_r", brightness)
            coordinator.light_state["tail_right_r"] = call.data.get("tail_right_r", brightness)

    async def handle_set_chute_velocity(call: ServiceCall) -> None:
        """Handle yarbo.set_chute_velocity — control snow chute direction."""
        device_id: str = call.data["device_id"]
        # Service field 'velocity' maps to python-yarbo API parameter 'vel'
        velocity: int = call.data["velocity"]
        _LOGGER.debug("yarbo.set_chute_velocity: device=%s velocity=%d", device_id, velocity)
        _, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            client = coordinator.client
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.set_chute(vel=velocity)

    async def handle_manual_drive(call: ServiceCall) -> None:
        """Handle yarbo.manual_drive — send linear/angular velocity."""
        device_id: str = call.data["device_id"]
        linear: float = call.data["linear"]
        angular: float = call.data["angular"]
        _LOGGER.debug(
            "yarbo.manual_drive: device=%s linear=%.3f angular=%.3f",
            device_id,
            linear,
            angular,
        )
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.set_velocity(linear, angular)

    async def handle_go_to_waypoint(call: ServiceCall) -> None:
        """Handle yarbo.go_to_waypoint — navigate to waypoint index."""
        device_id: str = call.data["device_id"]
        index: int = call.data["index"]
        _LOGGER.debug("yarbo.go_to_waypoint: device=%s index=%d", device_id, index)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.publish_raw("start_way_point", {"index": index})

    async def handle_delete_plan(call: ServiceCall) -> None:
        """Handle yarbo.delete_plan — delete a plan by id."""
        device_id: str = call.data["device_id"]
        plan_id: str = call.data["plan_id"]
        _LOGGER.debug("yarbo.delete_plan: device=%s plan_id=%s", device_id, plan_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.delete_plan(plan_id, confirm=True)

    async def handle_delete_all_plans(call: ServiceCall) -> None:
        """Handle yarbo.delete_all_plans — delete all plans."""
        device_id: str = call.data["device_id"]
        _LOGGER.debug("yarbo.delete_all_plans: device=%s", device_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.delete_all_plans(confirm=True)

    async def handle_erase_map(call: ServiceCall) -> None:
        """Handle yarbo.erase_map — erase the current map."""
        device_id: str = call.data["device_id"]
        _LOGGER.debug("yarbo.erase_map: device=%s", device_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.erase_map(confirm=True)

    async def handle_map_recovery(call: ServiceCall) -> None:
        """Handle yarbo.map_recovery — recover a map by optional map ID."""
        device_id: str = call.data["device_id"]
        map_id: str | None = call.data.get("map_id")
        _LOGGER.debug("yarbo.map_recovery: device=%s map_id=%s", device_id, map_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.map_recovery(map_id=map_id, confirm=True)

    async def handle_save_current_map(call: ServiceCall) -> None:
        """Handle yarbo.save_current_map — save the current working map."""
        device_id: str = call.data["device_id"]
        _LOGGER.debug("yarbo.save_current_map: device=%s", device_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.publish_raw("save_current_map", {})

    async def handle_save_map_backup(call: ServiceCall) -> None:
        """Handle yarbo.save_map_backup_and_get_all_map_backup_nameandid.

        Saves a backup of the current map and retrieves all backup names and IDs.
        """
        device_id: str = call.data["device_id"]
        _LOGGER.debug("yarbo.save_map_backup: device=%s", device_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            if _should_auto_acquire_controller(coordinator):
                await _acquire_controller(client, coordinator)
            await client.publish_raw("save_map_backup_and_get_all_map_backup_nameandid", {})

    services = {
        SERVICE_SEND_COMMAND: (handle_send_command, SERVICE_SEND_COMMAND_SCHEMA),
        SERVICE_START_PLAN: (handle_start_plan, SERVICE_START_PLAN_SCHEMA),
        SERVICE_PAUSE: (handle_pause, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_RESUME: (handle_resume, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_RETURN_TO_DOCK: (handle_return_to_dock, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_SET_LIGHTS: (handle_set_lights, SERVICE_SET_LIGHTS_SCHEMA),
        SERVICE_SET_CHUTE_VELOCITY: (handle_set_chute_velocity, SERVICE_SET_CHUTE_VELOCITY_SCHEMA),
        SERVICE_MANUAL_DRIVE: (handle_manual_drive, SERVICE_MANUAL_DRIVE_SCHEMA),
        SERVICE_GO_TO_WAYPOINT: (handle_go_to_waypoint, SERVICE_GO_TO_WAYPOINT_SCHEMA),
        SERVICE_DELETE_PLAN: (handle_delete_plan, SERVICE_DELETE_PLAN_SCHEMA),
        SERVICE_DELETE_ALL_PLANS: (handle_delete_all_plans, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_ERASE_MAP: (handle_erase_map, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_MAP_RECOVERY: (handle_map_recovery, SERVICE_MAP_RECOVERY_SCHEMA),
        SERVICE_SAVE_CURRENT_MAP: (handle_save_current_map, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_SAVE_MAP_BACKUP: (handle_save_map_backup, SERVICE_DEVICE_ONLY_SCHEMA),
    }

    for name, (handler, schema) in services.items():
        if not hass.services.has_service(DOMAIN, name):
            hass.services.async_register(DOMAIN, name, handler, schema=schema)

    _LOGGER.debug("Yarbo services registered")


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Yarbo services when the last config entry is removed."""
    service_names = [
        SERVICE_SEND_COMMAND,
        SERVICE_START_PLAN,
        SERVICE_PAUSE,
        SERVICE_RESUME,
        SERVICE_RETURN_TO_DOCK,
        SERVICE_SET_LIGHTS,
        SERVICE_SET_CHUTE_VELOCITY,
        SERVICE_MANUAL_DRIVE,
        SERVICE_GO_TO_WAYPOINT,
        SERVICE_DELETE_PLAN,
        SERVICE_DELETE_ALL_PLANS,
        SERVICE_ERASE_MAP,
        SERVICE_MAP_RECOVERY,
        SERVICE_SAVE_CURRENT_MAP,
        SERVICE_SAVE_MAP_BACKUP,
    ]
    for name in service_names:
        if hass.services.has_service(DOMAIN, name):
            hass.services.async_remove(DOMAIN, name)
