with open('custom_components/yarbo/services.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('<<<<<<< HEAD'):
        skip = True
        new_lines.append('        _, coordinator = _get_client_and_coordinator(hass, device_id)\n')
        new_lines.append('        # Optional percent override; fall back to coordinator stored value\n')
        new_lines.append('        percent: int = call.data.get("percent", coordinator.plan_start_percent)\n')
    elif line.startswith('======='):
        pass
    elif line.startswith('>>>>>>> origin/develop'):
        skip = False
    elif not skip:
        new_lines.append(line)

with open('custom_components/yarbo/services.py', 'w') as f:
    f.writelines(new_lines)
