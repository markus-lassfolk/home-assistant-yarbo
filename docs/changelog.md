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

## [2026.4.270] — 2026-04-27

> **Since Git tag [`v2026.3.63`](https://github.com/markus-lassfolk/home-assistant-yarbo/releases/tag/v2026.3.63`):** see [Release notes — v2026.4.270](releases/v2026.4.270.md). On `main`: Sentry **release** uses manifest version (`2539a70`), `event.py` **battery_capacity** `None` guard (`bdc735b`), then [#156](https://github.com/markus-lassfolk/home-assistant-yarbo/pull/156) (Community Yarbo rename and related fixes).

### Breaking

- **Community Yarbo** — domain `community_yarbo` (folder `custom_components/community_yarbo/`). Coexists with the official `yarbo` integration. Remove the old community integration, install the new folder, restart, re-add **Community Yarbo**; update services, events, blueprints, and entity IDs. MQTT debug folder: `community_yarbo_recordings/`.

### Added

- **Translations:** `fi`, `sv`, `de`, `nl`, `nb`, `es`, `fr`, `it`, `pl` (#131).
- **`CONFIG_SCHEMA`**; **`async_ensure_controller`** for clearer timeout errors (#147); broker host resolution and migration (#155).

### Fixed

- **Sentry / GlitchTip** — release string from integration version, not commit hash (`2539a70`).
- **Low battery** — `None` `battery_capacity` guard in `event.py` (`bdc735b`; #146).
- **Telemetry / shutdown** (#137, #154); **options & unload** (#148); **library guard** vs manifest (#153); **CI** `python-yarbo@main`; Ruff + DHCP test socket fixes; **Copilot** docs + **`discover_yarbo`** for discovery/DHCP (no direct `paho.mqtt` in those paths).

### Changed

- **GitHub Actions** (#149, #150); dev **setuptools** `>=82.0.1` (#151).
- **`python-yarbo>=2026.3.60`** (see **2026.3.60–2026.3.63** in the root changelog for polling, Last Seen, and MQTT tooling already on the 2026.3.x line).

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
  - `community_yarbo.start_plan`, `community_yarbo.stop_plan`, `community_yarbo.pause_plan`, `community_yarbo.resume_plan`
  - `community_yarbo.set_velocity`, `community_yarbo.set_blade_height`, `community_yarbo.set_blade_speed`
  - `community_yarbo.set_roller_speed`, `community_yarbo.push_snow_direction`, `community_yarbo.set_chute`
  - `community_yarbo.send_command` (with input validation against injection)
  - `community_yarbo.delete_plan`, `community_yarbo.delete_all_plans`, `community_yarbo.erase_map`, `community_yarbo.map_recovery` (with confirmation required)
  - `community_yarbo.get_map`, `community_yarbo.get_wifi_list`, `community_yarbo.get_hub_info`
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
- `community_yarbo.send_command` service for advanced users
- `community_yarbo.start_plan` service with optional start percentage
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
