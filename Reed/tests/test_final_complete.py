"""
PHASE 2A FINAL FIX VERIFICATION TEST

Tests both fixes:
1. "fact" field added (makes memories searchable)
2. "turn_index" field added (makes memories eligible for recent import boost)

Expected results:
- Sparky memory should be retrieved
- Branch tracking logs should appear
- Tree access_count should increment
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
from agent_state import AgentState
import json
import os

print("="*70)
print(" PHASE 2A FINAL FIX VERIFICATION TEST")
print("="*70)

# Initialize
print("\nInitializing memory engine...")
memory = MemoryEngine()
agent_state = AgentState()

initial_turn = memory.current_turn
print(f"Current turn before import: {initial_turn}")

# Import test file
print("\nImporting test_final_fix.txt...")
importer = EmotionalMemoryImporter()
result = importer.import_to_memory_engine('test_final_fix.txt', memory)

print(f"\nImport complete:")
print(f"  Total chunks: {result['total_chunks']}")
print(f"  Turn after import: {memory.current_turn}")

# Check stored memory has both fixes
print("\nVerifying stored memory has required fields...")
with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])
sparky_memories = [m for m in all_memories if 'Sparky' in m.get('fact', '')]

if sparky_memories:
    mem = sparky_memories[0]
    print(f"[OK] Found Sparky memory in storage")
    print(f"  Has 'fact' field: {'fact' in mem} {'[OK]' if 'fact' in mem else '[FAIL]'}")
    print(f"  Has 'turn_index' field: {'turn_index' in mem} {'[OK]' if 'turn_index' in mem else '[FAIL]'}")
    print(f"  Has 'doc_id' field: {'doc_id' in mem} {'[OK]' if 'doc_id' in mem else '[FAIL]'}")
    print(f"  Has 'chunk_index' field: {'chunk_index' in mem} {'[OK]' if 'chunk_index' in mem else '[FAIL]'}")
    print(f"  turn_index value: {mem.get('turn_index')}")
    print(f"  doc_id value: {mem.get('doc_id')}")
else:
    print("[FAIL] ERROR: Sparky memory not found in storage!")
    exit(1)

# Test retrieval
print("\nTesting retrieval: 'Tell me about Sparky'...")
print("(This should trigger branch tracking logs)")

memories = memory.recall(agent_state, "Tell me about Sparky the dog", num_memories=50)

# Check if Sparky was retrieved
sparky_retrieved = [m for m in memories if 'Sparky' in m.get('fact', '')]

if sparky_retrieved:
    print(f"\n[SUCCESS] Sparky memory WAS retrieved!")
    mem = sparky_retrieved[0]
    print(f"  Retrieved fact: {mem.get('fact')[:80]}...")
    print(f"  doc_id: {mem.get('doc_id')}")
    print(f"  chunk_index: {mem.get('chunk_index')}")
else:
    print(f"\n[WARNING] Sparky not in retrieved memories")
    print(f"  (But this might be OK if query relevance is low)")

# Check if branch tracking happened
print("\nVerifying branch tracking...")
doc_id = sparky_memories[0].get('doc_id')
tree_path = f"data/trees/tree_{doc_id}.json"

if os.path.exists(tree_path):
    with open(tree_path, 'r', encoding='utf-8') as f:
        tree_data = json.load(f)

    tree_access = tree_data.get('access_count', 0)
    branch_access = tree_data.get('branches', [{}])[0].get('access_count', 0)

    if sparky_retrieved and tree_access > 0:
        print(f"[COMPLETE SUCCESS] Branch tracking is working!")
        print(f"  Tree access_count: {tree_access}")
        print(f"  Branch access_count: {branch_access}")
        print(f"  Last accessed: {tree_data.get('branches', [{}])[0].get('last_accessed')}")
    elif sparky_retrieved and tree_access == 0:
        print(f"[PARTIAL] Memory retrieved but branch NOT tracked")
        print(f"  This means the branch tracking code didn't run")
    else:
        print(f"  Tree exists but memory not retrieved, so access_count=0 is expected")

    print(f"\nTree structure:")
    for branch in tree_data.get('branches', []):
        print(f"  - {branch.get('title')}: {len(branch.get('chunk_indices', []))} chunks")
else:
    print(f"[ERROR] Tree file not found: {tree_path}")

print("\n" + "="*70)
print(" TEST COMPLETE")
print("="*70)

# Summary
print("\nSUMMARY:")
print(f"  1. fact field present: {'[OK]' if 'fact' in sparky_memories[0] else '[FAIL]'}")
print(f"  2. turn_index present: {'[OK]' if 'turn_index' in sparky_memories[0] else '[FAIL]'}")
print(f"  3. doc_id/chunk_index present: {'[OK]' if 'doc_id' in sparky_memories[0] else '[FAIL]'}")
print(f"  4. Memory retrieved: {'[OK]' if sparky_retrieved else '[FAIL]'}")
if os.path.exists(tree_path):
    with open(tree_path, 'r', encoding='utf-8') as f:
        tree_data = json.load(f)
    tree_tracked = tree_data.get('access_count', 0) > 0
    print(f"  5. Branch tracking working: {'[OK]' if tree_tracked else '[FAIL]'}")
else:
    print(f"  5. Branch tracking working: [FAIL] (tree file missing)")

print("\nIf all 5 items show [OK], Phase 2A is COMPLETE!")
