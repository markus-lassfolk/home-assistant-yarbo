# data_feedback payload shape (recorded from real traffic)

This document describes the **actual** structure of `data_feedback` messages received when the robot responds to `get_device_msg`, so handling can be implemented from real traffic instead of guessing.

## How the capture was made

1. **Record traffic** (from this repo, with python-yarbo installed):

   ```bash
   uv run --extra scripts python scripts/capture_mqtt_traffic.py \
     --broker 192.168.1.55 --sn YOUR_SN \
     --output /tmp/yarbo_cap.jsonl --duration 45
   ```

   Or from the python-yarbo repo (same script pattern): connect with `mqtt_log_path=output_path`, send `get_device_msg` every 10s, record all received MQTT to JSONL.

2. **Analyse payloads**:

   ```bash
   python scripts/analyze_mqtt_capture.py /tmp/yarbo_cap.jsonl
   ```

## Recorded shape for get_device_msg → data_feedback

Captured **2026-03-06** (broker 192.168.1.55, SN 24400102L8HO5227).

- **Topic leaf**: `data_feedback`
- **Top-level keys**: `state`, `msg`, `topic`, `data`
- **Telemetry**: The full DeviceMSG-like object (BatteryMSG, StateMSG, etc.) is **inside `data`**, not at top level.

Example (structure only):

```json
{
  "state": 0,
  "msg": "Device messages retrieved successfully.",
  "topic": "get_device_msg",
  "data": {
    "BatteryMSG": { ... },
    "BodyMsg": { ... },
    "BodyVersionMsg": { ... },
    "CombinedOdom": { ... },
    "DebugMsg": { ... },
    "EletricMSG": { ... },
    "HeadAndVersionCheck": { ... },
    "HeadMsg": { ... },
    "HeadSerialMsg": { ... },
    "HubInfoMSG": { ... },
    "LedInfoMSG": { ... },
    "NetMSG": { ... },
    "RTKMSG": { ... },
    "RadarMsg": { ... },
    "RunningStatusMSG": { ... }
  }
}
```

So:

- **Accept as telemetry**: any `data_feedback` payload that has a top-level `"data"` key which is a dict containing at least one of `BatteryMSG`, `StateMSG`, or the other *MSG keys above.
- **Unwrap for parsing**: when building `YarboTelemetry` from such a message, use `payload["data"]` (and optional `topic=payload.get("topic")` or the MQTT topic), not the top-level payload.

## What python-yarbo should do

So that Home Assistant (and any client) can treat **get_device_msg responses** as telemetry and update “Last Seen” etc.:

1. **Recognise get_device_msg responses as telemetry**  
   When a message on topic leaf `data_feedback` has:
   - top-level key `"data"`, and  
   - `payload["data"]` is a dict that contains DeviceMSG-like keys (e.g. `BatteryMSG`, `StateMSG`, …),  
   then treat it as a telemetry message (same semantics as a `DeviceMSG` message).

2. **Unwrap when parsing**  
   When building `YarboTelemetry` from such a `data_feedback` message, pass the **inner** dict to your existing parser, e.g.:
   - `YarboTelemetry.from_dict(payload["data"], topic=...)`  
   not `YarboTelemetry.from_dict(payload, topic=...)`.

3. **Where to apply this**  
   - In `MqttTransport.telemetry_stream()` (or equivalent): when you receive `data_feedback`, if `payload.get("data")` is a dict with DeviceMSG-like keys, either:
     - yield a `TelemetryEnvelope` with `kind="DeviceMSG"` and `payload=payload["data"]`, so existing `is_telemetry` and `to_telemetry()` work unchanged; or  
     - extend `TelemetryEnvelope.is_telemetry` and `to_telemetry()` so that for `kind=="data_feedback"` with such a `payload`, `is_telemetry` is True and `to_telemetry()` uses `payload["data"]`.
   - In any `wait_for_message(..., accept_if=...)` used for get_device_msg: the accept predicate should return True for payloads that have `payload.get("data")` as a dict containing at least one of the *MSG keys (e.g. `BatteryMSG`, `StateMSG`).

4. **Heartbeats**  
   If you also want “Last Seen” to update on `heart_beat` when no DeviceMSG/data_feedback is received, keep yielding the last cached telemetry on heart_beat (as discussed in the Last Seen troubleshooting).

## Scripts in this repo

| Script | Purpose |
|--------|--------|
| `scripts/capture_mqtt_traffic.py` | Connect with `mqtt_log_path`, send get_device_msg every N s, write all received MQTT (topic + payload) to JSONL. Requires python-yarbo. |
| `scripts/analyze_mqtt_capture.py` | Read JSONL, print message counts by topic and data_feedback payload structure (top-level keys, where BatteryMSG/StateMSG live). No extra deps. |

Run capture on the same broker (and SN) as Home Assistant to see the same traffic the integration would see.
