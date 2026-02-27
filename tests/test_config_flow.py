"""Tests for the Yarbo config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.yarbo.const import (
    CONF_BROKER_HOST,
    CONF_BROKER_MAC,
    CONF_BROKER_PORT,
    CONF_ROBOT_NAME,
    CONF_ROBOT_SERIAL,
    DEFAULT_BROKER_PORT,
    DOMAIN,
)
from tests.conftest import (
    MOCK_BROKER_HOST,
    MOCK_BROKER_MAC,
    MOCK_ROBOT_NAME,
    MOCK_ROBOT_SERIAL,
)


def _mock_telemetry(serial: str = MOCK_ROBOT_SERIAL):
    """Object with serial_number for config flow mqtt_test step."""
    t = MagicMock()
    t.serial_number = serial
    return t


async def _async_gen_one(item):
    """Async generator yielding one item."""
    yield item


class TestManualConfigFlow:
    """Tests for the manual (user) config flow step.

    Flow: user → (manual if no discovery) → mqtt_test → name → (cloud) → create_entry
    """

    async def test_user_step_shows_manual_form_when_no_discovery(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """When discovery finds no devices, user sees manual IP/port form."""
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "manual"

    async def test_manual_submit_then_mqtt_test_shows_name(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """Submit manual IP/port and successful MQTT test leads to name step."""
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
        assert result["step_id"] == "manual"

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.serial_number = MOCK_ROBOT_SERIAL
        mock_client.watch_telemetry = MagicMock(
            return_value=_async_gen_one(_mock_telemetry())
        )

        with patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "name"

    async def test_user_step_creates_entry(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """Full manual config flow creates a config entry."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.serial_number = MOCK_ROBOT_SERIAL
        mock_client.watch_telemetry = MagicMock(
            return_value=_async_gen_one(_mock_telemetry())
        )
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ), patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
            # mqtt_test runs inline, next step is name
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_ROBOT_NAME: MOCK_ROBOT_NAME}
            )
        # Next: cloud step; submit empty to skip
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "cloud"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_BROKER_HOST] == MOCK_BROKER_HOST
        assert result["data"][CONF_ROBOT_SERIAL] == MOCK_ROBOT_SERIAL
        assert result["data"][CONF_ROBOT_NAME] == MOCK_ROBOT_NAME

    async def test_user_step_cannot_connect(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """Connection failure in MQTT test shows cannot_connect error."""
        from yarbo.exceptions import YarboConnectionError

        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=YarboConnectionError("refused"))
        mock_client.disconnect = AsyncMock()
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ), patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"
        assert result["step_id"] == "mqtt_test"

    async def test_user_step_no_telemetry(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """Missing telemetry (timeout) shows no_telemetry error."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.watch_telemetry = MagicMock(
            return_value=_async_gen_one(_mock_telemetry())
        )
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ), patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ), patch(
            "custom_components.yarbo.config_flow.asyncio.wait_for",
            side_effect=TimeoutError(),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "no_telemetry"
        assert result["step_id"] == "mqtt_test"

    async def test_user_step_decode_error(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """Decode/exception in MQTT test shows decode_error."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.watch_telemetry = MagicMock(
            side_effect=RuntimeError("decode failed")
        )
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ), patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "decode_error"
        assert result["step_id"] == "mqtt_test"

    async def test_duplicate_robot_aborts(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """Configuring the same robot SN twice aborts with already_configured."""
        def fresh_telemetry_gen():
            return _async_gen_one(_mock_telemetry())

        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.serial_number = MOCK_ROBOT_SERIAL
        mock_client.watch_telemetry = MagicMock(side_effect=fresh_telemetry_gen)
        with patch(
            "custom_components.yarbo.config_flow.async_discover_endpoints",
            return_value=[],
        ), patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            # manual -> name (mqtt_test runs inline) -> cloud skip
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_ROBOT_NAME: MOCK_ROBOT_NAME}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )
            assert result["type"] == FlowResultType.CREATE_ENTRY

            # Second flow: same broker, same serial -> already_configured at name step
            result2 = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {CONF_BROKER_HOST: MOCK_BROKER_HOST, CONF_BROKER_PORT: DEFAULT_BROKER_PORT},
            )
            # Name step: submit name; same serial will trigger already_configured abort
            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {CONF_ROBOT_NAME: "OtherName"},
            )
        assert result2["type"] == FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


class TestDhcpDiscoveryFlow:
    """Tests for DHCP auto-discovery config flow.

    Triggered when a device with MAC OUI C8:FE:0F:* appears.
    Flow: dhcp → confirm → mqtt_test → name → create_entry
    """

    async def test_dhcp_discovery_shows_confirm(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """DHCP discovery shows a confirmation form."""
        discovery_info = dhcp.DhcpServiceInfo(
            ip=MOCK_BROKER_HOST,
            macaddress=MOCK_BROKER_MAC,
            hostname="yarbo-dc",
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=discovery_info,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "confirm"

    async def test_dhcp_confirm_then_mqtt_test_and_create_entry(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """DHCP confirm → MQTT test → name → skip cloud → create entry."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.serial_number = MOCK_ROBOT_SERIAL
        mock_client.watch_telemetry = MagicMock(
            return_value=_async_gen_one(_mock_telemetry())
        )
        discovery_info = dhcp.DhcpServiceInfo(
            ip=MOCK_BROKER_HOST,
            macaddress=MOCK_BROKER_MAC,
            hostname="yarbo-dc",
        )
        with patch(
            "custom_components.yarbo.config_flow.YarboLocalClient",
            return_value=mock_client,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_DHCP},
                data=discovery_info,
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )
            # mqtt_test runs inline, next step is name
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_ROBOT_NAME: MOCK_ROBOT_NAME}
            )
        assert result["step_id"] == "cloud"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_BROKER_HOST] == MOCK_BROKER_HOST
        assert result["data"][CONF_BROKER_MAC] == MOCK_BROKER_MAC
        assert result["data"][CONF_ROBOT_SERIAL] == MOCK_ROBOT_SERIAL

    async def test_dhcp_discovery_already_configured(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """DHCP discovery aborts when same MAC and same IP already configured."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        existing_host = "192.0.2.99"
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ROBOT_SERIAL: MOCK_ROBOT_SERIAL,
                CONF_BROKER_HOST: existing_host,
                CONF_BROKER_PORT: DEFAULT_BROKER_PORT,
                CONF_BROKER_MAC: MOCK_BROKER_MAC,
                CONF_ROBOT_NAME: MOCK_ROBOT_NAME,
            },
            unique_id=MOCK_ROBOT_SERIAL,
        )
        mock_entry.add_to_hass(hass)

        discovery_info = dhcp.DhcpServiceInfo(
            ip=existing_host,
            macaddress=MOCK_BROKER_MAC,
            hostname="yarbo-dc",
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=discovery_info,
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    async def test_dhcp_discovery_same_mac_new_ip_shows_reconfigure(
        self, hass: HomeAssistant, enable_custom_integrations: None
    ) -> None:
        """DHCP discovery with same MAC but new IP shows reconfigure form."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ROBOT_SERIAL: MOCK_ROBOT_SERIAL,
                CONF_BROKER_HOST: "192.0.2.99",
                CONF_BROKER_PORT: DEFAULT_BROKER_PORT,
                CONF_BROKER_MAC: MOCK_BROKER_MAC,
                CONF_ROBOT_NAME: MOCK_ROBOT_NAME,
            },
            unique_id=MOCK_ROBOT_SERIAL,
        )
        mock_entry.add_to_hass(hass)

        discovery_info = dhcp.DhcpServiceInfo(
            ip=MOCK_BROKER_HOST,
            macaddress=MOCK_BROKER_MAC,
            hostname="yarbo-dc",
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=discovery_info,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"


class TestOptionsFlow:
    """Tests for the Yarbo options flow.

    Options: telemetry_throttle, auto_controller, cloud_enabled, activity_personality
    """

    @pytest.mark.skip(reason="Options flow tests — implement with issue #26")
    async def test_options_flow_shows_form(self, hass: HomeAssistant) -> None:
        """Options flow shows the options form."""
        pass

    @pytest.mark.skip(reason="Options flow tests — implement with issue #26")
    async def test_options_flow_saves_options(self, hass: HomeAssistant) -> None:
        """Options are saved correctly."""
        pass
