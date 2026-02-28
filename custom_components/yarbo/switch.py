"""Switch platform for Yarbo integration — buzzer toggle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_LAWN_MOWER_PRO,
    HEAD_TYPE_LEAF_BLOWER,
    HEAD_TYPE_TRIMMER,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboBuzzerSwitch(coordinator),
            YarboPersonDetectSwitch(coordinator),
            YarboHeatingFilmSwitch(coordinator),
            YarboFollowModeSwitch(coordinator),
            YarboAutoUpdateSwitch(coordinator),
            YarboCameraOtaSwitch(coordinator),
            YarboTrimmerSwitch(coordinator),
            YarboCameraSwitch(coordinator),
            YarboLaserSwitch(coordinator),
            YarboUsbSwitch(coordinator),
            YarboIgnoreObstaclesSwitch(coordinator),
            YarboDrawModeSwitch(coordinator),
            YarboModuleLockSwitch(coordinator),
            YarboWireChargingLockSwitch(coordinator),
            # #94 — Smart/edge blowing (leaf blower only)
            YarboSmartBlowingSwitch(coordinator),
            YarboEdgeBlowingSwitch(coordinator),
            # #95 — Motor protect + mower head sensor
            YarboMotorProtectSwitch(coordinator),
            YarboMowerHeadSensorSwitch(coordinator),
            # #96 — Roof lights
            YarboRoofLightsSwitch(coordinator),
            # #97 — Sound enable
            YarboSoundEnableSwitch(coordinator),
        ]
    )


class YarboBuzzerSwitch(YarboEntity, SwitchEntity):
    """Buzzer toggle switch."""

    _attr_translation_key = "buzzer"
    _attr_assumed_state = True  # No read-back from robot
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "buzzer")
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if buzzer is active."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the buzzer."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.buzzer(state=1)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the buzzer."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.buzzer(state=0)
        self._is_on = False
        self.async_write_ha_state()


class YarboCommandSwitch(YarboEntity, SwitchEntity):
    """Base class for simple command-backed switches."""

    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: YarboDataCoordinator,
        entity_key: str,
        command: str,
        payload_key: str = "state",
        on_value: int | bool = 1,
        off_value: int | bool = 0,
    ) -> None:
        super().__init__(coordinator, entity_key)
        self._command = command
        self._payload_key = payload_key
        self._on_value = on_value
        self._off_value = off_value
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self._is_on

    async def _publish(self, value: int | bool) -> None:
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                self._command,
                {self._payload_key: value},
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self._publish(self._on_value)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self._publish(self._off_value)
        self._is_on = False
        self.async_write_ha_state()


class YarboPersonDetectSwitch(YarboCommandSwitch):
    """Person detection toggle switch."""

    _attr_translation_key = "person_detect"
    _attr_icon = "mdi:account-eye"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "person_detect", "set_person_detect", payload_key="enable")


class YarboHeatingFilmSwitch(YarboCommandSwitch):
    """Heating film toggle."""

    _attr_translation_key = "heating_film"
    _attr_icon = "mdi:radiator"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "heating_film", "heating_film_ctrl", payload_key="state")


class YarboFollowModeSwitch(YarboCommandSwitch):
    """Follow mode toggle."""

    _attr_translation_key = "follow_mode"
    _attr_icon = "mdi:walk"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "follow_mode", "set_follow_state", payload_key="state")


class YarboAutoUpdateSwitch(YarboCommandSwitch):
    """Auto update toggle."""

    _attr_translation_key = "auto_update"
    _attr_icon = "mdi:update"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "auto_update",
            "set_greengrass_auto_update_switch",
            payload_key="enable",
        )


class YarboCameraOtaSwitch(YarboCommandSwitch):
    """Camera OTA toggle."""

    _attr_translation_key = "camera_ota"
    _attr_icon = "mdi:camera-wireless"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "camera_ota",
            "set_ipcamera_ota_switch",
            payload_key="enable",
        )


class YarboTrimmerSwitch(YarboCommandSwitch):
    """Trimmer head toggle."""

    _attr_translation_key = "trimmer"
    _attr_icon = "mdi:content-cut"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "trimmer", "cmd_trimmer", payload_key="state")

    @property
    def available(self) -> bool:
        """Only available when trimmer head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_TRIMMER


class YarboCameraSwitch(YarboCommandSwitch):
    """Camera toggle — sends {"enabled": true/false} per docs."""

    _attr_translation_key = "camera"
    _attr_icon = "mdi:camera"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "camera",
            "camera_toggle",
            payload_key="enabled",
            on_value=True,
            off_value=False,
        )


class YarboLaserSwitch(YarboCommandSwitch):
    """Laser toggle — sends {"enabled": true/false} per docs."""

    _attr_translation_key = "laser"
    _attr_icon = "mdi:laser-pointer"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "laser",
            "laser_toggle",
            payload_key="enabled",
            on_value=True,
            off_value=False,
        )


class YarboUsbSwitch(YarboCommandSwitch):
    """USB power toggle — sends {"enabled": true/false} per docs."""

    _attr_translation_key = "usb"
    _attr_icon = "mdi:usb"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "usb",
            "usb_toggle",
            payload_key="enabled",
            on_value=True,
            off_value=False,
        )


class YarboIgnoreObstaclesSwitch(YarboCommandSwitch):
    """Obstacle detection bypass.

    Verified against live robot: "ignore_obstacles" with {"state": int} is correct.
    "obstacle_toggle" and "setIgnoreObstacle" are silently ignored.
    Command confirmed 2026-02-28.
    """

    _attr_translation_key = "ignore_obstacles"
    _attr_icon = "mdi:shield-off"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "ignore_obstacles",
            "ignore_obstacles",
            payload_key="state",
            on_value=1,
            off_value=0,
        )


class YarboDrawModeSwitch(YarboCommandSwitch):
    """Boundary drawing mode toggle."""

    _attr_translation_key = "draw_mode"
    _attr_icon = "mdi:draw"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "draw_mode", "start_draw_cmd", payload_key="state")


class YarboModuleLockSwitch(YarboCommandSwitch):
    """Module lock toggle."""

    _attr_translation_key = "module_lock"
    _attr_icon = "mdi:lock"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "module_lock", "module_lock_ctl", payload_key="state")


class YarboWireChargingLockSwitch(YarboCommandSwitch):
    """Wire charging lock toggle."""

    _attr_translation_key = "wire_charging_lock"
    _attr_icon = "mdi:ev-plug-type1"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "wire_charging_lock",
            "wire_charging_lock",
            payload_key="state",
        )


class YarboSmartBlowingSwitch(YarboCommandSwitch):
    """Smart blowing mode toggle — leaf blower head only (#94)."""

    _attr_translation_key = "smart_blowing"
    _attr_icon = "mdi:brain"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "smart_blowing", "smart_blowing", payload_key="state")

    @property
    def available(self) -> bool:
        """Only available when leaf blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_LEAF_BLOWER


class YarboEdgeBlowingSwitch(YarboCommandSwitch):
    """Edge blowing mode toggle — leaf blower head only (#94)."""

    _attr_translation_key = "edge_blowing"
    _attr_icon = "mdi:border-outside"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "edge_blowing", "edge_blowing", payload_key="state")

    @property
    def available(self) -> bool:
        """Only available when leaf blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_LEAF_BLOWER


class YarboMotorProtectSwitch(YarboCommandSwitch):
    """Motor protection toggle (#95)."""

    _attr_translation_key = "motor_protect"
    _attr_icon = "mdi:shield-check"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "motor_protect", "cmd_motor_protect", payload_key="state")


class YarboMowerHeadSensorSwitch(YarboCommandSwitch):
    """Mower head sensor toggle — lawn mower head only (#95)."""

    _attr_translation_key = "mower_head_sensor"
    _attr_icon = "mdi:motion-sensor"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(
            coordinator,
            "mower_head_sensor",
            "mower_head_sensor_switch",
            payload_key="state",
        )

    @property
    def available(self) -> bool:
        """Only available when lawn mower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in {HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO}


class YarboRoofLightsSwitch(YarboCommandSwitch):
    """Roof lights enable toggle (#96)."""

    _attr_translation_key = "roof_lights"
    _attr_icon = "mdi:car-light-dimmed"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "roof_lights", "roof_lights_enable", payload_key="enable")


class YarboSoundEnableSwitch(YarboCommandSwitch):
    """Sound enable toggle (#97)."""

    _attr_translation_key = "sound_enable"
    _attr_icon = "mdi:volume-off"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "sound_enable", "set_sound_param", payload_key="enable")
