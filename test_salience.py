import ast
for f in ['shared/salience_accumulator.py', 'nexus/nexus_kay.py']:
    with open(f'D:\\Wrappers\\{f}', encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f"{f.split('/')[-1]}: OK")
