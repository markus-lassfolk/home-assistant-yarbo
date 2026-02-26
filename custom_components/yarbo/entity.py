"""Base entity class for Yarbo integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from yarbo import YarboTelemetry

from .const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL, DOMAIN
from .coordinator import YarboDataCoordinator


class YarboEntity(CoordinatorEntity[YarboDataCoordinator]):
    """Base class for all Yarbo entities.

    Provides:
    - Shared device_info (robot device)
    - Unique ID pattern: {robot_sn}_{entity_key}
    - Coordinator data access helpers
    - Head-type availability gating (override available in subclasses)

    TODO: Flesh out in v0.1.0
    - Add device_info with robot and data center entries
    - Add entity_picture support
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
        """Return device information for the robot.

        TODO: Implement in v0.1.0
        - Use robot serial from coordinator config entry
        - Include manufacturer, model, sw_version
        - Set via_device for the data center device
        """
        entry = self.coordinator._entry
        robot_sn = entry.data.get(CONF_ROBOT_SERIAL, "unknown")
        robot_name = entry.data.get(CONF_ROBOT_NAME, f"Yarbo {robot_sn[-4:]}")
        raw = self.coordinator.data.raw if self.coordinator.data else {}

        return DeviceInfo(
            identifiers={(DOMAIN, robot_sn)},
            name=robot_name,
            manufacturer="Yarbo (Hytech)",
            model="S1",
            sw_version=raw.get("firmware_version"),
        )

    @property
    def telemetry(self) -> YarboTelemetry | None:
        """Return the current telemetry object, or None if not available."""
        return self.coordinator.data
