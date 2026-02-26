"""Base entity class for Yarbo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
        robot_sn = coordinator._entry.data.get("robot_serial", "unknown")
        self._attr_unique_id = f"{robot_sn}_{entity_key}"
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
        robot_sn = entry.data.get("robot_serial", "unknown")
        robot_name = entry.data.get("robot_name", f"Yarbo {robot_sn[-4:]}")

        return DeviceInfo(
            identifiers={(DOMAIN, robot_sn)},
            name=robot_name,
            manufacturer="Yarbo / Hytech",
            model="Yarbo S1",  # TODO: Detect from telemetry
        )

    def _get_telemetry(self) -> dict[str, Any] | None:
        """Return the current telemetry dict, or None if not available."""
        if self.coordinator.data is None:
            return None
        # TODO: Adapt to actual YarboTelemetry type from python-yarbo
        return self.coordinator.data  # type: ignore[return-value]

    def _get_raw(self) -> dict[str, Any]:
        """Return the raw telemetry payload dict."""
        telemetry = self._get_telemetry()
        if telemetry is None:
            return {}
        # TODO: Access .raw attribute on YarboTelemetry
        return getattr(telemetry, "raw", {})
