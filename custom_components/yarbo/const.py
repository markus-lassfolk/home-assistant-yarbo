"""Constants for the Yarbo integration."""

from __future__ import annotations

from .models import YarboTelemetry

DOMAIN = "yarbo"

# Platforms to load
PLATFORMS: list[str] = [
    "sensor",
    "binary_sensor",
    "button",
    "event",
    "light",
    "select",
    "switch",
    "number",
    "device_tracker",
    "lawn_mower",
    "update",
]

# Config entry data keys
CONF_ROBOT_SERIAL = "robot_serial"
CONF_BROKER_HOST = "broker_host"
CONF_BROKER_PORT = "broker_port"
CONF_BROKER_MAC = "broker_mac"
CONF_ROBOT_NAME = "robot_name"
CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_REFRESH_TOKEN = "cloud_refresh_token"
# Rover vs DC endpoint selection (issue #50)
CONF_ALTERNATE_BROKER_HOST = "alternate_broker_host"  # kept for backward compat
CONF_BROKER_ENDPOINTS = "broker_endpoints"  # ordered list from discovery: [Primary, Secondary, ...]
CONF_CONNECTION_PATH = "connection_path"  # "dc" | "rover"
CONF_ROVER_IP = "rover_ip"  # rover IP for device info when known

# Endpoint types for discovery
ENDPOINT_TYPE_DC = "dc"
ENDPOINT_TYPE_ROVER = "rover"
ENDPOINT_TYPE_UNKNOWN = "unknown"

# Options keys
OPT_TELEMETRY_THROTTLE = "telemetry_throttle"
OPT_AUTO_CONTROLLER = "auto_controller"
OPT_CLOUD_ENABLED = "cloud_enabled"
OPT_ACTIVITY_PERSONALITY = "activity_personality"

# Defaults
DEFAULT_BROKER_PORT = 1883
DEFAULT_TELEMETRY_THROTTLE = 1.0
DEFAULT_AUTO_CONTROLLER = True
DEFAULT_CLOUD_ENABLED = False
DEFAULT_ACTIVITY_PERSONALITY = False  # Boolean: False=standard, True=fun/verbose descriptions

# Head types — MQTT wire values from APK _HEAD_TYPE_MAP (Smi-decoded keys)
# Confirmed via Blutter decompilation of deviceRules.dart + live telemetry.
# Wire 1 = Snow Blower confirmed via live MQTT + visual inspection.
HEAD_TYPE_NONE = 0
HEAD_TYPE_SNOW_BLOWER = 1
HEAD_TYPE_LEAF_BLOWER = 2
HEAD_TYPE_LAWN_MOWER = 3
HEAD_TYPE_SMART_COVER = 4  # SAM / patrol / sentry
HEAD_TYPE_LAWN_MOWER_PRO = 5
HEAD_TYPE_TRIMMER = 99

HEAD_TYPE_NAMES: dict[int, str] = {
    HEAD_TYPE_NONE: "None",
    HEAD_TYPE_SNOW_BLOWER: "Snow Blower",
    HEAD_TYPE_LEAF_BLOWER: "Leaf Blower",
    HEAD_TYPE_LAWN_MOWER: "Lawn Mower",
    HEAD_TYPE_SMART_COVER: "Smart Cover",
    HEAD_TYPE_LAWN_MOWER_PRO: "Lawn Mower Pro",
    HEAD_TYPE_TRIMMER: "Trimmer",
}

# Heartbeat timeout before raising a repair issue
HEARTBEAT_TIMEOUT_SECONDS = 60

# Retry delay for telemetry loop reconnection
TELEMETRY_RETRY_DELAY_SECONDS = 30

# hass.data storage keys
DATA_COORDINATOR = "coordinator"
DATA_CLIENT = "client"


def get_activity_state(telemetry: YarboTelemetry) -> str:
    """Map telemetry to activity state string.

    Args:
        telemetry: YarboTelemetry object

    Returns:
        Activity state: "error", "charging", "working", "returning", "paused", or "idle"
    """
    if telemetry.error_code != 0:
        return "error"
    if telemetry.charging_status in (1, 2, 3):
        return "charging"
    if telemetry.state in (1, 7, 8):
        return "working"
    if telemetry.state == 2:
        return "returning"
    if telemetry.state == 5:
        return "paused"
    if telemetry.state == 6:
        return "error"
    return "idle"


# Light channel names (for LED control)
LIGHT_CHANNEL_HEAD = "led_head"
LIGHT_CHANNEL_LEFT_W = "led_left_w"
LIGHT_CHANNEL_RIGHT_W = "led_right_w"
LIGHT_CHANNEL_BODY_LEFT = "body_left_r"
LIGHT_CHANNEL_BODY_RIGHT = "body_right_r"
LIGHT_CHANNEL_TAIL_LEFT = "tail_left_r"
LIGHT_CHANNEL_TAIL_RIGHT = "tail_right_r"

LIGHT_CHANNELS: list[str] = [
    LIGHT_CHANNEL_HEAD,
    LIGHT_CHANNEL_LEFT_W,
    LIGHT_CHANNEL_RIGHT_W,
    LIGHT_CHANNEL_BODY_LEFT,
    LIGHT_CHANNEL_BODY_RIGHT,
    LIGHT_CHANNEL_TAIL_LEFT,
    LIGHT_CHANNEL_TAIL_RIGHT,
]

# Verbose activity descriptions (shown in extra_state_attributes when personality=True)
VERBOSE_ACTIVITY_DESCRIPTIONS: dict[str, str] = {
    "charging": "Charging up for the next adventure ⚡",
    "idle": "Resting and waiting for orders 😴",
    "working": "Munching away on the task 🌱",
    "paused": "Taking a short break ☕",
    "returning": "Heading home to the dock 🏠",
    "error": "Oops! Something went wrong 🚨",
}
