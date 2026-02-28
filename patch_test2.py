with open('tests/test_services.py', 'r') as f:
    content = f.read()

content = content.replace(
    '    coordinator = MagicMock()',
    '    coordinator = MagicMock()\n    coordinator.client = client'
)

with open('tests/test_services.py', 'w') as f:
    f.write(content)
