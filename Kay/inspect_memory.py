import json, os
os.chdir('D:\\Wrappers\\Kay')
from engines.memory_layers import MemoryLayerManager
ml = MemoryLayerManager()
print(f"Working: {len(ml.working_memory)}")
print(f"Long-term: {len(ml.long_term_memory)}")
if ml.working_memory:
    m = ml.working_memory[0]
    print(f"\nWorking[0] keys: {list(m.keys())}")
    print(f"  emotion_tag: {m.get('emotion_tag', 'NONE')}")
    print(f"  importance: {m.get('importance', 'NONE')}")
if ml.long_term_memory:
    m = ml.long_term_memory[0]
    print(f"\nLong-term[0] keys: {list(m.keys())}")
    print(f"  emotion_tag: {m.get('emotion_tag', 'NONE')}")
    print(f"  importance: {m.get('importance', 'NONE')}")

all_mems = ml.working_memory + ml.long_term_memory
tags = [m.get('emotion_tag', '') for m in all_mems if m.get('emotion_tag')]
from collections import Counter
print(f"\nTop 15 emotion tags:")
for tag, count in Counter(tags).most_common(15):
    print(f"  {tag}: {count}")

# Check timestamp format
for m in all_mems[:3]:
    print(f"\nTimestamp: {m.get('timestamp', 'NONE')}")
    print(f"  Type: {type(m.get('timestamp', ''))}")
