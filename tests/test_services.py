"""Tests for Yarbo integration services (#16)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.yarbo.const import DOMAIN, HEAD_TYPE_LEAF_BLOWER, HEAD_TYPE_SNOW_BLOWER
from custom_components.yarbo.services import async_register_services, async_unregister_services


@pytest.fixture
def mock_client_and_coordinator() -> tuple[AsyncMock, MagicMock]:
    """Return a mock client and coordinator."""
    client = AsyncMock()
    client.get_controller = AsyncMock()
    client.publish_raw = AsyncMock()
    client.start_plan = AsyncMock()
    client.return_to_dock = AsyncMock()
    client.pause_planning = AsyncMock()
    client.resume = AsyncMock()
    client.set_velocity = AsyncMock()
    client.start_waypoint = AsyncMock()
    client.delete_plan = AsyncMock()
    client.delete_all_plans = AsyncMock()
    client.erase_map = AsyncMock()
    client.map_recovery = AsyncMock()
    client.save_current_map = AsyncMock()
    client.save_map_backup = AsyncMock()

    coordinator = MagicMock()
    coordinator.client = client
    coordinator.command_lock = asyncio.Lock()
    telemetry = MagicMock()
    telemetry.head_type = HEAD_TYPE_SNOW_BLOWER
    coordinator.data = telemetry
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
        assert hass.services.has_service(DOMAIN, "manual_drive")
        assert hass.services.has_service(DOMAIN, "go_to_waypoint")
        assert hass.services.has_service(DOMAIN, "delete_plan")
        assert hass.services.has_service(DOMAIN, "delete_all_plans")

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

    async def test_start_plan_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """start_plan calls client.start_plan with plan_id and percent."""
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
        client.start_plan.assert_awaited_once_with(
            "plan-abc-123", percent=coordinator.plan_start_percent
        )

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
                client.start_plan.assert_awaited_once_with(
                    plan_id,
                    percent=coordinator.plan_start_percent,
                )

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
        """start_plan calls get_controller before start_plan."""
        client, coordinator = mock_client_and_coordinator
        call_order: list[str] = []

        async def _get_controller(**_kw: Any) -> None:
            call_order.append("get_controller")

        client.get_controller.side_effect = _get_controller

        async def _start_plan(*_a: Any, **_kw: Any) -> None:
            call_order.append("start_plan")

        client.start_plan.side_effect = _start_plan

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

        assert call_order == ["get_controller", "start_plan"]


class TestSendCommandService:
    """Tests for the yarbo.send_command service and head validation."""

    async def test_send_command_passes_command(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """send_command passes the command through to publish_raw."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "send_command",
                {"device_id": "dev-id", "command": "read_clean_area", "payload": {}},
                blocking=True,
            )

        client.publish_raw.assert_awaited_once_with("read_clean_area", {})

    async def test_send_command_rejects_wrong_head_type(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """send_command rejects head-specific commands on wrong head type."""
        client, coordinator = mock_client_and_coordinator
        coordinator.data.head_type = HEAD_TYPE_SNOW_BLOWER

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            with pytest.raises(ServiceValidationError):
                await hass.services.async_call(
                    DOMAIN,
                    "send_command",
                    {"device_id": "dev-id", "command": "cmd_roller", "payload": {}},
                    blocking=True,
                )

    async def test_send_command_allows_correct_head_type(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """send_command allows head-specific commands on matching head type."""
        client, coordinator = mock_client_and_coordinator
        coordinator.data.head_type = HEAD_TYPE_LEAF_BLOWER

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "send_command",
                {"device_id": "dev-id", "command": "cmd_roller", "payload": {}},
                blocking=True,
            )

        client.publish_raw.assert_awaited_once_with("cmd_roller", {})


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

        dev_reg = dr.async_get(hass)
        mock_device = MagicMock()
        mock_device.config_entries = {"unknown-entry-id"}
        mock_device.id = "mock-device-id"

        with patch.object(dev_reg, "async_get", return_value=mock_device):
            with pytest.raises(ServiceValidationError):
                _get_client_and_coordinator(hass, "mock-device-id")


class TestManualDriveService:
    """Tests for the yarbo.manual_drive service."""

    async def test_manual_drive_uses_set_velocity(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """manual_drive calls client.set_velocity with linear and angular values."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "manual_drive",
                {"device_id": "fake-device-id", "linear": 0.5, "angular": -0.25},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.set_velocity.assert_awaited_once_with(0.5, -0.25)


class TestGoToWaypointService:
    """Tests for the yarbo.go_to_waypoint service."""

    async def test_go_to_waypoint_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """go_to_waypoint calls start_waypoint with index."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "go_to_waypoint",
                {"device_id": "fake-device-id", "index": 3},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.start_waypoint.assert_awaited_once_with(index=3)


class TestDeletePlanService:
    """Tests for the yarbo.delete_plan service."""

    async def test_delete_plan_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """delete_plan calls client.delete_plan(plan_id, confirm=True)."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "delete_plan",
                {"device_id": "fake-device-id", "plan_id": "plan-7"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.delete_plan.assert_awaited_once_with("plan-7", confirm=True)


class TestDeleteAllPlansService:
    """Tests for the yarbo.delete_all_plans service."""

    async def test_delete_all_plans_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """delete_all_plans calls client.delete_all_plans(confirm=True)."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "delete_all_plans",
                {"device_id": "fake-device-id"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.delete_all_plans.assert_awaited_once_with(confirm=True)


class TestMapManagementServices:
    """Tests for map management services (issue #115)."""

    async def test_erase_map_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """erase_map calls client.erase_map(confirm=True)."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "erase_map",
                {"device_id": "fake-device-id"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.erase_map.assert_awaited_once_with(confirm=True)

    async def test_map_recovery_without_map_id(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """map_recovery without map_id calls client.map_recovery(map_id=None, confirm=True)."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "map_recovery",
                {"device_id": "fake-device-id"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.map_recovery.assert_awaited_once_with(map_id=None, confirm=True)

    async def test_map_recovery_with_map_id(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """map_recovery with map_id calls client.map_recovery(map_id=..., confirm=True)."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "map_recovery",
                {"device_id": "fake-device-id", "map_id": "map-42"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.map_recovery.assert_awaited_once_with(map_id="map-42", confirm=True)

    async def test_save_current_map_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """save_current_map calls save_current_map."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "save_current_map",
                {"device_id": "fake-device-id"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.save_current_map.assert_awaited_once_with()

    async def test_save_map_backup_calls_typed_method(
        self,
        hass: HomeAssistant,
        mock_client_and_coordinator: tuple[AsyncMock, MagicMock],
    ) -> None:
        """save_map_backup calls save_map_backup."""
        client, coordinator = mock_client_and_coordinator

        with patch(
            "custom_components.yarbo.services._get_client_and_coordinator",
            return_value=(client, coordinator),
        ):
            async_register_services(hass)
            await hass.services.async_call(
                DOMAIN,
                "save_map_backup_and_get_all_map_backup_nameandid",
                {"device_id": "fake-device-id"},
                blocking=True,
            )

        client.get_controller.assert_awaited_once_with(timeout=5.0)
        client.save_map_backup.assert_awaited_once_with()

    async def test_map_services_registered(self, hass: HomeAssistant) -> None:
        """All map management services are registered."""
        async_register_services(hass)
        assert hass.services.has_service(DOMAIN, "erase_map")
        assert hass.services.has_service(DOMAIN, "map_recovery")
        assert hass.services.has_service(DOMAIN, "save_current_map")
        assert hass.services.has_service(DOMAIN, "save_map_backup_and_get_all_map_backup_nameandid")
