"""Button platform for Yarbo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    normalize_command_name,
    validate_head_type_for_command,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo buttons based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboBeepButton(coordinator),
            YarboReturnToDockButton(coordinator),
            YarboPauseButton(coordinator),
            YarboResumeButton(coordinator),
            YarboStopButton(coordinator),
            YarboEmergencyStopButton(coordinator),
            YarboEmergencyUnlockButton(coordinator),
            YarboPlaySoundButton(coordinator),
            YarboShutdownButton(coordinator),
            YarboRestartButton(coordinator),
            YarboManualStopButton(coordinator),
            YarboSaveChargingPointButton(coordinator),
            YarboStartHotspotButton(coordinator),
            YarboSaveMapBackupButton(coordinator),
            # #98 — Camera and firmware commands
            YarboCameraCalibrationButton(coordinator),
            YarboCheckCameraStatusButton(coordinator),
            YarboFirmwareUpdateNowButton(coordinator),
            YarboFirmwareUpdateTonightButton(coordinator),
            YarboFirmwareUpdateLaterButton(coordinator),
        ]
    )


class YarboButton(YarboEntity, ButtonEntity):
    """Base button for Yarbo commands."""

    def __init__(self, coordinator: YarboDataCoordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)

    async def _send_command(self, command: str, payload: dict[str, Any]) -> None:
        normalized_command = normalize_command_name(command)
        telemetry = self.telemetry
        current_head = telemetry.head_type if telemetry else None
        is_valid, error_message = validate_head_type_for_command(normalized_command, current_head)
        if not is_valid:
            raise HomeAssistantError(error_message)
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(normalized_command, payload)


class YarboBeepButton(YarboButton):
    """Beep the robot."""

    _attr_translation_key = "beep"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "beep")

    async def async_press(self) -> None:
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.buzzer(state=1)


class YarboReturnToDockButton(YarboButton):
    """Send the robot back to the dock."""

    _attr_translation_key = "return_to_dock"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "return_to_dock")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("cmd_recharge", {})


class YarboPauseButton(YarboButton):
    """Pause the current plan."""

    _attr_translation_key = "pause"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "pause")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("planning_paused", {})


class YarboResumeButton(YarboButton):
    """Resume a paused plan."""

    _attr_translation_key = "resume"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "resume")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("resume", {})


class YarboStopButton(YarboButton):
    """Stop the robot gracefully."""

    _attr_translation_key = "stop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "stop")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("dstop", {})


class YarboEmergencyStopButton(YarboButton):
    """Immediate emergency stop."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "emergency_stop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "emergency_stop")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("emergency_stop_active", {})


class YarboEmergencyUnlockButton(YarboButton):
    """Emergency unlock button."""

    _attr_translation_key = "emergency_unlock"
    _attr_icon = "mdi:lock-open-alert"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "emergency_unlock")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("emergency_unlock", {})


class YarboPlaySoundButton(YarboButton):
    """Play the default sound."""

    _attr_translation_key = "play_sound"
    _attr_icon = "mdi:music-note"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "play_sound")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("song_cmd", {"songId": 0})


class YarboShutdownButton(YarboButton):
    """Shutdown the robot."""

    _attr_translation_key = "shutdown"
    _attr_icon = "mdi:power"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "shutdown")

    async def async_press(self) -> None:
        # Verified live: "shutdown" correct. Powers off robot — physical restart required.
        await self._send_command("shutdown", {})


class YarboRestartButton(YarboButton):
    """Restart the robot container."""

    _attr_translation_key = "restart"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "restart")

    async def async_press(self) -> None:
        # ✅ Verified 2026-02-28: correct command, restarts EMQX container
        await self._send_command("restart_container", {})


class YarboManualStopButton(YarboButton):
    """Stop manual drive."""

    _attr_translation_key = "manual_stop"
    _attr_icon = "mdi:stop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "manual_stop")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("cmd_vel", {"vel": 0, "rev": 0})


class YarboSaveChargingPointButton(YarboButton):
    """Save current position as charging point."""

    _attr_translation_key = "save_charging_point"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "save_charging_point")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("save_charging_point", {})


class YarboStartHotspotButton(YarboButton):
    """Start WiFi hotspot on the robot."""

    _attr_translation_key = "start_hotspot"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "start_hotspot")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("start_hotspot", {})


class YarboSaveMapBackupButton(YarboButton):
    """Create a new map backup."""

    _attr_translation_key = "save_map_backup"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "save_map_backup")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("save_map_backup", {})


class YarboCameraCalibrationButton(YarboButton):
    """Calibrate the robot camera."""

    _attr_translation_key = "camera_calibration"
    _attr_icon = "mdi:camera-enhance"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "camera_calibration")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("camera_calibration", {})


class YarboCheckCameraStatusButton(YarboButton):
    """Request current camera status."""

    _attr_translation_key = "check_camera_status"
    _attr_icon = "mdi:camera-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "check_camera_status")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("check_camera_status", {})


class YarboFirmwareUpdateNowButton(YarboButton):
    """Trigger an immediate firmware update."""

    _attr_translation_key = "firmware_update_now"
    _attr_icon = "mdi:download-circle"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "firmware_update_now")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("firmware_update_now", {})


class YarboFirmwareUpdateTonightButton(YarboButton):
    """Schedule a firmware update for tonight."""

    _attr_translation_key = "firmware_update_tonight"
    _attr_icon = "mdi:download-circle-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "firmware_update_tonight")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("firmware_update_tonight", {})


class YarboFirmwareUpdateLaterButton(YarboButton):
    """Defer the pending firmware update."""

    _attr_translation_key = "firmware_update_later"
    _attr_icon = "mdi:update"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "firmware_update_later")

    async def async_press(self) -> None:
        # 🔇 Fire-and-forget: no data_feedback response
        await self._send_command("firmware_update_later", {})
