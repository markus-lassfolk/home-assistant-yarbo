# Home Assistant Yarbo Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/markus-lassfolk/home-assistant-yarbo.svg)](https://github.com/markus-lassfolk/home-assistant-yarbo/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/markus-lassfolk/home-assistant-yarbo.svg)](https://github.com/markus-lassfolk/home-assistant-yarbo/issues)

A **local, cloud-free** Home Assistant integration for [Yarbo](https://www.yarbo.com/) robot mowers. Control your mower via MQTT with zero-configuration auto-discovery — no Yarbo cloud account required at runtime.

> **Protocol documentation & reverse engineering notes:** [markus-lassfolk/yarbo-reversing](https://github.com/markus-lassfolk/yarbo-reversing)

---

## Features

- 🔍 **Zero-config auto-discovery** — Yarbo robots are detected automatically via DHCP MAC OUI and MQTT topic scanning. No manual IP or serial number entry.
- 🏠 **100% local control** — All communication stays on your LAN via your local MQTT broker (EMQX or Mosquitto). No cloud dependency at runtime.
- 📡 **Real-time telemetry** — Live status updates: battery level, mowing zone, GPS position, error codes, and more.
- 💡 **Light control** — Toggle the robot's work light on/off from Home Assistant.
- 🔔 **Buzzer control** — Trigger the robot's buzzer (useful for locating it in tall grass).
- 🔄 **Start / stop / dock** — Full mowing session control via HA services and dashboard buttons.
- 🛡️ **No cloud polling** — Everything is event-driven over MQTT; no REST polling, no rate limits.

---

## Requirements

- Home Assistant 2024.1 or later
- A local MQTT broker (e.g. [Mosquitto](https://mosquitto.org/) or EMQX) on your LAN
- Your Yarbo robot mower connected to your local Wi-Fi
- The [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) configured in Home Assistant

> The Yarbo robot ships with an EMQX broker embedded in its dock/base station. Point this integration at that broker (typically on port 1883, anonymous auth) or your own Mosquitto instance if you bridge it.

---

## Installation

### HACS (recommended)

1. Open **HACS** in Home Assistant → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/markus-lassfolk/home-assistant-yarbo` as category **Integration**
3. Search for **Yarbo** and click **Install**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/yarbo/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

### Configuration

After installation, go to **Settings → Devices & Services → Add Integration → Yarbo**.

You will be prompted for:
- **MQTT broker host** — IP/hostname of your local broker (e.g. `192.168.1.24`)
- **MQTT port** — default `1883`
- **Username / Password** — leave blank if your broker allows anonymous connections

The integration will auto-discover all Yarbo robots on the broker within seconds.

---

## How It Works

### 1. DHCP MAC OUI Detection

Yarbo robots advertise themselves on the local network. Their Wi-Fi MAC address uses a known OUI (Organizationally Unique Identifier) registered to the Yarbo manufacturer. When the integration starts, it scans ARP/DHCP leases (or listens passively) to identify candidate IPs matching this OUI.

### 2. MQTT Topic Discovery

Each Yarbo robot publishes telemetry and subscribes to commands under a well-known topic hierarchy:

```
yarbo/{serial_number}/heart_beat        ← live telemetry (zlib-compressed JSON)
yarbo/{serial_number}/command/set       ← outbound commands
yarbo/{serial_number}/command/response  ← command ACKs
```

The integration subscribes to the wildcard `yarbo/+/heart_beat` to catch all robots on the broker. The serial number extracted from the topic becomes the unique device identifier in Home Assistant — no manual entry needed.

### 3. Telemetry Decoding

Telemetry payloads are zlib-compressed JSON. The integration decompresses and parses these in real time, mapping fields to HA sensor entities (battery, status, GPS, zone, error codes, etc.).

### 4. Command Encoding

Commands (lights, buzzer, start/stop) are JSON payloads published to the robot's command topic. The protocol is documented in detail in the [yarbo-reversing](https://github.com/markus-lassfolk/yarbo-reversing) repository.

---

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.yarbo_battery` | Sensor | Battery percentage |
| `sensor.yarbo_status` | Sensor | Mowing / docked / error / charging |
| `sensor.yarbo_zone` | Sensor | Active mowing zone name |
| `device_tracker.yarbo` | Device Tracker | GPS position on HA map |
| `light.yarbo_work_light` | Light | Work light on/off |
| `button.yarbo_buzzer` | Button | Trigger buzzer |
| `button.yarbo_start` | Button | Start mowing |
| `button.yarbo_dock` | Button | Return to dock |

---

## Protocol Documentation

All reverse-engineered protocol details (MQTT topics, payload formats, zlib encoding, command structures) are documented in the companion repository:

👉 **[markus-lassfolk/yarbo-reversing](https://github.com/markus-lassfolk/yarbo-reversing)**

---

## Contributing

Pull requests welcome! Please open an issue first to discuss major changes.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push and open a PR

---

## License

[MIT](LICENSE) © Markus Lassfolk
