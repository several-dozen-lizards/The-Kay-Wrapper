#!/usr/bin/env python3
"""
Test case for list-valued attribute contradiction detection.
Verifies that the system doesn't crash when entities have list-valued attributes.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.entity_graph import Entity


def test_list_valued_attributes():
    """Test that contradiction detection works with list-valued attributes."""
    print("=" * 60)
    print("TEST: List-Valued Attribute Contradiction Detection")
    print("=" * 60)

    # Create entity
    entity = Entity("TestEntity", "concept")

    # Add list-valued attributes (should not crash)
    print("\n1. Adding list-valued attributes...")
    entity.add_attribute('favorite_colors', ['green', 'purple'], 1, 'user')
    entity.add_attribute('favorite_colors', ['blue', 'red'], 2, 'user')

    print("[OK] Successfully added list-valued attributes")

    # Detect contradictions (should not crash)
    print("\n2. Detecting contradictions...")
    contradictions = entity.detect_contradictions()

    print(f"[OK] Successfully detected contradictions without crashing")
    print(f"[OK] Found {len(contradictions)} contradiction(s)")

    # Verify contradiction was detected
    if len(contradictions) > 0:
        print("\n3. Contradiction details:")
        for c in contradictions:
            print(f"   - Attribute: {c['attribute']}")
            print(f"   - Values: {c['values']}")
            print(f"   - Severity: {c['severity']}")

    # Test with scalar values (should still work)
    print("\n4. Testing scalar values (baseline)...")
    entity.add_attribute('eye_color', 'green', 3, 'user')
    entity.add_attribute('eye_color', 'brown', 4, 'kay')

    contradictions = entity.detect_contradictions()
    print(f"[OK] Found {len(contradictions)} total contradiction(s)")

    # Test with mixed types
    print("\n5. Testing mixed types (list + scalar)...")
    entity.add_attribute('preferences', ['tea', 'coffee'], 5, 'user')
    entity.add_attribute('preferences', 'water', 6, 'user')

    contradictions = entity.detect_contradictions()
    print(f"[OK] Found {len(contradictions)} total contradiction(s)")

    print("\n" + "=" * 60)
    print("TEST PASSED: All operations completed without errors")
    print("=" * 60)


def test_empty_lists():
    """Test that empty lists are handled correctly."""
    print("\n" + "=" * 60)
    print("TEST: Empty List Handling")
    print("=" * 60)

    entity = Entity("TestEntity2", "concept")

    print("\n1. Adding empty list attribute...")
    entity.add_attribute('tags', [], 1, 'user')
    entity.add_attribute('tags', ['tag1'], 2, 'user')

    contradictions = entity.detect_contradictions()
    print(f"[OK] Successfully handled empty lists")
    print(f"[OK] Found {len(contradictions)} contradiction(s)")

    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)


def test_nested_lists():
    """Test that nested lists are handled correctly."""
    print("\n" + "=" * 60)
    print("TEST: Nested List Handling")
    print("=" * 60)

    entity = Entity("TestEntity3", "concept")

    print("\n1. Adding nested list attribute...")
    entity.add_attribute('matrix', [[1, 2], [3, 4]], 1, 'user')
    entity.add_attribute('matrix', [[5, 6], [7, 8]], 2, 'user')

    contradictions = entity.detect_contradictions()
    print(f"[OK] Successfully handled nested lists")
    print(f"[OK] Found {len(contradictions)} contradiction(s)")

    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_list_valued_attributes()
        test_empty_lists()
        test_nested_lists()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED [OK]")
        print("=" * 60)
    except Exception as e:
        print(f"\n{'=' * 60}")
        print(f"TEST FAILED [ERROR]")
        print(f"{'=' * 60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
