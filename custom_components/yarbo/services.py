"""Service registration for the Yarbo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_COMMAND = "send_command"

SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("command"): str,
        vol.Optional("payload", default={}): dict,
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register Yarbo services.

    Services registered here:
    - yarbo.send_command — escape hatch for raw MQTT commands (v0.1.0)
    - yarbo.start_plan   — start a saved work plan (v0.3.0)
    - yarbo.pause        — pause current job (v0.2.0)
    - yarbo.resume       — resume paused job (v0.2.0)
    - yarbo.return_to_dock — send robot to dock (v0.2.0)
    - yarbo.set_lights   — set all 7 LED channels (v0.2.0)
    - yarbo.set_chute_velocity — snow chute control (v0.2.0)

    TODO: Implement each service handler in its respective milestone
    """

    async def handle_send_command(call: ServiceCall) -> None:
        """Handle the yarbo.send_command service call.

        Publishes an arbitrary MQTT command to the robot.
        The payload is zlib-compressed automatically by python-yarbo.

        TODO: Implement in v0.1.0
        """
        device_id: str = call.data["device_id"]
        command: str = call.data["command"]
        payload: dict[str, Any] = call.data.get("payload", {})

        _LOGGER.debug(
            "yarbo.send_command: device=%s command=%s payload=%s",
            device_id,
            command,
            payload,
        )

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Device {device_id} not found")
        if not device.config_entries:
            raise ServiceValidationError(f"Device {device_id} has no config entry")
        entry_id = next(iter(device.config_entries))
        if entry_id not in hass.data.get(DOMAIN, {}):
            raise ServiceValidationError(
                f"Device {device_id} is not managed by the Yarbo integration"
            )

        client = hass.data[DOMAIN][entry_id][DATA_CLIENT]
        coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]
        async with coordinator.command_lock:
            await client.get_controller(timeout=5.0)
            await client.publish_raw(command, payload)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_COMMAND,
            handle_send_command,
            schema=SERVICE_SEND_COMMAND_SCHEMA,
        )

    _LOGGER.debug("Yarbo services registered")


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister Yarbo services when the last config entry is removed."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
