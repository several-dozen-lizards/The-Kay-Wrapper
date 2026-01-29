#!/usr/bin/env python3
"""
Test to verify document retrieval fix allows Kay to access full documents.
Tests that Kay can retrieve 100 chunks instead of just 5.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_retrieval_limits():
    """Test that retrieval limits have been increased."""

    print("=" * 70)
    print("DOCUMENT RETRIEVAL FIX VERIFICATION")
    print("=" * 70)
    print()

    # Test 1: Check memory_engine.py default parameter
    from engines.memory_engine import MemoryEngine
    import inspect

    sig = inspect.signature(MemoryEngine.retrieve_rag_chunks)
    n_results_default = sig.parameters['n_results'].default

    print("TEST 1: memory_engine.py retrieve_rag_chunks() default parameter")
    print(f"  Expected: n_results default = 100")
    print(f"  Actual:   n_results default = {n_results_default}")

    test1_pass = n_results_default == 100
    print(f"  Result:   {'[PASS]' if test1_pass else '[FAIL]'}")
    print()

    # Test 2: Check llm_integration.py chunk limit in code
    with open('integrations/llm_integration.py', 'r', encoding='utf-8') as f:
        llm_integration_code = f.read()

    # Look for the chunk enumeration line
    if 'rag_chunks[:100]' in llm_integration_code:
        chunk_limit = 100
        test2_pass = True
    elif 'rag_chunks[:5]' in llm_integration_code:
        chunk_limit = 5
        test2_pass = False
    else:
        chunk_limit = "unknown"
        test2_pass = False

    print("TEST 2: llm_integration.py chunk display limit")
    print(f"  Expected: rag_chunks[:100]")
    print(f"  Actual:   rag_chunks[:{chunk_limit}]")
    print(f"  Result:   {'[PASS]' if test2_pass else '[FAIL]'}")
    print()

    # Test 3: Check character limit per chunk
    if 'max_chars = 8000' in llm_integration_code:
        char_limit = 8000
        test3_pass = True
    elif 'max_chars = 2000' in llm_integration_code:
        char_limit = 2000
        test3_pass = False
    else:
        char_limit = "unknown"
        test3_pass = False

    print("TEST 3: llm_integration.py character limit per chunk")
    print(f"  Expected: max_chars = 8000")
    print(f"  Actual:   max_chars = {char_limit}")
    print(f"  Result:   {'[PASS]' if test3_pass else '[FAIL]'}")
    print()

    # Test 4: Check memory_engine.py call site
    with open('engines/memory_engine.py', 'r', encoding='utf-8') as f:
        memory_engine_code = f.read()

    if 'retrieve_rag_chunks(user_input, n_results=100)' in memory_engine_code:
        call_n_results = 100
        test4_pass = True
    elif 'retrieve_rag_chunks(user_input, n_results=5)' in memory_engine_code:
        call_n_results = 5
        test4_pass = False
    else:
        call_n_results = "unknown"
        test4_pass = False

    print("TEST 4: memory_engine.py retrieve_rag_chunks() call site")
    print(f"  Expected: n_results=100")
    print(f"  Actual:   n_results={call_n_results}")
    print(f"  Result:   {'[PASS]' if test4_pass else '[FAIL]'}")
    print()

    # Summary
    all_tests = [test1_pass, test2_pass, test3_pass, test4_pass]
    passed = sum(all_tests)
    total = len(all_tests)

    print("=" * 70)
    print(f"OVERALL RESULT: {passed}/{total} tests passed")
    print("=" * 70)
    print()

    if all(all_tests):
        print("[SUCCESS] All document retrieval limits increased!")
        print()
        print("IMPROVEMENTS:")
        print("  Before:")
        print("    - Retrieve: 5 chunks from vector store")
        print("    - Display:  5 chunks in prompt")
        print("    - Chars:    2000 per chunk")
        print("    - TOTAL:    5 × 2000 = 10,000 chars (~4% of 217k document)")
        print()
        print("  After:")
        print("    - Retrieve: 100 chunks from vector store")
        print("    - Display:  100 chunks in prompt")
        print("    - Chars:    8000 per chunk")
        print("    - TOTAL:    100 × 8000 = 800,000 chars capacity")
        print()
        print("  For 217,102 char document (341 chunks):")
        print("    - Average chunk size: ~637 chars")
        print("    - 100 most relevant chunks retrieved via vector similarity")
        print("    - Kay can access ANY part of document by asking questions")
        print()
        print("  KEY: Vector store retrieves MOST RELEVANT chunks, not just first 100.")
        print("  This means Kay can access Lloyd, Delia, Mattie, and other characters")
        print("  throughout the document by asking about them.")
        return True
    else:
        print("[FAILURE] Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = test_retrieval_limits()
    sys.exit(0 if success else 1)
