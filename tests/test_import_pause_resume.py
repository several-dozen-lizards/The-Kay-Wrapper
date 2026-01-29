"""
Test script for Import Pause/Resume and Duplicate Detection functionality.

Tests:
1. ImportStateManager state persistence
2. DuplicateDetector file hashing and duplicate detection
3. End-to-end pause/resume workflow
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Test imports
try:
    from import_state_manager import ImportStateManager
    from duplicate_detector import DuplicateDetector
    print("[OK] Module imports successful")
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)


def test_state_manager():
    """Test ImportStateManager functionality."""
    print("\n=== Testing ImportStateManager ===")

    # Create temporary state file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_state_file = f.name

    try:
        manager = ImportStateManager(state_file=temp_state_file)

        # Test 1: Start import
        files = ["file1.txt", "file2.txt", "file3.txt"]
        session_id = manager.start_import(files)
        print(f"[OK] Started import session: {session_id}")

        # Test 2: Mark file completed
        manager.mark_file_completed("file1.txt", success=True)
        progress = manager.get_progress()
        assert progress['completed'] == 1
        assert progress['total'] == 3
        print(f"[OK] Progress tracking: {progress['completed']}/{progress['total']}")

        # Test 3: Pause import
        manager.pause_import()
        assert manager.is_paused()
        print("[OK] Import paused")

        # Test 4: Check state persistence
        manager._save_state()
        new_manager = ImportStateManager(state_file=temp_state_file)
        incomplete = new_manager.get_incomplete_import()
        assert incomplete is not None
        assert incomplete['total_files'] == 3
        print("[OK] State persistence verified")

        # Test 5: Resume import
        new_manager.current_session = incomplete
        new_manager.resume_import()
        assert not new_manager.is_paused()
        print("[OK] Import resumed")

        # Test 6: Complete import
        new_manager.mark_file_completed("file2.txt", success=True)
        new_manager.mark_file_completed("file3.txt", success=True)
        new_manager.complete_import()

        # Verify no incomplete import
        final_manager = ImportStateManager(state_file=temp_state_file)
        incomplete = final_manager.get_incomplete_import()
        assert incomplete is None
        print("[OK] Import completed successfully")

    finally:
        # Cleanup
        if os.path.exists(temp_state_file):
            os.remove(temp_state_file)


def test_duplicate_detector():
    """Test DuplicateDetector functionality."""
    print("\n=== Testing DuplicateDetector ===")

    # Create temporary files and documents.json
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = os.path.join(temp_dir, "test_doc.txt")
        with open(test_file, 'w') as f:
            f.write("This is a test document.")

        # Create mock documents.json
        docs_file = os.path.join(temp_dir, "documents.json")

        detector = DuplicateDetector(documents_file=docs_file)

        # Test 1: Calculate hash
        hash1 = detector.calculate_file_hash(test_file)
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars
        print(f"[OK] File hash calculated: {hash1[:16]}...")

        # Test 2: No duplicate (new file)
        dup_info = detector.check_duplicate(test_file)
        assert dup_info is None
        print("[OK] New file detected correctly")

        # Test 3: Create existing document record
        existing_docs = {
            "doc_001": {
                "filename": "test_doc.txt",
                "content_hash": hash1,
                "import_date": "2025-01-01",
                "chunk_count": 5
            }
        }

        with open(docs_file, 'w') as f:
            json.dump(existing_docs, f)

        # Test 4: Detect exact duplicate
        dup_info = detector.check_duplicate(test_file)
        assert dup_info is not None
        assert dup_info['is_duplicate'] is True
        assert dup_info['duplicate_type'] == 'exact'
        print("[OK] Exact duplicate detected")

        # Test 5: Detect updated file
        with open(test_file, 'w') as f:
            f.write("This is an UPDATED test document.")

        dup_info = detector.check_duplicate(test_file)
        assert dup_info is not None
        assert dup_info['duplicate_type'] == 'updated'
        print("[OK] Updated file detected")

        # Test 6: Get duplicate summary
        new_file = os.path.join(temp_dir, "new_file.txt")
        with open(new_file, 'w') as f:
            f.write("Brand new file")

        summary = detector.get_duplicate_summary([test_file, new_file])
        assert len(summary['new_files']) == 1
        assert len(summary['updated_files']) == 1
        assert summary['has_duplicates'] is True
        print("[OK] Duplicate summary generated")


def test_integration():
    """Test end-to-end workflow."""
    print("\n=== Testing Integration ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup
        state_file = os.path.join(temp_dir, "import_state.json")
        docs_file = os.path.join(temp_dir, "documents.json")

        manager = ImportStateManager(state_file=state_file)
        detector = DuplicateDetector(documents_file=docs_file)

        # Create test files
        file1 = os.path.join(temp_dir, "doc1.txt")
        file2 = os.path.join(temp_dir, "doc2.txt")

        with open(file1, 'w') as f:
            f.write("Document 1")
        with open(file2, 'w') as f:
            f.write("Document 2")

        # Simulate import workflow
        files = [file1, file2]

        # Check for duplicates (should be none)
        summary = detector.get_duplicate_summary(files)
        assert not summary['has_duplicates']
        print("[OK] No duplicates in initial import")

        # Start import session
        session_id = manager.start_import(files)
        print(f"[OK] Session started: {session_id}")

        # Process first file
        manager.mark_file_completed(file1, success=True)

        # Simulate pause
        manager.pause_import()
        print("[OK] Import paused after first file")

        # Simulate crash/restart
        new_manager = ImportStateManager(state_file=state_file)
        incomplete = new_manager.get_incomplete_import()
        assert incomplete is not None
        print("[OK] Crash recovery: incomplete import detected")

        # Resume and complete
        new_manager.current_session = incomplete
        new_manager.resume_import()
        new_manager.mark_file_completed(file2, success=True)
        new_manager.complete_import()
        print("[OK] Import completed after resume")

        # Verify completion
        final_manager = ImportStateManager(state_file=state_file)
        incomplete = final_manager.get_incomplete_import()
        assert incomplete is None
        print("[OK] No incomplete imports remain")


if __name__ == "__main__":
    print("="*60)
    print("Import Pause/Resume System Test Suite")
    print("="*60)

    try:
        test_state_manager()
        test_duplicate_detector()
        test_integration()

        print("\n" + "="*60)
        print("[OK] ALL TESTS PASSED")
        print("="*60)
        print("\nThe import pause/resume system is ready for use!")
        print("\nFeatures verified:")
        print("  • State persistence and recovery")
        print("  • Pause/resume functionality")
        print("  • Duplicate detection (exact and updated)")
        print("  • Crash recovery")
        print("  • Progress tracking")

    except AssertionError as e:
        print(f"\n[ERROR] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
