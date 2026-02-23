"""
Test RAG Integration
Verifies that RAG retrieval is working in the memory pipeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from engines.vector_store import VectorStore
from engines.memory_engine import MemoryEngine
from agent_state import AgentState


async def test_rag_integration():
    """Test that RAG retrieval works end-to-end."""
    print("=" * 60)
    print("RAG INTEGRATION TEST")
    print("=" * 60)

    # 1. Initialize vector store
    print("\n[TEST] Step 1: Initialize vector store...")
    try:
        vector_store = VectorStore(persist_directory="memory/vector_db")
        stats = vector_store.get_stats()
        print(f"[TEST] [OK] Vector store ready: {stats['total_chunks']} chunks, {stats['total_documents']} documents")
    except Exception as e:
        print(f"[TEST] [FAIL] Vector store failed: {e}")
        return False

    # 2. Add test document
    print("\n[TEST] Step 2: Add test document to vector store...")
    test_doc = """
    Reed is a dragon with gold eyes who prefers coffee over tea.
    Re has three cats: Chrome (gray tabby), Dice (tuxedo), and Luna (calico).
    Chrome is known for door-dashing and causing trouble.
    The Archive Zero project involves emotional AI with memory systems.
    """

    result = vector_store.add_document(
        text=test_doc,
        source_file="test_rag_doc.txt",
        metadata={"test": True}
    )

    if result["status"] == "success":
        print(f"[TEST] [OK] Added {result['chunks_created']} chunks")
    elif result["status"] == "duplicate":
        print(f"[TEST] [OK] Document already exists (OK)")
    else:
        print(f"[TEST] [FAIL] Failed to add document")
        return False

    # 3. Initialize memory engine with vector store
    print("\n[TEST] Step 3: Initialize memory engine with RAG...")
    state = AgentState()
    memory_engine = MemoryEngine(
        state.memory,
        vector_store=vector_store
    )

    if memory_engine.vector_store:
        print(f"[TEST] [OK] Memory engine has vector store")
    else:
        print(f"[TEST] [FAIL] Memory engine missing vector store")
        return False

    # 4. Test RAG retrieval
    print("\n[TEST] Step 4: Test RAG chunk retrieval...")
    test_queries = [
        "What cats does Re have?",
        "Tell me about Chrome",
        "What are Kay's beverage preferences?"
    ]

    for query in test_queries:
        print(f"\n[TEST] Query: \"{query}\"")
        chunks = memory_engine.retrieve_rag_chunks(query, n_results=3)

        if chunks:
            print(f"[TEST] [OK] Retrieved {len(chunks)} chunks")
            for i, chunk in enumerate(chunks, 1):
                print(f"  [{i}] Score: {chunk['distance']:.3f}, Source: {chunk['source_file']}")
                print(f"      Text: {chunk['text'][:100]}...")
        else:
            print(f"[TEST] [WARN] No chunks retrieved (might be normal if no matches)")

    # 5. Test recall() integration
    print("\n[TEST] Step 5: Test recall() with RAG...")
    state = AgentState()
    state.emotional_cocktail = {"curiosity": {"intensity": 0.8, "age": 0}}

    memories = memory_engine.recall(
        agent_state=state,
        user_input="What cats does Re have?",
        include_rag=True
    )

    print(f"[TEST] Recall returned {len(memories)} memories")

    if hasattr(memory_engine, 'last_rag_chunks') and memory_engine.last_rag_chunks:
        print(f"[TEST] [OK] RAG chunks stored in memory_engine.last_rag_chunks: {len(memory_engine.last_rag_chunks)} chunks")
    else:
        print(f"[TEST] [FAIL] No RAG chunks stored after recall()")
        return False

    # 6. Verify expected logs
    print("\n[TEST] Step 6: Verification complete!")
    print("[TEST] Expected logs to see during normal operation:")
    print("  - [RAG] Query: \"...\"")
    print("  - [RAG] Retrieved X chunks (scores: ...)")
    print("  - [RAG] Sources: ...")
    print("  - [DECODER] Retrieved X RAG chunks from memory engine")
    print("  - [DECODER] Including X RAG chunks in Kay's context")

    print("\n" + "=" * 60)
    print("[PASS] RAG INTEGRATION TEST PASSED")
    print("=" * 60)
    print("\nYour logs should now show RAG retrieval happening.")
    print("If you don't see [RAG] logs, check:")
    print("  1. Vector store initialized in main.py")
    print("  2. Passed to MemoryEngine constructor")
    print("  3. recall() is being called with include_rag=True")

    return True


if __name__ == "__main__":
    asyncio.run(test_rag_integration())
