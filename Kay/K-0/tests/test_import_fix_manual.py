"""
Manual Test of Import Fix
Creates imported memories manually (bypassing LLM extraction) to verify retrieval works
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.memory_engine import MemoryEngine
from agent_state import AgentState
from datetime import datetime


def test_import_fix():
    """
    Test that manually adding memories to both arrays allows retrieval.
    This bypasses the LLM extraction to test just the storage/retrieval fix.
    """
    print("=" * 70)
    print("MANUAL IMPORT FIX TEST")
    print("=" * 70)

    # === SETUP ===
    print("\n[SETUP] Initializing memory system...")
    state = AgentState()
    memory_engine = MemoryEngine()
    state.memory = memory_engine

    initial_count = len(memory_engine.memories)
    print(f"[SETUP] Initial memory count: {initial_count}")

    # === CREATE TEST IMPORTED MEMORIES ===
    print("\n[TEST] Creating 5 test imported memories...")

    test_facts = [
        {
            "fact": "Chrome is Re's dog (gray husky)",
            "perspective": "user",
            "topic": "pets",
            "entities": ["Chrome", "Re"],
        },
        {
            "fact": "Saga is Re's dog (black labrador)",
            "perspective": "user",
            "topic": "pets",
            "entities": ["Saga", "Re"],
        },
        {
            "fact": "John is Re's spouse",
            "perspective": "user",
            "topic": "relationships",
            "entities": ["John", "Re"],
        },
        {
            "fact": "John teaches karate (black belt)",
            "perspective": "user",
            "topic": "occupation",
            "entities": ["John"],
        },
        {
            "fact": "Re enjoys painting and watercolors",
            "perspective": "user",
            "topic": "hobbies",
            "entities": ["Re"],
        },
    ]

    for i, fact_data in enumerate(test_facts):
        # Create memory in correct format
        memory = {
            # Core content
            "fact": fact_data["fact"],
            "user_input": fact_data["fact"],
            "response": "",

            # Classification
            "type": "extracted_fact",
            "perspective": fact_data["perspective"],
            "topic": fact_data["topic"],

            # Entities
            "entities": fact_data["entities"],
            "emotion_tags": [],

            # Scoring
            "importance": 0.8,
            "importance_score": 0.8,

            # Tier
            "tier": "semantic",
            "current_layer": "semantic",
            "current_strength": 1.0,

            # Turn tracking
            "turn_index": memory_engine.current_turn,
            "turn_number": memory_engine.current_turn,

            # Timestamps
            "added_timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),

            # Access tracking
            "access_count": 0,
            "last_accessed": None,

            # Import provenance
            "source_document": "manual_test",
            "chunk_index": i,
            "is_imported": True,
        }

        # CRITICAL FIX: Add to BOTH arrays
        memory_engine.memory_layers.add_memory(memory, layer="semantic")
        memory_engine.memories.append(memory)  # THIS IS THE FIX

        print(f"  [{i+1}] Added: {fact_data['fact']}")

    # Save
    memory_engine._save_to_disk()
    memory_engine.memory_layers._save_to_disk()

    final_count = len(memory_engine.memories)
    added = final_count - initial_count

    print(f"\n[STORAGE] Memories added: {added}")
    print(f"  Initial: {initial_count}")
    print(f"  Final: {final_count}")

    # === TEST RETRIEVAL ===
    print("\n[RETRIEVAL] Testing if imported memories can be found...")

    test_queries = [
        ("What are my dogs' names?", ["Chrome", "Saga"]),
        ("Tell me about Chrome", ["Chrome"]),
        ("What does John do?", ["John", "karate"]),
        ("What are my hobbies?", ["painting", "watercolors"]),
    ]

    passed = 0
    failed = 0

    for query, expected_keywords in test_queries:
        print(f"\n  Query: \"{query}\"")

        retrieved = memory_engine.recall(
            agent_state=state,
            user_input=query,
            num_memories=15
        )

        print(f"  Retrieved: {len(retrieved)} memories")

        # Check if imported memories were retrieved
        imported_retrieved = [m for m in retrieved if m.get("is_imported", False)]

        if imported_retrieved:
            print(f"  [PASS] Found {len(imported_retrieved)} imported memories!")

            # Verify keywords present
            all_text = " ".join([m.get("fact", "") for m in imported_retrieved])
            keywords_found = [kw for kw in expected_keywords if kw.lower() in all_text.lower()]

            print(f"    Expected keywords: {expected_keywords}")
            print(f"    Found: {keywords_found}")

            for mem in imported_retrieved[:2]:
                print(f"    - {mem.get('fact', '')}")

            if keywords_found:
                passed += 1
            else:
                print(f"  [WARN] Imported memories found but missing expected keywords")
                failed += 1
        else:
            print(f"  [FAIL] No imported memories retrieved")
            failed += 1

            # Debug: show what WAS retrieved
            if retrieved:
                print(f"  Retrieved (non-imported) memories:")
                for mem in retrieved[:2]:
                    fact = mem.get("fact", mem.get("user_input", ""))[:60]
                    is_imported = mem.get("is_imported", False)
                    print(f"    - [imported={is_imported}] {fact}...")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    print(f"\nStorage:")
    if added == len(test_facts):
        print(f"  [PASS] All {added} memories added to self.memories[] array")
    else:
        print(f"  [FAIL] Expected {len(test_facts)}, got {added}")

    print(f"\nRetrieval:")
    print(f"  Passed: {passed}/{len(test_queries)}")
    print(f"  Failed: {failed}/{len(test_queries)}")

    if passed == len(test_queries):
        print("\n[SUCCESS] Import fix is WORKING!")
        print("Imported memories are being stored AND retrieved correctly.")
    elif passed > 0:
        print("\n[PARTIAL] Import fix is partially working")
        print(f"{passed} queries succeeded, {failed} failed")
    else:
        print("\n[FAILURE] Import fix is NOT working")
        print("Imported memories are not being retrieved")

    # Cleanup recommendation
    print("\n[CLEANUP] To remove test data:")
    print(f"  python -c \"import json; m=json.load(open('memory/memories.json')); ")
    print(f"  m=[x for x in m if not x.get('is_imported') or x.get('source_document')!='manual_test']; ")
    print(f"  json.dump(m, open('memory/memories.json', 'w'), indent=2)\"")


if __name__ == "__main__":
    test_import_fix()
