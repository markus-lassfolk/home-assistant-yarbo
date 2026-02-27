"""Update platform for Yarbo integration — firmware update information.

Entity: update.{name}_firmware
- installed_version: read from DeviceMSG/deviceinfo_feedback/ota_feedback MQTT
- latest_version: read from cloud API (requires cloud_enabled option)
- No INSTALL support — OTA is managed by the Yarbo app via AWS Greengrass
"""

from __future__ import annotations

import logging

try:
    from yarbo.cloud import YarboCloudClient
except ImportError:  # pragma: no cover
    YarboCloudClient = None  # type: ignore[assignment,misc]

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    DATA_COORDINATOR,
    DEFAULT_CLOUD_ENABLED,
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
    coordinator: YarboDataCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([YarboFirmwareUpdate(coordinator)])


class YarboFirmwareUpdate(YarboEntity, UpdateEntity):
    """Firmware update information entity (informational only — no install).

    Installed version is sourced from telemetry (deviceinfo_feedback or
    ota_feedback MQTT messages, falling back to top-level firmware_version).

    Latest version comparison is available when cloud features are enabled.
    When cloud is disabled the latest_version property returns None, which
    makes the HA update entity show only the installed version without an
    update-available banner.

    OTA updates are triggered exclusively via the Yarbo app — this entity
    must NOT implement UpdateEntityFeature.INSTALL (safety requirement).
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
        """Return currently installed firmware version from telemetry.

        Checks (in priority order):
        1. deviceinfo_feedback MQTT message
        2. ota_feedback MQTT message
        3. Top-level firmware_version field
        """
        data = self.coordinator.data
        if data is None:
            return None

        if isinstance(data, dict):
            raw: dict[str, object] = data.get("raw", data)
        else:
            raw = getattr(data, "raw", {}) or {}

        if not isinstance(raw, dict):
            return None

        # 1. Try deviceinfo_feedback (preferred — contains current version)
        deviceinfo = raw.get("deviceinfo_feedback") or raw.get("DeviceInfoMSG") or {}
        if isinstance(deviceinfo, dict):
            v = deviceinfo.get("version") or deviceinfo.get("firmware_version")
            if v:
                return str(v)

        # 2. Try ota_feedback (reported after OTA completes)
        ota = raw.get("ota_feedback") or raw.get("OtaMSG") or {}
        if isinstance(ota, dict):
            v = ota.get("version") or ota.get("firmware_version")
            if v:
                return str(v)

        # 3. Fallback to top-level firmware_version key
        v = raw.get("firmware_version")
        return str(v) if v else None

    @property
    def latest_version(self) -> str | None:
        """Return latest available firmware version from cloud API.

        Falls back to installed_version when cloud is disabled or no cached
        version is available — this prevents HA from showing an "update unknown"
        state when the user hasn't configured cloud access.

        Populated via async_update() when cloud_enabled=True and a
        refresh_token is stored in the config entry.
        """
        cloud_enabled: bool = self.coordinator.entry.options.get(
            OPT_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED
        )
        if not cloud_enabled:
            # Cloud disabled — mirror installed version so no update banner appears
            return self.installed_version
        # Cloud enabled: return coordinator-cached latest, falling back to installed
        return self.coordinator.latest_firmware_version or self.installed_version

    async def async_update(self) -> None:
        """Fetch latest firmware version from the Yarbo cloud API.

        Called by HA when the entity needs refreshing (e.g., user presses
        refresh or the scheduled update interval fires).

        Skips the cloud call when:
        - cloud_enabled option is False
        - No refresh_token stored in the config entry
        - YarboCloudClient library is not available
        """
        cloud_enabled: bool = self.coordinator.entry.options.get(
            OPT_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED
        )
        if not cloud_enabled:
            return

        refresh_token: str | None = self.coordinator.entry.data.get(CONF_CLOUD_REFRESH_TOKEN)
        if not refresh_token:
            return

        if YarboCloudClient is None:
            _LOGGER.debug("yarbo.cloud not available — skipping firmware version check")
            return

        username: str = self.coordinator.entry.data.get(CONF_CLOUD_USERNAME, "")
        cloud_client = None
        try:
            cloud_client = YarboCloudClient(username=username, password="")
            # Inject the stored refresh token so auth.refresh() can exchange it
            # for a new access token without requiring the user's password again.
            cloud_client.auth.refresh_token = refresh_token
            await cloud_client.connect()
            result = await cloud_client.get_latest_version()
            if isinstance(result, dict) and "firmwareVersion" in result:
                self._latest_version = str(result["firmwareVersion"])
                self.coordinator.latest_firmware_version = self._latest_version
                _LOGGER.debug("Latest Yarbo firmware from cloud: %s", self._latest_version)
        except Exception as err:
            _LOGGER.warning("Failed to fetch latest Yarbo firmware version: %s", err)
        finally:
            if cloud_client is not None:
                await cloud_client.disconnect()
