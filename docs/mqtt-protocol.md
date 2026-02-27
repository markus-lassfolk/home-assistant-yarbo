# MQTT Protocol

## Broker

The Yarbo base station runs an on-board **EMQX** broker accessible over the local network.

| Property | Value |
|----------|-------|
| Port | `1883` |
| Authentication | None (unauthenticated) |
| TLS | Not available on port 1883 |
| Protocol version | MQTT 3.1.1 |

The integration connects to this broker using `python-yarbo`. The HA component never imports `paho-mqtt` directly.

## Topic Structure

Topics use the format `snowbot/{SN}/{direction}/{leaf}` where `{SN}` is the robot's serial number.

### Publish Topics (HA → Robot)

The integration publishes to `snowbot/{SN}/app/{cmd}`.

| Command (`{cmd}`) | Description | Head Types |
|-------------------|-------------|------------|
| `get_controller` | Request controller role | All |
| `light_ctrl` | Set LED channel brightness | All |
| `cmd_buzzer` | Enable/disable buzzer | All |
| `cmd_chute` | Set chute angle/velocity | 0 |
| `dstop` | Graceful stop | All |
| `emergency_stop_active` | Immediate hardware stop | All |
| `start_plan` | Start a saved plan | All |
| `planning_paused` | Pause active plan | All |
| `resume` | Resume paused plan | All |
| `cmd_recharge` | Return to dock | All |
| `set_blade_speed` | Set mowing blade speed | 1, 2 |
| `cmd_roller` | Control snow roller | 0 |
| `en_blower` | Enable/disable blower motor | 0, 3 |

### Subscribe Topics (Robot → HA)

The integration subscribes to `snowbot/{SN}/device/{leaf}`.

| Leaf (`{leaf}`) | Frequency | Encoding | Description |
|-----------------|-----------|----------|-------------|
| `DeviceMSG` | ~1–2 Hz | zlib-compressed JSON | Full telemetry (battery, heading, RTK, activity, errors, head type, lights, etc.) |
| `heart_beat` | ~1 Hz | Plain JSON | Keepalive with minimal status |
| `data_feedback` | On change | zlib JSON | Confirmation after command execution |
| `plan_feedback` | On change | zlib JSON | Plan execution progress and completion |
| `cloud_points_feedback` | On change | zlib JSON | Map/path data for cloud sync |
| `ota_feedback` | On change | Plain JSON | Firmware update progress |

Discovery uses wildcard: `snowbot/+/device/DeviceMSG` subscribes for all robots on the broker simultaneously.

## Message Encoding

`DeviceMSG` payloads are **zlib-compressed JSON**. The decompression and deserialization is handled entirely by `python-yarbo`:

```python
import zlib, json

raw_payload: bytes = ...  # received from MQTT
decompressed = zlib.decompress(raw_payload)
telemetry = json.loads(decompressed)
```

`heart_beat` payloads are plain UTF-8 JSON (no compression).

The integration accesses decoded data exclusively through `python-yarbo` dataclasses. It does not manually decompress or parse MQTT payloads.

## Command Envelope

All published commands are JSON objects. `python-yarbo` constructs the envelope:

```json
{
  "cmd": "cmd_buzzer",
  "sn": "YB2024XXXXXXXX",
  "timestamp": 1705312200,
  "payload": {
    "enable": true
  }
}
```

## Controller Role

The EMQX broker supports multiple simultaneous MQTT clients, but only one client can hold the **controller role** at a time. Commands sent without the controller role may be ignored by the robot.

The integration acquires the controller role by publishing to `get_controller` on setup. See `security.md` for implications of multiple HA instances sharing the same broker.

## python-yarbo Integration Point

```python
from python_yarbo import YarboClient, YarboTelemetry

# Use your discovered or configured broker IP (never hardcode in production)
client = YarboClient(host="<broker-ip>", port=1883)
await client.connect()
await client.subscribe(sn="YB2024XXXXXXXX")

@client.on_telemetry
def handle(data: YarboTelemetry) -> None:
    # data is a fully decoded dataclass
    print(data.battery, data.head_type, data.activity)
```
