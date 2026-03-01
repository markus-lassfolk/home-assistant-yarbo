---
layout: default
title: Automations
nav_order: 6
description: "Example Home Assistant automations for the Yarbo integration"
---

# Automations
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

Ready-to-use automation examples for common Yarbo scenarios. Replace `YOUR_DEVICE_ID` with your actual device ID and adjust entity IDs to match your robot's name.

1. TOC
{:toc}

---

## Basic Control

### Return to Dock on Low Battery

```yaml
automation:
  alias: "Yarbo: Return to dock on low battery"
  description: "Automatically sends the robot home when battery drops below 20%"
  trigger:
    - platform: numeric_state
      entity_id: sensor.yarbo_allgott_battery
      below: 20
  condition:
    - condition: state
      entity_id: sensor.yarbo_allgott_activity
      state: "working"
  action:
    - service: yarbo.return_to_dock
      data:
        device_id: "YOUR_DEVICE_ID"
```

### Pause When Rain Detected

```yaml
automation:
  alias: "Yarbo: Pause when rain detected"
  description: "Pauses the robot if rain is detected while working"
  trigger:
    - platform: state
      entity_id: binary_sensor.yarbo_allgott_rain_detected
      to: "on"
  condition:
    - condition: state
      entity_id: sensor.yarbo_allgott_activity
      state: "working"
  action:
    - service: yarbo.pause
      data:
        device_id: "YOUR_DEVICE_ID"
    - service: notify.mobile_app
      data:
        message: "Yarbo paused — rain detected"
```

### Resume After Rain Stops

```yaml
automation:
  alias: "Yarbo: Resume after rain stops"
  description: "Resumes the robot 5 minutes after rain stops"
  trigger:
    - platform: state
      entity_id: binary_sensor.yarbo_allgott_rain_detected
      to: "off"
      for:
        minutes: 5
  condition:
    - condition: state
      entity_id: sensor.yarbo_allgott_activity
      state: "paused"
  action:
    - service: yarbo.resume
      data:
        device_id: "YOUR_DEVICE_ID"
```

---

## Scheduling

### Start Mowing on a Fixed Schedule

```yaml
automation:
  alias: "Yarbo: Start mowing Tuesday and Friday mornings"
  trigger:
    - platform: time
      at: "09:00:00"
  condition:
    - condition: time
      weekday:
        - tue
        - fri
    - condition: state
      entity_id: binary_sensor.yarbo_allgott_charging
      state: "on"
    - condition: numeric_state
      entity_id: sensor.yarbo_allgott_battery
      above: 80
  action:
    - service: yarbo.start_plan
      data:
        device_id: "YOUR_DEVICE_ID"
        plan_id: "1"
```

### Start Snow Blowing After Snowfall

```yaml
automation:
  alias: "Yarbo: Start snow blowing after snowfall"
  description: "Starts snow blowing when the weather integration reports snowfall has ended"
  trigger:
    - platform: state
      entity_id: weather.home
      from: "snowy"
      for:
        minutes: 30
  condition:
    - condition: state
      entity_id: sensor.yarbo_allgott_activity
      state: "idle"
    - condition: numeric_state
      entity_id: sensor.yarbo_allgott_battery
      above: 50
  action:
    - service: yarbo.start_plan
      data:
        device_id: "YOUR_DEVICE_ID"
        plan_id: "2"
    - service: notify.mobile_app
      data:
        message: "Yarbo started snow clearing"
```

---

## Notifications

### Notify When Work Completes

```yaml
automation:
  alias: "Yarbo: Notify when work plan finishes"
  trigger:
    - platform: state
      entity_id: sensor.yarbo_allgott_activity
      from: "working"
      to: "returning"
  action:
    - service: notify.mobile_app
      data:
        title: "Yarbo"
        message: "Work plan complete — robot returning to dock"
```

### Notify on Error

```yaml
automation:
  alias: "Yarbo: Alert on error"
  trigger:
    - platform: state
      entity_id: binary_sensor.yarbo_allgott_problem
      to: "on"
  action:
    - service: notify.mobile_app
      data:
        title: "Yarbo Alert"
        message: >
          Yarbo has reported a problem.
          Error code: {{ states('sensor.yarbo_allgott_error_code') }}.
          Please check the robot.
```

### Daily Status Report

```yaml
automation:
  alias: "Yarbo: Daily status notification"
  trigger:
    - platform: time
      at: "20:00:00"
  action:
    - service: notify.mobile_app
      data:
        title: "Yarbo Daily Status"
        message: >
          Battery: {{ states('sensor.yarbo_allgott_battery') }}%
          Status: {{ states('sensor.yarbo_allgott_activity') }}
          Head: {{ states('sensor.yarbo_allgott_head_type') }}
```

---

## Lights

### Turn on Lights at Sunset

```yaml
automation:
  alias: "Yarbo: Turn on lights at sunset"
  trigger:
    - platform: sun
      event: sunset
  condition:
    - condition: state
      entity_id: sensor.yarbo_allgott_activity
      state: "working"
  action:
    - service: light.turn_on
      target:
        entity_id: light.yarbo_allgott_lights
      data:
        brightness: 255
```

### Turn off Lights When Docked

```yaml
automation:
  alias: "Yarbo: Turn off lights when docked"
  trigger:
    - platform: state
      entity_id: sensor.yarbo_allgott_activity
      to: "charging"
  action:
    - service: light.turn_off
      target:
        entity_id: light.yarbo_allgott_lights
```

---

## Snow Blower Specific

### Adjust Chute Direction with Input Select

Create a helper `input_select.yarbo_chute_direction` with options: Left, Right, Center.

```yaml
automation:
  alias: "Yarbo: Set snow chute direction from input"
  trigger:
    - platform: state
      entity_id: input_select.yarbo_chute_direction
  action:
    - choose:
        - conditions:
            - condition: state
              entity_id: input_select.yarbo_chute_direction
              state: "Left"
          sequence:
            - service: yarbo.set_chute_velocity
              data:
                device_id: "YOUR_DEVICE_ID"
                velocity: -1000
        - conditions:
            - condition: state
              entity_id: input_select.yarbo_chute_direction
              state: "Right"
          sequence:
            - service: yarbo.set_chute_velocity
              data:
                device_id: "YOUR_DEVICE_ID"
                velocity: 1000
        - conditions:
            - condition: state
              entity_id: input_select.yarbo_chute_direction
              state: "Center"
          sequence:
            - service: yarbo.set_chute_velocity
              data:
                device_id: "YOUR_DEVICE_ID"
                velocity: 0
```

---

## Dashboard Card Examples

### Mower Control Card

```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.yarbo_allgott_activity
    name: Yarbo Status
  - type: entities
    entities:
      - sensor.yarbo_allgott_battery
      - sensor.yarbo_allgott_head_type
      - binary_sensor.yarbo_allgott_charging
      - binary_sensor.yarbo_allgott_problem
  - type: grid
    columns: 3
    cards:
      - type: button
        entity: button.yarbo_allgott_return_to_dock
        name: Return
        icon: mdi:home-battery
      - type: button
        entity: button.yarbo_allgott_pause
        name: Pause
        icon: mdi:pause
      - type: button
        entity: button.yarbo_allgott_resume
        name: Resume
        icon: mdi:play
```

### GPS Tracking Map Card

```yaml
type: map
entities:
  - device_tracker.yarbo_allgott_location
title: Yarbo Location
aspect_ratio: 16x9
```

---

## Blueprints

Several of the above automations are available as importable blueprints. See the [Automations Blueprints](https://github.com/markus-lassfolk/home-assistant-yarbo/tree/main/blueprints) folder in the repository.

---

## Related Pages

- [Services](services.md) — all available services with parameters
- [Entities](entities.md) — entity reference for trigger/condition entities
- [Configuration](configuration.md) — integration options
