"""Tests for the Yarbo automation blueprints (#15)."""

from __future__ import annotations

import os

import yaml


# HA blueprints use !input tags; register a safe constructor that returns a sentinel
class _HALoader(yaml.SafeLoader):
    pass


def _input_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    """Return the input name as a string when encountering !input tags."""
    return f"!input:{loader.construct_scalar(node)}"


_HALoader.add_constructor("!input", _input_constructor)


def _load_blueprint(path: str) -> dict:  # type: ignore[type-arg]
    """Load a HA blueprint YAML file, handling !input custom tags."""
    with open(path) as f:
        return yaml.load(f, Loader=_HALoader)


BLUEPRINTS_DIR = os.path.join(os.path.dirname(__file__), "..", "blueprints", "automation", "yarbo")


class TestLowBatteryBlueprint:
    """Tests for the low battery notification blueprint (issue #15)."""

    def test_file_exists(self) -> None:
        """Blueprint file must exist at the expected path."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        assert os.path.isfile(path), f"Blueprint not found: {path}"

    def test_valid_yaml(self) -> None:
        """Blueprint must be valid YAML."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)
        assert data is not None

    def test_blueprint_metadata(self) -> None:
        """Blueprint must have correct domain and metadata."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        bp = data["blueprint"]
        assert bp["domain"] == "automation"
        assert "name" in bp
        assert "description" in bp

    def test_required_inputs_present(self) -> None:
        """Blueprint must have battery_sensor, threshold, and notify_service inputs."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        inputs = data["blueprint"]["input"]
        assert "battery_sensor" in inputs, "Missing 'battery_sensor' input"
        assert "threshold" in inputs, "Missing 'threshold' input"
        assert "notify_service" in inputs, "Missing 'notify_service' input"

    def test_battery_sensor_uses_device_class(self) -> None:
        """battery_sensor selector must use device_class=battery."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        sensor_input = data["blueprint"]["input"]["battery_sensor"]
        selector = sensor_input.get("selector", {})
        assert "entity" in selector, "Must use entity selector"
        assert selector["entity"].get("device_class") == "battery"

    def test_threshold_default_is_20(self) -> None:
        """threshold input must default to 20%."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        threshold_input = data["blueprint"]["input"]["threshold"]
        assert threshold_input.get("default") == 20

    def test_trigger_is_numeric_state(self) -> None:
        """Trigger must use numeric_state platform."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        triggers = data.get("trigger", [])
        assert len(triggers) >= 1
        trigger = triggers[0]
        assert trigger["platform"] == "numeric_state"

    def test_has_action(self) -> None:
        """Blueprint must have an action block."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        assert "action" in data
        assert len(data["action"]) >= 1

    def test_mode_is_single(self) -> None:
        """Automation mode must be 'single' to avoid duplicate notifications."""
        path = os.path.join(BLUEPRINTS_DIR, "low_battery_notification.yaml")
        data = _load_blueprint(path)

        assert data.get("mode") == "single"
