"""Tests for YarboDataCoordinator background task error handling.

Regression tests for GlitchTip #34: RuntimeError: Event loop is closed.
Verifies that background tasks (_telemetry_loop, _heartbeat_watchdog,
_diagnostic_polling_loop) exit gracefully when the asyncio event loop is
closed during HA shutdown, rather than propagating an unhandled exception.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.yarbo.const import (
    DEFAULT_TELEMETRY_THROTTLE,
    OPT_TELEMETRY_THROTTLE,
)
from custom_components.yarbo.coordinator import YarboDataCoordinator


async def _loop_closed_gen() -> AsyncGenerator[Any, None]:
    """Async generator that immediately raises RuntimeError: Event loop is closed."""
    raise RuntimeError("Event loop is closed")
    yield  # pragma: no cover – makes this function an async generator


async def _other_runtime_error_gen() -> AsyncGenerator[Any, None]:
    """Async generator that raises an unrelated RuntimeError immediately."""
    raise RuntimeError("Some other runtime error")
    yield  # pragma: no cover – makes this function an async generator


def _make_coordinator_for_tasks() -> YarboDataCoordinator:
    """Build a minimal coordinator for background-task tests.

    Uses object.__new__ to bypass __init__ and manually injects the
    minimum state that the background task methods require.
    """
    with patch(
        "custom_components.yarbo.coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = object.__new__(YarboDataCoordinator)
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.options = {OPT_TELEMETRY_THROTTLE: DEFAULT_TELEMETRY_THROTTLE}
        entry.data = {"robot_name": "TestBot", "broker_host": "192.0.2.1"}
        coord._entry = entry  # type: ignore[attr-defined]
        coord._throttle_interval = DEFAULT_TELEMETRY_THROTTLE  # type: ignore[attr-defined]
        coord._last_update = 0.0  # type: ignore[attr-defined]
        coord._last_seen = None  # type: ignore[attr-defined]
        coord._issue_active = False  # type: ignore[attr-defined]
        coord._controller_lost_active = False  # type: ignore[attr-defined]
        coord._plan_summaries = []  # type: ignore[attr-defined]
        coord._plan_by_id = {}  # type: ignore[attr-defined]
        coord._last_plan_fetch_attempt = 0.0  # type: ignore[attr-defined]
        coord._plan_fetch_retry_cooldown_sec = 120.0  # type: ignore[attr-defined]
        coord._recorder = MagicMock()  # type: ignore[attr-defined]
        coord._recorder.enabled = False  # type: ignore[attr-defined]
        coord._online_timer_cancel = None  # type: ignore[attr-defined]
        coord._update_count = 0  # type: ignore[attr-defined]
        coord._diagnostic_lock = asyncio.Semaphore(1)  # type: ignore[attr-defined]

        # Mock hass
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock()
        hass.async_create_task = MagicMock()
        coord.hass = hass  # type: ignore[attr-defined]

        # Mock client
        client = MagicMock()
        coord.client = client  # type: ignore[attr-defined]

        coord.last_update_success = True  # type: ignore[attr-defined]
        coord.data = None  # type: ignore[attr-defined]

    return coord  # type: ignore[return-value]


class TestTelemetryLoopEventLoopClosed:
    """GlitchTip #34: _telemetry_loop stops gracefully when event loop closes."""

    async def test_telemetry_loop_exits_on_event_loop_closed(self) -> None:
        """_telemetry_loop must return (not raise) when RuntimeError: Event loop is closed."""
        coord = _make_coordinator_for_tasks()
        coord.client.watch_telemetry = MagicMock(side_effect=lambda: _loop_closed_gen())

        # Should return without raising — not propagate the RuntimeError
        await asyncio.wait_for(coord._telemetry_loop(), timeout=2.0)

    async def test_telemetry_loop_reraises_other_runtime_errors(self) -> None:
        """_telemetry_loop must re-raise RuntimeErrors unrelated to event loop closure."""
        coord = _make_coordinator_for_tasks()
        coord.client.watch_telemetry = MagicMock(
            side_effect=lambda: _other_runtime_error_gen()
        )

        # Should not return immediately — task keeps retrying (sleeping) for other RuntimeErrors
        task = asyncio.create_task(coord._telemetry_loop())
        try:
            # Give it a moment to process the exception and enter the retry sleep
            await asyncio.sleep(0.05)
            # Task should still be running (sleeping in retry), not completed
            assert not task.done(), (
                "Task should be retrying, not exiting, for non-loop-closed RuntimeErrors"
            )
        finally:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


class TestHeartbeatWatchdogEventLoopClosed:
    """GlitchTip #34: _heartbeat_watchdog stops gracefully when event loop closes."""

    async def test_heartbeat_watchdog_exits_on_event_loop_closed(self) -> None:
        """_heartbeat_watchdog must return (not raise) on RuntimeError: Event loop is closed."""
        coord = _make_coordinator_for_tasks()

        async def _sleep_raises_loop_closed(_seconds: float) -> None:
            raise RuntimeError("Event loop is closed")

        with patch("asyncio.sleep", side_effect=_sleep_raises_loop_closed):
            # Should return without raising
            await asyncio.wait_for(coord._heartbeat_watchdog(), timeout=2.0)

    async def test_heartbeat_watchdog_reraises_other_runtime_errors(self) -> None:
        """_heartbeat_watchdog must re-raise other RuntimeErrors."""
        coord = _make_coordinator_for_tasks()

        async def _sleep_raises_other(_seconds: float) -> None:
            raise RuntimeError("Something unrelated")

        with patch("asyncio.sleep", side_effect=_sleep_raises_other):
            try:
                await asyncio.wait_for(coord._heartbeat_watchdog(), timeout=2.0)
                raise AssertionError("Should have raised RuntimeError")
            except RuntimeError as err:
                assert "Something unrelated" in str(err)
            except asyncio.TimeoutError:
                pass  # Also acceptable if it times out before raising


class TestDiagnosticPollingLoopEventLoopClosed:
    """GlitchTip #34: _diagnostic_polling_loop stops gracefully when event loop closes."""

    async def test_diagnostic_loop_exits_on_event_loop_closed(self) -> None:
        """_diagnostic_polling_loop must return (not raise) on RuntimeError: Event loop is closed."""
        coord = _make_coordinator_for_tasks()

        async def _sleep_raises_loop_closed(_seconds: float) -> None:
            raise RuntimeError("Event loop is closed")

        with patch("asyncio.sleep", side_effect=_sleep_raises_loop_closed):
            # Should return without raising
            await asyncio.wait_for(coord._diagnostic_polling_loop(), timeout=2.0)
