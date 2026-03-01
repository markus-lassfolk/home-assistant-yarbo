# Changelog

All notable changes to home-assistant-yarbo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

---

## [2026.3.11] — 2026-03-01

### Changed

- **Typed python-yarbo methods** — replaced ~18 `publish_raw()` calls with typed method equivalents
  - `light.py`: `set_head_light(True/False)` instead of raw MQTT
  - `lawn_mower.py`: `resume()`, `pause_planning()` 
  - `number.py`: `set_blade_height()`, `set_blade_speed()`, `set_roller_speed()`, `set_sound_param()`, `set_charge_limit()`, `set_chute_steering_work()`
  - `select.py`: `set_turn_type()`, `push_snow_dir()`
  - `coordinator.py`: `start_plan()`, `in_plan_action()`
  - `services.py`: `start_waypoint()`, `save_current_map()`, `save_map_backup()`, `resume()`, `pause_planning()`
- **Charge limit validation** — `min_pct <= max_pct` enforced, reads current counterpart value before updating

### Added

- **Default error reporting** (beta) — built-in GlitchTip DSN for crash telemetry, opt-out via config or `YARBO_SENTRY_DSN=""`
- **HACS directory preparation** — brand assets, `hacs.yml`, Hassfest/HACS CI validation
- **Gitleaks CI** — secret scanning with allowlist for false positives

### Fixed

- **Gitleaks config format** — allowlist uses direct binary install instead of paid Action

---

## [2026.3.10] — 2026-03-01

First public release. Full Home Assistant integration for Yarbo robotic mowers/snow blowers via local MQTT.

### Added

- Config flow with auto-discovery (mDNS) and manual setup
- Lawn mower entity (start, pause, dock)
- 15+ sensor entities (battery, status, GPS, WiFi signal, head type, etc.)
- 8+ switch entities (child lock, lights, laser, smart vision, etc.)
- Number entities (blade height/speed, charge limits, sound volume)
- Select entities (turn type, snow push direction)
- Button entities (emergency stop, recharge, buzzer, etc.)
- Service calls (start plan, start waypoint, save map, send raw command)
- Diagnostics download
- Full test suite (400+ tests)

