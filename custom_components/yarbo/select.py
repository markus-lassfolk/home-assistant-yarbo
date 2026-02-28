"""Select platform for Yarbo integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
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
    async_add_entities([YarboPlanSelect(coordinator)])


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
