"""Tests for Yarbo integration services (#16)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.yarbo.const import DOMAIN
from custom_components.yarbo.services import async_register_services, async_unregister_services


@pytest.fixture
def mock_client_and_coordinator() -> tuple[AsyncMock, MagicMock]:
    """Return a mock client and coordinator."""
    client = AsyncMock()
    client.get_controller = AsyncMock()
    client.publish_raw = AsyncMock()
    client.publish_command = AsyncMock()

    coordinator = MagicMock()
    coordinator.command_lock = asyncio.Lock()
    return client, coordinator


class TestServiceRegistration:
    """Test that services are registered and unregistered correctly."""

    async def test_services_are_registered(self, hass: HomeAssistant) -> None:
        """Test that all Yarbo services are registered."""
        async_register_services(hass)
        assert hass.services.has_service(DOMAIN, "send_command")
        assert hass.services.has_service(DOMAIN, "start_plan")
        assert hass.services.has_service(DOMAIN, "pause")
        assert hass.services.has_service(DOMAIN, "resume")
        assert hass.services.has_service(DOMAIN, "return_to_dock")
        assert hass.services.has_service(DOMAIN, "set_lights")
        assert hass.services.has_service(DOMAIN, "set_chute_velocity")

    async def test_services_not_duplicated(self, hass: HomeAssistant) -> None:
        """Test that calling register twice does not raise."""
        async_register_services(hass)
        async_register_services(hass)
        assert hass.services.has_service(DOMAIN, "start_plan")

    async def test_services_unregistered(self, hass: HomeAssistant) -> None:
        """Test that services are removed on unregister."""
        async_register_services(hass)
        async_unregister_services(hass)
        assert not hass.services.has_service(DOMAIN, "start_plan")
        assert not hass.services.has_service(DOMAIN, "send_command")


class TestStartPlanService:
    """Tests for the yarbo.start_plan service (issue #16)."""

    async def test_start_plan_calls_publish_command(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """start_plan calls publish_command with planId payload."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "start_plan",
                {"device_id": "fake-device-id", "plan_id": "plan-abc-123"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.publish_command.assert_awaited_once_with("start_plan", {"planId": "plan-abc-123"})

    async def test_start_plan_different_plan_ids(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """start_plan passes plan_id correctly for various IDs."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            for plan_id in ["short", "uuid-1234-5678-abcd", "UPPERCASE"]:
                client.reset_mock()
                await hass.services.async_call(
                    DOMAIN,
                    "start_plan",
                    {"device_id": "fake-device-id", "plan_id": plan_id},
                    blocking=True,
                )
                client.publish_command.assert_awaited_once_with("start_plan", {"planId": plan_id})

    async def test_start_plan_raises_for_unknown_device(self, hass: HomeAssistant) -> None:
        """start_plan raises ServiceValidationError for unknown device_id."""
        async_register_services(hass)
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                "start_plan",
                {"device_id": "nonexistent-device", "plan_id": "some-plan"},
                blocking=True,
            )

    async def test_start_plan_acquires_controller(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """start_plan calls get_controller before publish_command."""
        client, coordinator = mock_client_and_coordinator
        call_order: list[str] = []
        client.get_controller.side_effect = lambda **_kw: call_order.append("get_controller")
        client.publish_command.side_effect = lambda *_a, **_kw: call_order.append("publish_command")

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "start_plan",
                {"device_id": "dev-id", "plan_id": "p1"},
                blocking=True,
            )

        assert call_order == ["get_controller", "publish_command"]


class TestGetClientAndCoordinator:
    """Tests for the _get_client_and_coordinator helper."""

    async def test_unknown_device_raises(self, hass: HomeAssistant) -> None:
        """Raises ServiceValidationError when device not found in registry."""
        from custom_components.yarbo.services import _get_client_and_coordinator

        with pytest.raises(ServiceValidationError, match="not found"):
            _get_client_and_coordinator(hass, "nonexistent-device-id")

    async def test_device_not_in_domain_data_raises(self, hass: HomeAssistant) -> None:
        """Raises ServiceValidationError when device found but not in hass.data."""
        from unittest.mock import MagicMock

        from homeassistant.helpers import device_registry as dr

        from custom_components.yarbo.services import _get_client_and_coordinator

        # Mock a device with a config entry that is NOT in hass.data[DOMAIN]
        dev_reg = dr.async_get(hass)
        mock_device = MagicMock()
        mock_device.config_entries = {"unknown-entry-id"}
        mock_device.id = "mock-device-id"

        with patch.object(dev_reg, "async_get", return_value=mock_device):
            # hass.data[DOMAIN] does not have "unknown-entry-id"
            with pytest.raises(ServiceValidationError):
                _get_client_and_coordinator(hass, "mock-device-id")
