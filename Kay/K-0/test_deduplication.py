"""
Test Enhanced Deduplication System
Verifies that duplicate imports are caught and prevented
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from memory_import.import_manager import ImportManager
from memory_import.memory_extractor import ExtractedMemory
from engines.memory_engine import MemoryEngine
from agent_state import AgentState


def test_deduplication():
    """
    Test that deduplication works against both:
    1. Duplicates within the import batch
    2. Duplicates already in the database
    """
    print("=" * 70)
    print("DEDUPLICATION TEST")
    print("=" * 70)

    # === SETUP ===
    print("\n[SETUP] Initializing memory system...")
    state = AgentState()
    memory_engine = MemoryEngine()
    entity_graph = memory_engine.entity_graph
    state.memory = memory_engine

    manager = ImportManager(
        memory_engine=memory_engine,
        entity_graph=entity_graph
    )

    # === TEST 1: Duplicates within batch ===
    print("\n[TEST 1] Duplicates within import batch...")

    test_facts = [
        ExtractedMemory(
            text="Chrome is a gray husky",
            importance=0.8,
            category="pets",
            entities=["Chrome"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="pets"
        ),
        ExtractedMemory(
            text="Chrome is a gray husky.",  # Same with punctuation
            importance=0.8,
            category="pets",
            entities=["Chrome"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="pets"
        ),
        ExtractedMemory(
            text="Chrome is the gray husky",  # Same with "the"
            importance=0.8,
            category="pets",
            entities=["Chrome"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="pets"
        ),
        ExtractedMemory(
            text="Saga is a black labrador",  # Different - should keep
            importance=0.8,
            category="pets",
            entities=["Saga"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="pets"
        ),
    ]

    unique = manager._deduplicate_facts(test_facts)

    print(f"  Input: {len(test_facts)} facts")
    print(f"  Output: {len(unique)} unique facts")
    print(f"  Expected: 2 (Chrome + Saga)")

    if len(unique) == 2:
        print("  [PASS] Within-batch deduplication works!")
    else:
        print(f"  [FAIL] Expected 2, got {len(unique)}")
        for fact in unique:
            print(f"    - {fact.text}")

    # === TEST 2: Duplicates against database ===
    print("\n[TEST 2] Duplicates against existing database...")

    # Add a fact to the database
    existing_memory = {
        "fact": "John teaches karate",
        "user_input": "John teaches karate",
        "type": "extracted_fact",
        "perspective": "user",
        "topic": "occupation",
        "entities": ["John"],
        "importance": 0.8,
        "tier": "semantic",
    }
    memory_engine.memories.append(existing_memory)

    print(f"  Added 1 existing memory to database: '{existing_memory['fact']}'")

    # Try to import same fact (with variations)
    test_facts_db = [
        ExtractedMemory(
            text="John teaches karate",  # Exact duplicate
            importance=0.8,
            category="occupation",
            entities=["John"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="occupation"
        ),
        ExtractedMemory(
            text="John teaches karate.",  # Duplicate with punctuation
            importance=0.8,
            category="occupation",
            entities=["John"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="occupation"
        ),
        ExtractedMemory(
            text="John is a karate teacher",  # Different - should keep
            importance=0.8,
            category="occupation",
            entities=["John"],
            date=None,
            tier="semantic",
            perspective="user",
            topic="occupation"
        ),
    ]

    unique_db = manager._deduplicate_facts(test_facts_db)

    print(f"  Input: {len(test_facts_db)} facts")
    print(f"  Output: {len(unique_db)} unique facts")
    print(f"  Expected: 1 (only the 'karate teacher' variant)")

    if len(unique_db) == 1:
        print("  [PASS] Database deduplication works!")
        print(f"    Kept: '{unique_db[0].text}'")
    else:
        print(f"  [FAIL] Expected 1, got {len(unique_db)}")
        for fact in unique_db:
            print(f"    - {fact.text}")

    # === TEST 3: Normalization ===
    print("\n[TEST 3] Text normalization...")

    # Test that these are all considered duplicates
    variations = [
        "Chrome is a dog",
        "Chrome is a dog.",
        "Chrome is a dog!",
        "chrome is a dog",
        "CHROME IS A DOG",
        "Chrome is the dog",
        "Chrome is an dog",
        "  Chrome is a dog  ",
    ]

    unique_normalized = set()
    for var in variations:
        normalized = manager._normalize_text(var)
        unique_normalized.add(normalized)

    print(f"  Tested {len(variations)} variations")
    print(f"  Unique normalized forms: {len(unique_normalized)}")

    if len(unique_normalized) == 1:
        print("  [PASS] All variations normalized to same form!")
        print(f"    Normalized: '{list(unique_normalized)[0]}'")
    else:
        print(f"  [FAIL] Expected 1, got {len(unique_normalized)}")
        for norm in unique_normalized:
            print(f"    - '{norm}'")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    test_results = []
    test_results.append(("Within-batch dedup", len(unique) == 2))
    test_results.append(("Database dedup", len(unique_db) == 1))
    test_results.append(("Normalization", len(unique_normalized) == 1))

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    print(f"\nResults: {passed}/{total} passed\n")
    for test_name, result in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")

    if passed == total:
        print("\n[SUCCESS] All deduplication tests passed!")
        print("Re-importing the same file will not create duplicates.")
    else:
        print(f"\n[PARTIAL] Some tests failed ({total - passed} failures)")

    # Cleanup
    print("\n[CLEANUP] Removing test memory...")
    memory_engine.memories = [m for m in memory_engine.memories if m.get("fact") != "John teaches karate"]


if __name__ == "__main__":
    test_deduplication()
