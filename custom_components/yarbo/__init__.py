"""The Yarbo integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_integration

from yarbo import YarboLocalClient
from yarbo.exceptions import YarboConnectionError

from .const import (
    CONF_BROKER_HOST,
    CONF_BROKER_PORT,
    CONF_ROBOT_SERIAL,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import YarboDataCoordinator
from .error_reporting import init_error_reporting
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yarbo from a config entry."""
    # Get actual integration version from manifest
    integration_version = "unknown"
    try:
        integration = await async_get_integration(hass, DOMAIN)
        integration_version = integration.manifest.get("version", "unknown") or "unknown"
    except Exception:
        pass

    # Opt-in error reporting: only active if YARBO_SENTRY_DSN env var is set
    _serial = entry.data.get(CONF_ROBOT_SERIAL, "unknown")
    init_error_reporting(
        tags={
            "integration": DOMAIN,
            "integration_version": integration_version,
            "robot_serial": f"****{_serial[-4:]}" if len(_serial) > 4 else _serial,
            "ha_version": __version__,
        }
    )

    client = YarboLocalClient(
        host=entry.data[CONF_BROKER_HOST],
        port=entry.data[CONF_BROKER_PORT],
    )

    try:
        await client.connect()
        await client.get_controller(timeout=5.0)
    except YarboConnectionError as err:
        await client.disconnect()
        raise ConfigEntryNotReady(f"Cannot connect to Yarbo: {err}") from err
    except Exception:
        await client.disconnect()
        raise

    coordinator = YarboDataCoordinator(hass, client, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        # Fix: shut down coordinator (cancels background tasks) before re-raising
        await coordinator.async_shutdown()
        await client.disconnect()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)

    # Register options update listener so throttle and other options apply
    # immediately when the user changes them in the options UI — without
    # requiring a full config-entry reload.
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — propagate new options to the coordinator."""
    coordinator: YarboDataCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    options: dict[str, Any] = dict(entry.options)
    coordinator.update_options(options)
    _LOGGER.debug("Yarbo options applied for entry %s", entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from .repairs import async_delete_controller_lost_issue, async_delete_mqtt_disconnect_issue

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: YarboDataCoordinator = data[DATA_COORDINATOR]
        await coordinator.async_shutdown()
        await data[DATA_CLIENT].disconnect()
        # Clean up any active repair issues to prevent orphaned issues
        async_delete_mqtt_disconnect_issue(hass, entry.entry_id)
        async_delete_controller_lost_issue(hass, entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            async_unregister_services(hass)

    return unload_ok
