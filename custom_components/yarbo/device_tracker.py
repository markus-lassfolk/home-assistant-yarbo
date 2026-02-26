"""Device tracker platform for Yarbo integration — GPS position."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
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
    """Set up Yarbo device tracker."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboDeviceTracker(coordinator)])


class YarboDeviceTracker(YarboEntity, TrackerEntity):
    """GPS device tracker sourced from robot RTK telemetry."""

    _attr_translation_key = "location"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "location")

    @property
    def latitude(self) -> float | None:
        """Return latitude from RTK telemetry."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "latitude", None)

    @property
    def longitude(self) -> float | None:
        """Return longitude from RTK telemetry."""
        if not self.telemetry:
            return None
        return getattr(self.telemetry, "longitude", None)

