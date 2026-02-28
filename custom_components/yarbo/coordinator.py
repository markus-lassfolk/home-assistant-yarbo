"""Push-based DataUpdateCoordinator for Yarbo telemetry."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
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
    CONF_ROVER_IP,
    DATA_CLIENT,
    DEFAULT_BROKER_PORT,
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    ENDPOINT_TYPE_DC,
    ENDPOINT_TYPE_ROVER,
    HEARTBEAT_TIMEOUT_SECONDS,
    OPT_TELEMETRY_THROTTLE,
    TELEMETRY_RETRY_DELAY_SECONDS,
    is_active_only_diagnostic_command,
    is_active_operation,
    normalize_command_name,
)
from .models import YarboTelemetry
from .repairs import (
    async_create_controller_lost_issue,
    async_create_mqtt_disconnect_issue,
    async_delete_controller_lost_issue,
    async_delete_mqtt_disconnect_issue,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PlanSummary:
    """Minimal work plan summary."""

    plan_id: str | int
    name: str
    area_ids: list[str | int]


class YarboDataCoordinator(DataUpdateCoordinator[YarboTelemetry]):
    """Push-based coordinator — no polling interval.

    Receives telemetry from the python-yarbo library via an async generator
    (client.watch_telemetry()) and pushes updates to all entities.

    The robot streams DeviceMSG at ~1-2 Hz. A configurable throttle (default 1.0s)
    debounces updates to avoid stressing the HA recorder and event bus.

    On connection error, the loop retries after TELEMETRY_RETRY_DELAY_SECONDS.

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

        No update_interval is set — this is a push-based coordinator.
        Updates are triggered by incoming MQTT messages.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # No update_interval — push-based
        )
        self.client = client
        self._entry = entry
        self._telemetry_task: asyncio.Task[None] | None = None
        self._watchdog_task: asyncio.Task[None] | None = None
        self._last_update: float = 0.0
        self._last_seen: float = 0.0
        self._issue_active = False
        self._controller_lost_active = False
        self._throttle_interval: float = entry.options.get(
            OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE
        )
        self._update_count: int = 0
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

    def update_options(self, options: dict[str, Any]) -> None:
        """Apply updated config entry options without requiring a full reload.

        Called by the options update listener in __init__.py when the user
        changes settings in the integration options UI.

        Currently applies:
        - telemetry_throttle: debounce interval for pushing updates to HA
        """
        self._throttle_interval = options.get(OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE)
        _LOGGER.debug("Yarbo options updated — throttle=%.1fs", self._throttle_interval)

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

    async def read_all_plans(self, timeout: float = 5.0) -> list[PlanSummary]:
        """Read all plan summaries from the robot."""
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
            await self.client.publish_command("start_plan", {"planId": plan_id})
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
            await self.client.publish_command("in_plan_action", {"action": action})

    async def _request_data_feedback(
        self,
        command: str,
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        """Publish a command and await matching data_feedback.

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
        async with self.command_lock:
            await self.client.publish_command(normalized_command, payload)
            response = await self._await_data_feedback(normalized_command, timeout)
        if not isinstance(response, dict):
            return {}
        return response

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

        if self._telemetry_task is None:
            self._telemetry_task = asyncio.create_task(self._telemetry_loop())
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(self._heartbeat_watchdog())

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
                            try:
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
                                self.hass.config_entries.async_update_entry(
                                    self._entry, data=new_data
                                )
                            finally:
                                # Always disconnect old client to avoid leak on mid-swap exception
                                with contextlib.suppress(Exception):
                                    await old_client.disconnect()
                        # Re-acquire controller on failover (matches async_setup_entry)
                        try:
                            await new_client.get_controller(timeout=5.0)
                        except Exception as ctrl_err:
                            _LOGGER.warning("Failover controller acquisition failed: %s", ctrl_err)
                        _LOGGER.info("Failover to %s succeeded", next_host)
                        await asyncio.sleep(2)
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
        """Fallback: fetch a single snapshot if push stream isn't running.

        This method is called by the coordinator framework if no data is available.
        In normal operation, data comes from _telemetry_loop() via async_set_updated_data().
        """
        try:
            return await self.client.get_status(timeout=5.0)
        except YarboConnectionError as err:
            raise UpdateFailed(f"Cannot connect to Yarbo: {err}") from err

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
        await super().async_shutdown()
