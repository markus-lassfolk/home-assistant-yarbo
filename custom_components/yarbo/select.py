"""Select platform for Yarbo integration."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, HEAD_TYPE_SNOW_BLOWER
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo select entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboPlanSelect(coordinator),
            YarboTurnTypeSelect(coordinator),
            YarboSnowPushDirectionSelect(coordinator),
        ]
    )


class YarboPlanSelect(YarboEntity, SelectEntity):
    """Select a saved work plan to start."""

    _attr_translation_key = "work_plan"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "work_plan")

    async def async_added_to_hass(self) -> None:
        """Fetch plans when the entity is added."""
        await super().async_added_to_hass()
        try:
            await self.coordinator.read_all_plans()
        except Exception as err:  # pragma: no cover - best effort
            _LOGGER.debug("Failed to read plan list: %s", err)

    @property
    def options(self) -> list[str]:
        """Return available plan names."""
        return self.coordinator.plan_options

    @property
    def current_option(self) -> str | None:
        """Return current plan name, if known."""
        plan_id = self.coordinator.active_plan_id
        return self.coordinator.plan_name_for_id(plan_id)

    async def async_select_option(self, option: str) -> None:
        """Start the selected plan."""
        plan_id = self.coordinator.plan_id_for_name(option)
        if plan_id is None:
            raise HomeAssistantError(f"Unknown plan: {option}")
        await self.coordinator.start_plan(plan_id)


class YarboTurnTypeSelect(YarboEntity, SelectEntity):
    """Select the turn type for mowing."""

    _attr_translation_key = "turn_type"
    _attr_options: ClassVar[tuple[str, ...]] = ("u_turn", "three_point", "zero_radius")
    _attr_icon = "mdi:rotate-right"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True

    _turn_type_map: ClassVar[dict[str, int]] = MappingProxyType(
        {"u_turn": 0, "three_point": 1, "zero_radius": 2}
    )

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "turn_type")
        self._current_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the last selected turn type."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Set the turn type."""
        if option not in self._turn_type_map:
            raise HomeAssistantError(f"Unknown turn type: {option}")
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "set_turn_type",
                {"turn_type": self._turn_type_map[option]},
            )
        self._current_option = option
        self.async_write_ha_state()


class YarboSnowPushDirectionSelect(YarboEntity, SelectEntity):
    """Select snow push direction (snow blower head only)."""

    _attr_translation_key = "snow_push_direction"
    _attr_options: ClassVar[tuple[str, ...]] = ("left", "right", "center")
    _attr_icon = "mdi:snowflake"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True

    _direction_map: ClassVar[dict[str, int]] = MappingProxyType(
        {"left": 0, "right": 1, "center": 2}
    )

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "snow_push_direction")
        self._current_option: str | None = None

    @property
    def available(self) -> bool:
        """Only available when snow blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_SNOW_BLOWER

    @property
    def current_option(self) -> str | None:
        """Return the last selected direction."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Set the snow push direction."""
        if option not in self._direction_map:
            raise HomeAssistantError(f"Unknown snow push direction: {option}")
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "push_snow_dir",
                {"direction": self._direction_map[option]},
            )
        self._current_option = option
        self.async_write_ha_state()
