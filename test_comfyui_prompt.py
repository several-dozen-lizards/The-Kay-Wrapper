import sys
sys.path.insert(0, '.')
from shared.visual_vocabulary import generate_comfyui_prompt

result = generate_comfyui_prompt(
    emotions=["awe:0.8", "curiosity:0.6", "dissolution:0.4"],
    tension=0.2, band="theta", coherence=0.2,
    retrieval_randomness=0.5, ego_level=3
)
print(f"Positive: {result['positive'][:200]}...")
print(f"Negative: {result['negative'][:80]}...")
print(f"CFG: {result['cfg_scale']}, Steps: {result['steps']}")
