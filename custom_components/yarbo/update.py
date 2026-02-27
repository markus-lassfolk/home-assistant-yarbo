"""Update platform for Yarbo integration — firmware update information."""

from __future__ import annotations

import logging

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    CONF_ROBOT_SERIAL,
    DATA_COORDINATOR,
    DOMAIN,
    OPT_CLOUD_ENABLED,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity

_LOGGER = logging.getLogger(__name__)


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

    Displays currently installed firmware version from MQTT telemetry.
    When cloud auth is configured, also fetches the latest available version
    from the Yarbo cloud API for comparison.
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
        self._latest_version: str | None = None

    @property
    def installed_version(self) -> str | None:
        """Return currently installed firmware version from telemetry."""
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
        """Return latest available firmware version from cloud, if configured.

        Falls back to installed_version when cloud is disabled or unavailable,
        so the entity shows no pending update when cloud is not configured.
        """
        if self._latest_version is not None:
            return self._latest_version
        # When no cloud version is known, report latest == installed (no update)
        return self.installed_version

    async def async_update(self) -> None:
        """Fetch latest firmware version from cloud when cloud auth is enabled."""
        entry = self.coordinator._entry
        cloud_enabled = entry.options.get(OPT_CLOUD_ENABLED, False)
        refresh_token = entry.data.get(CONF_CLOUD_REFRESH_TOKEN)

        if not cloud_enabled or not refresh_token:
            return

        username = entry.data.get(CONF_CLOUD_USERNAME, "")
        robot_serial = entry.data.get(CONF_ROBOT_SERIAL, "")

        try:
            from yarbo.cloud import YarboCloudClient  # noqa: PLC0415

            cloud_client = YarboCloudClient()
            firmware_info: dict[str, str] = await cloud_client.get_firmware_version(
                serial_number=robot_serial,
                refresh_token=refresh_token,
                username=username,
            )
            self._latest_version = firmware_info.get("latest_version")
            _LOGGER.debug(
                "Cloud firmware check for %s: latest=%s installed=%s",
                robot_serial,
                self._latest_version,
                self.installed_version,
            )
        except ImportError:
            _LOGGER.debug("python-yarbo cloud client not available — skipping firmware check")
        except Exception:
            _LOGGER.warning(
                "Failed to fetch firmware version from cloud for %s",
                robot_serial,
                exc_info=True,
            )
            # Trigger reauth if this is an auth error
            # (cloud client should raise a specific exception; we handle gracefully)
