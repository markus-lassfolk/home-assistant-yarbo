# Contributing to home-assistant-yarbo

Thank you for contributing! This is a HACS custom integration for Yarbo robot mowers.

## Development Setup

### Prerequisites
- Python 3.12 or 3.13
- Home Assistant 2024.12+
- A Yarbo robot on your local network (or use the test fixtures)

### Quick Start

```bash
git clone https://github.com/markus-lassfolk/home-assistant-yarbo
cd home-assistant-yarbo

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install test dependencies
pip install -r requirements_test.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
ruff check custom_components/ tests/
ruff format --check custom_components/ tests/
mypy custom_components/yarbo/
```

### Installing in Home Assistant (dev mode)

1. Copy `custom_components/yarbo/` to your HA `config/custom_components/yarbo/`
2. Restart Home Assistant
3. Add the integration: Settings → Devices & Services → Add Integration → Yarbo

## Code Standards

### Required for all Python files
- Type annotations on all function signatures
- Docstrings on all public classes and methods
- `from __future__ import annotations` at the top
- `async`/`await` throughout (never blocking I/O in the event loop)
- Unit of measure: use `homeassistant.const` constants, not raw strings

### Entity unique IDs
Always follow: `{robot_sn}_{entity_key}`

Example: `2440011234567890_battery`

### Never in the integration
- `import paho.mqtt` — use `python-yarbo` exclusively
- Raw MQTT topic strings — use python-yarbo constants
- `time.sleep()` — use `await asyncio.sleep()`
- Blocking network calls on the event loop

### Coordinator pattern
The integration uses a push-based coordinator (no polling interval).
- Data comes from `python-yarbo`'s `client.watch_telemetry()` async generator
- Never set `update_interval` on the coordinator
- Call `coordinator.async_set_updated_data()` from the telemetry loop

## Pull Request Process

1. Branch from `develop` (not `main`)
2. Name your branch: `feature/short-description` or `fix/issue-number-description`
3. Write tests for new functionality
4. Ensure CI passes: `hassfest`, `hacs-validate`, `lint`, `test`
5. Update relevant docs in `docs/`
6. Reference the GitHub issue in your PR description

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full design overview.

Key docs:
- [Config flow](docs/config-flow.md) — DHCP discovery, manual setup
- [Entities](docs/entities.md) — Full entity list with sources
- [MQTT protocol](docs/mqtt-protocol.md) — Topic reference
- [Development](docs/development.md) — Testing strategy and coverage targets

## Milestones

- **v0.1.0**: Config flow, core sensors/buttons, push coordinator, diagnostics
- **v0.2.0**: Full telemetry, lights, numbers, switches
- **v0.3.0**: Scheduling, blueprints, optional cloud
- **v0.4.0**: GPS device_tracker, personality, lawn_mower platform
- **v1.0.0**: HACS default ready, 80% test coverage

See [docs/roadmap.md](docs/roadmap.md) for detail.

## Questions?

Open a [Discussion](https://github.com/markus-lassfolk/home-assistant-yarbo/discussions) or check existing issues.
