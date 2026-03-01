"""Tests for the Yarbo integration __init__.py."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant


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
        mock_yarbo_client: object,
        mock_config_entry: object,
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
        mock_yarbo_client: object,
        mock_config_entry: object,
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
        mock_yarbo_client: object,
        mock_config_entry: object,
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


def test_get_controller_accepts_timeout():
    """Regression: HA calls get_controller(timeout=5.0). GlitchTip #30/#32.

    Since conftest stubs yarbo, we verify via importlib.metadata that the
    installed version meets the minimum, AND check the stub has the method.
    """
    import importlib.metadata
    from packaging.version import Version

    installed = importlib.metadata.version("python-yarbo")
    assert Version(installed) >= Version("2026.3.12"), (
        f"python-yarbo {installed} too old; get_controller(timeout=...) "
        "requires >= 2026.3.12"
    )

    # Also verify the integration code actually calls with timeout=
    import ast
    import pathlib

    for pyfile in pathlib.Path("custom_components/yarbo").glob("*.py"):
        tree = ast.parse(pyfile.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get_controller"
            ):
                kw_names = [kw.arg for kw in node.keywords]
                if "timeout" in kw_names:
                    return  # Found a call with timeout= — test passes
    # If we get here, no call with timeout= was found (unexpected)
    assert False, "No get_controller(timeout=...) call found in integration code"


def test_min_lib_version_constant():
    """Ensure MIN_LIB_VERSION is set and the installed library meets it."""
    from packaging.version import Version
    import importlib.metadata

    from custom_components.yarbo import MIN_LIB_VERSION

    installed = importlib.metadata.version("python-yarbo")
    assert Version(installed) >= Version(MIN_LIB_VERSION), (
        f"Installed python-yarbo {installed} < required {MIN_LIB_VERSION}"
    )
