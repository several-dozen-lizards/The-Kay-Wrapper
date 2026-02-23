"""
Direct test: Does "pigeons" query find test-pigeons2.txt?

Shows exact matching behavior with detailed logs.
"""

import os
os.environ["DEBUG_MEMORY_TRACKING"] = "0"

from engines.document_index import DocumentIndex


def test_pigeon_query():
    print("=" * 80)
    print("DIRECT TEST: Query 'pigeons' finds test-pigeons2.txt")
    print("=" * 80)

    # Initialize index
    doc_index = DocumentIndex()

    # Check what entities test-pigeons2.txt has
    print("\n[STEP 1] Check test-pigeons2.txt entities:")
    print("-" * 80)

    for doc_id, meta in doc_index.index.items():
        if 'test-pigeons2' in meta['filename']:
            print(f"\nDocument: {meta['filename']}")
            print(f"  - doc_id: {doc_id}")
            print(f"  - Entities: {sorted(meta.get('entities', []))}")
            break

    # Check entity_index for 'pigeons' and variants
    print("\n[STEP 2] Check entity_index for 'pigeons' variants:")
    print("-" * 80)

    for variant in ['pigeon', 'pigeons', 'pigeons2', 'pigeons2s']:
        if variant in doc_index.entity_index:
            doc_ids = doc_index.entity_index[variant]
            filenames = [doc_index.index[did]['filename'] for did in doc_ids if did in doc_index.index]
            pigeon_files = [f for f in filenames if 'pigeon' in f.lower()]
            print(f"\n'{variant}' -> {len(pigeon_files)} pigeon docs:")
            for f in sorted(set(pigeon_files))[:5]:
                print(f"  - {f}")

    # Run actual query
    print("\n[STEP 3] Run query: 'Tell me about pigeons'")
    print("=" * 80)

    results = doc_index.search("Tell me about pigeons")

    # Check if test-pigeons2.txt is in results
    print("\n[STEP 4] Check if test-pigeons2.txt in results:")
    print("-" * 80)

    found_pigeons2 = False
    for i, doc_id in enumerate(results):
        filename = doc_index.index[doc_id]['filename']
        if 'test-pigeons2' in filename:
            print(f"\n[OK] FOUND: {filename} at position {i+1}")
            found_pigeons2 = True
            if i < 3:
                print("   [SUCCESS] In top 3 results!")
            break

    if not found_pigeons2:
        print("\n[X] FAILED: test-pigeons2.txt NOT in results")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\nQuery: 'Tell me about pigeons'")
    print(f"Total results: {len(results)}")

    pigeon_results = [doc_index.index[did]['filename'] for did in results
                     if 'pigeon' in doc_index.index[did]['filename'].lower()]

    print(f"\nPigeon-related documents in results: {len(pigeon_results)}")
    print("\nTop 5 pigeon documents:")
    for i, filename in enumerate(list(set(pigeon_results))[:5]):
        print(f"  {i+1}. {filename}")

    if found_pigeons2:
        print("\n[OK] TEST PASSED: Pigeon queries ALWAYS find pigeon documents")
    else:
        print("\n[X] TEST FAILED: Pigeon documents not found")

    return found_pigeons2


if __name__ == "__main__":
    import sys
    success = test_pigeon_query()
    sys.exit(0 if success else 1)
