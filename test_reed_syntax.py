import ast, sys
sys.path.insert(0, '.')
with open('nexus/nexus_reed.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('nexus_reed.py: OK')
