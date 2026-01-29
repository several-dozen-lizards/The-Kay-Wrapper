"""Test with minimal memory system - just one import to verify branch tracking works"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os
import shutil
from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
from agent_state import AgentState

print("="*70)
print(" CLEAN IMPORT TEST - Minimal Memory System")
print("="*70)

# Backup existing memories
if os.path.exists("memory/memory_layers.json"):
    shutil.copy("memory/memory_layers.json", "memory/memory_layers_backup.json")
    print("[BACKUP] Backed up existing memory_layers.json")

# Create minimal memory system (only identity facts)
minimal_memory = {
    "working": [],
    "episodic": [],
    "semantic": []
}

# Save minimal memory
with open("memory/memory_layers.json", 'w', encoding='utf-8') as f:
    json.dump(minimal_memory, f, indent=2)

print("[SETUP] Created minimal memory system (no imported memories)\n")

# Initialize clean memory engine
memory = MemoryEngine()
agent_state = AgentState()

print(f"Memory stats before import:")
print(f"  Working: {len(memory.memory_layers.working_memory)}")
print(f"  Episodic: {len(memory.memory_layers.episodic_memory)}")
print(f"  Semantic: {len(memory.memory_layers.semantic_memory)}")
print(f"  Current turn: {memory.current_turn}\n")

# Create test file
test_content = "Rusty is a red fox who lives in the forest. Rusty loves to hunt mice at dawn."
with open("test_rusty.txt", 'w', encoding='utf-8') as f:
    f.write(test_content)

# Import
print("Importing test_rusty.txt...")
importer = EmotionalMemoryImporter()
result = importer.import_to_memory_engine('test_rusty.txt', memory)

print(f"\nImport complete:")
print(f"  Chunks imported: {result['total_chunks']}")
print(f"  Current turn after import: {memory.current_turn}\n")

# Verify storage
with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])
rusty_memories = [m for m in all_memories if 'Rusty' in m.get('fact', '')]

print(f"Rusty memories in storage: {len(rusty_memories)}")
if rusty_memories:
    mem = rusty_memories[0]
    print(f"  fact: {mem.get('fact')}")
    print(f"  turn_index: {mem.get('turn_index')}")
    print(f"  is_imported: {mem.get('is_imported')}")
    print(f"  doc_id: {mem.get('doc_id')}")
    print(f"  chunk_index: {mem.get('chunk_index')}\n")

# Test retrieval
print("Testing retrieval: 'Tell me about Rusty'...")
print("(Should see [MEMORY FOREST] logs if branch tracking works)\n")

retrieved = memory.recall(agent_state, "Tell me about Rusty the fox", num_memories=50)

# Check if Rusty was retrieved
rusty_retrieved = [m for m in retrieved if 'Rusty' in m.get('fact', '')]

if rusty_retrieved:
    print(f"[SUCCESS] Rusty WAS retrieved!")
    mem = rusty_retrieved[0]
    print(f"  Position in results: {retrieved.index(mem)}")
    print(f"  doc_id: {mem.get('doc_id')}")
    print(f"  chunk_index: {mem.get('chunk_index')}\n")

    # Check tree
    doc_id = mem.get('doc_id')
    tree_path = f"data/trees/tree_{doc_id}.json"

    if os.path.exists(tree_path):
        with open(tree_path, 'r', encoding='utf-8') as f:
            tree_data = json.load(f)

        tree_access = tree_data.get('access_count', 0)
        if tree_access > 0:
            print(f"[COMPLETE SUCCESS] Branch tracking is WORKING!")
            print(f"  Tree access_count: {tree_access}")
            print(f"  Branch access_count: {tree_data.get('branches', [{}])[0].get('access_count', 0)}")
            print(f"\n*** PHASE 2A IS COMPLETE! ***")
        else:
            print(f"[PARTIAL] Rusty retrieved but tree access_count=0")
            print(f"  This means branch tracking code didn't execute")
    else:
        print(f"[ERROR] Tree file not found: {tree_path}")
else:
    print(f"[FAIL] Rusty NOT retrieved")
    print(f"  Total retrieved: {len(retrieved)}")
    print(f"  This shouldn't happen with a clean memory system!")

# Restore backup
if os.path.exists("memory/memory_layers_backup.json"):
    shutil.copy("memory/memory_layers_backup.json", "memory/memory_layers.json")
    os.remove("memory/memory_layers_backup.json")
    print(f"\n[CLEANUP] Restored original memory_layers.json")

# Clean up test file
if os.path.exists("test_rusty.txt"):
    os.remove("test_rusty.txt")
    print(f"[CLEANUP] Removed test_rusty.txt")

print("\n" + "="*70)
print(" TEST COMPLETE")
print("="*70)
