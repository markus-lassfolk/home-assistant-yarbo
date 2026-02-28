import re

with open('tests/test_services.py', 'r') as f:
    content = f.read()

# Replace synchronous lambdas with async ones
content = content.replace(
    'client.get_controller.side_effect = lambda **_kw: call_order.append("get_controller")',
    'async def _get_controller(**_kw): call_order.append("get_controller")\n        client.get_controller.side_effect = _get_controller'
)
content = content.replace(
    'client.publish_command.side_effect = lambda *_a, **_kw: call_order.append("publish_command")',
    'async def _publish(*_a, **_kw): call_order.append("publish_command")\n        client.publish_command.side_effect = _publish'
)

with open('tests/test_services.py', 'w') as f:
    f.write(content)
