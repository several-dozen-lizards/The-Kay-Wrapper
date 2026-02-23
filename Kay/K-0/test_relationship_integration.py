"""
Test relationship memory integration into main pipeline.
Verifies that relationship context flows through to LLM prompts.
"""

import os
os.environ['VERBOSE_DEBUG'] = 'false'  # Reduce noise for focused test

from engines.relationship_memory import RelationshipMemory
from integrations.llm_integration import build_prompt_from_context

print("=" * 80)
print("RELATIONSHIP MEMORY INTEGRATION TEST")
print("=" * 80)

# Initialize relationship memory
print("\n[STEP 1] Initialize relationship memory")
relationship = RelationshipMemory()
stats = relationship.get_stats()
print(f"  Landmarks: {stats['landmarks']}")
print(f"  Re states: {stats['re_states_tracked']}")
print(f"  Topics: {stats['topics_tracked']}")

# Build relationship context
print("\n[STEP 2] Build relationship context")
relationship_context = relationship.build_relationship_context()
print(f"  Context length: {len(relationship_context)} chars")
print(f"  Contains 'LANDMARKS': {'LANDMARKS' in relationship_context}")
print(f"  Contains landmarks: {relationship_context[:100]}...")

# Create mock context dict (simulating main.py filtered_prompt_context)
print("\n[STEP 3] Create mock context with relationship data")
mock_context = {
    "user_input": "How are you doing today?",
    "recalled_memories": [
        {
            "fact": "Re's dog is named Saga",
            "perspective": "user",
            "type": "semantic"
        },
        {
            "fact": "Kay likes coffee",
            "perspective": "kay",
            "type": "semantic"
        }
    ],
    "emotional_state": {"cocktail": {"curiosity": {"intensity": 0.7, "age": 1}}},
    "body": {"dopamine": 0.5, "serotonin": 0.6},
    "recent_context": [],
    "momentum_notes": [],
    "meta_awareness_notes": [],
    "consolidated_preferences": {},
    "preference_contradictions": [],
    "rag_chunks": [],
    "relationship_context": relationship_context,  # NEW: Relationship patterns
    "turn_count": 5,
    "recent_responses": [],
    "session_id": "test_session"
}

print(f"  Context keys: {list(mock_context.keys())}")
print(f"  Relationship context included: {'relationship_context' in mock_context}")

# Build prompt using llm_integration
print("\n[STEP 4] Build LLM prompt with relationship context")
try:
    prompt = build_prompt_from_context(mock_context, affect_level=3.5)
    print(f"  Prompt built successfully")
    print(f"  Prompt length: {len(prompt)} chars")
except Exception as e:
    print(f"  [ERROR] Failed to build prompt: {e}")
    import traceback
    traceback.print_exc()
    prompt = None

# Verify relationship context appears in prompt
if prompt:
    print("\n[STEP 5] Verify relationship patterns in prompt")

    checks = {
        "RELATIONSHIP PATTERNS section": "RELATIONSHIP PATTERNS" in prompt,
        "LANDMARKS section": "LANDMARKS" in prompt or "landmarks" in prompt.lower(),
        "wrapper landmark": "wrapper" in prompt.lower(),
        "Creiddylad landmark": "Creiddylad" in prompt or "creiddylad" in prompt.lower(),
        "TOPICS section": "TOPICS" in prompt
    }

    for check_name, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {check_name}")

    # Show excerpt of relationship section
    if "RELATIONSHIP PATTERNS" in prompt:
        start_idx = prompt.index("RELATIONSHIP PATTERNS")
        excerpt = prompt[start_idx:start_idx+500]
        print(f"\n[EXCERPT] Relationship patterns in prompt:")
        print("  " + excerpt.replace("\n", "\n  ")[:400] + "...")

    all_passed = all(checks.values())
else:
    all_passed = False

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

if all_passed and prompt:
    print("[SUCCESS] Relationship memory integration working correctly")
    print("  [PASS] Relationship memory initializes")
    print("  [PASS] Context builds correctly")
    print("  [PASS] Prompts include relationship patterns")
    print("  [PASS] Landmarks appear in final prompt")
else:
    print("[FAILURE] Integration issues detected")
    if not prompt:
        print("  [FAIL] Failed to build prompt")
    else:
        for check_name, result in checks.items():
            if not result:
                print(f"  [FAIL] Missing: {check_name}")

print("=" * 80)
