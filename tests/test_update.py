"""Tests for the Yarbo firmware update entity (#25)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from custom_components.yarbo.const import (
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
