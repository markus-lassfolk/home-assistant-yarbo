"""Tests for the Yarbo switch platform (#12)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yarbo.const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL
from custom_components.yarbo.switch import YarboBuzzerSwitch, YarboPersonDetectSwitch


def _make_coordinator() -> MagicMock:
    """Build a minimal mock coordinator for switch tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.buzzer = AsyncMock()
    coord.client.publish_command = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0002",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.data = None
    return coord


class TestYarboBuzzerSwitch:
    """Tests for the buzzer switch entity (issue #12)."""

    def test_disabled_by_default(self) -> None:
        """Buzzer switch must be disabled by default."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.entity_registry_enabled_default is False

    def test_icon(self) -> None:
        """Buzzer switch must use mdi:volume-high icon."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.icon == "mdi:volume-high"

    def test_translation_key(self) -> None:
        """Translation key must be 'buzzer'."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.translation_key == "buzzer"

    def test_unique_id(self) -> None:
        """Unique ID is based on robot serial."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.unique_id == "TEST0002_buzzer"

    def test_assumed_state(self) -> None:
        """Buzzer switch uses assumed state (no read-back)."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.assumed_state is True

    def test_initial_state_off(self) -> None:
        """Buzzer is off initially."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_calls_buzzer_state_1(self) -> None:
        """turn_on calls client.buzzer(state=1)."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.buzzer.assert_called_once_with(state=1)
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_calls_buzzer_state_0(self) -> None:
        """turn_off calls client.buzzer(state=0)."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()
            await entity.async_turn_off()

        coord.client.buzzer.assert_called_with(state=0)
        assert entity.is_on is False

    @pytest.mark.asyncio
    async def test_state_tracked_from_commands(self) -> None:
        """State is tracked from last command, not from telemetry."""
        coord = _make_coordinator()
        entity = YarboBuzzerSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            assert entity.is_on is False
            await entity.async_turn_on()
            assert entity.is_on is True
            await entity.async_turn_off()
            assert entity.is_on is False


class TestYarboPersonDetectSwitch:
    """Tests for the person detect switch."""

    def test_icon(self) -> None:
        """Person detect uses mdi:account-eye icon."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)
        assert entity.icon == "mdi:account-eye"

    def test_translation_key(self) -> None:
        """Translation key must be 'person_detect'."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)
        assert entity.translation_key == "person_detect"

    @pytest.mark.asyncio
    async def test_turn_on_publishes_enable(self) -> None:
        """turn_on publishes set_person_detect enable=1."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_person_detect", {"enable": 1})
        assert entity.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_publishes_disable(self) -> None:
        """turn_off publishes set_person_detect enable=0."""
        coord = _make_coordinator()
        entity = YarboPersonDetectSwitch(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()
            await entity.async_turn_off()

        coord.client.publish_command.assert_called_with("set_person_detect", {"enable": 0})
        assert entity.is_on is False
