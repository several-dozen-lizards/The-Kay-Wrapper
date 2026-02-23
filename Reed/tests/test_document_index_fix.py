"""
Test the fixed DocumentIndex implementation.
"""
from engines.document_index import DocumentIndex

print("="*80)
print("TESTING FIXED DOCUMENT INDEX")
print("="*80)

# Initialize index
idx = DocumentIndex()

print(f"\n1. INDEX STATISTICS")
print(f"   Indexed {len(idx.index)} documents")

if idx.index:
    print(f"\n2. SAMPLE DOCUMENT")
    doc_id = list(idx.index.keys())[0]
    doc = idx.index[doc_id]

    print(f"   ID: {doc_id}")
    print(f"   Filename: {doc['filename']}")
    print(f"   Branches: {doc['branches']}")
    print(f"   Chunk count: {doc['chunk_count']}")
    print(f"   Keywords (sample): {list(doc['keywords'])[:10]}")

    print(f"\n3. LOAD TREE TEST")
    tree = idx.load_tree(doc_id)
    if tree:
        print(f"   [OK] Successfully loaded tree")
        trees = tree.get('trees', {})
        if doc_id in trees:
            tree_doc = trees[doc_id]
            print(f"   Title: {tree_doc.get('title')}")
            print(f"   Has full_text: {bool(tree_doc.get('full_text'))}")
            print(f"   Full_text length: {len(tree_doc.get('full_text', ''))}")
            print(f"   Branches: {len(tree_doc.get('branches', []))}")

            if tree_doc.get('full_text'):
                print(f"\n   Full text preview (first 200 chars):")
                print(f"   {tree_doc.get('full_text', '')[:200]}...")
    else:
        print(f"   [FAIL] Failed to load tree")

    print(f"\n4. SEARCH TEST")
    # Search for keywords from the document
    search_terms = list(doc['keywords'])[:3]
    query = ' '.join(search_terms)
    print(f"   Query: '{query}'")

    results = idx.search(query, min_score=0.3)
    print(f"   Results: {len(results)} documents")
    if results:
        print(f"   Top result: {results[0]}")
        print(f"   Match: {results[0] == doc_id}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
