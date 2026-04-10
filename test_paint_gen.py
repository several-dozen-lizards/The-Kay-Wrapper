import ast, json, sys
sys.path.insert(0, '.')

with open('shared/visual_vocabulary.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('visual_vocabulary.py: OK')

from shared.visual_vocabulary import generate_paint_commands
cmds = generate_paint_commands(
    emotions=["curiosity:0.7", "warmth:0.4", "frustration:0.3"],
    tension=0.4, band="theta", coherence=0.25,
    retrieval_randomness=0.3, identity_expansion=0.5
)
print(f"Generated {len(cmds)} paint commands")
print(f"First: {cmds[0]}")
print(f"Shapes used: {set(c['action'] for c in cmds)}")
