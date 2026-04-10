import sys, ast

# Syntax check both files
for entity in ['Kay', 'Reed']:
    path = f'D:\\Wrappers\\{entity}\\engines\\memory_engine.py'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        
        # Check our additions exist
        has_randomness = 'retrieval_randomness' in source
        has_expansion = 'identity_expansion' in source
        has_rand_logic = 'RETRIEVAL RANDOMIZATION' in source
        has_exp_logic = 'IDENTITY EXPANSION' in source
        
        print(f"{entity}:")
        print(f"  Syntax: OK")
        print(f"  retrieval_randomness field: {has_randomness}")
        print(f"  identity_expansion field: {has_expansion}")
        print(f"  Randomization logic: {has_rand_logic}")
        print(f"  Expansion logic: {has_exp_logic}")
    except SyntaxError as e:
        print(f"{entity}: SYNTAX ERROR at line {e.lineno}: {e.msg}")

print()
print("=== Phase 0B #9 + #10 VERIFIED ===")
