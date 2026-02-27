"""Repair issue helpers for Yarbo integration.

Three actionable repair conditions are supported:

- mqtt_disconnect: no telemetry received for > 60s (base station unreachable)
- controller_lost: a command failed because the controller session was stolen
- cloud_token_expired: cloud API returned 401/403 (token must be refreshed)
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

# Issue ID constants — combined with entry_id to create a unique key per device
ISSUE_MQTT_DISCONNECT = "mqtt_disconnect"
ISSUE_CONTROLLER_LOST = "controller_lost"
ISSUE_CLOUD_TOKEN_EXPIRED = "cloud_token_expired"


# ---------------------------------------------------------------------------
# MQTT disconnect (base station unreachable, telemetry silence > 60 s)
# ---------------------------------------------------------------------------


def async_create_mqtt_disconnect_issue(hass: HomeAssistant, entry_id: str, name: str) -> None:
    """Create a WARNING repair issue for MQTT disconnect."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_MQTT_DISCONNECT}_{entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_MQTT_DISCONNECT,
        translation_placeholders={"name": name},
    )


def async_delete_mqtt_disconnect_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the MQTT disconnect repair issue when telemetry resumes."""
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_MQTT_DISCONNECT}_{entry_id}")


# ---------------------------------------------------------------------------
# Controller lost (another app has taken the controller session)
# ---------------------------------------------------------------------------


def async_create_controller_lost_issue(hass: HomeAssistant, entry_id: str, name: str) -> None:
    """Create an ERROR repair issue when the controller session is lost.

    Marked fixable so HA shows a 'Re-acquire' button in the UI.
    Resolving triggers async_resolve_controller_lost_issue which calls
    client.get_controller() and clears the issue.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_CONTROLLER_LOST}_{entry_id}",
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_CONTROLLER_LOST,
        translation_placeholders={"name": name},
    )


def async_delete_controller_lost_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the controller lost repair issue after re-acquisition succeeds."""
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_CONTROLLER_LOST}_{entry_id}")


# ---------------------------------------------------------------------------
# Cloud token expired (HTTP 401/403 from cloud API)
# ---------------------------------------------------------------------------


def async_create_cloud_token_expired_issue(hass: HomeAssistant, entry_id: str, name: str) -> None:
    """Create a WARNING repair issue when the cloud auth token has expired.

    The issue description guides the user to the reauth flow.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_CLOUD_TOKEN_EXPIRED}_{entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_CLOUD_TOKEN_EXPIRED,
        translation_placeholders={"name": name},
    )


def async_delete_cloud_token_expired_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the cloud token expired repair issue after successful re-auth."""
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_CLOUD_TOKEN_EXPIRED}_{entry_id}")
