---
layout: default
title: Changelog
nav_order: 15
description: "Version history for the Yarbo Home Assistant integration"
---

# Changelog
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

All notable changes to this project are documented here. The project follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [2026.3.10] — 2026-03-01

First public release of the Yarbo Home Assistant custom integration. Local MQTT control only.

### Added

- **Automatic DHCP discovery** via Yarbo MAC prefix (`C8:FE:0F:*`)
- **Manual configuration** with broker IP, serial number, and optional cloud credentials
- **Primary/Secondary failover** — automatic endpoint switching with configurable retry
- **Full entity support:**
  - Sensors: battery, RTK status, charge status, WiFi signal, odometry, GPS, firmware version, working state, and 20+ more
  - Switches: lights, person detection, obstacle avoidance, child lock, NGZ edge, geo-fence, electric fence, bag record
  - Buttons: buzzer, return to dock, emergency stop, recharge
  - Binary sensors: online status, charging, error state
- **Services:**
  - `yarbo.start_plan`, `yarbo.stop_plan`, `yarbo.pause_plan`, `yarbo.resume_plan`
  - `yarbo.set_velocity`, `yarbo.set_blade_height`, `yarbo.set_blade_speed`
  - `yarbo.set_roller_speed`, `yarbo.push_snow_direction`, `yarbo.set_chute`
  - `yarbo.send_command` (with input validation against injection)
  - `yarbo.delete_plan`, `yarbo.delete_all_plans`, `yarbo.erase_map`, `yarbo.map_recovery` (with confirmation required)
  - `yarbo.get_map`, `yarbo.get_wifi_list`, `yarbo.get_hub_info`
- **Diagnostics** — full device diagnostics download with credential redaction
- **MQTT telemetry recorder** — optional local recording for debugging
- **Sentry error reporting** — opt-in with comprehensive payload scrubbing
- **Yarbo app icon** in the HA device registry

### Security

- Event loop violation in connection setup resolved (no more throwaway event loops)
- Sentry scrubber covers all payload sections (extra, breadcrumbs, request, contexts)
- `send_command` validates command names (alphanumeric/underscore/hyphen only, max 64 chars)
- Destructive operations require explicit confirmation parameter

### Dependencies

- Requires `python-yarbo>=2026.3.10,<2027.0`

---

## [0.1.0] — Initial Release

### Added

- Core MQTT integration with local EMQX broker
- DHCP auto-discovery via `C8:FE:0F:*` MAC prefix
- UI config flow with MQTT validation
- **Sensor entities:** Battery, Activity, Head Type, Plan Remaining Time, Connection, GPS/RTK sensors, odometry, charging power, obstacle distances, rain sensor, error code, and more
- **Binary sensor entities:** Charging, Problem, Planning Active, Planning Paused, Returning to Charge, Rain Detected, and more
- **Button entities:** Return to Dock, Pause, Resume, Stop, Beep, Emergency Stop, Shutdown, Restart, and more
- **Switch entities:** Follow Mode, Heating Film, Camera, Laser, USB, Auto Update, and more
- **Number entities:** Chute Velocity, Blade Height, Blade Speed, Roller Speed, Blower Speed, Volume, Plan Start Percent, Battery limits
- **Select entities:** Work Plan (dynamic from robot), Turn Type, Snow Push Direction
- **Light entities:** All-channels group, individual LED channels (head, body, tail)
- **Lawn Mower entity:** Native HA mower card for Lawn Mower and Lawn Mower Pro heads
- **Device Tracker:** GPS/RTK location on HA map
- **Update entity:** Integration version checking
- Multi-head support — entities automatically available/unavailable based on installed head
- Work plan list dynamically loaded from robot
- `yarbo.send_command` service for advanced users
- `yarbo.start_plan` service with optional start percentage
- Multiple endpoint support (Data Center + Rover) with automatic failover
- Connection sensor showing active MQTT endpoint
- Telemetry throttle option to limit recorder load
- Debug logging option
- Full test suite

---

For the complete list of changes, see the [GitHub releases page](https://github.com/markus-lassfolk/home-assistant-yarbo/releases).

---

## Related Pages

- [Getting Started](getting-started.md) — installation and updates
- [Development](development.md) — contributing guide
