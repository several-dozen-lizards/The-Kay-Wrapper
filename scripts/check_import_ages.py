"""Check ages of all imported memories"""
import json

with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])

# Find all imported memories
imported = [m for m in all_memories if m.get('is_imported', False)]

print(f"Total memories: {len(all_memories)}")
print(f"Imported memories: {len(imported)}")

if imported:
    # Check turn_index distribution
    turn_indices = {}
    for mem in imported:
        turn_idx = mem.get('turn_index', 'missing')
        turn_indices[turn_idx] = turn_indices.get(turn_idx, 0) + 1

    print(f"\nturn_index distribution for imported memories:")
    for turn_idx in sorted(turn_indices.keys(), key=lambda x: x if isinstance(x, int) else 99999):
        count = turn_indices[turn_idx]
        print(f"  turn_index={turn_idx}: {count} memories")

    # Check if most are turn_index=0
    zero_turn = len([m for m in imported if m.get('turn_index') == 0])
    missing_turn = len([m for m in imported if 'turn_index' not in m])

    print(f"\nDiagnostics:")
    print(f"  Imported with turn_index=0: {zero_turn}")
    print(f"  Imported missing turn_index: {missing_turn}")
    print(f"  Imported with turn_index > 0: {len(imported) - zero_turn - missing_turn}")

    # Sample some imported memories
    print(f"\nSample imported memories:")
    for i, mem in enumerate(imported[:5]):
        print(f"  {i+1}. turn_index={mem.get('turn_index', 'N/A')}, fact={mem.get('fact', '')[:60]}...")
