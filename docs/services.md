---
layout: default
title: Services
nav_order: 5
description: "Home Assistant services provided by the Yarbo integration"
---

# Services
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

All services are registered under the `yarbo` domain. They require a `device_id` targeting a Yarbo device.

1. TOC
{:toc}

---

## yarbo.send_command

Send a raw MQTT command to the robot. For advanced users who want to send commands not yet exposed as entities.

> Commands are zlib-compressed automatically by the `python-yarbo` library.
{: .note }

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot to send the command to |
| `command` | string | Yes | The MQTT command name (e.g. `read_all_plan`, `cmd_recharge`) |
| `payload` | object | No | JSON payload for the command. Defaults to `{}` |

**Example — read all work plans:**

```yaml
service: yarbo.send_command
data:
  device_id: "YOUR_DEVICE_ID"
  command: read_all_plan
  payload: {}
```

**Example — set blade speed:**

```yaml
service: yarbo.send_command
data:
  device_id: "YOUR_DEVICE_ID"
  command: set_blade_speed
  payload:
    speed: 2000
```

**Example — set chute angle (snow blower):**

```yaml
service: yarbo.send_command
data:
  device_id: "YOUR_DEVICE_ID"
  command: cmd_chute
  payload:
    angle: 105
```

---

## yarbo.start_plan

Start a saved work plan by its ID.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |
| `plan_id` | string | Yes | The UUID or numeric ID of the work plan |
| `percent` | number (0–100) | No | Percentage into the plan at which to start. Defaults to the value of the Plan Start Percent number entity |

**Example — start a plan from the beginning:**

```yaml
service: yarbo.start_plan
data:
  device_id: "YOUR_DEVICE_ID"
  plan_id: "1"
```

**Example — resume a plan from 50%:**

```yaml
service: yarbo.start_plan
data:
  device_id: "YOUR_DEVICE_ID"
  plan_id: "1"
  percent: 50
```

**Example — start plan in an automation triggered by a calendar event:**

```yaml
automation:
  alias: "Start mowing on schedule"
  trigger:
    - platform: calendar
      event: start
      entity_id: calendar.mowing_schedule
  action:
    - service: yarbo.start_plan
      data:
        device_id: "YOUR_DEVICE_ID"
        plan_id: "1"
```

---

## yarbo.pause

Pause the robot's current work plan.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |

**Example:**

```yaml
service: yarbo.pause
data:
  device_id: "YOUR_DEVICE_ID"
```

---

## yarbo.resume

Resume a previously paused work plan.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |

**Example:**

```yaml
service: yarbo.resume
data:
  device_id: "YOUR_DEVICE_ID"
```

---

## yarbo.return_to_dock

Send the robot back to its charging dock.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |

**Example:**

```yaml
service: yarbo.return_to_dock
data:
  device_id: "YOUR_DEVICE_ID"
```

**Example — return to dock when battery drops below 20%:**

```yaml
automation:
  alias: "Return Yarbo to dock on low battery"
  trigger:
    - platform: numeric_state
      entity_id: sensor.yarbo_allgott_battery
      below: 20
  action:
    - service: yarbo.return_to_dock
      data:
        device_id: "YOUR_DEVICE_ID"
```

---

## yarbo.set_lights

Set brightness for all 7 LED channels simultaneously or individually. Useful for automations that change the light pattern.

**Fields:**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `device_id` | Device selector | — | The Yarbo robot |
| `brightness` | number | 0–255 | Set all channels to this value |
| `led_head` | number | 0–255 | Head light brightness |
| `led_left_w` | number | 0–255 | Left fill light brightness |
| `led_right_w` | number | 0–255 | Right fill light brightness |
| `body_left_r` | number | 0–255 | Left body accent brightness |
| `body_right_r` | number | 0–255 | Right body accent brightness |
| `tail_left_r` | number | 0–255 | Left tail light brightness |
| `tail_right_r` | number | 0–255 | Right tail light brightness |

**Example — turn all lights on at full brightness:**

```yaml
service: yarbo.set_lights
data:
  device_id: "YOUR_DEVICE_ID"
  brightness: 255
```

**Example — turn all lights off:**

```yaml
service: yarbo.set_lights
data:
  device_id: "YOUR_DEVICE_ID"
  brightness: 0
```

**Example — custom channel values:**

```yaml
service: yarbo.set_lights
data:
  device_id: "YOUR_DEVICE_ID"
  led_head: 255
  led_left_w: 128
  led_right_w: 128
  body_left_r: 0
  body_right_r: 0
  tail_left_r: 64
  tail_right_r: 64
```

---

## yarbo.set_chute_velocity

Control the snow chute direction and rotation speed (Snow Blower head only).

**Fields:**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `device_id` | Device selector | — | The Yarbo robot |
| `velocity` | number | −2000 to 2000 | Chute rotation velocity. Negative = left, 0 = stop, positive = right |

**Example — rotate chute to the right:**

```yaml
service: yarbo.set_chute_velocity
data:
  device_id: "YOUR_DEVICE_ID"
  velocity: 1000
```

**Example — stop chute rotation:**

```yaml
service: yarbo.set_chute_velocity
data:
  device_id: "YOUR_DEVICE_ID"
  velocity: 0
```

---

## yarbo.manual_drive

Send manual velocity commands to drive the robot. Use with caution in open areas.

> The robot must be in manual mode. Use the [Return to Dock](entities.md#buttons) button to stop.
{: .note }

**Fields:**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `device_id` | Device selector | — | The Yarbo robot |
| `linear` | number | −1.0 to 1.0 | Linear velocity (positive = forward) |
| `angular` | number | −1.0 to 1.0 | Angular velocity (positive = turn left) |

**Example — drive forward slowly:**

```yaml
service: yarbo.manual_drive
data:
  device_id: "YOUR_DEVICE_ID"
  linear: 0.3
  angular: 0.0
```

**Example — stop:**

```yaml
service: yarbo.manual_drive
data:
  device_id: "YOUR_DEVICE_ID"
  linear: 0.0
  angular: 0.0
```

---

## yarbo.go_to_waypoint

Navigate the robot to a stored waypoint by index.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |
| `index` | number | Yes | Waypoint index (0–9999) |

**Example:**

```yaml
service: yarbo.go_to_waypoint
data:
  device_id: "YOUR_DEVICE_ID"
  index: 0
```

---

## yarbo.delete_plan

Delete a single saved work plan by ID.

> **Warning:** This permanently removes the plan from the robot. There is no undo.
{: .warning }

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |
| `plan_id` | string | Yes | Plan ID to delete (must match exactly) |

**Example:**

```yaml
service: yarbo.delete_plan
data:
  device_id: "YOUR_DEVICE_ID"
  plan_id: "1"
```

---

## yarbo.delete_all_plans

Delete all saved work plans on the robot.

> **Warning:** This permanently removes ALL plans. There is no undo.
{: .warning }

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | Device selector | Yes | The Yarbo robot |

**Example:**

```yaml
service: yarbo.delete_all_plans
data:
  device_id: "YOUR_DEVICE_ID"
```

---

## Finding Your Device ID

To use services, you need the `device_id` for your robot:

1. Go to **Settings → Devices & Services → Yarbo → [your robot]**
2. Copy the device ID from the URL (`/config/devices/device/<device_id>`)

Or use the **Developer Tools → Services** UI to select the device visually.

---

## Related Pages

- [Entities](entities.md) — for state-based control via entity services
- [Automations](automations.md) — ready-to-use automation examples
- [Protocol Reference](protocol-reference.md) — raw MQTT command reference for `send_command`
