#!/usr/bin/env python3
"""
Test to verify memory compression fix.
Ensures all retrieved memories are presented in the prompt, not just 30 bullets.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrations.llm_integration import build_prompt_from_context

def test_no_compression():
    """Test that all memories are rendered without compression."""

    # Create mock context with 495 memories (matching the reported retrieval count)
    memories = []

    # Add 449 identity facts (as reported in logs)
    for i in range(449):
        memories.append({
            "fact": f"Identity fact {i}: Re's detail number {i}",
            "perspective": "user",
            "is_identity": True,
            "topic": "identity"
        })

    # Add 46 non-identity facts to reach 495 total
    for i in range(46):
        memories.append({
            "fact": f"Non-identity fact {i}: General detail number {i}",
            "perspective": "user",
            "is_identity": False,
            "topic": "general"
        })

    # Add one specific memory about Saga to test precision
    memories.append({
        "fact": "Saga is an orange rough collie",
        "perspective": "user",
        "is_identity": False,
        "topic": "pets"
    })

    context = {
        "user_input": "Tell me about Saga",
        "recalled_memories": memories,
        "emotional_state": {"cocktail": {}},
        "body": {},
        "consolidated_preferences": {},
        "preference_contradictions": [],
        "recent_context": [],
        "momentum_notes": [],
        "meta_awareness_notes": [],
        "entity_contradictions": []
    }

    # Build prompt
    prompt = build_prompt_from_context(context, affect_level=3.5)

    # Count bullet points in the prompt
    bullet_count = prompt.count("\n- ") + prompt.count("\n  - ")

    # Count memories in prompt by looking for specific facts
    identity_count = sum(1 for i in range(449) if f"Identity fact {i}" in prompt)
    general_count = sum(1 for i in range(46) if f"Non-identity fact {i}" in prompt)
    saga_in_prompt = "orange rough collie" in prompt

    print("=" * 70)
    print("MEMORY COMPRESSION FIX TEST")
    print("=" * 70)
    print(f"Total memories provided:     496 (449 identity + 46 general + 1 Saga)")
    print(f"Bullet points in prompt:     {bullet_count}")
    print(f"Identity facts in prompt:    {identity_count} / 449")
    print(f"General facts in prompt:     {general_count} / 46")
    print(f"Saga detail in prompt:       {'YES' if saga_in_prompt else 'NO'}")
    print()

    # Check if the fix worked
    if bullet_count >= 490:  # Allow for some formatting differences
        print("[SUCCESS] All memories rendered without compression!")
        print(f"  Expected ~496 bullets, got {bullet_count}")
    else:
        print("[FAILURE] Memories still being compressed!")
        print(f"  Expected ~496 bullets, only got {bullet_count}")
        return False

    if saga_in_prompt:
        print("[SUCCESS] Saga's precise detail (orange rough collie) in prompt!")
    else:
        print("[FAILURE] Saga's detail missing from prompt!")
        return False

    print()
    print("=" * 70)
    print("Prompt excerpt (first 500 chars):")
    print("=" * 70)
    print(prompt[:500])
    print("...")
    print()
    print("=" * 70)
    print("Prompt excerpt showing Saga:")
    print("=" * 70)
    saga_index = prompt.find("orange rough collie")
    if saga_index != -1:
        print(prompt[max(0, saga_index - 100):saga_index + 100])
    print()

    return True

if __name__ == "__main__":
    success = test_no_compression()
    sys.exit(0 if success else 1)
