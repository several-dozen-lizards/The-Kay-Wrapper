"""
Quick Cleanup - Remove Imported Bloat (No RAG Archival)

This is a FAST cleanup that:
1. Removes bulk imported facts (keeping only top 10 per source)
2. NO RAG archival (too slow with embedding generation)
3. User can re-import documents later with hybrid manager

This runs in seconds instead of minutes.
"""

import json
from pathlib import Path
from collections import defaultdict


def main():
    print("=" * 60)
    print("QUICK CLEANUP - REMOVE IMPORTED BLOAT")
    print("=" * 60)

    memory_file = Path("memory/memories.json")

    # Load
    print("\n[LOAD] Loading memories...")
    with open(memory_file, 'r', encoding='utf-8') as f:
        memories = json.load(f)

    total_before = len(memories)
    size_before_mb = memory_file.stat().st_size / (1024 * 1024)

    print(f"  Loaded: {total_before} memories ({size_before_mb:.2f} MB)")

    # Separate imported vs regular
    print("\n[SEPARATE] Separating imported vs regular...")
    imported = []
    regular = []

    for mem in memories:
        if mem.get("is_imported"):
            imported.append(mem)
        else:
            regular.append(mem)

    print(f"  Imported: {len(imported)}")
    print(f"  Regular: {len(regular)}")

    # Filter imported - keep only top 10 per source
    print("\n[FILTER] Keeping top 10 important facts per source...")

    by_source = defaultdict(list)
    for mem in imported:
        source = mem.get("source_document") or mem.get("source_file") or "unknown"
        by_source[source].append(mem)

    print(f"  Found {len(by_source)} source documents")

    kept_imported = []

    for source, facts in by_source.items():
        # Sort by importance
        facts.sort(key=lambda m: m.get("importance_score", 0) or m.get("importance", 0), reverse=True)

        # Keep top 10
        top = facts[:10]
        kept_imported.extend(top)

        print(f"  {source}: Keeping {len(top)}/{len(facts)} facts")

    # Combine
    print("\n[COMBINE] Combining regular + filtered imported...")
    cleaned = regular + kept_imported

    total_after = len(cleaned)
    removed = total_before - total_after

    print(f"  Total: {total_after} memories (removed {removed})")

    # Save
    print("\n[SAVE] Saving cleaned memories...")
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2)

    size_after_mb = memory_file.stat().st_size / (1024 * 1024)
    reduction = (1 - size_after_mb / size_before_mb) * 100

    print(f"  [OK] Saved {total_after} memories")
    print(f"  [OK] Size: {size_after_mb:.2f} MB (was {size_before_mb:.2f} MB)")
    print(f"  [OK] Reduction: {reduction:.1f}%")

    # Summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Before: {total_before} memories ({size_before_mb:.2f} MB)")
    print(f"After: {total_after} memories ({size_after_mb:.2f} MB)")
    print(f"Removed: {removed} memories ({reduction:.1f}% size reduction)")
    print("\n[DONE] Quick cleanup complete!")
    print("\nNOTE: Removed facts were NOT archived to RAG.")
    print("To preserve them, re-import original documents with:")
    print("  python -c 'from memory_import.hybrid_import_manager import HybridImportManager; ...'")


if __name__ == "__main__":
    main()
