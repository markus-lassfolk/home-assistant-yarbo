"""Local telemetry model for type hints.

python-yarbo provides the runtime telemetry dataclass. This local copy is
used for typing within the integration and includes newer fields used by
entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class YarboTelemetry:
    """Telemetry data model for type hints."""

    battery_capacity: int | None = None
    battery: int | None = None
    charging_status: int | None = None
    state: int | None = None
    error_code: int | None = None
    serial_number: str | None = None
    plan_id: str | int | None = None
    duration: int | None = None
    head_type: int | None = None
    rtk_status: int | None = None
    heading: float | None = None
    chute_angle: int | None = None
    rain_sensor: int | None = None
    satellite_count: int | None = None
    charge_voltage_mv: int | None = None
    charge_current_ma: int | None = None
    odom_confidence: float | None = None
    rtcm_age: float | None = None
    mqtt_age: float | None = None

    head_serial: str | None = None
    battery_temp_error: int | None = None
    base_station_status: int | str | None = None
    rtcm_source_type: int | str | None = None
    heading_dop: float | None = None
    heading_status: int | None = None
    antenna_distance: float | None = None
    wireless_charge_state: int | str | None = None
    wireless_charge_error: int | str | None = None
    chute_steering_info: int | str | None = None
    nav_sensor_front_right: int | None = None
    nav_sensor_rear_right: int | None = None
    head_gyro_pitch: float | None = None
    head_gyro_roll: float | None = None
    machine_controller: int | str | None = None
    odom_x: float | None = None
    odom_y: float | None = None
    odom_phi: float | None = None
    ultrasonic_left_front: int | None = None
    ultrasonic_middle: int | None = None
    ultrasonic_right_front: int | None = None

    raw: dict[str, Any] | None = None
