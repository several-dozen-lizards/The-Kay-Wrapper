"""
Test script for Memory Debug Tracker

This script tests the tracking functionality without needing to run the full Kay system.
"""
import os

# Enable debug tracking
os.environ["DEBUG_MEMORY_TRACKING"] = "1"

from engines.memory_debug_tracker import MemoryDebugTracker, reset_tracker, get_tracker

print("="*80)
print("MEMORY DEBUG TRACKER - TEST")
print("="*80)

# Create test memories
test_memories = [
    {"turn_index": 8, "fact": "Gimpy is a pigeon that Re told Kay about", "type": "extracted_fact"},
    {"turn_index": 8, "fact": "Bob is another pigeon Re mentioned", "type": "extracted_fact"},
    {"turn_index": 8, "fact": "Fork is a pigeon with a distinctive marking", "type": "extracted_fact"},
    {"turn_index": 8, "fact": "Zebra is a pigeon in the flock", "type": "extracted_fact"},
    {"turn_index": 12, "fact": "Clarence is the newest pigeon", "type": "extracted_fact"},
    {"turn_index": 15, "fact": "Kay likes coffee", "type": "extracted_fact"},
    {"turn_index": 20, "fact": "Re lives in Portland", "type": "extracted_fact"},
    {"turn_index": 25, "fact": "The pigeons live in the park", "type": "extracted_fact"},
]

# Initialize tracker
reset_tracker()
tracker = get_tracker(["Gimpy", "Bob", "Fork", "Zebra", "Clarence", "pigeon"])

# Test Stage 0
print("\n[TEST] Stage 0: Full dataset")
tracker.track_stage_0(test_memories, "What pigeons do I know?")

# Simulate Stage 1: SLOT_ALLOCATION (keep 5 memories)
allocated = test_memories[:5]  # First 5 memories
scored = [(0.8, mem) for mem in test_memories]  # Mock scores

print("\n[TEST] Stage 1: After SLOT_ALLOCATION")
tracker.track_stage_1(allocated, scored)

# Simulate Stage 2: PRE-FILTER (keep 3 memories)
prefiltered = allocated[:3]  # First 3 memories
scored_prefilter = [(mem, 50.0 + i*10) for i, mem in enumerate(allocated)]  # Mock scores

print("\n[TEST] Stage 2: After PRE-FILTER")
tracker.track_stage_2(prefiltered, scored_prefilter)

# Simulate Stage 3: GLYPH FILTER (keep 1 memory)
glyph_filtered = [prefiltered[0]]  # Only first memory

print("\n[TEST] Stage 3: After GLYPH FILTER")
tracker.track_stage_3(glyph_filtered, prefiltered)

# Print summary
tracker.print_summary()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
print("\nExpected results:")
print("  - Gimpy: Should survive all stages (in first position)")
print("  - Bob: Should survive Stage 1 and 2, die at Stage 3")
print("  - Fork: Should survive Stage 1 and 2, die at Stage 3")
print("  - Zebra: Should survive Stage 1, die at Stage 2")
print("  - Clarence: Should survive Stage 1, die at Stage 2")
print("  - pigeon: Should appear in multiple memories, track all instances")
print("\nIf the output above matches these expectations, tracking is working correctly!")
