"""
Quick test to verify Memory Forest logging is working
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine

def test_forest_logs():
    """Test that forest logs appear during import"""

    print("=" * 60)
    print("TESTING MEMORY FOREST LOGGING")
    print("=" * 60)
    print()

    # Use existing test file
    test_file = "test_import.txt"

    if not os.path.exists(test_file):
        print(f"[ERROR] Test file not found: {test_file}")
        return
    print(f"[TEST] Test document: {os.path.basename(test_file)}")
    print()

    # Create importer
    importer = EmotionalMemoryImporter()
    memory_engine = MemoryEngine()

    # Import with logging
    print("[TEST] Starting import (watch for [MEMORY FOREST] logs)...")
    print("-" * 60)

    try:
        result = importer.import_to_memory_engine(test_file, memory_engine)

        print("-" * 60)
        print()
        print("[SUCCESS] Import complete!")
        print()
        print(f"[RESULTS]:")
        print(f"   - Document ID: {result['doc_id']}")
        print(f"   - Total chunks: {result['chunk_count']}")
        print(f"   - Core identity: {result['tier_distribution'].get('CORE_IDENTITY', 0)}")
        print(f"   - Emotional: {result['tier_distribution'].get('EMOTIONAL_ACTIVE', 0)}")
        print(f"   - Relational: {result['tier_distribution'].get('RELATIONAL_SEMANTIC', 0)}")
        print(f"   - Peripheral: {result['tier_distribution'].get('PERIPHERAL_ARCHIVE', 0)}")
        print()

        # Check for tree file
        tree_path = f"data/trees/tree_{result['doc_id']}.json"
        if os.path.exists(tree_path):
            print(f"[SUCCESS] Tree file exists: {tree_path}")

            # Show tree contents
            import json
            with open(tree_path, 'r') as f:
                tree_data = json.load(f)

            tree_info = tree_data.get('trees', {}).get(result['doc_id'], {})
            print(f"   - Title: {tree_info.get('title')}")
            print(f"   - Shape: {tree_info.get('shape_description')}")
            print(f"   - Branches: {len(tree_info.get('branches', []))}")
            for branch in tree_info.get('branches', []):
                try:
                    print(f"     - {branch['glyphs']} {branch['title']}: {len(branch['chunk_indices'])} chunks")
                except UnicodeEncodeError:
                    print(f"     - {branch['title']}: {len(branch['chunk_indices'])} chunks")
        else:
            print(f"[ERROR] Tree file not found: {tree_path}")

    except Exception as e:
        print(f"[ERROR] Error during import: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_forest_logs()
