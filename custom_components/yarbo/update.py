"""Update platform for Yarbo integration — firmware update information."""

from __future__ import annotations

import logging

import aiohttp
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

try:
    from yarbo.cloud import YarboCloudClient
except ImportError:  # pragma: no cover
    YarboCloudClient = None

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
        """Fetch latest firmware version from cloud when cloud auth is enabled.

        Uses the stored refresh_token to get a new access_token without requiring
        the user's password. Falls back gracefully if cloud is unavailable.
        """
        entry = self.coordinator._entry
        cloud_enabled = entry.options.get(OPT_CLOUD_ENABLED, False)
        refresh_token = entry.data.get(CONF_CLOUD_REFRESH_TOKEN)

        if not cloud_enabled or not refresh_token or YarboCloudClient is None:
            return

        username = entry.data.get(CONF_CLOUD_USERNAME, "")
        robot_serial = entry.data.get(CONF_ROBOT_SERIAL, "")

        try:
            async with aiohttp.ClientSession(
                headers={"Content-Type": "application/json"}
            ) as session:
                cloud_client = YarboCloudClient(username=username)
                cloud_client._session = session
                cloud_client.auth._session = session
                cloud_client.auth.refresh_token = refresh_token
                await cloud_client.auth.refresh()
                new_refresh_token = cloud_client.auth.refresh_token
                if new_refresh_token != refresh_token:
                    new_data = dict(entry.data)
                    new_data[CONF_CLOUD_REFRESH_TOKEN] = new_refresh_token
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    _LOGGER.debug("Refresh token rotated for %s", robot_serial)
                version_data: dict[str, str] = await cloud_client.get_latest_version()
                self._latest_version = version_data.get("firmwareVersion")
            _LOGGER.debug(
                "Cloud firmware check for %s: latest=%s installed=%s",
                robot_serial,
                self._latest_version,
                self.installed_version,
            )
        except Exception:
            _LOGGER.warning(
                "Failed to fetch firmware version from cloud for %s — token may be expired",
                robot_serial,
                exc_info=True,
            )
