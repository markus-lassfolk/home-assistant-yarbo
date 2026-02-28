"""Tests for the Yarbo number platform (#13)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.entity import EntityCategory

from custom_components.yarbo.const import (
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_LAWN_MOWER_PRO,
    HEAD_TYPE_LEAF_BLOWER,
    HEAD_TYPE_SNOW_BLOWER,
)
from custom_components.yarbo.number import (
    YarboBatteryChargeMaxNumber,
    YarboBatteryChargeMinNumber,
    YarboBladeHeightNumber,
    YarboBladeSpeedNumber,
    YarboBlowerSpeedNumber,
    YarboChuteSteeringWorkNumber,
    YarboChuteVelocityNumber,
    YarboPlanStartPercentNumber,
    YarboRollerSpeedNumber,
    YarboVolumeNumber,
)


def _make_coordinator(head_type: int = HEAD_TYPE_SNOW_BLOWER) -> MagicMock:
    """Build a minimal mock coordinator for number tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.set_chute = AsyncMock()
    coord.client.publish_command = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0003",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.plan_start_percent = 0
    coord.set_plan_start_percent = MagicMock()
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
        """Available when head_type is snow blower (1)."""
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


class TestYarboChuteSteeringWorkNumber:
    """Tests for chute steering during work."""

    def test_translation_key(self) -> None:
        """Translation key must be chute_steering_work."""
        coord = _make_coordinator()
        entity = YarboChuteSteeringWorkNumber(coord)
        assert entity.translation_key == "chute_steering_work"

    def test_icon(self) -> None:
        """Icon must be mdi:rotate-3d-variant."""
        coord = _make_coordinator()
        entity = YarboChuteSteeringWorkNumber(coord)
        assert entity.icon == "mdi:rotate-3d-variant"

    def test_range(self) -> None:
        """Range must be -90 to 90 with step 5."""
        coord = _make_coordinator()
        entity = YarboChuteSteeringWorkNumber(coord)
        assert entity.native_min_value == -90.0
        assert entity.native_max_value == 90.0
        assert entity.native_step == 5.0

    def test_available_snow_blower(self) -> None:
        """Available when head_type is snow blower."""
        coord = _make_coordinator(head_type=HEAD_TYPE_SNOW_BLOWER)
        coord.last_update_success = True
        entity = YarboChuteSteeringWorkNumber(coord)
        assert entity.available is True

    def test_unavailable_other_head(self) -> None:
        """Unavailable when not snow blower head."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        coord.last_update_success = True
        entity = YarboChuteSteeringWorkNumber(coord)
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_set_angle_publishes_command(self) -> None:
        """Setting angle publishes cmd_chute_streeing_work."""
        coord = _make_coordinator()
        entity = YarboChuteSteeringWorkNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(25.0)

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with(
            "cmd_chute_streeing_work",
            {"angle": 25},
        )
        assert entity.native_value == 25.0


class TestYarboBladeHeightNumber:
    """Tests for blade height control."""

    def test_entity_category(self) -> None:
        """Blade height is a config entity."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboBladeHeightNumber(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    def test_available_lawn_mower(self) -> None:
        """Available for lawn mower heads."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER_PRO)
        entity = YarboBladeHeightNumber(coord)
        coord.last_update_success = True
        assert entity.available is True

    def test_unavailable_other_head(self) -> None:
        """Unavailable for non-lawn-mower heads."""
        coord = _make_coordinator(head_type=HEAD_TYPE_SNOW_BLOWER)
        entity = YarboBladeHeightNumber(coord)
        coord.last_update_success = True
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_set_height_publishes_command(self) -> None:
        """Setting blade height sends set_blade_height."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboBladeHeightNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(55.0)

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_blade_height", {"height": 55})
        assert entity.native_value == 55.0


class TestYarboBladeSpeedNumber:
    """Tests for blade speed control."""

    @pytest.mark.asyncio
    async def test_set_speed_publishes_command(self) -> None:
        """Setting blade speed sends set_blade_speed."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboBladeSpeedNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(3200.0)

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_blade_speed", {"speed": 3200})
        assert entity.native_value == 3200.0


class TestYarboBlowerSpeedNumber:
    """Tests for leaf blower speed control."""

    def test_available_leaf_blower(self) -> None:
        """Available for leaf blower head."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LEAF_BLOWER)
        entity = YarboBlowerSpeedNumber(coord)
        coord.last_update_success = True
        assert entity.available is True

    @pytest.mark.asyncio
    async def test_set_speed_publishes_command(self) -> None:
        """Setting blower speed sends blower_speed command."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LEAF_BLOWER)
        entity = YarboBlowerSpeedNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(7.0)

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("blower_speed", {"speed": 7})
        assert entity.native_value == 7.0


class TestYarboVolumeNumber:
    """Tests for volume control."""

    @pytest.mark.asyncio
    async def test_set_volume_publishes_command(self) -> None:
        """Setting volume sends set_sound_param."""
        coord = _make_coordinator()
        entity = YarboVolumeNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(42.0)

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_sound_param", {"vol": 42})
        assert entity.native_value == 42.0


class TestYarboPlanStartPercentNumber:
    """Tests for plan start percentage helper."""

    def _make_entry(self) -> MagicMock:
        entry = MagicMock()
        entry.options = {}
        return entry

    def test_reads_initial_value_from_coordinator(self) -> None:
        """Initial value comes from coordinator.plan_start_percent."""
        coord = _make_coordinator()
        coord.plan_start_percent = 30
        entry = self._make_entry()
        entity = YarboPlanStartPercentNumber(coord, entry)
        assert entity.native_value == 30.0

    @pytest.mark.asyncio
    async def test_set_percent_updates_coordinator(self) -> None:
        """Setting plan start percent updates coordinator state."""
        coord = _make_coordinator()
        entry = self._make_entry()
        entity = YarboPlanStartPercentNumber(coord, entry)
        entity.hass = MagicMock()
        entity.hass.config_entries = MagicMock()
        entity.hass.config_entries.async_update_entry = MagicMock()

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(25.0)

        coord.set_plan_start_percent.assert_called_once_with(25)

    @pytest.mark.asyncio
    async def test_set_percent_persists_to_entry_options(self) -> None:
        """Setting percent also persists to config entry options via hass (#16)."""
        coord = _make_coordinator()
        entry = self._make_entry()
        entity = YarboPlanStartPercentNumber(coord, entry)
        # Give entity a mock hass
        entity.hass = MagicMock()
        entity.hass.config_entries = MagicMock()
        entity.hass.config_entries.async_update_entry = MagicMock()

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(50.0)

        entity.hass.config_entries.async_update_entry.assert_called_once_with(
            entry,
            options={"plan_start_percent": 50},
        )


class TestYarboRollerSpeedNumber:
    """Tests for roller speed number entity (bug #4 — replaces roller switch)."""

    def test_icon(self) -> None:
        """Roller speed uses mdi:saw-blade icon."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSpeedNumber(coord)
        assert entity.icon == "mdi:saw-blade"

    def test_translation_key(self) -> None:
        """Translation key must be roller_speed."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSpeedNumber(coord)
        assert entity.translation_key == "roller_speed"

    def test_range_0_to_3500(self) -> None:
        """Range must be 0 to 3500 RPM."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSpeedNumber(coord)
        assert entity.native_min_value == 0.0
        assert entity.native_max_value == 3500.0

    def test_available_lawn_mower(self) -> None:
        """Available for lawn mower heads."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER_PRO)
        coord.last_update_success = True
        entity = YarboRollerSpeedNumber(coord)
        assert entity.available is True

    def test_unavailable_snow_blower(self) -> None:
        """Unavailable for non-mower heads."""
        coord = _make_coordinator(head_type=HEAD_TYPE_SNOW_BLOWER)
        coord.last_update_success = True
        entity = YarboRollerSpeedNumber(coord)
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_set_speed_publishes_command(self) -> None:
        """Setting speed publishes cmd_roller with speed key (not state)."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSpeedNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(2800.0)

        coord.client.publish_command.assert_called_once_with("cmd_roller", {"speed": 2800})
        assert entity.native_value == 2800.0

    @pytest.mark.asyncio
    async def test_set_zero_stops_roller(self) -> None:
        """Setting speed to 0 stops the roller."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSpeedNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(0.0)

        coord.client.publish_command.assert_called_once_with("cmd_roller", {"speed": 0})
        assert entity.native_value == 0.0


class TestYarboBatteryChargeMinNumber:
    """Tests for battery charge minimum limit (#93)."""

    def test_icon(self) -> None:
        """Battery charge min uses mdi:battery-charging icon."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMinNumber(coord)
        assert entity.icon == "mdi:battery-charging"

    def test_disabled_by_default(self) -> None:
        """Battery charge min must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMinNumber(coord)
        assert entity.entity_registry_enabled_default is False

    def test_range_0_to_100_step_5(self) -> None:
        """Range must be 0-100 with step 5."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMinNumber(coord)
        assert entity.native_min_value == 0.0
        assert entity.native_max_value == 100.0
        assert entity.native_step == 5.0

    @pytest.mark.asyncio
    async def test_set_min_publishes_command(self) -> None:
        """Setting min publishes set_charge_limit with min key."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMinNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(20.0)

        coord.client.publish_command.assert_called_once_with("set_charge_limit", {"min": 20})
        assert entity.native_value == 20.0


class TestYarboBatteryChargeMaxNumber:
    """Tests for battery charge maximum limit (#93)."""

    def test_icon(self) -> None:
        """Battery charge max uses mdi:battery-charging icon."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMaxNumber(coord)
        assert entity.icon == "mdi:battery-charging"

    def test_initial_value_100(self) -> None:
        """Initial value is 100%."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMaxNumber(coord)
        assert entity.native_value == 100.0

    @pytest.mark.asyncio
    async def test_set_max_publishes_command(self) -> None:
        """Setting max publishes set_charge_limit with max key."""
        coord = _make_coordinator()
        entity = YarboBatteryChargeMaxNumber(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_set_native_value(80.0)

        coord.client.publish_command.assert_called_once_with("set_charge_limit", {"max": 80})
        assert entity.native_value == 80.0
