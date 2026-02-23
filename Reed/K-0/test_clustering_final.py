"""
Final Document Clustering Test - End-to-End Verification

Creates a fresh import to test the complete clustering pipeline.
"""

import os
import shutil
from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
from agent_state import AgentState
from integrations.llm_integration import build_prompt_from_context

print("="*70)
print(" FINAL CLUSTERING TEST - Clean Import")
print("="*70)

# Backup existing memory
if os.path.exists("memory/memory_layers.json"):
    shutil.copy("memory/memory_layers.json", "memory/memory_layers_backup2.json")
    print("[BACKUP] Backed up existing memory")

# Create clean memory system
import json
with open("memory/memory_layers.json", 'w', encoding='utf-8') as f:
    json.dump({"working": [], "episodic": [], "semantic": []}, f)

print("[SETUP] Created clean memory system\n")

# Initialize
memory = MemoryEngine()
agent_state = AgentState()
importer = EmotionalMemoryImporter()

# Import pigeon story
print("Importing test_story.txt...")
result = importer.import_to_memory_engine('test_story.txt', memory)
print(f"  Total chunks: {result['total_chunks']}\n")

# Test retrieval
print("Querying: 'Tell me about the three pigeons in Central Park'")
memories = memory.recall(agent_state, "Tell me about the three pigeons in Central Park", num_memories=50)

# Check clustering
clustered = [m for m in memories if m.get('_cluster_doc_id')]
print(f"\nClustering results:")
print(f"  Total memories: {len(memories)}")
print(f"  Clustered memories: {len(clustered)}")

if clustered:
    print(f"  Cluster source: {clustered[0].get('_cluster_source')}")
    print(f"  Cluster size: {clustered[0].get('_cluster_size')}")

# Build context
context = {
    "user_input": "Tell me about the three pigeons",
    "recalled_memories": memories,
    "recalled_grouped": agent_state.last_recalled_grouped,
    "emotional_state": {"cocktail": agent_state.emotional_cocktail},
    "consolidated_preferences": {},
    "preference_contradictions": []
}

prompt = build_prompt_from_context(context, affect_level=3.5)

# Check for document headers
has_headers = "[From document:" in prompt
print(f"\nContext injection:")
print(f"  '[From document:' headers present: {has_headers}")

if has_headers:
    # Count and show headers
    count = prompt.count("[From document:")
    print(f"  Document clusters in context: {count}")

    # Extract sample
    lines = prompt.split('\n')
    for i, line in enumerate(lines):
        if "[From document:" in line:
            print(f"\n  Sample cluster:")
            for j in range(i, min(i+5, len(lines))):
                print(f"    {lines[j][:70]}")
            break

# Final verdict
print("\n" + "="*70)
print(" RESULTS")
print("="*70)

checks = [
    ("Chunks imported", result['total_chunks'] >= 3),
    ("Clustering triggered", len(clustered) > 0),
    ("Cluster metadata present", any(m.get('_cluster_size') for m in clustered)),
    ("Context shows headers", has_headers)
]

passed = sum(1 for _, result in checks if result)
print(f"\nChecks:")
for name, result in checks:
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {name}")

print(f"\nResult: {passed}/{len(checks)} checks passed")

if passed == len(checks):
    print("\n*** DOCUMENT CLUSTERING IS FULLY WORKING! ***")
    print("\nKay can now:")
    print("  - Retrieve complete documents when multiple chunks score highly")
    print("  - See explicit '[From document: ...]' headers showing relationships")
    print("  - Understand that memories are connected parts of the same source")
else:
    print(f"\n{len(checks) - passed} check(s) failed")

# Restore backup
if os.path.exists("memory/memory_layers_backup2.json"):
    shutil.copy("memory/memory_layers_backup2.json", "memory/memory_layers.json")
    os.remove("memory/memory_layers_backup2.json")
    print("\n[CLEANUP] Restored original memory")
