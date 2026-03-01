---
layout: default
title: Development
nav_order: 12
description: "Contributing guide for the Yarbo Home Assistant integration"
---

# Development
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer.
{: .warning }

1. TOC
{:toc}

---

## Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Python | 3.12 | Matches HA 2024.1+ |
| Home Assistant | 2024.1 | For testing |
| `python-yarbo` | 0.1.0 | Protocol library |
| Git | any | |

---

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/<your-fork>/home-assistant-yarbo.git
cd home-assistant-yarbo
```

### 2. Set Up Development Environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.dev.txt
```

### 3. Install in a Test HA Instance

The easiest way to test is with a development HA instance (container or `venv`):

```bash
# If using HA in a Python venv:
ln -s $(pwd)/custom_components/yarbo ~/.homeassistant/custom_components/yarbo
```

Or use the [Home Assistant Dev Container](https://developers.home-assistant.io/docs/development_environment/) setup.

---

## Project Structure

```
home-assistant-yarbo/
├── custom_components/
│   └── yarbo/               # Integration source
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── button.py
│       ├── switch.py
│       ├── number.py
│       ├── select.py
│       ├── light.py
│       ├── lawn_mower.py
│       ├── device_tracker.py
│       ├── update.py
│       ├── services.yaml
│       ├── strings.json
│       └── translations/
│           └── en.json
├── tests/                   # Test suite
├── docs/                    # GitHub Pages documentation
└── blueprints/              # HA automation blueprints
```

---

## Code Style

The project follows the [Home Assistant coding standards](https://developers.home-assistant.io/docs/development_guidelines):

- **Formatter:** Black (line length 88)
- **Linter:** Ruff
- **Type checking:** mypy with HA stubs
- **Import order:** isort (via Ruff)

Run all checks:

```bash
ruff check custom_components/yarbo/
black --check custom_components/yarbo/
mypy custom_components/yarbo/
```

Auto-fix:

```bash
ruff check --fix custom_components/yarbo/
black custom_components/yarbo/
```

---

## Testing

### Run Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
pytest --cov=custom_components.yarbo tests/
```

### Write a Test

Tests use `pytest-homeassistant-custom-component` for HA test infrastructure:

```python
# tests/test_sensor.py
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_battery_sensor(hass: HomeAssistant) -> None:
    # Set up integration with mock data
    entry = MockConfigEntry(domain="yarbo", data={...})
    entry.add_to_hass(hass)

    with patch("custom_components.yarbo.coordinator.YarboClient") as mock:
        mock.return_value.async_connect = AsyncMock()
        await hass.config_entries.async_setup(entry.entry_id)

    state = hass.states.get("sensor.yarbo_test_battery")
    assert state is not None
    assert state.state == "83"
```

---

## Adding a New Entity

### Step 1: Define the Entity Descriptor

In the relevant platform file (e.g., `sensor.py`), add an entry to the entity descriptions list:

```python
YarboSensorEntityDescription(
    key="my_new_sensor",
    name="My New Sensor",
    native_unit_of_measurement=UnitOfMeasurement.SOME_UNIT,
    device_class=SensorDeviceClass.SOME_CLASS,
    entity_registry_enabled_default=False,  # disable by default if diagnostic
    entity_category=EntityCategory.DIAGNOSTIC,
    value_fn=lambda data: data.get("my_field"),
)
```

### Step 2: Map to Telemetry

The `value_fn` receives the full `DeviceMSG` dictionary. Navigate the nested structure as needed:

```python
value_fn=lambda data: data.get("BatteryMSG", {}).get("my_new_field"),
```

### Step 3: Add Strings

Add a translation entry in `strings.json` and `translations/en.json`:

```json
{
  "entity": {
    "sensor": {
      "my_new_sensor": {
        "name": "My New Sensor"
      }
    }
  }
}
```

### Step 4: For Head-Specific Entities

Set `required_head_type` on the description:

```python
YarboSensorEntityDescription(
    key="blade_temp",
    required_head_type=HEAD_LAWN_MOWER,
    ...
)
```

---

## Adding a New Command/Service

### Step 1: Add to `services.yaml`

```yaml
my_new_service:
  name: My New Service
  description: Does something useful
  fields:
    device_id:
      required: true
      selector:
        device:
          integration: yarbo
    my_param:
      required: true
      selector:
        number:
          min: 0
          max: 100
```

### Step 2: Register the Service in `__init__.py`

```python
async def handle_my_new_service(call: ServiceCall) -> None:
    coordinator = _get_coordinator(hass, call.data["device_id"])
    await coordinator.send_command(
        "my_mqtt_command",
        {"param": call.data["my_param"]}
    )

hass.services.async_register(
    DOMAIN,
    "my_new_service",
    handle_my_new_service,
    schema=MY_NEW_SERVICE_SCHEMA,
)
```

---

## Protocol Research

When adding support for new robot features, the [Protocol Reference](protocol-reference.md) documents the known MQTT command names and payload formats. The [Command Catalogue](protocol-reference.md#core-commands) lists all known commands.

To observe what commands the robot responds to, enable debug logging (`logger: custom_components.yarbo: debug`) and watch for `data_feedback` messages after sending commands with `yarbo.send_command`.

---

## Submitting a Pull Request

1. Create a branch from `main`:
   ```bash
   git checkout -b feat/my-new-feature
   ```

2. Make your changes. Keep commits focused and write clear commit messages.

3. Add tests for new functionality.

4. Run the full test suite and linters (all must pass):
   ```bash
   pytest tests/
   ruff check custom_components/yarbo/
   black --check custom_components/yarbo/
   ```

5. Update relevant documentation in `docs/` if needed.

6. Open a PR against `main`. In the PR description:
   - Describe what the change does
   - Reference any related issues
   - Note which entities/services are added or changed
   - Describe how you tested it (ideally with a real robot)

---

## Documentation

The docs site is built with [just-the-docs](https://just-the-docs.com/) and served via GitHub Pages from the `docs/` directory.

To preview locally:

```bash
cd docs
bundle install
bundle exec jekyll serve
# Open http://localhost:4000
```

---

## Reporting Issues

- **Bugs:** [GitHub Issues](https://github.com/markus-lassfolk/home-assistant-yarbo/issues)
- **Feature requests:** Open a GitHub Issue with the `enhancement` label
- **Security issues:** Use GitHub's private security reporting

When reporting a bug, include:
- HA version
- Integration version
- Robot firmware version
- Debug logs (enable via Configuration options or `logger` config)

---

## Related Pages

- [Architecture](architecture.md) — integration internals
- [Protocol Reference](protocol-reference.md) — MQTT protocol
- [Entities](entities.md) — entity reference
