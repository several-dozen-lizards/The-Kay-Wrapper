# migrate_memories.py
"""
Migration utility for upgrading existing memories to new entity-resolution and multi-layer system.

This script:
1. Loads existing memories from memory/memories.json
2. Adds missing fields (entities, attributes, importance_score, etc.)
3. Migrates memories into multi-layer system
4. Creates entity graph from existing facts
5. Backs up original memories before migration

Usage:
    python scripts/migrate_memories.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os
import shutil
from datetime import datetime
from engines.memory_engine import MemoryEngine
from agent_state import AgentState


def backup_memories(memories_path: str):
    """Create a backup of existing memories before migration."""
    if not os.path.exists(memories_path):
        print(f"[MIGRATION] No existing memories found at {memories_path}")
        return None

    backup_path = memories_path.replace(".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy(memories_path, backup_path)
    print(f"[MIGRATION] ✓ Backed up memories to: {backup_path}")
    return backup_path


def migrate_memory_record(memory: dict, turn_index: int) -> dict:
    """
    Migrate a single memory record to new format.

    Adds:
    - entities: []
    - attributes: []
    - relationships: []
    - importance_score: 0.0
    - access_count: 0
    - current_layer: "episodic" (default for old memories)
    """
    # If memory already has new fields, skip
    if "entities" in memory and "importance_score" in memory:
        return memory

    # Add missing fields
    migrated = {**memory}  # Copy existing fields

    # Add entity fields if missing
    if "entities" not in migrated:
        migrated["entities"] = []
    if "attributes" not in migrated:
        migrated["attributes"] = []
    if "relationships" not in migrated:
        migrated["relationships"] = []

    # Add layer fields if missing
    if "importance_score" not in migrated:
        # Estimate importance from emotion_tags count
        emotion_count = len(memory.get("emotion_tags", []))
        migrated["importance_score"] = min(emotion_count * 0.2, 1.0)

    if "access_count" not in migrated:
        migrated["access_count"] = 0

    if "current_layer" not in migrated:
        # Old memories go to episodic by default
        migrated["current_layer"] = "episodic"

    if "added_timestamp" not in migrated:
        # Estimate timestamp based on position (older memories = earlier timestamp)
        # Assume 1 day per 50 memories for estimation
        days_ago = turn_index / 50
        estimated_time = datetime.now() - datetime.timedelta(days=days_ago)
        migrated["added_timestamp"] = estimated_time.isoformat()

    if "last_accessed" not in migrated:
        migrated["last_accessed"] = migrated.get("added_timestamp", datetime.now().isoformat())

    return migrated


def run_migration():
    """Main migration function."""
    print("=" * 60)
    print("AlphaKayZero Memory Migration Utility")
    print("=" * 60)
    print()

    memories_path = "memory/memories.json"

    # 1. Backup existing memories
    backup_path = backup_memories(memories_path)
    if not backup_path:
        print("[MIGRATION] No memories to migrate.")
        return

    # 2. Load existing memories
    try:
        with open(memories_path, "r", encoding="utf-8") as f:
            old_memories = json.load(f)
        print(f"[MIGRATION] Loaded {len(old_memories)} existing memories")
    except Exception as e:
        print(f"[MIGRATION] ❌ Error loading memories: {e}")
        return

    # 3. Migrate each memory
    migrated_memories = []
    for idx, memory in enumerate(old_memories):
        migrated = migrate_memory_record(memory, idx)
        migrated_memories.append(migrated)

    print(f"[MIGRATION] ✓ Migrated {len(migrated_memories)} memory records")

    # 4. Save migrated memories back to flat file
    try:
        with open(memories_path, "w", encoding="utf-8") as f:
            json.dump(migrated_memories, f, indent=2)
        print(f"[MIGRATION] ✓ Saved migrated memories to {memories_path}")
    except Exception as e:
        print(f"[MIGRATION] ❌ Error saving migrated memories: {e}")
        return

    # 5. Initialize memory engine with new systems
    print("[MIGRATION] Initializing MemoryEngine with entity graph and memory layers...")
    state = AgentState()
    memory_engine = MemoryEngine(state.memory, file_path=memories_path)

    # 6. Reload migrated memories into memory engine
    memory_engine.memories = migrated_memories

    # 7. Populate entity graph from migrated memories
    print("[MIGRATION] Populating entity graph from existing facts...")
    entity_count_before = len(memory_engine.entity_graph.entities)

    for turn_idx, mem in enumerate(memory_engine.memories):
        # If memory has entities already, process them
        if mem.get("entities") or mem.get("attributes"):
            memory_engine.current_turn = turn_idx
            memory_engine._process_entities(mem)

    entity_count_after = len(memory_engine.entity_graph.entities)
    print(f"[MIGRATION] ✓ Created {entity_count_after - entity_count_before} new entities")

    # 8. Migrate memories into layered system
    print("[MIGRATION] Migrating memories into multi-layer system...")
    for turn_idx, mem in enumerate(memory_engine.memories):
        memory_engine.memory_layers.migrate_memory_to_layers(mem, current_turn=turn_idx)

    # Get layer stats
    layer_stats = memory_engine.memory_layers.get_layer_stats()
    print(f"[MIGRATION] ✓ Layer distribution:")
    print(f"  - Working memory: {layer_stats['working']['count']} memories")
    print(f"  - Episodic memory: {layer_stats['episodic']['count']} memories")
    print(f"  - Semantic memory: {layer_stats['semantic']['count']} memories")

    # 9. Check for contradictions
    contradictions = memory_engine.entity_graph.get_all_contradictions(suppress_logging=True)
    if contradictions:
        print(f"[MIGRATION] ⚠️ Detected {len(contradictions)} entity contradictions:")
        for contradiction in contradictions[:5]:  # Show first 5
            entity_name = contradiction['entity']
            attr_name = contradiction['attribute']
            values = contradiction['values']
            print(f"  - {entity_name}.{attr_name}: {list(values.keys())}")
    else:
        print("[MIGRATION] ✓ No entity contradictions detected")

    # 10. Summary
    print()
    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"Migrated: {len(migrated_memories)} memories")
    print(f"Entities created: {len(memory_engine.entity_graph.entities)}")
    print(f"Relationships created: {len(memory_engine.entity_graph.relationships)}")
    print(f"Backup saved to: {backup_path}")
    print()
    print("New files created:")
    print("  - memory/entity_graph.json (entity resolution data)")
    print("  - memory/memory_layers.json (multi-layer memory system)")
    print()
    print("✓ AlphaKayZero is now using enhanced memory architecture!")


if __name__ == "__main__":
    try:
        run_migration()
    except KeyboardInterrupt:
        print("\n[MIGRATION] Cancelled by user")
    except Exception as e:
        print(f"\n[MIGRATION] ❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
