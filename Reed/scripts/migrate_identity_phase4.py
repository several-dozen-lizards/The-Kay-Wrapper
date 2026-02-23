"""
Phase 4 Migration Script

Migrates identity facts to their appropriate homes:
1. Core identity (25 facts) → Static system prompt (delete from DB)
2. Semantic knowledge (42 facts) → semantic_knowledge.json
3. Episodic events (6 facts) → Keep in identity_memory.json (or migrate to memory_layers.json)
4. Contradictions (9 facts) → Delete
5. Relationship context (8 facts) → Keep in identity_memory.json
"""

import json
import os
import shutil
from datetime import datetime
from core_identity_constants import (
    CORE_IDENTITY,
    SEMANTIC_KNOWLEDGE_MIGRATION,
    EPISODIC_MEMORY_MIGRATION,
    DELETE_FACTS,
    RELATIONSHIP_FACTS_KEEP_IN_MEMORY,
    get_core_identity_as_list
)

# Add parent directory to path to import engines
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.semantic_knowledge import get_semantic_knowledge


def create_backup():
    """Create timestamped backup of identity_memory.json"""
    source = "memory/identity_memory.json"
    if not os.path.exists(source):
        print(f"[WARN] {source} not found, cannot create backup")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"memory/backups/identity_memory_pre_phase4_{timestamp}.json"

    os.makedirs("memory/backups", exist_ok=True)
    shutil.copy(source, backup_path)

    print(f"[BACKUP] Created: {backup_path}")
    return backup_path


def load_identity_memory():
    """Load identity memory from disk"""
    path = "memory/identity_memory.json"
    if not os.path.exists(path):
        print(f"[ERROR] {path} not found")
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_identity_memory(data):
    """Save identity memory to disk"""
    path = "memory/identity_memory.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[SAVED] {path}")


def normalize_text(text):
    """Normalize text for comparison (lowercase, strip)"""
    return text.lower().strip()


def fact_matches(fact_text, target_list):
    """Check if fact text matches any in target list"""
    normalized_fact = normalize_text(fact_text)
    for target in target_list:
        if normalized_fact == normalize_text(target):
            return True
    return False


def migrate_to_semantic_knowledge(facts_to_migrate):
    """
    Migrate facts to semantic_knowledge.json

    Args:
        facts_to_migrate: List of fact dicts with 'fact', 'entities', 'topic'
    """
    sk = get_semantic_knowledge()

    migrated_count = 0
    for fact_data in facts_to_migrate:
        text = fact_data.get("fact", "")  # Fixed: identity_memory uses "fact" not "text"
        entities = fact_data.get("entities", [])
        topic = fact_data.get("topic", "general")

        # Map topic to semantic category
        category_map = {
            "pets": "animals",
            "appearance": "animals",
            "system": "concepts",
            "family": "people",
            "identity": "people",
            "relationships": "relationships"
        }
        category = category_map.get(topic, "general")

        # Add to semantic knowledge
        sk.add_fact(
            text=text,
            entities=entities,
            source="phase4_migration",
            category=category,
            metadata={"migrated_from": "identity_memory"}
        )

        migrated_count += 1

    # Save semantic knowledge
    sk.save()

    print(f"[MIGRATED] {migrated_count} facts to semantic_knowledge.json")
    return migrated_count


def migrate_identity():
    """Main migration function"""
    print("=" * 80)
    print("PHASE 4 MIGRATION: Separate Core Identity")
    print("=" * 80)

    # Step 1: Create backup
    print("\n[STEP 1] Creating backup...")
    backup_path = create_backup()
    if not backup_path:
        print("[ERROR] Cannot proceed without backup")
        return False

    # Step 2: Load identity memory
    print("\n[STEP 2] Loading identity memory...")
    identity_data = load_identity_memory()
    if not identity_data:
        print("[ERROR] No identity data to migrate")
        return False

    print(f"[LOADED] {sum(len(v) for v in identity_data.values() if isinstance(v, list))} total facts")

    # Step 3: Categorize facts
    print("\n[STEP 3] Categorizing facts...")

    core_identity_list = get_core_identity_as_list()

    to_delete = []  # Core identity + contradictions
    to_semantic = []  # Semantic knowledge migration
    to_keep = []  # Episodic + relationship context

    stats = {
        "core_identity_removed": 0,
        "semantic_migrated": 0,
        "contradictions_deleted": 0,
        "kept_in_memory": 0
    }

    # Process each entity key
    for entity_key, facts in identity_data.items():
        if not isinstance(facts, list):
            continue

        print(f"\n[PROCESSING] {entity_key.upper()}: {len(facts)} facts")

        for fact in facts:
            fact_text = fact.get("fact", "")

            # Check if it's core identity (should be removed from DB)
            if fact_matches(fact_text, core_identity_list):
                to_delete.append((entity_key, fact))
                stats["core_identity_removed"] += 1
                continue

            # Check if it's a contradiction (should be deleted)
            if fact_matches(fact_text, DELETE_FACTS):
                to_delete.append((entity_key, fact))
                stats["contradictions_deleted"] += 1
                continue

            # Check if it should migrate to semantic knowledge
            if fact_matches(fact_text, SEMANTIC_KNOWLEDGE_MIGRATION):
                to_semantic.append(fact)
                to_delete.append((entity_key, fact))
                stats["semantic_migrated"] += 1
                continue

            # Check if it's episodic or relationship context (keep)
            if (fact_matches(fact_text, EPISODIC_MEMORY_MIGRATION) or
                fact_matches(fact_text, RELATIONSHIP_FACTS_KEEP_IN_MEMORY)):
                to_keep.append((entity_key, fact))
                stats["kept_in_memory"] += 1
                continue

            # Default: keep in memory (unknown classification)
            to_keep.append((entity_key, fact))
            stats["kept_in_memory"] += 1
            print(f"  [KEEP] (unclassified): {fact_text[:60]}...")

    # Step 4: Migrate to semantic knowledge
    if to_semantic:
        print("\n[STEP 4] Migrating to semantic knowledge...")
        migrate_to_semantic_knowledge(to_semantic)
    else:
        print("\n[STEP 4] No facts to migrate to semantic knowledge")

    # Step 5: Remove facts from identity memory
    print("\n[STEP 5] Removing facts from identity memory...")

    # Rebuild identity_data with only kept facts
    new_identity_data = {}
    for entity_key, facts in identity_data.items():
        if not isinstance(facts, list):
            new_identity_data[entity_key] = facts
            continue

        # Keep only facts that weren't deleted
        kept_facts = [
            fact for fact in facts
            if not any(
                fact.get("fact") == deleted_fact.get("fact")
                for ek, deleted_fact in to_delete
                if ek == entity_key
            )
        ]

        new_identity_data[entity_key] = kept_facts

    # Step 6: Save updated identity memory
    print("\n[STEP 6] Saving updated identity memory...")
    save_identity_memory(new_identity_data)

    # Summary
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)

    print(f"\nCore identity facts removed: {stats['core_identity_removed']}")
    print(f"  -> These are now in static system prompt")

    print(f"\nSemantic knowledge facts migrated: {stats['semantic_migrated']}")
    print(f"  -> Moved to memory/semantic_knowledge.json")

    print(f"\nContradictions deleted: {stats['contradictions_deleted']}")
    print(f"  -> Removed from database")

    print(f"\nFacts kept in identity memory: {stats['kept_in_memory']}")
    print(f"  -> Episodic events and relationship context")

    original_total = sum(len(v) for v in identity_data.values() if isinstance(v, list))
    new_total = sum(len(v) for v in new_identity_data.values() if isinstance(v, list))

    print(f"\n{'=' * 80}")
    print(f"Identity memory: {original_total} facts -> {new_total} facts")
    print(f"Reduction: {original_total - new_total} facts ({((original_total - new_total) / original_total * 100):.1f}%)")
    print(f"{'=' * 80}")

    print(f"\nBackup saved to: {backup_path}")
    print(f"\nNext step: Add CORE_IDENTITY to system prompt")

    return True


if __name__ == "__main__":
    success = migrate_identity()
    if success:
        print("\n[SUCCESS] Phase 4 migration complete")
        print("\nTo complete Phase 4:")
        print("1. Add CORE_IDENTITY to system prompt in integrations/llm_integration.py")
        print("2. Test that Kay can answer 'Who are you?' without memory retrieval")
        print("3. Verify no regressions in existing functionality")
    else:
        print("\n[FAILED] Migration did not complete successfully")
