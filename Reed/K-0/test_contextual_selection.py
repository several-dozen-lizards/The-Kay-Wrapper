"""
Test script for contextually-aware document selection.

Tests the _build_document_context() helper function to verify:
1. Time-based recency detection (10-minute window)
2. Implicit reference detection
3. Request type categorization
"""

import sys
from datetime import datetime, timedelta
from typing import List, Dict

# Add project root to path
sys.path.insert(0, 'F:\\AlphaKayZero')

from engines.llm_retrieval import _build_document_context


def test_recent_import_detection():
    """Test that recently imported documents are correctly identified."""
    print("\n=== TEST 1: Recent Import Detection ===")

    # Create mock documents
    now = datetime.now()
    recent_doc = {
        'doc_id': 'doc_1',
        'filename': 'YW-part1.txt',
        'upload_date': (now - timedelta(minutes=5)).isoformat()  # 5 minutes ago
    }
    old_doc = {
        'doc_id': 'doc_2',
        'filename': 'old_document.txt',
        'upload_date': (now - timedelta(minutes=30)).isoformat()  # 30 minutes ago
    }

    documents = [recent_doc, old_doc]
    query = "See if you can look past this beginning scene"

    context = _build_document_context(documents, query)

    print(f"Query: {query}")
    print(f"Recently imported: {context['recently_imported']}")
    print(f"Expected: ['doc_1']")

    assert 'doc_1' in context['recently_imported'], "Recent document should be detected"
    assert 'doc_2' not in context['recently_imported'], "Old document should not be detected"
    print("[PASS] Recent import detection working")


def test_implicit_reference_detection():
    """Test that implicit references are correctly detected."""
    print("\n=== TEST 2: Implicit Reference Detection ===")

    test_cases = [
        ("See if you can look past this beginning scene", True, "contains 'this'"),
        ("Tell me about that character", True, "contains 'that'"),
        ("Continue reading the document", True, "contains 'the document'"),
        ("What's the weather today?", False, "no implicit reference"),
        ("What happens to Mattie and Delia?", False, "no implicit reference"),
    ]

    documents = []  # Empty for this test

    for query, expected_result, reason in test_cases:
        context = _build_document_context(documents, query)
        result = context['has_implicit_reference']

        status = "[PASS]" if result == expected_result else "[FAIL]"
        print(f"{status}: '{query}' -> {result} ({reason})")

        assert result == expected_result, f"Failed for: {query}"

    print("[PASS] All implicit reference detection tests passed")


def test_request_type_categorization():
    """Test that request types are correctly categorized."""
    print("\n=== TEST 3: Request Type Categorization ===")

    test_cases = [
        ("Continue reading", "reading", "reading request"),
        ("See if you can look past this beginning scene", "analysis", "analysis request"),
        ("What happens to Mattie and Delia?", "navigation", "navigation request"),
        ("What's the weather today?", "general", "general request"),
        ("Tell me about the pigeons", "analysis", "analysis request"),
    ]

    documents = []  # Empty for this test

    for query, expected_type, reason in test_cases:
        context = _build_document_context(documents, query)
        result = context['request_type']

        status = "[PASS]" if result == expected_type else "[FAIL]"
        print(f"{status}: '{query}' -> {result} (expected: {expected_type}) - {reason}")

        assert result == expected_type, f"Failed for: {query}"

    print("[PASS] All request type categorization tests passed")


def test_combined_context():
    """Test combined context building with all signals."""
    print("\n=== TEST 4: Combined Context Building ===")

    # Simulate real scenario from user's problem
    now = datetime.now()
    documents = [
        {
            'doc_id': 'doc_yw_part1',
            'filename': 'YW-part1.txt',
            'upload_date': (now - timedelta(minutes=2)).isoformat()  # Just uploaded
        }
    ]

    query = "See if you can look past this beginning scene"

    context = _build_document_context(documents, query)

    print(f"Query: {query}")
    print(f"Recently imported: {context['recently_imported']}")
    print(f"Has implicit reference: {context['has_implicit_reference']}")
    print(f"Request type: {context['request_type']}")

    # This is the exact scenario from the user's problem
    assert len(context['recently_imported']) == 1, "Should have 1 recent document"
    assert context['has_implicit_reference'] == True, "Should detect 'this' reference"
    assert context['request_type'] == 'analysis', "Should categorize as analysis"

    print("[PASS] Combined context correctly identifies user's problem scenario")
    print("\nThis context should trigger document selection (not NONE)!")


if __name__ == "__main__":
    print("=" * 60)
    print("CONTEXTUAL SELECTION TESTS")
    print("=" * 60)

    try:
        test_recent_import_detection()
        test_implicit_reference_detection()
        test_request_type_categorization()
        test_combined_context()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        print("\nContextual selection logic is working correctly.")
        print("Ready for integration testing with real documents.")

    except AssertionError as e:
        print(f"\n[TEST FAILED]: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
