import ast
with open('Kay/wrapper_bridge.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('wrapper_bridge.py: OK')
