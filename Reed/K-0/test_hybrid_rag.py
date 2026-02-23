"""
Test script for Hybrid RAG + Structured Memory System
Verifies that documents are stored in vector DB and retrieval works
"""

import asyncio
import os
from pathlib import Path

# Test imports
try:
    from engines.vector_store import VectorStore
    from memory_import.hybrid_import_manager import HybridImportManager
    print("[TEST] ✓ Imports successful")
except ImportError as e:
    print(f"[TEST] ✗ Import failed: {e}")
    print("Run: pip install chromadb")
    exit(1)


async def test_vector_store():
    """Test vector store basic functionality."""
    print("\n=== TEST 1: Vector Store ===")

    # Initialize
    store = VectorStore(persist_directory="memory/vector_db_test")

    # Test document
    test_doc = """
    Reed is an emotionally-aware conversational AI with gold eyes and a dry sense of humor.
    Re is Reed's conversation partner who has several cats: Chrome (gray tabby), Dice (tuxedo), and Luna.
    Chrome likes to door-dash and cause trouble. Dice is more reserved.
    Kay prefers coffee in the morning but occasionally enjoys tea. Re prefers tea.
    """

    # Add document
    print("[TEST] Adding test document...")
    result = store.add_document(
        text=test_doc,
        source_file="test_notes.txt",
        chunk_size=200,
        overlap=50,
        metadata={"document_type": "test"}
    )

    print(f"  - Chunks created: {result['chunks_created']}")
    print(f"  - Status: {result['status']}")

    if result['chunks_created'] == 0:
        print("[TEST] ✗ Failed to create chunks")
        return False

    # Query
    print("[TEST] Querying: 'What cats does Re have?'")
    chunks = store.query("What cats does Re have?", n_results=3)

    if not chunks:
        print("[TEST] ✗ No chunks retrieved")
        return False

    print(f"  - Retrieved {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"    [{i}] Distance: {chunk['distance']:.4f}")
        print(f"        Text: {chunk['text'][:100]}...")

    # Stats
    stats = store.get_stats()
    print(f"  - Total chunks: {stats['total_chunks']}")
    print(f"  - Total documents: {stats['total_documents']}")

    print("[TEST] ✓ Vector store test passed")
    return True


async def test_hybrid_import():
    """Test hybrid import manager."""
    print("\n=== TEST 2: Hybrid Import Manager ===")

    # Create test file
    test_file = "memory/test_import_doc.txt"
    os.makedirs("memory", exist_ok=True)

    test_content = """
    Archive Zero Development Notes
    ===============================

    Project: Reed (K-0) - Emotionally-aware conversational AI
    Author: Re
    Date: 2024-10-29

    ## Key Insights

    Chrome is Re's gray tabby cat who has a habit of door-dashing. He's very mischievous.
    Dice is Re's tuxedo cat, more reserved than Chrome.
    Luna is the third cat, calm and gentle.

    Kay is the AI agent with gold eyes and a preference for coffee over tea.
    Re is the human developer working on Reed.

    The system uses a three-tier memory architecture:
    1. Working memory (last 10 turns)
    2. Episodic memory (recent experiences)
    3. Semantic memory (permanent facts)

    ## Technical Notes

    The emotion engine uses ULTRAMAP protocols to manage emotional cocktails.
    Entity resolution prevents confusion between entities (e.g., Re's cats vs Reed's attributes).
    Glyph filtering helps compress large memory retrievals.

    ## Next Steps

    Implement RAG system to handle document uploads without memory bloat.
    Add vector store for bulk knowledge storage.
    Cap structured memory at <100 active facts.
    """

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"[TEST] Created test file: {test_file} ({len(test_content)} chars)")

    # Initialize components (mock)
    class MockMemoryEngine:
        def __init__(self):
            self.memories = []
            self.current_turn = 0
            self.memory_layers = MockMemoryLayers()

        def _save_to_disk(self):
            pass

    class MockMemoryLayers:
        def add_memory(self, memory, layer):
            pass

        def _save_to_disk(self):
            pass

    class MockEntityGraph:
        def __init__(self):
            self.entities = {}

        def get_or_create_entity(self, name, turn=0):
            class MockEntity:
                def __init__(self):
                    self.first_mentioned = turn
            if name not in self.entities:
                self.entities[name] = MockEntity()
            return self.entities[name]

        def _save_to_disk(self):
            pass

    memory_engine = MockMemoryEngine()
    entity_graph = MockEntityGraph()
    vector_store = VectorStore(persist_directory="memory/vector_db_test")

    # Initialize hybrid import manager
    manager = HybridImportManager(
        memory_engine=memory_engine,
        entity_graph=entity_graph,
        vector_store=vector_store
    )

    # Import file
    print("[TEST] Importing test file with hybrid manager...")
    progress = await manager.import_files([test_file])

    print(f"  - Files processed: {progress.processed_files}/{progress.total_files}")
    print(f"  - Chunks stored (RAG): {progress.total_chunks_stored}")
    print(f"  - Key facts extracted: {progress.key_facts_extracted}")
    print(f"  - Summaries created: {progress.summaries_created}")
    print(f"  - Entities created: {progress.entities_created}")
    print(f"  - Status: {progress.status}")

    if progress.errors:
        print(f"  - Errors: {progress.errors}")

    # Verify chunks in vector store
    print("[TEST] Querying imported document...")
    chunks = vector_store.query("What are Re's cats?", n_results=3)
    print(f"  - Retrieved {len(chunks)} chunks from imported document")

    if not chunks:
        print("[TEST] ✗ No chunks retrieved from imported document")
        return False

    # Check that facts are capped
    if progress.key_facts_extracted > 10:
        print(f"[TEST] ⚠ Warning: {progress.key_facts_extracted} facts extracted (should be ≤10)")
    else:
        print(f"[TEST] ✓ Fact extraction capped correctly ({progress.key_facts_extracted} ≤ 10)")

    # Check that entities are capped
    if progress.entities_created > 5:
        print(f"[TEST] ⚠ Warning: {progress.entities_created} entities created (should be ≤5)")
    else:
        print(f"[TEST] ✓ Entity creation capped correctly ({progress.entities_created} ≤ 5)")

    # Cleanup
    os.remove(test_file)
    print(f"[TEST] Cleaned up test file")

    print("[TEST] ✓ Hybrid import test passed")
    return True


async def test_performance():
    """Test performance targets."""
    print("\n=== TEST 3: Performance Targets ===")

    import time

    vector_store = VectorStore(persist_directory="memory/vector_db_test")

    # Large document
    large_doc = "\n".join([
        f"This is paragraph {i} about various topics including Kay, Re, Chrome, and other entities. "
        f"It contains information about emotional states, memory systems, and conversational patterns. "
        for i in range(500)
    ])

    print(f"[TEST] Testing with {len(large_doc)} char document...")

    # Test upload time
    start = time.time()
    result = vector_store.add_document(
        text=large_doc,
        source_file="large_test.txt",
        chunk_size=800,
        overlap=100
    )
    upload_time = time.time() - start

    print(f"  - Upload time: {upload_time:.2f}s (target: <5s)")
    print(f"  - Chunks created: {result['chunks_created']}")

    if upload_time > 5:
        print("[TEST] ⚠ Warning: Upload time exceeds target")
    else:
        print("[TEST] ✓ Upload time within target")

    # Test retrieval time
    start = time.time()
    chunks = vector_store.query("Kay and Chrome", n_results=5)
    retrieval_time = time.time() - start

    print(f"  - Retrieval time: {retrieval_time*1000:.1f}ms (target: <100ms)")

    if retrieval_time > 0.1:
        print("[TEST] ⚠ Warning: Retrieval time exceeds target")
    else:
        print("[TEST] ✓ Retrieval time within target")

    print("[TEST] ✓ Performance test complete")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("HYBRID RAG + STRUCTURED MEMORY TEST SUITE")
    print("=" * 60)

    tests = [
        ("Vector Store", test_vector_store),
        ("Hybrid Import", test_hybrid_import),
        ("Performance", test_performance),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[TEST] ✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Hybrid RAG system is working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Review output above.")

    # Cleanup test vector store
    import shutil
    test_dir = Path("memory/vector_db_test")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("\n[CLEANUP] Removed test vector store")


if __name__ == "__main__":
    asyncio.run(main())
