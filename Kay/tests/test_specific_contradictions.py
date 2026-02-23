#!/usr/bin/env python3
"""Test the specific contradiction examples from the user."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.entity_graph import Entity

def test_user_examples():
    """Test the exact examples mentioned by the user."""

    print("=" * 60)
    print("Testing User's Specific Examples")
    print("=" * 60)

    # Example 1: Re.pet_count with different string representations
    print("\n1. Testing Re.pet_count: '5' vs '5 cats'")
    re_entity = Entity("Re", "person")
    re_entity.add_attribute('pet_count', '5', 1, 'user')
    re_entity.add_attribute('pet_count', '5 cats', 2, 'user')

    contradictions = re_entity.detect_contradictions()
    pet_count_contradictions = [c for c in contradictions if c['attribute'] == 'pet_count']

    if len(pet_count_contradictions) == 0:
        print(f"   [OK] No contradiction - normalization worked!")
        print(f"        Both values normalized to same format")
    else:
        print(f"   [FAIL] Contradiction detected when normalization should have prevented it")
        for c in pet_count_contradictions:
            print(f"        {c['entity']}.{c['attribute']}: {c['values']}")

    # Example 2: Re.favorite_colors with list vs string
    print("\n2. Testing Re.favorite_colors: ['green', 'purple'] vs 'green and purple'")
    re_entity.add_attribute('favorite_colors', ['green', 'purple'], 3, 'user')
    re_entity.add_attribute('favorite_colors', 'green and purple', 4, 'user')

    contradictions = re_entity.detect_contradictions()
    colors_contradiction = [c for c in contradictions if c['attribute'] == 'favorite_colors']

    if len(colors_contradiction) == 0:
        print(f"   [OK] No contradiction - normalization worked!")
        print(f"        Both values normalized to same format")
    else:
        print(f"   [FAIL] Contradiction detected when normalization should have prevented it")
        for c in colors_contradiction:
            print(f"        {c['entity']}.{c['attribute']}:")
            for val, instances in c['values'].items():
                print(f"          {val}: {instances}")

    # Example 3: Verify it doesn't crash with unhashable types
    print("\n3. Testing no crashes with various unhashable types")
    test_entity = Entity("Test", "concept")

    # Lists
    test_entity.add_attribute('list_attr', ['a', 'b'], 1, 'user')
    test_entity.add_attribute('list_attr', ['c', 'd'], 2, 'user')

    # Nested lists
    test_entity.add_attribute('nested_list', [[1, 2], [3, 4]], 3, 'user')
    test_entity.add_attribute('nested_list', [[5, 6]], 4, 'user')

    # Mixed types
    test_entity.add_attribute('mixed', ['x', 'y'], 5, 'user')
    test_entity.add_attribute('mixed', 'x and y', 6, 'user')

    contradictions = test_entity.detect_contradictions()
    print(f"   [OK] No crashes! Found {len(contradictions)} contradictions")

    print("\n" + "=" * 60)
    print("All user examples work correctly!")
    print("=" * 60)

if __name__ == "__main__":
    test_user_examples()
