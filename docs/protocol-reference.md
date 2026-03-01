---
layout: default
title: Protocol Reference
nav_order: 7
description: "Local MQTT protocol documentation for the Yarbo robot"
---

# Protocol Reference
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

This page documents the local MQTT protocol the Yarbo robot exposes on your home network. The integration uses this protocol to communicate with the robot.

1. TOC
{:toc}

---

## Local MQTT Broker

The Yarbo robot runs an EMQX MQTT broker that is accessible to any device on the same local network.

| Property | Value |
|----------|-------|
| Port | `1883` (TCP, unauthenticated) |
| WebSocket port | `8083` |
| TLS port | `8883` |
| Authentication | None required for local connections |
| Protocol version | MQTT 3.1.1 |
| Topic prefix | `snowbot/<SN>/` |

Where `<SN>` is the robot's serial number (e.g. `24400102L8HO5227`).

### Wi-Fi Access

The robot also broadcasts its own Wi-Fi HaLow network for direct access when you are near the robot. The network name follows the pattern `Yarbo_HaLow_xxxxxx` where `xxxxxx` derives from the serial number suffix.

---

## Payload Encoding

All payloads (both sent and received) on the local broker are **zlib-compressed JSON**, except the `heart_beat` topic which is plain JSON.

```python
import json
import zlib

# Encode a command payload
def encode(data: dict) -> bytes:
    return zlib.compress(json.dumps(data).encode())

# Decode a received payload
def decode(payload: bytes) -> dict:
    try:
        return json.loads(zlib.decompress(payload))
    except zlib.error:
        return json.loads(payload)  # Fallback for plain JSON
```

> This encoding applies to firmware version 3.9.0 and later. Older firmware versions may use plain JSON.
{: .note }

---

## Topic Structure

### Robot → HA (Incoming)

| Topic | Encoding | Rate | Description |
|-------|----------|------|-------------|
| `snowbot/<SN>/device/DeviceMSG` | zlib JSON | 1–2 Hz | Full telemetry payload |
| `snowbot/<SN>/device/heart_beat` | Plain JSON | ~1 Hz | Minimal heartbeat: `{"working_state": 0\|1}` |
| `snowbot/<SN>/device/data_feedback` | zlib JSON | On demand | Responses to commands |
| `snowbot/<SN>/device/plan_feedback` | zlib JSON | ~1 Hz when active | Work plan execution state |
| `snowbot/<SN>/device/recharge_feedback` | zlib JSON | ~1 Hz when returning | Return path and ETA |
| `snowbot/<SN>/device/cloud_points_feedback` | zlib JSON | ~1–2 Hz when active | Obstacle/map point cloud |
| `snowbot/<SN>/device/ota_feedback` | zlib JSON | On demand | Firmware update progress |
| `snowbot/<SN>/device/patrol_feedback` | zlib JSON | When active | Patrol mode events |
| `snowbot/<SN>/device/combined_odom_path` | zlib JSON | When active | Fused odometry path |
| `snowbot/<SN>/device/deviceinfo_feedback` | zlib JSON | On demand | Device info responses |
| `snowbot/<SN>/device/log_feedback` | zlib JSON | On demand | Robot log stream |

**Discovery:** To find robots on the network without knowing the serial number, wildcard-subscribe to `snowbot/+/device/DeviceMSG` or `snowbot/+/device/heart_beat`. The `<SN>` appears as the second path segment.

### HA → Robot (Outgoing)

| Topic | Encoding | Description |
|-------|----------|-------------|
| `snowbot/<SN>/app/<cmd_name>` | zlib JSON | Primary command channel |

---

## DeviceMSG Schema

The main telemetry payload published every 1–2 seconds. Example (annotated):

```json
{
  "BatteryMSG": {
    "capacity": 83,
    "status": 3,
    "temp_err": 0,
    "timestamp": 1771943280.057
  },
  "BodyMsg": {
    "recharge_state": 2
  },
  "CombinedOdom": {
    "phi": -0.359,
    "x": 1.268,
    "y": -0.338
  },
  "HeadMsg": {
    "head_type": 1
  },
  "HeadSerialMsg": {
    "head_sn": "243904023M1L1599"
  },
  "RTKMSG": {
    "gga_atn_dis": 0.3902,
    "heading": 339.4576,
    "heading_atn_dis": 0.3892,
    "heading_dop": 0.6207,
    "heading_status": 1,
    "status": "4",
    "timestamp": 1771943280.131
  },
  "RunningStatusMSG": {
    "chute_angle": 105,
    "chute_steering_engine_info": 55,
    "elec_navigation_front_right_sensor": 3943,
    "elec_navigation_rear_right_sensor": 3962,
    "head_gyro_pitch": 0.0,
    "head_gyro_roll": 0.0,
    "rain_sensor_data": 0
  },
  "StateMSG": {
    "car_controller": false,
    "charging_status": 2,
    "error_code": 0,
    "machine_controller": 1,
    "on_going_planning": 0,
    "on_going_recharging": 0,
    "on_going_to_start_point": 0,
    "planning_paused": 0,
    "robot_follow_state": false,
    "working_state": 1
  },
  "base_status": 7,
  "combined_odom_confidence": 0.915,
  "green_grass_update_switch": 1,
  "ipcamera_ota_switch": 0,
  "route_priority": {
    "hg0": 10,
    "wlan0": 600,
    "wwan0": 50000
  },
  "rtcm_age": 2.0,
  "rtcm_info": { "current_source_type": 2 },
  "rtk_base_data": {
    "base": { "gngga": "$GNGGA,..." },
    "rover": { "gngga": "$GNGGA,...", "heading": "#HEADINGA,..." }
  },
  "timestamp": 1771943280.0,
  "ultrasonic_msg": { "lf_dis": 0, "mt_dis": 0, "rf_dis": 0 },
  "wireless_recharge": {
    "error_code": 0,
    "output_current": 1489,
    "output_voltage": 4186,
    "state": 2
  }
}
```

### Key Field Reference

| Field path | Type | Description |
|-----------|------|-------------|
| `BatteryMSG.capacity` | int | Battery percentage (0–100) |
| `BatteryMSG.status` | int | Battery status code |
| `BatteryMSG.temp_err` | int | Temperature error flag (0 = OK) |
| `StateMSG.working_state` | int | 0 = idle/sleep, 1 = active |
| `StateMSG.charging_status` | int | 0 = not charging, 1–3 = charging variants |
| `StateMSG.error_code` | int | Error code (0 = no error) |
| `StateMSG.on_going_planning` | int | 1 = plan actively running |
| `StateMSG.planning_paused` | int | 1 = plan paused |
| `StateMSG.on_going_recharging` | int | 1 = returning to dock |
| `StateMSG.on_going_to_start_point` | int | 1 = navigating to plan start |
| `StateMSG.robot_follow_state` | bool | true = follow mode active |
| `StateMSG.car_controller` | bool | true = manual controller active |
| `HeadMsg.head_type` | int | See head type table below |
| `RTKMSG.heading` | float | Compass heading in degrees (0–360) |
| `RTKMSG.status` | string | "4" = RTK Fixed (highest quality) |
| `RTKMSG.heading_dop` | float | Heading dilution of precision |
| `CombinedOdom.x` | float | X position, local frame (meters) |
| `CombinedOdom.y` | float | Y position, local frame (meters) |
| `CombinedOdom.phi` | float | Heading, local frame (radians) |
| `combined_odom_confidence` | float | Fusion quality score (0.0–1.0) |
| `RunningStatusMSG.chute_angle` | int | Snow chute angle (0–200) |
| `RunningStatusMSG.rain_sensor_data` | int | 0 = dry; higher = moisture detected |
| `wireless_recharge.state` | int | 2 = wireless charging active |
| `wireless_recharge.output_voltage` | int | Charging voltage in mV |
| `wireless_recharge.output_current` | int | Charging current in mA |
| `ultrasonic_msg.lf_dis` | int | Left-front obstacle distance (mm; 0 = no obstacle) |
| `ultrasonic_msg.mt_dis` | int | Front obstacle distance (mm) |
| `ultrasonic_msg.rf_dis` | int | Right-front obstacle distance (mm) |
| `route_priority.hg0` | int | HaLow interface routing priority (lower = preferred) |
| `route_priority.wlan0` | int | Wi-Fi routing priority |
| `route_priority.wwan0` | int | Cellular routing priority |

### Head Type Values

| Value | Head |
|-------|------|
| 0 | None / base only |
| 1 | Snow Blower |
| 2 | Leaf Blower |
| 3 | Lawn Mower |
| 4 | Smart Cover |
| 5 | Lawn Mower Pro |
| 99 | Trimmer |

---

## Command Format

Commands are sent to `snowbot/<SN>/app/<cmd_name>` with a zlib-compressed JSON payload.

```python
import json
import zlib
import paho.mqtt.client as mqtt

SN = "YOUR_SERIAL_NUMBER"
BROKER_IP = "YOUR_ROBOT_IP"

def send_command(client, cmd_name: str, payload: dict = None):
    topic = f"snowbot/{SN}/app/{cmd_name}"
    data = json.dumps(payload or {}).encode()
    client.publish(topic, zlib.compress(data))
```

### Controller Acquisition

Before sending any control command, the integration acquires the "controller" role:

```python
send_command(client, "get_controller", {})
# Wait for data_feedback: "Successfully connected to the physical controller."
# Then send other commands
```

Only one MQTT client can hold the controller role at a time. If another client (such as the Yarbo app) is active, commands may be rejected.

---

## Command Response Format

Responses arrive on `snowbot/<SN>/device/data_feedback`:

```json
{
  "topic": "<cmd_name>",
  "state": 0,
  "msg": "Optional status message",
  "data": { "...command-specific response..." }
}
```

| Field | Description |
|-------|-------------|
| `topic` | Echo of the command name that was sent |
| `state` | `0` = success, non-zero = error |
| `msg` | Human-readable status or error message |
| `data` | Command-specific response data |

Some commands are **fire-and-forget** and produce no `data_feedback` response — see the command reference tables below.

---

## Core Commands

### State & Control

| Command | Payload | Response | Description |
|---------|---------|----------|-------------|
| `get_controller` | `{}` | `"Successfully connected..."` | **Required before sending commands.** Acquires controller role. |
| `set_working_state` | `{"state": 1}` | state:0 | Wake/activate robot (state=1) or sleep (state=0) |
| `dstop` | `{}` | None (fire-and-forget) | Graceful stop — finish current move, then halt |
| `emergency_stop_active` | `{}` | None | Immediate hardware emergency stop |
| `cmd_vel` | `{"vel": float, "rev": float}` | None | Manual velocity command (vel=linear m/s, rev=angular rad/s) |

### Plan Execution

| Command | Payload | Response | Description |
|---------|---------|----------|-------------|
| `start_plan` | `{"planId": string}` | state:0 | Start a saved work plan by ID |
| `planning_paused` | `{}` | None | Pause the active plan |
| `resume` | `{}` | None | Resume a paused plan |
| `cmd_recharge` | `{}` | None | Return robot to charging dock |
| `in_plan_action` | `{"action": string}` | state:0 | Action during active plan execution |

### Plan Management

| Command | Payload | Response | Description |
|---------|---------|----------|-------------|
| `read_all_plan` | `{}` | Plan list | Returns array of `{id, name, areaIds, enable_self_order}` |
| `read_plan` | `{"planId": string}` | Plan detail | Returns full plan with waypoints |
| `del_plan` | `{"planId": string}` | state:0 | Delete a single plan |
| `del_all_plan` | `{}` | state:0 | **Destructive:** Delete all plans |

### Light Control

| Command | Payload | Response | Description |
|---------|---------|----------|-------------|
| `light_ctrl` | See LED payload | None (fire-and-forget) | Set all 7 LED channels |
| `head_light` | `{"state": 0\|1}` | None | Toggle head light on/off |
| `roof_lights_enable` | `{"enable": bool}` | None | Enable/disable roof lights |

**LED payload format for `light_ctrl`:**

```json
{
  "led_head":      0-255,
  "led_left_w":    0-255,
  "led_right_w":   0-255,
  "body_left_r":   0-255,
  "body_right_r":  0-255,
  "tail_left_r":   0-255,
  "tail_right_r":  0-255
}
```

### Audio

| Command | Payload | Response | Description |
|---------|---------|----------|-------------|
| `cmd_buzzer` | `{"state": 1, "timeStamp": int}` | None | Activate (state=1) or deactivate buzzer |
| `song_cmd` | `{"songId": 0}` | None | Play built-in sound |
| `set_sound_param` | `{"vol": int, "enable": bool}` | None | Set volume and sound enable |

### System

| Command | Payload | Response | Description |
|---------|---------|----------|-------------|
| `shutdown` | `{}` | state:0 | Power off robot (physical restart required) |
| `restart_container` | `{}` | `"Container restarted..."` | Restart robot software (~30s offline) |
| `read_all_plan` | `{}` | Plan array | List saved plans |
| `get_connect_wifi_name` | `{}` | WiFi info | Returns `{name, ip, signal}` |
| `read_no_charge_period` | `{}` | Period array | List no-charge time windows |
| `read_global_params` | `{"id": 1}` | Global settings | Full robot configuration object |
| `save_charging_point` | `{}` | None | Save current position as dock location |
| `start_hotspot` | `{}` | None | Start robot Wi-Fi hotspot |
| `save_map_backup` | `{}` | None | Create a map backup |
| `ignore_obstacles` | `{"state": 0\|1}` | state:0 | Toggle obstacle bypass during active plan |

---

## Head-Specific Commands

### Snow Blower Head (head_type = 1)

| Command | Payload | Description |
|---------|---------|-------------|
| `cmd_chute` | `{"vel": int}` | Chute rotation velocity |
| `cmd_chute_streeing_work` | `{"angle": int}` | Chute steering angle during work (±90°) |
| `push_snow_dir` | `{"direction": 0\|1\|2}` | Snow push direction (0=left, 1=right, 2=center) |
| `blower_speed` | `{"vel": int}` | Blower auger speed (0–80; only works when actively blowing) |
| `en_blower` | `{"enabled": bool}` | Enable/disable blower |
| `enable_smart_blowing` | `{"enabled": bool}` | Smart blowing mode |
| `edge_blower_switch` | `{"enabled": bool}` | Edge blowing mode |

### Lawn Mower Head (head_type = 3 or 5)

| Command | Payload | Description |
|---------|---------|-------------|
| `set_blade_height` | `{"height": int}` | Cutting height (25–75 mm) |
| `set_blade_speed` | `{"speed": int}` | Blade speed (1000–3500 RPM) |
| `cmd_roller` | `{"vel": int}` | Roller/drum speed |
| `mower_head_sensor_switch` | `{"state": 0\|1}` | Mower head collision sensor |
| `set_turn_type` | `{"turn_type": 0\|1\|2}` | Turn type (0=U-turn, 1=three-point, 2=zero-radius) |

### Leaf Blower Head (head_type = 2)

| Command | Payload | Description |
|---------|---------|-------------|
| `cmd_roller` | `{"vel": int}` | Roller speed (RPM presets vary by device version) |
| `smart_blowing` | `{"state": 0\|1}` | Smart auto-blowing mode |
| `edge_blowing` | `{"state": 0\|1}` | Edge-focused blowing mode |

### Trimmer Head (head_type = 99)

| Command | Payload | Description |
|---------|---------|-------------|
| `cmd_trimmer` | `{"state": 0\|1}` | Engage/disengage trimmer blade |

---

## Global Parameters Schema

The `read_global_params` command returns the full robot configuration. Key fields:

```json
{
  "plan_speed": 0.65,
  "max_vel": 0.7,
  "min_vel": 0.04,
  "max_rev": 1.5,
  "min_rev": 0.08,
  "recharge_battery": 20,
  "resume_battery": 80,
  "recharge_battery_max": 30,
  "recharge_battery_min": 15,
  "resume_battery_max": 80,
  "resume_battery_min": 50,
  "standby_time": 300,
  "chute_min_angle": 0,
  "chute_max_angle": 200,
  "max_roller_speed": 2000,
  "min_roller_speed": 0,
  "enable_weather_schedule": true,
  "enable_advanced_fusion": true,
  "rain_temp_ntc_sensor_detec": true
}
```

---

## Plan Schema

Returned by `read_all_plan`:

```json
{
  "id": 1,
  "name": "Front Yard",
  "areaIds": [29],
  "enable_self_order": true
}
```

---

## Schedule Schema

Returned by `read_schedules`:

```json
{
  "id": 1,
  "name": "Schedule 1",
  "plan_id": 2,
  "enable": false,
  "schedule_type": 1,
  "start_time": "05:00:00",
  "end_time": "06:00:00",
  "week_day": 127,
  "interval_time": 0,
  "return_method": 2,
  "timezone": ""
}
```

`week_day` is a bitmask: 127 = all days, 62 = Mon–Fri.

---

## plan_feedback Schema

Published when a plan is running:

```json
{
  "planId": 1,
  "areaIds": [29],
  "runningState": 1,
  "actualCleanArea": 0.0,
  "totalCleanArea": 0.0,
  "finishCleanArea": 0.0,
  "leftTime": 0.0,
  "totalTime": 0.0,
  "startTime": 0,
  "battery_consumption": 0,
  "cleanPathProgress": [
    {
      "id": 29,
      "path": [{"x": 30.07, "y": 13.814}],
      "clean_index": 0,
      "clean_times": 0
    }
  ]
}
```

---

## Important Notes

### Destructive Commands

The following commands are irreversible — use with caution:

| Command | Risk |
|---------|------|
| `erase_map` | Permanently erases the robot's saved map |
| `del_all_plan` | Deletes all work plans |
| `del_all_nogozone` | Removes all safety no-go zones |
| `shutdown` | Powers off robot hardware |
| `restore_default_setting` | Factory resets all settings |
| `firmware_update_now` | Triggers an OTA firmware update |
| `del_all_map_backup` | Deletes all map backups |

### Network Priority

The robot prefers network interfaces in this order (from `route_priority` field):
1. HaLow (hg0) — priority 10 (most preferred)
2. Wi-Fi (wlan0) — priority 600
3. Cellular (wwan0) — priority 50000 (fallback only)

---

## Related Pages

- [Communication Architecture](communication-architecture.md) — how the system connects
- [Cloud API](cloud-api.md) — cloud REST API reference
- [Services](services.md) — HA services that use these commands
- [Development](development.md) — contributing guide
