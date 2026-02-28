"""Lawn mower platform for Yarbo integration."""

from __future__ import annotations

from homeassistant.components.lawn_mower import LawnMowerActivity, LawnMowerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_LAWN_MOWER_PRO,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo lawn mower entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboLawnMower(coordinator)])


class YarboLawnMower(YarboEntity, LawnMowerEntity):
    """Lawn mower entity — available only when mower head is installed.

    Maps Yarbo robot states to HA LawnMowerActivity:
    - working/planning active → MOWING
    - paused → PAUSED
    - returning/docked/charging → DOCKED
    - error → ERROR
    """

    _attr_translation_key = "mower"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "mower")

    @property
    def available(self) -> bool:
        """Only available when lawn mower or lawn mower pro head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in (HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO)

    @property
    def activity(self) -> LawnMowerActivity | None:
        """Return current mowing activity."""
        telemetry = self.telemetry
        if not telemetry:
            return None

        if telemetry.error_code != 0:
            return LawnMowerActivity.ERROR
        if telemetry.charging_status in (1, 2, 3):
            return LawnMowerActivity.DOCKED
        if telemetry.state in (1, 7, 8):
            return LawnMowerActivity.MOWING
        if telemetry.state == 5:
            return LawnMowerActivity.PAUSED
        if telemetry.state == 2:
            return LawnMowerActivity.DOCKED
        return LawnMowerActivity.DOCKED

    async def async_start_mowing(self) -> None:
        """Start mowing — resumes last plan or starts default."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            # 🔇 Fire-and-forget: no data_feedback response
            await self.coordinator.client.publish_command("resume", {})

    async def async_pause(self) -> None:
        """Pause mowing."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            # 🔇 Fire-and-forget: no data_feedback response
            await self.coordinator.client.publish_command("planning_paused", {})

    async def async_dock(self) -> None:
        """Return robot to dock."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            # 🔇 Fire-and-forget: no data_feedback response
            await self.coordinator.client.publish_command("cmd_recharge", {})
