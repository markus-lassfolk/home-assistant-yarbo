"""The Yarbo integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

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
    # Opt-in error reporting: only active if YARBO_SENTRY_DSN env var is set
    _serial = entry.data.get(CONF_ROBOT_SERIAL, "unknown")
    init_error_reporting(
        tags={
            "integration": DOMAIN,
            "integration_version": str(entry.version) if hasattr(entry, "version") else "unknown",
            "robot_serial": f"****{_serial[-4:]}" if len(_serial) > 4 else _serial,
            "ha_version": str(hass.config.as_dict().get("version", "unknown")),
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: YarboDataCoordinator = data[DATA_COORDINATOR]
        await coordinator.async_shutdown()
        await data[DATA_CLIENT].disconnect()
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            async_unregister_services(hass)

    return unload_ok
