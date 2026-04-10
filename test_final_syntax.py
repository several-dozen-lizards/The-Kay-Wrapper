import ast
for f in ['nexus/server.py', 'resonant_core/psychedelic_state.py']:
    with open(f'D:\\Wrappers\\{f}', encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f"{f.split('/')[-1]}: OK")
