---
layout: default
title: Multi-Head Guide
nav_order: 13
description: "Head types, entity availability, and head-specific features"
---

# Multi-Head Guide
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

Yarbo robots accept interchangeable attachment heads. The integration tracks the installed head type from live telemetry and dynamically adjusts entity availability.

1. TOC
{:toc}

---

## Head Types

| Head Type | Code | Description |
|-----------|------|-------------|
| None / Base Only | 0 | No head installed |
| Snow Blower | 1 | Snow clearing with auger and chute |
| Leaf Blower | 2 | Leaf and debris clearing |
| Lawn Mower | 3 | Grass cutting with rotating blade |
| Smart Cover | 4 | Protective cover / transport mode |
| Lawn Mower Pro | 5 | Enhanced lawn mower with additional features |
| Trimmer | 99 | String trimmer for edge cutting |

The current head type is shown in the **Head Type** sensor (`sensor.<name>_head_type`).

---

## Entity Availability by Head

Entities marked with a specific head are only **available** when that head is installed. All other entities are available regardless of head type.

### Always Available (All Heads)

- All core status sensors (Battery, Activity, Connection)
- All GPS/RTK sensors
- All charging sensors
- All system buttons (Return to Dock, Pause, Resume, Stop, Beep, Shutdown, Restart)
- All universal switches (Follow Mode, Heating Film, etc.)
- All light entities
- Device tracker

### Snow Blower Head (code: 1)

**Entities unlocked:**

| Entity | Type | Description |
|--------|------|-------------|
| Chute Velocity | Number | Chute rotation speed (−2000 to 2000) |
| Chute Steering Work | Number | Chute steering angle during work (±90°) |
| Snow Push Direction | Select | Left / Right / Center |
| Chute Angle | Sensor | Current chute angle (degrees) |
| Chute Steering Info | Sensor | Chute steering engine position (diagnostic) |

**Head-specific features:**
- Chute rotates continuously (velocity control) or to a fixed angle
- Snow push direction controls where snow is thrown
- The chute can be steered to a different position during active work

### Leaf Blower Head (code: 2)

**Entities unlocked:**

| Entity | Type | Description |
|--------|------|-------------|
| Blower Speed | Number | Speed level 1–10 |
| Smart Blowing | Switch | Intelligent auto-blowing mode |
| Edge Blowing | Switch | Edge-focused blowing mode |
| Roller Speed | Number | Roller RPM |

**Head-specific features:**
- Adjustable blower speed (1–10)
- Smart blowing mode automatically adjusts intensity
- Edge mode focuses on boundary areas

### Lawn Mower Head (code: 3)

**Entities unlocked:**

| Entity | Type | Description |
|--------|------|-------------|
| Mower | Lawn Mower | Native HA lawn mower card |
| Blade Height | Number | Cutting height 25–75 mm |
| Blade Speed | Number | Blade RPM 1000–3500 |
| Roller Speed | Number | Roller RPM 0–3500 |
| Turn Type | Select | U-turn / Three-point / Zero-radius |
| Mower Head Sensor | Switch | Head collision sensor toggle |

**Head-specific features:**
- Full HA lawn mower card integration
- Adjustable cutting height in 5 mm steps
- Multiple turn types for different yard shapes
- `Turn Type` select persists the chosen turning style

### Smart Cover (code: 4)

No additional head-specific entities. The Smart Cover is used for transportation or storage.

### Lawn Mower Pro (code: 5)

Same entities as Lawn Mower (code: 3) — the Pro model uses the same integration interface with enhanced firmware capabilities.

### Trimmer Head (code: 99)

**Entities unlocked:**

| Entity | Type | Description |
|--------|------|-------------|
| Trimmer | Switch | Engage/disengage trimmer blade |

**Head-specific features:**
- String trimmer for edge cutting
- Single on/off control
- Speed is automatically managed by the robot

---

## Switching Heads

When you physically swap the head attachment:

1. The robot publishes the new `head_type` in the next `DeviceMSG` telemetry (within 1–2 seconds of power-up with the new head)
2. The integration detects the change
3. Head-specific entities for the old head become **unavailable**
4. Head-specific entities for the new head become **available**

No integration reload or HA restart is required — the head switch is handled automatically.

---

## Head Identification

The **Head Serial** sensor (`sensor.<name>_head_serial`) shows the serial number of the currently installed head. Each head has a unique serial number, which allows you to:
- Identify which physical head is installed
- Track head usage in history
- Build automations that change behaviour based on head type

```yaml
# Example: Send notification when head changes
automation:
  alias: "Yarbo: Notify when head type changes"
  trigger:
    - platform: state
      entity_id: sensor.yarbo_allgott_head_type
  action:
    - service: notify.mobile_app
      data:
        message: >
          Yarbo head changed to {{ states('sensor.yarbo_allgott_head_type') }}
```

---

## Lawn Mower Card

When a Lawn Mower or Lawn Mower Pro head is installed, the `Mower` entity (`lawn_mower.<name>_mower`) integrates with HA's native lawn mower card.

Add the card to your dashboard:

```yaml
type: lawn-mower
entity: lawn_mower.yarbo_allgott_mower
```

The card shows:
- Current activity (mowing, paused, docked, error)
- Controls: Start, Pause, Dock

---

## FAQ

**Q: Can I use the robot without any head?**
A: Yes — the robot body (base unit) operates normally. Navigation, GPS, charging, and most automations work regardless of head.

**Q: Do I need to reload the integration after swapping heads?**
A: No. Head changes are detected automatically from the robot's telemetry.

**Q: Why are mower entities still showing for my snow blower?**
A: After swapping heads, it may take up to 2 seconds for the new head type to arrive in telemetry. If entities remain available unexpectedly, try restarting the robot.

---

## Related Pages

- [Entities](entities.md) — full entity reference
- [Automations](automations.md) — head-specific automation examples
- [Protocol Reference](protocol-reference.md) — head type codes in telemetry
