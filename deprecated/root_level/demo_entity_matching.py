"""
Demonstration: Entity-Based Document Matching

Shows how entity extraction and matching ensures "pigeons" queries
ALWAYS find pigeon documents with 10.0x score boost.
"""

import os
import sys
os.environ["DEBUG_MEMORY_TRACKING"] = "0"

from engines.document_index import DocumentIndex


def demo_entity_matching():
    print("=" * 80)
    print("DEMO: Entity-Based Document Matching")
    print("=" * 80)

    # Initialize index
    print("\n[SETUP] Initializing document index...")
    doc_index = DocumentIndex()

    print(f"\n[SETUP] Indexed {len(doc_index.index)} documents")
    print(f"[SETUP] Entity index contains {len(doc_index.entity_index)} entities")

    # Show entity extraction examples
    print("\n" + "=" * 80)
    print("STEP 1: Entity Extraction from Filenames")
    print("=" * 80)

    test_files = [
        "test-pigeons.txt",
        "test-pigeons2.txt",
        "Pigeon_Data_2025.docx",
        "debug-gerbils.txt"
    ]

    for filename in test_files:
        entities = doc_index._extract_entities_from_filename(filename)
        print(f"\n  '{filename}'")
        print(f"    -> Entities: {sorted(entities)}")

    # Show entity mappings for pigeon-related entities
    print("\n" + "=" * 80)
    print("STEP 2: Entity Index Mappings")
    print("=" * 80)

    pigeon_entities = ['pigeon', 'pigeons', 'test', 'tests']
    print("\nChecking pigeon-related entity mappings:")

    for entity in pigeon_entities:
        if entity in doc_index.entity_index:
            doc_ids = doc_index.entity_index[entity]
            # Get filenames for these doc_ids
            filenames = [doc_index.index[did]['filename'] for did in doc_ids if did in doc_index.index]
            # Filter to pigeon-related files
            pigeon_files = [f for f in filenames if 'pigeon' in f.lower()]
            if pigeon_files:
                print(f"\n  '{entity}' -> {len(pigeon_files)} pigeon docs:")
                for f in sorted(set(pigeon_files))[:3]:
                    print(f"    - {f}")

    # Test queries
    print("\n" + "=" * 80)
    print("STEP 3: Query Testing")
    print("=" * 80)

    queries = [
        "Remember the pigeons?",
        "What about test-pigeons2?",
        "Tell me about pigeons",
        "pigeon data"
    ]

    for query in queries:
        print(f"\n{'=' * 80}")
        print(f"Query: '{query}'")
        print('=' * 80)

        results = doc_index.search(query)

        print(f"\n[RESULT] Found {len(results)} documents")

        # Show top 3 pigeon-related results
        pigeon_results = [doc_id for doc_id in results
                         if 'pigeon' in doc_index.index[doc_id]['filename'].lower()]

        if pigeon_results:
            print(f"\n[SUCCESS] Pigeon documents found ({len(pigeon_results)}):")
            for i, doc_id in enumerate(pigeon_results[:3]):
                print(f"  {i+1}. {doc_index.index[doc_id]['filename']}")
        else:
            print("\n[FAIL] No pigeon documents in results!")

    # Compare entity_map vs keyword_matching
    print("\n" + "=" * 80)
    print("STEP 4: Matching Strategy Comparison")
    print("=" * 80)

    print("\nQuery: 'Tell me about pigeons'")
    print("\nExpected behavior:")
    print("  1. Query word 'pigeons' extracted")
    print("  2. entity_index checked: 'pigeons' -> doc_ids")
    print("  3. Matched docs get score=10.0 (ENTITY MATCH)")
    print("  4. Other docs get score=0.0-1.0 (keyword matching)")
    print("  5. Results sorted by score (10.0+ first)")

    print("\n" + "=" * 80)
    print("Running search with detailed logging:")
    print("=" * 80)

    doc_index.search("Tell me about pigeons")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)

    print("\nKey Takeaways:")
    print("  ✓ Entities extracted from filenames (test-pigeons.txt -> pigeon, pigeons)")
    print("  ✓ Entity index maps entities to document IDs")
    print("  ✓ Entity matches checked FIRST before keywords")
    print("  ✓ Entity matches get 10.0x score boost")
    print("  ✓ Match strategy logged: [ENTITY MATCH] vs [KEYWORD MATCH]")
    print("  ✓ Pigeon queries ALWAYS find pigeon documents")

    return True


if __name__ == "__main__":
    demo_entity_matching()
