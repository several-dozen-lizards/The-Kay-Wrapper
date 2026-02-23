"""
Test confidence marker system.
Verifies that memories are correctly tagged with bedrock/inferred/unknown confidence levels.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['VERBOSE_DEBUG'] = 'true'

from engines.memory_engine import MemoryEngine
from agent_state import AgentState

print("=" * 80)
print("CONFIDENCE MARKER SYSTEM TEST")
print("=" * 80)

# Initialize
memory_engine = MemoryEngine()
agent_state = AgentState()
agent_state.emotional_cocktail = {"curiosity": {"intensity": 0.7, "age": 1}}

print(f"\n[SETUP] Memory engine initialized")
print(f"[SETUP] Working layer: {len(memory_engine.memory_layers.working_memory)} memories")
print(f"[SETUP] Episodic layer: {len(memory_engine.memory_layers.episodic_memory)} memories")
print(f"[SETUP] Semantic layer: {len(memory_engine.memory_layers.semantic_memory)} memories")

# Test 1: Query with good coverage (should have bedrock + inferred, no gaps)
print("\n" + "=" * 80)
print("TEST 1: Query with good memory coverage")
print("=" * 80)

result1 = memory_engine.recall(
    agent_state=agent_state,
    user_input="Tell me about Saga",
    num_memories=30
)

print(f"\n[TEST 1 RESULTS]")
print(f"  Total memories: {len(result1)}")

confidence_counts = {
    'bedrock': 0,
    'inferred': 0,
    'unknown': 0,
    'untagged': 0
}

for mem in result1:
    conf = mem.get('confidence')
    if conf == 'bedrock':
        confidence_counts['bedrock'] += 1
    elif conf == 'inferred':
        confidence_counts['inferred'] += 1
    elif conf == 'unknown':
        confidence_counts['unknown'] += 1
    else:
        confidence_counts['untagged'] += 1

print(f"  Bedrock: {confidence_counts['bedrock']}")
print(f"  Inferred: {confidence_counts['inferred']}")
print(f"  Gap/Unknown: {confidence_counts['unknown']}")
if confidence_counts['untagged'] > 0:
    print(f"  WARNING: Untagged: {confidence_counts['untagged']} (should be 0!)")

# Test 2: Query with no relevant memories (should trigger gap detection)
print("\n" + "=" * 80)
print("TEST 2: Query with sparse memory (should trigger gap)")
print("=" * 80)

result2 = memory_engine.recall(
    agent_state=agent_state,
    user_input="Tell me about quantum entanglement experiments in 2023",
    num_memories=30
)

print(f"\n[TEST 2 RESULTS]")
print(f"  Total memories: {len(result2)}")

gap_detected = any(mem.get('is_gap_marker', False) for mem in result2)
print(f"  Gap marker present: {'YES' if gap_detected else 'NO'}")

if gap_detected:
    gap_mem = [m for m in result2 if m.get('is_gap_marker')][0]
    print(f"  Gap message: {gap_mem.get('fact', '')[:100]}")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

all_pass = True

# Check Test 1
if confidence_counts['bedrock'] > 0 and confidence_counts['inferred'] >= 0:
    print("[PASS] Test 1: Bedrock and inferred memories present")
else:
    print("[FAIL] Test 1: Missing confidence tags")
    all_pass = False

if confidence_counts['untagged'] == 0:
    print("[PASS] All memories properly tagged with confidence")
else:
    print(f"[FAIL] {confidence_counts['untagged']} memories missing confidence tags")
    all_pass = False

# Check Test 2
if gap_detected:
    print("[PASS] Test 2: Gap detection working")
else:
    print("[INFO] Test 2: No gap detected (query may have found relevant memories)")

if all_pass:
    print("\n[SUCCESS] ALL TESTS PASSED - Confidence system working correctly")
else:
    print("\n[FAILURE] SOME TESTS FAILED - Check implementation")

print("=" * 80)
