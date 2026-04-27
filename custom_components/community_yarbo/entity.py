"""Base entity class for Yarbo integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BROKER_HOST, CONF_ROBOT_NAME, CONF_ROBOT_SERIAL, DOMAIN
from .coordinator import YarboDataCoordinator
from .models import YarboTelemetry


class YarboEntity(CoordinatorEntity[YarboDataCoordinator]):
    """Base class for all Yarbo entities.

    Provides:
    - Shared device_info (robot device)
    - Unique ID pattern: {robot_sn}_{entity_key}
    - Coordinator data access helpers
    - Head-type availability gating (override available in subclasses)
    - Entity picture (robot image from integration assets)
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YarboDataCoordinator,
        entity_key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        robot_sn = coordinator._entry.data.get(CONF_ROBOT_SERIAL, "unknown")
        self._attr_unique_id = f"{robot_sn}_{entity_key}"
        self._attr_translation_key = entity_key
        self._entity_key = entity_key

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the robot."""
        entry = self.coordinator._entry
        robot_sn = entry.data.get(CONF_ROBOT_SERIAL, "unknown")
        robot_name = entry.data.get(CONF_ROBOT_NAME, f"Yarbo {robot_sn[-4:]}")
        raw_source = self.coordinator.data
        if isinstance(raw_source, dict):
            raw: dict = raw_source.get("raw", raw_source)
        elif raw_source is not None:
            raw = getattr(raw_source, "raw", {})
        else:
            raw = {}

        broker_host = entry.data.get(CONF_BROKER_HOST)
        return DeviceInfo(
            identifiers={(DOMAIN, robot_sn)},
            name=robot_name,
            manufacturer="Yarbo (Hytech)",
            model="S1",
            sw_version=raw.get("firmware_version") if isinstance(raw, dict) else None,
            configuration_url=f"http://{broker_host}" if broker_host else None,
        )

    @property
    def telemetry(self) -> YarboTelemetry | None:
        """Return the current telemetry object, or None if not available."""
        return self.coordinator.data  # type: ignore[return-value]
