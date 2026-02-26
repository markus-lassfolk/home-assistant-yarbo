# Roadmap

## v0.1.0 — MVP

**Goal**: Installable integration with live telemetry and basic control.

| Area | Deliverables |
|------|-------------|
| Config flow | DHCP discovery, manual IP entry, MQTT validation, naming step |
| Core entities | Battery sensor, activity sensor, charging binary_sensor, problem binary_sensor, head_type sensor |
| Control entities | Beep button, return_to_dock button, pause button, resume button, stop button |
| Events | `event` entity, `yarbo_job_started`, `yarbo_job_completed`, `yarbo_job_paused`, `yarbo_error` |
| Diagnostics | Robot SN, firmware version, MQTT connected, last seen, signal strength |
| Services | `yarbo.send_command`, `yarbo.pause`, `yarbo.resume`, `yarbo.return_to_dock` |
| Testing | 40% coverage target |

## v0.2.0 — Full Telemetry

**Goal**: All sensor data surfaced; full light and switch control.

| Area | Deliverables |
|------|-------------|
| Extended entities | RTK status, heading, chute angle, rain sensor, satellite count, charging power |
| Light entities | Group light entity, 7 individual LED channel lights |
| Switch entities | Buzzer switch, planning binary_sensor |
| Number entities | Chute velocity (-2000 to 2000) |
| Services | `yarbo.set_lights`, `yarbo.set_chute_velocity` |
| Events | `yarbo_head_changed`, `yarbo_low_battery`, `yarbo_controller_lost` |
| Blueprints | Low Battery Notification, Job Complete Notification |
| Options flow | `telemetry_throttle`, `auto_controller` |
| Testing | 55% coverage target |

## v0.3.0 — Scheduling and Weather

**Goal**: Plan execution and weather-reactive automations.

| Area | Deliverables |
|------|-------------|
| Services | `yarbo.start_plan` |
| Blueprints | Pause on Rain, Snow Deployment (all 4 blueprints complete) |
| Cloud auth | Optional cloud credentials in config flow and options flow |
| Options flow | `cloud_enabled` option |
| Testing | 65% coverage target |

## v0.4.0 — Map and Personality

**Goal**: GPS tracking, lawn mower platform, and UX improvements.

| Area | Deliverables |
|------|-------------|
| GPS tracking | `device_tracker` entity from RTK coordinates |
| Lawn mower platform | `lawn_mower` entity for head types 1 and 2 |
| Activity personality | `activity_personality` option (default, verbose, simple) |
| Logbook | Head change entries, job start/stop entries |
| Emergency stop | Emergency stop button entity |
| Testing | 70% coverage target |

## v1.0.0 — HACS Default

**Goal**: Production-quality release eligible for HACS default repository inclusion.

| Area | Deliverables |
|------|-------------|
| Firmware update | `update` entity with OTA trigger |
| Options flow | Full options flow with all settings |
| Repair flows | Auto-repair for lost controller, connection failure, SN mismatch |
| Translations | Complete `en.json`; skeleton files for `de`, `fr`, `zh-Hans` |
| CI/CD | GitHub Actions: lint, test, coverage gate, HACS validation |
| Brands PR | Submit to `home-assistant/brands` for official logo |
| Testing | 80% coverage target |

## Future (Post v1.0)

| Feature | Notes |
|---------|-------|
| `yarbo-card` | Custom Lovelace card with robot map overlay and live status |
| Automated zone creation | Generate HA zones from Yarbo plan boundaries |
| Camera proxy | Proxy robot camera feed via HA (v0.4+ firmware required) |
| Multi-robot dashboard | Aggregated view for households with multiple robots |
| Voice assistant integration | Expose mowing start/stop via Assist pipeline |

## Version Support Policy

| Component | Minimum | Notes |
|-----------|---------|-------|
| Home Assistant | 2024.12 | DataUpdateCoordinator push API stable |
| python-yarbo | Pinned per release | See `manifest.json` requirements |
| HACS | 1.34 | Required for blueprint import UI |
