"""Tests for the Yarbo device tracker platform (#106)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.const import STATE_HOME, STATE_NOT_HOME

from custom_components.yarbo.const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL
from custom_components.yarbo.device_tracker import YarboDeviceTracker


def _make_coordinator(**telemetry_kwargs: object) -> MagicMock:
    """Build a minimal mock coordinator for device tracker tests."""
    coord = MagicMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0106",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.last_update_success = True
    telemetry = MagicMock()
    telemetry.charging_status = 0
    telemetry.state = None
    for k, v in telemetry_kwargs.items():
        setattr(telemetry, k, v)
    telemetry.raw = {}
    coord.data = telemetry
    return coord


def _update(entity: YarboDeviceTracker) -> None:
    """Call _handle_coordinator_update with async_write_ha_state suppressed."""
    with patch.object(entity, "async_write_ha_state"):
        entity._handle_coordinator_update()


class TestYarboDeviceTracker:
    """Tests for device tracker home/not-home detection."""

    def test_charging_status_1_is_home(self) -> None:
        """charging_status=1 → home."""
        coord = _make_coordinator(charging_status=1)
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name == STATE_HOME

    def test_charging_status_2_is_home(self) -> None:
        """charging_status=2 → home."""
        coord = _make_coordinator(charging_status=2)
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name == STATE_HOME

    def test_charging_status_3_is_home(self) -> None:
        """charging_status=3 → home."""
        coord = _make_coordinator(charging_status=3)
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name == STATE_HOME

    def test_charging_status_0_not_home(self) -> None:
        """charging_status=0 with no work_status → not_home."""
        coord = _make_coordinator(charging_status=0, state=None)
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name == STATE_NOT_HOME

    def test_work_status_0_is_home(self) -> None:
        """state=0 (idle/standby) → home (#106)."""
        coord = _make_coordinator(charging_status=0, state=0)
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name == STATE_HOME

    def test_work_status_nonzero_not_home(self) -> None:
        """state=1 (active) → not_home when not charging."""
        coord = _make_coordinator(charging_status=0, state=1)
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name == STATE_NOT_HOME

    def test_no_telemetry_clears_location(self) -> None:
        """No telemetry → location_name is None."""
        coord = _make_coordinator()
        coord.data = None
        entity = YarboDeviceTracker(coord)
        _update(entity)
        assert entity._attr_location_name is None
