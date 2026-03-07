---
layout: default
title: Testing before release
nav_order: 11
description: "Manually update HASS with latest integration and python-yarbo, then verify behaviour"
---

# Testing before release
{: .no_toc }

Use this flow to run the **latest** integration and **latest** python-yarbo on your Home Assistant instance before publishing a release, and to verify telemetry and Last Seen in both script-driven and HASS-only setups.

1. TOC
{:toc}

---

## 1. Install latest integration and python-yarbo

### Option A: Same machine (HA in venv or config dir available)

From the `home-assistant-yarbo` repo:

```bash
# Set your HA config path (where custom_components/ lives)
export HASS_CONFIG="$HOME/.homeassistant"   # or /path/to/ha/config

# Optional: set python-yarbo path if not ../python-yarbo
export PYTHON_YARBO="$HOME/python-yarbo"

./scripts/install_latest_to_hass.sh "$HASS_CONFIG" "$PYTHON_YARBO"
```

Then install the **python-yarbo** wheel into the same Python environment Home Assistant uses:

```bash
# If HA runs in a venv:
source /path/to/homeassistant/bin/activate
pip install --force-reinstall /path/to/home-assistant-yarbo/dist_wheels/python_yarbo-*.whl
```

Restart Home Assistant.

### Option B: HA on another host (e.g. HA OS / Supervised)

1. **Integration**
   - Copy the contents of `custom_components/yarbo/` to your HA config (e.g. via Samba share, or **Settings → Add-ons → Samba share** then copy to `config/custom_components/yarbo/`).
   - Or from your dev machine:  
     `rsync -av custom_components/yarbo/ user@ha-host:/config/custom_components/yarbo/`

2. **python-yarbo**
   - Build a wheel on your dev machine:
     ```bash
     cd /path/to/python-yarbo
     python3 -m build -w
     # Wheel is in dist/python_yarbo-*.whl
     ```
   - Copy the wheel to the HA host (e.g. into `/config` or a folder accessible from the **Terminal & SSH** add-on).
   - In **Terminal & SSH** (or SSH into the host), install it into HA’s environment. On HA OS this is often:
     ```bash
     pip install --force-reinstall /config/python_yarbo-2026.3.60-py3-none-any.whl
     ```
     (Path and `pip` location depend on your setup; use the add-on’s docs if needed.)

3. **Restart** Home Assistant.

---

## 2. Verify integration and library versions

1. Open **Settings → Devices & Services → Yarbo** (your entry).
2. Click **⋮ → Diagnostics**.
3. Check:
   - **integration_version** matches the version in `custom_components/yarbo/manifest.json` (e.g. `2026.3.60`).
   - Under **connection**, **broker_host** (or **actual_broker_host**) is the broker IP HA is using.
   - Under **coordinator**, **last_telemetry_received_utc** and **seconds_since_last_telemetry** — these will be used below to confirm telemetry is flowing.

If the integration fails to load with “python-yarbo … is too old”, the installed library is still the old one: install the wheel you built (see above) and restart HA again.

---

## 3. Verification A: python-yarbo script sending updates (same broker as HA)

This checks that when an **external script** sends `get_device_msg` on the **same broker** as HA, HA receives the responses and Last Seen (and telemetry) update.

1. Ensure the Yarbo integration is configured to use the **same** broker as the script (e.g. `192.168.1.55`). Check **Diagnostics → connection → broker_host**.
2. On a machine that can reach the broker, run a script that sends `get_device_msg` every 10 seconds (e.g. from the **python-yarbo** repo):
   ```bash
   uv run python scripts/test_polling_with_app_in_control.py \
     --broker 192.168.1.55 --sn YOUR_SN --duration 120 --no-controller
   ```
   Use the same `--broker` as in HA diagnostics.
3. In HA, open the Yarbo device and watch:
   - **Last Seen** sensor: it should update every ~10–30 seconds (e.g. “1 minute ago” then “30 seconds ago”).
   - **Diagnostics → coordinator → last_telemetry_received_utc**: the timestamp should advance while the script runs.
4. Optional: **Developer Tools → Logs** — set `logger: custom_components.yarbo: info` and look for log lines like “Telemetry received (first in Xs)” to confirm the coordinator is processing incoming telemetry.

**Pass:** Last Seen and coordinator diagnostics update while the script is running on the same broker.

---

## 4. Verification B: HASS only (no external script)

This checks that HA’s **own** telemetry path works: either from the robot’s **DeviceMSG** stream (when the app is connected) or from the integration’s **polling** (e.g. `get_status` / get_device_msg) if configured.

1. **Stop** any external script that was sending `get_device_msg` (so only HA is talking to the broker).
2. Ensure the robot is powered and reachable; optionally open the Yarbo app briefly so the robot may send **DeviceMSG** for a while.
3. In HA, watch:
   - **Last Seen**: should still update periodically (from DeviceMSG at ~1–2 Hz when the app is connected, or from HA’s own polling if enabled and no DeviceMSG).
   - **Diagnostics → coordinator → last_telemetry_received_utc** and **seconds_since_last_telemetry**: should continue to update.
4. If your integration options include a **poll interval** (or similar), ensure it’s enabled so that when the app is closed, HA still requests telemetry (e.g. get_device_msg) at the configured interval. Then close the Yarbo app and confirm Last Seen still updates after a short delay.

**Pass:** Last Seen and coordinator diagnostics update with no external script, using only HA’s connection and (if applicable) its polling.

---

## 5. Summary

| Step | What to do | What to check |
|------|------------|----------------|
| 1 | Install latest integration + python-yarbo, restart HA | Diagnostics show correct integration_version; no “python-yarbo too old” |
| 2 | — | Diagnostics show broker_host and coordinator timestamps |
| 3 | Run get_device_msg script on same broker as HA | Last Seen and last_telemetry_received_utc update |
| 4 | Stop script; rely only on HA | Last Seen still updates (DeviceMSG or HA polling) |

If both verifications pass, the stack is behaving as intended for release testing.
