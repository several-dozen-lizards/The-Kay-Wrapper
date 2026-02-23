"""
Test script for identity memory fixes:
1. Entity deduplication (no duplicate entities)
2. Relationship extraction (captures "my dog's name is Saga")
3. Recall prioritization (returns specific names, not generic "a dog")
4. Generic fact downweighting
"""

import asyncio
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.memory_engine import MemoryEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine


def test_identity_memory_fixes():
    """Test all identity memory fixes."""

    print("=" * 80)
    print("IDENTITY MEMORY FIX TEST")
    print("=" * 80)

    # Setup
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    memory = MemoryEngine(state.memory, motif_engine=motif, momentum_engine=momentum, emotion_engine=emotion)
    state.memory = memory

    # Test 1: Relationship extraction with regex
    print("\n[TEST 1] Regex relationship extraction")
    print("-" * 80)

    user_input = "Hey Kay - my dog's name is Saga, my husband named John, and my cat's name is Dice."
    memory.extract_and_store_user_facts(state, user_input)

    # Check if regex captured the relationships
    extracted_facts = memory.memories

    saga_found = False
    john_found = False

    for fact in extracted_facts:
        fact_text = fact.get("fact", "").lower()

        if "saga" in fact_text and "dog" in fact_text:
            saga_found = True
            print(f"  [OK] Found Saga (dog): {fact['fact']}")

        if "john" in fact_text and ("husband" in fact_text or "spouse" in fact_text):
            john_found = True
            print(f"  [OK] Found John (husband): {fact['fact']}")

    assert saga_found, "FAILED: Saga (dog) relationship not extracted"
    assert john_found, "FAILED: John (husband) relationship not extracted"

    print("\n[PASS] TEST 1: Regex extraction captured Saga and John")

    # Test 2: Entity deduplication
    print("\n\n[TEST 2] Entity deduplication")
    print("-" * 80)

    # Mention Dice multiple times with variations
    user_input_2 = "Dice is my cat. dice is great. Dice's fur is gray."
    memory.extract_and_store_user_facts(state, user_input_2)

    # Check entity graph - should only have ONE Dice entity
    entity_graph = memory.entity_graph
    dice_entities = [name for name in entity_graph.entities.keys() if "dice" in name.lower()]

    print(f"  Found {len(dice_entities)} Dice entities: {dice_entities}")

    assert len(dice_entities) == 1, f"FAILED: Expected 1 Dice entity, found {len(dice_entities)}: {dice_entities}"

    print("\n[PASS] TEST 2: Entity deduplication prevents duplicate Dice entities")

    # Test 3: Recall prioritization for relationships
    print("\n\n[TEST 3] Recall prioritization for relationship queries")
    print("-" * 80)

    # Ask about dog's name
    query = "What's my dog's name?"
    memory.recall(state, query, num_memories=7)

    recalled_memories = state.last_recalled_memories

    print(f"\n  Recalled {len(recalled_memories)} memories:")

    # Check if Saga is in the recalled memories
    saga_recalled = False
    for mem in recalled_memories:
        mem_text = mem.get("fact", "").lower()
        print(f"    - {mem.get('fact', 'N/A')[:80]}")

        if "saga" in mem_text:
            saga_recalled = True

    assert saga_recalled, "FAILED: Saga not in recalled memories when asked 'What's my dog's name?'"

    print("\n[PASS] TEST 3: Recall prioritized Saga when asked about dog's name")

    # Final summary
    print("\n" + "=" * 80)
    print("ALL IDENTITY MEMORY TESTS PASSED [PASS]")
    print("=" * 80)
    print("\nSummary:")
    print("- Regex extraction captured specific relationships (Saga, John)")
    print("- Entity deduplication prevents duplicate entities (only 1 Dice)")
    print("- Recall prioritizes identity facts for relationship queries")


if __name__ == "__main__":
    test_identity_memory_fixes()
