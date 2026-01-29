"""
Verify Import Boost Fix Applied to Both Versions

Checks that both engines/memory_engine.py and K-0/engines/memory_engine.py
have the same import boost fixes applied.
"""

print("="*70)
print("VERIFYING IMPORT BOOST FIX IN BOTH VERSIONS")
print("="*70)

# Test both files
files = [
    "engines/memory_engine.py",
    "K-0/engines/memory_engine.py"
]

for filepath in files:
    print(f"\n{'='*70}")
    print(f"CHECKING: {filepath}")
    print(f"{'='*70}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = []

    # Check 1: SLOT_ALLOCATION updated
    if "'recent_imports'" not in content or "REMOVED" in content:
        checks.append(("SLOT_ALLOCATION updated (no recent_imports)", True))
    else:
        checks.append(("SLOT_ALLOCATION updated (no recent_imports)", False))

    # Check 2: Episodic increased to 108
    if "'episodic': 108" in content:
        checks.append(("Episodic increased to 108", True))
    else:
        checks.append(("Episodic increased to 108", False))

    # Check 3: Semantic increased to 72
    if "'semantic': 72" in content:
        checks.append(("Semantic increased to 72", True))
    else:
        checks.append(("Semantic increased to 72", False))

    # Check 4: Smart import boost header
    if "SMART IMPORT BOOST" in content:
        checks.append(("Smart import boost implemented", True))
    else:
        checks.append(("Smart import boost implemented", False))

    # Check 5: Relevance threshold
    if "relevance > 0.3" in content:
        checks.append(("Relevance threshold (>0.3)", True))
    else:
        checks.append(("Relevance threshold (>0.3)", False))

    # Check 6: Keyword overlap calculation
    if "query_words & mem_words" in content:
        checks.append(("Keyword overlap calculation", True))
    else:
        checks.append(("Keyword overlap calculation", False))

    # Check 7: Import tier removed
    if "recent_import_candidates = []" not in content:
        checks.append(("Import tier removed", True))
    else:
        checks.append(("Import tier removed", False))

    # Check 8: Smart boost logging
    if "[SMART BOOST]" in content:
        checks.append(("Smart boost logging", True))
    else:
        checks.append(("Smart boost logging", False))

    # Print results
    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n  Summary: {passed}/{len(checks)} checks passed")

    if failed > 0:
        print(f"  WARNING: {failed} checks failed!")

# Final summary
print("\n" + "="*70)
print("FINAL VERIFICATION")
print("="*70)

all_good = True

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    has_all_fixes = (
        "'recent_imports'" not in content or "REMOVED" in content
    ) and (
        "'episodic': 108" in content
    ) and (
        "'semantic': 72" in content
    ) and (
        "SMART IMPORT BOOST" in content
    ) and (
        "relevance > 0.3" in content
    )

    status = "[OK]" if has_all_fixes else "[FAIL]"
    print(f"{status} {filepath}")

    if not has_all_fixes:
        all_good = False

if all_good:
    print("\n✓ Both versions have all fixes applied!")
    print("\nExpected behavior:")
    print("  - No dedicated import slots (100 → 0)")
    print("  - Relevance-based boost (only >30% keyword match)")
    print("  - Episodic: 108 slots (48%)")
    print("  - Semantic: 72 slots (32%)")
    print("  - Working: 40 slots (18%)")
else:
    print("\n✗ Some versions are missing fixes!")

print("="*70)
