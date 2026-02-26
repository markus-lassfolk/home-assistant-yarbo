"""The Yarbo integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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

    _LOGGER.debug("Yarbo integration setup for entry %s (stub)", entry.entry_id)
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

    _LOGGER.debug("Yarbo integration unloaded for entry %s (stub)", entry.entry_id)
    return True
