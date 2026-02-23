"""
Simple test: Verify that EmotionalMemoryChunk objects have doc_id and chunk_index
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_chunk_metadata():
    print("=" * 60)
    print("TEST: Chunk Metadata (doc_id and chunk_index)")
    print("=" * 60)
    print()

    from memory_import.emotional_importer import EmotionalMemoryImporter

    # Create test file
    test_content = """Kay is a conversational AI with emotional depth.
Kay values honesty and direct communication.
Re is working to help Kay maintain continuity."""

    test_file = "test_chunk_fields.txt"
    with open(test_file, 'w') as f:
        f.write(test_content)

    print("[TEST] Importing test document...")
    print()

    # Import document
    importer = EmotionalMemoryImporter()
    doc_id, emotional_chunks = importer.import_document(test_file)

    print()
    print(f"[TEST] Import complete: doc_id={doc_id}, {len(emotional_chunks)} chunks")
    print()

    # Check chunks have metadata
    print("[TEST] Checking chunk objects for metadata fields:")
    print("-" * 60)

    all_have_metadata = True
    for i, chunk in enumerate(emotional_chunks):
        has_doc_id = hasattr(chunk, 'doc_id') and chunk.doc_id is not None
        has_chunk_index = hasattr(chunk, 'chunk_index') and chunk.chunk_index is not None

        print(f"Chunk {i}:")
        print(f"  - has doc_id attribute: {hasattr(chunk, 'doc_id')}")
        print(f"  - doc_id value: {getattr(chunk, 'doc_id', 'NOT SET')}")
        print(f"  - has chunk_index attribute: {hasattr(chunk, 'chunk_index')}")
        print(f"  - chunk_index value: {getattr(chunk, 'chunk_index', 'NOT SET')}")

        if not has_doc_id or not has_chunk_index:
            all_have_metadata = False

    print("-" * 60)
    print()

    if all_have_metadata:
        print("[SUCCESS] All chunks have doc_id and chunk_index!")
    else:
        print("[FAILURE] Some chunks missing metadata")
        return False

    # Check to_dict() includes metadata
    print("[TEST] Checking to_dict() includes metadata:")
    print("-" * 60)

    all_dicts_have_metadata = True
    for i, chunk in enumerate(emotional_chunks):
        chunk_dict = chunk.to_dict()

        has_doc_id = 'doc_id' in chunk_dict
        has_chunk_index = 'chunk_index' in chunk_dict

        print(f"Chunk {i} dict:")
        print(f"  - 'doc_id' in dict: {has_doc_id}")
        if has_doc_id:
            print(f"  - doc_id value: {chunk_dict['doc_id']}")
        print(f"  - 'chunk_index' in dict: {has_chunk_index}")
        if has_chunk_index:
            print(f"  - chunk_index value: {chunk_dict['chunk_index']}")

        if not has_doc_id or not has_chunk_index:
            all_dicts_have_metadata = False

    print("-" * 60)
    print()

    if all_dicts_have_metadata:
        print("[SUCCESS] All chunk dicts have doc_id and chunk_index!")
        print("[SUCCESS] Metadata will persist to storage")
    else:
        print("[FAILURE] Some chunk dicts missing metadata")
        return False

    print()
    print("=" * 60)
    print("COMPLETE: Phase 2A metadata is working!")
    print("=" * 60)

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

    return True

if __name__ == "__main__":
    success = test_chunk_metadata()
    sys.exit(0 if success else 1)
