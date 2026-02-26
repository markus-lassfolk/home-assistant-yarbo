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
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import YarboDataCoordinator
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yarbo from a config entry.

    TODO: Implement in v0.1.0
    - Instantiate YarboClient from python-yarbo
    - Connect to the local MQTT broker
    - Create YarboDataCoordinator and start telemetry loop
    - Register device in device_registry (robot + data center)
    - Register services (yarbo.send_command, etc.)
    - Forward entry setup to all platforms
    """
    # TODO: Import YarboClient from python-yarbo
    # from yarbo import YarboClient

    # TODO: Create client
    # client = YarboClient(
    #     broker=entry.data[CONF_BROKER_HOST],
    #     sn=entry.data[CONF_ROBOT_SERIAL],
    #     port=entry.data.get(CONF_BROKER_PORT, DEFAULT_BROKER_PORT),
    #     auto_controller=entry.options.get(OPT_AUTO_CONTROLLER, DEFAULT_AUTO_CONTROLLER),
    # )
    # await client.connect()

    # TODO: Create coordinator
    # coordinator = YarboDataCoordinator(hass, client, entry)
    # await coordinator.async_config_entry_first_refresh()

    # TODO: Store in hass.data
    # hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
    #     DATA_CLIENT: client,
    #     DATA_COORDINATOR: coordinator,
    # }

    # TODO: Forward setup to platforms
    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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

    coordinator = YarboDataCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    TODO: Implement in v0.1.0
    - Cancel telemetry task
    - Disconnect YarboClient
    - Unload all platforms
    """
    # TODO: Unload platforms
    # unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # TODO: Disconnect and cleanup
    # if unload_ok:
    #     data = hass.data[DOMAIN].pop(entry.entry_id)
    #     await data[DATA_CLIENT].disconnect()

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
