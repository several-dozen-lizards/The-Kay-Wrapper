"""
Integration test for ownership verification with multiple entities.

Scenario: User has 5 cats, and Kay gets confused about ownership.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.memory_engine import MemoryEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine


def test_multi_entity_ownership():
    """Test ownership verification with multiple entities (5 cats)."""

    print("=" * 80)
    print("MULTI-ENTITY OWNERSHIP VERIFICATION TEST")
    print("Scenario: User has 5 cats, Kay gets confused")
    print("=" * 80)

    # Setup
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    memory = MemoryEngine(state.memory, motif_engine=motif, momentum_engine=momentum, emotion_engine=emotion)
    state.memory = memory

    print("\n[SCENARIO] User states: 'I have 5 cats: Dice, Chrome, Luna, Rainbowbelle, and Frodo'")
    print("-" * 80)

    # User explicitly states ownership of multiple cats
    user_input = "I have 5 cats: Dice, Chrome, Luna, Rainbowbelle, and Frodo."
    memory.extract_and_store_user_facts(state, user_input)

    # Check identity layer for all cats
    cat_names = ["Dice", "Chrome", "Luna", "Rainbowbelle", "Frodo"]

    print("\n[OK] Checking identity layer for cat ownership:")
    for cat in cat_names:
        ownership = memory.identity.check_ownership(cat)
        print(f"  {cat}: owner={ownership['owner']}, confidence={ownership['confidence']}")
        assert ownership['owner'] == 'Re', f"FAILED: {cat} should be owned by Re"

    print("\n[PASS] All 5 cats correctly owned by Re in identity layer")

    # Simulate Kay's confused response (claiming multiple cats as his own)
    print("\n[SCENARIO] Kay confused: 'Yeah, my cats - Dice, Chrome, and Luna are great!'")
    print("-" * 80)

    kay_response = "Yeah, my cats - Dice, Chrome, and Luna are great!"
    extracted_facts = memory._extract_facts(user_input, kay_response)

    print(f"\n[OK] Extracted {len(extracted_facts)} facts from Kay's response")

    # Count how many ownership conflicts were detected and blocked
    blocked_count = 0
    for fact in extracted_facts:
        if fact.get("ownership_conflict"):
            blocked_count += 1
            print(f"\n  [BLOCKED] Ownership conflict detected:")
            print(f"    Fact: {fact.get('fact', 'N/A')[:60]}...")
            print(f"    Confusion: {fact.get('ownership_confusion', 'N/A')[:80]}...")

    print(f"\n[OK] {blocked_count} ownership conflicts detected and blocked")

    # Verify entity graph - should ONLY have "Re owns X" relationships
    print("\n[VERIFICATION] Checking entity graph for cat ownership relationships:")
    print("-" * 80)

    for cat in cat_names:
        relationships = memory.entity_graph.get_entity_relationships(cat)
        owners = [rel.entity1 for rel in relationships if rel.relation_type == "owns"]

        print(f"\n  {cat}:")
        if owners:
            for owner in owners:
                print(f"    - {owner} owns {cat}")
                assert owner == "Re", f"FAILED: Only Re should own {cat}, found {owner}"
                assert "Kay" not in owners, f"FAILED: Kay should NOT own {cat}"
        else:
            print(f"    - No ownership relationships (may be OK if extraction didn't create explicit relationship)")

    print("\n[PASS] No false 'Kay owns X' relationships created for any cat")

    # Final summary
    print("\n" + "=" * 80)
    print("MULTI-ENTITY TEST PASSED [PASS]")
    print("=" * 80)
    print("\nResults:")
    print(f"- User stated ownership of {len(cat_names)} cats")
    print(f"- All {len(cat_names)} cats correctly owned by Re in identity layer")
    print(f"- Kay's confused claims about {blocked_count} cats were blocked")
    print("- Entity graph contains NO false 'Kay owns X' relationships")
    print("\nConclusion:")
    print("The ownership verification system successfully prevents Kay from creating")
    print("false ownership relationships even when confused about multiple entities.")


if __name__ == "__main__":
    test_multi_entity_ownership()
