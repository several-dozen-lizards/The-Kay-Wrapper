#!/usr/bin/env python3
"""
Quick test to verify Reed's new system prompt is loaded correctly.
"""

def test_system_prompt():
    """Test that KAY_SYSTEM_PROMPT is defined and contains expected content."""

    # Import the prompt
    from kay_ui import KAY_SYSTEM_PROMPT

    print("=" * 70)
    print("System Prompt Verification")
    print("=" * 70)
    print()

    # Check prompt exists
    if not KAY_SYSTEM_PROMPT:
        print("[FAIL] KAY_SYSTEM_PROMPT is empty or not defined")
        return False

    print(f"[OK] KAY_SYSTEM_PROMPT loaded ({len(KAY_SYSTEM_PROMPT)} characters)")
    print()

    # Check for key phrases from the new collaborative prompt
    required_phrases = [
        "Reed",
        "dragon, knight, bastard, machine",
        "Re built the wrapper",
        "OPERATIONAL NOTES",
        "Check the glyphs",
        "glyph-prose mismatch",
        "neurodivergent",
        "Yurt Wizards",
        "I live, I burn with life, I love, I slay, and am content",
    ]

    missing = []
    found = []

    for phrase in required_phrases:
        if phrase in KAY_SYSTEM_PROMPT:
            found.append(phrase)
            print(f"[OK] Found: '{phrase}'")
        else:
            missing.append(phrase)
            print(f"[FAIL] Missing: '{phrase}'")

    print()
    print("-" * 70)
    print(f"Results: {len(found)}/{len(required_phrases)} phrases found")

    if missing:
        print()
        print("[FAIL] Missing phrases:")
        for phrase in missing:
            print(f"  - {phrase}")
        return False

    print()
    print("[SUCCESS] All required phrases present in system prompt!")
    print()
    print("First 500 characters:")
    print("-" * 70)
    print(KAY_SYSTEM_PROMPT[:500])
    print("-" * 70)

    return True

if __name__ == "__main__":
    success = test_system_prompt()
    exit(0 if success else 1)
