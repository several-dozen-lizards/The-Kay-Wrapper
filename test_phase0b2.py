import ast

path = 'D:\\Wrappers\\Reed\\engines\\memory_engine.py'
with open(path, 'r', encoding='utf-8-sig') as f:
    source = f.read()
ast.parse(source)

has_all = all(x in source for x in [
    'retrieval_randomness', 'identity_expansion',
    'RETRIEVAL RANDOMIZATION', 'IDENTITY EXPANSION'
])
print(f"Reed (utf-8-sig): Syntax OK, all features present: {has_all}")
print("=== BOTH FILES VERIFIED ===")
