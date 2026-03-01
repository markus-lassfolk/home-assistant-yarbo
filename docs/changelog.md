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

Changes in `develop` branch, not yet released.

- Comprehensive GitHub Pages documentation site

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
