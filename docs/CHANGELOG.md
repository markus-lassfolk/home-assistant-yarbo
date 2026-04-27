# Changelog

All notable changes to home-assistant-yarbo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

---

## [2026.4.270] — 2026-04-27

Full notes: [docs/releases/v2026.4.270.md](releases/v2026.4.270.md).

Scope: everything after Git tag **[v2026.3.63](https://github.com/markus-lassfolk/home-assistant-yarbo/releases/tag/v2026.3.63)** on `main` (Sentry release tagging, event battery guard, then squash merge [#156](https://github.com/markus-lassfolk/home-assistant-yarbo/pull/156)).

### Breaking

- **Community Yarbo** — domain `community_yarbo`, folder `custom_components/community_yarbo/`, UI name **Community Yarbo** (coexists with [YarboInc/YarboHA](https://github.com/YarboInc/YarboHA)). Remove old `yarbo` entry, install new folder, restart, re-add; update entity IDs, `community_yarbo.*` services, events (e.g. `community_yarbo_job_completed`); MQTT under `community_yarbo_recordings/`.

### Added

- **Translations:** fi, sv, de, nl, nb, es, fr, it, pl (#131).
- **`CONFIG_SCHEMA`**, **`async_ensure_controller`**, broker-host regression tests, controller timeout tests, coordinator performance diagnostics test for `community_yarbo` (see **2026.3.62** below for coordinator diagnostics fields).

### Fixed

- **GlitchTip / Sentry** — `sentry_sdk.init` **release** uses integration **version** from metadata or `manifest.json`, not a raw git hash (`2539a70`).
- **Low battery / offline robot** — guard `None` `battery_capacity` before comparisons in `event.py` (`bdc735b`; [#146](https://github.com/markus-lassfolk/home-assistant-yarbo/issues/146)).
- **PR #156:** rename + `MIN_LIB_VERSION` **2026.3.60**, `YarboLocalClient(broker=..., sn=...)`, failover **polling restart** + **telemetry retry sleep**, **shutdown / telemetry** (#137, #154), **broker host** resolution (#155), **options & unload** (#148), **controller timeout** mapping (#147), **library guard** (#153), **Sentry** duplicate init + **`yarbo.error_reporting`** conftest stub, **CI** `python-yarbo@main`, **Copilot:** `docs/services.md` / **CONTRIBUTING** + **`discover_yarbo`** instead of direct **`paho.mqtt`** in `discovery.py` and DHCP probe.
- **Actions / dev deps:** `action-gh-release` v3 (#149), `github-script` v9 (#150), setuptools `>=82.0.1` (#151).

### Changed

- **Requirement:** `python-yarbo>=2026.3.60,<2027.0` (floor matches **2026.3.61–2026.3.63** work in the changelog below: polling, Last Seen write optimization, MQTT capture docs, performance troubleshooting).

---

## [2026.3.63] — 2026-03-06

### Changed
- **Last Seen / Last Seen Latency** — These diagnostic sensors now write state only when their rounded value actually changes (once per minute for Last Seen, once per 30s for Latency). This reduces recorder and Activity log updates and avoids flooding the logbook.

---

## [2026.3.62] — 2026-03-06

### Added
- **Performance diagnostics** — coordinator diagnostics now include `listener_count` and `poll_interval` to help diagnose "HA hangs" or high load when there are many entities.
- **Performance troubleshooting** — new section in [Troubleshooting](troubleshooting.md): "HA hangs or runs out of resources when Yarbo is enabled" (what to collect, what to try, how to report).
- **Debug timing** — when debug logging is on, log when `async_set_updated_data` takes >0.1s (listener count in message).
- **Performance test** — `tests/test_coordinator_performance.py` (diagnostics include listener_count and poll_interval).

### Changed
- **Diagnostic polling** — 0.3s delay between each diagnostic request (every 300s) to avoid blocking the event loop and reduce burst load on the robot.
- **Options** — improved description for `poll_acquire_controller` (when app is closed, what "acquire controller" means, when to leave off).

### Fixed
- One-time INFO when entity count >40 suggesting to raise telemetry update interval if HA is slow.

---

## [2026.3.61] — 2026-03-06

All changes since 2026.3.40.

### Changed
- **python-yarbo** — requirement `>=2026.3.60,<2027.0` for correct `data_feedback` get_device_msg handling and Last Seen updates.
- **Options UI** — clarified labels and descriptions for `poll_acquire_controller` (acquire when polling for telemetry) vs `auto_controller` (acquire before sending commands); added description for auto_controller.

### Added
- **MQTT capture and analysis** — `scripts/capture_mqtt_traffic.py`, `scripts/analyze_mqtt_capture.py`, [docs/mqtt-data-feedback-payload.md](mqtt-data-feedback-payload.md).
- **Testing before release** — [docs/testing-before-release.md](testing-before-release.md), `scripts/install_latest_to_hass.sh`.

### Documentation
- Troubleshooting: link to data_feedback payload doc and capture/analyze scripts (Last Seen).
- Development: link to Testing before release guide.

---

## [2026.3.21] — 2026-03-02

### Fixed
- **Sentry event filtering** — error reports now only capture exceptions from the Yarbo integration; errors from other HA integrations (Tibber, Victron, Cast, etc.) are dropped before sending

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

