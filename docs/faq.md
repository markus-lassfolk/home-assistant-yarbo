---
layout: default
title: FAQ
nav_order: 14
description: "Frequently asked questions about the Yarbo Home Assistant integration"
---

# FAQ
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

1. TOC
{:toc}

---

## General

**Q: Is this integration official?**

No. This is an independent community project and is **not affiliated with, endorsed by, or associated with Yarbo or its manufacturer** in any way. "Yarbo" is a trademark of its respective owner.

---

**Q: Is this safe to use?**

The integration communicates with your robot via its local MQTT broker using the same protocol the robot exposes on your home network. It does not modify the robot's firmware, software, or configuration files. It observes the protocol the robot uses and sends commands in the format the robot accepts.

As with any third-party software, use at your own risk. Always ensure your robot is in a safe location when testing new automations.

---

**Q: Does this integration require internet access?**

No, for core functionality. All real-time control and telemetry use local MQTT on your home network. Internet is only needed for:
- Installing the integration via HACS (one-time)
- Checking for integration updates (optional)
- The cloud API endpoints used for initial robot binding (if applicable)

---

**Q: Will using this integration void my warranty?**

We don't know. The integration only communicates with the robot via its local MQTT broker — it does not modify the robot's software, firmware, or hardware. However, we cannot make any guarantee about warranty implications. Use at your own risk.

---

**Q: Does the Yarbo app still work if I use this integration?**

Yes. Both the Yarbo app and the HA integration can connect to the robot's MQTT broker simultaneously. However, the "controller role" (which allows sending commands) can only be held by one client at a time. If both the app and HA try to control the robot simultaneously, one may temporarily lose the controller role.

Close the Yarbo app on all devices when you want HA to have reliable control.

---

## Setup

**Q: My robot isn't discovered automatically. What should I do?**

1. Check that the robot is powered on and connected to your Wi-Fi network
2. Find the robot's IP address in your router's DHCP table (look for a device named `YARBO*` or with MAC prefix `C8:FE:0F:*`)
3. Go to **Settings → Devices & Services → Add Integration → Yarbo** and enter the IP manually

---

**Q: Can I use this with multiple Yarbo robots?**

Yes. Each robot is a separate integration entry with its own device and entities. Add each robot separately during setup.

---

**Q: What firmware version is required?**

The integration works with firmware **3.9.0 or later** (which uses zlib-compressed MQTT payloads). Earlier firmware used plain JSON and is not currently supported.

Check your firmware version in the Yarbo app: Settings → Robot → Firmware.

---

**Q: Do I need to keep the Yarbo app installed?**

No. Once your robot is set up and connected to your Wi-Fi, the integration communicates directly with the robot over local MQTT. You don't need the Yarbo app running for the integration to work. However, you'll need the app for:
- Initial WiFi setup of the robot
- Creating work plans and maps (map editing is not available in HA)
- Firmware updates

---

## Entities

**Q: Many entities are disabled. How do I enable them?**

Go to **Settings → Devices & Services → Yarbo → [your robot]** and scroll down to the entity list. Click on a disabled entity and toggle it on.

Most diagnostic and config-category entities are disabled by default to keep the dashboard clean.

---

**Q: Why does the Work Plan select sometimes show no options?**

The work plan list is loaded from the robot when the integration starts. If you just created a new plan in the app, you may need to reload the integration: **Settings → Devices & Services → Yarbo → ⋮ → Reload**.

---

**Q: The Activity sensor shows "idle" but the robot seems to be working. Why?**

The `Activity` sensor is derived from `StateMSG.working_state` and related fields. If the robot is in a transitional state (e.g., just starting up, navigating to plan start), it may briefly show "idle" before reaching "working". Check the `Planning Active` binary sensor for a more granular view.

---

**Q: Can I control the exact GPS coordinates the robot navigates to?**

Not directly — work plans and waypoints must be created in the Yarbo app. The integration allows you to *start* saved plans by name/ID, but does not expose a waypoint editor.

---

**Q: Why don't switches read back their actual state?**

Most switches use **assumed state** — the integration tracks what was last sent, not what the robot reports. The robot's `DeviceMSG` telemetry doesn't include states for most toggle settings. This means if you change a setting via the Yarbo app, the HA switch may not reflect the change until you toggle it in HA.

---

## Control

**Q: Why do some commands seem to be ignored?**

Possible causes:
1. **Controller role:** Another client (e.g., the Yarbo app) holds the controller role. Close the app and try again.
2. **Robot state:** Some commands only work in certain states (e.g., head-specific commands require the matching head).
3. **Connection loss:** The integration may have briefly lost connection. Check the `Connection` sensor.

---

**Q: Can I run the robot without a work plan (manual drive)?**

The integration includes the `yarbo.manual_drive` service for velocity commands. Use it carefully — the robot will continue driving until you send a stop command.

---

**Q: Can I create or edit work plans from Home Assistant?**

No. Work plan creation and map editing are only available in the Yarbo app. The integration can start existing plans by name but cannot create or modify them.

---

## Automation

**Q: Can I schedule the robot from Home Assistant instead of using the Yarbo app scheduler?**

Yes. Use time-based or calendar-based automations to call `yarbo.start_plan` or press the Work Plan select entity. See [Automations](automations.md) for examples.

Note: Schedules created in the Yarbo app are stored on the robot and run independently of Home Assistant. If you want HA to be in charge of scheduling, disable the in-app schedules.

---

**Q: How do I pause the robot when I enter the garden?**

Use a presence sensor or button:

```yaml
automation:
  alias: "Pause Yarbo when person detected in garden"
  trigger:
    - platform: state
      entity_id: binary_sensor.garden_motion
      to: "on"
  condition:
    - condition: state
      entity_id: sensor.yarbo_allgott_activity
      state: "working"
  action:
    - service: yarbo.pause
      data:
        device_id: "YOUR_DEVICE_ID"
```

---

## Troubleshooting

**Q: The integration stops responding after a while.**

This typically means the MQTT connection was lost and hasn't reconnected. Check:
1. Is the robot still on?
2. Has the robot's IP changed?
3. Is your home network healthy?

Reload the integration via **Settings → Devices & Services → Yarbo → ⋮ → Reload**.

---

**Q: How do I report a bug?**

Open an issue at [GitHub Issues](https://github.com/markus-lassfolk/home-assistant-yarbo/issues) with:
- Your HA version
- Integration version
- Robot firmware version
- Debug logs (enable via Configuration options)
- Steps to reproduce

---

## Related Pages

- [Getting Started](getting-started.md) — installation guide
- [Troubleshooting](troubleshooting.md) — detailed troubleshooting
- [Configuration](configuration.md) — options and settings
- [Automations](automations.md) — automation examples
