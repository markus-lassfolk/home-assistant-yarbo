"""Push-based DataUpdateCoordinator for Yarbo telemetry."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from yarbo import YarboLocalClient, YarboTelemetry
from yarbo.exceptions import YarboConnectionError

from .const import (
    CONF_ALTERNATE_BROKER_HOST,
    CONF_BROKER_ENDPOINTS,
    CONF_BROKER_HOST,
    CONF_BROKER_PORT,
    CONF_CONNECTION_PATH,
    CONF_ROBOT_NAME,
    DATA_CLIENT,
    DEFAULT_BROKER_PORT,
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    HEARTBEAT_TIMEOUT_SECONDS,
    OPT_TELEMETRY_THROTTLE,
    TELEMETRY_RETRY_DELAY_SECONDS,
)
from .repairs import (
    async_create_controller_lost_issue,
    async_create_mqtt_disconnect_issue,
    async_delete_controller_lost_issue,
    async_delete_mqtt_disconnect_issue,
)

_LOGGER = logging.getLogger(__name__)


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
                        new_client = YarboLocalClient(host=next_host, port=port)
                        # Acquire command_lock to prevent commands in-flight during swap
                        async with self.command_lock:
                            await new_client.connect()
                            old_client = self.client
                            self.client = new_client
                            entry_data = self.hass.data.get(DOMAIN, {})
                            if self._entry.entry_id in entry_data:
                                entry_data[self._entry.entry_id][DATA_CLIENT] = new_client
                            # Persist current host so next failover uses it
                            new_data = dict(self._entry.data)
                            new_data[CONF_BROKER_HOST] = next_host
                            # Update connection path: swap current label on failover
                            current_path = self._entry.data.get(CONF_CONNECTION_PATH, "")
                            if current_path == "dc":
                                new_data[CONF_CONNECTION_PATH] = "rover"
                            elif current_path == "rover":
                                new_data[CONF_CONNECTION_PATH] = "dc"
                            self.hass.config_entries.async_update_entry(self._entry, data=new_data)
                            # Disconnect old client; suppress errors to avoid leaking
                            with contextlib.suppress(Exception):
                                await old_client.disconnect()
                        # Re-acquire controller on failover (matches async_setup_entry)
                        try:
                            await new_client.get_controller(timeout=5.0)
                        except Exception as ctrl_err:
                            _LOGGER.warning("Failover controller acquisition failed: %s", ctrl_err)
                        _LOGGER.info("Failover to %s succeeded", next_host)
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
