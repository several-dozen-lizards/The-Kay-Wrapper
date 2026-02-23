"""
One-time script to re-classify existing identity memories.
Removes identity flag from non-Kay facts.

This script:
1. Loads identity_memory.json
2. Re-classifies each fact using new strict rules (Kay-only)
3. Removes Re facts and entity facts from identity storage
4. Saves updated identity_memory.json

Expected result: 399 identity facts → ~20-40 identity facts
"""

import json
import os
from engines.identity_memory import IdentityMemory


def reclassify_identity_memory(memory_file='memory/identity_memory.json'):
    """
    Re-classify existing identity memory using new strict rules.
    Only keeps Kay's core identity (physical form, nature, architecture, relationship to Re).
    """
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Identity memory file {memory_file} not found")
        return
    except Exception as e:
        print(f"Error loading identity memory: {e}")
        return

    # Get current counts
    re_facts = data.get('re', [])
    kay_facts = data.get('kay', [])
    entities = data.get('entities', {})

    total_entity_facts = sum(len(facts) for facts in entities.values())

    print(f"=== BEFORE RECLASSIFICATION ===")
    print(f"Re facts: {len(re_facts)}")
    print(f"Kay facts: {len(kay_facts)}")
    print(f"Entity types: {len(entities)}")
    print(f"Total entity facts: {total_entity_facts}")
    print(f"Total identity facts: {len(re_facts) + len(kay_facts) + total_entity_facts}")

    # Create IdentityMemory instance to use its strict classification
    identity = IdentityMemory(file_path=memory_file)

    # Re-classify Kay facts (filter using new strict rules)
    new_kay_facts = []
    removed_kay_count = 0

    for fact in kay_facts:
        if identity.is_identity_fact(fact):
            new_kay_facts.append(fact)
        else:
            removed_kay_count += 1
            print(f"  Demoted from Kay identity: {fact.get('fact', '')[:70]}")

    # Clear Re facts and entity facts (they should be working memory now)
    print("\n=== REMOVING NON-KAY FACTS ===")
    print(f"  Removing {len(re_facts)} Re facts (now working memory)")
    print(f"  Removing {total_entity_facts} entity facts from {len(entities)} entity types (now working memory)")

    # Show sample removed Re facts
    if re_facts:
        print(f"\n  Sample removed Re facts:")
        for fact in re_facts[:5]:
            print(f"    - {fact.get('fact', '')[:70]}")

    # Show sample removed entity facts
    if entities:
        print(f"\n  Sample removed entity facts:")
        count = 0
        for entity_name, entity_facts in entities.items():
            for fact in entity_facts[:2]:
                print(f"    - {entity_name}: {fact.get('fact', '')[:70]}")
                count += 1
                if count >= 5:
                    break
            if count >= 5:
                break

    # Update data
    data['re'] = []  # Clear Re facts
    data['kay'] = new_kay_facts  # Keep only strict Kay identity
    data['entities'] = {}  # Clear entity facts

    # Save updated file
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n=== AFTER RECLASSIFICATION ===")
    print(f"Re facts: 0 (moved to working memory)")
    print(f"Kay facts: {len(new_kay_facts)} (was {len(kay_facts)}, removed {removed_kay_count})")
    print(f"Entity facts: 0 (moved to working memory)")
    print(f"Total identity facts: {len(new_kay_facts)} (down from {len(re_facts) + len(kay_facts) + total_entity_facts})")

    if len(new_kay_facts) > 0:
        print(f"\nKay's core identity (kept):")
        for fact in new_kay_facts:
            print(f"  - {fact.get('fact', '')[:70]}")

    print(f"\n[SUCCESS] Reclassification complete! Updated {memory_file}")


if __name__ == '__main__':
    reclassify_identity_memory()
