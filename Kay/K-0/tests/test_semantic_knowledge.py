"""
Test Semantic Knowledge Store

Validates that the semantic knowledge system correctly:
1. Stores facts with entity indexing
2. Retrieves facts by entity matching and keyword overlap
3. Scores relevance correctly
4. Persists to disk and reloads
"""

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.semantic_knowledge import SemanticKnowledge, reset_semantic_knowledge


def test_semantic_knowledge():
    """Run comprehensive semantic knowledge tests"""

    print("=" * 80)
    print("SEMANTIC KNOWLEDGE STORE - TEST SUITE")
    print("=" * 80)

    # Use test file to avoid polluting production data
    test_path = "memory/test_semantic_knowledge.json"

    # Clean up any existing test file
    if os.path.exists(test_path):
        os.remove(test_path)

    # Reset singleton
    reset_semantic_knowledge()

    # Create instance
    sk = SemanticKnowledge(storage_path=test_path)

    print("\n[TEST 1] Adding facts")
    print("-" * 80)

    # Add pigeon facts
    sk.add_fact(
        text="Gimpy is a pigeon with one leg",
        entities=["Gimpy", "pigeon"],
        source="pigeon_names.txt",
        category="animals"
    )

    sk.add_fact(
        text="Bob is a speckled pigeon that visits the park",
        entities=["Bob", "pigeon", "park"],
        source="pigeon_names.txt",
        category="animals"
    )

    sk.add_fact(
        text="Fork is a pigeon with a split tail feather",
        entities=["Fork", "pigeon"],
        source="pigeon_names.txt",
        category="animals"
    )

    sk.add_fact(
        text="Zebra is a black and white striped pigeon",
        entities=["Zebra", "pigeon"],
        source="pigeon_names.txt",
        category="animals"
    )

    # Add non-pigeon facts
    sk.add_fact(
        text="Chrome is a cat who steals burritos from doordash",
        entities=["Chrome", "cat", "burritos"],
        source="conversation",
        category="animals"
    )

    sk.add_fact(
        text="Re is a researcher studying AI persistence",
        entities=["Re", "AI", "researcher"],
        source="core_identity",
        category="people"
    )

    sk.add_fact(
        text="Archive Zero uses shame mechanisms for containment",
        entities=["Archive Zero", "shame"],
        source="imported_document.txt",
        category="concepts"
    )

    print(f"\n[OK] Added {len(sk.facts)} facts")

    # Verify stats
    stats = sk.get_stats()
    print(f"[OK] Stats: {stats['total_facts']} facts, {stats['total_entities']} entities, {stats['total_categories']} categories")
    print(f"[OK] Categories: {stats['categories']}")

    assert stats['total_facts'] == 7, f"Expected 7 facts, got {stats['total_facts']}"
    assert stats['total_categories'] == 3, f"Expected 3 categories, got {stats['total_categories']}"

    print("\n[TEST 2] Query by entity")
    print("-" * 80)

    # Query for specific pigeon
    results = sk.query("What do you know about Gimpy?", entities=["Gimpy"])

    print(f"\nQuery: 'What do you know about Gimpy?'")
    print(f"Results: {len(results)} facts")

    for r in results[:3]:
        print(f"  - [{r['relevance_score']:.1f}] {r['text']}")

    assert len(results) > 0, "Should find at least one fact about Gimpy"
    assert "Gimpy" in results[0]['text'], "Top result should mention Gimpy"
    assert results[0]['relevance_score'] > 100, "Entity match should score high (100+ points)"

    print("[OK] Entity query returned correct results")

    print("\n[TEST 3] Query by keyword (no explicit entity)")
    print("-" * 80)

    # Query with keyword only
    results = sk.query("What pigeons do I know?")

    print(f"\nQuery: 'What pigeons do I know?'")
    print(f"Results: {len(results)} facts")

    for r in results[:5]:
        print(f"  - [{r['relevance_score']:.1f}] {r['text']}")

    # Should find all 4 pigeon facts
    pigeon_results = [r for r in results if 'pigeon' in r['text'].lower()]
    assert len(pigeon_results) == 4, f"Expected 4 pigeon facts, found {len(pigeon_results)}"

    # Should NOT include Chrome (cat)
    chrome_in_results = any('chrome' in r['text'].lower() for r in results[:4])
    assert not chrome_in_results, "Chrome (cat) should not appear in pigeon query results"

    print("[OK] Keyword query returned all pigeon facts, excluded irrelevant facts")

    print("\n[TEST 4] Get facts by entity (direct lookup)")
    print("-" * 80)

    # Direct entity lookup
    gimpy_facts = sk.get_facts_by_entity("Gimpy")

    print(f"\nDirect lookup: Entity='Gimpy'")
    print(f"Results: {len(gimpy_facts)} facts")

    for f in gimpy_facts:
        print(f"  - {f['text']}")

    assert len(gimpy_facts) == 1, f"Expected 1 fact about Gimpy, got {len(gimpy_facts)}"
    assert "one leg" in gimpy_facts[0]['text'], "Should be the correct Gimpy fact"

    print("[OK] Entity lookup returned correct facts")

    print("\n[TEST 5] Get facts by category")
    print("-" * 80)

    # Category lookup
    animal_facts = sk.get_facts_by_category("animals")

    print(f"\nCategory lookup: 'animals'")
    print(f"Results: {len(animal_facts)} facts")

    for f in animal_facts[:5]:
        print(f"  - {f['text'][:60]}...")

    assert len(animal_facts) == 5, f"Expected 5 animal facts, got {len(animal_facts)}"

    people_facts = sk.get_facts_by_category("people")
    assert len(people_facts) == 1, f"Expected 1 people fact, got {len(people_facts)}"

    print("[OK] Category lookup returned correct facts")

    print("\n[TEST 6] Persistence (save and reload)")
    print("-" * 80)

    # Save to disk
    sk.save()
    print(f"[OK] Saved knowledge base to {test_path}")

    # Create new instance and load
    reset_semantic_knowledge()
    sk2 = SemanticKnowledge(storage_path=test_path)

    print(f"[OK] Loaded knowledge base from {test_path}")

    # Verify same facts exist
    assert len(sk2.facts) == 7, f"Expected 7 facts after reload, got {len(sk2.facts)}"

    # Verify entity index rebuilt correctly
    gimpy_facts_after_reload = sk2.get_facts_by_entity("Gimpy")
    assert len(gimpy_facts_after_reload) == 1, "Entity index should be restored after reload"

    # Query should still work
    results = sk2.query("What pigeons do I know?")
    pigeon_results = [r for r in results if 'pigeon' in r['text'].lower()]
    assert len(pigeon_results) == 4, f"Expected 4 pigeon facts after reload, found {len(pigeon_results)}"

    print("[OK] All data persisted and reloaded correctly")

    print("\n[TEST 7] Scoring logic")
    print("-" * 80)

    # Query that should rank Gimpy highest
    results = sk2.query("Tell me about the pigeon named Gimpy")

    print(f"\nQuery: 'Tell me about the pigeon named Gimpy'")
    print(f"Top 3 results:")

    for r in results[:3]:
        print(f"  - [{r['relevance_score']:.1f}] {r['text'][:60]}...")

    # Gimpy should be top result (entity match = 100 points)
    assert results[0]['text'].startswith("Gimpy"), "Gimpy should be top result (entity match)"
    assert results[0]['relevance_score'] >= 120, "Should have high score (Gimpy entity + keywords)"

    print("[OK] Scoring prioritizes entity matches correctly")

    print("\n[TEST 8] Delete fact")
    print("-" * 80)

    # Get Gimpy's fact ID
    gimpy_fact = sk2.get_facts_by_entity("Gimpy")[0]
    gimpy_id = gimpy_fact['fact_id']

    print(f"Deleting fact: {gimpy_id} - {gimpy_fact['text']}")

    # Delete
    deleted = sk2.delete_fact(gimpy_id)
    assert deleted, "Should successfully delete fact"

    # Verify deleted
    gimpy_facts_after_delete = sk2.get_facts_by_entity("Gimpy")
    assert len(gimpy_facts_after_delete) == 0, "Gimpy fact should be deleted"

    # Total facts should decrease
    assert len(sk2.facts) == 6, f"Expected 6 facts after delete, got {len(sk2.facts)}"

    print("[OK] Fact deleted correctly, indexes updated")

    # Clean up test file
    if os.path.exists(test_path):
        os.remove(test_path)
        print(f"\n[CLEANUP] Removed test file: {test_path}")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print("\nSemantic Knowledge Store is working correctly:")
    print("  [OK] Stores facts with entity and category indexing")
    print("  [OK] Retrieves facts by entity matching and keywords")
    print("  [OK] Scores relevance correctly (entity > keyword)")
    print("  [OK] Persists to disk and reloads successfully")
    print("  [OK] Supports category filtering and deletion")
    print("\nReady for Phase 2: Document import integration")
    print("=" * 80)


if __name__ == "__main__":
    test_semantic_knowledge()
