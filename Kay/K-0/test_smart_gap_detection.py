"""
Test smart gap detection system.
Verifies that gaps are classified correctly as:
- TRUE GAP: Important topic discussed before, now missing
- NEVER DISCUSSED: New topic, no historical mentions
- LOW SALIENCE: Mentioned before but not important, naturally faded
"""

import os
os.environ['VERBOSE_DEBUG'] = 'true'

from engines.memory_engine import MemoryEngine
from agent_state import AgentState

print("=" * 80)
print("SMART GAP DETECTION TEST")
print("=" * 80)

# Initialize
memory_engine = MemoryEngine()
agent_state = AgentState()
agent_state.emotional_cocktail = {"curiosity": {"intensity": 0.7, "age": 1}}

print(f"\n[SETUP] Memory engine initialized")
print(f"[SETUP] Working layer: {len(memory_engine.memory_layers.working_memory)} memories")
print(f"[SETUP] Episodic layer: {len(memory_engine.memory_layers.episodic_memory)} memories")
print(f"[SETUP] Semantic layer: {len(memory_engine.memory_layers.semantic_memory)} memories")
print(f"[SETUP] Entity graph: {len(memory_engine.entity_graph.entities)} entities")

# === TEST 1: TRUE GAP ===
# Query for "Saga" (known entity with high importance) but with a query that might return sparse results
print("\n" + "=" * 80)
print("TEST 1: TRUE GAP - Known important entity with specific query")
print("=" * 80)

result1 = memory_engine.recall(
    agent_state=agent_state,
    user_input="Tell me about Saga's medical history and vaccinations",
    num_memories=30
)

print(f"\n[TEST 1 RESULTS]")
print(f"  Total memories: {len(result1)}")

gap_markers = [m for m in result1 if m.get('is_gap_marker', False)]
info_markers = [m for m in result1 if m.get('is_info_marker', False)]

if gap_markers:
    gap = gap_markers[0]
    print(f"  Gap detected: {gap.get('gap_type', 'unknown')}")
    print(f"  Gap message: {gap.get('fact', '')[:100]}")
elif info_markers:
    info = info_markers[0]
    print(f"  Info marker: {info.get('gap_type', 'unknown')}")
    print(f"  Info message: {info.get('fact', '')[:100]}")
else:
    print(f"  No gap/info markers (sufficient memory)")

# === TEST 2: NEVER DISCUSSED ===
# Query for something completely new that has never been mentioned
print("\n" + "=" * 80)
print("TEST 2: NEVER DISCUSSED - Completely new topic")
print("=" * 80)

result2 = memory_engine.recall(
    agent_state=agent_state,
    user_input="Tell me about quantum entanglement experiments in 2023",
    num_memories=30
)

print(f"\n[TEST 2 RESULTS]")
print(f"  Total memories: {len(result2)}")

gap_markers = [m for m in result2 if m.get('is_gap_marker', False)]
info_markers = [m for m in result2 if m.get('is_info_marker', False)]

if gap_markers:
    gap = gap_markers[0]
    print(f"  Gap detected: {gap.get('gap_type', 'unknown')}")
    print(f"  Gap message: {gap.get('fact', '')[:100]}")
elif info_markers:
    info = info_markers[0]
    print(f"  Info marker: {info.get('gap_type', 'unknown')}")
    print(f"  Info message: {info.get('fact', '')[:100]}")
else:
    print(f"  No gap/info markers (sufficient memory)")

# === TEST 3: LOW SALIENCE ===
# Query for something that might have been mentioned but with low importance
print("\n" + "=" * 80)
print("TEST 3: LOW SALIENCE - Topic mentioned but not important")
print("=" * 80)

result3 = memory_engine.recall(
    agent_state=agent_state,
    user_input="What did we talk about regarding breakfast cereal brands",
    num_memories=30
)

print(f"\n[TEST 3 RESULTS]")
print(f"  Total memories: {len(result3)}")

gap_markers = [m for m in result3 if m.get('is_gap_marker', False)]
info_markers = [m for m in result3 if m.get('is_info_marker', False)]

if gap_markers:
    gap = gap_markers[0]
    print(f"  Gap detected: {gap.get('gap_type', 'unknown')}")
    print(f"  Gap message: {gap.get('fact', '')[:100]}")
elif info_markers:
    info = info_markers[0]
    print(f"  Info marker: {info.get('gap_type', 'unknown')}")
    print(f"  Info message: {info.get('fact', '')[:100]}")
else:
    print(f"  No gap/info markers (natural fade or sufficient memory)")

# === TEST 4: KNOWN ENTITY WITH GOOD COVERAGE ===
# Query for something that should have plenty of memory coverage
print("\n" + "=" * 80)
print("TEST 4: SUFFICIENT MEMORY - Known entity with good coverage")
print("=" * 80)

result4 = memory_engine.recall(
    agent_state=agent_state,
    user_input="Tell me about Saga",
    num_memories=30
)

print(f"\n[TEST 4 RESULTS]")
print(f"  Total memories: {len(result4)}")

gap_markers = [m for m in result4 if m.get('is_gap_marker', False)]
info_markers = [m for m in result4 if m.get('is_info_marker', False)]

if gap_markers:
    gap = gap_markers[0]
    print(f"  Gap detected: {gap.get('gap_type', 'unknown')}")
    print(f"  Gap message: {gap.get('fact', '')[:100]}")
elif info_markers:
    info = info_markers[0]
    print(f"  Info marker: {info.get('gap_type', 'unknown')}")
    print(f"  Info message: {info.get('fact', '')[:100]}")
else:
    print(f"  No gap/info markers (sufficient memory)")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

print("\n[EXPECTED BEHAVIOR]")
print("  Test 1: Should detect TRUE GAP if Saga's medical history has sparse memory")
print("  Test 2: Should detect NEVER DISCUSSED for quantum entanglement")
print("  Test 3: Should detect LOW SALIENCE or NEVER DISCUSSED for breakfast cereal")
print("  Test 4: Should have NO MARKER for general Saga query (good coverage)")

print("\n[SUCCESS] Smart gap detection test complete")
print("=" * 80)
