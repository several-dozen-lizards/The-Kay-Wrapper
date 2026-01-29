"""
Test script for extraction logic fix.

Tests that Kay's conversational references don't create false Kay-facts.
"""

import asyncio
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.memory_engine import MemoryEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine


def test_extraction_conversational_references():
    """Test that extraction doesn't create Kay-facts from conversational references."""

    print("=" * 80)
    print("EXTRACTION LOGIC FIX TEST")
    print("Testing: Kay's conversational references should NOT create Kay-facts")
    print("=" * 80)

    # Setup
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    memory = MemoryEngine(state.memory, motif_engine=motif, momentum_engine=momentum, emotion_engine=emotion)
    state.memory = memory

    # Test 1: User states ownership, Kay makes conversational reference
    print("\n[TEST 1] Kay says 'your cats' - should NOT create Kay ownership")
    print("-" * 80)

    user_input = "My cats are Dice, Chrome, and Luna."
    kay_response = "Your cats - Dice, Chrome, and Luna - sound wonderful!"

    # Extract facts
    extracted_facts = memory._extract_facts(user_input, kay_response)

    print(f"\n[OK] Extracted {len(extracted_facts)} facts")

    # Check: Should have Re ownership, NOT Kay ownership
    kay_ownership_found = False
    re_ownership_found = False

    for fact in extracted_facts:
        fact_text = fact.get("fact", "")
        perspective = fact.get("perspective", "")
        relationships = fact.get("relationships", [])

        print(f"\n  Fact: {fact_text}")
        print(f"  Perspective: {perspective}")

        # Check relationships
        for rel in relationships:
            entity1 = rel.get("entity1")
            relation = rel.get("relation")
            entity2 = rel.get("entity2")

            if relation == "owns":
                print(f"  Relationship: {entity1} owns {entity2}")

                if entity1 == "Kay":
                    kay_ownership_found = True
                    print(f"    [FAIL] Kay ownership found (should NOT exist)")
                elif entity1 == "Re":
                    re_ownership_found = True
                    print(f"    [OK] Re ownership (correct)")

    assert not kay_ownership_found, "FAILED: Kay ownership should NOT be created"
    assert re_ownership_found, "FAILED: Re ownership should be created"
    print("\n[PASS] TEST 1: Kay's conversational reference did NOT create Kay ownership")

    # Test 2: Kay makes direct self-assertion
    print("\n\n[TEST 2] Kay says 'my eyes are gold' - SHOULD create Kay fact")
    print("-" * 80)

    user_input_2 = "What color are your eyes?"
    kay_response_2 = "My eyes are gold."

    extracted_facts_2 = memory._extract_facts(user_input_2, kay_response_2)

    print(f"\n[OK] Extracted {len(extracted_facts_2)} facts")

    # Check: Should have Kay eye color fact
    kay_eye_color_found = False

    for fact in extracted_facts_2:
        fact_text = fact.get("fact", "")
        perspective = fact.get("perspective", "")
        attributes = fact.get("attributes", [])

        print(f"\n  Fact: {fact_text}")
        print(f"  Perspective: {perspective}")

        # Check attributes
        for attr in attributes:
            entity = attr.get("entity")
            attr_name = attr.get("attribute")
            value = attr.get("value")

            if entity == "Kay" and attr_name == "eye_color":
                kay_eye_color_found = True
                print(f"  [OK] Kay.eye_color = {value} (correct)")

    assert kay_eye_color_found, "FAILED: Kay's self-assertion should create Kay fact"
    print("\n[PASS] TEST 2: Kay's direct self-assertion created Kay fact")

    # Test 3: Kay confused, mentions Re's entities as "my"
    print("\n\n[TEST 3] Kay confused says 'my cats' but they're Re's - should NOT create Kay ownership")
    print("-" * 80)

    user_input_3 = "My cats are Dice and Chrome."
    kay_response_3 = "Yeah, my cats - Dice and Chrome - are great!"

    extracted_facts_3 = memory._extract_facts(user_input_3, kay_response_3)

    print(f"\n[OK] Extracted {len(extracted_facts_3)} facts")

    # Check: Should NOT have Kay ownership
    kay_owns_dice = False
    kay_owns_chrome = False
    re_owns_dice = False
    re_owns_chrome = False

    for fact in extracted_facts_3:
        fact_text = fact.get("fact", "")
        perspective = fact.get("perspective", "")
        relationships = fact.get("relationships", [])

        print(f"\n  Fact: {fact_text}")
        print(f"  Perspective: {perspective}")

        for rel in relationships:
            entity1 = rel.get("entity1")
            relation = rel.get("relation")
            entity2 = rel.get("entity2")

            if relation == "owns":
                print(f"  Relationship: {entity1} owns {entity2}")

                if entity1 == "Kay" and entity2 == "Dice":
                    kay_owns_dice = True
                    print(f"    [FAIL] Kay owns Dice (should NOT exist)")
                elif entity1 == "Kay" and entity2 == "Chrome":
                    kay_owns_chrome = True
                    print(f"    [FAIL] Kay owns Chrome (should NOT exist)")
                elif entity1 == "Re" and entity2 == "Dice":
                    re_owns_dice = True
                    print(f"    [OK] Re owns Dice (correct)")
                elif entity1 == "Re" and entity2 == "Chrome":
                    re_owns_chrome = True
                    print(f"    [OK] Re owns Chrome (correct)")

    assert not kay_owns_dice, "FAILED: Kay should NOT own Dice"
    assert not kay_owns_chrome, "FAILED: Kay should NOT own Chrome"
    assert re_owns_dice, "FAILED: Re should own Dice"
    assert re_owns_chrome, "FAILED: Re should own Chrome"
    print("\n[PASS] TEST 3: Kay's confused statement did NOT create Kay ownership")

    # Final summary
    print("\n" + "=" * 80)
    print("ALL EXTRACTION TESTS PASSED [PASS]")
    print("=" * 80)
    print("\nResults:")
    print("- Kay's conversational references ('your cats') do NOT create Kay-facts")
    print("- Kay's direct self-assertions ('my eyes are gold') DO create Kay-facts")
    print("- Kay's confused statements ('my cats' when they're Re's) do NOT create Kay ownership")
    print("\nConclusion:")
    print("The extraction logic correctly distinguishes between:")
    print("1. Conversational references (don't extract)")
    print("2. Direct self-assertions (do extract)")
    print("3. Confused echoing (don't extract)")


if __name__ == "__main__":
    test_extraction_conversational_references()
