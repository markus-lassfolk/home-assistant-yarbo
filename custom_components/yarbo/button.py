"""Button platform for Yarbo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
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
        ]
    )


class YarboButton(YarboEntity, ButtonEntity):
    """Base button for Yarbo commands."""

    def __init__(self, coordinator: YarboDataCoordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)

    async def _send_command(self, command: str, payload: dict[str, Any]) -> None:
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(command, payload)


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
        await self._send_command("cmd_recharge", {})


class YarboPauseButton(YarboButton):
    """Pause the current plan."""

    _attr_translation_key = "pause"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "pause")

    async def async_press(self) -> None:
        await self._send_command("planning_paused", {})


class YarboResumeButton(YarboButton):
    """Resume a paused plan."""

    _attr_translation_key = "resume"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "resume")

    async def async_press(self) -> None:
        await self._send_command("resume", {})


class YarboStopButton(YarboButton):
    """Stop the robot gracefully."""

    _attr_translation_key = "stop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "stop")

    async def async_press(self) -> None:
        await self._send_command("dstop", {})


class YarboEmergencyStopButton(YarboButton):
    """Immediate emergency stop."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "emergency_stop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "emergency_stop")

    async def async_press(self) -> None:
        await self._send_command("emergency_stop_active", {})


class YarboEmergencyUnlockButton(YarboButton):
    """Emergency unlock button."""

    _attr_translation_key = "emergency_unlock"
    _attr_icon = "mdi:lock-open-alert"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "emergency_unlock")

    async def async_press(self) -> None:
        await self._send_command("emergency_unlock", {})


class YarboPlaySoundButton(YarboButton):
    """Play the default sound."""

    _attr_translation_key = "play_sound"
    _attr_icon = "mdi:music-note"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "play_sound")

    async def async_press(self) -> None:
        await self._send_command("song_cmd", {"song_name": "default"})
