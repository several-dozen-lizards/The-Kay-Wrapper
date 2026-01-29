"""
Quick verification that identity layer fix is working.
"""

import json
from engines.identity_memory import IdentityMemory
from engines.memory_engine import MemoryEngine

print("=" * 70)
print("IDENTITY LAYER FIX VERIFICATION")
print("=" * 70)

# Load identity memory
identity = IdentityMemory()

# Get identity facts
all_identity = identity.get_all_identity_facts()

print(f"\n1. Identity memory loaded:")
print(f"   - Kay facts: {len(identity.kay_identity)}")
print(f"   - Re facts: {len(identity.re_identity)}")
print(f"   - Entity types: {len(identity.entities)}")

print(f"\n2. get_all_identity_facts() returns:")
print(f"   - Total: {len(all_identity)} facts (should be ~4, Kay's core identity only)")

if len(all_identity) > 50:
    print(f"\n   [ERROR] PROBLEM: Still loading {len(all_identity)} identity facts!")
    print(f"   Expected: ~4 Kay identity facts")
elif len(all_identity) == 0:
    print(f"\n   [WARNING] No identity facts found! Kay should have core identity.")
else:
    print(f"\n   [SUCCESS] Only loading Kay's core identity")

print(f"\n3. Kay's core identity facts:")
for fact in all_identity:
    print(f"   - {fact.get('fact', '')[:70]}")

# Create memory engine and verify retrieval
print(f"\n4. Testing memory retrieval...")
memory = MemoryEngine()

print(f"\n5. Memory engine loaded:")
print(f"   - Total memories in store: {len(memory.memories)}")
print(f"   - Identity system: {memory.identity.get_summary()}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print(f"\nExpected behavior:")
print(f"  [OK] get_all_identity_facts() returns 4 Kay facts")
print(f"  [OK] Re facts, entity facts -> working memory (retrieved by relevance)")
print(f"  [OK] No pigeon facts, Saga facts, etc. in permanent identity")
