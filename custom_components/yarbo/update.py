"""Update platform for Yarbo integration — firmware update information.

Entity: update.{name}_firmware
- installed_version: read from DeviceMSG/deviceinfo_feedback/ota_feedback MQTT
- latest_version: read from cloud API (requires cloud_enabled option)
- No INSTALL support — OTA is managed by the Yarbo app via AWS Greengrass
"""

from __future__ import annotations

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DEFAULT_CLOUD_ENABLED, DOMAIN, OPT_CLOUD_ENABLED
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


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
    _attr_entity_category = EntityCategory.CONFIG
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

        Returns None when cloud features are disabled (OPT_CLOUD_ENABLED=False)
        or when the cloud has not yet reported a version.
        Populated by coordinator.latest_firmware_version once cloud auth is set up.
        """
        cloud_enabled: bool = self.coordinator._entry.options.get(
            OPT_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED
        )
        if not cloud_enabled:
            return None
        return self.coordinator.latest_firmware_version
