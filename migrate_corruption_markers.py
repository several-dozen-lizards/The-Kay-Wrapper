"""
Migration Script: Add Corruption Markers to Existing Memories

Adds corruption detection fields to all existing memories in:
- memory/memories.json
- memory/memory_layers.json

Backwards compatible - preserves all existing data.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import shutil


def backup_file(filepath: str) -> str:
    """Create timestamped backup of file."""
    if not os.path.exists(filepath):
        print(f"[BACKUP] File not found: {filepath}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.replace('.json', f'_backup_{timestamp}.json')

    shutil.copy2(filepath, backup_path)
    print(f"[BACKUP] Created: {backup_path}")

    return backup_path


def add_corruption_markers(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Add corruption marker fields to a single memory."""
    # Only add if not already present
    if 'corrupted' not in memory:
        memory['corrupted'] = False
    if 'corruption_reason' not in memory:
        memory['corruption_reason'] = None
    if 'corruption_detected_turn' not in memory:
        memory['corruption_detected_turn'] = None
    if 'superseded_by' not in memory:
        memory['superseded_by'] = None
    if 'supersedes' not in memory:
        memory['supersedes'] = None
    if 'correction_applied' not in memory:
        memory['correction_applied'] = False
    if 'correction_turn' not in memory:
        memory['correction_turn'] = None

    # Ensure memory has an ID
    if 'memory_id' not in memory:
        memory['memory_id'] = None  # Will be assigned later

    return memory


def migrate_memories_file(filepath: str) -> Dict[str, int]:
    """
    Migrate flat memories.json file.

    Returns:
        Dict with migration stats
    """
    print(f"\n[MIGRATE] Processing: {filepath}")

    if not os.path.exists(filepath):
        print(f"[MIGRATE] File not found, skipping: {filepath}")
        return {'total': 0, 'updated': 0, 'skipped': 0}

    # Load memories
    with open(filepath, 'r', encoding='utf-8') as f:
        memories = json.load(f)

    print(f"[MIGRATE] Loaded {len(memories)} memories")

    updated = 0
    skipped = 0

    # Add corruption markers to each memory
    for i, memory in enumerate(memories):
        # Check if already has markers
        if 'corrupted' in memory:
            skipped += 1
        else:
            add_corruption_markers(memory)
            updated += 1

        # Assign memory ID if missing
        if not memory.get('memory_id'):
            memory['memory_id'] = f"mem_{i}"

    # Save updated memories
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)

    print(f"[MIGRATE] Updated: {updated}, Skipped: {skipped}")

    return {
        'total': len(memories),
        'updated': updated,
        'skipped': skipped
    }


def migrate_memory_layers_file(filepath: str) -> Dict[str, int]:
    """
    Migrate memory_layers.json file.

    Returns:
        Dict with migration stats
    """
    print(f"\n[MIGRATE] Processing: {filepath}")

    if not os.path.exists(filepath):
        print(f"[MIGRATE] File not found, skipping: {filepath}")
        return {'total': 0, 'updated': 0, 'skipped': 0}

    # Load memory layers
    with open(filepath, 'r', encoding='utf-8') as f:
        layers_data = json.load(f)

    total = 0
    updated = 0
    skipped = 0
    memory_index = 0

    # Process each layer
    for layer_name in ['working_memory', 'episodic_memory', 'semantic_memory']:
        if layer_name not in layers_data:
            continue

        memories = layers_data[layer_name]
        print(f"[MIGRATE]   Layer '{layer_name}': {len(memories)} memories")

        for memory in memories:
            total += 1

            # Check if already has markers
            if 'corrupted' in memory:
                skipped += 1
            else:
                add_corruption_markers(memory)
                updated += 1

            # Assign memory ID if missing
            if not memory.get('memory_id'):
                memory['memory_id'] = f"mem_{memory_index}"
                memory_index += 1

    # Save updated layers
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(layers_data, f, indent=2, ensure_ascii=False)

    print(f"[MIGRATE] Updated: {updated}, Skipped: {skipped}")

    return {
        'total': total,
        'updated': updated,
        'skipped': skipped
    }


def main():
    """Run migration on all memory files."""
    print("="*70)
    print("CORRUPTION MARKERS MIGRATION")
    print("="*70)

    memory_dir = "memory"

    # Check if memory directory exists
    if not os.path.exists(memory_dir):
        print(f"\n[ERROR] Memory directory not found: {memory_dir}")
        print("Creating directory...")
        os.makedirs(memory_dir)

    # Files to migrate
    files_to_migrate = [
        "memory/memories.json",
        "memory/memory_layers.json"
    ]

    # Backup all files first
    print("\n" + "="*70)
    print("STEP 1: BACKUP")
    print("="*70)

    backups = {}
    for filepath in files_to_migrate:
        backup = backup_file(filepath)
        if backup:
            backups[filepath] = backup

    # Migrate each file
    print("\n" + "="*70)
    print("STEP 2: MIGRATION")
    print("="*70)

    all_stats = {
        'total': 0,
        'updated': 0,
        'skipped': 0
    }

    # Migrate flat memories
    if os.path.exists("memory/memories.json"):
        stats = migrate_memories_file("memory/memories.json")
        all_stats['total'] += stats['total']
        all_stats['updated'] += stats['updated']
        all_stats['skipped'] += stats['skipped']

    # Migrate layered memories
    if os.path.exists("memory/memory_layers.json"):
        stats = migrate_memory_layers_file("memory/memory_layers.json")
        all_stats['total'] += stats['total']
        all_stats['updated'] += stats['updated']
        all_stats['skipped'] += stats['skipped']

    # Summary
    print("\n" + "="*70)
    print("MIGRATION COMPLETE")
    print("="*70)
    print(f"Total memories: {all_stats['total']}")
    print(f"Updated with corruption markers: {all_stats['updated']}")
    print(f"Already had markers (skipped): {all_stats['skipped']}")

    if backups:
        print(f"\nBackups created:")
        for original, backup in backups.items():
            print(f"  {original} -> {backup}")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Run AlphaKayZero: python main.py")
    print("2. Scan for corruption: /scan")
    print("3. View stats: /corruption_stats")
    print("4. Flag known bad data: /corrupt <pattern>")
    print("5. Correct specific memories: /correct <id> | <corrected_fact>")
    print("="*70)


if __name__ == "__main__":
    main()
