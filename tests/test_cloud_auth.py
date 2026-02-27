"""Tests for optional cloud authentication (issue #20)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.yarbo.const import (
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
)


def _make_mock_cloud_client(refresh_token: str = "rt_secret_token") -> MagicMock:
    """Return a mock YarboCloudClient with the real API shape."""
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.auth = MagicMock()
    mock_client.auth.refresh_token = refresh_token
    mock_client.auth.refresh = AsyncMock()
    mock_client.get_latest_version = AsyncMock(
        return_value={"firmwareVersion": "3.11.0", "appVersion": "3.16.3"}
    )
    return mock_client


class TestCloudConfigFlowStep:
    """Tests for async_step_cloud in the config flow."""

    def _make_flow(self, hass: HomeAssistant) -> Any:
        """Create a config flow instance with pre-filled pending data."""
        from custom_components.yarbo.config_flow import YarboConfigFlow

        flow = YarboConfigFlow()
        flow.hass = hass
        flow._pending_data = {
            CONF_ROBOT_NAME: "Yarbo Test",
            CONF_ROBOT_SERIAL: "TEST1234",
            "broker_host": "192.168.1.10",
            "broker_port": 1883,
        }
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        flow.async_show_form = MagicMock(return_value={"type": "form"})
        flow.async_abort = MagicMock(return_value={"type": "abort"})
        return flow

    async def test_cloud_step_skipped_when_email_empty(self, hass: HomeAssistant) -> None:
        """Submitting empty email skips cloud and creates entry without cloud data."""
        flow = self._make_flow(hass)
        result = await flow.async_step_cloud(
            user_input={"cloud_username": "", "cloud_password": ""}
        )
        assert result["type"] == "create_entry"
        call_kwargs: dict[str, Any] = flow.async_create_entry.call_args.kwargs
        assert CONF_CLOUD_USERNAME not in call_kwargs.get("data", {})
        assert CONF_CLOUD_REFRESH_TOKEN not in call_kwargs.get("data", {})

    async def test_cloud_step_skipped_when_password_empty(self, hass: HomeAssistant) -> None:
        """Submitting email but no password also skips cloud auth."""
        flow = self._make_flow(hass)
        result = await flow.async_step_cloud(
            user_input={"cloud_username": "user@example.com", "cloud_password": ""}
        )
        assert result["type"] == "create_entry"

    async def test_cloud_step_shows_form_on_first_call(self, hass: HomeAssistant) -> None:
        """Calling async_step_cloud with no input shows the form."""
        flow = self._make_flow(hass)
        result = await flow.async_step_cloud(user_input=None)
        assert result["type"] == "form"
        flow.async_show_form.assert_called_once()
        assert flow.async_show_form.call_args.kwargs.get("step_id") == "cloud"

    async def test_cloud_auth_success_stores_refresh_token(self, hass: HomeAssistant) -> None:
        """Successful cloud auth stores refresh_token (not password) in entry data."""
        flow = self._make_flow(hass)
        mock_client = _make_mock_cloud_client(refresh_token="rt_secret_token")

        with patch(
            "custom_components.yarbo.config_flow.YarboCloudClient",
            return_value=mock_client,
        ):
            result = await flow.async_step_cloud(
                user_input={"cloud_username": "user@example.com", "cloud_password": "s3cr3t"}
            )

        assert result["type"] == "create_entry"
        mock_client.connect.assert_awaited_once()
        mock_client.disconnect.assert_awaited_once()
        call_kwargs = flow.async_create_entry.call_args.kwargs
        data = call_kwargs.get("data", {})
        assert data.get(CONF_CLOUD_USERNAME) == "user@example.com"
        assert data.get(CONF_CLOUD_REFRESH_TOKEN) == "rt_secret_token"
        # Password must NOT be stored
        assert "cloud_password" not in data

    async def test_cloud_auth_failure_shows_error(self, hass: HomeAssistant) -> None:
        """Failed cloud auth shows error form without creating entry."""
        flow = self._make_flow(hass)
        mock_client = _make_mock_cloud_client()
        mock_client.connect = AsyncMock(side_effect=Exception("Invalid credentials"))

        with patch(
            "custom_components.yarbo.config_flow.YarboCloudClient",
            return_value=mock_client,
        ):
            result = await flow.async_step_cloud(
                user_input={"cloud_username": "bad@example.com", "cloud_password": "wrong"}
            )

        assert result["type"] == "form"
        errors = flow.async_show_form.call_args.kwargs.get("errors", {})
        assert errors.get("base") == "cloud_auth_failed"
        flow.async_create_entry.assert_not_called()


class TestReauthFlow:
    """Tests for the reauth config flow (cloud token expiry)."""

    def _make_reauth_flow(self, hass: HomeAssistant) -> tuple[Any, MagicMock]:
        """Create a config flow in reauth context."""
        from custom_components.yarbo.config_flow import YarboConfigFlow

        flow = YarboConfigFlow()
        flow.hass = hass

        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_CLOUD_USERNAME: "user@example.com",
            CONF_CLOUD_REFRESH_TOKEN: "old_refresh_token",
        }
        mock_entry.entry_id = "test_reauth_entry"
        flow._get_reauth_entry = MagicMock(return_value=mock_entry)
        flow.async_show_form = MagicMock(return_value={"type": "form"})
        flow.async_abort = MagicMock(return_value={"type": "abort"})

        return flow, mock_entry

    async def test_reauth_confirm_shows_form(self, hass: HomeAssistant) -> None:
        """Reauth confirm step shows password form."""
        flow, _ = self._make_reauth_flow(hass)
        result = await flow.async_step_reauth_confirm(user_input=None)
        assert result["type"] == "form"
        assert flow.async_show_form.call_args.kwargs.get("step_id") == "reauth_confirm"

    async def test_reauth_confirm_success_updates_token(self, hass: HomeAssistant) -> None:
        """Successful reauth updates refresh_token in config entry."""
        flow, _mock_entry = self._make_reauth_flow(hass)
        flow.hass.config_entries = MagicMock()
        flow.hass.config_entries.async_update_entry = MagicMock()
        flow.hass.config_entries.async_reload = AsyncMock()

        mock_client = _make_mock_cloud_client(refresh_token="new_token")

        with patch(
            "custom_components.yarbo.config_flow.YarboCloudClient",
            return_value=mock_client,
        ):
            result = await flow.async_step_reauth_confirm(
                user_input={"cloud_password": "newpassword"}
            )

        assert result["type"] == "abort"
        flow.async_abort.assert_called_once_with(reason="reauth_successful")
        flow.hass.config_entries.async_update_entry.assert_called_once()
        # Verify the new token is in the updated data
        update_call = flow.hass.config_entries.async_update_entry.call_args
        new_data = update_call.kwargs.get("data") or (
            update_call.args[1] if len(update_call.args) > 1 else {}
        )
        assert new_data.get(CONF_CLOUD_REFRESH_TOKEN) == "new_token"

    async def test_reauth_confirm_failure_shows_error(self, hass: HomeAssistant) -> None:
        """Failed reauth shows error without updating entry."""
        flow, _ = self._make_reauth_flow(hass)
        mock_client = _make_mock_cloud_client()
        mock_client.connect = AsyncMock(side_effect=Exception("Auth failed"))

        with patch(
            "custom_components.yarbo.config_flow.YarboCloudClient",
            return_value=mock_client,
        ):
            result = await flow.async_step_reauth_confirm(
                user_input={"cloud_password": "wrongpass"}
            )

        assert result["type"] == "form"
        errors = flow.async_show_form.call_args.kwargs.get("errors", {})
        assert errors.get("base") == "cloud_auth_failed"


class TestFirmwareUpdate:
    """Tests for cloud firmware version in update.py."""

    async def test_latest_version_returns_installed_when_no_cloud(
        self, hass: HomeAssistant
    ) -> None:
        """latest_version returns installed_version (None) when cloud is not configured."""
        from custom_components.yarbo.update import YarboFirmwareUpdate

        coordinator = MagicMock()
        coordinator.entry = MagicMock()
        coordinator.entry.data = {}
        coordinator.entry.options = {}
        coordinator.data = None

        entity = YarboFirmwareUpdate(coordinator)
        # Cloud disabled → latest_version mirrors installed_version (both None here)
        assert entity.latest_version is None
        assert entity.installed_version is None

    async def test_latest_version_falls_back_to_installed(self, hass: HomeAssistant) -> None:
        """When no cloud version cached, latest_version mirrors installed_version."""
        from custom_components.yarbo.update import YarboFirmwareUpdate

        coordinator = MagicMock()
        coordinator.entry = MagicMock()
        coordinator.entry.data = {}
        coordinator.entry.options = {}
        mock_telemetry = MagicMock()
        mock_telemetry.raw = {"firmware_version": "1.2.3"}
        coordinator.data = mock_telemetry

        entity = YarboFirmwareUpdate(coordinator)
        assert entity.latest_version == entity.installed_version

    async def test_async_update_skipped_when_cloud_disabled(self, hass: HomeAssistant) -> None:
        """async_update does not call cloud API when cloud_enabled is False."""
        from custom_components.yarbo.update import YarboFirmwareUpdate

        coordinator = MagicMock()
        coordinator.entry = MagicMock()
        coordinator.entry.data = {CONF_CLOUD_REFRESH_TOKEN: "some_token"}
        coordinator.entry.options = {"cloud_enabled": False}
        coordinator.data = None

        entity = YarboFirmwareUpdate(coordinator)
        with patch("custom_components.yarbo.update.YarboCloudClient") as mock_cloud_cls:
            await entity.async_update()
            mock_cloud_cls.assert_not_called()

    async def test_async_update_skipped_when_no_token(self, hass: HomeAssistant) -> None:
        """async_update does not call cloud API when no refresh_token is stored."""
        from custom_components.yarbo.update import YarboFirmwareUpdate

        coordinator = MagicMock()
        coordinator.entry = MagicMock()
        coordinator.entry.data = {}  # no token
        coordinator.entry.options = {"cloud_enabled": True}
        coordinator.data = None

        entity = YarboFirmwareUpdate(coordinator)
        with patch("custom_components.yarbo.update.YarboCloudClient") as mock_cloud_cls:
            await entity.async_update()
            mock_cloud_cls.assert_not_called()

    async def test_async_update_fetches_latest_version(self, hass: HomeAssistant) -> None:
        """async_update fetches and stores latest firmware version from cloud."""

        from custom_components.yarbo.update import YarboFirmwareUpdate

        coordinator = MagicMock()
        coordinator.entry = MagicMock()
        coordinator.entry.data = {
            CONF_CLOUD_REFRESH_TOKEN: "valid_token",
            CONF_CLOUD_USERNAME: "user@example.com",
            CONF_ROBOT_SERIAL: "TEST1234",
        }
        coordinator.entry.options = {"cloud_enabled": True}
        coordinator.data = None

        entity = YarboFirmwareUpdate(coordinator)

        mock_client = _make_mock_cloud_client()
        mock_client.get_latest_version = AsyncMock(
            return_value={"firmwareVersion": "3.11.0", "appVersion": "3.16.3"}
        )

        with patch("custom_components.yarbo.update.YarboCloudClient", return_value=mock_client):
            await entity.async_update()

        assert entity._latest_version == "3.11.0"
        assert entity.latest_version == "3.11.0"
