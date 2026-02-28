"""Push-based DataUpdateCoordinator for Yarbo telemetry."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from yarbo import YarboLocalClient
from yarbo.exceptions import YarboConnectionError

from .const import (
    CONF_ALTERNATE_BROKER_HOST,
    CONF_BROKER_ENDPOINTS,
    CONF_BROKER_HOST,
    CONF_BROKER_PORT,
    CONF_CONNECTION_PATH,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    CONF_ROVER_IP,
    DATA_CLIENT,
    DEFAULT_BROKER_PORT,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MQTT_RECORDING,
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    ENDPOINT_TYPE_DC,
    ENDPOINT_TYPE_ROVER,
    HEARTBEAT_TIMEOUT_SECONDS,
    MQTT_RECORDING_MAX_SIZE_BYTES,
    OPT_DEBUG_LOGGING,
    OPT_MQTT_RECORDING,
    OPT_TELEMETRY_THROTTLE,
    TELEMETRY_RETRY_DELAY_SECONDS,
    is_active_only_diagnostic_command,
    is_active_operation,
    normalize_command_name,
)
from .models import YarboTelemetry
from .mqtt_recorder import MqttRecorder
from .repairs import (
    async_create_controller_lost_issue,
    async_create_mqtt_disconnect_issue,
    async_delete_controller_lost_issue,
    async_delete_mqtt_disconnect_issue,
)

# ──────────────────────────────────────────────────────────────────────
# MQTT Command Verification Status (tested live 2026-02-28, SN 24400102L8HO5227)
#
# ✅ CONFIRMED (data_feedback response received):
#   get_controller        → {"state": 0, "msg": "Successfully connected..."}
#   shutdown              → {"state": 0, "msg": "success"} — POWERS OFF ROBOT!
#   restart_container     → {"state": 0, "msg": "Container restarted successfully."}
#   read_clean_area       → {"state": -2} when no areas (command recognized)
#   ignore_obstacles      → {"state": 0} with payload {"state": int}
#   read_no_charge_period → {"state": 0, "data": []}
#   get_connect_wifi_name → {"state": 0, "data": {"name":"LWLML-IOT","ip":"..."}}
#
# ⚠️ RECOGNIZED BUT ERROR:
#   set_person_detect     → {"state": -1} — may require camera hardware
#
# 🔇 FIRE-AND-FORGET (no data_feedback, execute silently):
#   head_light, roof_lights_enable, laser_toggle, camera_toggle,
#   set_sound_param, song_cmd, usb_toggle, cmd_vel, cmd_recharge,
#   planning_paused, resume, dstop, emergency_stop_active,
#   emergency_unlock, save_charging_point, start_hotspot,
#   save_map_backup, in_plan_action, start_plan, del_plan,
#   del_all_plan, start_way_point
#
# ❓ NO RESPONSE WHILE IDLE (may need active/mowing state):
#   battery_cell_temp_msg, motor_temp_samp, body_current_msg,
#   head_current_msg, speed_msg, odometer_msg, product_code_msg,
#   hub_info, get_wifi_list, read_recharge_point, get_all_map_backup,
#   read_schedules, read_all_plan, read_plan
#
# ❌ WRONG NAMES (silently ignored by robot):
#   obstacle_toggle, setIgnoreObstacle, read_all_clean_area,
#   readCleanArea, shutdownYarbo, restart_yarbo_system,
#   cmd_roller, blower_speed, set_roller_speed
# ──────────────────────────────────────────────────────────────────────

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PlanSummary:
    """Minimal work plan summary."""

    plan_id: str | int
    name: str
    area_ids: list[str | int]


def _to_float(value: Any) -> float | None:
    """Convert a value to float, returning None on failure (not None-safe for 0.0)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _extract_float(data: Any) -> float | None:
    """Best-effort numeric extraction from feedback payloads."""
    scalar = _to_float(data)
    if scalar is not None:
        return scalar
    if isinstance(data, dict):
        for key in ("value", "current", "speed", "temp", "temperature", "data"):
            value = data.get(key)
            extracted = _extract_float(value)
            if extracted is not None:
                return extracted
    if isinstance(data, list) and data:
        return _extract_float(data[0])
    return None


def _extract_text(data: Any, keys: tuple[str, ...]) -> str | None:
    """Best-effort text extraction from feedback payloads."""
    if isinstance(data, (str, bytes)):
        return data.decode() if isinstance(data, bytes) else data
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, (str, bytes)):
                return value.decode() if isinstance(value, bytes) else value
            return str(value)
        return json.dumps(data, ensure_ascii=True)
    if isinstance(data, list):
        return json.dumps(data, ensure_ascii=True)
    return None


class YarboDataCoordinator(DataUpdateCoordinator[YarboTelemetry]):
    """Push-based coordinator with periodic diagnostic polling.

    Receives telemetry from the python-yarbo library via an async generator
    (client.watch_telemetry()) and pushes updates to all entities.

    The robot streams DeviceMSG at ~1-2 Hz. A configurable throttle (default 1.0s)
    debounces updates to avoid stressing the HA recorder and event bus.

    On connection error, the loop retries after TELEMETRY_RETRY_DELAY_SECONDS.

    A separate diagnostic polling task runs every 300s to fetch wifi, battery cell
    temps, odometer, and other non-streaming data. Core telemetry continues via
    the push stream without interruption.

    Repair issues managed here:
    - mqtt_disconnect: raised by _heartbeat_watchdog when no telemetry for > 60s
    - controller_lost: raised by report_controller_lost(), cleared by resolve_controller_lost()
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,  # YarboLocalClient from python-yarbo
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        Push-based telemetry with periodic diagnostic polling in a separate task.
        Core telemetry updates are triggered by incoming MQTT messages.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.client = client
        self._entry = entry
        self._telemetry_task: asyncio.Task[None] | None = None
        self._watchdog_task: asyncio.Task[None] | None = None
        self._diagnostic_task: asyncio.Task[None] | None = None
        self._last_update: float = 0.0
        self._last_seen: float = 0.0
        self._issue_active = False
        self._controller_lost_active = False
        self._diagnostic_lock = asyncio.Semaphore(1)
        self._throttle_interval: float = entry.options.get(
            OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE
        )
        self._update_count: int = 0

        # Debug logging toggle
        self._debug_logging: bool = entry.options.get(OPT_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
        self._original_log_levels: dict[str, int] = {}
        if self._debug_logging:
            self._apply_debug_logging(True)

        # MQTT recorder for diagnostics
        storage_dir = Path(hass.config.config_dir)
        serial = entry.data.get(CONF_ROBOT_SERIAL, "unknown")
        self._recorder = MqttRecorder(
            storage_dir=storage_dir,
            serial_number=serial,
            max_size_bytes=MQTT_RECORDING_MAX_SIZE_BYTES,
        )
        self._recorder_enabled_option = entry.options.get(
            OPT_MQTT_RECORDING, DEFAULT_MQTT_RECORDING
        )
        self.command_lock = asyncio.Lock()
        self.light_state: dict[str, int] = {
            "led_head": 0,
            "led_left_w": 0,
            "led_right_w": 0,
            "body_left_r": 0,
            "body_right_r": 0,
            "tail_left_r": 0,
            "tail_right_r": 0,
        }
        # Latest firmware version from cloud API — populated when cloud is enabled
        self.latest_firmware_version: str | None = None
        self._plan_summaries: list[PlanSummary] = []
        self._plan_by_id: dict[str | int, PlanSummary] = {}
        self._plan_remaining_time: int | None = None
        self._selected_plan_id: str | int | None = None
        self._plan_start_percent: int = int(entry.options.get("plan_start_percent", 0))
        self._wifi_name: str | None = None
        self._battery_cell_temp_min: float | None = None
        self._battery_cell_temp_max: float | None = None
        self._battery_cell_temp_avg: float | None = None
        self._odometer_m: float | None = None
        self._no_charge_period_active: bool | None = None
        self._no_charge_period_start: str | None = None
        self._no_charge_period_end: str | None = None
        self._no_charge_period_periods: list[Any] | None = None
        self._schedules: list[Any] = []
        self._body_current: float | None = None
        self._head_current: float | None = None
        self._speed_m_s: float | None = None
        self._product_code: str | None = None
        self._hub_info: str | None = None
        self._recharge_point_status: str | None = None
        self._recharge_point_details: dict[str, Any] | None = None
        self._wifi_list: list[Any] = []
        self._map_backups: list[Any] = []
        self._clean_areas: list[Any] = []
        self._motor_temp_c: float | None = None

    def update_options(self, options: dict[str, Any]) -> None:
        """Apply updated config entry options without requiring a full reload.

        Called by the options update listener in __init__.py when the user
        changes settings in the integration options UI.

        Currently applies:
        - telemetry_throttle: debounce interval for pushing updates to HA
        """
        self._throttle_interval = options.get(OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE)

        # Debug logging
        new_debug = options.get(OPT_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
        if new_debug != self._debug_logging:
            self._debug_logging = new_debug
            self._apply_debug_logging(new_debug)

        # MQTT recording
        new_recording = options.get(OPT_MQTT_RECORDING, DEFAULT_MQTT_RECORDING)
        if new_recording != self._recorder_enabled_option:
            self._recorder_enabled_option = new_recording
            if new_recording and not self._recorder.enabled:
                self.hass.async_create_task(self._async_start_recorder())
            elif not new_recording and self._recorder.enabled:
                self.hass.async_create_task(self._async_stop_recorder())

        _LOGGER.debug(
            "Yarbo options updated — throttle=%.1fs, debug=%s, recording=%s",
            self._throttle_interval,
            self._debug_logging,
            self._recorder.enabled,
        )

    def report_controller_lost(self) -> None:
        """Raise an ERROR repair issue when the controller session is stolen.

        Call this from command handlers when a command fails because another
        client holds the controller (data_feedback error).
        The issue is marked fixable — the user can re-acquire via the repair UI.
        """
        if self._controller_lost_active:
            return
        name: str = self._entry.data.get(CONF_ROBOT_NAME, "Yarbo")
        async_create_controller_lost_issue(self.hass, self._entry.entry_id, name)
        self._controller_lost_active = True

    def resolve_controller_lost(self) -> None:
        """Clear the controller lost repair issue after successful re-acquisition."""
        if not self._controller_lost_active:
            return
        async_delete_controller_lost_issue(self.hass, self._entry.entry_id)
        self._controller_lost_active = False

    @property
    def entry(self) -> ConfigEntry:
        """Return the config entry (public accessor)."""
        return self._entry

    @property
    def plan_options(self) -> list[str]:
        """Return available plan names."""
        return [plan.name for plan in self._plan_summaries]

    @property
    def active_plan_id(self) -> str | int | None:
        """Return the active plan id, preferring telemetry when available."""
        telemetry = self.data
        if telemetry is not None and getattr(telemetry, "plan_id", None) is not None:
            return telemetry.plan_id
        return self._selected_plan_id

    def plan_name_for_id(self, plan_id: str | int | None) -> str | None:
        """Return plan name for an id, if known."""
        if plan_id is None:
            return None
        plan = self._plan_by_id.get(plan_id)
        return plan.name if plan else None

    def plan_id_for_name(self, name: str) -> str | int | None:
        """Return plan id for a plan name, if known."""
        for plan in self._plan_summaries:
            if plan.name == name:
                return plan.plan_id
        return None

    @property
    def plan_remaining_time(self) -> int | None:
        """Return remaining time for the last read plan, in seconds."""
        return self._plan_remaining_time

    @property
    def plan_start_percent(self) -> int:
        """Return the configured plan start percentage."""
        return self._plan_start_percent

    def set_plan_start_percent(self, value: int) -> None:
        """Update the stored plan start percentage (0-100)."""
        self._plan_start_percent = max(0, min(100, int(value)))

    @property
    def wifi_name(self) -> str | None:
        """Return the last known WiFi network name."""
        return self._wifi_name

    @property
    def battery_cell_temp_min(self) -> float | None:
        """Return minimum battery cell temperature (°C)."""
        return self._battery_cell_temp_min

    @property
    def battery_cell_temp_max(self) -> float | None:
        """Return maximum battery cell temperature (°C)."""
        return self._battery_cell_temp_max

    @property
    def battery_cell_temp_avg(self) -> float | None:
        """Return average battery cell temperature (°C)."""
        return self._battery_cell_temp_avg

    @property
    def odometer_m(self) -> float | None:
        """Return odometer distance in meters."""
        return self._odometer_m

    @property
    def no_charge_period_active(self) -> bool | None:
        """Return whether a no-charge period is active."""
        return self._no_charge_period_active

    @property
    def no_charge_period_start(self) -> str | None:
        """Return no-charge period start time (if known)."""
        return self._no_charge_period_start

    @property
    def no_charge_period_end(self) -> str | None:
        """Return no-charge period end time (if known)."""
        return self._no_charge_period_end

    @property
    def no_charge_periods(self) -> list[Any] | None:
        """Return list of no-charge periods, if provided."""
        return self._no_charge_period_periods

    @property
    def schedule_list(self) -> list[Any]:
        """Return last known schedules list."""
        return self._schedules

    @property
    def body_current(self) -> float | None:
        """Return last known body current (A)."""
        return self._body_current

    @property
    def head_current(self) -> float | None:
        """Return last known head current (A)."""
        return self._head_current

    @property
    def speed_m_s(self) -> float | None:
        """Return last known speed (m/s)."""
        return self._speed_m_s

    @property
    def product_code(self) -> str | None:
        """Return last known product code."""
        return self._product_code

    @property
    def hub_info(self) -> str | None:
        """Return last known hub info."""
        return self._hub_info

    @property
    def recharge_point_status(self) -> str | None:
        """Return last known recharge point status."""
        return self._recharge_point_status

    @property
    def recharge_point_details(self) -> dict[str, Any] | None:
        """Return recharge point details."""
        return self._recharge_point_details

    @property
    def wifi_list(self) -> list[Any]:
        """Return last known WiFi list."""
        return self._wifi_list

    @property
    def map_backups(self) -> list[Any]:
        """Return last known map backups list."""
        return self._map_backups

    @property
    def clean_areas(self) -> list[Any]:
        """Return last known clean areas list."""
        return self._clean_areas

    @property
    def motor_temp_c(self) -> float | None:
        """Return last known motor temperature (°C)."""
        return self._motor_temp_c

    async def read_all_plans(self, timeout: float = 5.0) -> list[PlanSummary]:
        """Read all plan summaries from the robot."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("read_all_plan", {}, timeout)
        data = response.get("data") if isinstance(response, dict) else None
        plans = data if isinstance(data, list) else []
        summaries: list[PlanSummary] = []
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            plan_id = plan.get("id")
            name = plan.get("name")
            if plan_id is None or name is None:
                continue
            area_ids_raw = plan.get("areaIds") or []
            area_ids = list(area_ids_raw) if isinstance(area_ids_raw, list) else [str(area_ids_raw)]
            summaries.append(PlanSummary(plan_id=plan_id, name=str(name), area_ids=area_ids))
        self._plan_summaries = summaries
        self._plan_by_id = {plan.plan_id: plan for plan in summaries}
        self.async_update_listeners()
        return summaries

    async def read_plan(self, plan_id: str | int, timeout: float = 5.0) -> dict[str, Any]:
        """Read a specific plan detail and update remaining time."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("read_plan", {"id": plan_id}, timeout)
        detail: dict[str, Any] = {}
        if isinstance(response, dict):
            if isinstance(response.get("data"), dict):
                detail = response["data"]
            else:
                detail = response
        left_time = detail.get("leftTime")
        if isinstance(left_time, (int, float)):
            self._plan_remaining_time = int(left_time)
        else:
            self._plan_remaining_time = None
        self.async_update_listeners()
        return detail

    async def start_plan(self, plan_id: str | int) -> None:
        """Start a work plan by id."""
        async with self.command_lock:
            await self.client.get_controller(timeout=5.0)
            await self.client.publish_command(
                "start_plan",
                {"planId": plan_id, "percent": self._plan_start_percent},
            )
        self._selected_plan_id = plan_id
        self.async_update_listeners()
        try:
            await self.read_plan(plan_id)
        except Exception as err:  # pragma: no cover - best effort
            _LOGGER.debug("Failed to read plan %s after start: %s", plan_id, err)

    async def plan_action(self, action: str) -> None:
        """Send an in-plan action (pause, resume, stop)."""
        if action not in {"pause", "resume", "stop"}:
            raise ValueError(f"Unsupported plan action: {action}")
        async with self.command_lock:
            await self.client.get_controller(timeout=5.0)
            # 🔇 Fire-and-forget: no data_feedback response
            await self.client.publish_command("in_plan_action", {"action": action})

    async def _request_data_feedback(
        self,
        command: str,
        payload: dict[str, Any],
        timeout: float,
        skip_lock: bool = False,
    ) -> dict[str, Any]:
        """Publish a command and await matching data_feedback.

        Args:
            command: MQTT command name
            payload: Command payload
            timeout: Response timeout in seconds
            skip_lock: If True, skip command_lock acquisition (for low-priority diagnostics)

        Note: diagnostic commands in ACTIVE_ONLY_DIAGNOSTIC_COMMANDS only
        respond while the robot is actively working, so requests are skipped
        when the robot is idle or charging.
        """
        normalized_command = normalize_command_name(command)
        if is_active_only_diagnostic_command(normalized_command) and not is_active_operation(
            self.data
        ):
            _LOGGER.debug(
                "Skipping %s data_feedback: robot not in active operation state",
                normalized_command,
            )
            return {}

        async def _execute_command() -> Any:
            feedback_coro = self._await_data_feedback(normalized_command, timeout)
            feedback_task = asyncio.create_task(feedback_coro)
            await asyncio.sleep(0)
            await self.client.publish_command(normalized_command, payload)
            try:
                if self._recorder.enabled:
                    try:
                        await self.hass.async_add_executor_job(
                            self._recorder.record_tx, normalized_command, payload or {}
                        )
                    except Exception as rec_err:
                        _LOGGER.debug("MQTT recorder error (non-fatal): %s", rec_err)
                return await feedback_task
            except asyncio.CancelledError:
                feedback_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await feedback_task
                raise

        if skip_lock:
            response = await _execute_command()
        else:
            async with self.command_lock:
                response = await _execute_command()
        if not isinstance(response, dict):
            return {}
        return response

    async def get_wifi_name(self, timeout: float = 5.0, skip_lock: bool = False) -> str | None:
        """Request the connected WiFi network name."""
        # ✅ Verified 2026-02-28: returns SSID, IP, signal
        response = await self._request_data_feedback(
            "get_connect_wifi_name", {}, timeout, skip_lock
        )
        if not response:
            return self._wifi_name
        data = response.get("data", response)
        name: str | None = None
        if isinstance(data, dict):
            for key in ("wifi_name", "ssid", "name", "wifi", "wifiName"):
                value = data.get(key)
                if value:
                    name = str(value)
                    break
        elif isinstance(data, (str, bytes)):
            name = data.decode() if isinstance(data, bytes) else data
        self._wifi_name = name
        return name

    async def get_battery_cell_temps(
        self, timeout: float = 5.0, skip_lock: bool = False
    ) -> tuple[float | None, ...]:
        """Request battery cell temperature stats (min, max, avg)."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback(
            "battery_cell_temp_msg", {}, timeout, skip_lock
        )
        if not response:
            return (
                self._battery_cell_temp_min,
                self._battery_cell_temp_max,
                self._battery_cell_temp_avg,
            )
        data = response.get("data", response)
        min_val = max_val = avg_val = None

        def _first_not_none(data: dict[str, Any], *keys: str) -> float | None:
            """Return _to_float of the first key whose value is not None."""
            for key in keys:
                raw = data.get(key)
                if raw is not None:
                    converted = _to_float(raw)
                    if converted is not None:
                        return converted
            return None

        if isinstance(data, dict):
            min_val = _first_not_none(data, "min", "min_temp", "min_temp_c", "temp_min")
            max_val = _first_not_none(data, "max", "max_temp", "max_temp_c", "temp_max")
            avg_val = _first_not_none(data, "avg", "avg_temp", "avg_temp_c", "temp_avg")
            temps = data.get("temps") or data.get("cell_temps") or data.get("temperature_list")
            if temps is None:
                temps = data.get("battery_cell_temp")
            if isinstance(temps, list):
                numeric = [val for val in (_to_float(t) for t in temps) if val is not None]
                if numeric:
                    min_val = min_val if min_val is not None else min(numeric)
                    max_val = max_val if max_val is not None else max(numeric)
                    avg_val = avg_val if avg_val is not None else sum(numeric) / len(numeric)
        elif isinstance(data, list):
            numeric = [val for val in (_to_float(t) for t in data) if val is not None]
            if numeric:
                min_val = min(numeric)
                max_val = max(numeric)
                avg_val = sum(numeric) / len(numeric)

        self._battery_cell_temp_min = min_val
        self._battery_cell_temp_max = max_val
        self._battery_cell_temp_avg = avg_val
        return min_val, max_val, avg_val

    async def get_odometer(self, timeout: float = 5.0, skip_lock: bool = False) -> float | None:
        """Request odometer distance (meters)."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("odometer_msg", {}, timeout, skip_lock)
        if not response:
            return self._odometer_m
        data = response.get("data", response)
        odometer_m: float | None = None
        if isinstance(data, dict):
            for key in (
                "total_distance_m",
                "distance_m",
                "odometer_m",
                "total_distance",
                "distance",
                "odometer",
                "total",
            ):
                value = _to_float(data.get(key))
                if value is not None:
                    odometer_m = value
                    break
            if odometer_m is None:
                for key in ("total_distance_km", "distance_km", "odometer_km", "total_km"):
                    value = _to_float(data.get(key))
                    if value is not None:
                        odometer_m = value * 1000.0
                        break
        else:
            odometer_m = _to_float(data)

        self._odometer_m = odometer_m
        return odometer_m

    async def get_no_charge_period(
        self, timeout: float = 5.0, skip_lock: bool = False
    ) -> dict[str, Any]:
        """Request no-charge period settings."""
        # ✅ Verified 2026-02-28: returns data_feedback
        response = await self._request_data_feedback(
            "read_no_charge_period", {}, timeout, skip_lock
        )
        if not response:
            return {}
        data = response.get("data", response)
        active: bool | None = None
        start_time: str | None = None
        end_time: str | None = None
        periods: list[Any] | None = None

        def _to_bool(value: Any) -> bool | None:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"1", "true", "on", "enabled", "active", "yes"}:
                    return True
                if lowered in {"0", "false", "off", "disabled", "inactive", "no"}:
                    return False
            return None

        if isinstance(data, dict):
            for key in ("enable", "enabled", "state", "active", "status", "on"):
                active = _to_bool(data.get(key))
                if active is not None:
                    break
            start_time = (
                data.get("start_time") or data.get("start") or data.get("begin") or data.get("from")
            )
            end_time = data.get("end_time") or data.get("end") or data.get("to")
            periods = data.get("periods") or data.get("period_list") or data.get("time_list")
            if periods is None and isinstance(data.get("period"), list):
                periods = data.get("period")
        elif isinstance(data, list):
            periods = data

        if periods and (start_time is None or end_time is None):
            first = periods[0] if isinstance(periods, list) else None
            if isinstance(first, dict):
                start_time = start_time or first.get("start") or first.get("start_time")
                end_time = end_time or first.get("end") or first.get("end_time")

        if active is None and (start_time or end_time or periods):
            active = True

        self._no_charge_period_active = active
        self._no_charge_period_start = str(start_time) if start_time is not None else None
        self._no_charge_period_end = str(end_time) if end_time is not None else None
        self._no_charge_period_periods = periods
        return response if isinstance(response, dict) else {}

    async def get_schedules(self, timeout: float = 5.0, skip_lock: bool = False) -> list[Any]:
        """Request schedules list."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("read_schedules", {}, timeout, skip_lock)
        if not response:
            return self._schedules
        data = response.get("data", response)
        schedules: list[Any] = []
        if isinstance(data, list):
            schedules = data
        elif isinstance(data, dict):
            for key in ("schedules", "schedule_list", "schedule", "list"):
                value = data.get(key)
                if isinstance(value, list):
                    schedules = value
                    break
        self._schedules = schedules
        return schedules

    async def get_body_current(self, timeout: float = 5.0, skip_lock: bool = False) -> float | None:
        """Request body current (A)."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("body_current_msg", {}, timeout, skip_lock)
        if not response:
            return self._body_current
        data = response.get("data", response)
        self._body_current = _extract_float(data)
        return self._body_current

    async def get_head_current(self, timeout: float = 5.0, skip_lock: bool = False) -> float | None:
        """Request head current (A)."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("head_current_msg", {}, timeout, skip_lock)
        if not response:
            return self._head_current
        data = response.get("data", response)
        self._head_current = _extract_float(data)
        return self._head_current

    async def get_speed(self, timeout: float = 5.0, skip_lock: bool = False) -> float | None:
        """Request speed (m/s)."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("speed_msg", {}, timeout, skip_lock)
        if not response:
            return self._speed_m_s
        data = response.get("data", response)
        self._speed_m_s = _extract_float(data)
        return self._speed_m_s

    async def get_product_code(self, timeout: float = 5.0, skip_lock: bool = False) -> str | None:
        """Request product code."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("product_code_msg", {}, timeout, skip_lock)
        if not response:
            return self._product_code
        data = response.get("data", response)
        self._product_code = _extract_text(data, ("product_code", "product", "code"))
        return self._product_code

    async def get_hub_info(self, timeout: float = 5.0, skip_lock: bool = False) -> str | None:
        """Request hub info."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("hub_info", {}, timeout, skip_lock)
        if not response:
            return self._hub_info
        data = response.get("data", response)
        self._hub_info = _extract_text(data, ("hub_info", "info", "hub"))
        return self._hub_info

    async def get_recharge_point(self, timeout: float = 5.0, skip_lock: bool = False) -> str | None:
        """Request recharge point status."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("read_recharge_point", {}, timeout, skip_lock)
        if not response:
            return self._recharge_point_status
        data = response.get("data", response)
        status: str | None = None
        details: dict[str, Any] | None = None

        def _status_from_value(value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, bool):
                return "set" if value else "unset"
            if isinstance(value, (int, float)):
                return "set" if value != 0 else "unset"
            if isinstance(value, str) and value.strip():
                return value
            return None

        if isinstance(data, dict):
            details = data
            for key in ("status", "state", "valid", "exist", "enabled", "active"):
                status = _status_from_value(data.get(key))
                if status is not None:
                    break
            if status is None:
                if any(k in data for k in ("x", "y", "lat", "lon", "latitude", "longitude")):
                    status = "set"
        elif data is not None:
            status = _status_from_value(data) or str(data)

        self._recharge_point_status = status
        self._recharge_point_details = details
        return status

    async def get_wifi_list(self, timeout: float = 5.0, skip_lock: bool = False) -> list[Any]:
        """Request available WiFi list."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("get_wifi_list", {}, timeout, skip_lock)
        if not response:
            return self._wifi_list
        data = response.get("data", response)
        wifi_list: list[Any] = []
        if isinstance(data, list):
            wifi_list = data
        elif isinstance(data, dict):
            for key in ("wifi_list", "list", "networks", "aps"):
                value = data.get(key)
                if isinstance(value, list):
                    wifi_list = value
                    break
        self._wifi_list = wifi_list
        return wifi_list

    async def get_map_backups(self, timeout: float = 5.0, skip_lock: bool = False) -> list[Any]:
        """Request map backup list."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("get_all_map_backup", {}, timeout, skip_lock)
        if not response:
            return self._map_backups
        data = response.get("data", response)
        backups: list[Any] = []
        if isinstance(data, list):
            backups = data
        elif isinstance(data, dict):
            for key in ("backups", "list", "map_backups", "maps"):
                value = data.get(key)
                if isinstance(value, list):
                    backups = value
                    break
        self._map_backups = backups
        return backups

    async def get_clean_areas(self, timeout: float = 5.0, skip_lock: bool = False) -> list[Any]:
        """Request clean area list."""
        # Verified against live robot: "read_clean_area" is the correct command.
        # "read_all_clean_area" and "readCleanArea" are silently ignored.
        # ✅ Verified 2026-02-28: correct (not read_all_clean_area or readCleanArea)
        response = await self._request_data_feedback("read_clean_area", {}, timeout, skip_lock)
        if not response:
            return self._clean_areas
        data = response.get("data", response)
        areas: list[Any] = []
        if isinstance(data, list):
            areas = data
        elif isinstance(data, dict):
            for key in ("areas", "list", "clean_areas", "clean_area"):
                value = data.get(key)
                if isinstance(value, list):
                    areas = value
                    break
        self._clean_areas = areas
        return areas

    async def get_motor_temp(self, timeout: float = 5.0, skip_lock: bool = False) -> float | None:
        """Request motor temperature (°C)."""
        # ❓ No response while idle — may need active state
        response = await self._request_data_feedback("motor_temp_samp", {}, timeout, skip_lock)
        if not response:
            return self._motor_temp_c
        data = response.get("data", response)
        self._motor_temp_c = _extract_float(data)
        return self._motor_temp_c

    async def _await_data_feedback(self, topic: str, timeout: float) -> dict[str, Any] | None:
        """Await a data_feedback response for a command, if supported."""
        waiter = getattr(self.client, "wait_for_data_feedback", None)
        if callable(waiter):
            return await waiter(topic, timeout=timeout)
        waiter = getattr(self.client, "wait_for_feedback", None)
        if callable(waiter):
            return await waiter(topic, timeout=timeout)
        _LOGGER.debug("Client does not support data_feedback waits for %s", topic)
        return None

    async def _async_setup(self) -> None:
        """Start the telemetry listener task."""
        from homeassistant.helpers import issue_registry as ir

        # Clean up legacy telemetry_timeout issue from versions before the rename
        ir.async_delete_issue(self.hass, DOMAIN, f"telemetry_timeout_{self._entry.entry_id}")
        # Reset any stale mqtt_disconnect issue from before a restart so the
        # watchdog starts with a clean slate and re-raises if needed.
        async_delete_mqtt_disconnect_issue(self.hass, self._entry.entry_id)
        self._issue_active = False
        # Reset any stale controller_lost issue from before a restart
        async_delete_controller_lost_issue(self.hass, self._entry.entry_id)
        self._controller_lost_active = False

        if self._recorder_enabled_option and not self._recorder.enabled:
            try:
                await self._async_start_recorder()
            except Exception as err:
                _LOGGER.warning("Failed to start MQTT recorder (non-fatal): %s", err)

        if self._telemetry_task is None:
            self._telemetry_task = asyncio.create_task(self._telemetry_loop())
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(self._heartbeat_watchdog())
        if self._diagnostic_task is None:
            self._diagnostic_task = asyncio.create_task(self._diagnostic_polling_loop())

    def _apply_debug_logging(self, enabled: bool) -> None:
        """Toggle debug logging for all yarbo components."""
        logger_names = (
            "custom_components.yarbo",
            "yarbo",
            "yarbo.client",
            "yarbo.local",
            "yarbo.mqtt",
            "yarbo.cloud",
        )
        if enabled:
            for name in logger_names:
                logger = logging.getLogger(name)
                if name not in self._original_log_levels:
                    self._original_log_levels[name] = logger.level
                logger.setLevel(logging.DEBUG)
            _LOGGER.info("Yarbo debug logging ENABLED")
        else:
            for name in logger_names:
                logger = logging.getLogger(name)
                original_level = self._original_log_levels.get(name, logging.INFO)
                logger.setLevel(original_level)
            _LOGGER.info("Yarbo debug logging DISABLED")

    @property
    def recorder(self) -> MqttRecorder:
        """Return the MQTT recorder instance."""
        return self._recorder

    async def _telemetry_loop(self) -> None:
        """Listen to python-yarbo telemetry stream and push updates.

        Runs continuously until cancelled.
        Retries automatically after TELEMETRY_RETRY_DELAY_SECONDS on connection error.
        """
        while True:
            try:
                async for telemetry in self.client.watch_telemetry():
                    now = time.monotonic()
                    self._last_seen = now
                    if now - self._last_update < self._throttle_interval:
                        continue
                    # Record raw telemetry for diagnostics
                    if self._recorder.enabled:
                        try:
                            await self.hass.async_add_executor_job(
                                self._recorder.record_rx,
                                "telemetry",
                                telemetry.raw if hasattr(telemetry, "raw") else str(telemetry),
                            )
                        except Exception as rec_err:
                            _LOGGER.debug("MQTT recorder error (non-fatal): %s", rec_err)
                    self._last_update = now
                    self._update_count += 1
                    self.async_set_updated_data(telemetry)
                    if self._issue_active:
                        async_delete_mqtt_disconnect_issue(self.hass, self._entry.entry_id)
                        self._issue_active = False
            except asyncio.CancelledError:
                _LOGGER.debug("Telemetry loop cancelled")
                raise
            except YarboConnectionError as err:
                self.last_update_success = False
                port = self._entry.data.get(CONF_BROKER_PORT) or DEFAULT_BROKER_PORT
                # Ordered list from discovery: Primary, Secondary, … (like DNS)
                endpoints = self._entry.data.get(CONF_BROKER_ENDPOINTS)
                if not endpoints and self._entry.data.get(CONF_ALTERNATE_BROKER_HOST):
                    endpoints = [
                        self._entry.data[CONF_BROKER_HOST],
                        self._entry.data[CONF_ALTERNATE_BROKER_HOST],
                    ]
                if not endpoints:
                    endpoints = [self._entry.data.get(CONF_BROKER_HOST)]
                endpoints = [h for h in endpoints if h]

                current_host = self._entry.data.get(CONF_BROKER_HOST)
                try:
                    idx = endpoints.index(current_host)
                except (ValueError, TypeError):
                    # Not found — start from index -1 so next_idx wraps to 0 (Primary)
                    idx = -1
                next_idx = (idx + 1) % len(endpoints) if len(endpoints) > 1 else idx
                next_host = endpoints[next_idx] if endpoints else None

                if next_host and next_host != current_host and len(endpoints) > 1:
                    _LOGGER.warning(
                        "Yarbo connection error: %s — failing over to %s",
                        err,
                        next_host,
                    )
                    try:
                        new_client = YarboLocalClient(broker=next_host, port=port)
                        # Acquire command_lock to prevent commands in-flight during swap
                        async with self.command_lock:
                            await new_client.connect()
                            old_client = self.client
                            self.client = new_client
                            # Disconnect old client immediately after swap to prevent leaks
                            with contextlib.suppress(Exception):
                                await old_client.disconnect()
                            entry_data = self.hass.data.get(DOMAIN, {})
                            if self._entry.entry_id in entry_data:
                                entry_data[self._entry.entry_id][DATA_CLIENT] = new_client
                            # Persist current host so next failover uses it
                            new_data = dict(self._entry.data)
                            new_data[CONF_BROKER_HOST] = next_host
                            # Update connection path based on actual endpoint metadata
                            rover_ip = self._entry.data.get(CONF_ROVER_IP)
                            if rover_ip:
                                if next_host == rover_ip:
                                    new_data[CONF_CONNECTION_PATH] = ENDPOINT_TYPE_ROVER
                                else:
                                    new_data[CONF_CONNECTION_PATH] = ENDPOINT_TYPE_DC
                            # If rover_ip unknown, leave connection path unchanged
                            self.hass.config_entries.async_update_entry(self._entry, data=new_data)
                        # Re-acquire controller on failover (matches async_setup_entry)
                        try:
                            await new_client.get_controller(timeout=5.0)
                        except Exception as ctrl_err:
                            _LOGGER.warning("Failover controller acquisition failed: %s", ctrl_err)
                        _LOGGER.info("Failover to %s succeeded", next_host)
                        await asyncio.sleep(TELEMETRY_RETRY_DELAY_SECONDS)
                        continue
                    except Exception as connect_err:
                        _LOGGER.warning(
                            "Failover to %s failed: %s — retrying current in %ds",
                            next_host,
                            connect_err,
                            TELEMETRY_RETRY_DELAY_SECONDS,
                        )
                else:
                    _LOGGER.warning(
                        "Yarbo telemetry connection error: %s — retrying in %ds",
                        err,
                        TELEMETRY_RETRY_DELAY_SECONDS,
                    )
                await asyncio.sleep(TELEMETRY_RETRY_DELAY_SECONDS)
                try:
                    await self.client.disconnect()
                    await self.client.connect()
                except Exception as connect_err:
                    _LOGGER.warning("Failed to reconnect: %s", connect_err)
            except Exception:
                _LOGGER.exception(
                    "Unexpected error in telemetry loop — retrying in %ds",
                    TELEMETRY_RETRY_DELAY_SECONDS,
                )
                self.last_update_success = False
                await asyncio.sleep(TELEMETRY_RETRY_DELAY_SECONDS)

    async def _heartbeat_watchdog(self) -> None:
        """Watch for telemetry silence and raise a repair issue.

        If no telemetry is received for HEARTBEAT_TIMEOUT_SECONDS, creates a
        mqtt_disconnect repair issue. Auto-resolves when telemetry resumes.
        """
        try:
            while True:
                await asyncio.sleep(5)
                if not self._last_seen:
                    continue
                if time.monotonic() - self._last_seen < HEARTBEAT_TIMEOUT_SECONDS:
                    continue
                if self._issue_active:
                    continue
                name: str = self._entry.data.get(CONF_ROBOT_NAME, "Yarbo")
                async_create_mqtt_disconnect_issue(self.hass, self._entry.entry_id, name)
                self._issue_active = True
        except asyncio.CancelledError:
            _LOGGER.debug("Heartbeat watchdog cancelled")
            raise

    async def _async_update_data(self) -> YarboTelemetry:
        """Fallback status fetch for initial data load.

        In normal operation, core telemetry arrives via _telemetry_loop() using
        async_set_updated_data(). This method only runs once at startup to provide
        initial data before the push stream is established.
        """
        try:
            return await self.client.get_status(timeout=5.0)
        except YarboConnectionError as err:
            raise UpdateFailed(f"Cannot connect to Yarbo: {err}") from err

    async def _diagnostic_polling_loop(self) -> None:
        """Periodically poll diagnostic data without overwriting push-stream telemetry.

        Runs every 300 seconds to fetch non-streaming data like wifi, battery temps,
        odometer, etc. Does not modify self.data, only updates internal state.
        """
        while True:
            try:
                await asyncio.sleep(300)
                async with self._diagnostic_lock:
                    diagnostic_methods = [
                        self.get_wifi_name,
                        self.get_battery_cell_temps,
                        self.get_odometer,
                        self.get_no_charge_period,
                        self.get_schedules,
                        self.get_body_current,
                        self.get_head_current,
                        self.get_speed,
                        self.get_product_code,
                        self.get_hub_info,
                        self.get_recharge_point,
                        self.get_wifi_list,
                        self.get_map_backups,
                        self.get_clean_areas,
                        self.get_motor_temp,
                    ]
                    for method in diagnostic_methods:
                        try:
                            await method(timeout=1.0, skip_lock=True)
                        except Exception as err:
                            _LOGGER.debug("Diagnostic request failed (non-fatal): %s", err)
                    self.async_update_listeners()
            except asyncio.CancelledError:
                _LOGGER.debug("Diagnostic polling loop cancelled")
                raise
            except Exception:
                _LOGGER.exception("Unexpected error in diagnostic polling loop — retrying in 300s")
                await asyncio.sleep(300)

    async def async_config_entry_first_refresh(self) -> None:
        """Start push telemetry before the first refresh."""
        await self._async_setup()
        await super().async_config_entry_first_refresh()

    async def async_shutdown(self) -> None:
        """Shut down background tasks."""
        if self._telemetry_task:
            self._telemetry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._telemetry_task
            self._telemetry_task = None
        if self._watchdog_task:
            self._watchdog_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watchdog_task
            self._watchdog_task = None
        if self._diagnostic_task:
            self._diagnostic_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._diagnostic_task
            self._diagnostic_task = None
        if self._recorder.enabled:
            await self._async_stop_recorder()
        if self._debug_logging:
            self._apply_debug_logging(False)
        await super().async_shutdown()

    async def _async_start_recorder(self) -> None:
        """Start MQTT recording in the executor."""
        await self.hass.async_add_executor_job(self._recorder.start)

    async def _async_stop_recorder(self) -> None:
        """Stop MQTT recording in the executor."""
        await self.hass.async_add_executor_job(self._recorder.stop)
