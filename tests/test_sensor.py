"""Tests for the Yarbo sensor platform (#14)."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.yarbo.const import (
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_SNOW_BLOWER,
)
from custom_components.yarbo.sensor import (
    YarboBatterySensor,
    YarboChargeCurrentSensor,
    YarboChargeVoltageSensor,
    YarboChargingPowerSensor,
    YarboChuteAngleSensor,
    YarboErrorCodeSensor,
    YarboHeadingSensor,
    YarboMqttAgeSensor,
    YarboOdomConfidenceSensor,
    YarboRainSensor,
    YarboRtcmAgeSensor,
    YarboRtkStatusSensor,
    YarboSatelliteCountSensor,
)


def _make_coordinator(**telemetry_kwargs: object) -> MagicMock:
    """Build a minimal mock coordinator for sensor tests."""
    coord = MagicMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0004",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.last_update_success = True
    telemetry = MagicMock()
    # Default telemetry values
    telemetry.battery_capacity = 83
    telemetry.battery = 83
    telemetry.charging_status = 0
    telemetry.state = 0
    telemetry.error_code = 0
    telemetry.head_type = HEAD_TYPE_SNOW_BLOWER
    # v0.2.0 extended fields (may be absent in older firmware)
    telemetry.rtk_status = 4  # RTK fixed
    telemetry.heading = 180.0
    telemetry.chute_angle = 90
    telemetry.rain_sensor = 0
    telemetry.satellite_count = 12
    telemetry.charge_voltage_mv = None
    telemetry.charge_current_ma = None
    telemetry.odom_confidence = None
    telemetry.rtcm_age = None
    telemetry.mqtt_age = None
    for k, v in telemetry_kwargs.items():
        setattr(telemetry, k, v)
    coord.data = telemetry
    return coord


class TestBatterySensor:
    """Tests for battery sensor (pre-existing, issue #14 baseline)."""

    def test_native_value(self) -> None:
        """Returns battery_capacity from telemetry."""
        coord = _make_coordinator(battery_capacity=75)
        entity = YarboBatterySensor(coord)
        assert entity.native_value == 75

    def test_no_telemetry(self) -> None:
        """Returns None when no telemetry."""
        coord = _make_coordinator()
        coord.data = None
        entity = YarboBatterySensor(coord)
        assert entity.native_value is None


class TestRtkStatusSensor:
    """Tests for RTK status sensor (issue #14)."""

    def test_disabled_by_default(self) -> None:
        """RTK status must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboRtkStatusSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_rtk_fixed(self) -> None:
        """Status code 4 maps to 'rtk_fixed'."""
        coord = _make_coordinator(rtk_status=4)
        entity = YarboRtkStatusSensor(coord)
        assert entity.native_value == "rtk_fixed"

    def test_rtk_float(self) -> None:
        """Status code 5 maps to 'rtk_float'."""
        coord = _make_coordinator(rtk_status=5)
        entity = YarboRtkStatusSensor(coord)
        assert entity.native_value == "rtk_float"

    def test_invalid(self) -> None:
        """Status code 0 maps to 'invalid'."""
        coord = _make_coordinator(rtk_status=0)
        entity = YarboRtkStatusSensor(coord)
        assert entity.native_value == "invalid"

    def test_gps(self) -> None:
        """Status code 1 maps to 'gps'."""
        coord = _make_coordinator(rtk_status=1)
        entity = YarboRtkStatusSensor(coord)
        assert entity.native_value == "gps"

    def test_unknown_code(self) -> None:
        """Unknown status code maps to 'unknown'."""
        coord = _make_coordinator(rtk_status=99)
        entity = YarboRtkStatusSensor(coord)
        assert entity.native_value == "unknown"

    def test_none_returns_none(self) -> None:
        """Returns None when rtk_status is absent."""
        coord = _make_coordinator()
        coord.data.rtk_status = None
        entity = YarboRtkStatusSensor(coord)
        assert entity.native_value is None


class TestHeadingSensor:
    """Tests for heading sensor (issue #14)."""

    def test_disabled_by_default(self) -> None:
        """Heading sensor must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboHeadingSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_native_value(self) -> None:
        """Returns heading in degrees."""
        coord = _make_coordinator(heading=270.0)
        entity = YarboHeadingSensor(coord)
        assert entity.native_value == 270.0

    def test_unit_of_measurement(self) -> None:
        """Unit is degrees."""
        coord = _make_coordinator()
        entity = YarboHeadingSensor(coord)
        assert entity.native_unit_of_measurement == "°"


class TestChuteAngleSensor:
    """Tests for chute angle sensor (issue #14)."""

    def test_disabled_by_default(self) -> None:
        """Chute angle sensor must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboChuteAngleSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_native_value_snow_blower(self) -> None:
        """Returns chute_angle when snow blower head is installed."""
        coord = _make_coordinator(head_type=HEAD_TYPE_SNOW_BLOWER, chute_angle=45)
        coord.last_update_success = True
        entity = YarboChuteAngleSensor(coord)
        assert entity.native_value == 45

    def test_unavailable_non_snow_blower(self) -> None:
        """Not available when non-snow-blower head is installed."""
        coord = _make_coordinator(head_type=HEAD_TYPE_LAWN_MOWER)
        coord.last_update_success = True
        entity = YarboChuteAngleSensor(coord)
        assert entity.available is False


class TestRainSensor:
    """Tests for rain sensor (issue #14)."""

    def test_disabled_by_default(self) -> None:
        """Rain sensor must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboRainSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_dry(self) -> None:
        """Returns 0 when dry."""
        coord = _make_coordinator(rain_sensor=0)
        entity = YarboRainSensor(coord)
        assert entity.native_value == 0

    def test_wet(self) -> None:
        """Returns non-zero when wet."""
        coord = _make_coordinator(rain_sensor=150)
        entity = YarboRainSensor(coord)
        assert entity.native_value == 150


class TestSatelliteCountSensor:
    """Tests for satellite count sensor (issue #14)."""

    def test_disabled_by_default(self) -> None:
        """Satellite count sensor must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboSatelliteCountSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_native_value(self) -> None:
        """Returns satellite count."""
        coord = _make_coordinator(satellite_count=14)
        entity = YarboSatelliteCountSensor(coord)
        assert entity.native_value == 14

    def test_none_when_absent(self) -> None:
        """Returns None when satellite_count not in telemetry."""
        coord = _make_coordinator()
        coord.data.satellite_count = None
        entity = YarboSatelliteCountSensor(coord)
        assert entity.native_value is None


class TestChargingPowerSensor:
    """Tests for charging power sensor (issue #14)."""

    def test_disabled_by_default(self) -> None:
        """Charging power sensor must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboChargingPowerSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_power_calculation(self) -> None:
        """Power = voltage_mV x current_mA / 1_000_000."""
        coord = _make_coordinator(charge_voltage_mv=20000, charge_current_ma=1500)
        entity = YarboChargingPowerSensor(coord)
        # 20000 mV x 1500 mA / 1_000_000 = 30.0 W
        assert entity.native_value == 30.0

    def test_none_when_voltage_absent(self) -> None:
        """Returns None when voltage is not available."""
        coord = _make_coordinator(charge_voltage_mv=None, charge_current_ma=1500)
        entity = YarboChargingPowerSensor(coord)
        assert entity.native_value is None

    def test_none_when_current_absent(self) -> None:
        """Returns None when current is not available."""
        coord = _make_coordinator(charge_voltage_mv=20000, charge_current_ma=None)
        entity = YarboChargingPowerSensor(coord)
        assert entity.native_value is None

    def test_unit_of_measurement(self) -> None:
        """Unit is watts."""
        coord = _make_coordinator()
        entity = YarboChargingPowerSensor(coord)
        assert entity.native_unit_of_measurement == "W"


class TestDiagnosticSensors:
    """Tests for diagnostic sensors (issue #14)."""

    def test_odom_confidence_disabled_by_default(self) -> None:
        coord = _make_coordinator()
        entity = YarboOdomConfidenceSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_rtcm_age_disabled_by_default(self) -> None:
        coord = _make_coordinator()
        entity = YarboRtcmAgeSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_charge_voltage_disabled_by_default(self) -> None:
        coord = _make_coordinator()
        entity = YarboChargeVoltageSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_charge_current_disabled_by_default(self) -> None:
        coord = _make_coordinator()
        entity = YarboChargeCurrentSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_mqtt_age_disabled_by_default(self) -> None:
        coord = _make_coordinator()
        entity = YarboMqttAgeSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_charge_voltage_unit(self) -> None:
        coord = _make_coordinator()
        entity = YarboChargeVoltageSensor(coord)
        assert entity.native_unit_of_measurement == "V"

    def test_charge_current_unit(self) -> None:
        coord = _make_coordinator()
        entity = YarboChargeCurrentSensor(coord)
        assert entity.native_unit_of_measurement == "A"

    def test_rtcm_age_unit(self) -> None:
        coord = _make_coordinator()
        entity = YarboRtcmAgeSensor(coord)
        assert entity.native_unit_of_measurement == "s"

    def test_mqtt_age_unit(self) -> None:
        coord = _make_coordinator()
        entity = YarboMqttAgeSensor(coord)
        assert entity.native_unit_of_measurement == "s"


class TestErrorCodeSensor:
    """Tests for error code diagnostic sensor."""

    def test_disabled_by_default(self) -> None:
        """Error code sensor must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboErrorCodeSensor(coord)
        assert entity.entity_registry_enabled_default is False

    def test_native_value(self) -> None:
        """Returns error_code from telemetry."""
        coord = _make_coordinator(error_code=42)
        entity = YarboErrorCodeSensor(coord)
        assert entity.native_value == 42
