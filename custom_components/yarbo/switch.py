"""Switch platform for Yarbo integration — buzzer toggle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboBuzzerSwitch(coordinator)])


class YarboBuzzerSwitch(YarboEntity, SwitchEntity):
    """Buzzer toggle switch."""

    _attr_translation_key = "buzzer"
    _attr_assumed_state = True  # No read-back from robot

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "buzzer")
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if buzzer is active."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the buzzer."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.buzzer(state=1)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the buzzer."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.buzzer(state=0)
        self._is_on = False
        self.async_write_ha_state()
