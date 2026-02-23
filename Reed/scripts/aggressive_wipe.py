"""
Aggressive Memory Wipe for Reed
Deletes ALL memory files and prevents re-population
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def aggressive_wipe():
    """
    Nuclear option: Delete ALL memory data and indexes.
    Creates fresh empty files that prevent auto-population.
    """
    print("=" * 70)
    print("AGGRESSIVE MEMORY WIPE")
    print("=" * 70)

    # Create backup first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"memory/backups/backup_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)

    print(f"\n[BACKUP] Creating backup at {backup_dir}...")
    backed_up = []

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

    for filepath in memory_files:
        if os.path.exists(filepath):
            filename = os.path.basename(filepath)
            shutil.copy2(filepath, os.path.join(backup_dir, filename))
            size_kb = os.path.getsize(filepath) / 1024
            backed_up.append((filename, size_kb))
            print(f"  [BACKUP] {filename} ({size_kb:.1f} KB)")

    print(f"[BACKUP] Complete! {len(backed_up)} files backed up")

    # DELETE everything
    print("\n[DELETE] Removing all memory files...")
    for filepath in memory_files:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  [DELETED] {os.path.basename(filepath)}")

    # Create fresh EMPTY files with proper structure
    print("\n[CREATE] Creating fresh empty memory files...")

    # memories.json - empty array
    with open("memory/memories.json", "w") as f:
        json.dump([], f, indent=2)
    print("  [CREATED] memories.json (empty array)")

    # entity_graph.json - empty entities and relationships
    with open("memory/entity_graph.json", "w") as f:
        json.dump({"entities": {}, "relationships": []}, f, indent=2)
    print("  [CREATED] entity_graph.json (empty)")

    # memory_layers.json - empty layers
    with open("memory/memory_layers.json", "w") as f:
        json.dump({
            "working": [],
            "episodic": [],
            "semantic": []
        }, f, indent=2)
    print("  [CREATED] memory_layers.json (empty)")

    # identity_memory.json - empty identity
    with open("memory/identity_memory.json", "w") as f:
        json.dump({
            "re": [],
            "kay": [],
            "entities": {}
        }, f, indent=2)
    print("  [CREATED] identity_memory.json (empty)")

    # preferences.json - empty preferences
    with open("memory/preferences.json", "w") as f:
        json.dump({
            "domains": {},
            "contradictions": []
        }, f, indent=2)
    print("  [CREATED] preferences.json (empty)")

    # motifs.json - empty motifs
    with open("memory/motifs.json", "w") as f:
        json.dump({
            "entities": {},
            "last_updated": datetime.now().isoformat()
        }, f, indent=2)
    print("  [CREATED] motifs.json (empty)")

    # memory_index.json - empty index
    with open("memory/memory_index.json", "w") as f:
        json.dump({
            "version": "1.0",
            "indices": [],
            "metadata": {
                "total_memories": 0,
                "last_updated": datetime.now().isoformat()
            }
        }, f, indent=2)
    print("  [CREATED] memory_index.json (empty)")

    # identity_index.json - empty identity index
    with open("memory/identity_index.json", "w") as f:
        json.dump({
            "version": "1.0",
            "re_facts": [],
            "kay_facts": [],
            "entity_facts": []
        }, f, indent=2)
    print("  [CREATED] identity_index.json (empty)")

    # VERIFY everything is empty
    print("\n[VERIFY] Verifying wipe succeeded...")

    verification_passed = True

    with open("memory/memories.json", "r") as f:
        memories = json.load(f)
        if len(memories) != 0:
            print(f"  [FAIL] memories.json has {len(memories)} items!")
            verification_passed = False
        else:
            print(f"  [OK] memories.json is empty")

    with open("memory/memory_layers.json", "r") as f:
        layers = json.load(f)
        total = len(layers.get("working", [])) + len(layers.get("episodic", [])) + len(layers.get("semantic", []))
        if total != 0:
            print(f"  [FAIL] memory_layers.json has {total} items!")
            verification_passed = False
        else:
            print(f"  [OK] memory_layers.json is empty")

    with open("memory/entity_graph.json", "r") as f:
        entities = json.load(f)
        count = len(entities.get("entities", {}))
        if count != 0:
            print(f"  [FAIL] entity_graph.json has {count} entities!")
            verification_passed = False
        else:
            print(f"  [OK] entity_graph.json is empty")

    if verification_passed:
        print("\n[SUCCESS] Aggressive wipe complete!")
        print("  - All memory files deleted and recreated")
        print("  - All indexes cleared")
        print("  - Verification passed")
        print(f"  - Backup saved to: {backup_dir}")
        print("\nKay has ZERO memories, ZERO entities, ZERO history")
        print("DO NOT run Kay or MemoryEngine until you're ready to test!")
    else:
        print("\n[ERROR] Wipe verification FAILED - files still contain data!")
        print("Manual intervention required")

    return backup_dir


if __name__ == "__main__":
    aggressive_wipe()
