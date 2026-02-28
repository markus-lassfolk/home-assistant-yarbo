with open("custom_components/yarbo/switch.py", "r") as f:
    text = f.read()

text = text.replace(
    'super().__init__(coordinator, "camera", "camera_toggle", payload_key="enabled", on_value=True, off_value=False)',
    'super().__init__(\n            coordinator,\n            "camera",\n            "camera_toggle",\n            payload_key="enabled",\n            on_value=True,\n            off_value=False,\n        )'
)
text = text.replace(
    'super().__init__(coordinator, "laser", "laser_toggle", payload_key="enabled", on_value=True, off_value=False)',
    'super().__init__(\n            coordinator,\n            "laser",\n            "laser_toggle",\n            payload_key="enabled",\n            on_value=True,\n            off_value=False,\n        )'
)
text = text.replace(
    'super().__init__(coordinator, "usb", "usb_toggle", payload_key="enabled", on_value=True, off_value=False)',
    'super().__init__(\n            coordinator,\n            "usb",\n            "usb_toggle",\n            payload_key="enabled",\n            on_value=True,\n            off_value=False,\n        )'
)

with open("custom_components/yarbo/switch.py", "w") as f:
    f.write(text)

with open("custom_components/yarbo/coordinator.py", "r") as f:
    text = f.read()
text = text.replace('  # noqa: E501', '')
with open("custom_components/yarbo/coordinator.py", "w") as f:
    f.write(text)

