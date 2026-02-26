"""Tests for the Yarbo integration __init__.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.yarbo.const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_ROBOT_SERIAL


class TestAsyncSetupEntry:
    """Tests for async_setup_entry.

    TODO: Implement fully in v0.1.0 once the coordinator and client are real.

    These tests verify the integration setup contract:
    - YarboClient is instantiated and connected
    - YarboDataCoordinator is created
    - Data is stored in hass.data
    - Platforms are forwarded
    """

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_yarbo_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test successful integration setup."""
        # TODO: Implement when async_setup_entry calls YarboClient
        # result = await async_setup_entry(hass, mock_config_entry)
        # assert result is True
        # assert DOMAIN in hass.data
        # assert mock_config_entry.entry_id in hass.data[DOMAIN]
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_setup_entry_connection_failure(
        self,
        hass: HomeAssistant,
        mock_yarbo_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that connection failure raises ConfigEntryNotReady."""
        # TODO: Implement
        # mock_yarbo_client.connect.side_effect = YarboConnectionError("refused")
        # with pytest.raises(ConfigEntryNotReady):
        #     await async_setup_entry(hass, mock_config_entry)
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_unload_entry(
        self,
        hass: HomeAssistant,
        mock_yarbo_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that unload disconnects the client."""
        # TODO: Implement
        # await async_setup_entry(hass, mock_config_entry)
        # result = await async_unload_entry(hass, mock_config_entry)
        # assert result is True
        # mock_yarbo_client.disconnect.assert_called_once()
        pass


class TestMultipleRobots:
    """Tests for multi-robot (multiple config entry) scenarios.

    TODO: Implement in v0.1.0

    Each config entry is independent — separate YarboClient and coordinator
    instances per robot. No shared state between entries.
    """

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_two_robots_independent(self, hass: HomeAssistant) -> None:
        """Test that two config entries don't share state."""
        pass
