"""
Test script for contradiction resolution system.
Verifies that contradictions auto-resolve after consistent mentions.
"""

from engines.entity_graph import Entity

def test_basic_resolution():
    """Test basic consecutive consistency resolution."""
    print("\n=== TEST 1: Basic Resolution (3 consecutive mentions) ===")

    entity = Entity("Kay", "person")

    # Create initial contradiction
    entity.add_attribute("beverage", "tea", turn=1, source="kay")
    entity.add_attribute("beverage", "coffee", turn=5, source="kay")

    # Check that contradiction exists
    contradictions = entity.detect_contradictions(current_turn=5, resolution_threshold=3)
    print(f"Initial contradictions: {len(contradictions)}")
    assert len(contradictions) == 1, "Should have 1 active contradiction"
    assert not entity.is_contradiction_resolved("beverage"), "Should not be resolved yet"

    # Add 3 consecutive "coffee" mentions
    entity.add_attribute("beverage", "coffee", turn=6, source="kay")
    entity.add_attribute("beverage", "coffee", turn=7, source="kay")
    entity.add_attribute("beverage", "coffee", turn=8, source="kay")

    # Check that contradiction is now resolved
    contradictions = entity.detect_contradictions(current_turn=8, resolution_threshold=3)
    print(f"After 3 consistent mentions: {len(contradictions)} active contradictions")
    assert len(contradictions) == 0, "Should have 0 active contradictions (resolved)"
    assert entity.is_contradiction_resolved("beverage"), "Should be marked as resolved"
    assert entity.get_canonical_value("beverage") == "coffee", "Canonical value should be 'coffee'"

    print("[PASS] TEST 1: Contradiction resolved after 3 consecutive mentions\n")


def test_dominant_value_resolution():
    """Test resolution via dominant value (3x ratio)."""
    print("\n=== TEST 2: Dominant Value Resolution (3x ratio) ===")

    entity = Entity("Kay", "person")

    # Add multiple mentions with clear dominant value
    entity.add_attribute("beverage", "tea", turn=1, source="kay")
    entity.add_attribute("beverage", "coffee", turn=2, source="kay")
    entity.add_attribute("beverage", "coffee", turn=3, source="kay")
    entity.add_attribute("beverage", "coffee", turn=4, source="kay")
    entity.add_attribute("beverage", "coffee", turn=5, source="kay")
    entity.add_attribute("beverage", "coffee", turn=6, source="kay")
    entity.add_attribute("beverage", "coffee", turn=7, source="kay")

    # Recent window (last 10 turns): coffee=6x, tea=1x
    # 6 >= 1 * 3? YES (6 >= 3) → Should resolve

    contradictions = entity.detect_contradictions(current_turn=7, resolution_threshold=3)
    print(f"With 6x coffee vs 1x tea: {len(contradictions)} active contradictions")
    assert len(contradictions) == 0, "Should be resolved via dominant value"
    assert entity.is_contradiction_resolved("beverage"), "Should be marked as resolved"

    print("[PASS] TEST 2: Dominant value resolution works\n")


def test_inconsistent_mentions():
    """Test that inconsistent mentions do NOT resolve."""
    print("\n=== TEST 3: Inconsistent Mentions (should stay active) ===")

    entity = Entity("Kay", "person")

    # Alternating mentions - should NOT resolve
    entity.add_attribute("beverage", "coffee", turn=1, source="kay")
    entity.add_attribute("beverage", "tea", turn=2, source="kay")
    entity.add_attribute("beverage", "coffee", turn=3, source="kay")
    entity.add_attribute("beverage", "tea", turn=4, source="kay")
    entity.add_attribute("beverage", "coffee", turn=5, source="kay")

    contradictions = entity.detect_contradictions(current_turn=5, resolution_threshold=3)
    print(f"With alternating mentions: {len(contradictions)} active contradictions")
    assert len(contradictions) == 1, "Should still have active contradiction"
    assert not entity.is_contradiction_resolved("beverage"), "Should NOT be resolved"

    print("[PASS] TEST 3: Inconsistent mentions keep contradiction active\n")


def test_list_normalization():
    """Test that normalized lists (multi-value attributes) don't trigger contradictions."""
    print("\n=== TEST 4: Multi-Value Attributes (nuanced preferences) ===")

    entity = Entity("Kay", "person")

    # Normalized lists: ["coffee", "tea"] stored consistently
    entity.add_attribute("beverage", ["coffee", "tea"], turn=1, source="kay")
    entity.add_attribute("beverage", ["coffee", "tea"], turn=2, source="kay")
    entity.add_attribute("beverage", ["coffee", "tea"], turn=3, source="kay")

    contradictions = entity.detect_contradictions(current_turn=3, resolution_threshold=3)
    print(f"With consistent multi-value list: {len(contradictions)} active contradictions")
    assert len(contradictions) == 0, "Consistent lists should not create contradictions"

    print("[PASS] TEST 4: Multi-value attributes handled correctly\n")


def test_persistence():
    """Test that resolution status persists through serialization."""
    print("\n=== TEST 5: Persistence (to_dict/from_dict) ===")

    # Create entity and resolve contradiction
    entity = Entity("Kay", "person")
    entity.add_attribute("beverage", "tea", turn=1, source="kay")
    entity.add_attribute("beverage", "coffee", turn=2, source="kay")
    entity.add_attribute("beverage", "coffee", turn=3, source="kay")
    entity.add_attribute("beverage", "coffee", turn=4, source="kay")
    entity.add_attribute("beverage", "coffee", turn=5, source="kay")

    # Resolve
    contradictions = entity.detect_contradictions(current_turn=5, resolution_threshold=3)
    assert len(contradictions) == 0, "Should be resolved"

    # Serialize
    entity_dict = entity.to_dict()
    assert "contradiction_resolution" in entity_dict, "Should persist resolution data"

    # Deserialize
    entity_restored = Entity.from_dict(entity_dict)
    assert entity_restored.is_contradiction_resolved("beverage"), "Resolution should persist"
    assert entity_restored.get_canonical_value("beverage") == "coffee", "Canonical value should persist"

    print("[PASS] TEST 5: Resolution status persists correctly\n")


def run_all_tests():
    """Run all contradiction resolution tests."""
    print("=" * 70)
    print("CONTRADICTION RESOLUTION SYSTEM - TEST SUITE")
    print("=" * 70)

    try:
        test_basic_resolution()
        test_dominant_value_resolution()
        test_inconsistent_mentions()
        test_list_normalization()
        test_persistence()

        print("\n" + "=" * 70)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("=" * 70)
        print("\nContradiction resolution system is working correctly.")
        print("Contradictions will auto-resolve after 3 consecutive consistent mentions.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
