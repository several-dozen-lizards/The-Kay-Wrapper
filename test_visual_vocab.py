import ast
with open('shared/visual_vocabulary.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('visual_vocabulary.py: OK')

# Quick functional test
import sys
sys.path.insert(0, '.')
from shared.visual_vocabulary import palette_from_state, shapes_from_state, composition_complexity

p = palette_from_state(["curiosity:0.7", "warmth:0.4"], tension=0.1, band="theta")
print(f"Palette: {p.name} ({p.mood[:40]})")

s = shapes_from_state(["curiosity:0.7", "frustration:0.3", "warmth:0.4"], tension=0.4, band="theta", coherence=0.25, retrieval_randomness=0.3)
print(f"Shapes: {s}")

c = composition_complexity(coherence=0.25, retrieval_randomness=0.3, identity_expansion=0.5)
print(f"Composition: {c}")
