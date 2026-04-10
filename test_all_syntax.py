import ast

files = [
    ('resonant_core/psychedelic_state.py', 'utf-8'),
    ('resonant_core/memory_interoception.py', 'utf-8'),
    ('nexus/nexus_kay.py', 'utf-8'),
    ('shared/salience_accumulator.py', 'utf-8'),
    ('shared/cross_modal_router.py', 'utf-8'),
]

for f, enc in files:
    path = f'D:\\Wrappers\\{f}'
    try:
        with open(path, encoding=enc) as fh:
            ast.parse(fh.read())
        print(f"{f.split('/')[-1]}: OK")
    except SyntaxError as e:
        print(f"{f.split('/')[-1]}: SYNTAX ERROR line {e.lineno}: {e.msg}")
