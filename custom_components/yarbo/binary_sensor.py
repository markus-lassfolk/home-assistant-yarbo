"""Binary sensor platform for Yarbo integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboChargingSensor(coordinator),
            YarboProblemSensor(coordinator),
        ]
    )


class YarboBinarySensor(YarboEntity, BinarySensorEntity):
    """Base binary sensor for Yarbo."""

    def __init__(self, coordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)


class YarboChargingSensor(YarboBinarySensor):
    """Charging status sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "charging")

    @property
    def is_on(self) -> bool | None:
        """Return True when charging."""
        if not self.telemetry:
            return None
        return self.telemetry.charging_status == 2


class YarboProblemSensor(YarboBinarySensor):
    """Problem indicator sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "problem")

    @property
    def is_on(self) -> bool | None:
        """Return True when an error is present."""
        if not self.telemetry:
            return None
        return self.telemetry.error_code != 0
