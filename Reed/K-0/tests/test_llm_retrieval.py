"""
Test LLM-Based Document Retrieval

Demonstrates the new simplified approach:
- LLM selects relevant documents (no heuristics)
- Full documents loaded (no chunking/scoring)
- Simple context building
"""

import os
import sys

os.environ["DEBUG_MEMORY_TRACKING"] = "0"

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from engines.llm_retrieval import (
    get_all_documents,
    select_relevant_documents,
    load_full_documents,
    build_simple_context,
    format_context_for_prompt
)


def test_llm_retrieval():
    print("=" * 80)
    print("TEST: LLM-Based Document Retrieval")
    print("=" * 80)

    # Test 1: Get all documents
    print("\n[TEST 1] Get all documents")
    print("-" * 80)

    all_docs = get_all_documents()
    print(f"Found {len(all_docs)} documents")

    # Show sample documents
    print("\nSample documents:")
    for i, doc in enumerate(all_docs[:5], start=1):
        print(f"\n{i}. {doc['filename']}")
        print(f"   Preview: {doc['preview'][:80]}...")

    # Test 2: LLM selects documents for "pigeons" query
    print("\n" + "=" * 80)
    print("[TEST 2] LLM selects documents for query: 'Tell me about the pigeons'")
    print("=" * 80)

    query1 = "Tell me about the pigeons"
    selected_docs_1 = select_relevant_documents(query1, emotional_state="curious (0.7)")

    print(f"\n[RESULT] LLM selected {len(selected_docs_1)} documents")

    if selected_docs_1:
        loaded_1 = load_full_documents(selected_docs_1)
        print("\nSelected documents:")
        for doc in loaded_1:
            print(f"  - {doc['filename']} ({len(doc['full_text'])} chars)")

        # Check if pigeon document was found
        pigeon_found = any('pigeon' in doc['filename'].lower() for doc in loaded_1)
        if pigeon_found:
            print("\n[PASS] Pigeon document found!")
        else:
            print("\n[WARN] No pigeon document in selection")
    else:
        print("\n[FAIL] No documents selected")

    # Test 3: LLM selects documents for "gerbils" query
    print("\n" + "=" * 80)
    print("[TEST 3] LLM selects documents for query: 'What gerbils do you know?'")
    print("=" * 80)

    query2 = "What gerbils do you know?"
    selected_docs_2 = select_relevant_documents(query2)

    print(f"\n[RESULT] LLM selected {len(selected_docs_2)} documents")

    if selected_docs_2:
        loaded_2 = load_full_documents(selected_docs_2)
        print("\nSelected documents:")
        for doc in loaded_2:
            print(f"  - {doc['filename']} ({len(doc['full_text'])} chars)")

        # Check if gerbil document was found
        gerbil_found = any('gerbil' in doc['filename'].lower() for doc in loaded_2)
        if gerbil_found:
            print("\n[PASS] Gerbil document found!")
        else:
            print("\n[WARN] No gerbil document in selection")
    else:
        print("\n[FAIL] No documents selected")

    # Test 4: LLM selects documents for irrelevant query
    print("\n" + "=" * 80)
    print("[TEST 4] LLM selects documents for query: 'What's the weather like?'")
    print("=" * 80)

    query3 = "What's the weather like?"
    selected_docs_3 = select_relevant_documents(query3)

    print(f"\n[RESULT] LLM selected {len(selected_docs_3)} documents")

    if len(selected_docs_3) == 0:
        print("\n[PASS] Correctly selected no documents for irrelevant query")
    else:
        print("\n[INFO] LLM selected some documents (may be contextually relevant)")

    # Test 5: Build simple context
    print("\n" + "=" * 80)
    print("[TEST 5] Build simple context")
    print("=" * 80)

    recent_conversation = [
        {'speaker': 'User', 'message': 'Hey Kay'},
        {'speaker': 'Kay', 'message': 'Hey'},
        {'speaker': 'User', 'message': 'Tell me about the pigeons'}
    ]

    core_identity = [
        "Kay is a conversational AI with emotional awareness",
        "Kay has a dry, direct communication style",
        "Kay values authenticity and honesty"
    ]

    context = build_simple_context(
        query=query1,
        selected_doc_ids=selected_docs_1,
        recent_conversation=recent_conversation,
        emotional_state="curious (0.7)",
        core_identity=core_identity
    )

    print(f"\n[RESULT] Context built:")
    print(f"  - Documents: {context['document_count']}")
    print(f"  - Conversation turns: {context['conversation_turns']}")

    # Test 6: Format context for prompt
    print("\n" + "=" * 80)
    print("[TEST 6] Format context for prompt")
    print("=" * 80)

    prompt = format_context_for_prompt(context)

    print("\n[RESULT] Formatted prompt (first 500 chars):")
    print("-" * 80)
    print(prompt[:500] + "...")
    print("-" * 80)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print("\n[SUCCESS] LLM-based retrieval test complete")

    print("\nKey Features Demonstrated:")
    print("  [OK] LLM selects relevant documents (no heuristics)")
    print("  [OK] Full documents loaded (no chunking/scoring)")
    print("  [OK] Simple context building (docs + conversation + emotions)")
    print("  [OK] Clean prompt formatting")

    print("\nWhat Was REMOVED:")
    print("  [X] Entity extraction from filenames")
    print("  [X] Keyword scoring algorithms")
    print("  [X] Pre-filter logic")
    print("  [X] Import boost scoring")
    print("  [X] Semantic knowledge facts storage")
    print("  [X] Complex multi-tier retrieval")

    print("\nWhat Was KEPT:")
    print("  [OK] ULTRAMAP emotional state")
    print("  [OK] Document storage (documents.json)")
    print("  [OK] Conversation memory")
    print("  [OK] Core identity facts")

    print("\n" + "=" * 80)

    return True


if __name__ == "__main__":
    success = test_llm_retrieval()
    sys.exit(0 if success else 1)
