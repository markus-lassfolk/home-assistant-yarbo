"""Tests for the Yarbo binary sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.helpers.entity import EntityCategory

import time

from custom_components.yarbo.binary_sensor import YarboNoChargePeriodSensor, YarboOnlineBinarySensor
from custom_components.yarbo.const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL, HEARTBEAT_TIMEOUT_SECONDS


def _make_coordinator() -> MagicMock:
    """Build a minimal mock coordinator for binary sensor tests."""
    coord = MagicMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0010",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.no_charge_period_active = True
    coord.no_charge_period_start = "22:00"
    coord.no_charge_period_end = "06:00"
    coord.no_charge_periods = [{"start": "22:00", "end": "06:00"}]
    coord.data = None
    return coord


class TestYarboNoChargePeriodSensor:
    """Tests for no-charge period binary sensor."""

    def test_translation_key(self) -> None:
        """Translation key must be no_charge_period."""
        coord = _make_coordinator()
        entity = YarboNoChargePeriodSensor(coord)
        assert entity.translation_key == "no_charge_period"

    def test_entity_category(self) -> None:
        """No-charge period is a config entity."""
        coord = _make_coordinator()
        entity = YarboNoChargePeriodSensor(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    def test_disabled_by_default(self) -> None:
        """No-charge period is disabled by default."""
        coord = _make_coordinator()
        entity = YarboNoChargePeriodSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_is_on(self) -> None:
        """Returns coordinator no_charge_period_active."""
        coord = _make_coordinator()
        entity = YarboNoChargePeriodSensor(coord)
        assert entity.is_on is True

    def test_attributes(self) -> None:
        """Includes start/end time and periods."""
        coord = _make_coordinator()
        entity = YarboNoChargePeriodSensor(coord)
        assert entity.extra_state_attributes["start_time"] == "22:00"
        assert entity.extra_state_attributes["end_time"] == "06:00"
        assert entity.extra_state_attributes["periods"] == [{"start": "22:00", "end": "06:00"}]


class TestYarboOnlineBinarySensor:
    """Tests for the Online connectivity binary sensor."""

    def _make_online_coordinator(self, last_seen: float | None = None) -> MagicMock:
        """Build a minimal coordinator mock for online sensor tests."""
        coord = MagicMock()
        coord._entry = MagicMock()
        coord._entry.data = {
            CONF_ROBOT_SERIAL: "TEST0116",
            CONF_ROBOT_NAME: "TestBot",
        }
        coord._entry.options = {}
        coord.last_update_success = True
        coord.last_seen = last_seen
        coord.data = None
        return coord

    def test_true_when_recent(self) -> None:
        """Returns True when last telemetry was received recently."""
        coord = self._make_online_coordinator(last_seen=time.monotonic())
        entity = YarboOnlineBinarySensor(coord)
        assert entity.is_on is True

    def test_false_when_stale(self) -> None:
        """Returns False when last telemetry is older than HEARTBEAT_TIMEOUT_SECONDS."""
        stale_time = time.monotonic() - (HEARTBEAT_TIMEOUT_SECONDS + 10)
        coord = self._make_online_coordinator(last_seen=stale_time)
        entity = YarboOnlineBinarySensor(coord)
        assert entity.is_on is False

    def test_false_when_unset(self) -> None:
        """Returns False when no telemetry has been received (last_seen is None)."""
        coord = self._make_online_coordinator(last_seen=None)
        entity = YarboOnlineBinarySensor(coord)
        assert entity.is_on is False
