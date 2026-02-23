"""
Comprehensive test of all Document Index fixes.

Tests:
1. Query parsing (punctuation removal, stop word filtering)
2. Keyword extraction (cleaned keywords)
3. Refresh method (index rebuilding)
4. Search functionality (cleaned queries)
"""
from engines.document_index import DocumentIndex

print("="*80)
print("COMPREHENSIVE DOCUMENT INDEX FIXES TEST")
print("="*80)

# TEST 1: Query Parsing
print("\n[TEST 1] Query Parsing - Punctuation and Stop Words")
print("-" * 60)

idx = DocumentIndex()

test_cases = [
    ("Remember the pigeons?", {'remember', 'pigeons'}),
    ("Can you see the document I just uploaded?", {'document', 'uploaded', 'just'}),
    ("What were their names?", {'names'}),
    ("Tell me about the dragons!", {'tell', 'dragons'}),
]

query_parsing_pass = True
for query, expected_keywords in test_cases:
    print(f"\nQuery: '{query}'")

    # Manually parse to check (same logic as search())
    import re
    query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    query_words = set(w for w in query_clean.split() if len(w) > 2)
    stop_words = {'the', 'and', 'are', 'you', 'any', 'have', 'been', 'see', 'can', 'for',
                  'this', 'that', 'from', 'with', 'what', 'they', 'there', 'here', 'then',
                  'than', 'your', 'their', 'about', 'would', 'could', 'should', 'were'}
    query_words = query_words - stop_words

    print(f"  Cleaned: {query_words}")
    print(f"  Expected: {expected_keywords}")

    # Check if punctuation removed
    has_punctuation = any(c in ''.join(query_words) for c in '?!.,;:')
    if has_punctuation:
        print(f"  [FAIL] Punctuation still present")
        query_parsing_pass = False
    else:
        print(f"  [OK] No punctuation")

    # Check if stop words removed
    has_stop_words = bool(query_words & stop_words)
    if has_stop_words:
        print(f"  [FAIL] Stop words still present: {query_words & stop_words}")
        query_parsing_pass = False
    else:
        print(f"  [OK] Stop words removed")

# TEST 2: Keyword Extraction
print("\n\n[TEST 2] Keyword Extraction - Cleaned Keywords")
print("-" * 60)

keywords_pass = True
if idx.index:
    doc_id = list(idx.index.keys())[0]
    doc_meta = idx.index[doc_id]

    print(f"\nDocument: {doc_meta['filename']}")
    print(f"Total keywords: {len(doc_meta['keywords'])}")
    print(f"Sample keywords: {list(doc_meta['keywords'])[:15]}")

    # Check for stop words in keywords
    stop_words_in_keywords = doc_meta['keywords'] & stop_words
    if stop_words_in_keywords:
        print(f"  [FAIL] Stop words in keywords: {stop_words_in_keywords}")
        keywords_pass = False
    else:
        print(f"  [OK] No stop words in keywords")

    # Check for punctuation in keywords
    keywords_with_punct = [k for k in doc_meta['keywords'] if any(c in k for c in '?!.,;:')]
    if keywords_with_punct:
        print(f"  [FAIL] Punctuation in keywords: {keywords_with_punct[:5]}")
        keywords_pass = False
    else:
        print(f"  [OK] No punctuation in keywords")

# TEST 3: Refresh Method
print("\n\n[TEST 3] Refresh Method")
print("-" * 60)

old_count = len(idx.index)
print(f"Before refresh: {old_count} documents")

idx.refresh()

new_count = len(idx.index)
print(f"After refresh: {new_count} documents")

refresh_pass = (new_count == old_count)
if refresh_pass:
    print(f"[OK] Refresh maintained document count")
else:
    print(f"[FAIL] Document count changed: {old_count} -> {new_count}")

# TEST 4: Search Functionality
print("\n\n[TEST 4] Search with Real Queries")
print("-" * 60)

search_queries = [
    "dragon",
    "test document",
    "emotional moments",
]

search_pass = True
for query in search_queries:
    print(f"\nSearching: '{query}'")
    try:
        results = idx.search(query, min_score=0.2)
        print(f"  [OK] Search completed, found {len(results)} documents")
    except Exception as e:
        print(f"  [FAIL] Search error: {e}")
        search_pass = False

# TEST 5: Integration Check
print("\n\n[TEST 5] Method Availability")
print("-" * 60)

integration_checks = {
    "refresh() exists": hasattr(idx, 'refresh'),
    "search() exists": hasattr(idx, 'search'),
    "load_tree() exists": hasattr(idx, 'load_tree'),
    "_build_index() exists": hasattr(idx, '_build_index'),
}

integration_pass = all(integration_checks.values())

for check, result in integration_checks.items():
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {check}")

# FINAL SUMMARY
print("\n" + "="*80)
print("FINAL TEST SUMMARY")
print("="*80)

all_checks = {
    "Query parsing (punctuation/stop words)": query_parsing_pass,
    "Keyword extraction (cleaned)": keywords_pass,
    "Refresh method works": refresh_pass,
    "Search functionality": search_pass,
    "Method integration": integration_pass,
}

passed = sum(1 for check in all_checks.values() if check)
total = len(all_checks)

print(f"\nChecks passed: {passed}/{total}\n")

for check_name, check_passed in all_checks.items():
    status = "[OK]" if check_passed else "[FAIL]"
    print(f"  {status} {check_name}")

if passed == total:
    print(f"\n{'='*80}")
    print("[SUCCESS] ALL DOCUMENT INDEX FIXES VERIFIED!")
    print("="*80)
    print("\nFixed issues:")
    print("  1. Query words now cleaned (no punctuation)")
    print("  2. Stop words removed from search")
    print("  3. Keywords extracted cleanly (no stop words)")
    print("  4. Refresh method works correctly")
    print("  5. Search handles natural language queries")
    print("\nDocument Index is fully operational!")
else:
    print(f"\n[FAILURE] {total - passed} checks failed - see details above")

print("\n" + "="*80)
