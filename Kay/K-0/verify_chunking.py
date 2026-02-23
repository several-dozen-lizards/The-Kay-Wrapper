"""
Verification Script: Document Chunking Integration

Confirms that main.py has the correct chunking code with enhanced logging.
Run this to verify you're using the updated version.
"""

import os
import sys

def verify_chunking_integration():
    """Verify that document chunking is properly integrated."""

    print("=" * 60)
    print("DOCUMENT CHUNKING VERIFICATION")
    print("=" * 60)

    # Check 1: Correct directory
    print("\n[CHECK 1] Working Directory")
    cwd = os.getcwd()
    expected_dir = "AlphaKayZero"

    if expected_dir in cwd and "K-0" not in cwd:
        print(f"  [OK] Correct: {cwd}")
    else:
        print(f"  [FAIL] WRONG: {cwd}")
        if "K-0" in cwd:
            print("  WARNING: You're in the K-0 directory!")
            print("  Run from F:\\AlphaKayZero instead")
        return False

    # Check 2: main.py exists
    print("\n[CHECK 2] main.py exists")
    if os.path.exists("main.py"):
        print("  [OK] Found: main.py")
    else:
        print("  [FAIL] NOT FOUND: main.py")
        return False

    # Check 3: Verify enhanced logging exists
    print("\n[CHECK 3] Enhanced Logging")

    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("[DOC CHUNKING] Processing", "Document processing log"),
        ("[DOC CHUNKING] Checking", "Document checking log"),
        ("[DOC CHUNKING] Added to context:", "Summary log with counts"),
        ("chunked_count = sum", "Chunked count calculation"),
    ]

    all_found = True
    for pattern, description in checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [FAIL] MISSING: {description}")
            all_found = False

    # Check 4: Old message NOT present
    print("\n[CHECK 4] Old Messages Removed")

    old_patterns = [
        "[DEBUG] Added 3 documents to context as RAG chunks",
        "[DEBUG] Added {len(rag_chunks)} documents to context as RAG chunks"
    ]

    old_found = False
    for pattern in old_patterns:
        if pattern in content:
            print(f"  [FAIL] FOUND OLD MESSAGE: {pattern}")
            old_found = True

    if not old_found:
        print("  [OK] No old messages found")

    # Check 5: DocumentReader import
    print("\n[CHECK 5] DocumentReader Integration")

    if "from engines.document_reader import DocumentReader" in content:
        print("  [OK] DocumentReader imported")
    else:
        print("  [FAIL] MISSING: DocumentReader import")
        all_found = False

    if "doc_reader = DocumentReader(chunk_size=25000)" in content:
        print("  [OK] DocumentReader initialized")
    else:
        print("  [FAIL] MISSING: DocumentReader initialization")
        all_found = False

    # Check 6: Chunking threshold
    print("\n[CHECK 6] Chunking Threshold")

    if "if len(doc_text) > 30000:" in content:
        print("  [OK] 30k char threshold set")
    else:
        print("  [FAIL] MISSING: 30k threshold")
        all_found = False

    # Check 7: llm_integration.py truncation fix
    print("\n[CHECK 7] LLM Integration Truncation Fix")

    if os.path.exists("integrations/llm_integration.py"):
        with open("integrations/llm_integration.py", "r", encoding="utf-8") as f:
            llm_content = f.read()

        if "is_chunked" in llm_content and "DocumentReader chunks" in llm_content:
            print("  [OK] Truncation fix applied")
        else:
            print("  [FAIL] MISSING: Truncation fix in llm_integration.py")
            all_found = False
    else:
        print("  [FAIL] NOT FOUND: integrations/llm_integration.py")
        all_found = False

    # Final verdict
    print("\n" + "=" * 60)

    if all_found and not old_found:
        print("[OK] ALL CHECKS PASSED")
        print("=" * 60)
        print("\nDocument chunking is properly integrated!")
        print("\nExpected terminal output when loading large document:")
        print("  [LLM Retrieval] Loaded 1 documents")
        print("  [LLM Retrieval]   - filename.txt: 217,102 chars")
        print("  [DOC CHUNKING] Processing 1 documents")
        print("  [DOC CHUNKING] Checking filename.txt: 217,102 chars")
        print("  [DOC READER] Large document detected: filename.txt (217,102 chars)")
        print("  [DOC READER] Loaded: 9 chunks")
        print("  [DOC READER] Chunk added to context: 24,873 chars (section 1/9)")
        print("  [DOC CHUNKING] Added to context: 1 chunked, 0 whole documents")
        return True
    else:
        print("[FAIL] VERIFICATION FAILED")
        print("=" * 60)
        print("\nSome checks did not pass. Review the errors above.")

        if old_found:
            print("\nWARNING: Old messages detected!")
            print("You may be running an outdated version of main.py")
            print("Ensure you're using the correct file")

        return False


if __name__ == "__main__":
    success = verify_chunking_integration()
    sys.exit(0 if success else 1)
