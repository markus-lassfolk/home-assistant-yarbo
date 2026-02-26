# Entity Reference

All entity unique IDs follow the pattern `{robot_sn}_{entity_key}`.

## Core Entities (Always Enabled)

These entities are enabled by default and available for all head types.

| Entity | Platform | Key | Device Class | Unit | Notes |
|--------|----------|-----|--------------|------|-------|
| Battery | `sensor` | `battery` | `battery` | `%` | From `DeviceMSG.battery` |
| Activity | `sensor` | `activity` | — | — | State machine; see table below |
| Charging | `binary_sensor` | `charging` | `battery_charging` | — | True when docked and charging |
| Problem | `binary_sensor` | `problem` | `problem` | — | True on any error code |
| Head Type | `sensor` | `head_type` | — | — | Human-readable; see multi-head.md |
| Beep | `button` | `beep` | — | — | Sends `cmd_buzzer` |
| Return to Dock | `button` | `return_to_dock` | — | — | Sends `cmd_recharge` |
| Pause | `button` | `pause` | — | — | Sends `planning_paused` |
| Resume | `button` | `resume` | — | — | Sends `resume` |
| Stop | `button` | `stop` | — | — | Sends `dstop` |
| Lights | `light` | `lights` | — | — | Group entity controlling all channels |
| Events | `event` | `events` | — | — | See events.md |

### Activity State Machine

| State | Raw Value | Description |
|-------|-----------|-------------|
| `idle` | 0 | Powered on, no job |
| `mowing` | 1 | Executing a plan (head_type 1/2) |
| `snow_blowing` | 1 | Executing a plan (head_type 0) |
| `leaf_blowing` | 1 | Executing a plan (head_type 3) |
| `returning` | 2 | Driving back to dock |
| `docked` | 3 | Physically in dock |
| `charging` | 4 | Docked and charging |
| `paused` | 5 | Job paused |
| `error` | 6 | Error state; check `problem` sensor |
| `planning` | 7 | Computing path |
| `manual` | 8 | Remote/joystick control active |

## Extended Entities (Disabled by Default)

Enable individually in **Settings → Devices & Services → Yarbo → {device} → entities**.

| Entity | Platform | Key | Device Class | Unit | Notes |
|--------|----------|-----|--------------|------|-------|
| RTK Status | `sensor` | `rtk_status` | — | — | GPS fix quality string |
| Heading | `sensor` | `heading` | — | `°` | Compass heading 0-359 |
| Chute Angle | `sensor` | `chute_angle` | — | `°` | Snow chute position |
| Rain Sensor | `binary_sensor` | `rain` | `moisture` | — | From rain sensor input |
| Satellite Count | `sensor` | `satellite_count` | — | — | RTK satellite count |
| Charging Power | `sensor` | `charging_power` | `power` | `W` | From DC telemetry |
| Light Ch. 1–7 | `light` | `light_ch_{1-7}` | — | — | Individual LED channels (0-255) |
| Chute Velocity | `number` | `chute_velocity` | — | — | Range: -2000 to 2000 |
| Buzzer | `switch` | `buzzer` | — | — | Enable/disable buzzer sounds |
| Planning | `binary_sensor` | `planning` | `running` | — | True when path planning active |
| Emergency Stop | `button` | `emergency_stop` | — | — | Sends `emergency_stop_active` |

## Diagnostic Entities

| Entity | Platform | Entity Category | Notes |
|--------|----------|-----------------|-------|
| Robot SN | `sensor` | `diagnostic` | Partial redaction in diagnostics download |
| Firmware Version | `sensor` | `diagnostic` | From `DeviceMSG.firmware` |
| MQTT Connected | `binary_sensor` | `diagnostic` | Connectivity to on-board broker |
| Last Seen | `sensor` | `diagnostic` | Timestamp of last `DeviceMSG` |
| Signal Strength | `sensor` | `diagnostic` | WiFi RSSI in dBm |

## Multi-Head Dynamic Entities

Availability is gated by `head_type`. Entities show as `unavailable` when the installed head does not support them. See `multi-head.md` for head type values.

| Entity | Platform | Required Head Types |
|--------|----------|-------------------|
| Blade Speed | `number` | 1, 2 (LawnMower) |
| Roller | `switch` | 0 (SnowBlower) |
| Blower | `switch` | 0, 3 (Snow/Leaf) |
| Lawn Mower | `lawn_mower` | 1, 2 (v0.4+) |
| Chute Angle | `sensor` | 0 (SnowBlower) |
| Chute Velocity | `number` | 0 (SnowBlower) |
| SAM Status | `sensor` | 4 (SmartCover) |

## Entity Naming Convention

Entities are named `{device_name} {entity_name}` by default.

Example: device named "Yarbo Front Yard" → `sensor.yarbo_front_yard_battery`.
