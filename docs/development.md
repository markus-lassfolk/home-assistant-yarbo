# Development Guide

## Prerequisites

| Requirement | Minimum Version |
|-------------|----------------|
| Python | 3.12 |
| Home Assistant | 2024.12 |
| pip | 23.0 |
| git | 2.40 |

## Setup

```bash
git clone https://github.com/your-org/ha-yarbo-forge.git
cd ha-yarbo-forge

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements_test.txt
pre-commit install
```

`requirements_test.txt` includes `pytest-homeassistant-custom-component`, `pytest-asyncio`, `ruff`, `mypy`, and `python-yarbo` (from the mock/stub package used in tests).

## Running Tests

```bash
# Full test suite with coverage
pytest tests/ --cov=custom_components/yarbo --cov-report=term-missing

# Single test file
pytest tests/test_coordinator.py -v

# Tests matching a keyword
pytest tests/ -k "test_battery" -v
```

## Linting and Formatting

```bash
# Check style
ruff check custom_components/yarbo/

# Auto-fix style issues
ruff check --fix custom_components/yarbo/

# Format code
ruff format custom_components/yarbo/

# Type checking
mypy custom_components/yarbo/
```

Pre-commit hooks run `ruff check`, `ruff format`, and `mypy` automatically on `git commit`.

## Integration Structure

```
custom_components/yarbo/
├── __init__.py          # async_setup_entry, async_unload_entry
├── coordinator.py       # YarboDataCoordinator
├── entity.py            # YarboEntity base (unique_id, device_info)
├── config_flow.py       # ConfigFlow, OptionsFlow, ReconfigureFlow
├── sensor.py
├── binary_sensor.py
├── button.py
├── light.py
├── switch.py
├── number.py
├── event.py
└── services.py          # async_register_services
```

## Testing Strategy

### Mock python-yarbo

Tests use a mock `YarboClient` that never opens a network connection:

```python
# tests/conftest.py
from unittest.mock import AsyncMock, MagicMock
from pytest_homeassistant_custom_component.common import MockConfigEntry

@pytest.fixture
def mock_yarbo_client():
    client = MagicMock()
    client.connect = AsyncMock()
    client.subscribe = AsyncMock()
    client.publish = AsyncMock()
    client.disconnect = AsyncMock()
    return client
```

### Unit Tests (entity logic)

Test that entity state properties return expected values given specific `coordinator.data` values:

```python
async def test_battery_sensor_state(hass, coordinator):
    coordinator.data.battery = 75
    sensor = BatterySensor(coordinator, "YB001")
    assert sensor.native_value == 75
```

### Integration Tests (config flow)

Use `pytest-homeassistant-custom-component` to run full config flow against a mock client:

```python
async def test_config_flow_dhcp(hass, mock_yarbo_client):
    result = await hass.config_entries.flow.async_init(
        "yarbo", context={"source": SOURCE_DHCP}, data=dhcp_data
    )
    assert result["type"] == FlowResultType.FORM
```

## Coverage Targets by Milestone

| Milestone | Target Coverage | Focus Areas |
|-----------|----------------|-------------|
| v0.1.0 | 40% | Config flow, coordinator, core entities |
| v0.2.0 | 55% | Extended entities, services, options flow |
| v0.3.0 | 65% | Blueprints, scheduling, cloud auth |
| v0.4.0 | 70% | lawn_mower platform, GPS tracker, logbook |
| v1.0.0 | 80% | Repair flows, OTA, full entity coverage |

Coverage is measured with `pytest-cov`. CI fails if coverage drops below the milestone target.

## Adding a New Entity

1. Define the entity class in the appropriate platform file (e.g., `sensor.py`).
2. Add it to the `async_setup_entry` list in that file.
3. Add translation strings to `translations/en.json`.
4. Add entity description to `docs/entities.md`.
5. Write unit tests covering `available`, `native_value`/`is_on`, and `unique_id`.
