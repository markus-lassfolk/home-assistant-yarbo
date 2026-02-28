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
            YarboRollerSwitch(coordinator),
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
        on_value: int = 1,
        off_value: int = 0,
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

    async def _publish(self, value: int) -> None:
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


class YarboPersonDetectSwitch(YarboEntity, SwitchEntity):
    """Person detection toggle switch."""

    _attr_translation_key = "person_detect"
    _attr_assumed_state = True
    _attr_icon = "mdi:account-eye"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "person_detect")
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if person detection is enabled."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable person detection."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command("set_person_detect", {"enable": 1})
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable person detection."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command("set_person_detect", {"enable": 0})
        self._is_on = False
        self.async_write_ha_state()


class YarboRollerSwitch(YarboCommandSwitch):
    """Roller/blade toggle for lawn mower heads."""

    _attr_translation_key = "roller"
    _attr_icon = "mdi:saw-blade"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "roller", "cmd_roller", payload_key="state")

    @property
    def available(self) -> bool:
        """Only available when a lawn mower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in {HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO}


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
    """Camera toggle."""

    _attr_translation_key = "camera"
    _attr_icon = "mdi:camera"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "camera", "camera_toggle", payload_key="state")


class YarboLaserSwitch(YarboCommandSwitch):
    """Laser toggle."""

    _attr_translation_key = "laser"
    _attr_icon = "mdi:laser-pointer"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "laser", "laser_toggle", payload_key="state")


class YarboUsbSwitch(YarboCommandSwitch):
    """USB power toggle."""

    _attr_translation_key = "usb"
    _attr_icon = "mdi:usb"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "usb", "usb_toggle", payload_key="state")


class YarboIgnoreObstaclesSwitch(YarboCommandSwitch):
    """Obstacle detection bypass."""

    _attr_translation_key = "ignore_obstacles"
    _attr_icon = "mdi:shield-off"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "ignore_obstacles", "ignore_obstacles", payload_key="state")


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
