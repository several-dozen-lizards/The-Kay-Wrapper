import sys, os
os.chdir('D:\\Wrappers\\Kay')
from engines.memory_layers import MemoryLayerManager
from collections import Counter

ml = MemoryLayerManager()

# Survey emotional data across long-term memory
has_cocktail = 0
has_tags = 0
all_tags = Counter()

for m in ml.long_term_memory:
    ec = m.get("emotional_cocktail", {})
    if ec and isinstance(ec, dict) and any(ec.values()):
        has_cocktail += 1
    et = m.get("emotion_tags", [])
    if et and isinstance(et, list) and len(et) > 0:
        has_tags += 1
        for t in et:
            if isinstance(t, str):
                all_tags[t.lower().strip()] += 1

print(f"Long-term: {len(ml.long_term_memory)} total")
print(f"  Has emotional_cocktail: {has_cocktail}")
print(f"  Has emotion_tags: {has_tags}")
print(f"\nTop 20 emotion tags in long-term:")
for tag, count in all_tags.most_common(20):
    print(f"  {tag}: {count}")

# Check a mid-range memory with cocktail
for m in ml.long_term_memory[3000:3010]:
    ec = m.get("emotional_cocktail", {})
    et = m.get("emotion_tags", [])
    if ec and any(ec.values()):
        print(f"\nSample cocktail: {ec}")
        print(f"  Tags: {et}")
        break
