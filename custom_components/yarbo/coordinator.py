"""Push-based DataUpdateCoordinator for Yarbo telemetry."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from yarbo import YarboTelemetry
from yarbo.exceptions import YarboConnectionError

from .const import (
    CONF_ROBOT_NAME,
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    HEARTBEAT_TIMEOUT_SECONDS,
    OPT_TELEMETRY_THROTTLE,
    TELEMETRY_RETRY_DELAY_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class YarboDataCoordinator(DataUpdateCoordinator[YarboTelemetry]):
    """Push-based coordinator — no polling interval.

    Receives telemetry from the python-yarbo library via an async generator
    (client.watch_telemetry()) and pushes updates to all entities.

    The robot streams DeviceMSG at ~1-2 Hz. A configurable throttle (default 1.0s)
    debounces updates to avoid stressing the HA recorder and event bus.

    On connection error, the loop retries after TELEMETRY_RETRY_DELAY_SECONDS.
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

    async def _async_setup(self) -> None:
        """Start the telemetry listener task."""
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
                        ir.async_delete_issue(
                            self.hass, DOMAIN, f"telemetry_timeout_{self._entry.entry_id}"
                        )
                        self._issue_active = False
            except asyncio.CancelledError:
                _LOGGER.debug("Telemetry loop cancelled")
                raise
            except YarboConnectionError as err:
                _LOGGER.warning(
                    "Yarbo telemetry connection error: %s — retrying in %ds",
                    err,
                    TELEMETRY_RETRY_DELAY_SECONDS,
                )
                self.last_update_success = False
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
        """Watch for telemetry silence and raise a repair issue."""
        try:
            while True:
                await asyncio.sleep(5)
                if not self._last_seen:
                    continue
                if time.monotonic() - self._last_seen < HEARTBEAT_TIMEOUT_SECONDS:
                    continue
                if self._issue_active:
                    continue
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"telemetry_timeout_{self._entry.entry_id}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="telemetry_timeout",
                    translation_placeholders={
                        "name": self._entry.data.get(CONF_ROBOT_NAME, "Yarbo"),
                    },
                )
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
