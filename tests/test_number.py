"""Tests for the Yarbo number platform (#13)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yarbo.const import (
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_SNOW_BLOWER,
)
from custom_components.yarbo.number import YarboChuteVelocityNumber


def _make_coordinator(head_type: int = HEAD_TYPE_SNOW_BLOWER) -> MagicMock:
    """Build a minimal mock coordinator for number tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.set_chute = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0003",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    telemetry = MagicMock()
    telemetry.head_type = head_type
    coord.data = telemetry
    return coord


class TestYarboChuteVelocityNumber:
    """Tests for the chute velocity number entity (issue #13)."""

    def test_disabled_by_default(self) -> None:
        """Chute velocity number must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Chute velocity must use mdi:rotate-right icon."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)
        assert entity.icon == "mdi:rotate-right"

    def test_translation_key(self) -> None:
        """Translation key must be 'chute_velocity'."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)
        assert entity.translation_key == "chute_velocity"

    def test_unique_id(self) -> None:
        """Unique ID is based on robot serial."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)
        assert entity.unique_id == "TEST0003_chute_velocity"

    def test_range(self) -> None:
        """Range must be -2000 to 2000."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)
        assert entity.native_min_value == -2000.0
        assert entity.native_max_value == 2000.0

    def test_initial_value(self) -> None:
        """Initial velocity is 0."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)
        assert entity.native_value == 0.0

    def test_available_snow_blower(self) -> None:
        """Available when head_type is snow blower (0)."""
        coord = _make_coordinator(head_type=HEAD_TYPE_SNOW_BLOWER)
        entity = YarboChuteVelocityNumber(coord)
        # CoordinatorEntity.available checks coordinator.last_update_success
        coord.last_update_success = True
        assert entity.available is True

    def test_unavailable_lawn_mower(self) -> None:
        """Not available when head_type is lawn mower."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboChuteVelocityNumber(coord)
        coord.last_update_success = True
        assert entity.available is False

    def test_unavailable_no_telemetry(self) -> None:
        """Not available when telemetry is None."""
        coord = _make_coordinator()
        coord.data = None
        entity = YarboChuteVelocityNumber(coord)
        coord.last_update_success = True
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_set_value_calls_set_chute(self) -> None:
        """async_set_native_value calls client.set_chute with vel parameter."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(500.0)

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.set_chute.assert_called_once_with(vel=500)
        assert entity.native_value == 500.0

    @pytest.mark.asyncio
    async def test_set_negative_value(self) -> None:
        """Negative velocity (left) is passed correctly."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(-1000.0)

        coord.client.set_chute.assert_called_once_with(vel=-1000)
        assert entity.native_value == -1000.0

    @pytest.mark.asyncio
    async def test_set_zero_stops_chute(self) -> None:
        """Velocity 0 stops the chute."""
        coord = _make_coordinator()
        entity = YarboChuteVelocityNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(0.0)

        coord.client.set_chute.assert_called_once_with(vel=0)
        assert entity.native_value == 0.0
