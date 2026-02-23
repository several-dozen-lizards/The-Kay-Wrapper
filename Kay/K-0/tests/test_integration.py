"""
Test script to verify llm_retrieval integration in main.py

This script tests that:
1. Old systems (semantic_knowledge, document_index) are disabled
2. New llm_retrieval system is active
3. Documents are correctly selected and loaded
"""

import subprocess
import sys
import time

def test_integration():
    """Run main.py with a test query and check logs."""

    print("=" * 60)
    print("INTEGRATION TEST: LLM Retrieval in Main.py")
    print("=" * 60)

    # Test query about pigeons
    test_query = "Tell me about the pigeons\nquit\n"

    print("\n[TEST] Starting main.py with pigeon query...")
    print(f"[TEST] Query: 'Tell me about the pigeons'")

    try:
        # Run main.py with test input
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        # Send test query
        output, _ = process.communicate(input=test_query, timeout=30)

        print("\n" + "=" * 60)
        print("OUTPUT:")
        print("=" * 60)
        print(output)
        print("=" * 60)

        # Check for old system logs (should NOT appear)
        old_system_indicators = [
            "[SEMANTIC] Loaded",
            "[DOCUMENT INDEX] Found",
            "[DOCUMENT INDEX] Searching",
            "semantic_knowledge.json"
        ]

        # Check for new system logs (should appear)
        new_system_indicators = [
            "[LLM Retrieval] Selecting relevant documents",
            "[LLM RETRIEVAL]"
        ]

        print("\n" + "=" * 60)
        print("VERIFICATION:")
        print("=" * 60)

        # Check old systems are disabled
        old_system_found = False
        for indicator in old_system_indicators:
            if indicator in output:
                print(f"❌ FAIL: Old system still active - found '{indicator}'")
                old_system_found = True

        if not old_system_found:
            print("✅ PASS: Old systems (semantic_knowledge, document_index) are disabled")

        # Check new system is active
        new_system_found = False
        for indicator in new_system_indicators:
            if indicator in output:
                print(f"✅ PASS: New system active - found '{indicator}'")
                new_system_found = True
                break

        if not new_system_found:
            print("❌ FAIL: New llm_retrieval system not found in logs")

        # Check for document selection
        if "Selected:" in output or "Loaded:" in output:
            print("✅ PASS: Documents were selected/loaded")
        else:
            print("⚠️  WARNING: No document selection logs found")

        # Check for deprecation messages
        if "DEPRECATED" in output:
            print("✅ PASS: Deprecation warnings present (old systems properly disabled)")

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)

        return not old_system_found and new_system_found

    except subprocess.TimeoutExpired:
        print("❌ FAIL: Test timed out after 30 seconds")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ FAIL: Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
