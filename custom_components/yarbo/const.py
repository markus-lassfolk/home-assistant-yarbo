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

# Command name aliases (Dart/UI naming confusion)
COMMAND_ALIASES: dict[str, str] = {
    "read_all_clean_area": "read_clean_area",
    "readCleanArea": "read_clean_area",
    "setIgnoreObstacle": "ignore_obstacles",
    "shutdownYarbo": "shutdown",
    "restart_yarbo_system": "restart_container",
    "set_roller_speed": "cmd_roller",
}

# Head-specific commands and their required head types
COMMAND_REQUIRED_HEAD_TYPE: dict[str, int] = {
    "cmd_roller": HEAD_TYPE_LEAF_BLOWER,
    "blower_speed": HEAD_TYPE_SNOW_BLOWER,
}

# Diagnostic commands only valid during active operation (working state)
ACTIVE_ONLY_DIAGNOSTIC_COMMANDS: set[str] = {
    "battery_cell_temp_msg",
    "motor_temp_samp",
    "body_current_msg",
    "head_current_msg",
    "speed_msg",
    "odometer_msg",
    "product_code_msg",
    "hub_info",
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


def normalize_command_name(command: str) -> str:
    """Normalize command names to MQTT wire names."""
    return COMMAND_ALIASES.get(command, command)


def required_head_type_for_command(command: str) -> int | None:
    """Return required head type for a head-specific command, if any."""
    return COMMAND_REQUIRED_HEAD_TYPE.get(command)


def is_active_only_diagnostic_command(command: str) -> bool:
    """Return True for diagnostic commands that only work during active operation."""
    return command in ACTIVE_ONLY_DIAGNOSTIC_COMMANDS


def is_active_operation(telemetry: YarboTelemetry | None) -> bool:
    """Return True when telemetry indicates the robot is actively working."""
    if telemetry is None:
        return False
    return get_activity_state(telemetry) == "working"


def validate_head_type_for_command(
    command: str, current_head_type: int | None
) -> tuple[bool, str | None]:
    """Validate if current head type matches command requirements.

    Args:
        command: The normalized command name
        current_head_type: The current head type from telemetry (or None)

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
        If invalid, error_message contains a human-readable error string.
    """
    required_head = required_head_type_for_command(command)
    if required_head is None:
        return (True, None)
    if current_head_type == required_head:
        return (True, None)
    head_name = HEAD_TYPE_NAMES.get(required_head, str(required_head))
    return (False, f"Command {command} requires head type {head_name}")


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

# Debug & Recording options
OPT_DEBUG_LOGGING = "debug_logging"
OPT_MQTT_RECORDING = "mqtt_recording"
DEFAULT_DEBUG_LOGGING = False
DEFAULT_MQTT_RECORDING = False
MQTT_RECORDING_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
