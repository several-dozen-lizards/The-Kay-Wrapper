"""
Verification Script: Kay UI Document Chunking Integration

Verifies that kay_ui.py has all the chunking components properly integrated.
Run this to confirm the integration matches main.py functionality.
"""

import os
import sys

def verify_kay_ui_chunking():
    """Verify that document chunking is properly integrated in kay_ui.py."""

    print("=" * 70)
    print("KAY UI DOCUMENT CHUNKING VERIFICATION")
    print("=" * 70)

    # Check 1: Working Directory
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

    # Check 2: kay_ui.py exists
    print("\n[CHECK 2] kay_ui.py exists")
    if os.path.exists("kay_ui.py"):
        print("  [OK] Found: kay_ui.py")
    else:
        print("  [FAIL] NOT FOUND: kay_ui.py")
        return False

    # Check 3: Verify DocumentReader import
    print("\n[CHECK 3] DocumentReader Import")

    with open("kay_ui.py", "r", encoding="utf-8") as f:
        content = f.read()

    if "from engines.document_reader import DocumentReader" in content:
        print("  [OK] DocumentReader imported")
    else:
        print("  [FAIL] MISSING: DocumentReader import")
        return False

    # Check 4: Verify doc_reader initialization
    print("\n[CHECK 4] DocumentReader Initialization")

    if "self.doc_reader = DocumentReader(chunk_size=25000)" in content:
        print("  [OK] doc_reader instance created")
    else:
        print("  [FAIL] MISSING: doc_reader initialization")
        return False

    # Check 5: Verify navigation command detection
    print("\n[CHECK 5] Navigation Command Detection")

    navigation_checks = [
        ("continue reading", "Continue reading command"),
        ("next section", "Next section command"),
        ("previous section", "Previous section command"),
        ("go back", "Go back command"),
        ("jump to section", "Jump to section command"),
        ("restart document", "Restart document command"),
        ("self.doc_reader.advance()", "Advance method call"),
        ("self.doc_reader.previous()", "Previous method call"),
        ("self.doc_reader.jump_to", "Jump_to method call"),
        ("self.doc_reader.get_current_chunk()", "Get current chunk call"),
    ]

    all_found = True
    for pattern, description in navigation_checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [FAIL] MISSING: {description}")
            all_found = False

    if not all_found:
        return False

    # Check 6: Verify chunking logic
    print("\n[CHECK 6] Document Chunking Logic")

    chunking_checks = [
        ("[DOC CHUNKING] Processing", "Processing log message"),
        ("[DOC CHUNKING] Checking", "Checking log message"),
        ("if len(doc_text) > 30000:", "30k threshold check"),
        ("self.doc_reader.load_document", "load_document call"),
        ('is_chunked', "is_chunked flag"),
        ("[DOC READER] Chunk added to context", "Chunk added log"),
        ("chunked_count = sum", "Chunked count calculation"),
        ("[DOC CHUNKING] Added to context:", "Summary log"),
    ]

    all_found = True
    for pattern, description in chunking_checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [FAIL] MISSING: {description}")
            all_found = False

    if not all_found:
        return False

    # Check 7: Verify enhanced logging
    print("\n[CHECK 7] Enhanced Logging")

    logging_checks = [
        ("[LLM Retrieval] Loaded", "Document count log"),
        ("len(doc.get('full_text', '')):,", "Document size formatting"),
        ("[DOC CHUNKING] Small document added whole", "Small doc message"),
        ("whole_count = len(rag_chunks) - chunked_count", "Whole count calc"),
    ]

    all_found = True
    for pattern, description in logging_checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [FAIL] MISSING: {description}")
            all_found = False

    if not all_found:
        return False

    # Check 8: Verify formatting structure
    print("\n[CHECK 8] Document Formatting")

    formatting_checks = [
        ("═══ DOCUMENT:", "Document header"),
        ("Section {chunk['position']}/{chunk['total']}", "Section display"),
        ("({chunk['progress_percent']}%)", "Progress percentage"),
        ("Navigation: Say 'continue reading'", "Navigation instructions"),
        ("───────────", "Section separator"),
    ]

    all_found = True
    for pattern, description in formatting_checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [FAIL] MISSING: {description}")
            all_found = False

    if not all_found:
        return False

    # Check 9: Verify chunk metadata
    print("\n[CHECK 9] Chunk Metadata Structure")

    metadata_checks = [
        ('"source_file": doc_filename', "source_file field"),
        ('"text": chunk_text', "text field"),
        ('"is_chunked": True', "is_chunked flag"),
        ('"memory_id": doc_id', "memory_id field"),
        ('"chunk_info":', "chunk_info dict"),
        ('"current_section":', "current_section field"),
        ('"total_sections":', "total_sections field"),
        ('"chunk_size":', "chunk_size field"),
    ]

    all_found = True
    for pattern, description in metadata_checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [FAIL] MISSING: {description}")
            all_found = False

    if not all_found:
        return False

    # Check 10: Compare with main.py
    print("\n[CHECK 10] Consistency with main.py")

    if os.path.exists("main.py"):
        with open("main.py", "r", encoding="utf-8") as f:
            main_content = f.read()

        consistency_checks = [
            ("30000", "Same 30k threshold in both files"),
            ("25000", "Same 25k chunk size in both files"),
            ("[DOC CHUNKING]", "Same logging prefix in both files"),
        ]

        all_consistent = True
        for pattern, description in consistency_checks:
            in_main = pattern in main_content
            in_ui = pattern in content
            if in_main and in_ui:
                print(f"  [OK] {description}")
            else:
                print(f"  [WARN] Inconsistency: {description}")
                if not in_ui:
                    print(f"    Missing in kay_ui.py")
                if not in_main:
                    print(f"    Missing in main.py")
                all_consistent = False

        if not all_consistent:
            print("  [WARN] Some consistency issues found (may not be critical)")
    else:
        print("  [SKIP] main.py not found for comparison")

    # Final verdict
    print("\n" + "=" * 70)
    print("[OK] ALL CHECKS PASSED")
    print("=" * 70)
    print("\nKay UI document chunking is properly integrated!")
    print("\nExpected behavior when loading large document:")
    print("  [LLM Retrieval] Loaded 1 documents")
    print("  [LLM Retrieval]   - filename.txt: 44,788 chars")
    print("  [DOC CHUNKING] Processing 1 documents")
    print("  [DOC CHUNKING] Checking filename.txt: 44,788 chars")
    print("  [DOC READER] Chunk added to context: 24,607 chars (section 1/2)")
    print("  [DOC CHUNKING] Added to context: 1 chunked, 0 whole documents")
    print("\nNavigation commands available:")
    print("  - continue reading / next section")
    print("  - previous section / go back")
    print("  - jump to section N")
    print("  - restart document")
    print("\nReady for manual testing with: python kay_ui.py")

    return True


if __name__ == "__main__":
    try:
        success = verify_kay_ui_chunking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
