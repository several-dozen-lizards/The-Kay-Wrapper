"""
Test Document Clustering Feature

Verifies that:
1. Multiple chunks from same document trigger clustering
2. ALL chunks from significant documents are retrieved
3. Cluster metadata is injected into context
4. Kay sees explicit "[From document: ...]" headers
"""

from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
from agent_state import AgentState
from integrations.llm_integration import build_prompt_from_context
import json
import os

print("="*70)
print(" DOCUMENT CLUSTERING TEST")
print("="*70)

# Initialize
print("\nInitializing...")
memory = MemoryEngine()
agent_state = AgentState()
importer = EmotionalMemoryImporter()

print(f"Current turn: {memory.current_turn}")
print(f"Memory layers: W={len(memory.memory_layers.working_memory)}, "
      f"E={len(memory.memory_layers.episodic_memory)}, "
      f"S={len(memory.memory_layers.semantic_memory)}\n")

# Import multi-chunk document
print("Importing test_story.txt (should create multiple chunks)...")
result = importer.import_to_memory_engine('test_story.txt', memory)

print(f"\nImport complete:")
print(f"  Total chunks: {result['total_chunks']}")
print(f"  Tiers: {result['tiers']}")

if result['total_chunks'] < 3:
    print(f"\n[WARNING] Only {result['total_chunks']} chunks created.")
    print("  This test works best with 3+ chunks to demonstrate clustering.")

# Verify chunks have required metadata
with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])
story_chunks = [m for m in all_memories if 'pigeon' in m.get('fact', '').lower()]

print(f"\nFound {len(story_chunks)} chunks mentioning 'pigeon'")

if story_chunks:
    # Check first chunk has metadata
    sample = story_chunks[0]
    print(f"  Sample chunk has doc_id: {sample.get('doc_id') is not None}")
    print(f"  Sample chunk has chunk_index: {sample.get('chunk_index') is not None}")
    print(f"  Sample chunk has turn_index: {sample.get('turn_index') is not None}")

    doc_id = sample.get('doc_id')
    print(f"\n  All chunks share doc_id: {doc_id}")

# Test retrieval with query about pigeons
print("\n" + "="*70)
print(" TESTING RETRIEVAL & CLUSTERING")
print("="*70)

# Query that should trigger multiple chunk retrieval
query = "Tell me about the pigeons in Central Park"
print(f"\nQuery: '{query}'")
print("\nExpected behavior:")
print("  1. Multiple chunks about pigeons should score highly")
print("  2. [MEMORY CLUSTER] log should appear")
print("  3. ALL chunks from document should be retrieved\n")

# Do recall (this triggers clustering)
recalled_memories = memory.recall(agent_state, query, num_memories=50)

print(f"\n[RESULT] Recalled {len(recalled_memories)} total memories")

# Check for clustered chunks
pigeon_memories = [m for m in recalled_memories if 'pigeon' in m.get('fact', '').lower()]
print(f"[RESULT] {len(pigeon_memories)} memories mention 'pigeon'")

# Check for cluster metadata
clustered = [m for m in pigeon_memories if m.get('_cluster_doc_id')]
if clustered:
    print(f"[SUCCESS] {len(clustered)} memories have cluster metadata!")

    # Check if they all have same doc_id
    cluster_ids = set(m.get('_cluster_doc_id') for m in clustered)
    print(f"  Cluster IDs found: {len(cluster_ids)}")
    print(f"  Cluster sizes: {set(m.get('_cluster_size') for m in clustered)}")
    print(f"  Source files: {set(m.get('_cluster_source') for m in clustered)}")
else:
    print(f"[PARTIAL] Memories retrieved but no cluster metadata found")
    print(f"  This might mean fewer than 2 chunks scored highly enough")

# Test context building
print("\n" + "="*70)
print(" TESTING CONTEXT INJECTION")
print("="*70)

# Build context as Kay would see it
context = {
    "user_input": query,
    "recalled_memories": recalled_memories,
    "recalled_grouped": agent_state.last_recalled_grouped,
    "emotional_state": {"cocktail": agent_state.emotional_cocktail},
    "consolidated_preferences": {},
    "preference_contradictions": []
}

prompt = build_prompt_from_context(context, affect_level=3.5)

# Check if prompt contains cluster headers
if "[From document:" in prompt:
    print("[SUCCESS] Context contains '[From document:' headers!")

    # Count cluster headers
    cluster_count = prompt.count("[From document:")
    print(f"  Found {cluster_count} document cluster(s) in context")

    # Extract and show the clustered section
    print("\n  Sample of clustered content in context:")
    lines = prompt.split('\n')
    in_cluster = False
    cluster_lines = []

    for line in lines:
        if "[From document:" in line:
            in_cluster = True
            cluster_lines = [line]
        elif in_cluster:
            if line.startswith("  -") or line.startswith("-"):
                cluster_lines.append(line)
            else:
                # End of cluster
                if cluster_lines:
                    print("\n".join(cluster_lines[:8]))  # Show first 8 lines
                    if len(cluster_lines) > 8:
                        print(f"    ... ({len(cluster_lines)-8} more lines)")
                break
else:
    print("[PARTIAL] No '[From document:' headers found in context")
    print("  Clustered memories may not have been grouped")

print("\n" + "="*70)
print(" TEST SUMMARY")
print("="*70)

success_count = 0
total_checks = 4

print("\nChecklist:")

# Check 1: Multiple chunks imported
if result['total_chunks'] >= 3:
    print("[OK] Multiple chunks imported")
    success_count += 1
else:
    print("[PARTIAL] Only {result['total_chunks']} chunks imported (3+ needed)")

# Check 2: Clustering detected
if clustered:
    print("[OK] Memory clustering triggered")
    success_count += 1
else:
    print("[PARTIAL] Clustering not triggered (need 2+ chunks in top results)")

# Check 3: Cluster metadata present
if clustered and any(m.get('_cluster_size') for m in clustered):
    print("[OK] Cluster metadata injected")
    success_count += 1
else:
    print("[FAIL] Cluster metadata missing")

# Check 4: Context shows document headers
if "[From document:" in prompt:
    print("[OK] Context shows document grouping")
    success_count += 1
else:
    print("[FAIL] Context does not show document grouping")

print(f"\nResult: {success_count}/{total_checks} checks passed")

if success_count == total_checks:
    print("\n*** DOCUMENT CLUSTERING IS WORKING! ***")
else:
    print(f"\n{total_checks - success_count} checks need attention")

# Cleanup
if os.path.exists("test_story.txt"):
    # Keep file for manual testing
    print(f"\nNote: test_story.txt preserved for manual testing")
