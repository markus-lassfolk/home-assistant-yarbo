"""Tests for the Yarbo select platform."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.yarbo.const import CONF_ROBOT_NAME, CONF_ROBOT_SERIAL
from custom_components.yarbo.select import YarboPlanSelect, YarboTurnTypeSelect


def _make_coordinator() -> MagicMock:
    """Build a minimal mock coordinator for select tests."""
    coord = MagicMock()
    coord.command_lock = asyncio.Lock()
    coord.client = MagicMock()
    coord.client.get_controller = AsyncMock()
    coord.client.publish_command = AsyncMock()
    coord._entry = MagicMock()
    coord._entry.data = {
        CONF_ROBOT_SERIAL: "TEST0006",
        CONF_ROBOT_NAME: "TestBot",
    }
    coord._entry.options = {}
    coord.plan_options = ["Front Yard", "Back Yard"]
    coord.active_plan_id = "plan-1"
    coord.plan_name_for_id = MagicMock(return_value="Front Yard")
    coord.plan_id_for_name = MagicMock(
        side_effect=lambda name: {"Front Yard": "plan-1", "Back Yard": "plan-2"}.get(name)
    )
    coord.start_plan = AsyncMock()
    return coord


class TestYarboPlanSelect:
    """Tests for the work plan select entity."""

    def test_options(self) -> None:
        """Options are derived from coordinator plans."""
        coord = _make_coordinator()
        entity = YarboPlanSelect(coord)
        assert entity.options == ["Front Yard", "Back Yard"]

    def test_current_option(self) -> None:
        """Current option is derived from active plan id."""
        coord = _make_coordinator()
        entity = YarboPlanSelect(coord)
        assert entity.current_option == "Front Yard"
        coord.plan_name_for_id.assert_called_once_with("plan-1")

    @pytest.mark.asyncio
    async def test_select_option_starts_plan(self) -> None:
        """Selecting an option starts the matching plan."""
        coord = _make_coordinator()
        entity = YarboPlanSelect(coord)
        await entity.async_select_option("Back Yard")
        coord.start_plan.assert_awaited_once_with("plan-2")

    @pytest.mark.asyncio
    async def test_unknown_option_raises(self) -> None:
        """Unknown plan names raise HomeAssistantError."""
        coord = _make_coordinator()
        coord.plan_id_for_name = MagicMock(return_value=None)
        entity = YarboPlanSelect(coord)
        with pytest.raises(HomeAssistantError):
            await entity.async_select_option("Unknown")


class TestYarboTurnTypeSelect:
    """Tests for the turn type select entity."""

    def test_options(self) -> None:
        """Options include the required turn types."""
        coord = _make_coordinator()
        entity = YarboTurnTypeSelect(coord)
        assert list(entity.options) == ["u_turn", "three_point", "zero_radius"]

    @pytest.mark.asyncio
    async def test_select_option_publishes_command(self) -> None:
        """Selecting a turn type sends set_turn_type."""
        coord = _make_coordinator()
        entity = YarboTurnTypeSelect(coord)

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_select_option("three_point")

        coord.client.get_controller.assert_called_once_with(timeout=5.0)
        coord.client.publish_command.assert_called_once_with("set_turn_type", {"turn_type": 1})
        assert entity.current_option == "three_point"

    @pytest.mark.asyncio
    async def test_unknown_option_raises(self) -> None:
        """Unknown option raises HomeAssistantError."""
        coord = _make_coordinator()
        entity = YarboTurnTypeSelect(coord)
        with pytest.raises(HomeAssistantError):
            await entity.async_select_option("spin")
