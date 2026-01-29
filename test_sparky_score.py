"""Debug why Sparky isn't being retrieved despite having correct fields"""
from engines.memory_engine import MemoryEngine
from agent_state import AgentState
import json

memory = MemoryEngine()
agent_state = AgentState()

# Get Sparky memory
with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])
sparky = [m for m in all_memories if 'Sparky' in m.get('fact', '')][0]

print("Sparky memory details:")
print(f"  fact: {sparky.get('fact')}")
print(f"  turn_index: {sparky.get('turn_index')}")
print(f"  is_imported: {sparky.get('is_imported')}")
print(f"  current_turn: {memory.current_turn}")
print(f"  turns_since_import: {memory.current_turn - sparky.get('turn_index', 0)}")

# Calculate what the boost should be
turns_since = memory.current_turn - sparky.get('turn_index', 0)
print(f"\nExpected import_boost:")
if turns_since <= 1:
    print(f"  turns_since={turns_since} -> boost=8.0x")
elif turns_since <= 5:
    print(f"  turns_since={turns_since} -> boost=3.0x")
else:
    print(f"  turns_since={turns_since} -> boost=1.0x (no boost)")

# Check if it would be categorized as recent import
if sparky.get('is_imported', False) and turns_since <= 5:
    print(f"\n[OK] Should be categorized as 'recent_import' (dedicated 20 slots)")
else:
    print(f"\n[FAIL] Would NOT be categorized as recent_import!")
    print(f"  is_imported: {sparky.get('is_imported')}")
    print(f"  turns_since <= 5: {turns_since <= 5}")

# Do actual retrieval and check if Sparky appears
print("\n" + "="*60)
print("Doing retrieval...")
print("="*60)

retrieved = memory.retrieve_multi_factor(
    agent_state.emotional_cocktail,
    "Tell me about Sparky the dog",
    num_memories=100  # Request 100 to see where Sparky ranks
)

print(f"\nRetrieved {len(retrieved)} memories total")

# Find Sparky
for i, mem in enumerate(retrieved):
    if 'Sparky' in mem.get('fact', ''):
        print(f"\n[SUCCESS] Found Sparky at position {i}!")
        print(f"  retrieval_score: {mem.get('retrieval_score', 'N/A')}")
        break
else:
    print(f"\n[FAIL] Sparky NOT in top {len(retrieved)} memories")
    print(f"\nThis means Sparky's score was too low even with import boost")
    print(f"\nPossible causes:")
    print(f"  1. turn_index not set correctly (it's {sparky.get('turn_index')})")
    print(f"  2. is_imported not set correctly (it's {sparky.get('is_imported')})")
    print(f"  3. No keyword overlap with query")
    print(f"  4. Too many other high-scoring memories")
