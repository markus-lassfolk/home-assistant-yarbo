"""Sensor platform for Yarbo integration."""

from __future__ import annotations

from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_LAWN_MOWER_PRO,
    HEAD_TYPE_LEAF_BLOWER,
    HEAD_TYPE_NONE,
    HEAD_TYPE_SNOW_BLOWER,
    HEAD_TYPE_SMART_COVER,
    HEAD_TYPE_TRIMMER,
)
from .entity import YarboEntity

ACTIVITY_CHARGING: Final = "charging"
ACTIVITY_IDLE: Final = "idle"
ACTIVITY_WORKING: Final = "working"
ACTIVITY_PAUSED: Final = "paused"
ACTIVITY_RETURNING: Final = "returning"
ACTIVITY_ERROR: Final = "error"

ACTIVITY_OPTIONS: Final = [
    ACTIVITY_CHARGING,
    ACTIVITY_IDLE,
    ACTIVITY_WORKING,
    ACTIVITY_PAUSED,
    ACTIVITY_RETURNING,
    ACTIVITY_ERROR,
]

HEAD_TYPE_OPTIONS: Final = [
    "snow_blower",
    "lawn_mower",
    "lawn_mower_pro",
    "leaf_blower",
    "smart_cover",
    "trimmer",
    "none",
]

HEAD_TYPE_MAP: Final = {
    HEAD_TYPE_SNOW_BLOWER: "snow_blower",
    HEAD_TYPE_LAWN_MOWER: "lawn_mower",
    HEAD_TYPE_LAWN_MOWER_PRO: "lawn_mower_pro",
    HEAD_TYPE_LEAF_BLOWER: "leaf_blower",
    HEAD_TYPE_SMART_COVER: "smart_cover",
    HEAD_TYPE_TRIMMER: "trimmer",
    HEAD_TYPE_NONE: "none",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboBatterySensor(coordinator),
            YarboActivitySensor(coordinator),
            YarboHeadTypeSensor(coordinator),
        ]
    )


class YarboSensor(YarboEntity, SensorEntity):
    """Base sensor for Yarbo."""

    def __init__(self, coordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)


class YarboBatterySensor(YarboSensor):
    """Battery capacity sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "battery")

    @property
    def native_value(self) -> int | None:
        """Return the battery percentage."""
        if not self.telemetry:
            return None
        return self.telemetry.battery_capacity


class YarboActivitySensor(YarboSensor):
    """Activity state sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ACTIVITY_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "activity")

    @property
    def native_value(self) -> str | None:
        """Return the current activity state."""
        telemetry = self.telemetry
        if not telemetry:
            return None

        if telemetry.error_code != 0:
            return ACTIVITY_ERROR
        if telemetry.charging_status in (1, 2, 3):
            return ACTIVITY_CHARGING

        state = telemetry.state
        if state in (1, 7, 8):
            return ACTIVITY_WORKING
        if state == 2:
            return ACTIVITY_RETURNING
        if state == 5:
            return ACTIVITY_PAUSED
        if state == 6:
            return ACTIVITY_ERROR

        return ACTIVITY_IDLE


class YarboHeadTypeSensor(YarboSensor):
    """Installed head type sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = HEAD_TYPE_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "head_type")

    @property
    def native_value(self) -> str | None:
        """Return the head type string."""
        if not self.telemetry:
            return None
        return HEAD_TYPE_MAP.get(self.telemetry.head_type, "none")

