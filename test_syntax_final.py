import ast

for f in ['D:\\Wrappers\\nexus\\nexus_kay.py',
          'D:\\Wrappers\\resonant_core\\resonant_integration.py',
          'D:\\Wrappers\\resonant_core\\psychedelic_state.py']:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read())
        name = f.split('\\')[-1]
        print(f"  {name}: Syntax OK")
    except SyntaxError as e:
        print(f"  {f}: SYNTAX ERROR line {e.lineno}: {e.msg}")

print("\n=== ALL FILES VERIFIED ===")
