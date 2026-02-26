# Service Reference

All services are registered under the `yarbo` domain. They require a `device_id` or `entity_id` targeting a Yarbo device.

## `yarbo.send_command`

Send an arbitrary low-level MQTT command to the robot. Intended for advanced users and debugging.

Available: **v0.1.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |
| `command` | `str` | Yes | Command name (e.g., `dstop`, `cmd_buzzer`) |
| `payload` | `dict` | No | JSON payload merged with command envelope |

```yaml
action: yarbo.send_command
data:
  device_id: "abc123def456"
  command: "cmd_buzzer"
  payload:
    enable: true
```

## `yarbo.start_plan`

Start execution of a saved mowing or snow plan.

Available: **v0.3.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |
| `plan_id` | `str` | Yes | Plan UUID from the Yarbo app |
| `head_type` | `int` | No | Assert head type before starting (aborts if mismatch) |

```yaml
action: yarbo.start_plan
data:
  device_id: "abc123def456"
  plan_id: "plan-uuid-1234-abcd"
  head_type: 0
```

## `yarbo.pause`

Pause the currently running job. Equivalent to pressing the Pause button entity.

Available: **v0.1.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |

```yaml
action: yarbo.pause
data:
  device_id: "abc123def456"
```

## `yarbo.resume`

Resume a paused job.

Available: **v0.1.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |

```yaml
action: yarbo.resume
data:
  device_id: "abc123def456"
```

## `yarbo.return_to_dock`

Command the robot to return to the docking station.

Available: **v0.1.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |

```yaml
action: yarbo.return_to_dock
data:
  device_id: "abc123def456"
```

## `yarbo.set_lights`

Set brightness for one or more of the 7 LED channels.

Available: **v0.2.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |
| `channel` | `int` | No | LED channel 1–7. Omit to set all channels. |
| `brightness` | `int` | Yes | Brightness value 0–255 |

```yaml
# Set all lights to 50% brightness
action: yarbo.set_lights
data:
  device_id: "abc123def456"
  brightness: 128

# Set only channel 3 to full brightness
action: yarbo.set_lights
data:
  device_id: "abc123def456"
  channel: 3
  brightness: 255
```

## `yarbo.set_chute_velocity`

Set the snow chute rotation velocity. Only effective when head_type is 0 (SnowBlower).

Available: **v0.2.0+**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | `str` | Yes | Target Yarbo device |
| `velocity` | `int` | Yes | Velocity in range -2000 to 2000. Negative = clockwise, positive = counter-clockwise. |

```yaml
action: yarbo.set_chute_velocity
data:
  device_id: "abc123def456"
  velocity: 1500
```

## Service Response Values

Services that trigger a command return immediately after the MQTT publish. They do not wait for robot acknowledgment. Monitor the `activity` sensor or `data_feedback` topic to confirm execution.

Commands are serialized through an `asyncio.Lock` per device to prevent interleaved MQTT publishes.
