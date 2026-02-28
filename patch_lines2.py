with open('custom_components/yarbo/switch.py', 'r') as f:
    content = f.read()

content = content.replace('payload_key="enabled", on_value=True, off_value=False', 'payload_key="enabled",\\n            on_value=True,\\n            off_value=False')

with open('custom_components/yarbo/switch.py', 'w') as f:
    f.write(content)
