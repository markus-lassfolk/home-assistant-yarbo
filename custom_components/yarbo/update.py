"""Update platform for Yarbo integration — firmware update information."""

from __future__ import annotations

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo firmware update entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboFirmwareUpdate(coordinator)])


class YarboFirmwareUpdate(YarboEntity, UpdateEntity):
    """Firmware update information entity (informational only — no install).

    Displays current firmware version from telemetry.
    Latest version comparison requires cloud API (future feature).
    """

    _attr_translation_key = "firmware"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # No INSTALL feature — OTA is triggered via the robot's own update mechanism
    _attr_supported_features = UpdateEntityFeature(0)
    _attr_auto_update = False
    _attr_release_summary = (
        "Firmware updates are managed by the Yarbo app. "
        "This entity shows the currently installed version."
    )

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "firmware")

    @property
    def installed_version(self) -> str | None:
        """Return currently installed firmware version."""
        raw_source = self.coordinator.data
        if raw_source is None:
            return None
        if isinstance(raw_source, dict):
            raw = raw_source.get("raw", raw_source)
        else:
            raw = getattr(raw_source, "raw", {})
        return raw.get("firmware_version") if isinstance(raw, dict) else None

    @property
    def latest_version(self) -> str | None:
        """Return latest available firmware version.

        Currently None — cloud API integration required for version comparison.
        This will be populated once cloud auth (#20) is complete.
        """
        return None
