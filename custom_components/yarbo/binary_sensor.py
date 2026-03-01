"""Binary sensor platform for Yarbo integration."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, HEARTBEAT_TIMEOUT_SECONDS
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity
from .telemetry import get_nested_raw_value, get_value_from_paths


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboChargingSensor(coordinator),
            YarboProblemSensor(coordinator),
            YarboPlanningActiveSensor(coordinator),
            YarboReturningToChargeSensor(coordinator),
            YarboGoingToStartSensor(coordinator),
            YarboFollowModeSensor(coordinator),
            YarboPlanningPausedSensor(coordinator),
            YarboManualControllerSensor(coordinator),
            YarboRainDetectedSensor(coordinator),
            YarboNoChargePeriodSensor(coordinator),
            YarboOnlineBinarySensor(coordinator),
        ]
    )


class YarboBinarySensor(YarboEntity, BinarySensorEntity):
    """Base binary sensor for Yarbo."""

    def __init__(self, coordinator: YarboDataCoordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)


class YarboChargingSensor(YarboBinarySensor):
    """Charging status sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_translation_key = "charging"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "charging")

    @property
    def is_on(self) -> bool | None:
        """Return True when charging."""
        if not self.telemetry:
            return None
        return self.telemetry.charging_status in (1, 2, 3)


class YarboProblemSensor(YarboBinarySensor):
    """Problem indicator sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "problem"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "problem")

    @property
    def is_on(self) -> bool | None:
        """Return True when an error is present."""
        if not self.telemetry:
            return None
        return self.telemetry.error_code != 0


class YarboPlanningActiveSensor(YarboBinarySensor):
    """Planning active sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "planning_active"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "planning_active")

    @property
    def is_on(self) -> bool | None:
        """Return True when planning is active."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "on_going_planning", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "StateMSG", "on_going_planning")
        if value is None:
            return None
        return value != 0


class YarboReturningToChargeSensor(YarboBinarySensor):
    """Returning to charge sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "returning_to_charge"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "returning_to_charge")

    @property
    def is_on(self) -> bool | None:
        """Return True when returning to charge."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "on_going_recharging", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "StateMSG", "on_going_recharging")
        if value is None:
            return None
        return value != 0


class YarboGoingToStartSensor(YarboBinarySensor):
    """Going to start point sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "going_to_start"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "going_to_start")

    @property
    def is_on(self) -> bool | None:
        """Return True when going to start point."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "on_going_to_start_point", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "StateMSG", "on_going_to_start_point")
        if value is None:
            return None
        return value != 0


class YarboFollowModeSensor(YarboBinarySensor):
    """Follow mode sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "follow_mode"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "follow_mode")

    @property
    def is_on(self) -> bool | None:
        """Return True when robot follow mode is active."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "robot_follow_state", None)
        if value is None:
            value = get_value_from_paths(
                telemetry,
                [
                    ("StateMSG", "robot_follow_state"),
                    ("RunningStatusMSG", "robot_follow_state"),
                    ("robot_follow_state",),
                ],
            )
        if value is None:
            return None
        return value != 0


class YarboPlanningPausedSensor(YarboBinarySensor):
    """Planning paused sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "planning_paused"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "planning_paused")

    @property
    def is_on(self) -> bool | None:
        """Return True when planning is paused."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "planning_paused", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "StateMSG", "planning_paused")
        if value is None:
            return None
        return value != 0


class YarboManualControllerSensor(YarboBinarySensor):
    """Manual controller sensor."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "manual_controller"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "manual_controller")

    @property
    def is_on(self) -> bool | None:
        """Return True when manual controller is active."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "car_controller", None)
        if value is None:
            value = get_value_from_paths(
                telemetry,
                [
                    ("StateMSG", "car_controller"),
                    ("RunningStatusMSG", "car_controller"),
                    ("car_controller",),
                ],
            )
        if value is None:
            return None
        return value != 0


class YarboRainDetectedSensor(YarboBinarySensor):
    """Rain detected sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rain_detected"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "rain_detected")

    @property
    def is_on(self) -> bool | None:
        """Return True when rain is detected."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "rain_sensor", None)
        if value is None:
            value = get_value_from_paths(
                telemetry,
                [
                    ("RunningStatusMSG", "rain_sensor_data"),
                    ("rain_sensor_data",),
                    ("rain_sensor",),
                ],
            )
        if value is None:
            return None
        return value != 0


class YarboNoChargePeriodSensor(YarboBinarySensor):
    """No-charge period active sensor."""

    _attr_translation_key = "no_charge_period"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "no_charge_period")

    @property
    def is_on(self) -> bool | None:
        """Return True when a no-charge period is active."""
        return self.coordinator.no_charge_period_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return no-charge period details."""
        attrs: dict[str, Any] = {}
        if self.coordinator.no_charge_period_start:
            attrs["start_time"] = self.coordinator.no_charge_period_start
        if self.coordinator.no_charge_period_end:
            attrs["end_time"] = self.coordinator.no_charge_period_end
        periods = self.coordinator.no_charge_periods
        if periods:
            attrs["periods"] = periods
        return attrs


class YarboOnlineBinarySensor(YarboBinarySensor):
    """Binary sensor that is ON when the robot sent telemetry within HEARTBEAT_TIMEOUT_SECONDS."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "online"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "online")

    @property
    def is_on(self) -> bool:
        """Return True if last telemetry was received within HEARTBEAT_TIMEOUT_SECONDS."""
        last_seen = self.coordinator.last_seen
        if last_seen is None:
            return False
        return time.monotonic() - last_seen < HEARTBEAT_TIMEOUT_SECONDS
