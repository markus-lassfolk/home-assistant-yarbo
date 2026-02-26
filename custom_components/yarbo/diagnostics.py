"""Diagnostics support for Yarbo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


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
    # TODO: Implement when coordinator is available
    # data = hass.data[DOMAIN][entry.entry_id]
    # coordinator = data[DATA_COORDINATOR]
    # client = data[DATA_CLIENT]

    return {
        "config_entry": {
            "broker": entry.data.get("broker_host", "unknown"),
            "port": entry.data.get("broker_port", 1883),
            "sn": _redact_sn(entry.data.get("robot_serial", "")),
            "cloud_enabled": bool(entry.data.get("cloud_username")),
        },
        "coordinator": {
            # TODO: "last_update_success": coordinator.last_update_success,
            # TODO: "update_count": coordinator._update_count,
            "status": "not_implemented",
        },
        "telemetry": {
            # TODO: _redact_telemetry(coordinator.data.raw if coordinator.data else {})
            "status": "not_implemented",
        },
        "connection": {
            # TODO: "connected": client.is_connected,
            # TODO: "controller_acquired": client._local._controller_acquired,
            "status": "not_implemented",
        },
    }


def _redact_sn(sn: str) -> str:
    """Redact serial number — keep first 6 chars only."""
    if not sn:
        return "***"
    return sn[:6] + "***"


def _redact_telemetry(raw: dict[str, Any]) -> dict[str, Any]:
    """Remove GPS coordinates and serial numbers from telemetry."""
    redacted = dict(raw)
    redacted.pop("rtk_base_data", None)  # Contains exact GPS coordinates
    if "HeadSerialMsg" in redacted:
        redacted["HeadSerialMsg"] = {"head_sn": "***"}
    return redacted
