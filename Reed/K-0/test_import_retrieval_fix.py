"""
Test Import Retrieval Fix
Verifies that imported facts are retrievable after import
"""

import sys
sys.path.insert(0, '.')

from engines.memory_engine import MemoryEngine
from agent_state import AgentState
import json

print("=" * 70)
print("TESTING IMPORT RETRIEVAL FIX")
print("=" * 70)

# Initialize
memory = MemoryEngine()
state = AgentState()
state.memory = memory
state.emotional_cocktail = {}

# Add some test imported facts manually
print("\n[SETUP] Adding test imported facts...")

test_facts = [
    {
        "fact": "Re experienced PTSD from a traumatic incident at Kroger",
        "user_input": "Re experienced PTSD from a traumatic incident at Kroger",
        "type": "extracted_fact",
        "perspective": "user",
        "tier": "semantic",
        "current_layer": "semantic",
        "importance": 0.9,
        "importance_score": 0.9,
        "turn_index": 0,
        "entities": ["Re", "Kroger"],
        "emotion_tags": [],
        "is_imported": True
    },
    {
        "fact": "Security guards at Kroger confronted Re about an angry letter",
        "user_input": "Security guards at Kroger confronted Re about an angry letter",
        "type": "extracted_fact",
        "perspective": "user",
        "tier": "semantic",
        "current_layer": "semantic",
        "importance": 0.8,
        "importance_score": 0.8,
        "turn_index": 0,
        "entities": ["Re", "Kroger", "security guards"],
        "emotion_tags": [],
        "is_imported": True
    },
    {
        "fact": "The trauma from Kroger involved public humiliation and anxiety",
        "user_input": "The trauma from Kroger involved public humiliation and anxiety",
        "type": "extracted_fact",
        "perspective": "user",
        "tier": "semantic",
        "current_layer": "semantic",
        "importance": 0.8,
        "importance_score": 0.8,
        "turn_index": 0,
        "entities": ["Re", "Kroger"],
        "emotion_tags": ["anxiety"],
        "is_imported": True
    }
]

# Add to memory
for fact in test_facts:
    memory.memories.append(fact)
    memory.memory_layers.add_memory(fact, layer="semantic")

print(f"[SETUP] Added {len(test_facts)} imported facts")
print(f"[SETUP] Total memories: {len(memory.memories)}")

# Save to disk
memory._save_to_disk()
memory.memory_layers._save_to_disk()
print("[SETUP] Saved to disk")

# TEST 1: Query about imported content
print("\n" + "=" * 70)
print("TEST 1: Import Query - 'what's in what I just imported?'")
print("=" * 70)

memory.recall(state, "what's in what I just imported?")

print(f"\n[RESULT] Retrieved {len(state.last_recalled_memories)} memories")

# Count imported vs conversation
imported_count = sum(1 for m in state.last_recalled_memories if m.get('is_imported', False))
print(f"[RESULT] Imported facts in results: {imported_count}")

if imported_count >= 2:
    print(f"[SUCCESS] Import query retrieves imported facts!")
else:
    print(f"[FAIL] Only {imported_count} imported facts retrieved (expected >= 2)")

print("\nTop 10 retrieved memories:")
for i, mem in enumerate(state.last_recalled_memories[:10], 1):
    fact = mem.get('fact', mem.get('user_input', ''))[:50]
    is_imp = '[IMP]' if mem.get('is_imported') else '[CONV]'
    print(f"  {i}. {is_imp} {fact}...")

# TEST 2: Specific query about content
print("\n" + "=" * 70)
print("TEST 2: Specific Query - 'Tell me about Kroger'")
print("=" * 70)

memory.recall(state, "Tell me about Kroger")

imported_count = sum(1 for m in state.last_recalled_memories if m.get('is_imported', False))
kroger_facts = [m for m in state.last_recalled_memories if 'Kroger' in str(m.get('entities', []))]

print(f"\n[RESULT] Retrieved {len(state.last_recalled_memories)} memories")
print(f"[RESULT] Imported facts: {imported_count}")
print(f"[RESULT] Kroger-related facts: {len(kroger_facts)}")

if len(kroger_facts) >= 2:
    print(f"[SUCCESS] Specific query retrieves relevant imported facts!")
else:
    print(f"[FAIL] Only {len(kroger_facts)} Kroger facts retrieved")

print("\nKroger-related memories:")
for i, mem in enumerate(kroger_facts[:5], 1):
    fact = mem.get('fact', mem.get('user_input', ''))[:60]
    is_imp = '[IMP]' if mem.get('is_imported') else '[CONV]'
    print(f"  {i}. {is_imp} {fact}...")

# TEST 3: Check scoring breakdown
print("\n" + "=" * 70)
print("TEST 3: Scoring Analysis")
print("=" * 70)

print("\nImported fact scoring for query 'what's in what I just imported?':")
for fact in test_facts:
    fact_text = fact['fact'][:40]
    importance = fact['importance_score']
    is_imported = fact.get('is_imported', False)

    # Simulate boost calculation
    turns_since_import = memory.current_turn - fact['turn_index']
    if is_imported and turns_since_import < 50:
        import_boost = 1.0 + (2.0 * max(0, (50 - turns_since_import) / 50))
        # Check if query would trigger
        if "what" in "what's in what I just imported?".lower() and "import" in "what's in what I just imported?".lower():
            import_boost *= 5.0
    else:
        import_boost = 1.0

    base_score = importance * 0.20  # Just importance component
    final_score = base_score * import_boost

    print(f"  {fact_text}...")
    print(f"    Base score: {base_score:.3f}, Boost: {import_boost:.1f}x, Final: {final_score:.3f}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
