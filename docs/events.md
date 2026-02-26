# Events

The integration fires events on the HA event bus and exposes an `event` platform entity for use in automations.

## Event Entity

Each Yarbo device exposes a single event entity:

- **Entity ID**: `event.{device_name}_events`
- **Unique ID**: `{robot_sn}_events`

The entity's `event_types` attribute lists all possible event type strings. The `event_type` state attribute reflects the most recently fired event.

```yaml
# Example entity state
entity_id: event.yarbo_front_yard_events
state: "2024-01-15T10:30:00+00:00"
attributes:
  event_type: yarbo_job_completed
  event_types:
    - yarbo_job_started
    - yarbo_job_completed
    - yarbo_job_paused
    - yarbo_error
    - yarbo_head_changed
    - yarbo_low_battery
    - yarbo_controller_lost
```

## Event Definitions

### `yarbo_job_started`

Fired when a job transitions from `idle` or `paused` to an active working state.

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `plan_id` | `str \| None` | Plan UUID if started via plan |
| `head_type` | `int` | Head type integer at job start |
| `timestamp` | `str` | ISO 8601 timestamp |

### `yarbo_job_completed`

Fired when a job finishes normally (robot returns to dock after completing plan).

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `plan_id` | `str \| None` | Completed plan UUID |
| `duration_seconds` | `int` | Elapsed job time |
| `timestamp` | `str` | ISO 8601 timestamp |

### `yarbo_job_paused`

Fired when a running job is paused (by command or automatically).

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `reason` | `str` | `"command"`, `"rain"`, `"low_battery"`, `"error"` |
| `timestamp` | `str` | ISO 8601 timestamp |

### `yarbo_error`

Fired when the `problem` binary sensor transitions to `on`.

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `error_code` | `int` | Raw error code from `DeviceMSG` |
| `error_description` | `str` | Human-readable description |
| `timestamp` | `str` | ISO 8601 timestamp |

### `yarbo_head_changed`

Fired when `head_type` changes between telemetry messages.

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `previous_head` | `int` | Previous head type integer |
| `new_head` | `int` | New head type integer |
| `timestamp` | `str` | ISO 8601 timestamp |

### `yarbo_low_battery`

Fired when battery drops below 20% while not charging.

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `battery_level` | `int` | Current battery percentage |
| `timestamp` | `str` | ISO 8601 timestamp |

### `yarbo_controller_lost`

Fired when the integration loses the MQTT controller role (another client claimed it).

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | HA device registry ID |
| `robot_sn` | `str` | Robot serial number |
| `timestamp` | `str` | ISO 8601 timestamp |

## Automation Trigger Examples

```yaml
# Trigger on job completion
trigger:
  - platform: event
    event_type: yarbo_job_completed
    event_data:
      robot_sn: "YB2024XXXXXXXX"

# Trigger on any error
trigger:
  - platform: state
    entity_id: event.yarbo_front_yard_events
    attribute: event_type
    to: "yarbo_error"

# Trigger via event entity (recommended for UI-based automations)
trigger:
  - platform: event
    event_type: state_changed
    event_data:
      entity_id: event.yarbo_front_yard_events
```

## Event Bus vs. Event Entity

| Mechanism | Best For |
|-----------|----------|
| HA event bus (`yarbo_*`) | Script/automation triggers, Node-RED, AppDaemon |
| `event` entity | UI-based automations, logbook, history |

Both are fired for every event; they are not mutually exclusive.
