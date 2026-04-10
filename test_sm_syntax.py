import ast, sys
sys.path.insert(0, '.')
with open('shared/somatic_markers.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('somatic_markers.py: OK')
