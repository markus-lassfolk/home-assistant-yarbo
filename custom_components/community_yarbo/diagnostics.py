"""Diagnostics support for Yarbo integration."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BROKER_HOST,
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

    # Seconds since we last received any telemetry (for debugging "Last Seen" issues)
    last_seen_mono = getattr(coordinator, "_last_seen", None)
    seconds_since_last_telemetry: float | None = None
    if last_seen_mono is not None:
        try:
            seconds_since_last_telemetry = time.monotonic() - last_seen_mono
        except (TypeError, AttributeError):
            pass

    # Actual broker the client is connected to (may differ after failover)
    actual_broker = None
    try:
        transport = getattr(client, "_transport", None)
        if transport is not None:
            actual_broker = getattr(transport, "_broker", None)
    except Exception:
        pass

    # Listener count helps diagnose "HA hangs" — many entities = more work per update
    listener_count: int | None = None
    try:
        listeners = getattr(coordinator, "_listeners", None)
        if listeners is not None and isinstance(listeners, list):
            listener_count = len(listeners)
    except Exception:
        pass

    diagnostics = {
        "config_entry": _redact_config(entry.data),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_count": coordinator._update_count,
            "listener_count": listener_count,
            "last_seen": coordinator._last_seen,
            "last_telemetry_received_utc": getattr(
                coordinator, "_last_telemetry_received_utc", None
            ),
            "seconds_since_last_telemetry": seconds_since_last_telemetry,
            "throttle_interval": coordinator._throttle_interval,
            "poll_interval": getattr(coordinator, "_poll_interval", None),
        },
        "telemetry": {
            "raw": _redact_telemetry(raw),
        },
        "connection": {
            "broker_host": entry.data.get(CONF_BROKER_HOST),
            "actual_broker_host": actual_broker,
            "connected": client.is_connected,
            "controller_acquired": client.controller_acquired,
            "serial_number": _redact_sn(getattr(client, "serial_number", "")),
        },
    }

    if hasattr(coordinator, "recorder"):
        diagnostics["mqtt_recording"] = {
            "enabled": coordinator.recorder.enabled,
            "path": (
                str(coordinator.recorder.recording_path)
                if coordinator.recorder.recording_path
                else None
            ),
            "files": [str(p) for p in coordinator.recorder.list_recordings()[:5]],
        }

    return diagnostics


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
