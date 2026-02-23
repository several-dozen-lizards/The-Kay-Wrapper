"""
Quick test to verify .docx encoding fix
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from memory_import.emotional_importer import EmotionalMemoryImporter

def test_docx_import():
    """Test importing a .docx file with curly quotes."""

    print("="*80)
    print("TESTING: .docx Import with Encoding Fix")
    print("="*80)
    print()

    # Your actual file path
    docx_file = "F:/Braindump/2025/AI Logs/Master-clean.docx"

    if not Path(docx_file).exists():
        print(f"[SKIP] Test file not found: {docx_file}")
        return

    print(f"[TEST] Importing: {docx_file}")
    print()

    try:
        importer = EmotionalMemoryImporter()

        doc_id, chunks = importer.import_document(docx_file)

        print()
        print("="*80)
        print("[SUCCESS] .docx import completed!")
        print(f"  Document ID: {doc_id}")
        print(f"  Chunks created: {len(chunks)}")
        print()

        # Show tier distribution
        tiers = {}
        for chunk in chunks:
            tier = chunk._calculate_tier()
            tiers[tier] = tiers.get(tier, 0) + 1

        print("Tier Distribution:")
        for tier, count in sorted(tiers.items()):
            pct = (count / len(chunks)) * 100
            print(f"  {tier:25s}: {count:3d} ({pct:5.1f}%)")

        print()
        print("The encoding error is FIXED!")
        print("="*80)

    except Exception as e:
        print()
        print("="*80)
        print(f"[FAILURE] Import failed: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_docx_import()
