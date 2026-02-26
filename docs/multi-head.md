# Multi-Head Support

Yarbo robots accept interchangeable heads. The integration tracks the installed head type from live telemetry and adjusts entity availability dynamically.

## Head Type Reference

Source: Dart `HeadType` enum from Yarbo APK v3.17.4.

| Value | Constant | Display Name | Platform |
|-------|----------|--------------|----------|
| `0` | `SnowBlower` | Snow Blower | — |
| `1` | `LawnMower` | Lawn Mower | `lawn_mower` (v0.4+) |
| `2` | `LawnMowerPro` | Lawn Mower Pro | `lawn_mower` (v0.4+) |
| `3` | `LeafBlower` | Leaf Blower | — |
| `4` | `SmartCover` | Smart Cover (SAM) | — |
| `5` | `Trimmer` | Trimmer | — |
| `6` | `None` | No Head / Unknown | — |

The `head_type` sensor entity exposes the display name as its state.

## Availability Gating

Entities that only apply to certain heads return `STATE_UNAVAILABLE` when the wrong head is installed. This is implemented in the entity's `available` property:

```python
@property
def available(self) -> bool:
    if not self.coordinator.last_update_success:
        return False
    head = self.coordinator.data.head_type
    return head in self._supported_heads
```

No entity is removed or re-created on head change; availability toggling is sufficient for the HA UI and automations.

## Head-Specific Entities

| Entity | Supported Head Values |
|--------|-----------------------|
| Chute Angle sensor | 0 |
| Chute Velocity number | 0 |
| Roller switch | 0 |
| Blower switch | 0, 3 |
| Blade Speed number | 1, 2 |
| SAM Status sensor | 4 |
| Lawn Mower platform | 1, 2 |

## Head Change Behavior

When `head_type` changes between two telemetry messages, the coordinator:

1. Fires `yarbo_head_changed` event (see `events.md`).
2. Calls `async_set_updated_data()` — all entities re-evaluate `available`.
3. Writes a logbook entry: `"Head changed from {old} to {new}"`.

The sequence is synchronous within a single coordinator update cycle, so entity states and logbook entries are consistent.

## `lawn_mower` Platform (v0.4+)

When `head_type` is `1` (LawnMower) or `2` (LawnMowerPro), the robot is also registered as a `lawn_mower` platform entity. This provides:

- Standard `lawn_mower.start_mowing` / `lawn_mower.pause` / `lawn_mower.dock` actions.
- Integration with HA's built-in lawn mower card.
- Activity states mapped to the `lawn_mower` state model: `mowing`, `paused`, `docked`, `error`.

The `lawn_mower` entity becomes unavailable when a non-mowing head is installed.

## Multi-Head Automation Example

```yaml
# Notify when head is changed to snow blower
trigger:
  - platform: event
    event_type: yarbo_head_changed
condition:
  - condition: template
    value_template: "{{ trigger.event.data.new_head == 0 }}"
action:
  - action: notify.mobile_app
    data:
      title: "Yarbo Ready for Winter"
      message: "Snow blower head detected. Remember to update your plans."
```

## Head Type in Config Entry

Head type is **not** stored in the config entry. It is always derived from live telemetry. If telemetry is unavailable, `head_type` sensor state is `unknown` and all head-specific entities are `unavailable`.
