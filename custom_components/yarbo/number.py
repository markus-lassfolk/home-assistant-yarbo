"""Number platform for Yarbo integration — chute velocity control."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, HEAD_TYPE_SNOW_BLOWER
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboChuteVelocityNumber(coordinator)])


class YarboChuteVelocityNumber(YarboEntity, NumberEntity):
    """Chute velocity control — snow blower head only.

    Controls the snow chute direction and speed.
    Negative = left, zero = stop, positive = right.
    Range: -2000 to 2000.
    """

    _attr_translation_key = "chute_velocity"
    _attr_native_min_value = -2000.0
    _attr_native_max_value = 2000.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "chute_velocity")
        self._current_velocity: float = 0.0

    @property
    def available(self) -> bool:
        """Only available when snow blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_SNOW_BLOWER

    @property
    def native_value(self) -> float:
        """Return the last set velocity."""
        return self._current_velocity

    async def async_set_native_value(self, value: float) -> None:
        """Set chute velocity."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            # Note: python-yarbo API uses 'vel' parameter name
            await self.coordinator.client.set_chute(vel=int(value))
        self._current_velocity = value
        self.async_write_ha_state()
