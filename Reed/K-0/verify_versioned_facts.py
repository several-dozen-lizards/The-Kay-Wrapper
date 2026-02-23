"""
Verify temporal fact versioning is working correctly.
"""

import json
from engines.memory_engine import find_existing_fact, should_update_fact, amend_fact, confirm_fact

print("=" * 70)
print("TEMPORAL FACT VERSIONING VERIFICATION")
print("=" * 70)

# Test data
test_memories = []

# Test 1: Create new fact
print("\n[TEST 1] Creating new fact")
new_fact = {
    'entity': 'Saga',
    'attribute': 'color',
    'current_value': 'orange',
    'type': 'extracted_fact'
}

existing = find_existing_fact(new_fact, test_memories)
update_type = should_update_fact(existing, 'orange')

print(f"  Existing fact: {existing}")
print(f"  Update type: {update_type}")
assert update_type == 'new', "Should be 'new' for first fact"
print("  ✓ PASS: New fact recognized")

# Add to memories
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
new_fact.update({
    'created_at': now,
    'last_confirmed': now,
    'version': 1,
    'history': []
})
test_memories.append(new_fact)

# Test 2: Confirm unchanged fact
print("\n[TEST 2] Confirming unchanged fact")
same_fact = {
    'entity': 'Saga',
    'attribute': 'color',
    'current_value': 'orange',
    'type': 'extracted_fact'
}

existing = find_existing_fact(same_fact, test_memories)
update_type = should_update_fact(existing, 'orange')

print(f"  Existing fact: Found")
print(f"  Update type: {update_type}")
assert update_type == 'skip', "Should be 'skip' for same value"

confirm_fact(existing)
print("  ✓ PASS: Unchanged fact confirmed (not duplicated)")

# Test 3: Amend changed fact
print("\n[TEST 3] Amending changed fact")
changed_fact = {
    'entity': 'Saga',
    'attribute': 'color',
    'current_value': 'brown',
    'type': 'extracted_fact'
}

existing = find_existing_fact(changed_fact, test_memories)
update_type = should_update_fact(existing, 'brown')

print(f"  Existing fact: Found")
print(f"  Update type: {update_type}")
assert update_type == 'amend', "Should be 'amend' for different value"

amend_fact(existing, 'brown', turn_count=10)
print(f"  Current value: {existing.get('current_value')}")
print(f"  Version: {existing.get('version')}")
print(f"  History entries: {len(existing.get('history', []))}")

assert existing.get('current_value') == 'brown', "Current value should be 'brown'"
assert existing.get('version') == 2, "Version should be 2"
assert len(existing.get('history', [])) == 1, "Should have 1 history entry"
assert existing['history'][0]['value'] == 'orange', "History should contain old value 'orange'"
print("  ✓ PASS: Fact amended with history")

# Test 4: Check memory count
print("\n[TEST 4] Verifying memory count")
print(f"  Total memories: {len(test_memories)}")
assert len(test_memories) == 1, "Should only have 1 memory (not 3 duplicates)"
print("  ✓ PASS: No duplicates created")

# Test 5: Load real memories and check deduplication
print("\n[TEST 5] Checking real memory file")
try:
    with open('memory/memories.json', 'r', encoding='utf-8') as f:
        real_memories = json.load(f)

    if isinstance(real_memories, dict):
        memories_list = real_memories.get('memories', [])
    else:
        memories_list = real_memories

    print(f"  Total memories: {len(memories_list)}")

    # Count versioned facts
    versioned_count = 0
    non_versioned_count = 0

    for mem in memories_list:
        if mem.get('version') or mem.get('history') is not None:
            versioned_count += 1
        elif mem.get('entity') and mem.get('attribute'):
            non_versioned_count += 1

    print(f"  Versioned facts: {versioned_count}")
    print(f"  Non-versioned entity facts: {non_versioned_count}")

    if versioned_count > 0:
        print("  ✓ Migration has been run - facts are versioned")
    elif non_versioned_count > 100:
        print("  ⚠ Migration NOT run - consider running migrate_to_versioned_facts.py")
    else:
        print("  ✓ Fresh start - versioning will apply to new facts")

except FileNotFoundError:
    print("  No existing memory file - this is okay for first run")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nExpected behavior:")
print("  ✓ New facts create versioned entries")
print("  ✓ Duplicate facts update last_confirmed (not stored again)")
print("  ✓ Changed facts create history entries")
print("  ✓ Memory count stays low (no duplicates)")
