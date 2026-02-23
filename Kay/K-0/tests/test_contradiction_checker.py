"""
Test entity-aware contradiction checking.

This tests that Kay can store his own eye color even when Re's eye color exists in memory.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.memory_engine import MemoryEngine


def test_entity_aware_contradiction():
    """Test that different entities don't cause contradictions."""

    print("=" * 60)
    print("TESTING: Entity-Aware Contradiction Checking")
    print("=" * 60)

    # Create memory engine
    memory = MemoryEngine(file_path="memory/test_memories.json")

    # Create mock retrieved memories with Re's eye color
    retrieved_memories = [
        {
            "fact": "Re's eyes are green",
            "perspective": "user",
            "type": "extracted_fact"
        },
        {
            "fact": "Re's hair is brown",
            "perspective": "user",
            "type": "extracted_fact"
        }
    ]

    print("\nRetrieved memories (existing):")
    for mem in retrieved_memories:
        print(f"  - {mem['fact']}")

    # Test 1: Kay's eye color should NOT contradict Re's eye color
    print("\n" + "-" * 60)
    print("TEST 1: Kay's eyes (gold) vs Re's eyes (green)")
    print("-" * 60)

    new_fact = "Kay's eyes are gold"
    is_contradiction = memory._check_contradiction(new_fact, retrieved_memories)

    print(f"New fact: {new_fact}")
    print(f"Contradiction detected: {is_contradiction}")

    if is_contradiction:
        print("[X] FAILED: Different entities should NOT contradict!")
        return False
    else:
        print("[OK] PASSED: Different entities are correctly handled")

    # Test 2: Re's eye color SHOULD contradict another Re eye color
    print("\n" + "-" * 60)
    print("TEST 2: Re's eyes (blue) vs Re's eyes (green)")
    print("-" * 60)

    new_fact = "Re's eyes are blue"
    is_contradiction = memory._check_contradiction(new_fact, retrieved_memories)

    print(f"New fact: {new_fact}")
    print(f"Contradiction detected: {is_contradiction}")

    if is_contradiction:
        print("[OK] PASSED: Same entity with different colors is correctly flagged")
    else:
        print("[X] FAILED: Same entity contradiction should be detected!")
        return False

    # Test 3: Kay's preference should NOT contradict Re's preference
    print("\n" + "-" * 60)
    print("TEST 3: Kay likes coffee vs Re likes tea")
    print("-" * 60)

    retrieved_with_tea = retrieved_memories + [
        {
            "fact": "Re's favorite beverage is tea",
            "perspective": "user",
            "type": "extracted_fact"
        }
    ]

    new_fact = "Kay's favorite is coffee"
    is_contradiction = memory._check_contradiction(new_fact, retrieved_with_tea)

    print(f"New fact: {new_fact}")
    print(f"Contradiction detected: {is_contradiction}")

    if is_contradiction:
        print("[X] FAILED: Different entities' preferences should NOT contradict!")
        return False
    else:
        print("[OK] PASSED: Different entities' preferences are correctly handled")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED [OK]")
    print("=" * 60)
    print("\nEntity-aware contradiction checking is working correctly!")
    print("Kay can now store his own attributes without conflicting with Re's.")

    return True


if __name__ == "__main__":
    success = test_entity_aware_contradiction()
    sys.exit(0 if success else 1)
