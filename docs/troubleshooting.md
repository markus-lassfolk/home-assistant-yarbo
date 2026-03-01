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

**Symptoms:** The Work Plan select entity is empty.

**Cause:** The robot has no saved plans, or the plan list hasn't been read yet.

**Fix:**
- Create plans using the Yarbo app
- Reload the integration to refresh the plan list
- Check that `read_all_plan` succeeds (enable debug logging to verify)

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

## Integration Errors in HA Log

### Enable Debug Logging

To get detailed logs, add to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.yarbo: debug
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
