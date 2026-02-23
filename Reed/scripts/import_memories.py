#!/usr/bin/env python
"""
CLI Memory Import Tool for Reed
Imports archived documents into Reed's persistent memory

Usage:
    python import_memories.py --input ./archives/
    python import_memories.py --input document.pdf --dry-run
    python import_memories.py --input ./docs/ --start-date 2020-01-01 --end-date 2024-10-27
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_import import ImportManager, ImportProgress
from engines.memory_engine import MemoryEngine
from engines.entity_graph import EntityGraph
from agent_state import AgentState


def print_progress(progress: ImportProgress):
    """Print progress updates to console (ASCII-safe for Windows)."""
    status_symbol = {
        "idle": "[IDLE]",
        "parsing": "[PARSE]",
        "extracting": "[EXTRACT]",
        "integrating": "[SAVE]",
        "complete": "[DONE]",
        "error": "[ERROR]"
    }.get(progress.status, "[WORKING]")

    print(f"\r{status_symbol} {progress.status.upper()}: "
          f"Files {progress.processed_files}/{progress.total_files} | "
          f"Chunks {progress.processed_chunks}/{progress.total_chunks} | "
          f"Facts {progress.facts_extracted} | "
          f"Memories {progress.memories_imported}",
          end="", flush=True)


async def import_memories(args):
    """Main import function."""
    print("=" * 70)
    print("REED MEMORY IMPORT")
    print("=" * 70)

    # Initialize memory system
    print("\n[INIT] Loading Reed's memory system...")
    try:
        state = AgentState()
        memory_engine = MemoryEngine()
        entity_graph = memory_engine.entity_graph

        print(f"[INIT] Loaded {len(memory_engine.memories)} existing memories")
        print(f"[INIT] Loaded {len(entity_graph.entities)} existing entities")

    except Exception as e:
        print(f"[ERROR] Failed to initialize memory system: {e}")
        return 1

    # Initialize import manager
    manager = ImportManager(
        memory_engine=memory_engine,
        entity_graph=entity_graph,
        chunk_size=args.chunk_size,
        overlap=500,
        batch_size=args.batch_size
    )

    # Set progress callback
    manager.set_progress_callback(print_progress)

    # Collect input paths
    input_paths = []
    for input_path in args.input:
        path = Path(input_path)
        if not path.exists():
            print(f"[WARNING] Path does not exist: {input_path}")
            continue
        input_paths.append(str(path))

    if not input_paths:
        print("[ERROR] No valid input paths provided")
        return 1

    print(f"\n[INPUT] Processing {len(input_paths)} path(s)")

    # Import
    try:
        if args.dry_run:
            print("[DRY RUN] Extracting memories WITHOUT saving to database\n")
        else:
            print("[IMPORT] Extracting and saving memories\n")

        progress = await manager.import_files(
            file_paths=input_paths,
            dry_run=args.dry_run,
            start_date=args.start_date,
            end_date=args.end_date
        )

        # Print summary
        print("\n\n" + "=" * 70)
        print("IMPORT COMPLETE")
        print("=" * 70)
        print(f"\nFiles processed: {progress.processed_files}")
        print(f"Chunks processed: {progress.processed_chunks}")
        print(f"Facts extracted: {progress.facts_extracted}")

        if not args.dry_run:
            print(f"Memories imported: {progress.memories_imported}")
            print(f"\nMemory Tier Distribution:")
            print(f"  - Semantic: {progress.tier_distribution['semantic']}")
            print(f"  - Episodic: {progress.tier_distribution['episodic']}")
            print(f"  - Working: {progress.tier_distribution['working']}")

            print(f"\nEntities:")
            print(f"  - Created: {progress.entities_created}")
            print(f"  - Updated: {progress.entities_updated}")

        if progress.errors:
            print(f"\n[WARNING] Errors encountered: {len(progress.errors)}")
            for i, error in enumerate(progress.errors[:5]):  # Show first 5
                print(f"  {i+1}. {error}")
            if len(progress.errors) > 5:
                print(f"  ... and {len(progress.errors) - 5} more")

        elapsed = progress.get_elapsed_time()
        print(f"\nTime elapsed: {elapsed:.1f} seconds")

        return 0

    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Import interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\n[ERROR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Import archived documents into Reed's memory system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all documents in a directory
  python import_memories.py --input ./archives/

  # Import a single PDF
  python import_memories.py --input transcript.pdf

  # Dry run (preview without saving)
  python import_memories.py --input ./docs/ --dry-run

  # Import with date filter
  python import_memories.py --input ./archives/ --start-date 2020-01-01 --end-date 2024-10-27

  # Batch processing with custom chunk size
  python import_memories.py --input ./large_docs/ --chunk-size 5000 --batch-size 3
        """
    )

    parser.add_argument(
        '--input', '-i',
        required=True,
        nargs='+',
        help='Input file or directory path(s)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Extract memories without saving (preview mode)'
    )

    parser.add_argument(
        '--start-date',
        help='Filter by start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        help='Filter by end date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=3000,
        help='Document chunk size in characters (default: 3000)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=5,
        help='LLM batch size for rate limiting (default: 5)'
    )

    args = parser.parse_args()

    # Run async import
    exit_code = asyncio.run(import_memories(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
