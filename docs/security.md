# Security Considerations

## Anonymous MQTT

The Yarbo base station runs an **unauthenticated MQTT broker** on port 1883. Any device on the same LAN segment can:

- Subscribe to all telemetry topics and read location, battery, activity, and head data in real time.
- Publish commands to any robot on the network (including `emergency_stop_active`).

This is a design constraint of the robot's firmware, not a limitation of this integration.

### Recommended Hardening

| Action | Description |
|--------|-------------|
| IoT VLAN isolation | Place the Yarbo base station on a dedicated VLAN. Route only HA host ↔ base station traffic. |
| Firewall rule | Allow TCP port 1883 inbound only from the HA host IP. Block all other LAN sources. |
| No port forwarding | Never expose port 1883 to the internet or DMZ. |
| Router-level MAC binding | Assign a static IP to the base station MAC to prevent IP spoofing. |

## Cloud Credential Storage

Cloud credentials (email and password for Yarbo cloud API) are optional. When provided:

- Stored in the HA **config entry data** dictionary.
- Config entry data is encrypted at rest by HA's secret storage (if HA is configured with an encryption key).
- Never logged at any log level.
- Never included in diagnostics downloads.

To rotate credentials, use the **Reconfigure** flow or remove and re-add the integration.

## Diagnostics PII Redaction

When the user downloads diagnostics via **Settings → Devices → Download Diagnostics**, the integration applies the following redaction:

| Field | Treatment |
|-------|-----------|
| Robot serial number (SN) | Last 4 characters visible; rest replaced with `****` |
| Head serial number | Fully replaced with `[REDACTED]` |
| GPS coordinates | Removed entirely |
| Cloud email | Replaced with `[REDACTED]` |
| Cloud password | Never included |
| WiFi SSID | Included (not considered sensitive) |
| IP address | Included (local LAN address only) |

## Rate Limiting

To prevent accidental command flooding:

- **Telemetry debounce**: Coordinator updates are throttled to at most once per `telemetry_throttle` seconds (default: 1 s, configurable in options flow).
- **Command serialization**: All MQTT publishes go through a per-device `asyncio.Lock`. Concurrent service calls queue and execute sequentially.

```python
async def send_command(self, cmd: str, payload: dict) -> None:
    async with self._command_lock:
        await self._client.publish(cmd, payload)
```

## Multiple HA Instances

If two HA instances connect to the same Yarbo base station broker:

- **Telemetry**: Both instances receive all telemetry. This is safe and expected.
- **Controller role**: Only one instance can hold the controller role at a time. The second instance to call `get_controller` will claim the role, causing the first to lose it and fire a `yarbo_controller_lost` event.

Running two HA instances with `auto_controller: true` against the same robot will cause controller role contention. Set `auto_controller: false` on the secondary instance to avoid this.

## Threat Model Summary

| Threat | Severity | Mitigation |
|--------|----------|------------|
| LAN attacker reads telemetry | Medium | IoT VLAN isolation |
| LAN attacker sends commands | High | IoT VLAN + firewall to HA only |
| Cloud credential exposure | Low | HA encrypted config entry storage |
| GPS data in diagnostics | Low | Coordinates stripped from diagnostics |
| Command flooding | Low | asyncio.Lock serialization |
