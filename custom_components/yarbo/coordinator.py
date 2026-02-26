"""Push-based DataUpdateCoordinator for Yarbo telemetry."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_TELEMETRY_THROTTLE,
    DOMAIN,
    OPT_TELEMETRY_THROTTLE,
)

_LOGGER = logging.getLogger(__name__)


class YarboDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Push-based coordinator — no polling interval.

    Receives telemetry from the python-yarbo library via an async generator
    (client.watch_telemetry()) and pushes updates to all entities.

    The robot streams DeviceMSG at ~1-2 Hz. A configurable throttle (default 1.0s)
    debounces updates to avoid stressing the HA recorder and event bus.

    TODO: Implement in v0.1.0
    - Start telemetry loop task in _async_setup()
    - Implement debounce logic
    - Handle MQTT disconnects (set last_update_success=False)
    - Implement heartbeat watchdog (repair issue after 60s silence)
    - Handle reconnection
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,  # TODO: Type as YarboClient from python-yarbo
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
        self._last_update: float = 0.0
        self._throttle_interval: float = entry.options.get(
            OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE
        )
        self._update_count: int = 0

    async def _async_setup(self) -> None:
        """Start the telemetry listener task.

        Called by async_config_entry_first_refresh().

        TODO: Implement in v0.1.0
        - Create telemetry loop task
        - Register cleanup on entry unload
        """
        # TODO: Start the telemetry loop
        # self._telemetry_task = asyncio.create_task(self._telemetry_loop())
        _LOGGER.debug("YarboDataCoordinator._async_setup() called (stub)")

    async def _telemetry_loop(self) -> None:
        """Listen to python-yarbo telemetry stream and push updates.

        Runs continuously until cancelled.

        TODO: Implement in v0.1.0
        - Iterate over client.watch_telemetry() async generator
        - Apply throttle debounce
        - Call async_set_updated_data() with each telemetry object
        - Handle YarboConnectionError → set last_update_success=False
        - Heartbeat watchdog: if no update in 60s, create repair issue
        """
        # TODO: Implement
        # async for telemetry in self.client.watch_telemetry():
        #     now = time.monotonic()
        #     if now - self._last_update < self._throttle_interval:
        #         continue
        #     self._last_update = now
        #     self._update_count += 1
        #     self.async_set_updated_data(telemetry)
        pass

    async def _async_update_data(self) -> dict[str, Any]:
        """Fallback: fetch a single snapshot if push stream isn't running.

        This method is called by the coordinator framework if no data is available.
        In normal operation, data comes from _telemetry_loop() via async_set_updated_data().

        TODO: Implement in v0.1.0
        """
        # TODO: Implement fallback
        # try:
        #     return await self.client.get_status(timeout=5.0)
        # except YarboConnectionError as err:
        #     raise UpdateFailed(f"Cannot connect to Yarbo: {err}") from err
        raise UpdateFailed("Yarbo coordinator not yet implemented")
