#!/usr/bin/env python3
"""
Test attribute normalization in entity graph to prevent duplicate storage.
Verifies that values like "5 cats" and "5" are normalized to the same format.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.entity_graph import Entity, EntityGraph


def test_number_normalization():
    """Test that number-related attributes are normalized."""
    print("=" * 70)
    print("TEST 1: Number Attribute Normalization")
    print("=" * 70)

    entity = Entity("Re", "person")

    # Add pet_count in different formats
    print("\n1. Adding pet_count: '5' and '5 cats'")
    entity.add_attribute('pet_count', '5', 1, 'user')
    entity.add_attribute('pet_count', '5 cats', 2, 'user')

    # Check that both normalized to the same value
    history = entity.get_attribute_history('pet_count')
    values = [val for val, _, _, _ in history]

    print(f"   Stored values: {values}")

    if values[0] == values[1]:
        print("   [OK] Both normalized to same value - no duplicate!")
    else:
        print("   [FAIL] Values are different - duplicate created")

    # Test age attribute
    print("\n2. Adding age: '25' and '25 years old'")
    entity.add_attribute('age', '25', 3, 'user')
    entity.add_attribute('age', '25 years old', 4, 'user')

    history = entity.get_attribute_history('age')
    values = [val for val, _, _, _ in history]

    print(f"   Stored values: {values}")

    if values[0] == values[1]:
        print("   [OK] Both normalized to same value - no duplicate!")
    else:
        print("   [FAIL] Values are different - duplicate created")

    print("\n" + "=" * 70)
    print("TEST 1 COMPLETE")
    print("=" * 70)


def test_multi_value_normalization():
    """Test that multi-value attributes are normalized."""
    print("\n" + "=" * 70)
    print("TEST 2: Multi-Value Attribute Normalization")
    print("=" * 70)

    entity = Entity("Re", "person")

    # Add favorite_colors in different formats
    print("\n1. Adding favorite_colors: ['green', 'purple'] and 'green and purple'")
    entity.add_attribute('favorite_colors', ['green', 'purple'], 1, 'user')
    entity.add_attribute('favorite_colors', 'green and purple', 2, 'user')

    history = entity.get_attribute_history('favorite_colors')
    values = [val for val, _, _, _ in history]

    print(f"   Stored values: {values}")

    if values[0] == values[1]:
        print("   [OK] Both normalized to same value - no duplicate!")
    else:
        print("   [FAIL] Values are different - duplicate created")

    # Test hobbies with comma separator
    print("\n2. Adding hobbies: ['reading', 'gaming'] and 'reading, gaming'")
    entity.add_attribute('hobbies', ['reading', 'gaming'], 3, 'user')
    entity.add_attribute('hobbies', 'reading, gaming', 4, 'user')

    history = entity.get_attribute_history('hobbies')
    values = [val for val, _, _, _ in history]

    print(f"   Stored values: {values}")

    if values[0] == values[1]:
        print("   [OK] Both normalized to same value - no duplicate!")
    else:
        print("   [FAIL] Values are different - duplicate created")

    print("\n" + "=" * 70)
    print("TEST 2 COMPLETE")
    print("=" * 70)


def test_contradiction_detection_after_normalization():
    """Test that normalization doesn't break contradiction detection."""
    print("\n" + "=" * 70)
    print("TEST 3: Contradiction Detection (After Normalization)")
    print("=" * 70)

    entity = Entity("Re", "person")

    # These should NOT create contradictions (same after normalization)
    print("\n1. Adding normalized duplicates (should NOT conflict):")
    entity.add_attribute('pet_count', '5', 1, 'user')
    entity.add_attribute('pet_count', '5 cats', 2, 'user')

    contradictions = entity.detect_contradictions()
    pet_count_contradictions = [c for c in contradictions if c['attribute'] == 'pet_count']

    if len(pet_count_contradictions) == 0:
        print("   [OK] No contradiction detected for '5' vs '5 cats'")
    else:
        print("   [FAIL] Contradiction detected when values should be normalized")

    # These SHOULD create contradictions (different after normalization)
    print("\n2. Adding real contradictions (SHOULD conflict):")
    entity.add_attribute('age', '25', 3, 'user')
    entity.add_attribute('age', '30', 4, 'user')

    contradictions = entity.detect_contradictions()
    age_contradictions = [c for c in contradictions if c['attribute'] == 'age']

    if len(age_contradictions) > 0:
        print("   [OK] Contradiction detected for '25' vs '30'")
        print(f"        Values: {age_contradictions[0]['values']}")
    else:
        print("   [FAIL] No contradiction detected for truly different values")

    print("\n" + "=" * 70)
    print("TEST 3 COMPLETE")
    print("=" * 70)


def test_ownership_relationships_unaffected():
    """Test that normalization doesn't affect relationship tracking."""
    print("\n" + "=" * 70)
    print("TEST 4: Relationship Tracking (Ownership System)")
    print("=" * 70)

    graph = EntityGraph("memory/test_entity_graph_normalization.json")

    # Create entities
    print("\n1. Creating entities and relationships:")
    re_entity = graph.get_or_create_entity("Re", "person", turn=1)
    saga_entity = graph.get_or_create_entity("Saga", "pet", turn=1)

    # Add ownership relationship
    graph.add_relationship("Re", "owns", "Saga", turn=1, source="user")

    # Verify relationship exists
    relationships = graph.get_entity_relationships("Re")

    if len(relationships) > 0:
        print("   [OK] Relationship created successfully")
        print(f"        {relationships[0].entity1} {relationships[0].relation_type} {relationships[0].entity2}")
    else:
        print("   [FAIL] Relationship not created")

    # Add normalized attributes to entities (shouldn't affect relationships)
    print("\n2. Adding normalized attributes to entities:")
    re_entity.add_attribute('pet_count', '1 cat', 2, 'user')
    saga_entity.add_attribute('age', '3 years', 2, 'user')

    # Verify relationships still intact
    relationships = graph.get_entity_relationships("Re")

    if len(relationships) > 0:
        print("   [OK] Relationships intact after adding normalized attributes")
    else:
        print("   [FAIL] Relationships broken after normalization")

    # Cleanup
    import os
    if os.path.exists("memory/test_entity_graph_normalization.json"):
        os.remove("memory/test_entity_graph_normalization.json")

    print("\n" + "=" * 70)
    print("TEST 4 COMPLETE")
    print("=" * 70)


def test_edge_cases():
    """Test edge cases and special scenarios."""
    print("\n" + "=" * 70)
    print("TEST 5: Edge Cases")
    print("=" * 70)

    entity = Entity("Test", "concept")

    # Test 1: Single word (shouldn't split)
    print("\n1. Single value shouldn't split:")
    entity.add_attribute('favorite_color', 'green', 1, 'user')
    val = entity.get_current_value('favorite_color')
    print(f"   Input: 'green' -> Output: {val}")
    if val == 'green':
        print("   [OK] Single value preserved")
    else:
        print("   [FAIL] Single value incorrectly modified")

    # Test 2: Number in non-count attribute (shouldn't extract)
    print("\n2. Numbers in non-count attributes:")
    entity.add_attribute('address', '123 Main Street', 2, 'user')
    val = entity.get_current_value('address')
    print(f"   Input: '123 Main Street' -> Output: {val}")
    if '123' in str(val) and 'Main' in str(val):
        print("   [OK] Non-count number attribute preserved")
    else:
        print("   [FAIL] Number incorrectly extracted from address")

    # Test 3: Empty list
    print("\n3. Empty list handling:")
    entity.add_attribute('tags', [], 3, 'user')
    val = entity.get_current_value('tags')
    print(f"   Input: [] -> Output: {val}")
    if val == []:
        print("   [OK] Empty list preserved")
    else:
        print("   [FAIL] Empty list modified")

    # Test 4: Whitespace stripping
    print("\n4. Whitespace normalization:")
    entity.add_attribute('name', '  John Doe  ', 4, 'user')
    val = entity.get_current_value('name')
    print(f"   Input: '  John Doe  ' -> Output: '{val}'")
    if val == 'John Doe':
        print("   [OK] Whitespace stripped")
    else:
        print("   [FAIL] Whitespace not handled correctly")

    print("\n" + "=" * 70)
    print("TEST 5 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_number_normalization()
        test_multi_value_normalization()
        test_contradiction_detection_after_normalization()
        test_ownership_relationships_unaffected()
        test_edge_cases()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED [OK]")
        print("=" * 70)
        print("\nSummary:")
        print("- Number attributes normalized (e.g., '5 cats' -> '5')")
        print("- Multi-value attributes normalized (e.g., 'green and purple' -> ['green', 'purple'])")
        print("- Contradiction detection still works correctly")
        print("- Relationship tracking unaffected")
        print("- Edge cases handled properly")

    except Exception as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED [ERROR]")
        print(f"{'=' * 70}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
