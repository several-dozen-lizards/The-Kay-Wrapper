import ast, sys
sys.path.insert(0, '.')
with open('Kay/engines/llm_retrieval.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('llm_retrieval.py: OK')
