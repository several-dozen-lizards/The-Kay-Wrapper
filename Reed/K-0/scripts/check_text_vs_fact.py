import json

with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])

# Find memories with doc_id
imported_memories = [m for m in all_memories if m.get('doc_id')]

print(f"Found {len(imported_memories)} imported memories\n")

for i, mem in enumerate(imported_memories[:3]):
    print(f"Memory {i+1}:")
    print(f"  doc_id: {mem.get('doc_id')}")
    print(f"  chunk_index: {mem.get('chunk_index')}")
    print(f"  Has 'text' field: {'text' in mem}")
    print(f"  Has 'fact' field: {'fact' in mem}")
    print(f"  Has 'user_input' field: {'user_input' in mem}")

    if 'text' in mem:
        print(f"  text value: {mem['text'][:80]}...")
    if 'fact' in mem:
        print(f"  fact value: {mem['fact'][:80]}...")
    if 'user_input' in mem:
        print(f"  user_input value: {mem['user_input'][:80]}...")

    print()
