"""Tests for Yarbo options flow and coordinator options handling (#26)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.community_yarbo.const import (
    DEFAULT_ACTIVITY_PERSONALITY,
    DEFAULT_AUTO_CONTROLLER,
    DEFAULT_CLOUD_ENABLED,
    DEFAULT_POLL_ACQUIRE_CONTROLLER,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TELEMETRY_THROTTLE,
    OPT_ACTIVITY_PERSONALITY,
    OPT_AUTO_CONTROLLER,
    OPT_CLOUD_ENABLED,
    OPT_POLL_ACQUIRE_CONTROLLER,
    OPT_POLL_INTERVAL,
    OPT_TELEMETRY_THROTTLE,
    POLL_INTERVAL_MAX,
    POLL_INTERVAL_MIN,
)
from custom_components.community_yarbo.coordinator import YarboDataCoordinator


def _make_coordinator(options: dict | None = None) -> YarboDataCoordinator:
    """Build a minimal coordinator for options tests."""
    with patch(
        "custom_components.community_yarbo.coordinator.DataUpdateCoordinator.__init__",
        return_value=None,
    ):
        coord = object.__new__(YarboDataCoordinator)
        entry = MagicMock()
        entry.options = options or {}
        coord._entry = entry  # type: ignore[attr-defined]
        coord._throttle_interval = entry.options.get(  # type: ignore[attr-defined]
            OPT_TELEMETRY_THROTTLE, DEFAULT_TELEMETRY_THROTTLE
        )
        coord._poll_interval = entry.options.get(  # type: ignore[attr-defined]
            OPT_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )
        coord._poll_acquire_controller = entry.options.get(  # type: ignore[attr-defined]
            OPT_POLL_ACQUIRE_CONTROLLER, DEFAULT_POLL_ACQUIRE_CONTROLLER
        )
        coord._debug_logging = False  # type: ignore[attr-defined]
        coord._recorder = MagicMock()  # type: ignore[attr-defined]
        coord._recorder_enabled_option = False  # type: ignore[attr-defined]
        coord.client = MagicMock()  # type: ignore[attr-defined]  # for update_options poll logic
        coord.hass = MagicMock()  # type: ignore[attr-defined]
        coord.hass.async_create_task = MagicMock(return_value=None)  # no-op for poll apply
    return coord  # type: ignore[return-value]


class TestCoordinatorDefaults:
    """Test that coordinator reads defaults from options correctly."""

    def test_default_throttle_is_1_second(self) -> None:
        coord = _make_coordinator()
        assert coord._throttle_interval == DEFAULT_TELEMETRY_THROTTLE

    def test_throttle_from_options(self) -> None:
        coord = _make_coordinator(options={OPT_TELEMETRY_THROTTLE: 5.0})
        assert coord._throttle_interval == 5.0

    def test_default_poll_interval(self) -> None:
        coord = _make_coordinator()
        assert coord._poll_interval == DEFAULT_POLL_INTERVAL

    def test_poll_interval_from_options(self) -> None:
        coord = _make_coordinator(options={OPT_POLL_INTERVAL: 30})
        assert coord._poll_interval == 30


class TestUpdateOptions:
    """Tests for YarboDataCoordinator.update_options()."""

    def test_update_throttle(self) -> None:
        coord = _make_coordinator()
        coord.update_options({OPT_TELEMETRY_THROTTLE: 3.0})
        assert coord._throttle_interval == 3.0

    def test_update_throttle_uses_default_when_missing(self) -> None:
        coord = _make_coordinator()
        coord._throttle_interval = 5.0  # start at non-default
        coord.update_options({})  # empty options → should reset to default
        assert coord._throttle_interval == DEFAULT_TELEMETRY_THROTTLE

    def test_update_poll_interval(self) -> None:
        coord = _make_coordinator()
        coord.update_options({OPT_POLL_INTERVAL: 60})
        assert coord._poll_interval == 60

    def test_default_poll_acquire_controller(self) -> None:
        coord = _make_coordinator()
        assert coord._poll_acquire_controller is DEFAULT_POLL_ACQUIRE_CONTROLLER

    def test_update_poll_acquire_controller(self) -> None:
        coord = _make_coordinator()
        coord.update_options({OPT_POLL_ACQUIRE_CONTROLLER: True})
        assert coord._poll_acquire_controller is True

    def test_update_multiple_times(self) -> None:
        coord = _make_coordinator()
        coord.update_options({OPT_TELEMETRY_THROTTLE: 2.0})
        coord.update_options({OPT_TELEMETRY_THROTTLE: 8.0})
        assert coord._throttle_interval == 8.0


class TestOptionsConstants:
    """Verify option key constants and defaults match spec."""

    def test_telemetry_throttle_default(self) -> None:
        assert DEFAULT_TELEMETRY_THROTTLE == 1.0

    def test_auto_controller_default(self) -> None:
        assert DEFAULT_AUTO_CONTROLLER is True

    def test_cloud_enabled_default(self) -> None:
        assert DEFAULT_CLOUD_ENABLED is False

    def test_activity_personality_default(self) -> None:
        assert DEFAULT_ACTIVITY_PERSONALITY is False

    def test_option_key_names(self) -> None:
        assert OPT_TELEMETRY_THROTTLE == "telemetry_throttle"
        assert OPT_POLL_INTERVAL == "poll_interval"
        assert OPT_AUTO_CONTROLLER == "auto_controller"
        assert OPT_CLOUD_ENABLED == "cloud_enabled"
        assert OPT_ACTIVITY_PERSONALITY == "activity_personality"

    def test_poll_interval_default_and_limits(self) -> None:
        assert DEFAULT_POLL_INTERVAL == 10
        assert POLL_INTERVAL_MIN == 1  # match python-yarbo POLLING_INTERVAL_MIN
        assert POLL_INTERVAL_MAX == 3600

    def test_poll_acquire_controller_default(self) -> None:
        assert DEFAULT_POLL_ACQUIRE_CONTROLLER is False


class TestOptionsFlowSchema:
    """Verify the options flow schema validates correctly.

    Note: config_flow.py imports homeassistant.components.dhcp which requires
    aiodhcpwatcher. We test the schema directly with voluptuous to avoid the
    transitive import issue in environments without that optional dependency.
    """

    def _build_schema(self) -> object:
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Optional(OPT_TELEMETRY_THROTTLE, default=DEFAULT_TELEMETRY_THROTTLE): vol.All(
                    vol.Coerce(float), vol.Range(min=1.0, max=10.0)
                ),
                vol.Optional(OPT_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=POLL_INTERVAL_MIN, max=POLL_INTERVAL_MAX)
                ),
                vol.Optional(
                    OPT_POLL_ACQUIRE_CONTROLLER, default=DEFAULT_POLL_ACQUIRE_CONTROLLER
                ): bool,
                vol.Optional(OPT_AUTO_CONTROLLER, default=DEFAULT_AUTO_CONTROLLER): bool,
                vol.Optional(OPT_CLOUD_ENABLED, default=DEFAULT_CLOUD_ENABLED): bool,
                vol.Optional(OPT_ACTIVITY_PERSONALITY, default=DEFAULT_ACTIVITY_PERSONALITY): bool,
            }
        )

    def test_options_flow_accepts_valid_throttle(self) -> None:
        schema = self._build_schema()
        result = schema(
            {
                OPT_TELEMETRY_THROTTLE: 2.5,
                OPT_POLL_INTERVAL: 15,
                OPT_POLL_ACQUIRE_CONTROLLER: True,
                OPT_AUTO_CONTROLLER: False,
                OPT_CLOUD_ENABLED: True,
                OPT_ACTIVITY_PERSONALITY: True,
            }
        )
        assert result[OPT_TELEMETRY_THROTTLE] == 2.5
        assert result[OPT_POLL_INTERVAL] == 15
        assert result[OPT_POLL_ACQUIRE_CONTROLLER] is True
        assert result[OPT_AUTO_CONTROLLER] is False
        assert result[OPT_CLOUD_ENABLED] is True
        assert result[OPT_ACTIVITY_PERSONALITY] is True

    def test_options_flow_rejects_poll_interval_below_min(self) -> None:
        import voluptuous as vol

        schema = vol.Schema(
            {
                vol.Optional(OPT_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=POLL_INTERVAL_MIN, max=POLL_INTERVAL_MAX)
                ),
            }
        )
        with pytest.raises(vol.Invalid):
            schema({OPT_POLL_INTERVAL: 0})  # min is 1 (match python-yarbo)

    def test_options_flow_rejects_poll_interval_above_max(self) -> None:
        import voluptuous as vol

        schema = vol.Schema(
            {
                vol.Optional(OPT_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=POLL_INTERVAL_MIN, max=POLL_INTERVAL_MAX)
                ),
            }
        )
        with pytest.raises(vol.Invalid):
            schema({OPT_POLL_INTERVAL: 4000})

    def test_options_flow_rejects_throttle_below_min(self) -> None:
        import voluptuous as vol

        schema = vol.Schema(
            {
                vol.Optional(OPT_TELEMETRY_THROTTLE, default=DEFAULT_TELEMETRY_THROTTLE): vol.All(
                    vol.Coerce(float), vol.Range(min=1.0, max=10.0)
                ),
            }
        )
        with pytest.raises(vol.Invalid):
            schema({OPT_TELEMETRY_THROTTLE: 0.5})

    def test_options_flow_rejects_throttle_above_max(self) -> None:
        import voluptuous as vol

        schema = vol.Schema(
            {
                vol.Optional(OPT_TELEMETRY_THROTTLE, default=DEFAULT_TELEMETRY_THROTTLE): vol.All(
                    vol.Coerce(float), vol.Range(min=1.0, max=10.0)
                ),
            }
        )
        with pytest.raises(vol.Invalid):
            schema({OPT_TELEMETRY_THROTTLE: 11.0})
