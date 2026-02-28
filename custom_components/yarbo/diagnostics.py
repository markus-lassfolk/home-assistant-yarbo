"""Diagnostics support for Yarbo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    CONF_ROBOT_SERIAL,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Output is redacted to remove PII:
    - Serial number (partial)
    - Head serial (full redaction)
    - GPS coordinates (removed entirely)
    - Cloud credentials (never included)

    TODO: Implement in v0.1.0
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data[DATA_COORDINATOR]
    client = data[DATA_CLIENT]

    raw_source = coordinator.data
    if isinstance(raw_source, dict):
        raw = raw_source.get("raw", raw_source)
    elif raw_source is not None:
        raw = getattr(raw_source, "raw", {})
    else:
        raw = {}

    # Ensure raw is a dict before passing to _redact_telemetry
    if not isinstance(raw, dict):
        raw = {}

    return {
        "config_entry": _redact_config(entry.data),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_count": coordinator._update_count,
            "last_seen": coordinator._last_seen,
            "throttle_interval": coordinator._throttle_interval,
        },
        "telemetry": {
            "raw": _redact_telemetry(raw),
        },
        "connection": {
            "connected": client.is_connected,
            "controller_acquired": client.controller_acquired,
            "serial_number": _redact_sn(getattr(client, "serial_number", "")),
        },
    }


def _redact_sn(sn: str) -> str:
    """Redact serial number — keep last 4 chars only."""
    if not sn:
        return "****"
    if len(sn) <= 4:
        return sn
    return f"****{sn[-4:]}"


def _redact_config(config: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive config fields."""
    redacted = dict(config)
    if CONF_ROBOT_SERIAL in redacted:
        redacted[CONF_ROBOT_SERIAL] = _redact_sn(redacted[CONF_ROBOT_SERIAL])
    # Include recording file path if active
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator and hasattr(coordinator, "recorder"):
        data["mqtt_recording"] = {
            "enabled": coordinator.recorder.enabled,
            "path": str(coordinator.recorder.recording_path) if coordinator.recorder.recording_path else None,
            "files": [str(p) for p in coordinator.recorder.list_recordings()[:5]],
        }

    if CONF_CLOUD_USERNAME in redacted:
        redacted[CONF_CLOUD_USERNAME] = "[REDACTED]"
    if CONF_CLOUD_REFRESH_TOKEN in redacted:
        redacted[CONF_CLOUD_REFRESH_TOKEN] = "[REDACTED]"
    return redacted


def _redact_telemetry(raw: dict[str, Any]) -> dict[str, Any]:
    """Remove GPS coordinates and serial numbers from telemetry."""
    redacted = dict(raw)
    redacted.pop("rtk_base_data", None)  # Contains exact GPS coordinates
    redacted.pop("gps", None)
    redacted.pop("gps_lat", None)
    redacted.pop("gps_lon", None)
    redacted.pop("latitude", None)
    redacted.pop("longitude", None)
    if "HeadSerialMsg" in redacted:
        redacted["HeadSerialMsg"] = {"head_sn": "[REDACTED]"}
    return redacted
