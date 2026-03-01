---
layout: default
title: Architecture
nav_order: 11
description: "Home Assistant integration architecture and internals"
---

# Architecture
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

1. TOC
{:toc}

---

## Overview

The Yarbo integration is a **local-first** HACS custom component. All real-time telemetry and command control operates over a direct LAN connection to the robot's on-board EMQX MQTT broker. No cloud connection is required for core functionality.

```
┌───────────────────────────────────────────────────────┐
│                 Home Assistant Core                    │
│  ┌────────────────────────────────────────────────┐   │
│  │              Yarbo Integration                 │   │
│  │  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │ Config Flow  │  │   Coordinator        │   │   │
│  │  │ (UI setup)   │  │  (state management)  │   │   │
│  │  └──────────────┘  └──────────┬───────────┘   │   │
│  │                               │               │   │
│  │  ┌────────────────────────────▼────────────┐  │   │
│  │  │             Entity Platforms            │  │   │
│  │  │  sensor  binary_sensor  button  switch  │  │   │
│  │  │  select  number  light  lawn_mower      │  │   │
│  │  │  device_tracker  update                 │  │   │
│  │  └────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────┘   │   │
└───────────────────────────────────────────────────────┘
                     │ python-yarbo library
                     │ MQTT :1883
                     ▼
            ┌─────────────────┐
            │   Yarbo Robot   │
            │  EMQX Broker    │
            └─────────────────┘
```

---

## Core Components

### Config Flow (`config_flow.py`)

Handles the UI-based setup wizard and reconfiguration. Steps:

1. **DHCP discovery** — detects robot via MAC prefix `C8:FE:0F:*`
2. **User step** — collects host/port if not discovered
3. **MQTT validation** — connects and waits for first telemetry
4. **Name step** — collects a friendly name for the device
5. **Endpoint selection** — chooses between DC and rover endpoints if both found

Stores the config entry with `broker_host`, `broker_port`, `robot_serial`, and `robot_name`.

### Data Coordinator (`coordinator.py`)

The `YarboDataCoordinator` is a custom coordinator (not using `DataUpdateCoordinator` — data is push-based, not polled).

Key responsibilities:
- Maintains the MQTT client connection via `python-yarbo`
- Receives push telemetry from the robot at 1–2 Hz
- Notifies registered entities when new data arrives
- Handles reconnection on connection loss
- Implements telemetry throttle (minimum interval between state updates)
- Tracks head type and controls entity availability

### Entity Manager

Entities subscribe to coordinator updates. On each update:
1. Coordinator receives `DeviceMSG`
2. Coordinator checks the throttle interval
3. Coordinator calls `async_write_ha_state()` on relevant entities
4. Entities read their value from the coordinator's cached data

### `python-yarbo` Library

The `python-yarbo` library (`python-yarbo >= 0.1.0`) handles:
- MQTT connection management
- zlib compression/decompression of payloads
- Topic construction for the `snowbot/<SN>/` namespace
- `get_controller` acquisition before commands
- Retry logic and connection monitoring

---

## Entity Platforms

| Platform | File | Entity count | Notes |
|----------|------|-------------|-------|
| `sensor` | `sensor.py` | ~40 | Numeric and enum state sensors |
| `binary_sensor` | `binary_sensor.py` | 10 | Boolean state sensors |
| `button` | `button.py` | 15 | One-shot action triggers |
| `switch` | `switch.py` | 20 | Toggle controls (assumed state) |
| `number` | `number.py` | 10 | Numeric configuration entities |
| `select` | `select.py` | 3 | Enumerated selection entities |
| `light` | `light.py` | 9 | LED brightness controls |
| `lawn_mower` | `lawn_mower.py` | 1 | Native HA mower platform entity |
| `device_tracker` | `device_tracker.py` | 1 | GPS location entity |
| `update` | `update.py` | 1 | Integration version checker |

---

## Data Flow

### Incoming (Robot → HA)

```
Robot EMQX broker
  │ MQTT publish (zlib-compressed JSON)
  ▼
python-yarbo MQTT client
  │ Decompress + parse
  ▼
YarboDataCoordinator
  │ Cache update
  │ Throttle check
  ▼
Entity update callbacks
  │ async_write_ha_state()
  ▼
Home Assistant state machine
  │
  ▼
Automations, dashboard, history
```

### Outgoing (HA → Robot)

```
HA service call / entity action
  │
  ▼
Entity handler (e.g. async_press() on Button)
  │
  ▼
YarboDataCoordinator.send_command()
  │
  ▼
python-yarbo
  │ get_controller (if needed)
  │ zlib-compress payload
  │ MQTT publish to snowbot/<SN>/app/<cmd>
  ▼
Robot EMQX broker
  │
  ▼
data_feedback (optional response)
```

---

## Head-Aware Entities

When the `HeadMsg.head_type` field changes in telemetry, the coordinator:
1. Updates the cached head type
2. Calls `async_write_ha_state()` on all head-specific entities
3. Each entity checks if its required head is installed via the `available` property

```python
@property
def available(self) -> bool:
    required = self._required_head_type  # e.g., HEAD_SNOW_BLOWER
    current = self.coordinator.data.get("head_type")
    return super().available and (
        required is None or current == required
    )
```

---

## Connection Management

The integration monitors the MQTT connection continuously:

- **Connection sensor**: Updated whenever the active endpoint changes
- **Automatic reconnect**: The `python-yarbo` library handles reconnection with exponential backoff
- **IP change handling**: When DHCP assigns a new IP, the integration detects the new lease and updates the broker address
- **Multi-endpoint failover**: If the primary endpoint fails, the integration tries the secondary (rover vs. DC)

---

## Work Plan Select

The `Work Plan` select entity is dynamically populated:

1. On connect, the coordinator sends `read_all_plan`
2. The response returns an array of `{id, name}` objects
3. The select entity updates its `options` list with plan names
4. When the user selects a plan name, it maps back to the plan ID and calls `start_plan`

---

## Services

Services are registered in `__init__.py` and call coordinator methods:

```python
async def handle_send_command(call: ServiceCall) -> None:
    device_id = call.data["device_id"]
    command = call.data["command"]
    payload = call.data.get("payload", {})
    coordinator = get_coordinator_for_device(device_id)
    await coordinator.send_command(command, payload)
```

---

## File Structure

```
custom_components/yarbo/
├── __init__.py              # Integration setup, service registration
├── manifest.json            # Integration metadata, requirements
├── config_flow.py           # UI setup wizard
├── coordinator.py           # Data coordinator and MQTT management
├── sensor.py                # Sensor entities
├── binary_sensor.py         # Binary sensor entities
├── button.py                # Button entities
├── switch.py                # Switch entities
├── number.py                # Number entities
├── select.py                # Select entities
├── light.py                 # Light entities
├── lawn_mower.py            # Lawn mower platform entity
├── device_tracker.py        # GPS device tracker entity
├── update.py                # Update entity (version checker)
├── services.yaml            # Service schema definitions
├── strings.json             # UI strings (English)
└── translations/
    └── en.json              # English translations
```

---

## IoT Class

The integration declares `iot_class: local_push` in `manifest.json`. This means:
- Communication is local (LAN)
- Data is pushed from the device (not polled)
- No cloud subscription required for real-time state

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `python-yarbo` | `>=0.1.0,<1.0` | MQTT client, protocol handling |

Installed automatically via `requirements` in `manifest.json`.

---

## Related Pages

- [Development](development.md) — contributing guide
- [Communication Architecture](communication-architecture.md) — system communication
- [Protocol Reference](protocol-reference.md) — MQTT protocol details
- [Entities](entities.md) — entity reference
