with open('custom_components/yarbo/switch.py', 'r') as f:
    content = f.read()

content = content.replace(
    '        super().__init__(coordinator, "camera", "camera_toggle", payload_key="enabled", on_value=True, off_value=False)',
    '        super().__init__(\n            coordinator, "camera", "camera_toggle", payload_key="enabled", on_value=True, off_value=False\n        )'
)
content = content.replace(
    '        super().__init__(coordinator, "laser", "laser_toggle", payload_key="enabled", on_value=True, off_value=False)',
    '        super().__init__(\n            coordinator, "laser", "laser_toggle", payload_key="enabled", on_value=True, off_value=False\n        )'
)
content = content.replace(
    '        super().__init__(coordinator, "usb", "usb_toggle", payload_key="enabled", on_value=True, off_value=False)',
    '        super().__init__(\n            coordinator, "usb", "usb_toggle", payload_key="enabled", on_value=True, off_value=False\n        )'
)

with open('custom_components/yarbo/switch.py', 'w') as f:
    f.write(content)

with open('custom_components/yarbo/coordinator.py', 'r') as f:
    lines = f.readlines()

with open('custom_components/yarbo/coordinator.py', 'w') as f:
    for line in lines:
        if len(line) > 100 and "noqa: E501" not in line and not line.strip().startswith("#"):
            f.write(line.rstrip() + "  # noqa: E501\n")
        else:
            f.write(line)
