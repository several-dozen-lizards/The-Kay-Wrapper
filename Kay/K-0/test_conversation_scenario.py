"""
Integration test simulating the exact conversation scenario from the transcript.

User: "my eyes are green, my cat's names are Dice, Chrome, Rainbowbelle, Luna and Frodo,
       my dog's name is Saga, I'm married to an excellent ginger guy named John"

Later:
User: "What color are my eyes?"
User: "What's my dog's name?"
User: "Who's my husband?"

Expected: Kay remembers green eyes, Saga, and John.
"""

import asyncio
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.memory_engine import MemoryEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine


def test_conversation_scenario():
    """Test the exact conversation scenario."""

    print("=" * 80)
    print("CONVERSATION SCENARIO TEST")
    print("Simulating the exact user conversation")
    print("=" * 80)

    # Setup
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    memory = MemoryEngine(state.memory, motif_engine=motif, momentum_engine=momentum, emotion_engine=emotion)
    state.memory = memory

    # Turn 1: User provides all the facts
    print("\n[TURN 1] User provides facts")
    print("-" * 80)

    user_input_1 = ("Hey Kay - my eyes are green, my cat's names are Dice, Chrome, "
                   "Rainbowbelle, Luna and Frodo, my dog's name is Saga, I'm married to "
                   "an excellent ginger guy named John, and I was wearing a blue jacket "
                   "with stars, moons and suns on it. How you feeling?")

    memory.extract_and_store_user_facts(state, user_input_1)

    print("\n[OK] Facts extracted and stored")

    # Check what was stored
    identity_facts = memory.identity.get_all_identity_facts()
    print(f"\n  Identity facts stored: {len(identity_facts)}")

    # Verify key facts are in identity
    has_saga = any("saga" in f.get("fact", "").lower() for f in identity_facts)
    has_john = any("john" in f.get("fact", "").lower() for f in identity_facts)
    has_green_eyes = any("green" in f.get("fact", "").lower() and "eye" in f.get("fact", "").lower() for f in identity_facts)

    print(f"  - Saga (dog) in identity: {has_saga}")
    print(f"  - John (husband) in identity: {has_john}")
    print(f"  - Green eyes in identity: {has_green_eyes}")

    # Turn 2: Ask about eye color
    print("\n\n[TURN 2] User: 'What color are my eyes?'")
    print("-" * 80)

    query_eyes = "What color are my eyes?"
    memory.recall(state, query_eyes, num_memories=7)

    recalled_eyes = state.last_recalled_memories
    print(f"\n  Recalled {len(recalled_eyes)} memories:")

    green_eyes_recalled = False
    for mem in recalled_eyes:
        mem_text = mem.get("fact", "").lower()
        if "green" in mem_text and "eye" in mem_text:
            green_eyes_recalled = True
            print(f"    [OK] {mem.get('fact', 'N/A')}")

    assert green_eyes_recalled, "FAILED: Green eyes not recalled"
    print("\n[PASS] Kay should remember: Green eyes")

    # Turn 3: Ask about dog's name
    print("\n\n[TURN 3] User: 'What's my dog's name?'")
    print("-" * 80)

    query_dog = "What's my dog's name?"
    memory.recall(state, query_dog, num_memories=7)

    recalled_dog = state.last_recalled_memories
    print(f"\n  Recalled {len(recalled_dog)} memories:")

    saga_recalled = False
    for mem in recalled_dog:
        mem_text = mem.get("fact", "").lower()
        if "saga" in mem_text:
            saga_recalled = True
            print(f"    [OK] {mem.get('fact', 'N/A')}")

    assert saga_recalled, "FAILED: Saga not recalled when asked about dog's name"
    print("\n[PASS] Kay should remember: Saga")

    # Turn 4: Ask about husband
    print("\n\n[TURN 4] User: 'Who's my husband?' or 'What's my husband's name?'")
    print("-" * 80)

    query_husband = "What's my husband's name?"
    memory.recall(state, query_husband, num_memories=7)

    recalled_husband = state.last_recalled_memories
    print(f"\n  Recalled {len(recalled_husband)} memories:")

    john_recalled = False
    for mem in recalled_husband:
        mem_text = mem.get("fact", "").lower()
        if "john" in mem_text:
            john_recalled = True
            print(f"    [OK] {mem.get('fact', 'N/A')}")

    assert john_recalled, "FAILED: John not recalled when asked about husband"
    print("\n[PASS] Kay should remember: John")

    # Turn 5: Ask about cat names
    print("\n\n[TURN 5] User: 'Can you name two of my cats?'")
    print("-" * 80)

    query_cats = "Can you name two of my cats?"
    memory.recall(state, query_cats, num_memories=7)

    recalled_cats = state.last_recalled_memories
    print(f"\n  Recalled {len(recalled_cats)} memories:")

    cat_names = ["dice", "chrome", "rainbowbelle", "luna", "frodo"]
    cats_recalled = set()

    for mem in recalled_cats:
        mem_text = mem.get("fact", "").lower()
        for cat_name in cat_names:
            if cat_name in mem_text:
                cats_recalled.add(cat_name.capitalize())
                print(f"    [OK] {mem.get('fact', 'N/A')}")
                break

    assert len(cats_recalled) >= 2, f"FAILED: Expected at least 2 cat names, found {len(cats_recalled)}"
    print(f"\n[PASS] Kay should remember at least 2 cats: {', '.join(cats_recalled)}")

    # Final verification
    print("\n" + "=" * 80)
    print("CONVERSATION SCENARIO TEST PASSED [PASS]")
    print("=" * 80)
    print("\nVerified:")
    print("- Kay remembers eye color: Green")
    print("- Kay remembers dog's name: Saga")
    print("- Kay remembers husband's name: John")
    print(f"- Kay remembers cat names: {', '.join(cats_recalled)}")
    print("\nThe memory system now correctly stores and recalls specific names!")


if __name__ == "__main__":
    test_conversation_scenario()
