"""Tests for the Yarbo config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.yarbo.const import CONF_BROKER_HOST, CONF_BROKER_PORT, DOMAIN

from .conftest import MOCK_BROKER_HOST, MOCK_BROKER_MAC, MOCK_ROBOT_SERIAL


class TestManualConfigFlow:
    """Tests for the manual (user) config flow step.

    TODO: Implement fully in v0.1.0.

    Flow: user → mqtt_test → name → (cloud) → create_entry
    """

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_user_step_shows_form(self, hass: HomeAssistant) -> None:
        """Test that the user step shows the broker IP form."""
        # TODO: Implement
        # result = await hass.config_entries.flow.async_init(
        #     DOMAIN, context={"source": config_entries.SOURCE_USER}
        # )
        # assert result["type"] == FlowResultType.FORM
        # assert result["step_id"] == "user"
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_user_step_creates_entry(self, hass: HomeAssistant) -> None:
        """Test full manual config flow creates a config entry."""
        # TODO: Implement with mock MQTT validation
        # with patch(
        #     "custom_components.yarbo.config_flow.YarboLocalClient",
        # ) as mock_client_cls:
        #     mock_client = mock_client_cls.return_value
        #     mock_client.probe = AsyncMock(return_value=MOCK_ROBOT_SERIAL)
        #
        #     result = await hass.config_entries.flow.async_init(...)
        #     result = await hass.config_entries.flow.async_configure(
        #         result["flow_id"],
        #         {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: 1883},
        #     )
        #     assert result["type"] == FlowResultType.CREATE_ENTRY
        #     assert result["data"][CONF_BROKER_HOST] == MOCK_BROKER_HOST
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_user_step_cannot_connect(self, hass: HomeAssistant) -> None:
        """Test that connection failure shows an error."""
        # TODO: Implement
        # errors should contain "base": "cannot_connect"
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_user_step_no_telemetry(self, hass: HomeAssistant) -> None:
        """Test that missing telemetry (robot off) shows an error."""
        # TODO: Implement
        # errors should contain "base": "no_telemetry"
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_duplicate_robot_aborts(self, hass: HomeAssistant) -> None:
        """Test that configuring the same robot SN twice aborts."""
        # TODO: Implement
        # result type should be ABORT with reason "already_configured"
        pass


class TestDhcpDiscoveryFlow:
    """Tests for DHCP auto-discovery config flow.

    TODO: Implement in v0.1.0.

    Triggered when a device with MAC OUI C8:FE:0F:* appears.
    Flow: dhcp → confirm → mqtt_test → name → create_entry
    """

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_dhcp_discovery_shows_confirm(self, hass: HomeAssistant) -> None:
        """Test that DHCP discovery shows a confirmation form."""
        # TODO: Implement
        # discovery_info = dhcp.DhcpServiceInfo(
        #     ip=MOCK_BROKER_HOST,
        #     macaddress=MOCK_BROKER_MAC,
        #     hostname="yarbo-dc",
        # )
        # result = await hass.config_entries.flow.async_init(
        #     DOMAIN,
        #     context={"source": config_entries.SOURCE_DHCP},
        #     data=discovery_info,
        # )
        # assert result["type"] == FlowResultType.FORM
        # assert result["step_id"] == "confirm"
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_dhcp_discovery_already_configured(
        self, hass: HomeAssistant
    ) -> None:
        """Test that DHCP discovery aborts if robot is already configured."""
        pass


class TestOptionsFlow:
    """Tests for the Yarbo options flow.

    TODO: Implement in v0.1.0.

    Options: telemetry_throttle, auto_controller, cloud_enabled, activity_personality
    """

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_options_flow_shows_form(self, hass: HomeAssistant) -> None:
        """Test that the options flow shows the options form."""
        pass

    @pytest.mark.skip(reason="Stub — implement in v0.1.0")
    async def test_options_flow_saves_options(self, hass: HomeAssistant) -> None:
        """Test that options are saved correctly."""
        pass
