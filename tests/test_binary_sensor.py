"""Tests for the Yarbo binary sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.helpers.entity import EntityCategory

from custom_components.yarbo.binary_sensor import YarboNoChargePeriodSensor
from custom_components.yarbo.const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL


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
