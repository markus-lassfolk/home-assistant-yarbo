---
layout: default
title: Getting Started
nav_order: 2
description: "Install the Yarbo integration via HACS or manually"
---

# Getting Started
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

1. TOC
{:toc}

---

## Prerequisites

- Home Assistant **2024.1** or later
- Your Yarbo robot connected to your local Wi-Fi or HaLow network
- The robot must be reachable from your Home Assistant host (same subnet, or routed)
- Robot firmware **3.9.0** or later

---

## Install via HACS (Recommended)

[HACS](https://hacs.xyz) (Home Assistant Community Store) is the easiest way to install and keep the integration up to date.

### Step 1 — Add the Repository

1. Open Home Assistant → **HACS** → **Integrations**
2. Click the **⋮ menu** (top right) → **Custom repositories**
3. Enter the repository URL:
   ```
   https://github.com/markus-lassfolk/home-assistant-yarbo
   ```
4. Set category to **Integration**
5. Click **Add**

### Step 2 — Install

1. Search for **Yarbo** in HACS Integrations
2. Click **Download**
3. Restart Home Assistant

### Step 3 — Add the Integration

After restarting, go to **Settings → Devices & Services → Add Integration** and search for **Yarbo**.

If your robot is on the same network, it will usually be **auto-discovered** — a notification appears in Settings asking you to configure a newly found Yarbo robot.

---

## Manual Installation

If you prefer not to use HACS:

1. Download the latest release from [GitHub Releases](https://github.com/markus-lassfolk/home-assistant-yarbo/releases)
2. Copy the `custom_components/yarbo/` directory to your HA config directory:
   ```
   /config/custom_components/yarbo/
   ```
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services → Add Integration → Yarbo**

### Directory Structure

Your config directory should look like:

```
/config/
  custom_components/
    yarbo/
      __init__.py
      manifest.json
      config_flow.py
      sensor.py
      binary_sensor.py
      ... (other platform files)
```

---

## First-Time Setup

### Auto-Discovery (Recommended)

When the robot is powered on and connected to your network, Home Assistant automatically detects it via DHCP (the robot's network adapter uses a recognisable MAC prefix).

A notification appears in **Settings → Devices & Services** — click **Configure** to add it.

The integration probes the robot's MQTT broker to read the serial number, then creates a device entry with all entities.

### Manual Setup

If auto-discovery doesn't appear:

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Yarbo**
3. Enter your robot's IP address (find it in your router's DHCP table — look for a hostname starting with `YARBO` or a MAC starting with `C8:FE:0F`)
4. Leave the port at **1883** (default)
5. Click **Submit** — the integration connects and validates the robot is reachable

### Naming Your Robot

During setup you can give your robot a friendly name (e.g. "Yarbo Allgott"). This becomes the device name in HA. You can change it later via **Settings → Devices & Services → Yarbo → ⋮ → Rename**.

---

## Multiple Robots

Each robot is a separate integration entry. Repeat the setup steps for each robot. Each gets its own device with independent entities.

---

## Updating

### HACS

HACS shows update notifications automatically. Go to **HACS → Integrations → Yarbo → Update**.

Always **restart Home Assistant** after updating.

### Manual

Replace the `custom_components/yarbo/` directory with the new version and restart.

---

## Next Steps

- [Configuration](configuration.md) — review the available options
- [Entities](entities.md) — understand what each entity does
- [Automations](automations.md) — set up your first automation

---

## Uninstalling

1. Go to **Settings → Devices & Services → Yarbo**
2. Click **⋮ → Delete**
3. If installed via HACS, remove it from HACS as well
4. Restart Home Assistant
