"""Test fixtures for home-assistant-yarbo."""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch


# homeassistant.components.dhcp transitively imports several packages
# (aiodhcpwatcher, aiodiscover, cached_ipaddress, …) that are not available
# in the test environment.  Stub the entire dhcp component module so
# config_flow.py can import dhcp.DhcpServiceInfo without pulling in those deps.
class _DhcpServiceInfo:
    """Stub for DhcpServiceInfo with ip, macaddress, hostname."""

    def __init__(self, ip: str = "", macaddress: str = "", hostname: str = "") -> None:
        self.ip = ip
        self.macaddress = macaddress
        self.hostname = hostname


_dhcp_mock = MagicMock()
_dhcp_mock.DhcpServiceInfo = _DhcpServiceInfo
sys.modules.setdefault("homeassistant.components.dhcp", _dhcp_mock)

# Stub aiodns/pycares to avoid background threads during tests.
_aiodns_module = types.ModuleType("aiodns")


class _DNSResolver:
    """Stub for aiodns.DNSResolver."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass


_aiodns_module.DNSResolver = _DNSResolver
sys.modules.setdefault("aiodns", _aiodns_module)
sys.modules.setdefault("pycares", types.ModuleType("pycares"))

# Stub python-yarbo to avoid optional dependency in tests.
_yarbo_module = types.ModuleType("yarbo")


class _YarboLocalClient:
    """Stub for YarboLocalClient."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass


class _YarboTelemetry:
    """Stub for YarboTelemetry."""

    def __init__(self, **_kwargs: object) -> None:
        pass


class _YarboLightState:
    """Stub for YarboLightState."""

    def __init__(self, **_kwargs: object) -> None:
        pass

    @classmethod
    def all_off(cls) -> _YarboLightState:
        """Return a YarboLightState with all channels set to 0."""
        return cls(
            led_head=0,
            led_left_w=0,
            led_right_w=0,
            body_left_r=0,
            body_right_r=0,
            tail_left_r=0,
            tail_right_r=0,
        )


_yarbo_module.YarboLocalClient = _YarboLocalClient
_yarbo_module.YarboTelemetry = _YarboTelemetry
_yarbo_module.YarboLightState = _YarboLightState

_yarbo_exceptions = types.ModuleType("yarbo.exceptions")


class YarboConnectionError(Exception):
    """Stub for YarboConnectionError."""


_yarbo_exceptions.YarboConnectionError = YarboConnectionError
_yarbo_module.exceptions = _yarbo_exceptions
sys.modules.setdefault("yarbo", _yarbo_module)
sys.modules.setdefault("yarbo.exceptions", _yarbo_exceptions)

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
# RFC 5737 documentation address; no real private IPs in tests
MOCK_BROKER_HOST = "192.0.2.1"
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
        client.wait_for_data_feedback = AsyncMock(return_value={"data": []})
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
