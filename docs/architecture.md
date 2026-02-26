# Integration Architecture

## Overview

The Yarbo Home Assistant integration is a **local-first** HACS custom component. All real-time telemetry and command control operate over a direct LAN connection to the robot's on-board EMQX MQTT broker. No cloud connection is required for core functionality.

## Design Principles

- **Local push**: The robot broadcasts telemetry at ~1-2 Hz. The integration subscribes and reacts; it does not poll.
- **python-yarbo transport layer**: All MQTT encoding, decoding, and topic management is delegated to the `python-yarbo` library. The integration never imports `paho-mqtt` directly.
- **Multi-head awareness**: Head type (snow, mow, leaf, SAM, etc.) is tracked per robot. Entity availability is gated on the currently installed head.
- **Device identity**: Robot serial number (SN) is the primary identifier. The docking/charging station (DC) is a secondary device linked to the same config entry.

## Manifest Configuration

```json
{
  "domain": "yarbo",
  "name": "Yarbo",
  "iot_class": "local_push",
  "requirements": ["python-yarbo>=0.1.0"],
  "config_flow": true,
  "dhcp": [
    {"macaddress": "C8FE0F*"}
  ]
}
```

| Field | Value | Notes |
|-------|-------|-------|
| `domain` | `yarbo` | Integration domain |
| `iot_class` | `local_push` | Robot pushes data; no polling |
| `requirements` | `python-yarbo` | Transport + protocol library |
| `dhcp` | `C8FE0F*` | Yarbo MAC OUI for auto-discovery |

## Component Structure

```
custom_components/yarbo/
├── __init__.py          # Setup, unload, coordinator wiring
├── manifest.json
├── config_flow.py       # DHCP + manual discovery, options flow
├── coordinator.py       # YarboDataCoordinator (push-based)
├── entity.py            # YarboEntity base class
├── sensor.py            # Sensor entities
├── binary_sensor.py     # Binary sensor entities
├── button.py            # Command button entities
├── light.py             # LED channel light entities
├── switch.py            # Buzzer and feature switches
├── number.py            # Chute velocity number entity
├── event.py             # HA event entity
├── device_tracker.py    # GPS tracker (v0.4+)
├── lawn_mower.py        # Lawn mower platform (v0.4+)
├── services.py          # Service registrations
├── strings.json
└── translations/
    └── en.json
```

## Data Flow

```
Robot EMQX (port 1883)
        │
        │  MQTT push ~1-2 Hz (zlib JSON)
        ▼
  python-yarbo library
  (YarboClient / transport)
        │
        │  Decoded Python dataclasses
        ▼
  YarboDataCoordinator
  (coordinator.py)
        │
        ├── Fires HA event bus events (yarbo_*)
        ├── Updates self.data dict
        └── Calls async_set_updated_data()
                │
                ▼
        Entity platform listeners
        (sensor, binary_sensor, button, …)
                │
                ▼
        HA State Machine
```

## YarboDataCoordinator

The coordinator uses `DataUpdateCoordinator` in **push mode**: it does not set a `update_interval`. Instead, the `python-yarbo` callback invokes `async_set_updated_data()` whenever new telemetry arrives.

```python
class YarboDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, client: YarboClient) -> None:
        super().__init__(hass, _LOGGER, name="yarbo")
        self._client = client
        self._command_lock = asyncio.Lock()

    async def async_setup(self) -> None:
        self._client.on_telemetry = self._handle_telemetry

    def _handle_telemetry(self, data: YarboTelemetry) -> None:
        self.hass.loop.call_soon_threadsafe(
            self.async_set_updated_data, data
        )
```

## Device Identity Model

| Identifier | Source | Used For |
|------------|--------|----------|
| Robot SN | `DeviceMSG.sn` | Primary device ID, all entity unique IDs |
| DC SN | `DeviceMSG.dc_sn` | Secondary device (dock) |
| IP address | Config entry | MQTT broker connection |
| MAC address | DHCP discovery | Initial discovery only |

Entities use `unique_id = f"{robot_sn}_{entity_key}"` to survive IP address changes.
