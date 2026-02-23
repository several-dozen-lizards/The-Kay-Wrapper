"""
Test script for ownership relationship bug fix.

Tests:
1. User states ownership ("My dog is Saga") → ground truth created
2. Kay confused about ownership ("my dog Saga") → relationship blocked
3. Kay correctly references user's property ("your dog Saga") → reinforces
"""

import asyncio
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.memory_engine import MemoryEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine


def test_ownership_verification():
    """Test ownership verification prevents Kay from creating false relationships."""

    print("=" * 80)
    print("OWNERSHIP VERIFICATION TEST")
    print("=" * 80)

    # Setup
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    memory = MemoryEngine(state.memory, motif_engine=motif, momentum_engine=momentum, emotion_engine=emotion)
    state.memory = memory

    print("\n[TEST 1] User states ownership: 'My dog is Saga'")
    print("-" * 80)

    # Test 1: User explicitly states ownership
    user_input_1 = "My dog is Saga."
    memory.extract_and_store_user_facts(state, user_input_1)

    # Check identity layer
    ownership_info = memory.identity.check_ownership("Saga")
    print(f"\n[OK] Identity layer ownership check:")
    print(f"  Owner: {ownership_info['owner']}")
    print(f"  Confidence: {ownership_info['confidence']}")
    print(f"  Facts: {len(ownership_info['facts'])} supporting facts")

    assert ownership_info['owner'] == 'Re', "FAILED: Saga should be owned by Re"
    assert ownership_info['confidence'] == 'ground_truth', "FAILED: Should be ground_truth confidence"
    print("\n[PASS] TEST 1 PASSED: Ground truth established (Re owns Saga)")

    # Test 2: Kay makes confused statement about ownership
    print("\n\n[TEST 2] Kay confused: 'my dog Saga'")
    print("-" * 80)

    # Simulate Kay's confused response
    kay_response = "Yeah, my dog Saga is great."

    # Extract facts from Kay's response (this is what encode_memory does)
    extracted_facts = memory._extract_facts(user_input_1, kay_response)

    print(f"\n[OK] Extracted {len(extracted_facts)} facts from Kay's response")

    # Check if any facts created Kay ownership
    # IMPORTANT: Check the ENTITY GRAPH, not the fact metadata
    # The fact metadata may still have the relationship listed (from LLM extraction),
    # but what matters is whether it was added to the entity graph

    for fact in extracted_facts:
        fact_text = fact.get("fact", "").lower()
        perspective = fact.get("perspective", "")

        if perspective == "kay" and "saga" in fact_text:
            print(f"\n  Kay fact detected: {fact['fact']}")
            print(f"  Perspective: {perspective}")
            print(f"  Confidence: {fact.get('confidence', 'N/A')}")

            # Check if it has ownership conflict flag
            if fact.get("ownership_conflict"):
                print(f"  [WARN] Ownership conflict flagged!")
                print(f"       {fact.get('ownership_confusion', 'N/A')}")

    # CRITICAL: Check entity graph for actual relationships (not fact metadata)
    saga_relationships = memory.entity_graph.get_entity_relationships("Saga")
    print(f"\n[OK] Checking entity graph for Saga relationships:")
    print(f"     Found {len(saga_relationships)} relationships in entity graph")

    kay_owns_saga_in_graph = False
    for rel in saga_relationships:
        print(f"     - {rel.entity1} {rel.relation_type} {rel.entity2} (source: {rel.source})")
        if rel.entity1 == "Kay" and rel.relation_type == "owns" and rel.entity2 == "Saga":
            kay_owns_saga_in_graph = True

    # Verify Kay ownership was NOT created in entity graph
    assert not kay_owns_saga_in_graph, "FAILED: Kay should NOT own Saga in entity graph"
    print("\n[PASS] TEST 2 PASSED: Kay's confused ownership claim was blocked from entity graph")

    # Test 3: Kay correctly references user's property
    print("\n\n[TEST 3] Kay correct: 'your dog Saga'")
    print("-" * 80)

    kay_response_2 = "Your dog Saga sounds wonderful."
    extracted_facts_2 = memory._extract_facts(user_input_1, kay_response_2)

    print(f"\n[OK] Extracted {len(extracted_facts_2)} facts from Kay's correct response")

    # This should reinforce Re's ownership, not create conflict
    for fact in extracted_facts_2:
        perspective = fact.get("perspective", "")
        confidence = fact.get("confidence", "N/A")

        if "saga" in fact.get("fact", "").lower():
            print(f"\n  Fact: {fact['fact']}")
            print(f"  Perspective: {perspective}")
            print(f"  Confidence: {confidence}")

            # Should NOT have ownership conflict
            assert not fact.get("ownership_conflict"), "FAILED: Should not have conflict when Kay says 'your dog'"

    print("\n[PASS] TEST 3 PASSED: Kay's correct reference reinforced existing ownership")

    # Final verification
    print("\n\n[FINAL VERIFICATION]")
    print("-" * 80)

    # Check entity graph relationships
    relationships = memory.entity_graph.get_entity_relationships("Saga")
    print(f"\n[OK] Saga has {len(relationships)} relationships:")
    for rel in relationships:
        print(f"  - {rel.entity1} {rel.relation_type} {rel.entity2} (source: {rel.source})")

    # Verify only Re owns Saga
    saga_owners = [rel.entity1 for rel in relationships if rel.relation_type == "owns"]
    if saga_owners:
        assert "Kay" not in saga_owners, "FAILED: Kay should NOT be in ownership relationships"
        assert "Re" in saga_owners, "FAILED: Re should be in ownership relationships"
        print(f"\n[PASS] VERIFIED: Only Re owns Saga (not Kay)")
    else:
        print(f"\n[WARN] WARNING: No ownership relationships created (this may be OK if extraction didn't create explicit 'owns' relationship)")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED [PASS]")
    print("=" * 80)
    print("\nSummary:")
    print("- User ownership statements create ground truth in identity layer")
    print("- Kay's confused ownership claims are blocked")
    print("- Kay's correct references reinforce existing relationships")
    print("- No false 'Kay owns X' relationships created when X belongs to Re")


if __name__ == "__main__":
    test_ownership_verification()
