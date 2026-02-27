"""Tests for the Yarbo firmware update entity (#25)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yarbo.const import (
    CONF_CLOUD_REFRESH_TOKEN,
    CONF_CLOUD_USERNAME,
    DEFAULT_CLOUD_ENABLED,
    OPT_CLOUD_ENABLED,
)
from custom_components.yarbo.update import YarboFirmwareUpdate

from .conftest import MOCK_ROBOT_SERIAL


def _make_coordinator(data: Any = None, options: dict | None = None) -> MagicMock:
    """Return a minimal mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = data
    entry = MagicMock()
    entry.data = {"robot_serial": MOCK_ROBOT_SERIAL, "robot_name": "TestBot"}
    entry.options = options or {}
    coordinator._entry = entry
    coordinator.entry = entry
    return coordinator


def _make_entity(coordinator: MagicMock) -> YarboFirmwareUpdate:
    """Construct entity without calling CoordinatorEntity.__init__ HA machinery."""
    with patch.object(YarboFirmwareUpdate, "__init__", lambda self, c: None):
        entity: YarboFirmwareUpdate = object.__new__(YarboFirmwareUpdate)
    entity.coordinator = coordinator  # type: ignore[attr-defined]
    return entity


class TestInstalledVersion:
    """Tests for YarboFirmwareUpdate.installed_version."""

    def test_returns_none_when_no_data(self) -> None:
        coordinator = _make_coordinator(data=None)
        entity = _make_entity(coordinator)
        assert entity.installed_version is None

    def test_reads_deviceinfo_feedback_version(self) -> None:
        data = MagicMock()
        data.raw = {"deviceinfo_feedback": {"version": "1.2.3"}}
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version == "1.2.3"

    def test_reads_ota_feedback_version(self) -> None:
        data = MagicMock()
        data.raw = {"ota_feedback": {"version": "2.0.0"}}
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version == "2.0.0"

    def test_reads_top_level_firmware_version(self) -> None:
        data = MagicMock()
        data.raw = {"firmware_version": "0.9.1"}
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version == "0.9.1"

    def test_prefers_deviceinfo_feedback_over_ota(self) -> None:
        data = MagicMock()
        data.raw = {
            "deviceinfo_feedback": {"version": "3.0.0"},
            "ota_feedback": {"version": "2.9.9"},
        }
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version == "3.0.0"

    def test_falls_back_to_ota_when_deviceinfo_missing(self) -> None:
        data = MagicMock()
        data.raw = {"ota_feedback": {"version": "1.5.0"}}
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version == "1.5.0"

    def test_returns_none_when_raw_is_empty(self) -> None:
        data = MagicMock()
        data.raw = {}
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version is None

    def test_dict_data_uses_raw_subkey(self) -> None:
        data = {"raw": {"firmware_version": "5.0.0"}}
        coordinator = _make_coordinator(data=data)
        entity = _make_entity(coordinator)
        assert entity.installed_version == "5.0.0"


class TestLatestVersion:
    """Tests for YarboFirmwareUpdate.latest_version."""

    def test_returns_none_when_cloud_disabled(self) -> None:
        coordinator = _make_coordinator(options={OPT_CLOUD_ENABLED: False})
        coordinator.latest_firmware_version = "9.9.9"
        entity = _make_entity(coordinator)
        assert entity.latest_version is None

    def test_returns_none_by_default_cloud_disabled(self) -> None:
        coordinator = _make_coordinator(options={})
        coordinator.latest_firmware_version = "9.9.9"
        entity = _make_entity(coordinator)
        # DEFAULT_CLOUD_ENABLED is False
        assert DEFAULT_CLOUD_ENABLED is False
        assert entity.latest_version is None

    def test_returns_coordinator_version_when_cloud_enabled(self) -> None:
        coordinator = _make_coordinator(options={OPT_CLOUD_ENABLED: True})
        coordinator.latest_firmware_version = "4.2.0"
        entity = _make_entity(coordinator)
        assert entity.latest_version == "4.2.0"

    def test_returns_none_when_cloud_enabled_but_no_version_fetched(self) -> None:
        coordinator = _make_coordinator(options={OPT_CLOUD_ENABLED: True})
        coordinator.latest_firmware_version = None
        entity = _make_entity(coordinator)
        assert entity.latest_version is None


class TestEntityMetadata:
    """Tests for static entity metadata.

    HA's entity metaclass transforms ``_attr_*`` class assignments into
    descriptors and stores the underlying value under ``__attr_*``.  We
    read the stored value directly to verify the metadata that will be
    used at runtime.
    """

    def test_entity_category_is_diagnostic(self) -> None:
        from homeassistant.helpers.entity import EntityCategory

        # HA metaclass stores the value at __attr_entity_category
        stored = YarboFirmwareUpdate.__dict__.get("__attr_entity_category")
        assert stored == EntityCategory.DIAGNOSTIC

    def test_no_install_feature(self) -> None:
        from homeassistant.components.update import UpdateEntityFeature

        stored = YarboFirmwareUpdate.__dict__.get("__attr_supported_features")
        assert stored == UpdateEntityFeature(0)

    def test_auto_update_is_false(self) -> None:
        stored = YarboFirmwareUpdate.__dict__.get("__attr_auto_update")
        assert stored is False


class TestAsyncUpdate:
    """Tests for YarboFirmwareUpdate.async_update — firmwareVersion null/missing."""

    def _make_cloud_enabled_entity(self) -> tuple[YarboFirmwareUpdate, MagicMock]:
        """Return entity and coordinator configured for cloud update with pre-cached version."""
        coordinator = _make_coordinator(options={OPT_CLOUD_ENABLED: True})
        coordinator.entry.data = {
            "robot_serial": MOCK_ROBOT_SERIAL,
            "robot_name": "TestBot",
            CONF_CLOUD_REFRESH_TOKEN: "test-refresh-token",
            CONF_CLOUD_USERNAME: "user@example.com",
        }
        coordinator.latest_firmware_version = "1.0.0"
        entity = _make_entity(coordinator)
        entity._latest_version = "1.0.0"
        return entity, coordinator

    @pytest.mark.asyncio
    async def test_clears_cached_version_when_firmware_version_is_null(self) -> None:
        """firmwareVersion: null in cloud response clears coordinator and entity cached version."""
        entity, coordinator = self._make_cloud_enabled_entity()

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_latest_version = AsyncMock(return_value={"firmwareVersion": None})
        mock_client.auth = MagicMock()

        with patch("custom_components.yarbo.update.YarboCloudClient", return_value=mock_client):
            await entity.async_update()

        assert entity._latest_version is None
        assert coordinator.latest_firmware_version is None

    @pytest.mark.asyncio
    async def test_clears_cached_version_when_firmware_version_key_missing(self) -> None:
        """Missing firmwareVersion key clears coordinator and entity cached version."""
        entity, coordinator = self._make_cloud_enabled_entity()

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_latest_version = AsyncMock(return_value={})
        mock_client.auth = MagicMock()

        with patch("custom_components.yarbo.update.YarboCloudClient", return_value=mock_client):
            await entity.async_update()

        assert entity._latest_version is None
        assert coordinator.latest_firmware_version is None
