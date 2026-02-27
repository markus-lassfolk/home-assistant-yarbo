"""Repair issue helpers for Yarbo integration (issue #27).

Three repair conditions:
- mqtt_disconnect: no telemetry > 60s (base station unreachable)
- controller_lost: command failed (controller session stolen)
- cloud_token_expired: cloud API 401/403 → triggers reauth flow
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .const import CONF_ROBOT_NAME, DATA_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .coordinator import YarboDataCoordinator

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
# Cloud token expired (401/403 from cloud API) — triggers reauth
# ---------------------------------------------------------------------------


def async_create_cloud_token_expired_issue(
    hass: HomeAssistant, entry_id: str, name: str
) -> None:
    """Create a WARNING repair issue when cloud token expired (401/403).

    Fixable: opens the reauth flow to refresh the token.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_CLOUD_TOKEN_EXPIRED}_{entry_id}",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_CLOUD_TOKEN_EXPIRED,
        translation_placeholders={"name": name},
    )


def async_delete_cloud_token_expired_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the cloud token expired issue after reauth succeeds."""
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_CLOUD_TOKEN_EXPIRED}_{entry_id}")


# ---------------------------------------------------------------------------
# Repair flow handler for fixable issues
# ---------------------------------------------------------------------------


class YarboRepairFlow(RepairsFlow):
    """Handler for Yarbo repair flows."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle confirm: re-acquire controller or trigger cloud reauth."""
        if user_input is not None:
            issue_id = self.issue_id

            # Cloud token expired → start reauth flow and close repair
            if issue_id.startswith(f"{ISSUE_CLOUD_TOKEN_EXPIRED}_"):
                entry_id = issue_id[len(f"{ISSUE_CLOUD_TOKEN_EXPIRED}_") :]
                entry = self.hass.config_entries.async_get_entry(entry_id)
                if entry:
                    self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": SOURCE_REAUTH, "entry_id": entry_id},
                        data=entry.data,
                    )
                    return self.async_create_entry(data={})
                return self.async_abort(reason="unknown")

            # Controller lost → re-acquire controller
            if issue_id.startswith(f"{ISSUE_CONTROLLER_LOST}_"):
                entry_id = issue_id[len(f"{ISSUE_CONTROLLER_LOST}_") :]
                if DOMAIN in self.hass.data and entry_id in self.hass.data[DOMAIN]:
                    coordinator: YarboDataCoordinator = self.hass.data[DOMAIN][entry_id][
                        DATA_COORDINATOR
                    ]
                    async with coordinator.command_lock:
                        try:
                            await coordinator.client.get_controller(timeout=5.0)
                            coordinator.resolve_controller_lost()
                        except Exception as err:
                            _LOGGER.warning("Failed to re-acquire Yarbo controller: %s", err)
                            return self.async_abort(reason="cannot_connect")
                    return self.async_create_entry(data={})
                return self.async_abort(reason="unknown")

        # Show form: get robot name for placeholder
        issue_id = self.issue_id
        robot_name = "Yarbo"
        if issue_id.startswith(f"{ISSUE_CONTROLLER_LOST}_"):
            entry_id = issue_id[len(f"{ISSUE_CONTROLLER_LOST}_") :]
        elif issue_id.startswith(f"{ISSUE_CLOUD_TOKEN_EXPIRED}_"):
            entry_id = issue_id[len(f"{ISSUE_CLOUD_TOKEN_EXPIRED}_") :]
        else:
            entry_id = None
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry:
                robot_name = entry.data.get(CONF_ROBOT_NAME, "Yarbo")

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": robot_name},
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create a repair flow for fixable Yarbo issues."""
    return YarboRepairFlow()
