"""
Runtime Test: Document Chunking System

This script tests the document chunking flow by:
1. Loading a large test document
2. Simulating the document retrieval and chunking process
3. Verifying the expected log messages appear
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json

from engines.document_reader import DocumentReader
from agent_state import AgentState

def test_document_chunking():
    """Test the complete document chunking flow."""

    print("=" * 70)
    print("DOCUMENT CHUNKING RUNTIME TEST")
    print("=" * 70)

    # Step 1: Load test document
    print("\n[TEST] Step 1: Loading test document")
    test_doc_path = "test_large_document.txt"

    if not os.path.exists(test_doc_path):
        print(f"  [FAIL] Test document not found: {test_doc_path}")
        return False

    with open(test_doc_path, "r", encoding="utf-8") as f:
        doc_text = f.read()

    doc_size = len(doc_text)
    print(f"  [OK] Loaded document: {doc_size:,} chars")

    if doc_size <= 30000:
        print(f"  [WARN] Document too small ({doc_size} chars) - chunking requires >30k")
        return False

    # Step 2: Test DocumentReader chunking
    print("\n[TEST] Step 2: Testing DocumentReader chunking")
    doc_reader = DocumentReader(chunk_size=25000)

    # Simulate the chunking flow from main.py lines 377-401
    # Note: load_document signature is: (doc_text, doc_name, doc_id)
    doc_reader.load_document(doc_text, test_doc_path, "test_doc_001")

    # Get current chunk - returns a dict, not a tuple
    chunk_data = doc_reader.get_current_chunk()
    if not chunk_data:
        print("  [FAIL] get_current_chunk() returned None")
        return False

    chunk_info = {
        'current_section': chunk_data['position'],
        'total_sections': chunk_data['total'],
        'chunk_size': len(chunk_data['text'])
    }

    print(f"  [OK] Document split into {chunk_info['total_sections']} chunks")
    print(f"  [OK] Current chunk: section {chunk_info['current_section']}/{chunk_info['total_sections']}")
    print(f"  [OK] Chunk size: {chunk_info['chunk_size']:,} chars")

    # Step 3: Verify chunk structure
    print("\n[TEST] Step 3: Verifying chunk structure")

    if chunk_info['chunk_size'] > 30000:
        print(f"  [WARN] Chunk size ({chunk_info['chunk_size']}) exceeds 30k - may be too large")
    elif chunk_info['chunk_size'] < 10000:
        print(f"  [WARN] Chunk size ({chunk_info['chunk_size']}) is very small")
    else:
        print(f"  [OK] Chunk size within expected range (10k-30k)")

    # Step 4: Test navigation
    print("\n[TEST] Step 4: Testing navigation")

    # Test advance
    doc_reader.advance()
    if doc_reader.current_position == 1:
        print("  [OK] Advance to section 2 works")
    else:
        print(f"  [FAIL] Expected section 2, got section {doc_reader.current_position + 1}")
        return False

    # Test previous
    doc_reader.previous()
    if doc_reader.current_position == 0:
        print("  [OK] Previous to section 1 works")
    else:
        print(f"  [FAIL] Expected section 1, got section {doc_reader.current_position + 1}")
        return False

    # Test jump
    if chunk_info['total_sections'] >= 3:
        doc_reader.jump_to(2)  # Jump to section 3 (0-indexed)
        if doc_reader.current_position == 2:
            print("  [OK] Jump to section 3 works")
        else:
            print(f"  [FAIL] Expected section 3, got section {doc_reader.current_position + 1}")
            return False

    # Step 5: Simulate the main.py chunking flow
    print("\n[TEST] Step 5: Simulating main.py chunking flow")
    print("-" * 70)

    # This simulates what happens in main.py lines 363-430
    selected_documents = [
        {
            'filename': test_doc_path,
            'full_text': doc_text,
            'memory_id': 'test_doc_001'
        }
    ]

    # Simulate the logging from main.py
    print(f"[LLM Retrieval] Loaded {len(selected_documents)} documents")
    for doc in selected_documents:
        print(f"[LLM Retrieval]   - {doc.get('filename', 'unknown')}: {len(doc.get('full_text', '')):,} chars")

    print(f"[DOC CHUNKING] Processing {len(selected_documents)} documents")

    rag_chunks = []
    doc_reader_fresh = DocumentReader(chunk_size=25000)

    for doc in selected_documents:
        doc_filename = doc.get('filename', 'unknown')
        doc_text_sim = doc.get('full_text', '')

        print(f"[DOC CHUNKING] Checking {doc_filename}: {len(doc_text_sim):,} chars")

        if len(doc_text_sim) > 30000:
            # Large document - chunk it
            doc_id = doc.get('memory_id', 'test_doc_001')
            doc_reader_fresh.load_document(doc_text_sim, doc_filename, doc_id)

            # Get current chunk
            chunk = doc_reader_fresh.get_current_chunk()
            if chunk:
                print(f"[DOC READER] Chunk added to context: {len(chunk['text'])} chars (section {chunk['position']}/{chunk['total']})")

                # Format with document header and navigation
                chunk_text = f"""═══ DOCUMENT: {chunk['doc_name']} ═══
Section {chunk['position']}/{chunk['total']} ({chunk['progress_percent']}%)

{chunk['text']}

───────────────────────────────────
Navigation: Say 'continue reading' for next section, 'previous section' to go back,
or 'jump to section N' to skip ahead. 'restart document' returns to beginning.
"""

                rag_chunks.append({
                    "source_file": doc_filename,
                    "text": chunk_text,
                    "is_chunked": True,  # Critical flag!
                    "memory_id": doc_id,
                    "chunk_info": {
                        "current_section": chunk['position'],
                        "total_sections": chunk['total'],
                        "chunk_size": len(chunk['text'])
                    }
                })
        else:
            # Small document - add whole
            rag_chunks.append({
                "source_file": doc_filename,
                "text": doc_text_sim,
                "is_chunked": False,
                "memory_id": doc.get('memory_id', '')
            })
            print(f"[DOC CHUNKING] Small document added whole: {doc_filename} ({len(doc_text_sim)} chars)")

    # Summary
    chunked_count = sum(1 for c in rag_chunks if c.get('is_chunked', False))
    whole_count = len(rag_chunks) - chunked_count
    print(f"[DOC CHUNKING] Added to context: {chunked_count} chunked, {whole_count} whole documents")

    print("-" * 70)

    # Step 6: Verify results
    print("\n[TEST] Step 6: Verifying results")

    if chunked_count != 1:
        print(f"  [FAIL] Expected 1 chunked document, got {chunked_count}")
        return False
    print("  [OK] Correct number of chunked documents")

    if whole_count != 0:
        print(f"  [FAIL] Expected 0 whole documents, got {whole_count}")
        return False
    print("  [OK] Correct number of whole documents")

    chunk_data = rag_chunks[0]
    if not chunk_data.get('is_chunked', False):
        print("  [FAIL] is_chunked flag not set")
        return False
    print("  [OK] is_chunked flag properly set")

    chunk_text = chunk_data.get('text', '')
    if len(chunk_text) > 30000:
        print(f"  [WARN] Formatted chunk is large ({len(chunk_text):,} chars)")
    print(f"  [OK] Formatted chunk size: {len(chunk_text):,} chars")

    # Final verdict
    print("\n" + "=" * 70)
    print("[OK] ALL TESTS PASSED")
    print("=" * 70)
    print("\nDocument chunking system is working correctly!")
    print("\nNext steps:")
    print("1. Start Kay: python main.py")
    print("2. Import this document or create documents.json with it")
    print("3. Query Kay about the document")
    print("4. Verify the terminal output matches the simulated output above")

    return True


if __name__ == "__main__":
    try:
        success = test_document_chunking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
