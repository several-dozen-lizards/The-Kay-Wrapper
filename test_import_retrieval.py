"""
Test Import-Retrieval Pipeline
Verifies that imported documents can be recalled by Kay
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory_import import ImportManager
from engines.memory_engine import MemoryEngine
from engines.entity_graph import EntityGraph
from agent_state import AgentState


async def test_import_retrieval():
    """
    Test complete pipeline:
    1. Import test document
    2. Search for imported facts
    3. Verify Kay can retrieve them
    """
    print("=" * 70)
    print("IMPORT-RETRIEVAL PIPELINE TEST")
    print("=" * 70)

    # === SETUP ===
    print("\n[SETUP] Initializing memory system...")
    state = AgentState()
    memory_engine = MemoryEngine()
    entity_graph = memory_engine.entity_graph
    state.memory = memory_engine

    initial_memory_count = len(memory_engine.memories)
    print(f"[SETUP] Initial memory count: {initial_memory_count}")

    # === STEP 1: IMPORT ===
    print("\n[STEP 1] Importing test document...")
    manager = ImportManager(
        memory_engine=memory_engine,
        entity_graph=entity_graph,
        chunk_size=3000,
        batch_size=1
    )

    try:
        progress = await manager.import_files(
            file_paths=["test_archive.txt"],
            dry_run=False  # Actually save to memory
        )

        print(f"\n[IMPORT RESULTS]")
        print(f"  Files processed: {progress.processed_files}")
        print(f"  Facts extracted: {progress.facts_extracted}")
        print(f"  Memories imported: {progress.memories_imported}")
        print(f"  Entities created: {progress.entities_created}")
        print(f"  Tier distribution: {progress.tier_distribution}")

        if progress.errors:
            print(f"\n[WARNINGS] Errors encountered:")
            for error in progress.errors[:3]:
                print(f"  - {error}")

    except Exception as e:
        print(f"\n[ERROR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # === STEP 2: VERIFY STORAGE ===
    print(f"\n[STEP 2] Verifying storage...")
    final_memory_count = len(memory_engine.memories)
    new_memories = final_memory_count - initial_memory_count

    print(f"  Initial memories: {initial_memory_count}")
    print(f"  Final memories: {final_memory_count}")
    print(f"  New memories added: {new_memories}")

    if new_memories == 0:
        print("\n[FAIL] No memories were added to self.memories[] array!")
        return

    # Show sample of imported memories
    print(f"\n[SAMPLE] Last 3 imported memories:")
    for i, mem in enumerate(memory_engine.memories[-3:]):
        fact = mem.get("fact", "")[:60]
        perspective = mem.get("perspective", "unknown")
        is_imported = mem.get("is_imported", False)
        print(f"  [{i}] ({perspective}) [imported={is_imported}] {fact}...")

    # === STEP 3: TEST RETRIEVAL ===
    print(f"\n[STEP 3] Testing retrieval...")

    test_queries = [
        "What are my dogs' names?",
        "Tell me about Chrome",
        "Tell me about Saga",
        "What does John do?",
        "What are my hobbies?",
    ]

    for query in test_queries:
        print(f"\n  Query: \"{query}\"")

        # Retrieve using Kay's normal recall function
        retrieved = memory_engine.recall(
            agent_state=state,
            user_input=query,
            num_memories=10
        )

        print(f"  Retrieved: {len(retrieved)} memories")

        # Check if any retrieved memories are from the import
        imported_found = [m for m in retrieved if m.get("is_imported", False)]

        if imported_found:
            print(f"  [SUCCESS] Found {len(imported_found)} imported memories!")
            for mem in imported_found[:2]:
                fact = mem.get("fact", "")[:50]
                print(f"    - {fact}...")
        else:
            print(f"  [FAIL] No imported memories retrieved (only live conversation)")

            # Debug: show what was retrieved
            print(f"  Retrieved memories were:")
            for mem in retrieved[:3]:
                fact = mem.get("fact", mem.get("user_input", ""))[:50]
                is_imported = mem.get("is_imported", False)
                print(f"    - [imported={is_imported}] {fact}...")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    if new_memories > 0:
        print(f"[PASS] Import: {new_memories} memories added to storage")
    else:
        print(f"[FAIL] Import: No memories added")

    # Check if retrieval found imported content
    test_retrieval = memory_engine.recall(state, "Chrome Saga dogs", num_memories=15)
    imported_in_retrieval = [m for m in test_retrieval if m.get("is_imported", False)]

    if imported_in_retrieval:
        print(f"[PASS] Retrieval: Imported memories are retrievable ({len(imported_in_retrieval)} found)")
    else:
        print(f"[FAIL] Retrieval: Imported memories NOT retrievable")

    print(f"\nConclusion:")
    if new_memories > 0 and imported_in_retrieval:
        print("  Pipeline is WORKING! Kay can recall imported documents.")
    elif new_memories > 0:
        print("  Memories imported but NOT retrievable (scoring/filtering issue)")
    else:
        print("  Pipeline is BROKEN! Memories not being stored.")


if __name__ == "__main__":
    asyncio.run(test_import_retrieval())
