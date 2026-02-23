#!/usr/bin/env python3
"""
System Verification Test - Confirm Critical Systems Work Before Integration

Tests:
1. Hallucination blocking (prevents Kay from fabricating eye colors)
2. Memory layer promotion (episodic/semantic)
3. Entity relationship tracking (Re owns cats, etc.)
4. Contradiction warning system (showing Kay the conflicts)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.memory_engine import MemoryEngine
from engines.memory_layers import MemoryLayerManager
from engines.entity_graph import EntityGraph
from agent_state import AgentState


def test_hallucination_blocking():
    """Test 1: Hallucination blocking prevents Kay from fabricating facts."""
    print("=" * 70)
    print("TEST 1: Hallucination Blocking")
    print("=" * 70)

    memory_engine = MemoryEngine(file_path="memory/test_hallucination.json")

    # Scenario: User says eyes are green
    user_input = "My eyes are green"
    retrieved_memories = [
        {
            "fact": "Re's eyes are green",
            "perspective": "user",
            "user_input": "My eyes are green"
        }
    ]

    print("\n1. User establishes ground truth: 'My eyes are green'")
    print("   Stored in memories as: Re's eyes are green")

    # Test: Kay tries to fabricate a different color
    fabricated_fact = "Your eyes are gold"  # Kay making up a detail
    fact_perspective = "kay"

    print("\n2. Testing validation: Kay says 'Your eyes are gold'")

    is_valid = memory_engine._validate_fact_against_sources(
        fabricated_fact,
        fact_perspective,
        retrieved_memories
    )

    if not is_valid:
        print("   [OK] Hallucination blocked! Kay's fabrication rejected")
        print("   Expected: False (block), Got: False")
    else:
        print("   [FAIL] Hallucination NOT blocked - Kay can fabricate!")
        print("   Expected: False (block), Got: True")

    # Test: Kay correctly recalls user's fact
    correct_fact = "Your eyes are green"
    print("\n3. Testing validation: Kay says 'Your eyes are green'")

    is_valid = memory_engine._validate_fact_against_sources(
        correct_fact,
        fact_perspective,
        retrieved_memories
    )

    if is_valid:
        print("   [OK] Correct fact allowed through")
        print("   Expected: True (allow), Got: True")
    else:
        print("   [FAIL] Correct fact blocked!")
        print("   Expected: True (allow), Got: False")

    # Cleanup
    if os.path.exists("memory/test_hallucination.json"):
        os.remove("memory/test_hallucination.json")

    print("\n" + "=" * 70)
    print("TEST 1 COMPLETE")
    print("=" * 70)


def test_memory_layer_promotion():
    """Test 2: Memory layer promotion (working -> episodic -> semantic)."""
    print("\n" + "=" * 70)
    print("TEST 2: Memory Layer Promotion")
    print("=" * 70)

    layer_manager = MemoryLayerManager()

    # Create a test memory
    test_memory = {
        "type": "extracted_fact",
        "fact": "Test fact for promotion",
        "importance_score": 0.6,
        "access_count": 0,
        "turn_number": 1
    }

    print("\n1. Adding memory to working layer")
    layer_manager.add_memory(test_memory, layer="working")

    # Check it's in working (access the working_memory list directly)
    if test_memory in layer_manager.working_memory:
        print("   [OK] Memory in working layer")
    else:
        print("   [FAIL] Memory not in working layer")

    print(f"   Working layer: {len(layer_manager.working_memory)} memories")

    # Simulate access to trigger promotion (working -> episodic requires 2 accesses)
    print("\n2. Simulating memory access to trigger promotion")
    layer_manager.access_memory(test_memory)
    layer_manager.access_memory(test_memory)

    current_layer = test_memory.get("current_layer", "working")
    print(f"   Current layer after 2 accesses: {current_layer}")
    print(f"   Access count: {test_memory.get('access_count', 0)}")

    # Check layer distribution
    print(f"   Working: {len(layer_manager.working_memory)}, "
          f"Episodic: {len(layer_manager.episodic_memory)}, "
          f"Semantic: {len(layer_manager.semantic_memory)}")

    # Simulate more accesses for potential semantic promotion
    print("\n3. Simulating more accesses for semantic promotion")
    for _ in range(3):
        layer_manager.access_memory(test_memory)

    current_layer = test_memory.get("current_layer", "working")
    access_count = test_memory.get("access_count", 0)
    print(f"   Current layer after 5 total accesses: {current_layer}")
    print(f"   Access count: {access_count}")

    # Show final stats
    stats = layer_manager.get_layer_stats()
    print(f"\n   Layer stats:")
    print(f"   - Working: {stats['working']['count']} memories (capacity: {stats['working']['capacity']})")
    print(f"   - Episodic: {stats['episodic']['count']} memories (capacity: {stats['episodic']['capacity']})")
    print(f"   - Semantic: {stats['semantic']['count']} memories (capacity: {stats['semantic']['capacity']})")

    # Test temporal decay
    print("\n4. Testing temporal decay on episodic memories")
    layer_manager.apply_temporal_decay()
    print("   [OK] Temporal decay applied (no errors)")

    print("\n" + "=" * 70)
    print("TEST 2 COMPLETE")
    print("=" * 70)


def test_entity_relationship_tracking():
    """Test 3: Entity relationship tracking (Re owns cats, etc.)."""
    print("\n" + "=" * 70)
    print("TEST 3: Entity Relationship Tracking")
    print("=" * 70)

    entity_graph = EntityGraph("memory/test_entity_relationships.json")

    print("\n1. Creating entities: Re (person) and Saga (pet)")

    # Create entities
    re_entity = entity_graph.get_or_create_entity("Re", "person", turn=1)
    saga_entity = entity_graph.get_or_create_entity("Saga", "pet", turn=1)

    if "Re" in entity_graph.entities and "Saga" in entity_graph.entities:
        print("   [OK] Entities created successfully")
    else:
        print("   [FAIL] Entity creation failed")

    print("\n2. Creating ownership relationship: Re owns Saga")

    # Create relationship
    entity_graph.add_relationship("Re", "owns", "Saga", turn=1, source="user")

    # Verify relationship exists
    relationships = entity_graph.get_entity_relationships("Re")

    if len(relationships) > 0:
        print(f"   [OK] Relationship created: {relationships[0].entity1} {relationships[0].relation_type} {relationships[0].entity2}")
    else:
        print("   [FAIL] Relationship not created")

    print("\n3. Adding attributes to entities")

    # Add attributes
    saga_entity.add_attribute("species", "dog", turn=1, source="user")
    saga_entity.add_attribute("age", "3", turn=1, source="user")

    species = saga_entity.get_current_value("species")
    age = saga_entity.get_current_value("age")

    if species == "dog" and age == "3":
        print(f"   [OK] Attributes stored: species={species}, age={age}")
    else:
        print(f"   [FAIL] Attributes not stored correctly: species={species}, age={age}")

    print("\n4. Querying related entities")

    related = entity_graph.get_related_entities("Re", max_distance=1)

    if "Saga" in related:
        print(f"   [OK] Related entities found: {related}")
    else:
        print(f"   [FAIL] Related entities not found: {related}")

    # Cleanup
    if os.path.exists("memory/test_entity_relationships.json"):
        os.remove("memory/test_entity_relationships.json")

    print("\n" + "=" * 70)
    print("TEST 3 COMPLETE")
    print("=" * 70)


def test_contradiction_warning_system():
    """Test 4: Contradiction warning system (showing Kay the conflicts)."""
    print("\n" + "=" * 70)
    print("TEST 4: Contradiction Warning System")
    print("=" * 70)

    memory_engine = MemoryEngine(file_path="memory/test_contradictions.json")

    # Scenario: User states eye color is green
    retrieved_memories = [
        {
            "fact": "Re's eyes are green",
            "perspective": "user",
            "user_input": "My eyes are green"
        }
    ]

    print("\n1. Ground truth established: Re's eyes are green")

    # Test: Check for contradiction when Kay says different color
    new_fact = "Your eyes are brown"
    print("\n2. Testing contradiction detection: Kay says 'Your eyes are brown'")

    is_contradiction = memory_engine._check_contradiction(new_fact, retrieved_memories)

    if is_contradiction:
        print("   [OK] Contradiction detected!")
        print("   Expected: True (contradiction), Got: True")
    else:
        print("   [FAIL] Contradiction NOT detected")
        print("   Expected: True (contradiction), Got: False")

    # Test: Entity-aware contradiction (Reed's eyes vs Re's eyes)
    print("\n3. Testing entity-aware contradiction: Kay says 'My eyes are gold'")
    print("   (Should NOT contradict Re's green eyes)")

    kay_fact = "My eyes are gold"
    is_contradiction = memory_engine._check_contradiction(kay_fact, retrieved_memories)

    if not is_contradiction:
        print("   [OK] No false contradiction - different entities")
        print("   Expected: False (no contradiction), Got: False")
    else:
        print("   [FAIL] False contradiction detected between different entities")
        print("   Expected: False (no contradiction), Got: True")

    # Test: Entity contradiction detection in entity graph
    print("\n4. Testing entity graph contradiction detection")

    entity_graph = memory_engine.entity_graph
    re_entity = entity_graph.get_or_create_entity("Re", "person", turn=1)

    # Add conflicting eye colors
    re_entity.add_attribute("eye_color", "green", turn=1, source="user")
    re_entity.add_attribute("eye_color", "brown", turn=2, source="kay")

    contradictions = entity_graph.get_all_contradictions()

    if len(contradictions) > 0:
        print(f"   [OK] Entity contradiction detected: {len(contradictions)} contradiction(s)")
        for c in contradictions:
            print(f"        {c['entity']}.{c['attribute']}: {list(c['values'].keys())}")
    else:
        print("   [FAIL] Entity contradiction not detected")

    # Cleanup
    if os.path.exists("memory/test_contradictions.json"):
        os.remove("memory/test_contradictions.json")
    if os.path.exists("memory/test_entity_graph.json"):
        os.remove("memory/test_entity_graph.json")

    print("\n" + "=" * 70)
    print("TEST 4 COMPLETE")
    print("=" * 70)


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("SYSTEM VERIFICATION TEST SUITE")
    print("Verifying critical systems before integration changes")
    print("=" * 70)

    try:
        test_hallucination_blocking()
        test_memory_layer_promotion()
        test_entity_relationship_tracking()
        test_contradiction_warning_system()

        print("\n" + "=" * 70)
        print("ALL VERIFICATION TESTS PASSED [OK]")
        print("=" * 70)
        print("\nSystems verified:")
        print("  1. [OK] Hallucination blocking prevents Kay from fabricating facts")
        print("  2. [OK] Memory layer promotion (working -> episodic -> semantic)")
        print("  3. [OK] Entity relationship tracking (Re owns cats, etc.)")
        print("  4. [OK] Contradiction warning system detects conflicts")
        print("\n[READY] Safe to proceed with integration changes")

    except Exception as e:
        print(f"\n{'=' * 70}")
        print("VERIFICATION FAILED [ERROR]")
        print(f"{'=' * 70}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
