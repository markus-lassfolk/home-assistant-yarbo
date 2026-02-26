"""Constants for the Yarbo integration."""

from __future__ import annotations

DOMAIN = "yarbo"

# Platforms to load
PLATFORMS: list[str] = [
    "sensor",
    "binary_sensor",
    "button",
    "event",
]

# Config entry data keys
CONF_ROBOT_SERIAL = "robot_serial"
CONF_BROKER_HOST = "broker_host"
CONF_BROKER_PORT = "broker_port"
CONF_BROKER_MAC = "broker_mac"
CONF_ROBOT_NAME = "robot_name"
CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_REFRESH_TOKEN = "cloud_refresh_token"

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
ACTIVITY_PERSONALITY_OPTIONS: list[str] = ["default", "verbose", "simple"]
DEFAULT_ACTIVITY_PERSONALITY = "default"

# Head types (from Dart HeadType enum, APK v3.17.4)
HEAD_TYPE_SNOW_BLOWER = 0
HEAD_TYPE_LAWN_MOWER = 1
HEAD_TYPE_LAWN_MOWER_PRO = 2
HEAD_TYPE_LEAF_BLOWER = 3
HEAD_TYPE_SMART_COVER = 4  # SAM / patrol / sentry
HEAD_TYPE_TRIMMER = 5
HEAD_TYPE_NONE = 6

HEAD_TYPE_NAMES: dict[int, str] = {
    HEAD_TYPE_SNOW_BLOWER: "Snow Blower",
    HEAD_TYPE_LAWN_MOWER: "Lawn Mower",
    HEAD_TYPE_LAWN_MOWER_PRO: "Lawn Mower Pro",
    HEAD_TYPE_LEAF_BLOWER: "Leaf Blower",
    HEAD_TYPE_SMART_COVER: "Smart Cover",
    HEAD_TYPE_TRIMMER: "Trimmer",
    HEAD_TYPE_NONE: "None",
}

# Activity states
ACTIVITY_CHARGING = "Charging in the dock"
ACTIVITY_IDLE = "Idle"
ACTIVITY_WORKING = "Working on a plan"
ACTIVITY_PAUSED = "Paused"
ACTIVITY_RETURNING = "Returning to dock"
ACTIVITY_ERROR = "Error"

# Heartbeat timeout before raising a repair issue
HEARTBEAT_TIMEOUT_SECONDS = 60

# hass.data storage keys
DATA_COORDINATOR = "coordinator"
DATA_CLIENT = "client"
