"""Sensor platform for Yarbo integration."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BROKER_HOST,
    CONF_CONNECTION_PATH,
    CONF_ROVER_IP,
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
from .telemetry import get_gngga_data, get_nested_raw_value, get_value_from_paths

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
            YarboConnectionSensor(coordinator),
            YarboBatterySensor(coordinator),
            YarboActivitySensor(coordinator),
            YarboHeadTypeSensor(coordinator),
            YarboErrorCodeSensor(coordinator),
            YarboHeadSerialSensor(coordinator),
            YarboBatteryTempErrorSensor(coordinator),
            YarboBaseStationStatusSensor(coordinator),
            YarboRtkStatusSensor(coordinator),
            YarboRtcmSourceTypeSensor(coordinator),
            YarboHeadingSensor(coordinator),
            YarboHeadingDopSensor(coordinator),
            YarboHeadingStatusSensor(coordinator),
            YarboAntennaDistanceSensor(coordinator),
            YarboChuteAngleSensor(coordinator),
            YarboChuteSteeringInfoSensor(coordinator),
            YarboRainSensor(coordinator),
            YarboSatelliteCountSensor(coordinator),
            YarboGpsFixQualitySensor(coordinator),
            YarboGpsHdopSensor(coordinator),
            YarboGpsAltitudeSensor(coordinator),
            YarboChargingPowerSensor(coordinator),
            YarboWirelessChargeStateSensor(coordinator),
            YarboWirelessChargeErrorSensor(coordinator),
            YarboOdomConfidenceSensor(coordinator),
            YarboOdomXSensor(coordinator),
            YarboOdomYSensor(coordinator),
            YarboOdomPhiSensor(coordinator),
            YarboRtcmAgeSensor(coordinator),
            YarboChargeVoltageSensor(coordinator),
            YarboChargeCurrentSensor(coordinator),
            YarboMqttAgeSensor(coordinator),
            YarboNavSensorFrontRight(coordinator),
            YarboNavSensorRearRight(coordinator),
            YarboHeadGyroPitchSensor(coordinator),
            YarboHeadGyroRollSensor(coordinator),
            YarboMachineControllerSensor(coordinator),
            YarboPlanRemainingTimeSensor(coordinator),
            YarboWifiNetworkSensor(coordinator),
            YarboBatteryCellTempMinSensor(coordinator),
            YarboBatteryCellTempMaxSensor(coordinator),
            YarboBatteryCellTempAvgSensor(coordinator),
            YarboOdometerSensor(coordinator),
            YarboRoutePriorityHg0Sensor(coordinator),
            YarboRoutePriorityWlan0Sensor(coordinator),
            YarboRoutePriorityWwan0Sensor(coordinator),
            YarboUltrasonicLeftFrontSensor(coordinator),
            YarboUltrasonicMiddleSensor(coordinator),
            YarboUltrasonicRightFrontSensor(coordinator),
            YarboScheduleCountSensor(coordinator),
            YarboBodyCurrentSensor(coordinator),
            YarboHeadCurrentSensor(coordinator),
            YarboSpeedSensor(coordinator),
            YarboProductCodeSensor(coordinator),
            YarboHubInfoSensor(coordinator),
            YarboRechargePointSensor(coordinator),
            YarboWifiListSensor(coordinator),
            YarboMapBackupCountSensor(coordinator),
            YarboCleanAreaCountSensor(coordinator),
            YarboMotorTempSensor(coordinator),
            YarboLastSeenSensor(coordinator),
            # #98 — Saved WiFi networks list
            YarboSavedWifiListSensor(coordinator),
        ]
    )


class YarboSensor(YarboEntity, SensorEntity):
    """Base sensor for Yarbo."""

    def __init__(self, coordinator: YarboDataCoordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)


class YarboConnectionSensor(YarboSensor):
    """Shows connection path (Data Center vs Rover) and Rover IP for device panel (issue #50)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connection"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "connection")

    @property
    def native_value(self) -> str:
        """Return connection path label with active IP, e.g. 'Data Center (<dc-ip>)'."""
        entry = self.coordinator.entry
        # Prefer the active client's host (reflects failover); fall back to entry data
        host = (
            getattr(self.coordinator.client, "host", None) or entry.data.get(CONF_BROKER_HOST) or ""
        )
        path = entry.data.get(CONF_CONNECTION_PATH) or ""
        if path == "dc":
            label = "Data Center"
        elif path == "rover":
            label = "Rover"
        else:
            label = "MQTT"
        return f"{label} ({host})" if host else label

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return rover_ip when known (other endpoint for info)."""
        entry = self.coordinator.entry
        rover_ip = entry.data.get(CONF_ROVER_IP)
        if not rover_ip:
            return {}
        return {"rover_ip": rover_ip}


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
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "error_code"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "error_code")

    @property
    def native_value(self) -> int | None:
        """Return the raw error code."""
        if not self.telemetry:
            return None
        return self.telemetry.error_code


class YarboHeadSerialSensor(YarboSensor):
    """Diagnostic sensor for head serial number."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "head_serial"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "head_serial")

    @property
    def native_value(self) -> str | None:
        """Return head serial number."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "head_serial", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "HeadSerialMsg", "head_sn")
        return value if value is not None else None


class YarboBatteryTempErrorSensor(YarboSensor):
    """Diagnostic sensor for battery temperature error."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "battery_temp_error"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery_temp_error")

    @property
    def native_value(self) -> int | None:
        """Return battery temperature error."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "battery_temp_error", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "BatteryMSG", "temp_err")
        return value if value is not None else None


class YarboBaseStationStatusSensor(YarboSensor):
    """Diagnostic sensor for base station status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "base_station_status"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "base_station_status")

    @property
    def native_value(self) -> int | str | None:
        """Return base station status."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "base_station_status", None)
        if value is None:
            value = get_value_from_paths(
                telemetry,
                [
                    ("base_status",),
                    ("BaseStatusMsg", "base_status"),
                ],
            )
        return value if value is not None else None


class YarboRtkStatusSensor(YarboSensor):
    """RTK fix quality sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = RTK_STATUS_OPTIONS
    _attr_entity_registry_enabled_default = False
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


class YarboRtcmSourceTypeSensor(YarboSensor):
    """Diagnostic sensor for RTCM source type."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rtcm_source_type"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "rtcm_source_type")

    @property
    def native_value(self) -> int | str | None:
        """Return RTCM source type."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "rtcm_source_type", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "rtcm_info", "current_source_type")
        return value if value is not None else None


class YarboHeadingSensor(YarboSensor):
    """Compass heading sensor."""

    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "heading"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "heading")

    @property
    def native_value(self) -> float | None:
        """Return compass heading in degrees."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "heading", None)


class YarboHeadingDopSensor(YarboSensor):
    """Diagnostic sensor for heading DOP."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "heading_dop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "heading_dop")

    @property
    def native_value(self) -> float | None:
        """Return heading DOP."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "heading_dop", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "RTKMSG", "heading_dop")
        return value if value is not None else None


class YarboHeadingStatusSensor(YarboSensor):
    """Diagnostic sensor for heading status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "heading_status"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "heading_status")

    @property
    def native_value(self) -> int | None:
        """Return heading status."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "heading_status", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "RTKMSG", "heading_status")
        return value if value is not None else None


class YarboAntennaDistanceSensor(YarboSensor):
    """Diagnostic sensor for antenna distance."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "m"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "antenna_distance"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "antenna_distance")

    @property
    def native_value(self) -> float | None:
        """Return antenna distance in meters."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "antenna_distance", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "RTKMSG", "gga_atn_dis")
        return value if value is not None else None


class YarboChuteAngleSensor(YarboSensor):
    """Snow chute angle sensor — available for snow blower head only."""

    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
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


class YarboChuteSteeringInfoSensor(YarboSensor):
    """Diagnostic sensor for chute steering info."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "chute_steering_info"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "chute_steering_info")

    @property
    def available(self) -> bool:
        """Only available when snow blower head (head_type==1) is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_SNOW_BLOWER

    @property
    def native_value(self) -> int | str | None:
        """Return chute steering info."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "chute_steering_info", None)
        if value is None:
            value = get_nested_raw_value(
                telemetry, "RunningStatusMSG", "chute_steering_engine_info"
            )
        return value if value is not None else None


class YarboRainSensor(YarboSensor):
    """Rain sensor reading."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rain_sensor"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "rain_sensor")

    @property
    def available(self) -> bool:
        """Only available when a head with rain sensor is installed (head_type in (3, 5))."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in (HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO)

    @property
    def native_value(self) -> int | None:
        """Return rain sensor reading (0=dry, >0=wet)."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "rain_sensor", None)


class YarboSatelliteCountSensor(YarboSensor):
    """GNSS satellite count sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "satellite_count"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "satellite_count")

    @property
    def native_value(self) -> int | None:
        """Return number of visible satellites."""
        if not self.telemetry:
            return None
        gngga = get_gngga_data(self.telemetry)
        if gngga is not None and gngga.satellite_count is not None:
            return gngga.satellite_count
        return getattr(self.telemetry, "satellite_count", None)


class YarboGpsFixQualitySensor(YarboSensor):
    """Diagnostic sensor for GPS fix quality."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "gps_fix_quality"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "gps_fix_quality")

    @property
    def native_value(self) -> int | None:
        """Return GPS fix quality."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        gngga = get_gngga_data(telemetry)
        if gngga is not None:
            return gngga.fix_quality
        return None


class YarboGpsHdopSensor(YarboSensor):
    """Diagnostic sensor for GPS HDOP."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "gps_hdop"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "gps_hdop")

    @property
    def native_value(self) -> float | None:
        """Return GPS HDOP."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        gngga = get_gngga_data(telemetry)
        if gngga is not None:
            return gngga.hdop
        return None


class YarboGpsAltitudeSensor(YarboSensor):
    """Diagnostic sensor for GPS altitude."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "m"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "gps_altitude"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "gps_altitude")

    @property
    def native_value(self) -> float | None:
        """Return GPS altitude in meters."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        gngga = get_gngga_data(telemetry)
        if gngga is not None:
            return gngga.altitude_m
        return None


class YarboChargingPowerSensor(YarboSensor):
    """Wireless charging power sensor (output_voltage_mV x output_current_mA / 1_000_000 = W)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "charging_power"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "charging_power")

    @property
    def native_value(self) -> float | None:
        """Return wireless charging power in watts."""
        if not self.telemetry:
            return None
        voltage_mv = getattr(self.telemetry, "charge_voltage_mv", None)
        current_ma = getattr(self.telemetry, "charge_current_ma", None)
        if voltage_mv is None or current_ma is None:
            return None
        return round(voltage_mv * current_ma / 1_000_000, 2)


class YarboWirelessChargeStateSensor(YarboSensor):
    """Diagnostic sensor for wireless charge state."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "wireless_charge_state"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "wireless_charge_state")

    @property
    def native_value(self) -> int | str | None:
        """Return wireless charge state."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "wireless_charge_state", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "wireless_recharge", "state")
        return value if value is not None else None


class YarboWirelessChargeErrorSensor(YarboSensor):
    """Diagnostic sensor for wireless charge error."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "wireless_charge_error"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "wireless_charge_error")

    @property
    def native_value(self) -> int | str | None:
        """Return wireless charge error code."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "wireless_charge_error", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "wireless_recharge", "error_code")
        return value if value is not None else None


class YarboOdomConfidenceSensor(YarboSensor):
    """Odometry confidence diagnostic sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "odom_confidence"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "odom_confidence")

    @property
    def native_value(self) -> float | None:
        """Return odometry confidence."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "odom_confidence", None)


class YarboOdomXSensor(YarboSensor):
    """Diagnostic sensor for odometry X."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "odom_x"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "odom_x")

    @property
    def native_value(self) -> float | None:
        """Return odometry X."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "odom_x", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "CombinedOdom", "x")
        return value if value is not None else None


class YarboOdomYSensor(YarboSensor):
    """Diagnostic sensor for odometry Y."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "odom_y"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "odom_y")

    @property
    def native_value(self) -> float | None:
        """Return odometry Y."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "odom_y", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "CombinedOdom", "y")
        return value if value is not None else None


class YarboOdomPhiSensor(YarboSensor):
    """Diagnostic sensor for odometry Phi."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "odom_phi"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "odom_phi")

    @property
    def native_value(self) -> float | None:
        """Return odometry Phi."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "odom_phi", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "CombinedOdom", "phi")
        return value if value is not None else None


class YarboRtcmAgeSensor(YarboSensor):
    """RTCM correction age diagnostic sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "s"
    # No state_class: value grows unbounded when base station is unavailable, which
    # breaks long-term statistics. state_class=None avoids polluting the statistics DB.
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rtcm_age"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "rtcm_age")

    @property
    def native_value(self) -> float | None:
        """Return RTCM correction data age in seconds."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "rtcm_age", None)


class YarboChargeVoltageSensor(YarboSensor):
    """Charging voltage diagnostic sensor."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # HA expects V for SensorDeviceClass.VOLTAGE to enable unit conversion
    _attr_native_unit_of_measurement = "V"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "charge_voltage"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "charge_voltage")

    @property
    def native_value(self) -> float | None:
        """Return charging voltage in volts (MQTT payload is mV)."""
        if not self.telemetry:
            return None
        mv = getattr(self.telemetry, "charge_voltage_mv", None)
        return round(mv / 1000, 3) if mv is not None else None


class YarboChargeCurrentSensor(YarboSensor):
    """Charging current diagnostic sensor."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # HA expects A for SensorDeviceClass.CURRENT to enable unit conversion
    _attr_native_unit_of_measurement = "A"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "charge_current"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "charge_current")

    @property
    def native_value(self) -> float | None:
        """Return charging current in amperes (MQTT payload is mA)."""
        if not self.telemetry:
            return None
        ma = getattr(self.telemetry, "charge_current_ma", None)
        return round(ma / 1000, 3) if ma is not None else None


class YarboMqttAgeSensor(YarboSensor):
    """MQTT message age diagnostic sensor — seconds since last telemetry."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "s"
    # No state_class: value grows unbounded when robot is offline, which breaks
    # long-term statistics. state_class=None avoids polluting the statistics DB.
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "mqtt_age"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "mqtt_age")

    @property
    def native_value(self) -> float | None:
        """Return seconds since last MQTT telemetry message."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "mqtt_age", None)


class YarboNavSensorFrontRight(YarboSensor):
    """Diagnostic sensor for front-right navigation sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "nav_sensor_front_right"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "nav_sensor_front_right")

    @property
    def native_value(self) -> int | None:
        """Return front-right navigation sensor value."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "nav_sensor_front_right", None)
        if value is None:
            value = get_nested_raw_value(
                telemetry, "RunningStatusMSG", "elec_navigation_front_right_sensor"
            )
        return value if value is not None else None


class YarboNavSensorRearRight(YarboSensor):
    """Diagnostic sensor for rear-right navigation sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "nav_sensor_rear_right"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "nav_sensor_rear_right")

    @property
    def native_value(self) -> int | None:
        """Return rear-right navigation sensor value."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "nav_sensor_rear_right", None)
        if value is None:
            value = get_nested_raw_value(
                telemetry, "RunningStatusMSG", "elec_navigation_rear_right_sensor"
            )
        return value if value is not None else None


class YarboHeadGyroPitchSensor(YarboSensor):
    """Diagnostic sensor for head gyro pitch."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "head_gyro_pitch"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "head_gyro_pitch")

    @property
    def native_value(self) -> float | None:
        """Return head gyro pitch in degrees."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "head_gyro_pitch", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "RunningStatusMSG", "head_gyro_pitch")
        return value if value is not None else None


class YarboHeadGyroRollSensor(YarboSensor):
    """Diagnostic sensor for head gyro roll."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "°"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "head_gyro_roll"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "head_gyro_roll")

    @property
    def native_value(self) -> float | None:
        """Return head gyro roll in degrees."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "head_gyro_roll", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "RunningStatusMSG", "head_gyro_roll")
        return value if value is not None else None


class YarboMachineControllerSensor(YarboSensor):
    """Diagnostic sensor for machine controller."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "machine_controller"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "machine_controller")

    @property
    def native_value(self) -> int | str | None:
        """Return machine controller value."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "machine_controller", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "StateMSG", "machine_controller")
        return value if value is not None else None


class YarboPlanRemainingTimeSensor(YarboSensor):
    """Remaining time for the last read plan."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "plan_remaining_time"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "plan_remaining_time")

    @property
    def native_value(self) -> int | None:
        """Return remaining plan time in seconds."""
        return self.coordinator.plan_remaining_time


class YarboWifiNetworkSensor(YarboSensor):
    """Diagnostic sensor for connected WiFi network.

    Note (#109): this sensor may only return data during active robot operation
    or when a cloud connection is available. Shows unavailable when idle.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "wifi_network"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "wifi_network")

    @property
    def native_value(self) -> str | None:
        """Return the last known WiFi network name."""
        return self.coordinator.wifi_name


class YarboBatteryCellTempMinSensor(YarboSensor):
    """Minimum battery cell temperature."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_cell_temp_min"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery_cell_temp_min")

    @property
    def native_value(self) -> float | None:
        """Return minimum cell temperature."""
        return self.coordinator.battery_cell_temp_min


class YarboBatteryCellTempMaxSensor(YarboSensor):
    """Maximum battery cell temperature."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_cell_temp_max"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery_cell_temp_max")

    @property
    def native_value(self) -> float | None:
        """Return maximum cell temperature."""
        return self.coordinator.battery_cell_temp_max


class YarboBatteryCellTempAvgSensor(YarboSensor):
    """Average battery cell temperature."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_cell_temp_avg"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery_cell_temp_avg")

    @property
    def native_value(self) -> float | None:
        """Return average cell temperature."""
        return self.coordinator.battery_cell_temp_avg


class YarboOdometerSensor(YarboSensor):
    """Total distance traveled."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_translation_key = "odometer"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "odometer")

    @property
    def native_value(self) -> float | None:
        """Return odometer distance in meters."""
        return self.coordinator.odometer_m


class YarboRoutePriorityHg0Sensor(YarboSensor):
    """Diagnostic sensor for route priority hg0."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "route_priority_hg0"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "route_priority_hg0")

    @property
    def native_value(self) -> int | None:
        """Return route priority for hg0."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        return get_nested_raw_value(telemetry, "route_priority", "hg0")


class YarboRoutePriorityWlan0Sensor(YarboSensor):
    """Diagnostic sensor for route priority wlan0."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "route_priority_wlan0"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "route_priority_wlan0")

    @property
    def native_value(self) -> int | None:
        """Return route priority for wlan0."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        return get_nested_raw_value(telemetry, "route_priority", "wlan0")


class YarboRoutePriorityWwan0Sensor(YarboSensor):
    """Diagnostic sensor for route priority wwan0."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "route_priority_wwan0"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "route_priority_wwan0")

    @property
    def native_value(self) -> int | None:
        """Return route priority for wwan0."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        return get_nested_raw_value(telemetry, "route_priority", "wwan0")


class YarboUltrasonicLeftFrontSensor(YarboSensor):
    """Ultrasonic left-front distance sensor."""

    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "ultrasonic_left_front"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "ultrasonic_left_front")

    @property
    def native_value(self) -> int | None:
        """Return left-front ultrasonic distance in mm."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "ultrasonic_left_front", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "ultrasonic_msg", "lf_dis")
        return value if value is not None else None


class YarboUltrasonicMiddleSensor(YarboSensor):
    """Ultrasonic middle distance sensor."""

    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "ultrasonic_middle"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "ultrasonic_middle")

    @property
    def native_value(self) -> int | None:
        """Return middle ultrasonic distance in mm."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "ultrasonic_middle", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "ultrasonic_msg", "mt_dis")
        return value if value is not None else None


class YarboUltrasonicRightFrontSensor(YarboSensor):
    """Ultrasonic right-front distance sensor."""

    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "ultrasonic_right_front"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "ultrasonic_right_front")

    @property
    def native_value(self) -> int | None:
        """Return right-front ultrasonic distance in mm."""
        telemetry = self.telemetry
        if not telemetry:
            return None
        value = getattr(telemetry, "ultrasonic_right_front", None)
        if value is None:
            value = get_nested_raw_value(telemetry, "ultrasonic_msg", "rf_dis")
        return value if value is not None else None


class YarboScheduleCountSensor(YarboSensor):
    """Number of saved schedules."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "schedule_count"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "schedule_count")

    @property
    def native_value(self) -> int | None:
        """Return number of schedules."""
        return len(self.coordinator.schedule_list)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedules list."""
        return {"schedules": self.coordinator.schedule_list}


class YarboBodyCurrentSensor(YarboSensor):
    """Body current sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "body_current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "body_current")

    @property
    def native_value(self) -> float | None:
        """Return body current in A."""
        return self.coordinator.body_current


class YarboHeadCurrentSensor(YarboSensor):
    """Head current sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "head_current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "head_current")

    @property
    def native_value(self) -> float | None:
        """Return head current in A."""
        return self.coordinator.head_current


class YarboSpeedSensor(YarboSensor):
    """Speed sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "speed"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.METERS_PER_SECOND
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def native_value(self) -> float | None:
        """Return speed in m/s."""
        return self.coordinator.speed_m_s


class YarboProductCodeSensor(YarboSensor):
    """Product code sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "product_code"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "product_code")

    @property
    def native_value(self) -> str | None:
        """Return product code."""
        return self.coordinator.product_code


class YarboHubInfoSensor(YarboSensor):
    """Hub info sensor.

    Note (#109): this sensor may only return data during active robot operation
    or when a cloud connection is available. Shows unavailable when idle.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "hub_info"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "hub_info")

    @property
    def native_value(self) -> str | None:
        """Return hub info."""
        return self.coordinator.hub_info


class YarboRechargePointSensor(YarboSensor):
    """Recharge point status sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "recharge_point"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "recharge_point")

    @property
    def native_value(self) -> str | None:
        """Return recharge point status."""
        return self.coordinator.recharge_point_status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recharge point details."""
        details = self.coordinator.recharge_point_details
        return {"details": details} if details else {}


class YarboWifiListSensor(YarboSensor):
    """Available WiFi list sensor.

    Note (#109): this sensor may only return data during active robot operation
    or when a cloud connection is available. Shows unavailable when idle.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "wifi_list"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "wifi_list")

    @property
    def native_value(self) -> str | None:
        """Return WiFi list summary."""
        wifi_list = self.coordinator.wifi_list
        if not wifi_list:
            return None
        return str(len(wifi_list))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return WiFi list details."""
        return {"wifi_list": self.coordinator.wifi_list}


class YarboMapBackupCountSensor(YarboSensor):
    """Number of map backups."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "map_backup_count"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "map_backup_count")

    @property
    def native_value(self) -> int | None:
        """Return number of map backups."""
        return len(self.coordinator.map_backups)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return map backups list."""
        return {"map_backups": self.coordinator.map_backups}


class YarboCleanAreaCountSensor(YarboSensor):
    """Number of clean areas."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "clean_area_count"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "clean_area_count")

    @property
    def native_value(self) -> int | None:
        """Return number of clean areas."""
        return len(self.coordinator.clean_areas)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return clean area list."""
        return {"clean_areas": self.coordinator.clean_areas}


class YarboMotorTempSensor(YarboSensor):
    """Motor temperature sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "motor_temp"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "motor_temp")

    @property
    def native_value(self) -> float | None:
        """Return motor temperature."""
        return self.coordinator.motor_temp_c


class YarboSavedWifiListSensor(YarboSensor):
    """Sensor showing the list of saved (remembered) WiFi networks (#98).

    Note (#109): may only return data during active robot operation
    or when a cloud connection is available. Shows unavailable when idle.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "saved_wifi_list"
    _attr_icon = "mdi:wifi-star"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "saved_wifi_list")

    @property
    def native_value(self) -> str | None:
        """Return the number of saved WiFi networks, or None when unavailable."""
        saved = self.coordinator.saved_wifi_list
        if not saved:
            return None
        return str(len(saved))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the saved WiFi networks list."""
        return {"saved_wifi_list": self.coordinator.saved_wifi_list}


class YarboLastSeenSensor(YarboSensor):
    """Timestamp sensor showing when the robot last sent telemetry."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "last_seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "last_seen")

    @property
    def native_value(self) -> datetime | None:
        """Return the last-seen time as a UTC datetime."""
        last_seen = self.coordinator.last_seen
        if last_seen is None:
            return None
        elapsed = time.monotonic() - last_seen
        return datetime.now(UTC) - timedelta(seconds=elapsed)
