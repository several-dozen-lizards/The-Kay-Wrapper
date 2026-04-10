import ast
for f in ['Kay/engines/memory_engine.py', 'Reed/engines/memory_engine.py']:
    enc = 'utf-8-sig' if 'Reed' in f else 'utf-8'
    with open(f'D:\\Wrappers\\{f}', encoding=enc) as fh:
        ast.parse(fh.read())
    print(f"{f.split('/')[-1]} ({f.split('/')[0]}): OK")
