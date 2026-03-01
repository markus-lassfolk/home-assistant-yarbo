---
layout: default
title: Communication Architecture
nav_order: 9
description: "How the Yarbo robot communicates locally and via the cloud"
---

# Communication Architecture
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

This page describes how the Yarbo robot communicates across local and cloud paths, and how this integration fits into that architecture.

1. TOC
{:toc}

---

## Overview

The Yarbo robot supports multiple communication paths. The integration uses the **local MQTT path** as its primary channel, which provides low-latency, reliable communication entirely on your home network.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Yarbo Architecture                           │
├───────────────────────┬─────────────────────────────────────────────┤
│  Cloud REST API        │  Account / robot management                 │
│  AWS API Gateway       │  Login, robot binding, map backgrounds,     │
│  (us-east-1)           │  notifications, version info                │
├───────────────────────┼─────────────────────────────────────────────┤
│  Cloud MQTT            │  Remote robot control and telemetry         │
│  Tencent TDMQ          │  Used when robot and app are not on the     │
│  (US West)             │  same local network                         │
├───────────────────────┼─────────────────────────────────────────────┤
│  ★ Local MQTT ★        │  Direct local control (used by integration) │
│  EMQX on robot         │  Low latency, no internet required          │
│  Port 1883             │  Telemetry + command channel                │
├───────────────────────┼─────────────────────────────────────────────┤
│  Live Video            │  Robot camera stream via Agora RTC          │
│  Agora RTC SDK         │  Local P2P or cloud-relayed                 │
└───────────────────────┴─────────────────────────────────────────────┘
```

---

## Local MQTT Path (Used by This Integration)

The robot runs an **EMQX MQTT broker** on port 1883. Any device on the same local network can connect without authentication.

### How It Works

```
Home Assistant ──────────────────────────── Yarbo Robot
    │                                           │
    │   TCP :1883 (local network)               │
    │◄─────────── DeviceMSG (telemetry) ────────│
    │◄─────────── heart_beat ───────────────────│
    │◄─────────── data_feedback ────────────────│
    │◄─────────── plan_feedback ────────────────│
    │                                           │
    │─────────── get_controller ───────────────►│
    │─────────── start_plan / pause / etc. ────►│
    │─────────── light_ctrl ───────────────────►│
```

1. The integration connects to the robot's MQTT broker over TCP
2. It subscribes to `snowbot/<SN>/device/#` to receive all telemetry
3. Before sending commands, it publishes `get_controller` to acquire the controller role
4. Commands are published to `snowbot/<SN>/app/<cmd_name>`
5. Responses arrive on `snowbot/<SN>/device/data_feedback`

All payloads are **zlib-compressed JSON** (firmware 3.9.0+).

### Broker Discovery

The integration discovers the robot in two ways:

1. **DHCP auto-discovery**: When the robot connects to your network, HA detects it via the DHCP lease. The robot's network adapter uses a recognisable MAC prefix (`C8:FE:0F:*`).

2. **Manual entry**: You provide the robot's IP address directly in the setup flow.

### Controller Role

Only one MQTT client can be the "controller" at a time. When the Yarbo mobile app is also connected and active, it may hold the controller role. The integration re-acquires the role before each command.

---

## Robot Network Interfaces

The robot has multiple network interfaces with automatic failover:

| Interface | Description | Route Priority |
|-----------|-------------|---------------|
| `hg0` | Wi-Fi HaLow (Sub-GHz, long range) | 10 (most preferred) |
| `wlan0` | Standard 2.4/5 GHz Wi-Fi | 600 |
| `wwan0` | LTE / cellular (if equipped) | 50000 (last resort) |

The robot prefers HaLow for its superior range and interference characteristics. When the robot is within range of the base station, HaLow is used for MQTT traffic.

The integration's `Connection` sensor shows which IP and path is currently active:
- `Data Center (<ip>)` — connected via the base station relay
- `Rover (<ip>)` — connected directly to the rover unit
- `MQTT (<ip>)` — generic MQTT path

---

## Multiple Endpoints / Failover

In setups with a base station, there may be two MQTT endpoints:

1. **Data Center IP** (base station relay): Provides access even when the rover is out of direct Wi-Fi range
2. **Rover IP** (direct): Lower latency for direct rover communication

The integration stores both endpoints and tries them in order if the primary fails.

---

## Cloud MQTT Path

When the robot is not on the same local network as the Yarbo app (e.g., you are away from home), the app uses the **cloud MQTT broker** (Tencent TDMQ, US West region) for control and telemetry. This path requires active internet connectivity on both the robot and the controlling device.

> The Home Assistant integration does **not** use the cloud MQTT path. It requires local network access to the robot.
{: .note }

---

## Cloud REST API Path

The cloud REST API (AWS API Gateway, us-east-1) is used for:
- Account authentication
- Robot binding/unbinding
- Notification management
- Map background images (satellite overlays)
- Firmware version information
- Robot sharing (whitelist)

The integration optionally uses the cloud API during initial setup (to read robot metadata) and for the update entity (version checks). All real-time telemetry and control uses only the local MQTT path.

---

## Video Streaming Path

The robot's camera streams via **Agora RTC** (real-time communications SDK). When the app and robot are on the same local network, Agora uses direct peer-to-peer UDP. When remote, it routes through Agora's cloud relay servers.

> Video streaming is **not currently implemented** in the Home Assistant integration.
{: .note }

---

## Architecture Diagram

```
Your Home Network
┌─────────────────────────────────────────────────────┐
│                                                     │
│   Home Assistant                                    │
│   ┌─────────────────────┐                          │
│   │  Yarbo Integration  │                          │
│   │  (python-yarbo)     │◄── MQTT subscribe        │
│   │                     │                          │
│   │  Entities, services │──► MQTT publish          │
│   └──────────┬──────────┘                          │
│              │ TCP :1883                            │
│              │                                     │
│   ┌──────────▼──────────────────────────────────┐  │
│   │  Yarbo Robot                                │  │
│   │  ┌─────────────────┐                        │  │
│   │  │  EMQX Broker    │ snowbot/<SN>/device/#  │  │
│   │  │  (MQTT server)  │ snowbot/<SN>/app/#     │  │
│   │  └────────┬────────┘                        │  │
│   │           │ internal                         │  │
│   │  ┌────────▼────────┐                        │  │
│   │  │  Robot OS (ROS) │                        │  │
│   │  │  + Greengrass   │                        │  │
│   │  └─────────────────┘                        │  │
│   └─────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
         │                       │
         │ (optional)            │ (optional)
         ▼                       ▼
  Cloud REST API          Cloud MQTT
  (account, map,          (Tencent TDMQ)
   version info)          (remote control
                           via Yarbo app)
```

---

## System Software Stack

The robot runs on a Firefly ARM single-board computer with the following key software components:

| Component | Description |
|-----------|-------------|
| Ubuntu 22.04 LTS | Operating system |
| ROS (Robot Operating System) | Robotics middleware (motion planning, sensors) |
| EMQX | MQTT broker for local communication |
| AWS Greengrass v2 | IoT runtime, handles cloud MQTT connectivity and OTA updates |

---

## Local Network Requirements

For the integration to work:

1. Home Assistant and the robot must be on the **same local network** (or have routed connectivity between them)
2. TCP port **1883** must be accessible from HA to the robot (not blocked by a firewall)
3. The robot must be **powered on** — it enters a sleep state after ~5 minutes of inactivity
4. If the robot is sleeping, wake it via the Yarbo app before configuring the integration

### Wake-up Behaviour

The robot sends `heart_beat` at 1 Hz even when sleeping (`working_state: 0`). The integration detects this and uses `set_working_state` to wake the robot when needed.

When active (`working_state: 1`), the robot publishes full `DeviceMSG` telemetry at 1–2 Hz.

---

## Related Pages

- [Protocol Reference](protocol-reference.md) — MQTT protocol details
- [Cloud API](cloud-api.md) — cloud REST API reference
- [Configuration](configuration.md) — integration setup and options
- [Troubleshooting](troubleshooting.md) — connectivity issues
