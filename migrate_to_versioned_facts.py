"""
One-time migration script to convert duplicate facts to versioned facts.

This script:
1. Loads all memories from memory/memories.json
2. Groups facts by entity + attribute
3. Converts duplicates to single versioned fact with history
4. Saves deduplicated memory file

Expected result:
- Before: 9686 memories with many duplicates (e.g., "Saga.color = orange" 38 times)
- After: ~3000-5000 unique memories with version history
"""

import json
import shutil
from datetime import datetime, timezone
from collections import defaultdict


def migrate_facts(memory_file='memory/memories.json'):
    """
    Convert duplicate fact storage to versioned system.
    """
    # Backup original file
    backup_file = memory_file + '.pre-versioning-backup'
    try:
        shutil.copy(memory_file, backup_file)
        print(f"[BACKUP] Created backup: {backup_file}")
    except FileNotFoundError:
        print(f"[ERROR] Memory file {memory_file} not found")
        return
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        return

    # Load memories
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            memories = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load memories: {e}")
        return

    if isinstance(memories, dict):
        # Handle dict format (with metadata)
        memories_list = memories.get('memories', [])
    else:
        memories_list = memories

    print(f"[MIGRATION] Loaded {len(memories_list)} memories")

    # Group by entity + attribute
    fact_groups = defaultdict(list)
    non_entity_facts = []

    for mem in memories_list:
        entity = mem.get('entity')
        attribute = mem.get('attribute')

        if entity and attribute and mem.get('type') == 'extracted_fact':
            key = (entity, attribute)
            fact_groups[key].append(mem)
        else:
            # Not an entity fact, keep as-is
            non_entity_facts.append(mem)

    print(f"[MIGRATION] Found {len(fact_groups)} unique entity-attribute pairs")
    print(f"[MIGRATION] Found {len(non_entity_facts)} non-entity memories (kept as-is)")

    # Convert to versioned facts
    versioned_facts = []
    now = datetime.now(timezone.utc).isoformat()

    deduplicated_count = 0
    versioned_count = 0

    for (entity, attribute), facts in fact_groups.items():
        # Sort by turn number or timestamp to get chronological order
        facts_sorted = sorted(facts, key=lambda f: f.get('parent_turn', 0))

        # Get all values to check if fact changed over time
        values = []
        for f in facts_sorted:
            val = f.get('current_value')
            if val:
                values.append(val)

        if not values:
            # No values extracted, keep all as-is
            versioned_facts.extend(facts_sorted)
            continue

        # Check if all values are the same
        unique_values = list(set(values))

        if len(unique_values) == 1:
            # All same value - deduplicate to single fact
            base_fact = facts_sorted[0].copy()
            base_fact['created_at'] = base_fact.get('created_at', now)
            base_fact['last_confirmed'] = now
            base_fact['version'] = 1
            base_fact['history'] = []

            versioned_facts.append(base_fact)
            deduplicated_count += len(facts_sorted) - 1

            if len(facts_sorted) > 1:
                print(f"  [DEDUP] {entity}.{attribute}: {len(facts_sorted)} → 1 (constant value: {unique_values[0][:40]}...)")

        else:
            # Values changed over time - create versioned fact with history
            base_fact = facts_sorted[-1].copy()  # Use most recent as base
            base_fact['created_at'] = facts_sorted[0].get('created_at', now)
            base_fact['last_confirmed'] = now
            base_fact['version'] = len(unique_values)
            base_fact['history'] = []

            # Build history from changes
            prev_value = None
            for i, fact in enumerate(facts_sorted):
                curr_value = fact.get('current_value')
                if curr_value and curr_value != prev_value:
                    if prev_value is not None:
                        # This is a change, add previous value to history
                        history_entry = {
                            'value': prev_value,
                            'valid_from': facts_sorted[max(0, i-1)].get('created_at', now),
                            'valid_until': fact.get('created_at', now),
                            'turn': facts_sorted[max(0, i-1)].get('parent_turn', 0)
                        }
                        base_fact['history'].append(history_entry)
                    prev_value = curr_value

            versioned_facts.append(base_fact)
            versioned_count += 1
            deduplicated_count += len(facts_sorted) - 1

            print(f"  [VERSION] {entity}.{attribute}: {len(facts_sorted)} → 1 with {len(base_fact['history'])} history entries")
            print(f"            Values changed: {' → '.join([str(v)[:20] for v in unique_values])}")

    # Combine versioned facts + non-entity facts
    all_memories = versioned_facts + non_entity_facts

    print(f"\n[MIGRATION COMPLETE]")
    print(f"  Before: {len(memories_list)} memories")
    print(f"  After: {len(all_memories)} memories")
    print(f"  Deduplicated: {deduplicated_count} duplicate facts")
    print(f"  Versioned: {versioned_count} facts with history")
    print(f"  Reduction: {((len(memories_list) - len(all_memories)) / len(memories_list) * 100):.1f}%")

    # Save migrated memories
    if isinstance(memories, dict):
        memories['memories'] = all_memories
        output = memories
    else:
        output = all_memories

    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Migrated memory saved to {memory_file}")
    print(f"[BACKUP] Original backed up to {backup_file}")


if __name__ == '__main__':
    print("=" * 70)
    print("TEMPORAL FACT VERSIONING MIGRATION")
    print("=" * 70)
    print()

    migrate_facts()

    print()
    print("=" * 70)
    print("Run Kay now to see versioned fact system in action!")
    print("=" * 70)
