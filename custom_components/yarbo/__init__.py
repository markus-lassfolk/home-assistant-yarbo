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
    CONF_ALTERNATE_BROKER_HOST,
    CONF_BROKER_ENDPOINTS,
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


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Yarbo integration — run background ARP discovery on startup."""

    async def _discover_yarbos(_now: Any = None) -> None:
        """Scan ARP table for Yarbo devices and create discovery flows."""
        from .discovery import DEFAULT_BROKER_PORT, _discover_from_arp

        endpoints = await _discover_from_arp(DEFAULT_BROKER_PORT)
        if not endpoints:
            return

        for ep in endpoints:
            # Check if already configured for this host
            existing = any(
                entry.data.get(CONF_BROKER_HOST) == ep.host
                for entry in hass.config_entries.async_entries(DOMAIN)
            )
            if existing:
                continue

            _LOGGER.info("Yarbo discovered via ARP at %s (MAC %s)", ep.host, ep.mac)
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "dhcp"},
                    data={"ip": ep.host, "macaddress": ep.mac or "", "hostname": "yarbo"},
                )
            )

    # Run 30s after HA fully starts so the network stack is ready
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
    from homeassistant.helpers.event import async_call_later

    async def _on_start(_event: Any) -> None:
        async_call_later(hass, 30, _discover_yarbos)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_start)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry to the latest version."""
    _LOGGER.debug("Migrating Yarbo config entry from version %s", config_entry.version)

    if config_entry.version == 1:
        # v1 → v2: add CONF_BROKER_ENDPOINTS list for Primary/Secondary failover
        new_data = dict(config_entry.data)
        primary = new_data.get(CONF_BROKER_HOST)
        alternate = new_data.get(CONF_ALTERNATE_BROKER_HOST)
        if CONF_BROKER_ENDPOINTS not in new_data:
            endpoints = [primary, alternate] if alternate and alternate != primary else [primary]
            new_data[CONF_BROKER_ENDPOINTS] = [h for h in endpoints if h]
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=2)
        _LOGGER.info("Migrated Yarbo config entry to version 2")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yarbo from a config entry."""
    # Ensure ordered endpoints list for Primary/Secondary failover (from discovery order)
    if CONF_BROKER_ENDPOINTS not in entry.data:
        data = dict(entry.data)
        primary = entry.data.get(CONF_BROKER_HOST)
        alternate = entry.data.get(CONF_ALTERNATE_BROKER_HOST)
        data[CONF_BROKER_ENDPOINTS] = (
            [primary, alternate] if alternate and alternate != primary else [primary]
        )
        if primary:
            hass.config_entries.async_update_entry(entry, data=data)

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
        broker=entry.data[CONF_BROKER_HOST],
        port=entry.data[CONF_BROKER_PORT],
    )

    try:
        await client.connect()
        await client.get_controller()
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
    from .repairs import (
        async_delete_cloud_token_expired_issue,
        async_delete_controller_lost_issue,
        async_delete_mqtt_disconnect_issue,
    )

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: YarboDataCoordinator = data[DATA_COORDINATOR]
        await coordinator.async_shutdown()
        await data[DATA_CLIENT].disconnect()
        # Clean up any active repair issues to prevent orphaned issues
        async_delete_mqtt_disconnect_issue(hass, entry.entry_id)
        async_delete_controller_lost_issue(hass, entry.entry_id)
        async_delete_cloud_token_expired_issue(hass, entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            async_unregister_services(hass)

    return unload_ok
