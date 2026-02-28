"""Tests for the Yarbo switch platform (#12)."""

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
    HEAD_TYPE_TRIMMER,
)
from custom_components.yarbo.switch import (
    YarboAutoUpdateSwitch,
    YarboBuzzerSwitch,
    YarboCameraOtaSwitch,
    YarboCameraSwitch,
    YarboDrawModeSwitch,
    YarboFollowModeSwitch,
    YarboHeatingFilmSwitch,
    YarboIgnoreObstaclesSwitch,
    YarboLaserSwitch,
    YarboModuleLockSwitch,
    YarboPersonDetectSwitch,
    YarboRollerSwitch,
    YarboTrimmerSwitch,
    YarboUsbSwitch,
    YarboWireChargingLockSwitch,
)


def _make_coordinator(head_type: int | None = None) -> MagicMock:
    """Build a minimal mock coordinator for switch tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.buzzer = AsyncMock()
    coord.client.publish_command = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0002",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    if head_type is not None:
        telemetry = MagicMock()
        telemetry.head_type = head_type
        coord.data = telemetry
    else:
        coord.data = None
    return coord


class TestYarboBuzzerSwitch:
    """Tests for the buzzer switch entity (issue #12)."""

    def test_disabled_by_default(self) -> None:
        """Buzzer switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Buzzer switch must use mdi:volume-high icon."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.icon == "mdi:volume-high"

    def test_translation_key(self) -> None:
        """Translation key must be 'buzzer'."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.translation_key == "buzzer"

    def test_unique_id(self) -> None:
        """Unique ID is based on robot serial."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.unique_id == "TEST0002_buzzer"

    def test_assumed_state(self) -> None:
        """Buzzer switch uses assumed state (no read-back)."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.assumed_state is True

    def test_initial_state_off(self) -> None:
        """Buzzer is off initially."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_calls_buzzer_state_1(self) -> None:
        """turn_on calls client.buzzer(state=1)."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.buzzer.assert_called_once_with(state=1)
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_calls_buzzer_state_0(self) -> None:
        """turn_off calls client.buzzer(state=0)."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()
            await entity.async_turn_off()

        coord.client.buzzer.assert_called_with(state=0)
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_state_tracked_from_commands(self) -> None:
        """State is tracked from last command, not from telemetry."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            assert entity.is_on is False
            await entity.async_turn_on()
            assert entity.is_on is True
            await entity.async_turn_off()
            assert entity.is_on is False


class TestYarboPersonDetectSwitch:
    """Tests for the person detect switch."""

    def test_icon(self) -> None:
        """Person detect uses mdi:account-eye icon."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)
        assert entity.icon == "mdi:account-eye"

    def test_translation_key(self) -> None:
        """Translation key must be 'person_detect'."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)
        assert entity.translation_key == "person_detect"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_enable(self) -> None:
        """turn_on publishes set_person_detect enable=1."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_person_detect", {"enable": 1})
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_publishes_disable(self) -> None:
        """turn_off publishes set_person_detect enable=0."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()
            await entity.async_turn_off()

        coord.client.publish_command.assert_called_with("set_person_detect", {"enable": 0})
        assert entity.is_on is False


class TestYarboRollerSwitch:
    """Tests for roller switch."""

    def test_icon(self) -> None:
        """Roller uses mdi:saw-blade icon."""
        coord = _make_coordinator()
        entity = YarboRollerSwitch(coord)
        assert entity.icon == "mdi:saw-blade"

    def test_translation_key(self) -> None:
        """Translation key must be roller."""
        coord = _make_coordinator()
        entity = YarboRollerSwitch(coord)
        assert entity.translation_key == "roller"

    def test_available_lawn_mower(self) -> None:
        """Available for lawn mower heads."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER_PRO)
        coord.last_update_success = True
        entity = YarboRollerSwitch(coord)
        assert entity.available is True

    def test_unavailable_other_head(self) -> None:
        """Unavailable for non-lawn-mower heads."""
        coord = _make_coordinator(head_type=HEAD_TYPE_TRIMMER)
        coord.last_update_success = True
        entity = YarboRollerSwitch(coord)
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes cmd_roller state=1."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("cmd_roller", {"state": 1})
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_publishes_command(self) -> None:
        """turn_off publishes cmd_roller state=0."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        entity = YarboRollerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()
            await entity.async_turn_off()

        coord.client.publish_command.assert_called_with("cmd_roller", {"state": 0})
        assert entity.is_on is False


class TestYarboHeatingFilmSwitch:
    """Tests for heating film switch."""

    def test_entity_category(self) -> None:
        """Heating film is a config entity."""
        coord = _make_coordinator()
        entity = YarboHeatingFilmSwitch(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    def test_icon(self) -> None:
        """Heating film uses mdi:radiator icon."""
        coord = _make_coordinator()
        entity = YarboHeatingFilmSwitch(coord)
        assert entity.icon == "mdi:radiator"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes heating_film_ctrl state=1."""
        coord = _make_coordinator()
        entity = YarboHeatingFilmSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("heating_film_ctrl", {"state": 1})
        assert entity.is_on is True


class TestYarboFollowModeSwitch:
    """Tests for follow mode switch."""

    def test_icon(self) -> None:
        """Follow mode uses mdi:walk icon."""
        coord = _make_coordinator()
        entity = YarboFollowModeSwitch(coord)
        assert entity.icon == "mdi:walk"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes set_follow_state state=1."""
        coord = _make_coordinator()
        entity = YarboFollowModeSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_follow_state", {"state": 1})
        assert entity.is_on is True


class TestYarboAutoUpdateSwitch:
    """Tests for auto update switch."""

    def test_disabled_by_default(self) -> None:
        """Auto update switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboAutoUpdateSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_entity_category(self) -> None:
        """Auto update is a config entity."""
        coord = _make_coordinator()
        entity = YarboAutoUpdateSwitch(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    def test_icon(self) -> None:
        """Auto update uses mdi:update icon."""
        coord = _make_coordinator()
        entity = YarboAutoUpdateSwitch(coord)
        assert entity.icon == "mdi:update"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes set_greengrass_auto_update_switch enable=1."""
        coord = _make_coordinator()
        entity = YarboAutoUpdateSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with(
            "set_greengrass_auto_update_switch",
            {"enable": 1},
        )
        assert entity.is_on is True


class TestYarboCameraOtaSwitch:
    """Tests for camera OTA switch."""

    def test_disabled_by_default(self) -> None:
        """Camera OTA switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboCameraOtaSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Camera OTA uses mdi:camera-wireless icon."""
        coord = _make_coordinator()
        entity = YarboCameraOtaSwitch(coord)
        assert entity.icon == "mdi:camera-wireless"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes set_ipcamera_ota_switch enable=1."""
        coord = _make_coordinator()
        entity = YarboCameraOtaSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with(
            "set_ipcamera_ota_switch",
            {"enable": 1},
        )
        assert entity.is_on is True


class TestYarboTrimmerSwitch:
    """Tests for trimmer switch."""

    def test_available_trimmer(self) -> None:
        """Available for trimmer head."""
        coord = _make_coordinator(head_type=HEAD_TYPE_TRIMMER)
        coord.last_update_success = True
        entity = YarboTrimmerSwitch(coord)
        assert entity.available is True

    def test_unavailable_other_head(self) -> None:
        """Unavailable for non-trimmer head."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        coord.last_update_success = True
        entity = YarboTrimmerSwitch(coord)
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes cmd_trimmer state=1."""
        coord = _make_coordinator(head_type=HEAD_TYPE_TRIMMER)
        entity = YarboTrimmerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("cmd_trimmer", {"state": 1})
        assert entity.is_on is True


class TestYarboCameraSwitch:
    """Tests for camera switch."""

    def test_disabled_by_default(self) -> None:
        """Camera switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboCameraSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Camera uses mdi:camera icon."""
        coord = _make_coordinator()
        entity = YarboCameraSwitch(coord)
        assert entity.icon == "mdi:camera"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes camera_toggle state=1."""
        coord = _make_coordinator()
        entity = YarboCameraSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("camera_toggle", {"state": 1})
        assert entity.is_on is True


class TestYarboLaserSwitch:
    """Tests for laser switch."""

    def test_disabled_by_default(self) -> None:
        """Laser switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboLaserSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Laser uses mdi:laser-pointer icon."""
        coord = _make_coordinator()
        entity = YarboLaserSwitch(coord)
        assert entity.icon == "mdi:laser-pointer"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes laser_toggle state=1."""
        coord = _make_coordinator()
        entity = YarboLaserSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("laser_toggle", {"state": 1})
        assert entity.is_on is True


class TestYarboUsbSwitch:
    """Tests for USB switch."""

    def test_disabled_by_default(self) -> None:
        """USB switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboUsbSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """USB uses mdi:usb icon."""
        coord = _make_coordinator()
        entity = YarboUsbSwitch(coord)
        assert entity.icon == "mdi:usb"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes usb_toggle state=1."""
        coord = _make_coordinator()
        entity = YarboUsbSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("usb_toggle", {"state": 1})
        assert entity.is_on is True


class TestYarboIgnoreObstaclesSwitch:
    """Tests for ignore obstacles switch."""

    def test_disabled_by_default(self) -> None:
        """Ignore obstacles must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboIgnoreObstaclesSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Ignore obstacles uses mdi:shield-off icon."""
        coord = _make_coordinator()
        entity = YarboIgnoreObstaclesSwitch(coord)
        assert entity.icon == "mdi:shield-off"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes ignore_obstacles state=1."""
        coord = _make_coordinator()
        entity = YarboIgnoreObstaclesSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("ignore_obstacles", {"state": 1})
        assert entity.is_on is True


class TestYarboDrawModeSwitch:
    """Tests for draw mode switch."""

    def test_disabled_by_default(self) -> None:
        """Draw mode must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboDrawModeSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Draw mode uses mdi:draw icon."""
        coord = _make_coordinator()
        entity = YarboDrawModeSwitch(coord)
        assert entity.icon == "mdi:draw"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes start_draw_cmd state=1."""
        coord = _make_coordinator()
        entity = YarboDrawModeSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("start_draw_cmd", {"state": 1})
        assert entity.is_on is True


class TestYarboModuleLockSwitch:
    """Tests for module lock switch."""

    def test_disabled_by_default(self) -> None:
        """Module lock must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboModuleLockSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Module lock uses mdi:lock icon."""
        coord = _make_coordinator()
        entity = YarboModuleLockSwitch(coord)
        assert entity.icon == "mdi:lock"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes module_lock_ctl state=1."""
        coord = _make_coordinator()
        entity = YarboModuleLockSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("module_lock_ctl", {"state": 1})
        assert entity.is_on is True


class TestYarboWireChargingLockSwitch:
    """Tests for wire charging lock switch."""

    def test_disabled_by_default(self) -> None:
        """Wire charging lock must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboWireChargingLockSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Wire charging lock uses mdi:ev-plug-type1 icon."""
        coord = _make_coordinator()
        entity = YarboWireChargingLockSwitch(coord)
        assert entity.icon == "mdi:ev-plug-type1"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on publishes wire_charging_lock state=1."""
        coord = _make_coordinator()
        entity = YarboWireChargingLockSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("wire_charging_lock", {"state": 1})
        assert entity.is_on is True
