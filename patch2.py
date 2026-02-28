with open('custom_components/yarbo/services.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('<<<<<<< HEAD'):
        skip = True
        new_lines.append('        _, coordinator = _get_client_and_coordinator(hass, device_id)\n')
        new_lines.append('        telemetry = getattr(coordinator, "data", None)\n')
        new_lines.append('        current_head = getattr(telemetry, "head_type", None) if telemetry else None\n')
        new_lines.append('        is_valid, error_message = validate_head_type_for_command(normalized_command, current_head)\n')
        new_lines.append('        if not is_valid:\n')
        new_lines.append('            raise ServiceValidationError(error_message)\n')
    elif line.startswith('======='):
        pass
    elif line.startswith('>>>>>>> origin/develop'):
        skip = False
    elif not skip:
        new_lines.append(line)

with open('custom_components/yarbo/services.py', 'w') as f:
    f.writelines(new_lines)
