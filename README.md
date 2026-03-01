# home-assistant-yarbo

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/markus-lassfolk/home-assistant-yarbo.svg)](https://github.com/markus-lassfolk/home-assistant-yarbo/releases)
[![CI](https://github.com/markus-lassfolk/home-assistant-yarbo/actions/workflows/ci.yml/badge.svg)](https://github.com/markus-lassfolk/home-assistant-yarbo/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/markus-lassfolk/home-assistant-yarbo.svg)](https://github.com/markus-lassfolk/home-assistant-yarbo/issues)

Local-first Home Assistant integration for [Yarbo](https://www.yarbo.com/) — the multi-head outdoor robot platform (snow blower, lawn mower, leaf blower, SAM patrol). Connects via the robot's on-board MQTT broker. **No cloud account required.**

> **Status:** Pre-release scaffold. See the [roadmap](docs/roadmap.md) for implementation milestones.

> **⚠️ Disclaimer:** This is a community-driven integration for Home Assistant and is not affiliated with, endorsed by, or supported by Yarbo Inc. or any of its subsidiaries.

---

## Features

- **Auto-discovery** — Detects the Yarbo base station via DHCP MAC OUI `C8:FE:0F:*`; no IP entry required
- **Push telemetry** — `DeviceMSG` streamed at ~1–2 Hz; entities update in real time
- **Multi-head aware** — Head-specific entities show as unavailable when the wrong module is attached
- **Full controls** — Beep, pause, resume, stop, return to dock, start plan, light control
- **7-channel LED** — Individual control of head light, left/right white, body/tail red LEDs
- **GPS device tracker** — Parses GNGGA NMEA from RTK; robot appears on your HA map
- **Automation blueprints** — Rain pause, snow deployment, low battery alert, job complete notification
- **Diagnostics** — One-click download; PII redacted (GPS, serial numbers)

<img width="1312" height="1745" alt="image" src="https://github.com/user-attachments/assets/d9b4182f-cce3-4e96-8be7-6b45e51fbb0c" />

---

## Installation

### HACS (recommended)

1. **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/markus-lassfolk/home-assistant-yarbo` → category **Integration**
3. Search **Yarbo** → **Download**
4. Restart Home Assistant
5. **Settings → Devices & Services → Add Integration → Yarbo**

### Manual

Copy `custom_components/yarbo/` to your HA `config/custom_components/yarbo/` and restart.

---

## Troubleshooting

### "Unable to install package python-yarbo" / "not found in the package registry"

This integration depends on [python-yarbo](https://github.com/markus-lassfolk/python-yarbo). Home Assistant installs dependencies from PyPI only. If `python-yarbo` is not yet published on PyPI, install it manually **before** adding the integration:

1. **SSH or Terminal & SSH add-on:** On the host where Home Assistant runs, use the same Python environment HA uses (e.g. the venv inside the HA install, or the container’s pip). Install the dependency from the GitHub repo (until it is published on PyPI):
   ```bash
   source /path/to/homeassistant/bin/activate   # if using a venv
   pip install "git+https://github.com/markus-lassfolk/python-yarbo.git@main#egg=python-yarbo"
   ```
   Use `@develop` instead of `@main` if you need the development branch.

2. Restart Home Assistant, then add the Yarbo integration again.

**Long-term fix:** Publishing `python-yarbo` to [PyPI](https://pypi.org/) (e.g. as `python-yarbo`) will allow HA to install it automatically; no manual step needed.

---

## Quick Start

The integration supports two setup paths:

**Auto-discovery (recommended):** If your Yarbo base station is on the same LAN as Home Assistant, it will be discovered automatically when its MAC (`C8:FE:0F:*`) appears on DHCP. Accept the notification in HA.

**Manual:** Go to **Settings → Devices & Services → Add Integration → Yarbo** and enter the base station IP.

The config flow connects to MQTT port 1883, waits for telemetry, extracts the robot serial number, and creates the device.

---

## Entity Reference

### Core (always enabled)

| Entity | Platform | Description |
|---|---|---|
| `sensor.{name}_battery` | sensor | Battery % |
| `sensor.{name}_activity` | sensor | Human-readable status (Charging / Working / Paused…) |
| `sensor.{name}_head_type` | sensor | Attached head (Snow Blower / Lawn Mower…) |
| `binary_sensor.{name}_charging` | binary_sensor | Charging state |
| `binary_sensor.{name}_problem` | binary_sensor | Error present |
| `button.{name}_beep` | button | Trigger buzzer |
| `button.{name}_return_to_dock` | button | Send to dock |
| `button.{name}_pause` | button | Pause current plan |
| `button.{name}_resume` | button | Resume plan |
| `button.{name}_stop` | button | Stop |
| `light.{name}_lights` | light | All-lights group (7 channels) |
| `event.{name}_events` | event | Job lifecycle events |

### Extended (disabled by default) — see [docs/entities.md](docs/entities.md)

RTK status, heading, chute angle, rain sensor, satellite count, charging power, 7 individual LED channels, chute velocity, buzzer switch, planning binary sensor, emergency stop.

### Head-specific (availability gated)

| Entity | Available when |
|---|---|
| `lawn_mower.{name}` | Lawn Mower / Pro head |
| `number.{name}_chute_velocity` | Snow Blower head |
| `switch.{name}_blower` | Snow Blower head |
| `number.{name}_roller_speed` | Leaf Blower head |
| `device_tracker.{name}` | Any head (RTK fix) |

---

## Services

| Service | Description | Milestone |
|---|---|---|
| `yarbo.send_command` | Send any raw MQTT command | v0.1.0 |
| `yarbo.pause` | Pause current job | v0.2.0 |
| `yarbo.resume` | Resume paused job | v0.2.0 |
| `yarbo.return_to_dock` | Return to dock | v0.2.0 |
| `yarbo.set_lights` | Set all 7 LED channels | v0.2.0 |
| `yarbo.set_chute_velocity` | Snow chute control | v0.2.0 |
| `yarbo.start_plan` | Start a saved work plan | v0.3.0 |

---

## Blueprints

Four automation blueprints ship with the integration (available in `blueprints/automation/yarbo/`):

- **Rain Pause** — Pause and dock on rain, resume after dry delay
- **Snow Deployment** — Start snow clearing plan when snowfall threshold is exceeded
- **Low Battery Alert** — Notify when battery drops below threshold
- **Job Complete** — Notify when a work plan finishes

---

## Documentation

| Doc | Contents |
|---|---|
| [Architecture](docs/architecture.md) | Design principles, data flow, coordinator |
| [Config Flow](docs/config-flow.md) | Setup steps, DHCP discovery, options |
| [Entities](docs/entities.md) | Full entity reference with MQTT sources |
| [Services](docs/services.md) | Service definitions and examples |
| [Events](docs/events.md) | HA event bus events and triggers |
| [Multi-Head](docs/multi-head.md) | Head types, availability gating |
| [Blueprints](docs/blueprints.md) | Automation blueprint reference |
| [MQTT Protocol](docs/mqtt-protocol.md) | Topic reference, encoding |
| [Security](docs/security.md) | Hardening, credential storage |
| [Development](docs/development.md) | Contributing, testing, linting |
| [Roadmap](docs/roadmap.md) | Milestone plan |

---

## Security Note

The Yarbo base station MQTT broker (port 1883) is **unauthenticated**. Anyone on your LAN can read telemetry and send commands. Place the base station on an isolated IoT VLAN and restrict MQTT access to your HA host. See [docs/security.md](docs/security.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome — please open an issue first for major changes.

## License

[MIT](LICENSE) © Markus Lassfolk
