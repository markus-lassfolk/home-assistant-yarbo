---
layout: default
title: Entities
nav_order: 4
description: "Every entity created by the Yarbo integration"
---

# Entities
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

The integration creates entities across multiple platforms. Most operational entities are enabled by default; diagnostic entities are disabled by default and can be enabled individually.

Entities marked **🔵** are enabled by default. Entities marked **⚪** are disabled by default.

1. TOC
{:toc}

---

## Sensors

### Core Status

| Entity | Key | Device Class | Unit | Default | Description |
|--------|-----|-------------|------|---------|-------------|
| Battery | `battery` | `battery` | `%` | 🔵 | Battery percentage (0–100) |
| Activity | `activity` | `enum` | — | 🔵 | Current robot activity: `charging`, `idle`, `working`, `paused`, `returning`, `error` |
| Head Type | `head_type` | `enum` | — | 🔵 | Installed head: `snow_blower`, `lawn_mower`, `lawn_mower_pro`, `leaf_blower`, `smart_cover`, `trimmer`, `none` |
| Plan Remaining Time | `plan_remaining_time` | `duration` | `s` | 🔵 | Estimated seconds remaining in the active work plan |
| Connection | `connection` | — | — | 🔵 | Active MQTT endpoint label and IP (diagnostic) |

**Activity states:**

| State | Meaning |
|-------|---------|
| `charging` | Robot is on the dock and charging |
| `idle` | Robot is awake but not working and not charging |
| `working` | A work plan is actively running |
| `paused` | A work plan is paused |
| `returning` | Robot is returning to the dock |
| `error` | An error code is active |

### GPS / RTK

| Entity | Key | Device Class | Unit | Default | Description |
|--------|-----|-------------|------|---------|-------------|
| Heading | `heading` | — | `°` | ⚪ | Compass heading in degrees (0–360) |
| Heading DOP | `heading_dop` | — | — | ⚪ | Dilution of precision for heading (diagnostic) |
| Heading Status | `heading_status` | — | — | ⚪ | RTK heading solution status (diagnostic) |
| RTK Status | `rtk_status` | `enum` | — | ⚪ | GPS fix quality: `invalid`, `gps`, `dgps`, `rtk_float`, `rtk_fixed`, `unknown` |
| Satellite Count | `satellite_count` | — | — | ⚪ | Number of GNSS satellites in view (diagnostic) |
| GPS Fix Quality | `gps_fix_quality` | — | — | ⚪ | Raw GGA fix quality indicator (diagnostic) |
| GPS HDOP | `gps_hdop` | — | — | ⚪ | Horizontal dilution of precision (diagnostic) |
| GPS Altitude | `gps_altitude` | `distance` | `m` | ⚪ | Altitude above sea level in metres (diagnostic) |
| RTCM Age | `rtcm_age` | — | `s` | ⚪ | Age of RTCM correction data in seconds (diagnostic) |
| RTCM Source Type | `rtcm_source_type` | — | — | ⚪ | Current RTCM correction source type (diagnostic) |
| Antenna Distance | `antenna_distance` | `distance` | `m` | ⚪ | Baseline distance between GNSS antennas (diagnostic) |

### Odometry

| Entity | Key | Device Class | Unit | Default | Description |
|--------|-----|-------------|------|---------|-------------|
| Odometry X | `odom_x` | — | `m` | ⚪ | X position in local odometry frame (diagnostic) |
| Odometry Y | `odom_y` | — | `m` | ⚪ | Y position in local odometry frame (diagnostic) |
| Odometry Phi | `odom_phi` | — | `rad` | ⚪ | Heading in local odometry frame (diagnostic) |
| Odometry Confidence | `odom_confidence` | — | — | ⚪ | Fusion confidence score 0.0–1.0 (diagnostic) |
| Odometer | `odometer` | `distance` | `m` | ⚪ | Total distance traveled, always-increasing (diagnostic) |
| Speed | `speed` | `speed` | `m/s` | ⚪ | Current travel speed (diagnostic) |

### Charging

| Entity | Key | Device Class | Unit | Default | Description |
|--------|-----|-------------|------|---------|-------------|
| Charging Power | `charging_power` | `power` | `W` | ⚪ | Wireless charging power (voltage × current) |
| Charge Voltage | `charge_voltage` | `voltage` | `V` | ⚪ | Wireless charging voltage (diagnostic) |
| Charge Current | `charge_current` | `current` | `A` | ⚪ | Wireless charging current (diagnostic) |
| Wireless Charge State | `wireless_charge_state` | — | — | ⚪ | Wireless charging state code (diagnostic) |
| Wireless Charge Error | `wireless_charge_error` | — | — | ⚪ | Wireless charging error code (0 = no error) (diagnostic) |

### Battery Health

| Entity | Key | Device Class | Unit | Default | Description |
|--------|-----|-------------|------|---------|-------------|
| Battery Cell Temp Min | `battery_cell_temp_min` | `temperature` | `°C` | ⚪ | Minimum cell temperature (diagnostic) |
| Battery Cell Temp Max | `battery_cell_temp_max` | `temperature` | `°C` | ⚪ | Maximum cell temperature (diagnostic) |
| Battery Cell Temp Avg | `battery_cell_temp_avg` | `temperature` | `°C` | ⚪ | Average cell temperature (diagnostic) |
| Battery Temp Error | `battery_temp_error` | — | — | ⚪ | Temperature error flag from BMS (diagnostic) |
| Motor Temperature | `motor_temp` | `temperature` | `°C` | ⚪ | Motor temperature (diagnostic) |
| Body Current | `body_current` | `current` | `A` | ⚪ | Main body drive current (diagnostic) |
| Head Current | `head_current` | `current` | `A` | ⚪ | Head attachment current draw (diagnostic) |

### Environment

| Entity | Key | Unit | Default | Description |
|--------|-----|------|---------|-------------|
| Rain Sensor | `rain_sensor` | — | ⚪ | Raw rain sensor reading (0 = dry, higher = wet) |
| Ultrasonic Left Front | `ultrasonic_left_front` | `mm` | 🔵 | Left-front obstacle distance |
| Ultrasonic Middle | `ultrasonic_middle` | `mm` | 🔵 | Front obstacle distance |
| Ultrasonic Right Front | `ultrasonic_right_front` | `mm` | 🔵 | Right-front obstacle distance |

### Head-Specific Sensors

| Entity | Key | Unit | Default | Head | Description |
|--------|-----|------|---------|------|-------------|
| Chute Angle | `chute_angle` | `°` | ⚪ | Snow Blower | Current snow chute angle |
| Chute Steering Info | `chute_steering_info` | — | ⚪ | Snow Blower | Chute steering engine position (diagnostic) |

### System / Network

| Entity | Key | Default | Description |
|--------|-----|---------|-------------|
| WiFi Network | `wifi_network` | ⚪ | Currently connected WiFi SSID (diagnostic) |
| WiFi List | `wifi_list` | ⚪ | Number of visible WiFi networks; attributes contain full list (config) |
| Schedule Count | `schedule_count` | ⚪ | Number of saved schedules; attributes contain schedule data (diagnostic) |
| Map Backup Count | `map_backup_count` | ⚪ | Number of stored map backups; attributes list them (config) |
| Clean Area Count | `clean_area_count` | ⚪ | Number of defined clean areas (diagnostic) |
| Recharge Point | `recharge_point` | ⚪ | Charging dock location status (config) |
| MQTT Age | `mqtt_age` | ⚪ | Seconds since last MQTT telemetry message (diagnostic) |
| Error Code | `error_code` | ⚪ | Raw error code (0 = no error) (diagnostic) |
| Machine Controller | `machine_controller` | ⚪ | Controller state from StateMSG (diagnostic) |
| Base Station Status | `base_station_status` | ⚪ | Docking station status code (diagnostic) |
| Head Serial | `head_serial` | ⚪ | Serial number of the installed head attachment (diagnostic) |
| Product Code | `product_code` | ⚪ | Robot product code string (diagnostic) |
| Hub Info | `hub_info` | ⚪ | Hub board firmware information (diagnostic) |

### Network Routing (Diagnostic)

| Entity | Key | Default | Description |
|--------|-----|---------|-------------|
| Route Priority hg0 | `route_priority_hg0` | ⚪ | HaLow interface routing priority (lower = preferred) |
| Route Priority wlan0 | `route_priority_wlan0` | ⚪ | Wi-Fi interface routing priority |
| Route Priority wwan0 | `route_priority_wwan0` | ⚪ | Cellular interface routing priority |
| Nav Sensor Front Right | `nav_sensor_front_right` | ⚪ | Electric navigation front-right sensor raw value |
| Nav Sensor Rear Right | `nav_sensor_rear_right` | ⚪ | Electric navigation rear-right sensor raw value |
| Head Gyro Pitch | `head_gyro_pitch` | ⚪ | Head attachment pitch angle in degrees |
| Head Gyro Roll | `head_gyro_roll` | ⚪ | Head attachment roll angle in degrees |

---

## Binary Sensors

| Entity | Key | Device Class | Default | Description |
|--------|-----|-------------|---------|-------------|
| Charging | `charging` | `battery_charging` | 🔵 | `on` when robot is charging (`charging_status` ∈ {1, 2, 3}) |
| Problem | `problem` | `problem` | 🔵 | `on` when `error_code` ≠ 0 |
| Planning Active | `planning_active` | — | ⚪ | `on` when a work plan is actively running |
| Planning Paused | `planning_paused` | — | ⚪ | `on` when a work plan is paused |
| Returning to Charge | `returning_to_charge` | — | ⚪ | `on` when robot is returning to dock |
| Going to Start | `going_to_start` | — | ⚪ | `on` when robot is navigating to the plan start point |
| Follow Mode | `follow_mode` | — | ⚪ | `on` when robot follow mode is active |
| Manual Controller | `manual_controller` | — | ⚪ | `on` when a manual controller (gamepad) is active |
| Rain Detected | `rain_detected` | `moisture` | ⚪ | `on` when the rain sensor detects moisture |
| No-Charge Period | `no_charge_period` | — | ⚪ | `on` when a no-charge schedule window is currently active; attributes include start/end times |

---

## Buttons

| Entity | Key | Category | Default | Description |
|--------|-----|----------|---------|-------------|
| Beep | `beep` | — | 🔵 | Sound the buzzer once |
| Return to Dock | `return_to_dock` | — | 🔵 | Send robot to charging dock |
| Pause | `pause` | — | 🔵 | Pause the active work plan |
| Resume | `resume` | — | 🔵 | Resume a paused work plan |
| Stop | `stop` | — | 🔵 | Graceful stop (finish current move, then halt) |
| Emergency Stop | `emergency_stop` | — | ⚪ | Immediate hardware emergency stop |
| Emergency Unlock | `emergency_unlock` | — | 🔵 | Release emergency stop lock |
| Play Sound | `play_sound` | — | 🔵 | Play default robot sound |
| Manual Stop | `manual_stop` | — | 🔵 | Stop manual drive (zero velocity) |
| Shutdown | `shutdown` | Config | 🔵 | Power off robot (physical restart required to wake) |
| Restart | `restart` | Config | 🔵 | Restart robot software containers (~30 s offline) |
| Save Charging Point | `save_charging_point` | Config | ⚪ | Save current position as the charging dock location |
| Start Hotspot | `start_hotspot` | Config | ⚪ | Start robot Wi-Fi hotspot |
| Save Map Backup | `save_map_backup` | Config | ⚪ | Create a map backup on the robot |

> **Shutdown** powers off the robot hardware. A physical button press is required to restart.
> **Restart** restarts the robot's software. The robot goes offline for ~30 seconds then reconnects automatically.
{: .note }

---

## Switches

| Entity | Key | Category | Default | Head | Description |
|--------|-----|----------|---------|------|-------------|
| Buzzer | `buzzer` | — | ⚪ | All | Activate/deactivate the built-in buzzer (assumed state) |
| Follow Mode | `follow_mode` | — | 🔵 | All | Toggle follow-me mode |
| Heating Film | `heating_film` | Config | 🔵 | All | Toggle heating film (prevents ice buildup in winter) |
| Person Detection | `person_detect` | Config | ⚪ | All | Toggle person/obstacle detection via camera |
| Ignore Obstacles | `ignore_obstacles` | Config | ⚪ | All | Bypass obstacle detection during active plan |
| Camera | `camera` | Config | ⚪ | All | Toggle camera module on/off |
| Laser | `laser` | Config | ⚪ | All | Toggle laser sensor |
| USB | `usb` | Config | ⚪ | All | Toggle USB power output port |
| Auto Update | `auto_update` | Config | ⚪ | All | Toggle automatic firmware update |
| Camera OTA | `camera_ota` | Config | ⚪ | All | Allow camera module OTA firmware updates |
| Draw Mode | `draw_mode` | Config | ⚪ | All | Toggle boundary drawing mode |
| Module Lock | `module_lock` | Config | ⚪ | All | Toggle module attachment lock |
| Wire Charging Lock | `wire_charging_lock` | Config | ⚪ | All | Toggle wired charging lock |
| Roof Lights | `roof_lights` | Config | ⚪ | All | Enable/disable roof LED lights |
| Sound Enable | `sound_enable` | Config | ⚪ | All | Enable/disable robot sounds globally |
| Motor Protect | `motor_protect` | Config | ⚪ | All | Toggle motor thermal protection |
| Smart Blowing | `smart_blowing` | Config | ⚪ | Leaf Blower only | Intelligent auto-blowing mode |
| Edge Blowing | `edge_blowing` | Config | ⚪ | Leaf Blower only | Edge-focused blowing mode |
| Trimmer | `trimmer` | — | 🔵 | Trimmer only | Toggle trimmer blade engagement |
| Mower Head Sensor | `mower_head_sensor` | Config | ⚪ | Lawn Mower only | Toggle mower head collision sensor |

> All switches use **assumed state** — the integration reflects what was last sent, not actual hardware state.
{: .note }

---

## Number Entities

| Entity | Key | Range | Step | Category | Head | Description |
|--------|-----|-------|------|----------|------|-------------|
| Chute Velocity | `chute_velocity` | −2000 to 2000 | 1 | — | Snow Blower | Chute rotation speed (negative = left, positive = right); disabled by default |
| Chute Steering Work | `chute_steering_work` | −90° to 90° | 5° | Config | Snow Blower | Chute steering angle during active work |
| Blade Height | `blade_height` | 25–75 mm | 5 | Config | Lawn Mower | Cutting height |
| Blade Speed | `blade_speed` | 1000–3500 RPM | 100 | Config | Lawn Mower | Blade rotation speed |
| Roller Speed | `roller_speed` | 0–3500 RPM | 100 | Config | Lawn Mower | Roller/drum speed; disabled by default |
| Blower Speed | `blower_speed` | 1–10 | 1 | Config | Leaf Blower | Blower motor speed level; disabled by default |
| Volume | `volume` | 0–100 | 1 | Config | All | Speaker volume |
| Plan Start Percent | `plan_start_percent` | 0–100% | 1 | Config | All | Percentage into the plan at which to start; value is persisted across restarts |
| Battery Charge Min | `battery_charge_min` | 0–100% | 5 | Config | All | Minimum charge level before leaving dock; disabled by default |
| Battery Charge Max | `battery_charge_max` | 0–100% | 5 | Config | All | Maximum charge level (battery limit); disabled by default |

---

## Select Entities

| Entity | Key | Options | Default | Head | Description |
|--------|-----|---------|---------|------|-------------|
| Work Plan | `work_plan` | (saved plan names loaded from robot) | 🔵 | All | Select and start a saved work plan by name |
| Turn Type | `turn_type` | `u_turn`, `three_point`, `zero_radius` | 🔵 | All | Mowing pattern turn type |
| Snow Push Direction | `snow_push_direction` | `left`, `right`, `center` | 🔵 | Snow Blower only | Snow throw direction |

---

## Light Entities

| Entity | Key | Mode | Default | Description |
|--------|-----|------|---------|-------------|
| Lights (all channels) | `lights` | Brightness (0–255) | 🔵 | Sets all 7 LED channels simultaneously |
| Head Light | `head_light` | On/Off | 🔵 | Front/head LED; only available when a head is attached |
| LED Head | `light_led_head` | Brightness (0–255) | ⚪ | Head LED channel |
| LED Left White | `light_led_left_w` | Brightness (0–255) | ⚪ | Left fill light |
| LED Right White | `light_led_right_w` | Brightness (0–255) | ⚪ | Right fill light |
| LED Body Left | `light_led_body_left` | Brightness (0–255) | ⚪ | Left body accent light |
| LED Body Right | `light_led_body_right` | Brightness (0–255) | ⚪ | Right body accent light |
| LED Tail Left | `light_led_tail_left` | Brightness (0–255) | ⚪ | Left tail light |
| LED Tail Right | `light_led_tail_right` | Brightness (0–255) | ⚪ | Right tail light |

> Light entities use **assumed state** — there is no readback from the robot hardware.
{: .note }

---

## Lawn Mower Entity

| Entity | Key | Default | Description |
|--------|-----|---------|-------------|
| Mower | `mower` | 🔵 | Native HA lawn mower card entity (only available when Lawn Mower or Lawn Mower Pro head is installed) |

**Activity mapping:**

| HA Activity | Yarbo State |
|-------------|-------------|
| `mowing` | State 1, 7, or 8 (active plan) |
| `paused` | State 5 |
| `docked` | Charging, state 2, or default |
| `error` | Any non-zero error code |

Supports: **Start mowing**, **Pause**, **Dock** (return to charge).

---

## Device Tracker

| Entity | Key | Source Type | Default | Description |
|--------|-----|------------|---------|-------------|
| Location | `location` | `gps` | 🔵 | GPS coordinates from RTK/GNSS telemetry. Reports "home" when charging, "not_home" otherwise. |

---

## Entity Naming

All entity IDs follow the pattern: `<platform>.<device_name>_<entity_key>`

Example: `sensor.yarbo_allgott_battery`, `button.yarbo_allgott_return_to_dock`

The device name is derived from the friendly name set during setup.

---

## Related Pages

- [Multi-Head Guide](multi-head.md) — which entities are available per head type
- [Services](services.md) — HA services for advanced control
- [Automations](automations.md) — automation examples
