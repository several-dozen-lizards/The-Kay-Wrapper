import ast, sys
sys.stdout.reconfigure(encoding='utf-8')
for f in ['shared/room/visual_presence.py', 'shared/room/attention_focus.py']:
    with open(f, encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f'{f}: OK')
