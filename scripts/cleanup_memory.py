"""
Memory Cleanup Script for Kay Zero
Backs up current memory and creates fresh start
"""

import json
import shutil
import os
from datetime import datetime
from pathlib import Path


def backup_memory_files(backup_dir: str = None):
    """
    Create backup of all memory files.

    Args:
        backup_dir: Custom backup directory (default: memory/backups/TIMESTAMP)

    Returns:
        Path to backup directory
    """
    if backup_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"memory/backups/backup_{timestamp}"

    os.makedirs(backup_dir, exist_ok=True)

    memory_files = [
        "memory/memories.json",
        "memory/entity_graph.json",
        "memory/memory_layers.json",
        "memory/identity_memory.json",
        "memory/preferences.json",
        "memory/motifs.json",
        "memory/memory_index.json",
        "memory/identity_index.json",
    ]

    backed_up = []
    for file_path in memory_files:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            dest = os.path.join(backup_dir, filename)
            shutil.copy2(file_path, dest)

            # Get file size
            size = os.path.getsize(file_path)
            size_kb = size / 1024

            backed_up.append((filename, size_kb))
            print(f"  [BACKUP] {filename} ({size_kb:.1f} KB)")

    return backup_dir, backed_up


def get_memory_stats():
    """Get current memory statistics before cleanup."""
    stats = {}

    try:
        with open("memory/memories.json", "r") as f:
            memories = json.load(f)
            stats["total_memories"] = len(memories)

            # Count by type
            types = {}
            for mem in memories:
                mem_type = mem.get("type", "unknown")
                types[mem_type] = types.get(mem_type, 0) + 1
            stats["by_type"] = types

            # Count by perspective
            perspectives = {}
            for mem in memories:
                persp = mem.get("perspective", "unknown")
                perspectives[persp] = perspectives.get(persp, 0) + 1
            stats["by_perspective"] = perspectives

            # Count imported vs live
            imported = sum(1 for mem in memories if mem.get("is_imported", False))
            stats["imported"] = imported
            stats["live_conversation"] = len(memories) - imported

    except:
        stats["total_memories"] = 0

    try:
        with open("memory/entity_graph.json", "r") as f:
            entities = json.load(f)
            stats["entities"] = len(entities.get("entities", {}))
    except:
        stats["entities"] = 0

    try:
        with open("memory/identity_memory.json", "r") as f:
            identity = json.load(f)
            stats["identity_re"] = len(identity.get("re", []))
            stats["identity_kay"] = len(identity.get("kay", []))
    except:
        stats["identity_re"] = 0
        stats["identity_kay"] = 0

    return stats


def create_fresh_memory_files():
    """Create fresh, empty memory files."""

    # Fresh memories.json
    with open("memory/memories.json", "w") as f:
        json.dump([], f, indent=2)
    print("  [CREATED] memories.json (empty)")

    # Fresh entity_graph.json
    entity_graph = {
        "entities": {},
        "relationships": []
    }
    with open("memory/entity_graph.json", "w") as f:
        json.dump(entity_graph, f, indent=2)
    print("  [CREATED] entity_graph.json (empty)")

    # Fresh memory_layers.json
    memory_layers = {
        "working": [],
        "episodic": [],
        "semantic": []
    }
    with open("memory/memory_layers.json", "w") as f:
        json.dump(memory_layers, f, indent=2)
    print("  [CREATED] memory_layers.json (empty)")

    # Fresh identity_memory.json
    identity_memory = {
        "re": [],
        "kay": [],
        "entities": {}
    }
    with open("memory/identity_memory.json", "w") as f:
        json.dump(identity_memory, f, indent=2)
    print("  [CREATED] identity_memory.json (empty)")

    # Fresh preferences.json
    preferences = {
        "domains": {},
        "contradictions": []
    }
    with open("memory/preferences.json", "w") as f:
        json.dump(preferences, f, indent=2)
    print("  [CREATED] preferences.json (empty)")

    # Fresh motifs.json
    motifs = {
        "entities": {},
        "last_updated": datetime.now().isoformat()
    }
    with open("memory/motifs.json", "w") as f:
        json.dump(motifs, f, indent=2)
    print("  [CREATED] motifs.json (empty)")


def cleanup_memory(keep_identity: bool = False, dry_run: bool = False):
    """
    Clean Kay's memory with backup.

    Args:
        keep_identity: If True, preserve identity facts (Re and Kay's core info)
        dry_run: If True, only show what would be deleted without actually deleting

    Returns:
        Tuple of (backup_path, stats_before, stats_after)
    """
    print("=" * 70)
    print("KAY ZERO MEMORY CLEANUP")
    print("=" * 70)

    # Get stats before cleanup
    print("\n[STATS] Current memory state:")
    stats_before = get_memory_stats()
    print(f"  Total memories: {stats_before.get('total_memories', 0)}")
    print(f"  - Live conversation: {stats_before.get('live_conversation', 0)}")
    print(f"  - Imported: {stats_before.get('imported', 0)}")
    print(f"  Entities: {stats_before.get('entities', 0)}")
    print(f"  Identity facts: {stats_before.get('identity_re', 0)} (Re) + {stats_before.get('identity_kay', 0)} (Kay)")

    if stats_before.get("by_type"):
        print(f"  By type: {stats_before['by_type']}")

    if dry_run:
        print("\n[DRY RUN] Showing what would be deleted (not actually deleting)")
        print("\nFiles that would be backed up:")
        print("  - memories.json")
        print("  - entity_graph.json")
        print("  - memory_layers.json")
        if not keep_identity:
            print("  - identity_memory.json")
            print("  - preferences.json")
        print("  - motifs.json")

        print("\nTo actually clean, run without --dry-run")
        return None, stats_before, None

    # Confirm with user
    print("\n[WARNING] This will DELETE all memories and create fresh start!")
    if keep_identity:
        print("[INFO] Identity facts (Re and Kay's core info) will be PRESERVED")
    else:
        print("[WARNING] Identity facts will also be DELETED (fresh start)")

    confirm = input("\nType 'yes' to confirm cleanup: ")
    if confirm.lower() != 'yes':
        print("\n[CANCELLED] Cleanup cancelled by user")
        return None, stats_before, None

    # Backup
    print("\n[BACKUP] Creating backup...")
    backup_path, backed_up = backup_memory_files()
    print(f"[BACKUP] Complete! Saved to: {backup_path}")
    print(f"[BACKUP] Backed up {len(backed_up)} files")

    # Clean
    print("\n[CLEANUP] Creating fresh memory files...")

    if keep_identity:
        # Load existing identity
        try:
            with open("memory/identity_memory.json", "r") as f:
                existing_identity = json.load(f)
            print("[PRESERVE] Keeping existing identity facts")
        except:
            existing_identity = {"re": [], "kay": [], "entities": {}}
            print("[PRESERVE] No existing identity to preserve")

    # Create fresh files
    create_fresh_memory_files()

    # Restore identity if requested
    if keep_identity and existing_identity:
        with open("memory/identity_memory.json", "w") as f:
            json.dump(existing_identity, f, indent=2)
        print(f"[RESTORE] Identity facts restored: {len(existing_identity.get('re', []))} Re + {len(existing_identity.get('kay', []))} Kay")

    # Get stats after cleanup
    stats_after = get_memory_stats()

    print("\n[CLEANUP] Complete!")
    print(f"  Memories: {stats_before.get('total_memories', 0)} → {stats_after.get('total_memories', 0)}")
    print(f"  Entities: {stats_before.get('entities', 0)} → {stats_after.get('entities', 0)}")

    # Rebuild indexes
    print("\n[INDEXES] Memory indexes cleared (rebuild with: python build_memory_indexes.py)")

    return backup_path, stats_before, stats_after


def list_backups():
    """List all available backups."""
    backup_dir = "memory/backups"

    if not os.path.exists(backup_dir):
        print("No backups found")
        return []

    backups = []
    for dirname in sorted(os.listdir(backup_dir), reverse=True):
        backup_path = os.path.join(backup_dir, dirname)
        if os.path.isdir(backup_path):
            # Get backup timestamp from dirname
            timestamp_str = dirname.replace("backup_", "")

            # Count files in backup
            files = os.listdir(backup_path)

            backups.append({
                "path": backup_path,
                "name": dirname,
                "timestamp": timestamp_str,
                "file_count": len(files)
            })

    return backups


def restore_backup(backup_path: str, dry_run: bool = False):
    """
    Restore memory from backup.

    Args:
        backup_path: Path to backup directory
        dry_run: If True, show what would be restored without actually restoring
    """
    if not os.path.exists(backup_path):
        print(f"[ERROR] Backup not found: {backup_path}")
        return False

    print("=" * 70)
    print("RESTORE FROM BACKUP")
    print("=" * 70)

    files_to_restore = [f for f in os.listdir(backup_path) if f.endswith('.json')]

    print(f"\n[RESTORE] Found {len(files_to_restore)} files in backup:")
    for filename in files_to_restore:
        size = os.path.getsize(os.path.join(backup_path, filename))
        print(f"  - {filename} ({size / 1024:.1f} KB)")

    if dry_run:
        print("\n[DRY RUN] Would restore these files to memory/")
        return True

    confirm = input("\nType 'yes' to confirm restore: ")
    if confirm.lower() != 'yes':
        print("\n[CANCELLED] Restore cancelled")
        return False

    # Restore files
    print("\n[RESTORE] Restoring files...")
    for filename in files_to_restore:
        src = os.path.join(backup_path, filename)
        dest = os.path.join("memory", filename)
        shutil.copy2(src, dest)
        print(f"  [RESTORED] {filename}")

    print("\n[RESTORE] Complete!")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean or restore Kay's memory")
    parser.add_argument("--clean", action="store_true", help="Clean memory (create fresh start)")
    parser.add_argument("--keep-identity", action="store_true", help="Preserve identity facts when cleaning")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without doing it")
    parser.add_argument("--list-backups", action="store_true", help="List available backups")
    parser.add_argument("--restore", type=str, help="Restore from backup (provide backup path)")
    parser.add_argument("--stats", action="store_true", help="Show current memory statistics")

    args = parser.parse_args()

    if args.stats:
        print("=" * 70)
        print("MEMORY STATISTICS")
        print("=" * 70)
        stats = get_memory_stats()
        print(f"\nTotal memories: {stats.get('total_memories', 0)}")
        print(f"  - Live conversation: {stats.get('live_conversation', 0)}")
        print(f"  - Imported: {stats.get('imported', 0)}")
        print(f"\nEntities: {stats.get('entities', 0)}")
        print(f"\nIdentity facts:")
        print(f"  - Re: {stats.get('identity_re', 0)}")
        print(f"  - Kay: {stats.get('identity_kay', 0)}")

        if stats.get("by_type"):
            print(f"\nBy type:")
            for mem_type, count in stats['by_type'].items():
                print(f"  - {mem_type}: {count}")

    elif args.list_backups:
        print("=" * 70)
        print("AVAILABLE BACKUPS")
        print("=" * 70)
        backups = list_backups()

        if not backups:
            print("\nNo backups found")
        else:
            print(f"\nFound {len(backups)} backup(s):\n")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup['name']}")
                print(f"   Path: {backup['path']}")
                print(f"   Files: {backup['file_count']}")
                print()

    elif args.restore:
        restore_backup(args.restore, dry_run=args.dry_run)

    elif args.clean:
        cleanup_memory(keep_identity=args.keep_identity, dry_run=args.dry_run)

    else:
        parser.print_help()
        print("\nExamples:")
        print("  # Show current stats")
        print("  python cleanup_memory.py --stats")
        print()
        print("  # Clean memory (fresh start)")
        print("  python cleanup_memory.py --clean")
        print()
        print("  # Clean but keep identity facts")
        print("  python cleanup_memory.py --clean --keep-identity")
        print()
        print("  # Preview cleanup without actually doing it")
        print("  python cleanup_memory.py --clean --dry-run")
        print()
        print("  # List backups")
        print("  python cleanup_memory.py --list-backups")
        print()
        print("  # Restore from backup")
        print("  python cleanup_memory.py --restore memory/backups/backup_20241027_150000")
