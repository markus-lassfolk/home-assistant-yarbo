"""Device tracker platform for Yarbo integration — GPS position."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity
from .telemetry import get_gngga_data, get_nested_raw_value


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

    def _handle_coordinator_update(self) -> None:
        """Handle updated telemetry for GPS tracking."""
        telemetry = self.telemetry
        if telemetry is None:
            self._attr_latitude = None
            self._attr_longitude = None
            self._attr_location_name = None
        else:
            gngga = get_gngga_data(telemetry)
            if gngga is not None:
                self._attr_latitude = gngga.latitude
                self._attr_longitude = gngga.longitude
            else:
                self._attr_latitude = None
                self._attr_longitude = None

            charging_status = getattr(telemetry, "charging_status", None)
            if charging_status is None:
                charging_status = get_nested_raw_value(
                    telemetry, "StateMSG", "charging_status"
                )
            if charging_status in (1, 2, 3):
                self._attr_location_name = STATE_HOME
            else:
                self._attr_location_name = STATE_NOT_HOME
        super()._handle_coordinator_update()

    @property
    def latitude(self) -> float | None:
        """Return latitude from RTK telemetry."""
        if not self.telemetry:
            return None
        return self._attr_latitude

    @property
    def longitude(self) -> float | None:
        """Return longitude from RTK telemetry."""
        if not self.telemetry:
            return None
        return self._attr_longitude
