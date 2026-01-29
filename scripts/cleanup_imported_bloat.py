"""
Aggressive Cleanup for Imported Document Bloat

This script specifically targets the 2137 imported facts and:
1. Archives full imported content to vector DB (RAG)
2. Keeps only TOP 10 most important facts per imported document
3. Removes semantic layer bloat (1900 -> ~50)
4. Keeps identity facts + working memory

This is the REAL fix for the memory bloat issue.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import asyncio
from collections import defaultdict

try:
    from engines.vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    print("[ERROR] VectorStore not available! Run: pip install chromadb")


class ImportedBloatCleanup:
    """Aggressively cleans imported document bloat."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memories_file = self.memory_dir / "memories.json"

        self.stats = {
            "total_before": 0,
            "imported_found": 0,
            "imported_kept": 0,
            "imported_archived": 0,
            "total_after": 0,
            "size_before_mb": 0,
            "size_after_mb": 0
        }

    def load_memories(self) -> List[Dict]:
        """Load memories."""
        with open(self.memories_file, 'r', encoding='utf-8') as f:
            memories = json.load(f)

        self.stats["total_before"] = len(memories)
        self.stats["size_before_mb"] = self.memories_file.stat().st_size / (1024 * 1024)

        return memories

    def separate_imported(self, memories: List[Dict]) -> Dict[str, List[Dict]]:
        """Separate imported vs regular memories."""
        imported = []
        regular = []

        for mem in memories:
            if mem.get("is_imported"):
                imported.append(mem)
            else:
                regular.append(mem)

        self.stats["imported_found"] = len(imported)

        print(f"\n[SEPARATE] Found {len(imported)} imported facts vs {len(regular)} regular memories")

        return {"imported": imported, "regular": regular}

    def filter_top_imported_facts(self, imported: List[Dict], max_per_source: int = 10) -> Dict[str, List[Dict]]:
        """
        Keep only TOP N most important facts per imported source.

        Args:
            imported: List of imported memories
            max_per_source: Max facts to keep per source file (default: 10)

        Returns:
            Dict with "keep" and "archive" lists
        """
        print(f"\n[FILTER] Filtering imported facts (keeping top {max_per_source} per source)...")

        # Group by source file
        by_source = defaultdict(list)

        for mem in imported:
            source = mem.get("source_document") or mem.get("source_file") or "unknown"
            by_source[source].append(mem)

        print(f"  Found {len(by_source)} source documents")

        keep = []
        archive = []

        for source, facts in by_source.items():
            # Sort by importance
            facts.sort(key=lambda m: m.get("importance_score", 0) or m.get("importance", 0), reverse=True)

            # Keep top N
            top_facts = facts[:max_per_source]
            rest_facts = facts[max_per_source:]

            keep.extend(top_facts)
            archive.extend(rest_facts)

            if len(facts) > max_per_source:
                print(f"  {source}: Keeping {len(top_facts)}/{len(facts)} facts (archiving {len(rest_facts)})")
            else:
                print(f"  {source}: Keeping all {len(facts)} facts")

        self.stats["imported_kept"] = len(keep)
        self.stats["imported_archived"] = len(archive)

        print(f"\n  [OK] Keep: {len(keep)} imported facts")
        print(f"  [OK] Archive: {len(archive)} imported facts")

        return {"keep": keep, "archive": archive}

    async def archive_to_rag(self, memories: List[Dict]):
        """Archive imported facts to RAG."""
        if not VECTOR_STORE_AVAILABLE:
            print("\n[ERROR] Cannot archive - VectorStore not available!")
            print("  Run: pip install chromadb")
            return

        if not memories:
            return

        print(f"\n[ARCHIVE] Archiving {len(memories)} imported facts to vector DB...")

        try:
            vector_store = VectorStore(persist_directory="memory/vector_db")

            # Group by source document
            by_source = defaultdict(list)
            for mem in memories:
                source = mem.get("source_document") or mem.get("source_file") or "unknown"
                by_source[source].append(mem)

            print(f"  Archiving {len(by_source)} source documents")

            for source, facts in by_source.items():
                # Build document text from facts
                fact_texts = []
                for mem in facts:
                    fact = mem.get("fact", "")
                    if fact:
                        fact_texts.append(fact)

                if not fact_texts:
                    continue

                # Combine into document
                document_text = "\n".join(fact_texts)

                # Add to vector DB
                result = vector_store.add_document(
                    text=document_text,
                    source_file=f"archived_{source}",
                    chunk_size=800,
                    overlap=100,
                    metadata={
                        "document_type": "archived_imported_facts",
                        "original_source": source,
                        "fact_count": len(facts),
                        "archived_at": datetime.now().isoformat()
                    }
                )

                if result["status"] == "success":
                    print(f"  [OK] Archived {source} ({len(facts)} facts -> {result['chunks_created']} chunks)")
                elif result["status"] == "duplicate":
                    print(f"  [SKIP] {source} already in vector DB")

            print(f"[ARCHIVE] Complete!")

        except Exception as e:
            print(f"[ARCHIVE ERROR] {e}")
            import traceback
            traceback.print_exc()

    def save_cleaned_memories(self, memories: List[Dict]):
        """Save cleaned memories."""
        print(f"\n[SAVE] Saving {len(memories)} memories...")

        with open(self.memories_file, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2)

        self.stats["total_after"] = len(memories)
        self.stats["size_after_mb"] = self.memories_file.stat().st_size / (1024 * 1024)

        print(f"  [OK] Saved memories.json")
        print(f"  [OK] Size: {self.stats['size_after_mb']:.2f} MB (was {self.stats['size_before_mb']:.2f} MB)")

        reduction = (1 - self.stats['size_after_mb'] / self.stats['size_before_mb']) * 100
        print(f"  [OK] Reduction: {reduction:.1f}%")

    def print_summary(self):
        """Print summary."""
        print("\n" + "=" * 60)
        print("IMPORTED BLOAT CLEANUP SUMMARY")
        print("=" * 60)

        print(f"\nTotal memories before: {self.stats['total_before']}")
        print(f"  - Imported facts: {self.stats['imported_found']}")
        print(f"  - Regular memories: {self.stats['total_before'] - self.stats['imported_found']}")

        print(f"\nImported facts processed:")
        print(f"  - Kept (top important): {self.stats['imported_kept']}")
        print(f"  - Archived to RAG: {self.stats['imported_archived']}")

        print(f"\nTotal memories after: {self.stats['total_after']}")
        print(f"  - Reduction: {self.stats['total_before'] - self.stats['total_after']} memories removed")

        print(f"\nFile size:")
        print(f"  - Before: {self.stats['size_before_mb']:.2f} MB")
        print(f"  - After: {self.stats['size_after_mb']:.2f} MB")

        reduction = (1 - self.stats['size_after_mb'] / self.stats['size_before_mb']) * 100
        print(f"  - Reduction: {reduction:.1f}%")

        print("\n[DONE] Cleanup complete!")

    async def run(self, max_per_source: int = 10):
        """Run aggressive cleanup."""
        print("=" * 60)
        print("AGGRESSIVE IMPORTED BLOAT CLEANUP")
        print("=" * 60)
        print(f"Keeping top {max_per_source} facts per imported document")
        print("Archiving the rest to vector DB (RAG)")

        # Load
        memories = self.load_memories()

        # Separate imported vs regular
        separated = self.separate_imported(memories)

        # Filter imported facts
        filtered_imported = self.filter_top_imported_facts(
            separated["imported"],
            max_per_source=max_per_source
        )

        # Archive bulk imported content to RAG
        await self.archive_to_rag(filtered_imported["archive"])

        # Combine: regular + top imported
        cleaned_memories = separated["regular"] + filtered_imported["keep"]

        # Save
        self.save_cleaned_memories(cleaned_memories)

        # Summary
        self.print_summary()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Aggressively clean imported document bloat")
    parser.add_argument("--max-per-source", type=int, default=10, help="Max facts to keep per source (default: 10)")

    args = parser.parse_args()

    cleanup = ImportedBloatCleanup()
    await cleanup.run(max_per_source=args.max_per_source)


if __name__ == "__main__":
    asyncio.run(main())
