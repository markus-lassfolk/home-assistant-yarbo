"""Light platform for Yarbo integration — controls 7 LED channels."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from yarbo import YarboLightState

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    HEAD_TYPE_NONE,
    LIGHT_CHANNEL_BODY_LEFT,
    LIGHT_CHANNEL_BODY_RIGHT,
    LIGHT_CHANNEL_HEAD,
    LIGHT_CHANNEL_LEFT_W,
    LIGHT_CHANNEL_RIGHT_W,
    LIGHT_CHANNEL_TAIL_LEFT,
    LIGHT_CHANNEL_TAIL_RIGHT,
    LIGHT_CHANNELS,
)
from .coordinator import YarboDataCoordinator
from .entity import YarboEntity

# Channel translation key mapping — entity_key → translation key
_CHANNEL_TRANSLATION: dict[str, str] = {
    LIGHT_CHANNEL_HEAD: "led_head",
    LIGHT_CHANNEL_LEFT_W: "led_left_w",
    LIGHT_CHANNEL_RIGHT_W: "led_right_w",
    LIGHT_CHANNEL_BODY_LEFT: "led_body_left",
    LIGHT_CHANNEL_BODY_RIGHT: "led_body_right",
    LIGHT_CHANNEL_TAIL_LEFT: "led_tail_left",
    LIGHT_CHANNEL_TAIL_RIGHT: "led_tail_right",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yarbo light entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[LightEntity] = [
        YarboAllLightsGroup(coordinator),
        YarboHeadLight(coordinator),
    ]
    for channel in LIGHT_CHANNELS:
        entities.append(YarboChannelLight(coordinator, channel))
    async_add_entities(entities)


class YarboLight(YarboEntity, LightEntity):
    """Base Yarbo light entity."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.BRIGHTNESS}
    _attr_assumed_state = True  # No read-back from robot

    def __init__(self, coordinator: YarboDataCoordinator, entity_key: str) -> None:
        super().__init__(coordinator, entity_key)
        self._brightness: int | None = None
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return True if light is on."""
        return self._is_on

    @property
    def brightness(self) -> int | None:
        """Return current brightness (0-255)."""
        return self._brightness


class YarboAllLightsGroup(YarboLight):
    """All-lights group entity — sets all 7 channels at once."""

    _attr_translation_key = "lights"

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "lights")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on all lights, optionally at a given brightness."""
        brightness: int = kwargs.get(ATTR_BRIGHTNESS, 255)
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.set_lights(
                YarboLightState(
                    led_head=brightness,
                    led_left_w=brightness,
                    led_right_w=brightness,
                    body_left_r=brightness,
                    body_right_r=brightness,
                    tail_left_r=brightness,
                    tail_right_r=brightness,
                )
            )
            for channel in self.coordinator.light_state:
                self.coordinator.light_state[channel] = brightness
        self._brightness = brightness
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off all lights."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.set_lights(YarboLightState.all_off())
            for channel in self.coordinator.light_state:
                self.coordinator.light_state[channel] = 0
        self._brightness = 0
        self._is_on = False
        self.async_write_ha_state()


class YarboChannelLight(YarboLight):
    """Individual LED channel light entity."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: YarboDataCoordinator, channel: str) -> None:
        super().__init__(coordinator, f"light_{channel}")
        self._channel = channel
        self._attr_translation_key = _CHANNEL_TRANSLATION.get(channel, channel)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on this LED channel."""
        brightness: int = kwargs.get(ATTR_BRIGHTNESS, 255)
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            state_dict = self.coordinator.light_state.copy()
            state_dict[self._channel] = brightness
            await self.coordinator.client.set_lights(YarboLightState(**state_dict))
            self.coordinator.light_state[self._channel] = brightness
        self._brightness = brightness
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off this LED channel."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            state_dict = self.coordinator.light_state.copy()
            state_dict[self._channel] = 0
            await self.coordinator.client.set_lights(YarboLightState(**state_dict))
            self.coordinator.light_state[self._channel] = 0
        self._brightness = 0
        self._is_on = False
        self.async_write_ha_state()


class YarboHeadLight(YarboEntity, LightEntity):
    """Head light control (on/off)."""

    _attr_translation_key = "head_light"
    _attr_icon = "mdi:car-light-high"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.ONOFF}
    _attr_assumed_state = True

    def __init__(self, coordinator: YarboDataCoordinator) -> None:
        super().__init__(coordinator, "head_light")
        self._is_on: bool = False

    @property
    def available(self) -> bool:
        """Only available when a head is attached."""
        if not super().available:
            return False
        if not self.telemetry:
            return False
        return self.telemetry.head_type not in (HEAD_TYPE_NONE, None, "")

    @property
    def is_on(self) -> bool:
        """Return True if head light is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the head light."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command("head_light", {"state": 1})
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the head light."""
        async with self.coordinator.command_lock:
            await self.coordinator.client.get_controller(timeout=5.0)
            await self.coordinator.client.publish_command("head_light", {"state": 0})
        self._is_on = False
        self.async_write_ha_state()
