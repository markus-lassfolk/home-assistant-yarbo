"""Sensor platform for Yarbo integration."""

from __future__ import annotations

from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DEFAULT_ACTIVITY_PERSONALITY,
    DOMAIN,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_LAWN_MOWER_PRO,
    HEAD_TYPE_LEAF_BLOWER,
    HEAD_TYPE_NONE,
    HEAD_TYPE_SMART_COVER,
    HEAD_TYPE_SNOW_BLOWER,
    HEAD_TYPE_TRIMMER,
    OPT_ACTIVITY_PERSONALITY,
    VERBOSE_ACTIVITY_DESCRIPTIONS,
    get_activity_state,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity

# Internal activity state values (snake_case enum values)
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

RTK_STATUS_OPTIONS: Final = [
    "invalid",
    "gps",
    "dgps",
    "rtk_float",
    "rtk_fixed",
    "unknown",
]

RTK_STATUS_MAP: Final = {
    0: "invalid",
    1: "gps",
    2: "dgps",
    4: "rtk_fixed",
    5: "rtk_float",
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
            YarboErrorCodeSensor(coordinator),
            YarboRtkStatusSensor(coordinator),
            YarboHeadingSensor(coordinator),
            YarboChuteAngleSensor(coordinator),
            YarboRainSensor(coordinator),
        ]
    )


class YarboSensor(YarboEntity, SensorEntity):
    """Base sensor for Yarbo."""

    def __init__(self, coordinator: YarboDataCoordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)


class YarboBatterySensor(YarboSensor):
    """Battery capacity sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery")

    @property
    def native_value(self) -> int | None:
        """Return the battery percentage."""
        if not self.telemetry:
            return None
        return self.telemetry.battery_capacity


class YarboActivitySensor(YarboSensor):
    """Activity state sensor with optional personality mode."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ACTIVITY_OPTIONS
    _attr_translation_key = "activity"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "activity")

    @property
    def native_value(self) -> str | None:
        """Return the current activity state."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        return get_activity_state(telemetry)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return personality description when enabled."""
        if not self.coordinator._entry.options.get(
            OPT_ACTIVITY_PERSONALITY, DEFAULT_ACTIVITY_PERSONALITY
        ):
            return None
        state = self.native_value
        if state is None:
            return None
        return {"description": VERBOSE_ACTIVITY_DESCRIPTIONS.get(state, state)}


class YarboHeadTypeSensor(YarboSensor):
    """Installed head type sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = HEAD_TYPE_OPTIONS
    _attr_translation_key = "head_type"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "head_type")

    @property
    def native_value(self) -> str | None:
        """Return the head type string."""
        if not self.telemetry:
            return None
        return HEAD_TYPE_MAP.get(self.telemetry.head_type, "none")


class YarboErrorCodeSensor(YarboSensor):
    """Diagnostic sensor for raw error codes."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "error_code"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "error_code")

    @property
    def native_value(self) -> int | None:
        """Return the raw error code."""
        if not self.telemetry:
            return None
        return self.telemetry.error_code


class YarboRtkStatusSensor(YarboSensor):
    """RTK fix quality sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = RTK_STATUS_OPTIONS
    _attr_translation_key = "rtk_status"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "rtk_status")

    @property
    def native_value(self) -> str | None:
        """Return RTK fix quality."""
        if not self.telemetry:
            return None
        status = getattr(self.telemetry, "rtk_status", None)
        if status is None:
            return None
        return RTK_STATUS_MAP.get(status, "unknown")


class YarboHeadingSensor(YarboSensor):
    """Compass heading sensor."""

    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "heading"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "heading")

    @property
    def native_value(self) -> float | None:
        """Return compass heading in degrees."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "heading", None)


class YarboChuteAngleSensor(YarboSensor):
    """Snow chute angle sensor — available for snow blower head only."""

    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "chute_angle"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "chute_angle")

    @property
    def available(self) -> bool:
        """Only available when snow blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_SNOW_BLOWER

    @property
    def native_value(self) -> int | None:
        """Return chute angle."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "chute_angle", None)


class YarboRainSensor(YarboSensor):
    """Rain sensor reading."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "rain_sensor"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "rain_sensor")

    @property
    def native_value(self) -> int | None:
        """Return rain sensor reading (0=dry, >0=wet)."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "rain_sensor", None)
