"""Performance-related tests for YarboDataCoordinator.

These tests help ensure the integration does not block the event loop,
hammer the robot with unbounded requests, or leak when under load.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from custom_components.community_yarbo.const import DOMAIN
from custom_components.community_yarbo.coordinator import YarboDataCoordinator
from custom_components.community_yarbo.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture
def coordinator_with_mock_listeners() -> Iterator[Any]:
    """Coordinator with _listeners populated (for listener_count diagnostics)."""
    with patch(
        "custom_components.community_yarbo.coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = object.__new__(YarboDataCoordinator)
        entry = MagicMock()
        entry.data = {"broker_host": "192.0.2.1", "robot_serial": "TEST123"}
        entry.entry_id = "test-entry-id"
        entry.options = {}
        coord._entry = entry  # type: ignore[attr-defined]
        coord.data = None
        coord._listeners = [MagicMock() for _ in range(45)]
        coord._update_count = 100
        coord._last_seen = None
        coord._last_telemetry_received_utc = None
        coord._throttle_interval = 1.0
        coord._poll_interval = 10
        coord.last_update_success = True
        coord.client = MagicMock()
        coord.client.is_connected = True
        coord.controller_acquired = False
        coord.client.controller_acquired = False
        coord.client._transport = None
        _rec = MagicMock()
        _rec.enabled = False
        _rec.recording_path = None
        _rec.list_recordings = MagicMock(return_value=[])
        coord._recorder = _rec  # type: ignore[attr-defined]
        yield coord


@pytest.mark.asyncio
async def test_diagnostics_includes_listener_count_and_poll_interval(
    coordinator_with_mock_listeners: Any,
) -> None:
    """Diagnostics should expose listener_count and poll_interval for performance debugging."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            coordinator_with_mock_listeners._entry.entry_id: {
                "coordinator": coordinator_with_mock_listeners,
                "client": coordinator_with_mock_listeners.client,
            }
        }
    }
    entry = coordinator_with_mock_listeners._entry

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert "coordinator" in diag
    assert diag["coordinator"].get("listener_count") == 45
    assert diag["coordinator"].get("poll_interval") == 10
    assert diag["coordinator"].get("throttle_interval") == 1.0
