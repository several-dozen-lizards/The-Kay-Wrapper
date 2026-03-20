import sys
sys.path.insert(0, "D:\\Wrappers\\AlphaKayZero")

from engines.memory_engine import MemoryEngine

m = MemoryEngine()

print("Working memory timestamps:")
for x in m.memory_layers.working_memory[:5]:
    ts = x.get('timestamp')
    print(f"  Type: {type(ts).__name__}, Value: {ts}")

print("\nLong-term memory timestamps:")
for x in m.memory_layers.long_term_memory[:5]:
    ts = x.get('timestamp')
    print(f"  Type: {type(ts).__name__}, Value: {ts}")
