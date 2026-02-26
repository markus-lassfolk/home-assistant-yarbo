"""Event platform for Yarbo integration."""

from __future__ import annotations

from typing import Final

from homeassistant.components.event import EventEntity
from homeassistant.components.logbook import async_log_entry
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from yarbo import YarboTelemetry

from .const import CONF_ROBOT_SERIAL, DATA_COORDINATOR, DOMAIN, get_activity_state
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity

EVENT_TYPES: Final[list[str]] = [
    "job_started",
    "job_completed",
    "job_paused",
    "error",
    "head_changed",
    "low_battery",
    "controller_lost",
    "docked",
]


def _activity_state(telemetry: YarboTelemetry) -> str:
    """Compute activity state string from telemetry.

    Single source of truth — also imported by sensor.py to avoid duplication.
    """
    if telemetry.error_code != 0:
        return "error"
    if telemetry.charging_status in (1, 2, 3):
        return "charging"
    state = telemetry.state
    if state in (1, 7, 8):
        return "working"
    if state == 2:
        return "returning"
    if state == 5:
        return "paused"
    if state == 6:
        return "error"
    return "idle"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo event entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboEventEntity(coordinator)])


class YarboEventEntity(YarboEntity, EventEntity):
    """Event entity for Yarbo state transitions."""

    _attr_event_types = EVENT_TYPES
    _attr_translation_key = "events"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "events")
        self._previous: YarboTelemetry | None = None
        self._last_controller_acquired: bool | None = None
        self._device_id: str | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        telemetry = self.telemetry
        if telemetry is not None:
            self._process_events(telemetry)
        super()._handle_coordinator_update()

    def _device_id_for_event(self) -> str | None:
        if self._device_id is not None:
            return self._device_id
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, self.coordinator._entry.data.get(CONF_ROBOT_SERIAL))}
        )
        if device:
            self._device_id = device.id
        return self._device_id

    def _process_events(self, telemetry: YarboTelemetry) -> None:
        previous = self._previous
        if previous is None:
            self._previous = telemetry
            self._last_controller_acquired = getattr(
                self.coordinator.client, "controller_acquired", None
            )
            return

        previous_activity = get_activity_state(previous)
        current_activity = get_activity_state(telemetry)
        device_id = self._device_id_for_event()
        robot_sn = telemetry.serial_number
        now = dt_util.utcnow().isoformat()

        if previous_activity in {"idle", "paused"} and current_activity == "working":
            self._fire_event(
                "job_started",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "plan_id": telemetry.plan_id,
                    "head_type": telemetry.head_type,
                    "timestamp": now,
                },
            )
            self._logbook("Job started")

        if previous_activity in {"working", "returning"} and current_activity in {
            "charging",
            "idle",
        }:
            self._fire_event(
                "job_completed",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "plan_id": telemetry.plan_id,
                    "duration_seconds": telemetry.duration,
                    "timestamp": now,
                },
            )
            self._logbook("Job completed")

        if previous_activity == "working" and current_activity == "paused":
            self._fire_event(
                "job_paused",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "reason": "command",
                    "timestamp": now,
                },
            )
            self._logbook("Job paused")

        if previous.error_code == 0 and telemetry.error_code != 0:
            self._fire_event(
                "error",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "error_code": telemetry.error_code,
                    "error_description": "Unknown error",
                    "timestamp": now,
                },
            )
            self._logbook("Error detected")

        if previous.head_type != telemetry.head_type:
            self._fire_event(
                "head_changed",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "previous_head": previous.head_type,
                    "new_head": telemetry.head_type,
                    "timestamp": now,
                },
            )

        if (
            previous.battery_capacity >= 20
            and telemetry.battery_capacity < 20
            and telemetry.charging_status not in (1, 2, 3)
        ):
            self._fire_event(
                "low_battery",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "battery_level": telemetry.battery_capacity,
                    "timestamp": now,
                },
            )
            self._logbook("Low battery")

        current_controller = getattr(self.coordinator.client, "controller_acquired", None)
        if self._last_controller_acquired and not current_controller:
            self._fire_event(
                "controller_lost",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "timestamp": now,
                },
            )
            self._logbook("Controller role lost")
        self._last_controller_acquired = current_controller

        if previous.charging_status == 0 and telemetry.charging_status in (1, 2, 3):
            self._fire_event(
                "docked",
                {
                    "device_id": device_id,
                    "robot_sn": robot_sn,
                    "timestamp": now,
                },
            )
            self._logbook("Docked")

        self._previous = telemetry

    def _fire_event(self, event_type: str, data: dict) -> None:  # type: ignore[type-arg]
        self.hass.bus.async_fire(f"yarbo_{event_type}", data)
        self._trigger_event(event_type, data)  # Fixed: was async_trigger (wrong method name)
        self.async_write_ha_state()

    def _logbook(self, message: str) -> None:
        async_log_entry(
            self.hass,
            name=self.name or "Yarbo",
            message=message,
            entity_id=self.entity_id,
            domain=DOMAIN,
        )
