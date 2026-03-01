"""Tests for the Yarbo light platform (#11)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yarbo.const import (
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    HEAD_TYPE_NONE,
    HEAD_TYPE_SNOW_BLOWER,
    LIGHT_CHANNEL_HEAD,
    LIGHT_CHANNELS,
)
from custom_components.yarbo.light import (
    YarboAllLightsGroup,
    YarboChannelLight,
    YarboHeadLight,
)


def _make_coordinator() -> MagicMock:
    """Build a minimal mock coordinator for light tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.light_state = {
        "led_head": 0,
        "led_left_w": 0,
        "led_right_w": 0,
        "body_left_r": 0,
        "body_right_r": 0,
        "tail_left_r": 0,
        "tail_right_r": 0,
    }
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.set_lights = AsyncMock()
    coord.client.set_head_light = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0001",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.data = None
    return coord


class TestYarboAllLightsGroup:
    """Tests for the all-lights group entity (issue #11)."""

    def test_entity_enabled_by_default(self) -> None:
        """Group entity must be enabled by default."""
        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)
        assert entity.entity_registry_enabled_default is True

    def test_unique_id(self) -> None:
        """Unique ID is based on robot serial."""
        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)
        assert entity.unique_id == "TEST0001_lights"

    def test_translation_key(self) -> None:
        """Translation key must be 'lights'."""
        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)
        assert entity.translation_key == "lights"

    def test_initial_state_off(self) -> None:
        """Light is off initially."""
        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_all_channels(self) -> None:
        """turn_on sets all 7 channels to brightness 255."""
        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.set_lights.assert_called_once()
        assert entity.is_on is True
        assert entity.brightness == 255
        # All channels set to 255 in coordinator state
        for ch in LIGHT_CHANNELS:
            assert coord.light_state[ch] == 255

    @pytest.mark.asyncio
    async def test_turn_on_with_brightness(self) -> None:
        """turn_on respects explicit brightness kwarg."""
        from homeassistant.components.light import ATTR_BRIGHTNESS

        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on(**{ATTR_BRIGHTNESS: 128})

        assert entity.brightness == 128
        for ch in LIGHT_CHANNELS:
            assert coord.light_state[ch] == 128

    @pytest.mark.asyncio
    async def test_turn_off_all_channels(self) -> None:
        """turn_off sets all 7 channels to 0."""
        coord = _make_coordinator()
        entity = YarboAllLightsGroup(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_off()

        coord.client.set_lights.assert_called_once()
        assert entity.is_on is False
        assert entity.brightness == 0
        for ch in LIGHT_CHANNELS:
            assert coord.light_state[ch] == 0


class TestYarboChannelLight:
    """Tests for individual LED channel entities (issue #11)."""

    def test_channels_disabled_by_default(self) -> None:
        """Individual channel lights must be disabled by default."""
        coord = _make_coordinator()
        for channel in LIGHT_CHANNELS:
            entity = YarboChannelLight(coord, channel)
            assert entity.entity_registry_enabled_default is False, (
                f"Channel {channel} should be disabled by default"
            )

    def test_seven_channels_created(self) -> None:
        """Exactly 7 channel entities are created."""
        assert len(LIGHT_CHANNELS) == 7

    def test_head_channel_translation_key(self) -> None:
        """led_head channel uses 'led_head' translation key."""
        coord = _make_coordinator()
        entity = YarboChannelLight(coord, LIGHT_CHANNEL_HEAD)
        assert entity.translation_key == "led_head"

    def test_unique_id(self) -> None:
        """Unique ID is based on robot serial and channel."""
        coord = _make_coordinator()
        entity = YarboChannelLight(coord, LIGHT_CHANNEL_HEAD)
        assert entity.unique_id == "TEST0001_light_led_head"

    def test_initial_state_off(self) -> None:
        """Channel light is off initially."""
        coord = _make_coordinator()
        entity = YarboChannelLight(coord, LIGHT_CHANNEL_HEAD)
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_only_this_channel(self) -> None:
        """turn_on only modifies the channel's own slot."""
        coord = _make_coordinator()
        entity = YarboChannelLight(coord, LIGHT_CHANNEL_HEAD)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.set_lights.assert_called_once()
        assert entity.is_on is True
        assert entity.brightness == 255
        assert coord.light_state[LIGHT_CHANNEL_HEAD] == 255
        # Other channels unchanged
        assert coord.light_state["led_left_w"] == 0

    @pytest.mark.asyncio
    async def test_turn_on_with_brightness(self) -> None:
        """Channel turn_on respects brightness kwarg."""
        from homeassistant.components.light import ATTR_BRIGHTNESS

        coord = _make_coordinator()
        entity = YarboChannelLight(coord, LIGHT_CHANNEL_HEAD)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on(**{ATTR_BRIGHTNESS: 64})

        assert entity.brightness == 64
        assert coord.light_state[LIGHT_CHANNEL_HEAD] == 64

    @pytest.mark.asyncio
    async def test_turn_off_only_this_channel(self) -> None:
        """turn_off sets only this channel to 0."""
        coord = _make_coordinator()
        coord.light_state[LIGHT_CHANNEL_HEAD] = 200
        entity = YarboChannelLight(coord, LIGHT_CHANNEL_HEAD)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_off()

        assert entity.is_on is False
        assert entity.brightness == 0
        assert coord.light_state[LIGHT_CHANNEL_HEAD] == 0


class TestYarboHeadLight:
    """Tests for the head light entity."""

    def test_translation_key(self) -> None:
        """Translation key must be head_light."""
        coord = _make_coordinator()
        entity = YarboHeadLight(coord)
        assert entity.translation_key == "head_light"

    def test_available_with_head(self) -> None:
        """Available when a head is attached."""
        coord = _make_coordinator()
        telemetry = MagicMock()
        telemetry.head_type = HEAD_TYPE_SNOW_BLOWER
        coord.data = telemetry
        coord.last_update_success = True
        entity = YarboHeadLight(coord)
        assert entity.available is True

    def test_unavailable_no_head(self) -> None:
        """Unavailable when head_type is none."""
        coord = _make_coordinator()
        telemetry = MagicMock()
        telemetry.head_type = HEAD_TYPE_NONE
        coord.data = telemetry
        coord.last_update_success = True
        entity = YarboHeadLight(coord)
        assert entity.available is False

    @pytest.mark.asyncio
    async def test_turn_on_publishes_command(self) -> None:
        """turn_on calls set_head_light(True)."""
        coord = _make_coordinator()
        entity = YarboHeadLight(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.set_head_light.assert_called_once_with(True)
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_publishes_command(self) -> None:
        """turn_off calls set_head_light(False)."""
        coord = _make_coordinator()
        entity = YarboHeadLight(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()
            await entity.async_turn_off()

        coord.client.set_head_light.assert_called_with(False)
        assert entity.is_on is False
