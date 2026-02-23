"""
Test the exact scenario: "Tell Kay 'my eyes are green' and 5 turns later ask 'what color are my eyes?'"
"""

import sys
sys.path.insert(0, 'engines')

from memory_simple import SimplifiedMemoryEngine

def test_eye_color_recall():
    """
    User requirement: Tell Kay "my eyes are green" and 5 turns later ask "what color are my eyes?"
    Expected: Kay should recall it immediately.
    """
    print("\n" + "="*70)
    print("TEST: Eye Color Recall After 5 Turns")
    print("="*70 + "\n")

    mem = SimplifiedMemoryEngine(persist_dir="memory/test_simple")

    # Turn 1: User states eye color
    print("Turn 1: User states eye color")
    mem.store_turn(
        user_input="My eyes are green",
        reed_response="That's beautiful! Green eyes are quite striking"
    )

    # Turns 2-5: Other conversation
    print("\nTurns 2-5: Other conversation topics...")
    mem.store_turn("I like pizza", "Pizza is delicious!")
    mem.store_turn("My favorite color is blue", "Blue is a calming color")
    mem.store_turn("I work in tech", "Tech is an interesting field")
    mem.store_turn("I have a dog named Max", "Max sounds like a great companion")

    # Turn 6: User asks about eye color
    print("\nTurn 6: User asks about eye color")
    result = mem.recall("What color are my eyes?")

    print("\n" + "="*70)
    print("MEMORY CONTEXT FOR KAY:")
    print("="*70)
    formatted = mem.format_for_llm(result)
    print(formatted)

    print("\n" + "="*70)
    print("ANALYSIS:")
    print("="*70)

    # Check if eye color fact is present
    found_in_conversation = False
    found_in_facts = False

    for turn in result["recent_conversation"]:
        if "green" in turn["user"].lower():
            found_in_conversation = True
            print(f"✓ Eye color found in recent conversation (Turn {turn['turn']})")
            break

    for fact in result["relevant_facts"]:
        if "eyes are green" in fact["text"].lower():
            found_in_facts = True
            print(f"✓ Eye color found in semantic search: \"{fact['text']}\"")
            break

    if found_in_conversation or found_in_facts:
        print("\n✅ SUCCESS: Kay has access to eye color information!")
        print("   He can answer: 'Your eyes are green'")
    else:
        print("\n❌ FAILURE: Eye color not found in recall")

    return found_in_conversation or found_in_facts


if __name__ == "__main__":
    success = test_eye_color_recall()
    sys.exit(0 if success else 1)
