"""
Test script for three-tier memory system.
Verifies that lists are stored and retrieved correctly.
"""

from engines.memory_engine import MemoryEngine
from agent_state import AgentState

def test_list_storage_and_retrieval():
    """Test that lists of entities are properly stored and retrieved."""

    print("\n=== TEST: Three-Tier Memory Storage ===\n")

    # Initialize
    state = AgentState()
    memory = MemoryEngine(state.memory, file_path="memory/test_memories.json")
    state.memory = memory

    # === STEP 1: Store a list ===
    print("STEP 1: Storing list of 5 cats + 1 dog")
    user_input = "My cats are named Dice, Chrome, Luna, Rainbowbelle, and Frodo. My dog is Saga."
    response = "That's quite a menagerie! I love the name Rainbowbelle."

    memory.extract_and_store_user_facts(state, user_input)
    memory.encode(state, user_input, response, emotion_tags=["joy"])

    # Verify storage
    full_turns = [m for m in memory.memories if m.get("type") == "full_turn"]
    extracted_facts = [m for m in memory.memories if m.get("type") == "extracted_fact"]
    glyph_summaries = [m for m in memory.memories if m.get("type") == "glyph_summary"]

    print(f"\nOK Stored:")
    print(f"  - {len(full_turns)} full_turn(s)")
    print(f"  - {len(extracted_facts)} extracted_fact(s)")
    print(f"  - {len(glyph_summaries)} glyph_summary(ies)")

    if full_turns:
        ft = full_turns[-1]
        print(f"\nFull turn details:")
        print(f"  - Entities: {ft.get('entities', [])}")
        print(f"  - Is list: {ft.get('is_list', False)}")
        print(f"  - Importance: {ft.get('importance_score', 0)}")
        print(f"  - User input length: {len(ft.get('user_input', ''))}")

    # === STEP 2: Retrieve with list query ===
    print("\n\nSTEP 2: Retrieving with list query")
    list_query = "What are my cats' names?"

    memory.recall(state, list_query)
    retrieved = state.last_recalled_memories

    print(f"\nOK Retrieved {len(retrieved)} memories for query: '{list_query}'")

    # Check what was retrieved
    retrieved_full_turns = [m for m in retrieved if m.get("type") == "full_turn"]
    retrieved_facts = [m for m in retrieved if m.get("type") == "extracted_fact"]

    print(f"\nRetrieved breakdown:")
    print(f"  - {len(retrieved_full_turns)} full_turn(s)")
    print(f"  - {len(retrieved_facts)} extracted_fact(s)")

    # Verify full turn is prioritized
    if retrieved and retrieved[0].get("type") == "full_turn":
        print("\n[SUCCESS] Full turn with complete list was prioritized!")
        entities = retrieved[0].get("entities", [])
        print(f"   Retrieved entities: {entities}")

        expected_entities = ["Dice", "Chrome", "Luna", "Rainbowbelle", "Frodo", "Saga"]
        missing = set(expected_entities) - set(entities)

        if not missing:
            print("   [OK] All entities present!")
        else:
            print(f"   [FAIL] Missing entities: {missing}")
    else:
        print("\n[FAILURE] Full turn was not prioritized")
        print(f"   Top result type: {retrieved[0].get('type') if retrieved else 'none'}")

    # === STEP 3: Retrieve with specific query ===
    print("\n\nSTEP 3: Retrieving with specific query")
    specific_query = "Tell me about Chrome"

    memory.recall(state, specific_query)
    retrieved2 = state.last_recalled_memories

    print(f"\nOK Retrieved {len(retrieved2)} memories for query: '{specific_query}'")

    if retrieved2:
        print(f"   Top result type: {retrieved2[0].get('type')}")
        print(f"   Top result entities: {retrieved2[0].get('entities', [])}")

    print("\n=== TEST COMPLETE ===\n")

if __name__ == "__main__":
    test_list_storage_and_retrieval()
