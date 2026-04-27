"""Tests for controller acquisition helper (GlitchTip #147 / GitHub #147)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from yarbo.exceptions import YarboTimeoutError

from custom_components.community_yarbo.controller import async_ensure_controller


@pytest.mark.asyncio
async def test_async_ensure_controller_maps_yarbo_timeout() -> None:
    """YarboTimeoutError from get_controller becomes HomeAssistantError for the UI."""
    client = AsyncMock()
    client.get_controller = AsyncMock(side_effect=YarboTimeoutError("ack timeout"))
    with pytest.raises(HomeAssistantError, match="Timed out waiting"):
        await async_ensure_controller(client, timeout=5.0)
    client.get_controller.assert_awaited_once_with(timeout=5.0)


@pytest.mark.asyncio
async def test_async_ensure_controller_success() -> None:
    client = AsyncMock()
    await async_ensure_controller(client, timeout=3.0)
    client.get_controller.assert_awaited_once_with(timeout=3.0)
