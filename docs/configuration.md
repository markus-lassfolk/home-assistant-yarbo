---
layout: default
title: Configuration
nav_order: 3
description: "Config flow, connection options, and reconfiguration"
---

# Configuration
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

1. TOC
{:toc}

---

## Config Flow Overview

The integration uses Home Assistant's standard UI-based config flow. There is no YAML configuration.

### Setup Steps

```
Start
  │
  ├─ Auto-discovery found robot? ──YES──► Confirm step
  │                                            │
  │                                            ▼
  ├─ Manual IP entry ──────────────────► MQTT test
  │                                            │
  │                                            ▼
  │                                       Name step
  │                                            │
  │                                            ▼
  └──────────────────────────────────────► Done ✓
```

### Step: Confirm (DHCP Discovery)

When the robot is auto-discovered via DHCP, HA shows a confirmation dialog with the robot's IP address and serial number. Click **Add** to proceed.

### Step: Manual Entry

If discovery doesn't find the robot, enter:

| Field | Description | Default |
|-------|-------------|---------|
| **Host** | IP address of the robot's MQTT broker | — |
| **Port** | MQTT broker port | `1883` |

### Step: MQTT Test

The integration connects to the broker, subscribes to the robot's telemetry topics, and waits up to 30 seconds for a telemetry message. This confirms:
- The broker is reachable
- The robot is responding
- The serial number is readable

**Common errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot_connect` | TCP connection failed | Check IP, port, firewall |
| `no_telemetry` | Connected but no data | Robot may be in deep sleep — wake it via the Yarbo app first |
| `decode_error` | Unexpected data | Firmware version mismatch |

### Step: Select Endpoint

If the integration discovers multiple MQTT endpoints (e.g., direct rover IP and a base station relay), a selection screen appears. Choose the endpoint you prefer as primary. The other becomes an automatic fallback.

### Step: Name

Enter a friendly name for the robot (e.g., "Yarbo Allgott"). This is used as the device name in HA. Defaults to `Yarbo <last 4 of SN>`.

---

## Integration Options

After setup, options are available via **Settings → Devices & Services → Yarbo → Configure**.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **Telemetry throttle** | `float` | `1.0 s` | Minimum interval between HA state updates. Increase if telemetry floods your recorder. Range: 1.0–10.0 s |
| **Auto controller** | `bool` | `true` | Automatically send `get_controller` before each command. Required for most commands to work. Disable only if you are managing controller acquisition yourself. |
| **Debug logging** | `bool` | `false` | Enable verbose MQTT logging for troubleshooting. Logs to the HA log at DEBUG level. |
| **MQTT recording** | `bool` | `false` | Save raw MQTT payloads to a local file for diagnostic purposes. |
| **Activity personality** | `bool` | `false` | When enabled, the Activity sensor's `description` attribute contains a more human-friendly description of what the robot is doing. |

Options take effect immediately without restarting Home Assistant.

---

## Reconfiguration

If your robot's IP address changes (e.g., after a DHCP renewal), you can update it:

1. Go to **Settings → Devices & Services → Yarbo**
2. Click **⋮ → Reconfigure**
3. Enter the new IP address
4. The integration reconnects and verifies it is the same robot (by serial number)

The integration also handles IP changes automatically if DHCP discovery is active — the new IP is applied when the robot reconnects to the network.

---

## Config Entry Data

The following data is stored in the config entry (not user-configurable directly):

| Key | Description |
|-----|-------------|
| `broker_host` | Primary MQTT broker IP |
| `broker_port` | MQTT port (default 1883) |
| `robot_serial` | Robot serial number (used as unique ID) |
| `robot_name` | Friendly name |
| `broker_mac` | MAC address (used for IP change detection) |
| `connection_path` | `dc`, `rover`, or blank |
| `rover_ip` | Direct rover IP (if known) |
| `broker_endpoints` | Ordered list of endpoint IPs for failover |

---

## Entity Configuration

Most entities are enabled by default. Diagnostic and config-category entities are disabled by default to keep the dashboard clean. Enable them in:

**Settings → Devices & Services → Yarbo → [Device] → toggle the entity**

See [Entities](entities.md) for a full list of which entities are enabled by default.

---

## Connection Sensor

The **Connection** sensor (diagnostic, entity ID: `sensor.yarbo_XXXX_connection`) shows which MQTT endpoint the integration is currently using:

- `Data Center (<ip>)` — connected via the base-station relay
- `Rover (<ip>)` — connected directly to the rover unit
- `MQTT (<ip>)` — connected via a generic MQTT path

---

## Next Steps

- [Entities](entities.md) — detailed description of every entity
- [Services](services.md) — available HA services
- [Troubleshooting](troubleshooting.md) — if something isn't working
