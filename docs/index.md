---
layout: default
title: Home
nav_order: 1
description: "Yarbo for Home Assistant — unofficial community integration"
permalink: /
---

# Yarbo for Home Assistant
{: .no_toc }

> **Disclaimer:** This is an independent community project and is **NOT** affiliated with, endorsed by, or associated with Yarbo or its manufacturer in any way. "Yarbo" is a trademark of its respective owner. This integration is provided as-is with no warranty. Use at your own risk.
{: .warning }

Connect your Yarbo outdoor robot (snow blower, lawn mower, or leaf blower) to Home Assistant for local monitoring, automation, and control — entirely over your local network using the robot's built-in MQTT broker.

---

## Features
{: .no_toc }

- **Local-first** — connects directly to the robot's on-board EMQX MQTT broker; no cloud required for control
- **Live telemetry** at 1–2 Hz — battery, activity, GPS/RTK position, charging status, and more
- **All head types supported** — Snow Blower, Lawn Mower, Lawn Mower Pro, Leaf Blower, Trimmer, Smart Cover
- **Head-aware entities** — sensors and controls automatically become available or unavailable based on the installed head
- **Full LED control** — 7 individual light channels plus an all-lights group
- **Work plan management** — start saved plans by name via a Select entity or the `start_plan` service
- **GPS device tracker** — RTK-based coordinates shown on the HA map
- **Lawn mower platform** — integrates with HA's native mower card
- **Rich diagnostics** — RTCM age, odometry confidence, satellite count, charging current/voltage, and more
- **DHCP auto-discovery** — robot is found automatically when it joins your network
- **HACS compatible** — easy install and updates

---

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Quick Start

1. [Install via HACS](getting-started.md) (recommended) or manually
2. The integration auto-discovers your robot via DHCP — or enter the broker IP manually
3. A device with all entities appears in Home Assistant within seconds of the first telemetry message

---

## Head Types at a Glance

| Head | Code | Entities unlocked |
|------|------|-------------------|
| Snow Blower | 1 | Chute velocity, chute steering, snow push direction |
| Lawn Mower | 3 | Mower card, blade height, blade speed, roller speed |
| Lawn Mower Pro | 5 | Same as Lawn Mower |
| Leaf Blower | 2 | Blower speed, smart blowing, edge blowing, roller |
| Trimmer | 99 | Trimmer switch |
| Smart Cover | 4 | (no head-specific entities) |

See [Multi-Head Guide](multi-head.md) for full details.

---

## Navigation

| Page | Description |
|------|-------------|
| [Getting Started](getting-started.md) | Installation via HACS or manually |
| [Configuration](configuration.md) | Config flow, options, reconfiguration |
| [Entities](entities.md) | Every entity created by the integration |
| [Services](services.md) | HA services with YAML examples |
| [Automations](automations.md) | Ready-to-use automation examples |
| [Protocol Reference](protocol-reference.md) | Local MQTT protocol documentation |
| [Cloud API](cloud-api.md) | Cloud REST API reference |
| [Communication Architecture](communication-architecture.md) | How the system communicates |
| [Troubleshooting](troubleshooting.md) | Common problems and solutions |
| [Architecture](architecture.md) | Integration internals |
| [Development](development.md) | Contributing guide |
| [Multi-Head Guide](multi-head.md) | Head types and entity availability |
| [FAQ](faq.md) | Frequently asked questions |
| [Changelog](changelog.md) | Version history |

---

## Requirements

- Home Assistant 2024.1 or later
- Python library: `python-yarbo >= 0.1.0, < 1.0` (installed automatically)
- Yarbo robot on the same local network as Home Assistant (connected via Wi-Fi or HaLow)
- Robot firmware 3.9.0 or later (zlib-compressed MQTT)

---

## Project Links

- **GitHub:** [markus-lassfolk/home-assistant-yarbo](https://github.com/markus-lassfolk/home-assistant-yarbo)
- **Issues:** [GitHub Issues](https://github.com/markus-lassfolk/home-assistant-yarbo/issues)
- **HACS:** search for "Yarbo" in the HACS integrations store

---

> This integration communicates with the robot using the local MQTT protocol
> the robot exposes on your home network. It does not modify the robot's
> firmware or software in any way.
