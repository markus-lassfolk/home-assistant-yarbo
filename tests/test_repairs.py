"""Tests for Yarbo repair flows (#27)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.yarbo.repairs import (
    ISSUE_CLOUD_TOKEN_EXPIRED,
    ISSUE_CONTROLLER_LOST,
    ISSUE_MQTT_DISCONNECT,
    async_create_cloud_token_expired_issue,
    async_create_controller_lost_issue,
    async_create_fix_flow,
    async_create_mqtt_disconnect_issue,
    async_delete_cloud_token_expired_issue,
    async_delete_controller_lost_issue,
    async_delete_mqtt_disconnect_issue,
)

ENTRY_ID = "test_entry_abc"
ROBOT_NAME = "TestBot"


@pytest.fixture
def mock_hass() -> MagicMock:
    return MagicMock()


class TestIssueConstants:
    """Issue ID constants must be stable — translation keys depend on them."""

    def test_mqtt_disconnect_constant(self) -> None:
        assert ISSUE_MQTT_DISCONNECT == "mqtt_disconnect"

    def test_controller_lost_constant(self) -> None:
        assert ISSUE_CONTROLLER_LOST == "controller_lost"

    def test_cloud_token_expired_constant(self) -> None:
        assert ISSUE_CLOUD_TOKEN_EXPIRED == "cloud_token_expired"


class TestMqttDisconnectRepair:
    """Tests for MQTT disconnect repair issue helpers."""

    def test_create_calls_async_create_issue(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_mqtt_disconnect_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            mock_create.assert_called_once()
            args = mock_create.call_args[0]
            assert args[2] == f"{ISSUE_MQTT_DISCONNECT}_{ENTRY_ID}"

    def test_create_uses_warning_severity(self, mock_hass: MagicMock) -> None:
        from homeassistant.helpers import issue_registry as ir

        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_mqtt_disconnect_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["severity"] == ir.IssueSeverity.WARNING

    def test_create_not_fixable(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_mqtt_disconnect_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["is_fixable"] is False

    def test_create_uses_translation_key(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_mqtt_disconnect_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["translation_key"] == ISSUE_MQTT_DISCONNECT
            assert call_kwargs["translation_placeholders"] == {"name": ROBOT_NAME}

    def test_delete_calls_async_delete_issue(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_delete_issue") as mock_delete:
            async_delete_mqtt_disconnect_issue(mock_hass, ENTRY_ID)
            mock_delete.assert_called_once()
            args = mock_delete.call_args[0]
            assert args[2] == f"{ISSUE_MQTT_DISCONNECT}_{ENTRY_ID}"


class TestControllerLostRepair:
    """Tests for controller lost repair issue helpers."""

    def test_create_calls_async_create_issue(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_controller_lost_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            mock_create.assert_called_once()
            args = mock_create.call_args[0]
            assert args[2] == f"{ISSUE_CONTROLLER_LOST}_{ENTRY_ID}"

    def test_create_uses_error_severity(self, mock_hass: MagicMock) -> None:
        from homeassistant.helpers import issue_registry as ir

        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_controller_lost_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["severity"] == ir.IssueSeverity.ERROR

    def test_create_is_fixable(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_controller_lost_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["is_fixable"] is True

    def test_create_uses_translation_key(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_controller_lost_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["translation_key"] == ISSUE_CONTROLLER_LOST
            assert call_kwargs["translation_placeholders"] == {"name": ROBOT_NAME}

    def test_delete_calls_async_delete_issue(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_delete_issue") as mock_delete:
            async_delete_controller_lost_issue(mock_hass, ENTRY_ID)
            args = mock_delete.call_args[0]
            assert args[2] == f"{ISSUE_CONTROLLER_LOST}_{ENTRY_ID}"


class TestCoordinatorRepairIntegration:
    """Tests for coordinator's repair issue methods (#27)."""

    def _make_coordinator(self) -> object:
        """Build a minimal coordinator-like object for testing repair methods."""
        from custom_components.yarbo.coordinator import YarboDataCoordinator

        with patch(
            "custom_components.yarbo.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ):
            coord = object.__new__(YarboDataCoordinator)
            coord.hass = MagicMock()  # type: ignore[attr-defined]
            entry = MagicMock()
            entry.entry_id = ENTRY_ID
            entry.data = {"robot_name": ROBOT_NAME}
            coord._entry = entry  # type: ignore[attr-defined]
            coord._controller_lost_active = False  # type: ignore[attr-defined]
        return coord

    def test_report_controller_lost_creates_issue(self) -> None:
        coord = self._make_coordinator()
        with patch(
            "custom_components.yarbo.coordinator.async_create_controller_lost_issue"
        ) as mock_create:
            coord.report_controller_lost()  # type: ignore[attr-defined]
            mock_create.assert_called_once_with(
                coord.hass,
                ENTRY_ID,
                ROBOT_NAME,  # type: ignore[attr-defined]
            )

    def test_report_controller_lost_idempotent(self) -> None:
        """Calling report twice should only create the issue once."""
        coord = self._make_coordinator()
        with patch(
            "custom_components.yarbo.coordinator.async_create_controller_lost_issue"
        ) as mock_create:
            coord.report_controller_lost()  # type: ignore[attr-defined]
            coord.report_controller_lost()  # type: ignore[attr-defined]
            assert mock_create.call_count == 1

    def test_resolve_controller_lost_deletes_issue(self) -> None:
        coord = self._make_coordinator()
        coord._controller_lost_active = True  # type: ignore[attr-defined]
        with patch(
            "custom_components.yarbo.coordinator.async_delete_controller_lost_issue"
        ) as mock_delete:
            coord.resolve_controller_lost()  # type: ignore[attr-defined]
            mock_delete.assert_called_once_with(
                coord.hass,
                ENTRY_ID,  # type: ignore[attr-defined]
            )

    def test_resolve_controller_lost_no_op_when_not_active(self) -> None:
        coord = self._make_coordinator()
        with patch(
            "custom_components.yarbo.coordinator.async_delete_controller_lost_issue"
        ) as mock_delete:
            coord.resolve_controller_lost()  # type: ignore[attr-defined]
            mock_delete.assert_not_called()


class TestCloudTokenExpiredRepair:
    """Tests for cloud token expired repair issue helpers (#27)."""

    def test_create_calls_async_create_issue(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_cloud_token_expired_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            mock_create.assert_called_once()
            args = mock_create.call_args[0]
            assert args[2] == f"{ISSUE_CLOUD_TOKEN_EXPIRED}_{ENTRY_ID}"

    def test_create_uses_warning_severity(self, mock_hass: MagicMock) -> None:
        from homeassistant.helpers import issue_registry as ir

        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_cloud_token_expired_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["severity"] == ir.IssueSeverity.WARNING

    def test_create_is_fixable(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_cloud_token_expired_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["is_fixable"] is True

    def test_create_uses_translation_key(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_create_issue") as mock_create:
            async_create_cloud_token_expired_issue(mock_hass, ENTRY_ID, ROBOT_NAME)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["translation_key"] == ISSUE_CLOUD_TOKEN_EXPIRED
            assert call_kwargs["translation_placeholders"] == {"name": ROBOT_NAME}

    def test_delete_calls_async_delete_issue(self, mock_hass: MagicMock) -> None:
        with patch("custom_components.yarbo.repairs.ir.async_delete_issue") as mock_delete:
            async_delete_cloud_token_expired_issue(mock_hass, ENTRY_ID)
            mock_delete.assert_called_once()
            args = mock_delete.call_args[0]
            assert args[2] == f"{ISSUE_CLOUD_TOKEN_EXPIRED}_{ENTRY_ID}"


class TestCreateFixFlow:
    """Tests for async_create_fix_flow (#27)."""

    @pytest.mark.asyncio
    async def test_returns_repair_flow(self, mock_hass: MagicMock) -> None:
        flow = await async_create_fix_flow(mock_hass, "mqtt_disconnect_test_id", None)
        from custom_components.yarbo.repairs import YarboRepairFlow

        assert isinstance(flow, YarboRepairFlow)
