# Automation Blueprints

Blueprints are stored in `blueprints/automation/yarbo/`. They work with any HA weather or sensor provider.

## 1. Pause on Rain

**File**: `blueprints/automation/yarbo/pause_on_rain.yaml`

Pauses the robot and sends it to dock when rain is detected, then optionally resumes after rain stops and a dry delay elapses.

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `yarbo_device` | `device` | — | Target Yarbo device |
| `rain_sensor` | `entity` | — | Binary sensor (moisture/rain) that turns `on` when raining |
| `dry_delay_minutes` | `int` | `30` | Minutes to wait after rain stops before resuming |
| `auto_resume` | `bool` | `true` | Automatically resume job after dry delay |

### Behavior

1. When `rain_sensor` turns `on` and robot `activity` is `mowing` or `snow_blowing`:
   - Call `yarbo.pause`
   - Call `yarbo.return_to_dock`
   - Fire notification (if notify target provided)
2. When `rain_sensor` turns `off`:
   - Wait `dry_delay_minutes`
   - If `auto_resume` is true and robot is still docked: call `yarbo.resume`

```yaml
blueprint:
  name: "Yarbo: Pause on Rain"
  domain: automation
  input:
    yarbo_device:
      selector:
        device:
          integration: yarbo
    rain_sensor:
      selector:
        entity:
          device_class: moisture
```

## 2. Snow Deployment

**File**: `blueprints/automation/yarbo/snow_deployment.yaml`

Sends a notification (and optionally starts a plan) when a snowfall forecast exceeds a threshold.

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `yarbo_device` | `device` | — | Target Yarbo device |
| `weather_entity` | `entity` | — | Weather entity with forecast support |
| `snowfall_threshold_cm` | `float` | `2.5` | Minimum expected snowfall to trigger |
| `notify_target` | `str` | — | Notification target (e.g., `notify.mobile_app`) |
| `auto_start_plan` | `bool` | `false` | Automatically start a saved plan |
| `plan_id` | `str` | — | Plan UUID to start (required if auto_start enabled) |

### Notes

- Uses HA's `weather.get_forecasts` to check hourly or daily snowfall accumulation.
- Only triggers once per forecast event (uses `input_boolean` helper to track state).
- Works with any HA-compatible weather provider (Met.no, OpenWeatherMap, AccuWeather, etc.).

## 3. Low Battery Notification

**File**: `blueprints/automation/yarbo/low_battery_notify.yaml`

Notifies when the robot battery drops below a configurable threshold while the robot is not docked.

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `yarbo_device` | `device` | — | Target Yarbo device |
| `battery_threshold` | `int` | `20` | Battery percentage to trigger notification |
| `notify_target` | `str` | — | Notification service target |
| `notify_message` | `str` | `"Yarbo battery is low ({battery}%)"` | Notification message template |

### Notes

- Fires at most once per job (tracks via automation mode `single`).
- Resets when robot docks and begins charging.
- Also available as a built-in HA event trigger: `yarbo_low_battery`.

## 4. Job Complete Notification

**File**: `blueprints/automation/yarbo/job_complete_notify.yaml`

Sends a notification when the robot finishes a job and returns to the dock.

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `yarbo_device` | `device` | — | Target Yarbo device |
| `notify_target` | `str` | — | Notification service target |
| `include_duration` | `bool` | `true` | Include job duration in message |
| `notify_message` | `str` | `"Yarbo finished! Job took {duration}."` | Message template |

### Behavior

Triggers on the `event` entity when `event_type` is `yarbo_job_completed`. Extracts `duration_seconds` from the event data to populate the message template.

```yaml
# Example trigger block from blueprint
trigger:
  - platform: event
    event_type: yarbo_job_completed
    event_data:
      device_id: !input yarbo_device
action:
  - variables:
      duration: >
        {{ (trigger.event.data.duration_seconds // 60) | string + " minutes" }}
  - action: !input notify_target
    data:
      message: !input notify_message
```

## Blueprint Usage Notes

- Import blueprints via **Settings → Automations & Scenes → Blueprints → Import Blueprint**.
- URL: `https://github.com/your-org/ha-yarbo-forge/blob/main/blueprints/automation/yarbo/{filename}.yaml`
- All blueprints are mode `single` by default to prevent duplicate triggers.
