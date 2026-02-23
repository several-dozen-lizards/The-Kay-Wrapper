"""
Test Protected Import Logic

Verifies that imported memories bypass glyph pre-filter
"""

import json

def test_protection_logic():
    """Test the protection condition against actual memories."""

    # Load actual memories
    with open("memory/memories.json", "r", encoding="utf-8") as f:
        memories = json.load(f)

    # Find imported memories
    imported = [m for m in memories if m.get("is_imported")]

    print(f"Total memories: {len(memories)}")
    print(f"Imported memories: {len(imported)}")
    print()

    # Test protection logic
    protected_count = 0
    not_protected_count = 0

    for mem in imported:
        # Same logic as context_filter.py line 415
        is_protected = mem.get("protected") or (mem.get("is_imported") and mem.get("age", 999) < 3)

        if is_protected:
            protected_count += 1
        else:
            not_protected_count += 1

    print(f"[TEST] Protected: {protected_count}")
    print(f"[TEST] Not protected: {not_protected_count}")
    print()

    # Show sample
    if protected_count > 0:
        sample = next(m for m in imported if m.get("protected") or (m.get("is_imported") and m.get("age", 999) < 3))
        print("[TEST] Sample protected memory:")
        print(f"  Fact: {sample.get('fact', 'N/A')[:60]}...")
        print(f"  is_imported: {sample.get('is_imported')}")
        print(f"  protected: {sample.get('protected')}")
        print(f"  age: {sample.get('age')}")
        print()

    # Verify expected result
    if protected_count == len(imported):
        print("[PASS] All imported memories are protected!")
        return True
    else:
        print(f"[FAIL] Only {protected_count}/{len(imported)} imported memories are protected")

        # Show why some aren't protected
        not_protected = [m for m in imported if not (m.get("protected") or (m.get("is_imported") and m.get("age", 999) < 3))]
        if not_protected:
            sample = not_protected[0]
            print(f"\n[DEBUG] Sample unprotected memory:")
            print(f"  is_imported: {sample.get('is_imported')}")
            print(f"  protected: {sample.get('protected', 'MISSING')}")
            print(f"  age: {sample.get('age', 'MISSING')}")

        return False


if __name__ == "__main__":
    test_protection_logic()
