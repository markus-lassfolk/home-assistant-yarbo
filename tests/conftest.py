"""Test fixtures for home-assistant-yarbo."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# homeassistant.components.dhcp transitively imports several packages
# (aiodhcpwatcher, aiodiscover, cached_ipaddress, …) that are not available
# in the test environment.  Stub the entire dhcp component module so
# config_flow.py can import dhcp.DhcpServiceInfo without pulling in those deps.
_dhcp_mock = MagicMock()
_dhcp_mock.DhcpServiceInfo = type(
    "DhcpServiceInfo", (), {"ip": "", "macaddress": "", "hostname": ""}
)
sys.modules.setdefault("homeassistant.components.dhcp", _dhcp_mock)

# Disable Sentry/GlitchTip error reporting during tests.
# python-yarbo calls init_error_reporting() at module import time; the Sentry SDK
# starts a BackgroundWorker thread when the first event is captured, which causes
# pytest-homeassistant-custom-component's strict thread-leak checker to fail.
os.environ.setdefault("YARBO_SENTRY_DSN", "")

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.yarbo.const import (
    CONF_BROKER_HOST,
    CONF_BROKER_MAC,
    CONF_BROKER_PORT,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    DEFAULT_BROKER_PORT,
    DOMAIN,
)

# ---------------------------------------------------------------------------
# Mock robot serial and config data
# ---------------------------------------------------------------------------

MOCK_ROBOT_SERIAL = "2440011234567890"
MOCK_BROKER_HOST = "192.168.1.11"
MOCK_BROKER_MAC = "c8:fe:0f:aa:bb:cc"
MOCK_ROBOT_NAME = "TestBot"

MOCK_CONFIG_ENTRY_DATA: dict[str, Any] = {
    CONF_ROBOT_SERIAL: MOCK_ROBOT_SERIAL,
    CONF_BROKER_HOST: MOCK_BROKER_HOST,
    CONF_BROKER_PORT: DEFAULT_BROKER_PORT,
    CONF_BROKER_MAC: MOCK_BROKER_MAC,
    CONF_ROBOT_NAME: MOCK_ROBOT_NAME,
}

MOCK_TELEMETRY: dict[str, Any] = {
    "battery": 83,
    "charging_status": 0,
    "working_state": 0,
    "error_code": 0,
    "raw": {
        "BatteryMSG": {"capacity": 83},
        "StateMSG": {
            "working_state": 0,
            "charging_status": 0,
            "error_code": 0,
            "on_going_planning": 0,
            "planning_paused": 0,
            "on_going_recharging": 0,
        },
        "HeadMsg": {"head_type": 0},  # Snow blower
        "RTKMSG": {"status": 4, "heading": 180.0},
        "RunningStatusMSG": {
            "chute_angle": 90,
            "rain_sensor_data": 0,
        },
    },
}


@pytest.fixture
def mock_yarbo_client() -> Generator[MagicMock, None, None]:
    """Mock the YarboClient from python-yarbo.

    TODO: Expand this fixture as python-yarbo API stabilises.
    Mocks: connect, disconnect, watch_telemetry, get_status,
           publish_raw, set_lights, buzzer, set_chute.
    """
    with patch("custom_components.yarbo.YarboLocalClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.get_controller = AsyncMock()
        client.get_status = AsyncMock(return_value=MOCK_TELEMETRY)
        client.publish_raw = AsyncMock()
        client.publish_command = AsyncMock()
        client.set_lights = AsyncMock()
        client.buzzer = AsyncMock()
        client.set_chute = AsyncMock()
        client.start_plan = AsyncMock()
        client.is_connected = True
        client.controller_acquired = True
        client.serial_number = MOCK_ROBOT_SERIAL
        # watch_telemetry is an async generator — stub it to yield once then stop
        client.watch_telemetry = MagicMock(return_value=_async_gen([MOCK_TELEMETRY]))
        yield client


async def _async_gen(items: list[Any]) -> AsyncGenerator[Any, None]:
    """Yield items from a list as an async generator."""
    for item in items:
        yield item


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MagicMock:
    """Return a mock config entry with standard test data.

    TODO: Replace with actual ConfigEntry creation once config flow is implemented.
    """
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = MOCK_CONFIG_ENTRY_DATA
    entry.options = {}
    entry.unique_id = MOCK_ROBOT_SERIAL
    entry.title = MOCK_ROBOT_NAME
    return entry
