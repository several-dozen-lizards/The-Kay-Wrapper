import sys, os
os.chdir('D:\\Wrappers\\Kay')
from engines.memory_layers import MemoryLayerManager
ml = MemoryLayerManager()

# Check newest long-term memories for emotional_cocktail
recent = ml.long_term_memory[-5:]
for i, m in enumerate(recent):
    ec = m.get("emotional_cocktail", {})
    et = m.get("emotion_tags", [])
    ts = m.get("timestamp", "?")
    fact = str(m.get("fact", m.get("user_input", "?")))[:60]
    print(f"\n--- LT[-{5-i}] ---")
    print(f"  Content: {fact}")
    print(f"  emotional_cocktail: {ec}")
    print(f"  emotion_tags: {et}")
    print(f"  timestamp: {ts}")

# Also check working memory
print("\n\n=== WORKING MEMORY ===")
for i, m in enumerate(ml.working_memory[:3]):
    et = m.get("emotion_tags", [])
    fact = str(m.get("fact", "?"))[:60]
    print(f"\n--- W[{i}] ---")
    print(f"  Content: {fact}")
    print(f"  emotion_tags: {et}")
    print(f"  Keys: {list(m.keys())}")
