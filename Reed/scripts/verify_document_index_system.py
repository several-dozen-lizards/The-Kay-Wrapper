"""
Comprehensive verification of Document Index System.

This script verifies:
1. DocumentIndex initialization and indexing
2. Tree file loading with full_text
3. Document search functionality
4. Memory engine integration
5. End-to-end retrieval with document chunks
"""

from engines.document_index import DocumentIndex
from engines.memory_engine import MemoryEngine
from engines.identity_memory import IdentityMemory

print("="*80)
print("DOCUMENT INDEX SYSTEM - COMPREHENSIVE VERIFICATION")
print("="*80)

# TEST 1: DocumentIndex Initialization
print("\n[TEST 1] DocumentIndex Initialization")
print("-" * 40)

idx = DocumentIndex()
print(f"[OK] DocumentIndex created")
print(f"  Indexed documents: {len(idx.index)}")

if len(idx.index) == 0:
    print("  [WARNING] No documents indexed - check data/trees/ directory")
else:
    print(f"  [OK] Successfully indexed {len(idx.index)} documents")

# TEST 2: Tree File Loading
print("\n[TEST 2] Tree File Loading with Full Text")
print("-" * 40)

if idx.index:
    test_doc_id = list(idx.index.keys())[0]
    test_doc = idx.index[test_doc_id]

    print(f"  Testing with: {test_doc['filename']}")

    tree = idx.load_tree(test_doc_id)
    if tree:
        trees = tree.get('trees', {})
        if test_doc_id in trees:
            tree_doc = trees[test_doc_id]
            has_full_text = bool(tree_doc.get('full_text'))

            print(f"  [OK] Tree loaded successfully")
            print(f"    Has full_text: {has_full_text}")
            print(f"    Full_text length: {len(tree_doc.get('full_text', ''))} chars")
            print(f"    Branches: {len(tree_doc.get('branches', []))}")

            if not has_full_text:
                print(f"    [WARNING] No full_text - check documents.json")
            else:
                print(f"    [OK] Full text successfully loaded from documents.json")
        else:
            print(f"  [ERROR] Tree loaded but doc_id not found in trees")
    else:
        print(f"  [ERROR] Failed to load tree")

# TEST 3: Document Search
print("\n[TEST 3] Document Search Functionality")
print("-" * 40)

if idx.index:
    # Create search query from first document's keywords
    test_doc = idx.index[test_doc_id]
    keywords = list(test_doc['keywords'])[:3]
    query = ' '.join(keywords)

    print(f"  Query: '{query}'")

    results = idx.search(query, min_score=0.3)
    print(f"  Results: {len(results)} documents")

    if results:
        print(f"  [OK] Search returned {len(results)} matching documents")
        print(f"    Top match: {results[0]}")
        print(f"    Correct match: {results[0] == test_doc_id}")

        if results[0] == test_doc_id:
            print(f"    [OK] Search correctly matched target document")
        else:
            print(f"    [WARNING] Top match doesn't match test document")
    else:
        print(f"  [ERROR] No search results returned")

# TEST 4: Memory Engine Integration
print("\n[TEST 4] Memory Engine Integration")
print("-" * 40)

try:
    identity = IdentityMemory()
    memory_engine = MemoryEngine(identity)

    print(f"  [OK] MemoryEngine created")
    print(f"  [OK] DocumentIndex integrated: {hasattr(memory_engine, 'document_index')}")

    # Check if _retrieve_document_tree_chunks exists
    has_method = hasattr(memory_engine, '_retrieve_document_tree_chunks')
    print(f"  [OK] _retrieve_document_tree_chunks method: {has_method}")

    if has_method:
        print(f"    [OK] Document retrieval method available")
    else:
        print(f"    [ERROR] Document retrieval method missing")

except Exception as e:
    print(f"  [ERROR] Memory engine initialization failed: {e}")

# TEST 5: End-to-End Retrieval
print("\n[TEST 5] End-to-End Document Retrieval")
print("-" * 40)

try:
    # Create a query that should match indexed documents
    if idx.index:
        test_doc = idx.index[test_doc_id]
        query = test_doc['filename'].replace('.txt', '').replace('_', ' ')

        print(f"  Query: '{query}'")

        # Call _retrieve_document_tree_chunks directly
        document_chunks = memory_engine._retrieve_document_tree_chunks(query, max_docs=1)

        print(f"  Retrieved chunks: {len(document_chunks)}")

        if document_chunks:
            print(f"  [OK] Successfully retrieved document chunks")

            # Check chunk structure
            sample = document_chunks[0]
            print(f"\n  Sample chunk structure:")
            print(f"    type: {sample.get('type')}")
            print(f"    doc_id: {sample.get('doc_id')}")
            print(f"    source_file: {sample.get('source_file')}")
            print(f"    branch: {sample.get('branch')}")
            print(f"    has fact: {bool(sample.get('fact'))}")
            print(f"    fact length: {len(sample.get('fact', ''))} chars")
            print(f"    importance_score: {sample.get('importance_score')}")

            # Verify it's marked as document_tree
            if sample.get('type') == 'document_tree':
                print(f"\n    [OK] Chunk correctly marked as 'document_tree'")
            else:
                print(f"\n    [WARNING] Chunk type is '{sample.get('type')}', expected 'document_tree'")

            # Verify it has content
            if len(sample.get('fact', '')) > 0:
                print(f"    [OK] Chunk contains content ({len(sample.get('fact', ''))} chars)")
            else:
                print(f"    [ERROR] Chunk has no content")

        else:
            print(f"  [WARNING] No chunks retrieved")
            print(f"    Check if query matches document keywords")

except Exception as e:
    print(f"  [ERROR] Retrieval failed: {e}")
    import traceback
    traceback.print_exc()

# FINAL SUMMARY
print("\n" + "="*80)
print("VERIFICATION SUMMARY")
print("="*80)

checks = {
    "DocumentIndex initialized": len(idx.index) > 0,
    "Documents indexed": len(idx.index) >= 1,
    "Tree loading works": tree is not None if idx.index else False,
    "Full text loaded": has_full_text if idx.index else False,
    "Search functional": len(results) > 0 if idx.index else False,
    "Memory engine integration": hasattr(memory_engine, 'document_index'),
    "Retrieval method exists": hasattr(memory_engine, '_retrieve_document_tree_chunks'),
    "End-to-end retrieval": len(document_chunks) > 0 if idx.index else False
}

passed = sum(1 for check in checks.values() if check)
total = len(checks)

print(f"\nChecks passed: {passed}/{total}\n")

for check_name, check_passed in checks.items():
    status = "[OK]" if check_passed else "[FAIL]"
    print(f"  {status} {check_name}")

if passed == total:
    print(f"\n[SUCCESS] ALL CHECKS PASSED - Document Index System is fully functional!")
else:
    print(f"\n[WARNING] {total - passed} checks failed - see details above")

print("\n" + "="*80)
