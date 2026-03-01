# Changelog

All notable changes to home-assistant-yarbo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

---

## [2026.3.20] — 2026-03-02

### Fixed
- **Config flow discovery timeout** — capped at 10 seconds; falls through to manual IP/port entry if no robot found
- **Blocking I/O in version guard** — `importlib.metadata.version()` now runs in executor thread

### Changed
- Community disclaimer added to README

---

## [2026.3.15] — 2026-03-02

### Added
- **Runtime library version guard** — integration now checks python-yarbo version at startup; raises `ConfigEntryNotReady` with actionable error if library is too old (prevents stale `/config/deps/` issues)
- **Regression tests** for `get_controller(timeout=...)` compatibility and `MIN_LIB_VERSION` constant

### Fixed
- **Blocking call warnings eliminated** — Sentry init runs in executor, import caches pre-warmed (`idna`, `paho-mqtt`, `certifi`, `charset-normalizer`), TCP socket check for broker reachability
- **Event loop closed RuntimeError** — guarded `call_soon_threadsafe` against closed loops in MQTT disconnect callback

### Changed
- `MIN_LIB_VERSION` set to `2026.3.15`
- Version bump to 2026.3.15

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

