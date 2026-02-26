# GitHub Copilot Configuration

## Review Scope
Copilot is configured for **code review only** on this repository.
No automated branch creation or PR generation.

## Context
This is a Home Assistant HACS custom integration for Yarbo robot mowers.
Key patterns:
- Async/await throughout (HA convention)
- Type annotations on all functions
- DataUpdateCoordinator pattern (push-based, no polling interval)
- Entity unique IDs: `{robot_sn}_{entity_key}`
- Never import paho-mqtt directly — use python-yarbo library
