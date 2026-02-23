"""
Test Identity Memory Protection (Stage 2 + Stage 3)

This test validates that identity facts (score >= 999.0) survive through both:
- Stage 2 PRE-FILTER (keyword scoring bypass)
- Stage 3 GLYPH FILTER (auto-inclusion before LLM)

Expected behavior:
1. Identity facts should appear in Stage 2 output with [PRE-FILTER PROTECT] logging
2. Identity facts should appear in Stage 3 output with [IDENTITY AUTO-INCLUDE] logging
3. Final memory count should include all identity facts + LLM selections
"""

import os
import sys

# Disable debug tracking to avoid errors with protected memories
os.environ["DEBUG_MEMORY_TRACKING"] = "0"

from context_filter import GlyphFilter

# Create test memories (simulating Stage 1 output)
test_memories = [
    # IDENTITY FACTS (should be protected)
    {
        "fact": "Gimpy is a pigeon Kay knows from the park",
        "user_input": "Tell me about the pigeons you know",
        "turn": 5,
        "score": 999.0,  # Identity marker
        "is_identity": True,
        "topic": "relationships",
        "entities": ["Gimpy", "pigeon"],
        "importance_score": 0.9
    },
    {
        "fact": "Bob is another pigeon Kay knows",
        "user_input": "What about Bob?",
        "turn": 6,
        "score": 999.0,  # Identity marker
        "is_identity": True,
        "topic": "relationships",
        "entities": ["Bob", "pigeon"],
        "importance_score": 0.9
    },
    {
        "fact": "Fork is a pigeon with a crooked foot",
        "user_input": "Who is Fork?",
        "turn": 7,
        "score": 999.0,  # Identity marker
        "is_identity": True,
        "topic": "relationships",
        "entities": ["Fork", "pigeon"],
        "importance_score": 0.9
    },
    {
        "fact": "Zebra is a black and white striped pigeon",
        "user_input": "Tell me about Zebra",
        "turn": 8,
        "score": 999.0,  # Identity marker
        "is_identity": True,
        "topic": "relationships",
        "entities": ["Zebra", "pigeon"],
        "importance_score": 0.9
    },
    # NORMAL MEMORIES (should compete via keywords)
    {
        "fact": "Pigeons like bread crumbs",
        "user_input": "What do pigeons eat?",
        "turn": 3,
        "score": 0.6,
        "entities": ["pigeon", "bread"],
        "importance_score": 0.4
    },
    {
        "fact": "The park has many pigeons",
        "user_input": "Where do you see pigeons?",
        "turn": 2,
        "score": 0.5,
        "entities": ["park", "pigeon"],
        "importance_score": 0.3
    },
    {
        "fact": "Kay visits the park on weekends",
        "user_input": "When do you go to the park?",
        "turn": 1,
        "score": 0.4,
        "entities": ["Kay", "park"],
        "importance_score": 0.3
    },
]

# Add many filler memories to simulate realistic scenario
for i in range(100):
    test_memories.append({
        "fact": f"Generic memory #{i} about various topics",
        "user_input": f"Random conversation #{i}",
        "turn": i + 10,
        "score": 0.3,
        "entities": [f"topic{i}"],
        "importance_score": 0.2
    })

print("="*80)
print("IDENTITY MEMORY PROTECTION TEST")
print("="*80)
print(f"\nTest setup:")
print(f"  Total memories: {len(test_memories)}")
print(f"  Identity facts: 4 (Gimpy, Bob, Fork, Zebra)")
print(f"  Normal memories: {len(test_memories) - 4}")
print(f"\nQuery: 'What pigeons do I know?'")
print(f"Expected: All 4 identity facts should survive Stage 2 and Stage 3")
print("="*80)

# Create agent state
agent_state = {
    "memories": test_memories,
    "emotional_cocktail": {
        "curiosity": {"intensity": 0.6, "age": 0}
    },
    "recent_turns": [
        {"user": "What pigeons do I know?", "kay": "Let me think about that..."}
    ]
}

# Initialize glyph filter
context_filter = GlyphFilter(filter_model="claude-3-5-haiku-20241022")

print("\n" + "="*80)
print("RUNNING STAGE 2: PRE-FILTER")
print("="*80)

# Test Stage 2 pre-filter
pre_filtered = context_filter._prefilter_memories_by_relevance(
    test_memories,
    "What pigeons do I know?",
    max_count=20  # Small cap to test protection
)

print(f"\n[TEST] Stage 2 output: {len(pre_filtered)} memories")

# Check identity facts survived Stage 2
identity_survived_s2 = []
for mem in pre_filtered:
    if mem.get("score", 0) >= 999.0:
        identity_survived_s2.append(mem["fact"])

print(f"[TEST] Identity facts in Stage 2 output: {len(identity_survived_s2)}")
for fact in identity_survived_s2:
    print(f"  [OK] {fact}")

if len(identity_survived_s2) != 4:
    print(f"\n[FAIL] STAGE 2 FAILED: Expected 4 identity facts, got {len(identity_survived_s2)}")
    sys.exit(1)
else:
    print(f"\n[PASS] STAGE 2 PASSED: All 4 identity facts protected from keyword scoring!")

print("\n" + "="*80)
print("RUNNING STAGE 3: GLYPH FILTER")
print("="*80)

# Update agent state with pre-filtered memories
agent_state["memories"] = pre_filtered

# Test Stage 3 glyph filter (with identity auto-inclusion)
try:
    glyph_output = context_filter.filter_context(
        agent_state,
        "What pigeons do I know?"
    )

    print(f"\n[TEST] Stage 3 complete")
    print(f"[TEST] Glyph output: {glyph_output[:200]}...")

    # Extract MEM[...] indices from glyph output
    import re
    mem_match = re.search(r'MEM\[([0-9,]+)\]', glyph_output)
    if mem_match:
        indices = [int(idx.strip()) for idx in mem_match.group(1).split(',')]
        selected_memories = [pre_filtered[idx] for idx in indices if idx < len(pre_filtered)]

        identity_survived_s3 = []
        for mem in selected_memories:
            if mem.get("score", 0) >= 999.0:
                identity_survived_s3.append(mem["fact"])

        print(f"\n[TEST] Total memories selected: {len(selected_memories)}")
        print(f"[TEST] Identity facts in Stage 3 output: {len(identity_survived_s3)}")
        for fact in identity_survived_s3:
            print(f"  [OK] {fact}")

        if len(identity_survived_s3) != 4:
            print(f"\n[FAIL] STAGE 3 FAILED: Expected 4 identity facts, got {len(identity_survived_s3)}")
            sys.exit(1)
        else:
            print(f"\n[PASS] STAGE 3 PASSED: All 4 identity facts auto-included!")
    else:
        print(f"\n[FAIL] STAGE 3 FAILED: No MEM[...] line in glyph output")
        sys.exit(1)

except Exception as e:
    print(f"\n[FAIL] STAGE 3 FAILED WITH ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)
print(f"\n*** ALL TESTS PASSED ***")
print(f"\nIdentity protection working at BOTH stages:")
print(f"  Stage 2 (PRE-FILTER): Protected 4/4 identity facts from keyword scoring")
print(f"  Stage 3 (GLYPH FILTER): Auto-included 4/4 identity facts before LLM")
print(f"\nPigeon names (Gimpy, Bob, Fork, Zebra) will ALWAYS reach Kay!")
print("="*80)
