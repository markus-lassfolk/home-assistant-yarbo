"""Service registration for the Yarbo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from yarbo import YarboLightState

from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_COMMAND = "send_command"
SERVICE_START_PLAN = "start_plan"
SERVICE_PAUSE = "pause"
SERVICE_RESUME = "resume"
SERVICE_RETURN_TO_DOCK = "return_to_dock"
SERVICE_SET_LIGHTS = "set_lights"
SERVICE_SET_CHUTE_VELOCITY = "set_chute_velocity"

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


def async_register_services(hass: HomeAssistant) -> None:
    """Register all Yarbo services."""

    async def handle_send_command(call: ServiceCall) -> None:
        """Handle yarbo.send_command — publish arbitrary MQTT command."""
        device_id: str = call.data["device_id"]
        command: str = call.data["command"]
        payload: dict[str, Any] = call.data.get("payload") or {}
        _LOGGER.debug(
            "yarbo.send_command: device=%s command=%s payload=%s", device_id, command, payload
        )
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.publish_raw(command, payload)

    async def handle_start_plan(call: ServiceCall) -> None:
        """Handle yarbo.start_plan — start a saved work plan by ID."""
        device_id: str = call.data["device_id"]
        plan_id: str = call.data["plan_id"]
        _LOGGER.debug("yarbo.start_plan: device=%s plan_id=%s", device_id, plan_id)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.publish_command("start_plan", {"planId": plan_id})

    async def handle_pause(call: ServiceCall) -> None:
        """Handle yarbo.pause — pause current job."""
        client, coordinator = _get_client_and_coordinator(hass, call.data["device_id"])
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.publish_command("planning_paused", {})

    async def handle_resume(call: ServiceCall) -> None:
        """Handle yarbo.resume — resume paused job."""
        client, coordinator = _get_client_and_coordinator(hass, call.data["device_id"])
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.publish_command("resume", {})

    async def handle_return_to_dock(call: ServiceCall) -> None:
        """Handle yarbo.return_to_dock — send robot to dock."""
        client, coordinator = _get_client_and_coordinator(hass, call.data["device_id"])
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.publish_command("cmd_recharge", {})

    async def handle_set_lights(call: ServiceCall) -> None:
        """Handle yarbo.set_lights — set 7 LED channel brightness values."""
        device_id: str = call.data["device_id"]
        brightness: int = call.data.get("brightness", 255)
        _LOGGER.debug("yarbo.set_lights: device=%s brightness=%s", device_id, brightness)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
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

    async def handle_set_chute_velocity(call: ServiceCall) -> None:
        """Handle yarbo.set_chute_velocity — control snow chute direction."""
        device_id: str = call.data["device_id"]
        # Service field 'velocity' maps to python-yarbo API parameter 'vel'
        velocity: int = call.data["velocity"]
        _LOGGER.debug("yarbo.set_chute_velocity: device=%s velocity=%d", device_id, velocity)
        client, coordinator = _get_client_and_coordinator(hass, device_id)
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.set_chute(vel=velocity)

    services = {
        SERVICE_SEND_COMMAND: (handle_send_command, SERVICE_SEND_COMMAND_SCHEMA),
        SERVICE_START_PLAN: (handle_start_plan, SERVICE_START_PLAN_SCHEMA),
        SERVICE_PAUSE: (handle_pause, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_RESUME: (handle_resume, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_RETURN_TO_DOCK: (handle_return_to_dock, SERVICE_DEVICE_ONLY_SCHEMA),
        SERVICE_SET_LIGHTS: (handle_set_lights, SERVICE_SET_LIGHTS_SCHEMA),
        SERVICE_SET_CHUTE_VELOCITY: (handle_set_chute_velocity, SERVICE_SET_CHUTE_VELOCITY_SCHEMA),
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
    ]
    for name in service_names:
        if hass.services.has_service(DOMAIN, name):
            hass.services.async_remove(DOMAIN, name)
