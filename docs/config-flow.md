# Config Flow

## Discovery Methods

### DHCP Auto-Discovery

When a Yarbo base station joins the network, HA detects it via its MAC OUI (`C8:FE:0F:*`) and initiates the config flow automatically. The user sees a notification to configure the newly found device.

```
DHCP discovery → confirm_discovery step → mqtt_validate step → name step → (optional) cloud_auth step
```

### Manual Entry

Users can also add the integration via **Settings → Devices & Services → Add Integration → Yarbo**.

```
user step (IP input) → mqtt_validate step → name step → (optional) cloud_auth step
```

## Flow Steps

### Step: `user` / `confirm_discovery`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `host` | `str` | Yes | IP address of the base station |

Pre-filled from DHCP context when auto-discovered.

### Step: `mqtt_validate`

Validates the MQTT connection and extracts the robot identity.

1. Connect to `host:1883` (unauthenticated) via `python-yarbo`.
2. Subscribe to `snowbot/+/device/DeviceMSG`.
3. Wait up to **10 seconds** for a telemetry message.
4. Extract `SN` and `dc_sn` from the first message received.
5. Check `config_entries` for duplicate SN → abort if already configured.

### Step: `name`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `name` | `str` | `"Yarbo {SN[-4:]}"` | Friendly name for the device |

### Step: `cloud_auth` (optional)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `cloud_email` | `str` | No | Yarbo cloud account email |
| `cloud_password` | `str` | No | Yarbo cloud account password |

Cloud credentials enable firmware OTA and map sync features (v0.3+). Skip to complete setup without cloud.

## Error Table

| Error Key | Trigger Condition | User-Visible Message |
|-----------|------------------|----------------------|
| `cannot_connect` | TCP connection to port 1883 refused or timed out | "Cannot connect to the Yarbo base station. Check the IP address and network." |
| `no_telemetry` | Connected successfully but no `DeviceMSG` received within 10 s | "Connected but received no telemetry. Ensure the robot is powered on." |
| `decode_error` | Message received but failed zlib/JSON decode | "Received an unrecognized message format. Check python-yarbo version." |
| `already_configured` | SN matches an existing config entry | "This Yarbo robot is already configured." |
| `invalid_auth` | Cloud credential rejection (cloud_auth step only) | "Invalid cloud credentials." |

## Options Flow

Accessible via **Settings → Devices & Services → Yarbo → Configure**.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `telemetry_throttle` | `int` (seconds) | `1` | Minimum seconds between coordinator updates |
| `auto_controller` | `bool` | `true` | Automatically claim controller role on startup |
| `cloud_enabled` | `bool` | `false` | Enable cloud features (requires cloud_auth) |
| `activity_personality` | `select` | `"default"` | Controls how the activity sensor maps raw states (`default`, `verbose`, `simple`) |

## Reconfigure Flow

Allows changing the host IP without removing and re-adding the integration. Triggered via **3-dot menu → Reconfigure**.

Steps: `reconfigure` (new IP input) → `mqtt_validate` (must return same SN) → done.

If the SN from the new IP does not match the stored SN, the flow aborts with error `wrong_device`.

## Config Entry Data Schema

```python
# config_entry.data (persisted, encrypted)
{
    "host": "<broker-ip>",
    "sn": "YB2024XXXXXXXX",
    "dc_sn": "DC2024XXXXXXXX",
    "name": "Yarbo Front Yard",
    "cloud_email": "user@example.com",   # optional
    "cloud_password": "...",              # optional
}

# config_entry.options (user-adjustable)
{
    "telemetry_throttle": 1,
    "auto_controller": True,
    "cloud_enabled": False,
    "activity_personality": "default",
}
```
