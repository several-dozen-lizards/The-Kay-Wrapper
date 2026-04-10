import ast
with open('Kay/engines/visual_sensor.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('visual_sensor.py: OK')
