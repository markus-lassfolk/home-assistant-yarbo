"""Telemetry helpers for Yarbo integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GnggaData:
    """Parsed GNGGA data from RTK telemetry."""

    latitude: float | None
    longitude: float | None
    fix_quality: int | None
    satellite_count: int | None
    hdop: float | None
    altitude_m: float | None


def get_raw_dict(telemetry: Any) -> dict[str, Any]:
    """Return raw telemetry dict when available."""
    if telemetry is None:
        return {}
    if isinstance(telemetry, dict):
        raw = telemetry.get("raw", telemetry)
    else:
        raw = getattr(telemetry, "raw", {})
    return raw if isinstance(raw, dict) else {}


def get_nested_raw_value(telemetry: Any, *path: str) -> Any | None:
    """Return nested raw value by path from telemetry."""
    raw: Any = get_raw_dict(telemetry)
    for key in path:
        if not isinstance(raw, dict) or key not in raw:
            return None
        raw = raw[key]
    return raw


def get_value_from_paths(telemetry: Any, paths: list[tuple[str, ...]]) -> Any | None:
    """Return the first non-None value from a list of raw paths."""
    for path in paths:
        value = get_nested_raw_value(telemetry, *path)
        if value is not None:
            return value
    return None


def get_gngga_data(telemetry: Any) -> GnggaData | None:
    """Return parsed GNGGA data from telemetry, if present."""
    gngga = get_nested_raw_value(telemetry, "rtk_base_data", "rover", "gngga")
    return parse_gngga(gngga)


def parse_gngga(sentence: Any) -> GnggaData | None:
    """Parse GNGGA sentence into coordinates and quality metrics."""
    if not isinstance(sentence, str):
        return None
    line = sentence.strip()
    if not line:
        return None
    if "*" in line:
        line = line.split("*", 1)[0]
    if line.startswith("$"):
        line = line[1:]
    parts = line.split(",")
    if len(parts) < 10:
        return None

    latitude = _parse_lat_lon(parts[2], parts[3])
    longitude = _parse_lat_lon(parts[4], parts[5])
    fix_quality = _parse_int(parts[6])
    satellite_count = _parse_int(parts[7])
    hdop = _parse_float(parts[8])
    altitude = _parse_float(parts[9])

    return GnggaData(
        latitude=latitude,
        longitude=longitude,
        fix_quality=fix_quality,
        satellite_count=satellite_count,
        hdop=hdop,
        altitude_m=altitude,
    )


def _parse_lat_lon(value: str, hemisphere: str) -> float | None:
    """Convert NMEA lat/lon (DDMM.MMMMM or DDDMM.MMMMM) to decimal degrees."""
    if not value or not hemisphere:
        return None
    try:
        raw = float(value)
    except ValueError:
        return None
    degrees = int(raw // 100)
    minutes = raw - (degrees * 100)
    decimal = degrees + (minutes / 60)
    hemi = hemisphere.upper()
    if hemi in {"S", "W"}:
        decimal = -decimal
    return decimal


def _parse_int(value: str) -> int | None:
    """Parse int from NMEA field."""
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    """Parse float from NMEA field."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
