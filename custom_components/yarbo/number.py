"""Number platform for Yarbo integration — chute velocity control."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    HEAD_TYPE_LAWN_MOWER,
    HEAD_TYPE_LAWN_MOWER_PRO,
    HEAD_TYPE_LEAF_BLOWER,
    HEAD_TYPE_SNOW_BLOWER,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            YarboChuteVelocityNumber(coordinator),
            YarboChuteSteeringWorkNumber(coordinator),
            YarboBladeHeightNumber(coordinator),
            YarboBladeSpeedNumber(coordinator),
            YarboBlowerSpeedNumber(coordinator),
            YarboVolumeNumber(coordinator),
            YarboPlanStartPercentNumber(coordinator, entry),
            # Bug #4: roller converted from switch to speed number
            YarboRollerSpeedNumber(coordinator),
            # #93 — Battery charge limits
            YarboBatteryChargeMinNumber(coordinator),
            YarboBatteryChargeMaxNumber(coordinator),
        ]
    )


class YarboChuteSteeringWorkNumber(YarboEntity, NumberEntity):
    """Chute steering during work — snow blower head only."""

    _attr_translation_key = "chute_steering_work"
    _attr_native_min_value = -90.0
    _attr_native_max_value = 90.0
    _attr_native_step = 5.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:rotate-3d-variant"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "chute_steering_work")
        self._current_angle: float = 0.0

    @property
    def available(self) -> bool:
        """Only available when snow blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_SNOW_BLOWER

    @property
    def native_value(self) -> float:
        """Return the last set chute steering angle."""
        return self._current_angle

    async def async_set_native_value(self, value: float) -> None:
        """Set chute steering angle."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "cmd_chute_streeing_work",
                {"angle": int(value)},
            )
        self._current_angle = value
        self.async_write_ha_state()


class YarboChuteVelocityNumber(YarboEntity, NumberEntity):
    """Chute velocity control — snow blower head only.

    Controls the snow chute direction and speed.
    Negative = left, zero = stop, positive = right.
    Range: -2000 to 2000.
    """

    _attr_translation_key = "chute_velocity"
    _attr_native_min_value = -2000.0
    _attr_native_max_value = 2000.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = None
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:rotate-right"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "chute_velocity")
        self._current_velocity: float = 0.0

    @property
    def available(self) -> bool:
        """Only available when snow blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_SNOW_BLOWER

    @property
    def native_value(self) -> float:
        """Return the last set velocity."""
        return self._current_velocity

    async def async_set_native_value(self, value: float) -> None:
        """Set chute velocity."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            # Note: python-yarbo API uses 'vel' parameter name
            await self.coordinator.client.set_chute(vel=int(value))
        self._current_velocity = value
        self.async_write_ha_state()


class YarboBladeHeightNumber(YarboEntity, NumberEntity):
    """Blade height control for lawn mower heads."""

    _attr_translation_key = "blade_height"
    _attr_native_min_value = 25.0
    _attr_native_max_value = 75.0
    _attr_native_step = 5.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:arrow-expand-vertical"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "blade_height")
        self._current_height: float = 25.0

    @property
    def available(self) -> bool:
        """Only available when lawn mower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in {HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO}

    @property
    def native_value(self) -> float:
        """Return the last set blade height."""
        return self._current_height

    async def async_set_native_value(self, value: float) -> None:
        """Set blade height."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "set_blade_height",
                {"height": int(value)},
            )
        self._current_height = value
        self.async_write_ha_state()


class YarboBladeSpeedNumber(YarboEntity, NumberEntity):
    """Blade speed control for lawn mower heads."""

    _attr_translation_key = "blade_speed"
    _attr_native_min_value = 1000.0
    _attr_native_max_value = 3500.0
    _attr_native_step = 100.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:fan"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "blade_speed")
        self._current_speed: float = 1000.0

    @property
    def available(self) -> bool:
        """Only available when lawn mower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in {HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO}

    @property
    def native_value(self) -> float:
        """Return the last set blade speed."""
        return self._current_speed

    async def async_set_native_value(self, value: float) -> None:
        """Set blade speed."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "set_blade_speed",
                {"speed": int(value)},
            )
        self._current_speed = value
        self.async_write_ha_state()


class YarboBlowerSpeedNumber(YarboEntity, NumberEntity):
    """Leaf blower speed control."""

    _attr_translation_key = "blower_speed"
    _attr_native_min_value = 1.0
    _attr_native_max_value = 10.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:weather-windy"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "blower_speed")
        self._current_speed: float = 1.0

    @property
    def available(self) -> bool:
        """Only available when leaf blower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type == HEAD_TYPE_LEAF_BLOWER

    @property
    def native_value(self) -> float:
        """Return the last set blower speed."""
        return self._current_speed

    async def async_set_native_value(self, value: float) -> None:
        """Set blower speed."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            # TODO: Verify command name against live robot — APK may use "cmd_roller" instead
            await self.coordinator.client.publish_command(
                "blower_speed",
                {"speed": int(value)},
            )
        self._current_speed = value
        self.async_write_ha_state()


class YarboVolumeNumber(YarboEntity, NumberEntity):
    """Volume control."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "volume")
        self._current_volume: float = 0.0

    @property
    def native_value(self) -> float:
        """Return the last set volume."""
        return self._current_volume

    async def async_set_native_value(self, value: float) -> None:
        """Set volume."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "set_sound_param",
                {"vol": int(value)},
            )
        self._current_volume = value
        self.async_write_ha_state()


class YarboPlanStartPercentNumber(YarboEntity, NumberEntity):
    """Plan start percentage helper — persisted in config entry options (#16)."""

    _attr_translation_key = "plan_start_percent"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:percent"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, "plan_start_percent")
        self._entry = entry

    @property
    def native_value(self) -> float:
        """Return the configured plan start percentage."""
        return float(self.coordinator.plan_start_percent)

    async def async_set_native_value(self, value: float) -> None:
        """Update the stored plan start percentage and persist to config entry options."""
        int_val = int(value)
        self.coordinator.set_plan_start_percent(int_val)
        # Persist across HA restarts
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, "plan_start_percent": int_val},
        )
        self.async_write_ha_state()


class YarboRollerSpeedNumber(YarboEntity, NumberEntity):
    """Roller/blade RPM control for lawn mower heads (bug #4 — replaces roller switch)."""

    _attr_translation_key = "roller_speed"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 3500.0
    _attr_native_step = 100.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:saw-blade"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "roller_speed")
        self._current_speed: float = 0.0

    @property
    def available(self) -> bool:
        """Only available when a lawn mower head is installed."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type in {HEAD_TYPE_LAWN_MOWER, HEAD_TYPE_LAWN_MOWER_PRO}

    @property
    def native_value(self) -> float:
        """Return the last set roller speed."""
        return self._current_speed

    async def async_set_native_value(self, value: float) -> None:
        """Set roller speed in RPM."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "cmd_roller",
                {"speed": int(value)},
            )
        self._current_speed = value
        self.async_write_ha_state()


class YarboBatteryChargeMinNumber(YarboEntity, NumberEntity):
    """Minimum battery charge limit (#93)."""

    _attr_translation_key = "battery_charge_min"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 5.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-charging"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery_charge_min")
        self._current_value: float = 0.0

    @property
    def native_value(self) -> float:
        """Return the last set minimum charge limit."""
        return self._current_value

    async def async_set_native_value(self, value: float) -> None:
        """Set minimum battery charge limit."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "set_charge_limit",
                {"min": int(value)},
            )
        self._current_value = value
        self.async_write_ha_state()


class YarboBatteryChargeMaxNumber(YarboEntity, NumberEntity):
    """Maximum battery charge limit (#93)."""

    _attr_translation_key = "battery_charge_max"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 5.0
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-charging"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "battery_charge_max")
        self._current_value: float = 100.0

    @property
    def native_value(self) -> float:
        """Return the last set maximum charge limit."""
        return self._current_value

    async def async_set_native_value(self, value: float) -> None:
        """Set maximum battery charge limit."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command(
                "set_charge_limit",
                {"max": int(value)},
            )
        self._current_value = value
        self.async_write_ha_state()
