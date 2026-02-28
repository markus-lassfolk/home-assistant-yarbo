"""Tests for the Yarbo button platform."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.entity import EntityCategory

from custom_components.yarbo.button import (
    YarboEmergencyUnlockButton,
    YarboManualStopButton,
    YarboPlaySoundButton,
    YarboRestartButton,
    YarboSaveChargingPointButton,
    YarboSaveMapBackupButton,
    YarboShutdownButton,
    YarboStartHotspotButton,
)
from custom_components.yarbo.const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL


def _make_coordinator() -> MagicMock:
    """Build a minimal mock coordinator for button tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.publish_command = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0007",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.data = None
    return coord


class TestYarboEmergencyUnlockButton:
    """Tests for emergency unlock button."""

    def test_translation_key(self) -> None:
        """Translation key must be emergency_unlock."""
        coord = _make_coordinator()
        entity = YarboEmergencyUnlockButton(coord)
        assert entity.translation_key == "emergency_unlock"

    def test_icon(self) -> None:
        """Icon must be mdi:lock-open-alert."""
        coord = _make_coordinator()
        entity = YarboEmergencyUnlockButton(coord)
        assert entity.icon == "mdi:lock-open-alert"

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends emergency_unlock command."""
        coord = _make_coordinator()
        entity = YarboEmergencyUnlockButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("emergency_unlock", {})


class TestYarboPlaySoundButton:
    """Tests for play sound button."""

    def test_translation_key(self) -> None:
        """Translation key must be play_sound."""
        coord = _make_coordinator()
        entity = YarboPlaySoundButton(coord)
        assert entity.translation_key == "play_sound"

    def test_icon(self) -> None:
        """Icon must be mdi:music-note."""
        coord = _make_coordinator()
        entity = YarboPlaySoundButton(coord)
        assert entity.icon == "mdi:music-note"

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends song_cmd command."""
        coord = _make_coordinator()
        entity = YarboPlaySoundButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with(
            "song_cmd",
            {"song_name": "default"},
        )


class TestYarboShutdownButton:
    """Tests for shutdown button."""

    def test_translation_key(self) -> None:
        """Translation key must be shutdown."""
        coord = _make_coordinator()
        entity = YarboShutdownButton(coord)
        assert entity.translation_key == "shutdown"

    def test_icon(self) -> None:
        """Icon must be mdi:power."""
        coord = _make_coordinator()
        entity = YarboShutdownButton(coord)
        assert entity.icon == "mdi:power"

    def test_entity_category(self) -> None:
        """Shutdown button is a config entity."""
        coord = _make_coordinator()
        entity = YarboShutdownButton(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends shutdown command."""
        coord = _make_coordinator()
        entity = YarboShutdownButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("shutdown", {})


class TestYarboRestartButton:
    """Tests for restart button."""

    def test_translation_key(self) -> None:
        """Translation key must be restart."""
        coord = _make_coordinator()
        entity = YarboRestartButton(coord)
        assert entity.translation_key == "restart"

    def test_icon(self) -> None:
        """Icon must be mdi:restart."""
        coord = _make_coordinator()
        entity = YarboRestartButton(coord)
        assert entity.icon == "mdi:restart"

    def test_entity_category(self) -> None:
        """Restart button is a config entity."""
        coord = _make_coordinator()
        entity = YarboRestartButton(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends restart_container command."""
        coord = _make_coordinator()
        entity = YarboRestartButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("restart_container", {})


class TestYarboManualStopButton:
    """Tests for manual stop button."""

    def test_translation_key(self) -> None:
        """Translation key must be manual_stop."""
        coord = _make_coordinator()
        entity = YarboManualStopButton(coord)
        assert entity.translation_key == "manual_stop"

    def test_icon(self) -> None:
        """Icon must be mdi:stop."""
        coord = _make_coordinator()
        entity = YarboManualStopButton(coord)
        assert entity.icon == "mdi:stop"

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends cmd_vel with zeros."""
        coord = _make_coordinator()
        entity = YarboManualStopButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("cmd_vel", {"vel": 0, "rev": 0})


class TestYarboSaveChargingPointButton:
    """Tests for save charging point button."""

    def test_disabled_by_default(self) -> None:
        """Save charging point button must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboSaveChargingPointButton(coord)
        assert entity.entity_registry_enabled_default is False

    def test_entity_category(self) -> None:
        """Save charging point is a config entity."""
        coord = _make_coordinator()
        entity = YarboSaveChargingPointButton(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends save_charging_point command."""
        coord = _make_coordinator()
        entity = YarboSaveChargingPointButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("save_charging_point", {})


class TestYarboStartHotspotButton:
    """Tests for start hotspot button."""

    def test_disabled_by_default(self) -> None:
        """Start hotspot button must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboStartHotspotButton(coord)
        assert entity.entity_registry_enabled_default is False

    def test_entity_category(self) -> None:
        """Start hotspot is a config entity."""
        coord = _make_coordinator()
        entity = YarboStartHotspotButton(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends start_hotspot command."""
        coord = _make_coordinator()
        entity = YarboStartHotspotButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("start_hotspot", {})


class TestYarboSaveMapBackupButton:
    """Tests for save map backup button."""

    def test_disabled_by_default(self) -> None:
        """Save map backup button must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboSaveMapBackupButton(coord)
        assert entity.entity_registry_enabled_default is False

    def test_entity_category(self) -> None:
        """Save map backup is a config entity."""
        coord = _make_coordinator()
        entity = YarboSaveMapBackupButton(coord)
        assert entity.entity_category == EntityCategory.CONFIG

    @pytest.mark.asyncio
    async def test_press_publishes_command(self) -> None:
        """Press sends save_map_backup command."""
        coord = _make_coordinator()
        entity = YarboSaveMapBackupButton(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_press()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("save_map_backup", {})
