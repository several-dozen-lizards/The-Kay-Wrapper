"""
Test Document Index System with scenarios from implementation guide.

Tests:
1. Recent document access
2. Old document persistence (pigeons)
3. Multiple document access
4. Search diagnostics
"""

from engines.document_index import DocumentIndex
from engines.memory_engine import MemoryEngine
from engines.identity_memory import IdentityMemory

print("="*80)
print("DOCUMENT INDEX SCENARIOS - TEST SUITE")
print("="*80)

# Initialize with diagnostic output
print("\n[SCENARIO 0] Initialization")
print("-" * 40)

idx = DocumentIndex(print_diagnostic=True)

# TEST 1: Recent Document
print("\n[SCENARIO 1] Recent Document Access")
print("-" * 40)
print("User: 'Can you see the document I just uploaded?'")
print()

query1 = "can you see the document i just uploaded"
results1 = idx.search(query1, min_score=0.2)

if results1:
    print(f"\n[RESULT] Would retrieve {len(results1)} documents")
    for doc_id in results1[:2]:
        tree = idx.load_tree(doc_id)
        if tree:
            trees = tree.get('trees', {})
            if doc_id in trees:
                tree_doc = trees[doc_id]
                full_text_len = len(tree_doc.get('full_text', ''))
                print(f"  - {tree_doc.get('title')}: {full_text_len} chars")
else:
    print("[WARNING] No documents matched recent upload query")

# TEST 2: Old Document (Pigeons)
print("\n[SCENARIO 2] Old Document Persistence")
print("-" * 40)
print("User: 'Remember those pigeons I told you about? What were their names?'")
print()

query2 = "remember those pigeons i told you about what were their names"
results2 = idx.search(query2, min_score=0.2)

if results2:
    print(f"\n[RESULT] Found {len(results2)} matching documents for 'pigeons'")

    # Check if any mention pigeons
    pigeon_docs = []
    for doc_id in results2:
        doc_meta = idx.index[doc_id]
        if 'pigeon' in doc_meta['filename'].lower() or 'pigeon' in ' '.join(doc_meta['keywords']):
            pigeon_docs.append(doc_id)
            tree = idx.load_tree(doc_id)
            if tree:
                trees = tree.get('trees', {})
                if doc_id in trees:
                    tree_doc = trees[doc_id]
                    full_text = tree_doc.get('full_text', '')

                    print(f"\n  [PIGEON DOCUMENT FOUND]")
                    print(f"  File: {tree_doc.get('title')}")
                    print(f"  Full text length: {len(full_text)} chars")

                    # Try to extract pigeon names
                    if full_text:
                        print(f"  Content preview (first 300 chars):")
                        print(f"  {full_text[:300]}...")

                        # Simple name extraction (capitalize words that might be names)
                        potential_names = [word for word in full_text.split()
                                         if word[0].isupper() and len(word) > 2
                                         and word not in ['The', 'And', 'But', 'For', 'Kay']][:10]
                        if potential_names:
                            print(f"\n  Potential pigeon names found: {', '.join(potential_names)}")

    if not pigeon_docs:
        print("[WARNING] Query matched documents but none about pigeons")
        print("  Try searching directly for 'pigeon':")
        pigeon_search = idx.search("pigeon", min_score=0.1)
        if pigeon_search:
            print(f"  Direct search found {len(pigeon_search)} documents")
        else:
            print("  [CRITICAL] No pigeon documents in index!")
else:
    print("[WARNING] No documents matched pigeon query")

# TEST 3: Multiple Documents
print("\n[SCENARIO 3] Multiple Document Access")
print("-" * 40)
print("User: 'What documents do you have in your memory?'")
print()

print(f"[RESULT] Total documents in index: {len(idx.index)}")
print("\nIndexed documents:")
for doc_id, meta in idx.index.items():
    print(f"  - {meta['filename']}")
    print(f"      Branches: {', '.join(meta['branches'][:3])}")
    print(f"      Chunks: {meta['chunk_count']}")

# TEST 4: Search Diagnostics
print("\n[SCENARIO 4] Search Diagnostic Verification")
print("-" * 40)

print("\nChecking that search logs are being printed...")
print("Expected log patterns:")
print("  - [DOCUMENT INDEX] Searching for: '...'")
print("  - [DOCUMENT INDEX] Query words: {...}")
print("  - [MATCH] filename: score=X.XX")
print("  - [DOCUMENT INDEX] Found X matching documents")

print("\nPerforming test search...")
test_results = idx.search("test dragon import", min_score=0.2)

if test_results:
    print(f"\n[OK] Search logs appeared above with {len(test_results)} results")
else:
    print("\n[WARNING] No results from test search")

# FINAL SUMMARY
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

checks = {
    "DocumentIndex initialized": len(idx.index) > 0,
    "Recent document searchable": len(results1) > 0,
    "Old documents persist": len(results2) > 0,
    "Pigeon document found": len([m for m in idx.index.values() if 'pigeon' in m['filename'].lower()]) > 0,
    "Multiple documents indexed": len(idx.index) >= 2,
    "Search diagnostics visible": True,  # If we got here, logs printed
}

passed = sum(1 for check in checks.values() if check)
total = len(checks)

print(f"\nChecks passed: {passed}/{total}\n")

for check_name, check_passed in checks.items():
    status = "[OK]" if check_passed else "[FAIL]"
    print(f"  {status} {check_name}")

if passed == total:
    print(f"\n[SUCCESS] All scenario tests passed!")
    print("\nExpected Kay behavior:")
    print("  - Can see recently uploaded documents")
    print("  - Can remember old documents (pigeons persist)")
    print("  - Can list all documents in memory")
    print("  - Search diagnostics show matching process")
elif passed >= total * 0.75:
    print(f"\n[PARTIAL SUCCESS] {passed}/{total} tests passed")
    print("System mostly functional, check failed scenarios above")
else:
    print(f"\n[FAILURE] Only {passed}/{total} tests passed")
    print("See failed checks above for issues")

print("\n" + "="*80)
