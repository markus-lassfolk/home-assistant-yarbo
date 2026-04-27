---
layout: default
title: Troubleshooting
nav_order: 10
description: "Common problems and solutions for the Yarbo integration"
---

# Troubleshooting
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

1. TOC
{:toc}

---

## Integration Won't Set Up

### "Cannot connect" Error

**Symptoms:** Setup fails with `cannot_connect` error.

**Causes and fixes:**

| Cause | Fix |
|-------|-----|
| Wrong IP address | Find the robot's IP in your router's DHCP table — look for a device named `YARBO*` or with MAC prefix `C8:FE:0F` |
| Robot is in sleep mode | Wake the robot using the Yarbo app, then retry setup |
| Firewall blocking port 1883 | Check that your HA host can reach the robot on TCP port 1883 |
| Different network segment | Ensure HA and the robot are on the same subnet, or add a route |
| Robot not connected to Wi-Fi | Connect the robot to your network via the Yarbo app first |

**Test connectivity from HA host:**
```bash
# In the HA terminal / SSH
nc -zv <robot_ip> 1883
```

### "No Telemetry" Error

**Symptoms:** The integration connects but times out waiting for data.

**Causes:**
- Robot is in deep sleep — send a wake command via the Yarbo app
- Robot's MQTT topic prefix doesn't match expected pattern (unusual hardware variation)

**Fix:** Open the Yarbo app, wake/activate the robot, then retry the HA setup.

### Robot Not Auto-Discovered

**Symptoms:** No discovery notification appears in Settings.

**Causes:**
- HA's DHCP watcher may not have seen the robot's DHCP request
- Robot uses a static IP

**Fix:** Go to **Settings → Devices & Services → Add Integration → Yarbo** and enter the IP manually.

---

## Entities Show "Unavailable"

### All Entities Unavailable

**Cause:** Lost MQTT connection to the robot.

**What to check:**
1. Is the robot powered on and connected to Wi-Fi?
2. Has the robot's IP address changed? (DHCP lease expiry)
3. Is Home Assistant's network connection healthy?

**Fix:**
- Check the `Connection` sensor — if it shows "unavailable", the MQTT connection is lost
- Go to **Settings → Devices & Services → Yarbo → Reconfigure** to update the IP address
- Restart the integration entry: **Settings → Devices & Services → Yarbo → ⋮ → Reload**

### Last Seen Not Updating When Running a Script (e.g. get_status / test_polling_with_app_in_control)

**Symptoms:** You run a python-yarbo script that sends `get_device_msg` (e.g. `test_polling_with_app_in_control.py --broker 192.168.1.55 --sn ...`), and the robot responds with telemetry, but the Home Assistant **Last Seen** sensor still shows an old value (e.g. "25 minutes ago").

**Cause:** Home Assistant and the script use **different MQTT brokers**. The robot sends the response to the **same broker** the request was sent to. So:

- If the script uses `--broker 192.168.1.55`, the robot’s `data_feedback` reply is published on the MQTT server at **192.168.1.55**.
- If the integration is configured with a different broker (e.g. **192.168.1.24**), HA is subscribed on 192.168.1.24 and **never receives** those messages.

**How to check:**

1. In Home Assistant: **Settings → Devices & Services → Yarbo → ⋮ → Diagnostics**. In the **connection** section, note **broker_host** (the IP HA is connected to).
2. Compare with the broker you pass to the script (e.g. `--broker 192.168.1.55`). If they differ, that’s why Last Seen doesn’t update.

**Fix:**

- **Option A:** Reconfigure the integration to use the **same** broker as the script (e.g. 192.168.1.55): **Settings → Devices & Services → Yarbo → ⋮ → Reconfigure** and set the base station / broker IP to 192.168.1.55.
- **Option B:** Run the script with the **same** broker as HA (e.g. `--broker 192.168.1.24` if that’s what diagnostics show).

Some setups have two broker IPs (e.g. rover 192.168.1.55 and DC 192.168.1.24) that mirror traffic; if yours doesn’t, HA and the script must use the same broker to see each other’s traffic.

**Also:** Last Seen updates when the integration receives any telemetry: **DeviceMSG** (when the app is connected), **data_feedback** (e.g. from the integration’s own polling or a script’s `get_device_msg`), or **heart_beat** (robot sends ~1 Hz when connected). So with the same broker, Last Seen should update when the script runs. If it still doesn’t, check **Diagnostics → coordinator → last_telemetry_received_utc** while the script runs; if that timestamp doesn’t advance, the integration isn’t receiving those messages.

For the exact **data_feedback** payload shape (so the library can parse get_device_msg responses correctly), see [MQTT data_feedback payload](mqtt-data-feedback-payload.md). The integration provides scripts to record and analyse real MQTT traffic: `scripts/capture_mqtt_traffic.py` and `scripts/analyze_mqtt_capture.py`.

### Only Some Entities Unavailable

**Cause:** Head-specific entities are disabled when the corresponding head type is not installed. This is expected behaviour.

For example, `Snow Push Direction` is unavailable when no Snow Blower head is installed.

See [Multi-Head Guide](multi-head.md) for entity availability per head type.

---

## Commands Don't Work

### Buttons Don't Respond

**Symptoms:** Pressing a button entity (e.g., Return to Dock) doesn't make the robot move.

**Causes and fixes:**

| Cause | Fix |
|-------|-----|
| Controller role held by Yarbo app | Close the Yarbo app on all devices, then try again |
| Robot is in an error state | Check the `Problem` binary sensor and `Error Code` sensor |
| Robot is in sleep mode | Wake it via the Activity sensor or the Yarbo app |
| Integration lost connection | Reload the integration |

**Notes on controller role:** The integration sends `get_controller` before every command. If the Yarbo app is connected and active, it may re-acquire the role between commands. Close the app completely (not just minimised) if you want HA to have reliable control.

### Lights Don't Change

**Symptoms:** The light entities show the correct state, but the robot's lights don't visibly change.

**Notes:**
- Light entities use **assumed state** — the state shown is what was last sent, not confirmed by the hardware
- Ensure the `get_controller` command succeeds first (watch the `Connection` sensor)
- Some light commands are fire-and-forget with no hardware acknowledgement

---

## Work Plan Issues

### Work Plan Select Shows No Plans

**Symptoms:** The Work Plan select entity is empty (no options).

**Cause:** The robot has no saved plans, or the plan list has not been read yet. Many Yarbo robots **do not respond** to the `read_all_plan` command when idle — they only reply when the robot is in an active state (e.g. working).

**Fix:**
- Create at least one plan in the Yarbo app if you have not already.
- **Reload the integration** after creating plans: **Settings → Devices & Services → Yarbo → ⋮ → Reload**.
- The integration automatically **retries** loading the plan list when the robot starts working (e.g. when you start a plan from the app). After the robot has been active, the Work Plan select should populate; you can reload the integration to refresh immediately.
- To confirm whether the robot is responding, enable **Debug logging** for the integration (integration options) and check logs for `read_all_plan` (e.g. "returned no data" when idle is normal).

### Plan Doesn't Start

**Symptoms:** Selecting a plan in the Work Plan entity doesn't start the robot.

**Causes:**
- Battery too low — robot won't start a plan below the configured minimum battery level
- No RTK GPS fix — the robot may require a GPS fix before starting
- Error condition active — check the `Problem` binary sensor

---

## GPS / Location Issues

### Device Tracker Shows Wrong Location

**Cause:** RTK GPS needs time to achieve a fix after power-up. Until a fix is acquired, the device tracker may show stale coordinates.

**Fix:** Wait a few minutes outdoors with clear sky view for the RTK fix to establish. The `RTK Status` sensor shows the current fix quality (`rtk_fixed` is best).

### RTK Status Shows "gps" Instead of "rtk_fixed"

**Cause:** No RTCM correction data is available.

**What this means:** The robot's positioning accuracy is lower (~1-3m) instead of RTK-grade accuracy (<5cm).

**Fix:**
- Ensure the base station is powered on and has a clear sky view
- Check the `RTCM Age` sensor — if it's >10 seconds, the correction stream is interrupted
- Check the `RTCM Source Type` sensor for the active correction source

---

## High Battery Drain / Unexpected Behaviour

### Robot Not Returning to Dock After Work

**Check:** Is the `Return to Dock` button available? Is the battery level above the minimum configured return threshold?

The robot automatically returns to the dock when the battery drops below the `Battery Charge Min` setting. This can be checked in the number entities.

### Robot Not Charging

**Symptoms:** Robot is on the dock but `Charging` binary sensor is off.

**Checks:**
- `Wireless Charge State` sensor — shows the charging subsystem state
- `Wireless Charge Error` sensor — non-zero indicates a charging error
- `Charging Power` sensor — should show positive wattage when charging

---

## HA hangs or runs out of resources when Yarbo is enabled

If Home Assistant becomes slow, unresponsive, or runs out of memory/CPU after you enable the Yarbo integration, and there is **nothing useful in the logs** or in GlitchTip, use the steps below to narrow it down.

### 1. Collect diagnostics (no logs needed)

1. Go to **Settings → Devices & Services → Yarbo → ⋮ → Diagnostics**.
2. Download or copy the diagnostics JSON.
3. In the **coordinator** section, note:
   - **listener_count** — number of entities (sensors, switches, buttons, etc.). High values (e.g. 50+) mean every telemetry update notifies many entities; if your system is already under load, this can add up.
   - **throttle_interval** — how often (seconds) we push updates to HA. Lower = more updates per minute.
   - **poll_interval** — how often we request status from the robot when the app is closed.
4. In **mqtt_recording**, if **enabled** is true, recording writes to disk on every message; on slow or busy systems this can contribute to load.

Share these values when reporting the issue (e.g. listener_count, throttle_interval, mqtt_recording.enabled).

### 2. Try these changes first

| Change | Why it can help |
|--------|------------------|
| **Raise telemetry update interval** | In Yarbo options, set *Telemetry update interval* to **2–5 seconds** (default is 1). Fewer updates = less work for the recorder and entity callbacks. |
| **Turn off MQTT recording** | If it’s on, disable *MQTT recording* in options. Stops writing to disk on every message. |
| **Raise poll interval** | If the app is often closed, set *Telemetry poll interval* to **30** or **60** seconds instead of 10. Reduces how often we ask the robot for status. |
| **Disable debug logging** | If you had turned on *Debug logging*, turn it off. Debug I/O can add load. |

### 3. Enable debug to measure update cost (optional)

If the problem persists, enable **Debug logging** for the integration (options or `logger: custom_components.yarbo: debug`). After a few minutes, check the log for lines like:

```text
async_set_updated_data took 0.XXXs (listeners=N)
```

If you see times **over 0.1–0.2 seconds** regularly, entity updates are taking significant time; raising the telemetry update interval (step 2) usually helps. If you see a one-time INFO about “Yarbo has N entities … try raising telemetry update interval”, that’s a hint to use a higher throttle.

### 4. Compare with and without Yarbo

- Disable or remove the Yarbo integration and restart HA. If the system is fine without it, the cause is likely this integration or its interaction with your setup.
- Re-enable Yarbo with the options above (higher throttle, no recording, higher poll interval) and see if the problem comes back.

### 5. Report an issue

When opening a GitHub issue, please include:

- Diagnostics JSON (or at least coordinator.listener_count, throttle_interval, poll_interval, mqtt_recording.enabled).
- What you tried from step 2 and whether it helped.
- HA version, OS (e.g. HA OS / Supervised / venv), and whether you have one or multiple Yarbo devices.

---

## Integration Errors in HA Log

### Enable Debug Logging

To get detailed logs, add to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.community_yarbo: debug
    python_yarbo: debug
```

Or enable via the integration options: **Settings → Devices & Services → Yarbo → Configure → Debug logging**.

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `MQTT connection lost` | TCP connection to robot dropped | Check network; robot may be rebooting |
| `Cannot decompress payload` | Received unexpected uncompressed data | May be a firmware version mismatch |
| `get_controller timeout` | Controller acquisition timed out | Robot busy or Yarbo app active |
| `Unexpected topic` | Message on an unexpected topic | Non-critical; may be new firmware feature |

---

## After Updating the Integration

### Entities Missing or Duplicated After Update

**Fix:** Restart Home Assistant after installing any integration update. Sometimes a full HA restart is needed (not just integration reload) for new entities to appear.

### Stale Entity States After Robot Firmware Update

If Yarbo released a firmware update that changes the telemetry format, entity states may be incorrect until the integration is updated.

**Check:** Look at the integration's GitHub Issues for known firmware compatibility notes.

---

## Getting Help

1. **Check the [FAQ](faq.md)** for common questions
2. **Enable debug logging** and collect logs during the problematic behaviour
3. **Open a GitHub issue** at [github.com/markus-lassfolk/home-assistant-yarbo/issues](https://github.com/markus-lassfolk/home-assistant-yarbo/issues) with:
   - Your HA version
   - Integration version
   - Robot firmware version (visible in the Yarbo app)
   - Debug logs showing the problem
   - Steps to reproduce

---

## Related Pages

- [Configuration](configuration.md) — options and reconfiguration
- [FAQ](faq.md) — frequently asked questions
- [Architecture](architecture.md) — integration internals
