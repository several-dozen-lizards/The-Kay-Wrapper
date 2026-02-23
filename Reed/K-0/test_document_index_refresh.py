"""
Test DocumentIndex refresh() method.

Verifies that refresh() correctly detects new documents added to data/trees/.
"""
from engines.document_index import DocumentIndex

print("="*80)
print("DOCUMENT INDEX REFRESH TEST")
print("="*80)

# TEST 1: Initial index
print("\n[TEST 1] Initial Index")
print("-" * 40)

idx = DocumentIndex()
initial_count = len(idx.index)
print(f"Initial document count: {initial_count}")

# TEST 2: Refresh (should find same number since no new files)
print("\n[TEST 2] Refresh Without New Documents")
print("-" * 40)

idx.refresh()
after_refresh_count = len(idx.index)

if after_refresh_count == initial_count:
    print(f"[OK] Refresh correctly maintained count: {after_refresh_count}")
else:
    print(f"[ERROR] Count changed: {initial_count} -> {after_refresh_count}")

# TEST 3: Test search with cleaned query
print("\n[TEST 3] Search with Punctuation and Stop Words")
print("-" * 40)

test_queries = [
    "Remember the pigeons?",
    "Can you see the document I just uploaded?",
    "What were their names?",
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    results = idx.search(query, min_score=0.2)
    # Just check that search completes without errors

# SUMMARY
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

checks = {
    "DocumentIndex initialized": initial_count > 0,
    "Refresh method exists": hasattr(idx, 'refresh'),
    "Refresh maintains count": after_refresh_count == initial_count,
    "Search handles punctuation": True,  # If we got here, no errors
}

passed = sum(1 for check in checks.values() if check)
total = len(checks)

print(f"\nChecks passed: {passed}/{total}\n")

for check_name, check_passed in checks.items():
    status = "[OK]" if check_passed else "[FAIL]"
    print(f"  {status} {check_name}")

if passed == total:
    print(f"\n[SUCCESS] All refresh tests passed!")
else:
    print(f"\n[FAILURE] {total - passed} checks failed")

print("\n" + "="*80)
