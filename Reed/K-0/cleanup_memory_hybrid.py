"""
Memory Cleanup and Migration to Hybrid RAG System

This script:
1. Backs up existing memory files
2. Analyzes current memory bloat
3. Archives old conversational content to vector DB
4. Removes abstract entities
5. Deduplicates facts
6. Keeps only: identity facts + working memory (last 20 turns)
7. Exports cleaned database

SAFE: Creates backups before any changes
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set
import asyncio

# Import vector store for archival
try:
    from engines.vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    print("[WARNING] VectorStore not available - will skip archival")


class MemoryCleanup:
    """Cleans up bloated memory and migrates to hybrid RAG architecture."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.backup_dir = self.memory_dir / "backups" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # File paths
        self.memories_file = self.memory_dir / "memories.json"
        self.entities_file = self.memory_dir / "entity_graph.json"
        self.identity_file = self.memory_dir / "identity_memory.json"
        self.layers_file = self.memory_dir / "memory_layers.json"

        # Stats
        self.stats = {
            "original_memories": 0,
            "archived_to_rag": 0,
            "kept_in_structured": 0,
            "duplicates_removed": 0,
            "abstract_entities_removed": 0,
            "identity_facts_kept": 0,
            "working_memory_kept": 0,
            "size_before_mb": 0,
            "size_after_mb": 0
        }

        # Abstract concepts to remove
        self.abstract_concepts = {
            "desire", "contradiction", "rumor", "glitch", "fossil",
            "emotion", "feeling", "thought", "idea", "concept",
            "fear", "hope", "worry", "dream", "aspiration",
            "goal", "plan", "intention", "wish", "preference",
            "memory", "experience", "event", "moment", "situation",
            "problem", "issue", "challenge", "conflict", "tension",
            "pattern", "thread", "loop", "recursion", "emergence"
        }

    def backup_files(self):
        """Create backups of all memory files."""
        print(f"\n[BACKUP] Creating backups in {self.backup_dir}...")

        os.makedirs(self.backup_dir, exist_ok=True)

        files_to_backup = [
            self.memories_file,
            self.entities_file,
            self.identity_file,
            self.layers_file
        ]

        for file_path in files_to_backup:
            if file_path.exists():
                backup_path = self.backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] Backed up {file_path.name} ({size_mb:.2f} MB)")

        print(f"[BACKUP] Complete! Files saved to: {self.backup_dir}")

    def load_memories(self) -> List[Dict[str, Any]]:
        """Load memories from JSON."""
        if not self.memories_file.exists():
            print("[ERROR] memories.json not found!")
            return []

        with open(self.memories_file, 'r', encoding='utf-8') as f:
            memories = json.load(f)

        self.stats["original_memories"] = len(memories)
        self.stats["size_before_mb"] = self.memories_file.stat().st_size / (1024 * 1024)

        print(f"\n[LOAD] Loaded {len(memories)} memories ({self.stats['size_before_mb']:.2f} MB)")
        return memories

    def analyze_memories(self, memories: List[Dict]) -> Dict[str, Any]:
        """Analyze memory composition."""
        print("\n[ANALYZE] Memory composition:")

        analysis = {
            "by_type": {},
            "by_perspective": {},
            "by_layer": {},
            "turns_range": [float('inf'), 0],
            "is_imported": 0,
            "is_identity": 0,
            "has_fact": 0,
            "duplicates": 0
        }

        seen_facts = set()

        for mem in memories:
            # Type distribution
            mem_type = mem.get("type", "unknown")
            analysis["by_type"][mem_type] = analysis["by_type"].get(mem_type, 0) + 1

            # Perspective distribution
            perspective = mem.get("perspective", "unknown")
            analysis["by_perspective"][perspective] = analysis["by_perspective"].get(perspective, 0) + 1

            # Layer distribution
            layer = mem.get("current_layer", "unknown")
            analysis["by_layer"][layer] = analysis["by_layer"].get(layer, 0) + 1

            # Turn range
            turn = mem.get("turn_number") or mem.get("turn_index") or 0
            if turn:
                analysis["turns_range"][0] = min(analysis["turns_range"][0], turn)
                analysis["turns_range"][1] = max(analysis["turns_range"][1], turn)

            # Flags
            if mem.get("is_imported"):
                analysis["is_imported"] += 1
            if mem.get("is_identity"):
                analysis["is_identity"] += 1

            # Fact tracking
            fact = mem.get("fact", "")
            if fact:
                analysis["has_fact"] += 1
                fact_normalized = fact.lower().strip()
                if fact_normalized in seen_facts:
                    analysis["duplicates"] += 1
                else:
                    seen_facts.add(fact_normalized)

        # Print analysis
        print(f"  Types: {analysis['by_type']}")
        print(f"  Perspectives: {analysis['by_perspective']}")
        print(f"  Layers: {analysis['by_layer']}")
        print(f"  Turn range: {analysis['turns_range'][0]} to {analysis['turns_range'][1]}")
        print(f"  Imported facts: {analysis['is_imported']}")
        print(f"  Identity facts: {analysis['is_identity']}")
        print(f"  Duplicates detected: {analysis['duplicates']}")

        return analysis

    def clean_memories(self, memories: List[Dict], keep_last_n_turns: int = 20) -> Dict[str, List[Dict]]:
        """
        Clean memories according to hybrid RAG conventions.

        Returns:
            Dict with:
                - "keep": Memories to keep in structured storage
                - "archive": Memories to archive to vector DB
                - "discard": Duplicate/invalid memories to discard
        """
        print(f"\n[CLEAN] Cleaning memories (keeping last {keep_last_n_turns} turns)...")

        keep = []
        archive = []
        discard = []

        # Get max turn number
        max_turn = max((m.get("turn_number") or m.get("turn_index") or 0) for m in memories)
        working_memory_threshold = max(0, max_turn - keep_last_n_turns)

        print(f"  Max turn: {max_turn}")
        print(f"  Working memory threshold: {working_memory_threshold}")

        seen_facts = set()

        for mem in memories:
            mem_type = mem.get("type", "unknown")
            turn = mem.get("turn_number") or mem.get("turn_index") or 0
            fact = mem.get("fact", "")
            fact_normalized = fact.lower().strip()

            # RULE 1: Always keep identity facts
            if mem.get("is_identity"):
                keep.append(mem)
                self.stats["identity_facts_kept"] += 1
                continue

            # RULE 2: Check for duplicates
            if fact and fact_normalized in seen_facts:
                discard.append(mem)
                self.stats["duplicates_removed"] += 1
                continue

            if fact:
                seen_facts.add(fact_normalized)

            # RULE 3: Keep working memory (last N turns)
            if turn >= working_memory_threshold:
                keep.append(mem)
                self.stats["working_memory_kept"] += 1
                continue

            # RULE 4: Keep high-importance semantic memories
            importance = mem.get("importance_score", 0) or mem.get("importance", 0)
            current_layer = mem.get("current_layer", "")

            if current_layer == "semantic" and importance >= 0.8:
                keep.append(mem)
                continue

            # RULE 5: Archive old conversational content to RAG
            if mem_type in ["full_turn", "extracted_fact"]:
                # Archive full turns and old facts to vector DB
                archive.append(mem)
                continue

            # RULE 6: Discard glyph summaries (metadata only)
            if mem_type == "glyph_summary":
                discard.append(mem)
                continue

            # Default: Keep if uncertain
            keep.append(mem)

        self.stats["kept_in_structured"] = len(keep)
        self.stats["archived_to_rag"] = len(archive)

        print(f"  [OK] Keep: {len(keep)} memories")
        print(f"  [OK] Archive to RAG: {len(archive)} memories")
        print(f"  [OK] Discard: {len(discard)} memories")

        return {
            "keep": keep,
            "archive": archive,
            "discard": discard
        }

    async def archive_to_vector_db(self, memories: List[Dict]):
        """Archive old memories to vector DB."""
        if not VECTOR_STORE_AVAILABLE:
            print("\n[ARCHIVE] Skipping archival (VectorStore not available)")
            return

        if not memories:
            print("\n[ARCHIVE] No memories to archive")
            return

        print(f"\n[ARCHIVE] Archiving {len(memories)} memories to vector DB...")

        try:
            vector_store = VectorStore(persist_directory="memory/vector_db")

            # Group by conversation turns
            turn_groups = {}
            for mem in memories:
                turn = mem.get("turn_number") or mem.get("turn_index") or 0
                if turn not in turn_groups:
                    turn_groups[turn] = []
                turn_groups[turn].append(mem)

            print(f"  Grouped into {len(turn_groups)} conversation turns")

            # Archive each turn as a document
            for turn, turn_memories in turn_groups.items():
                # Build turn text
                turn_text_parts = []

                for mem in turn_memories:
                    if mem.get("type") == "full_turn":
                        user_input = mem.get("user_input", "")
                        response = mem.get("response", "")
                        if user_input:
                            turn_text_parts.append(f"User: {user_input}")
                        if response:
                            turn_text_parts.append(f"Kay: {response}")
                    elif mem.get("type") == "extracted_fact":
                        fact = mem.get("fact", "")
                        if fact:
                            turn_text_parts.append(f"Fact: {fact}")

                if not turn_text_parts:
                    continue

                turn_text = "\n".join(turn_text_parts)

                # Add to vector DB
                result = vector_store.add_document(
                    text=turn_text,
                    source_file=f"archived_turn_{turn}.txt",
                    chunk_size=800,
                    overlap=100,
                    metadata={
                        "document_type": "archived_memory",
                        "turn_number": turn,
                        "archived_at": datetime.now().isoformat()
                    }
                )

                if result["status"] == "success":
                    print(f"  [OK] Archived turn {turn} ({result['chunks_created']} chunks)")

            print(f"[ARCHIVE] Complete! {len(turn_groups)} turns archived to vector DB")

        except Exception as e:
            print(f"[ARCHIVE ERROR] {e}")

    def clean_entities(self) -> Dict[str, Any]:
        """Clean entity graph by removing abstract concepts."""
        if not self.entities_file.exists():
            print("\n[ENTITIES] entity_graph.json not found, skipping...")
            return {}

        print("\n[ENTITIES] Cleaning entity graph...")

        with open(self.entities_file, 'r', encoding='utf-8') as f:
            entity_data = json.load(f)

        entities = entity_data.get("entities", {})
        original_count = len(entities)

        print(f"  Original entities: {original_count}")

        # Remove abstract concepts
        cleaned_entities = {}
        removed = []

        for entity_name, entity_obj in entities.items():
            entity_lower = entity_name.lower().strip()

            # Check if abstract concept
            if entity_lower in self.abstract_concepts:
                removed.append(entity_name)
                self.stats["abstract_entities_removed"] += 1
                continue

            # Check if starts with lowercase (likely not a proper noun)
            if entity_name and entity_name[0].islower():
                removed.append(entity_name)
                self.stats["abstract_entities_removed"] += 1
                continue

            # Keep entity
            cleaned_entities[entity_name] = entity_obj

        entity_data["entities"] = cleaned_entities

        print(f"  [OK] Kept: {len(cleaned_entities)} entities")
        print(f"  [OK] Removed: {len(removed)} abstract entities")

        if removed:
            print(f"  Removed entities: {', '.join(removed[:20])}")
            if len(removed) > 20:
                print(f"  ... and {len(removed) - 20} more")

        return entity_data

    def save_cleaned_memories(self, memories: List[Dict]):
        """Save cleaned memories to disk."""
        print("\n[SAVE] Saving cleaned memories...")

        with open(self.memories_file, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2)

        self.stats["size_after_mb"] = self.memories_file.stat().st_size / (1024 * 1024)

        print(f"  [OK] Saved {len(memories)} memories")
        print(f"  [OK] Size: {self.stats['size_after_mb']:.2f} MB (was {self.stats['size_before_mb']:.2f} MB)")
        print(f"  [OK] Reduction: {(1 - self.stats['size_after_mb'] / self.stats['size_before_mb']) * 100:.1f}%")

    def save_cleaned_entities(self, entity_data: Dict[str, Any]):
        """Save cleaned entity graph."""
        if not entity_data:
            return

        print("\n[SAVE] Saving cleaned entity graph...")

        with open(self.entities_file, 'w', encoding='utf-8') as f:
            json.dump(entity_data, f, indent=2)

        print(f"  [OK] Saved entity graph")

    def print_summary(self):
        """Print cleanup summary."""
        print("\n" + "=" * 60)
        print("CLEANUP SUMMARY")
        print("=" * 60)

        print(f"\nOriginal memories: {self.stats['original_memories']}")
        print(f"Size before: {self.stats['size_before_mb']:.2f} MB")
        print(f"\nKept in structured memory: {self.stats['kept_in_structured']}")
        print(f"  - Identity facts: {self.stats['identity_facts_kept']}")
        print(f"  - Working memory: {self.stats['working_memory_kept']}")
        print(f"\nArchived to RAG: {self.stats['archived_to_rag']}")
        print(f"Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"Abstract entities removed: {self.stats['abstract_entities_removed']}")
        print(f"\nSize after: {self.stats['size_after_mb']:.2f} MB")

        reduction = (1 - self.stats['size_after_mb'] / self.stats['size_before_mb']) * 100
        print(f"Size reduction: {reduction:.1f}%")

        print("\n[DONE] Cleanup complete!")
        print(f"Backups saved to: {self.backup_dir}")

    async def run(self, keep_last_n_turns: int = 20, archive_to_rag: bool = True):
        """Run full cleanup process."""
        print("=" * 60)
        print("MEMORY CLEANUP AND MIGRATION TO HYBRID RAG")
        print("=" * 60)

        # Step 1: Backup
        self.backup_files()

        # Step 2: Load and analyze
        memories = self.load_memories()
        if not memories:
            print("[ERROR] No memories to clean!")
            return

        analysis = self.analyze_memories(memories)

        # Step 3: Clean memories
        cleaned = self.clean_memories(memories, keep_last_n_turns)

        # Step 4: Archive to vector DB (optional)
        if archive_to_rag and cleaned["archive"]:
            await self.archive_to_vector_db(cleaned["archive"])
        else:
            print(f"\n[ARCHIVE] Skipping archival (disabled or no memories to archive)")

        # Step 5: Clean entities
        cleaned_entities = self.clean_entities()

        # Step 6: Save cleaned data
        self.save_cleaned_memories(cleaned["keep"])
        if cleaned_entities:
            self.save_cleaned_entities(cleaned_entities)

        # Step 7: Summary
        self.print_summary()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Clean up bloated memory and migrate to hybrid RAG")
    parser.add_argument("--keep-turns", type=int, default=20, help="Number of recent turns to keep (default: 20)")
    parser.add_argument("--no-archive", action="store_true", help="Skip archiving to vector DB")
    parser.add_argument("--memory-dir", type=str, default="memory", help="Memory directory path")

    args = parser.parse_args()

    cleanup = MemoryCleanup(memory_dir=args.memory_dir)
    await cleanup.run(
        keep_last_n_turns=args.keep_turns,
        archive_to_rag=not args.no_archive
    )


if __name__ == "__main__":
    asyncio.run(main())
