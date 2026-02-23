"""
Test relationship memory system.
Verifies landmarks, patterns, and context building.
"""

from engines.relationship_memory import RelationshipMemory

print("=" * 80)
print("RELATIONSHIP MEMORY TEST")
print("=" * 80)

# Initialize
rm = RelationshipMemory()

print(f"\n[SETUP] Relationship memory initialized")
print(f"[SETUP] Data directory: {rm.data_dir}")

# Test 1: Check initial landmarks
print("\n" + "=" * 80)
print("TEST 1: Initial Landmarks")
print("=" * 80)

print(f"\nTotal landmarks: {len(rm.landmarks)}")
print("\nLandmarks:")
for i, lm in enumerate(rm.landmarks, 1):
    print(f"  {i}. {lm['description'][:60]}...")
    print(f"     Significance: {lm['significance'][:60]}...")
    print(f"     Tags: {', '.join(lm['tags'])}")
    print()

# Test 2: Record new patterns
print("=" * 80)
print("TEST 2: Record Patterns")
print("=" * 80)

print("\n[Recording Re's state - focused]")
rm.record_re_state(
    state_type="focused",
    observation="Deep work mode, minimal chat, precise technical questions",
    context="Building memory system"
)

print("[Recording Re's state - tired]")
rm.record_re_state(
    state_type="tired",
    observation="Shorter messages, more typos, but still engaged",
    context="Late night session"
)

print("[Recording topic response - pigeons]")
rm.record_topic_response(
    topic="pigeons",
    response_type="lights_up",
    notes="Immediate excitement, wants to share everything about them"
)

print("[Recording topic response - memory architecture]")
rm.record_topic_response(
    topic="memory architecture",
    response_type="lights_up",
    notes="Dives deep, asks detailed questions, energized by complexity"
)

print("[Recording topic response - emotional manipulation]")
rm.record_topic_response(
    topic="emotional manipulation ethics",
    response_type="shuts_down",
    notes="Immediate guilt, withdraws, apologizes profusely"
)

print("[Recording support pattern - overwhelmed]")
rm.record_support_pattern(
    situation="feeling overwhelmed",
    what_helped="Direct acknowledgment without forcing discussion",
    what_didnt="Trying to fix immediately, asking too many questions"
)

print("[Recording interaction rhythm - work sessions]")
rm.record_rhythm(
    rhythm_type="work_sessions",
    observation="Works in intense 2-3 hour bursts, then needs break"
)

# Test 3: Build context
print("\n" + "=" * 80)
print("TEST 3: Build Relationship Context")
print("=" * 80)

print("\n--- General Context ---")
general_context = rm.build_relationship_context()
print(general_context)

print("\n--- Context with Re in 'focused' state ---")
focused_context = rm.build_relationship_context(current_re_state="focused")
print(focused_context)

print("\n--- Context with Re in 'tired' state ---")
tired_context = rm.build_relationship_context(current_re_state="tired")
print(tired_context)

# Test 4: Query patterns
print("\n" + "=" * 80)
print("TEST 4: Query Patterns")
print("=" * 80)

print("\nTopics Re lights up about:")
lights_up_topics = rm.get_topics_by_response("lights_up")
for topic in lights_up_topics:
    print(f"  - {topic}")

print("\nTopics Re avoids/shuts down:")
shuts_down_topics = rm.get_topics_by_response("shuts_down")
for topic in shuts_down_topics:
    print(f"  - {topic}")

print("\nRe's state patterns:")
state_patterns = rm.get_re_state_patterns()
for state, observations in state_patterns.items():
    print(f"  {state}: {len(observations)} observation(s)")

# Test 5: Add new landmark
print("\n" + "=" * 80)
print("TEST 5: Add New Landmark")
print("=" * 80)

new_landmark = rm.record_landmark(
    description="First test of relationship memory system",
    significance="Testing connection texture tracking",
    tags=["test", "technical"]
)

print(f"\nNew landmark recorded:")
print(f"  Description: {new_landmark['description']}")
print(f"  Significance: {new_landmark['significance']}")
print(f"  Timestamp: {new_landmark['timestamp']}")
print(f"  Confidence: {new_landmark['confidence']}")

# Test 6: Stats
print("\n" + "=" * 80)
print("TEST 6: Relationship Memory Stats")
print("=" * 80)

stats = rm.get_stats()
print(f"\nRelationship Memory Statistics:")
print(f"  Landmarks: {stats['landmarks']}")
print(f"  Re states tracked: {stats['re_states_tracked']}")
print(f"  Topics tracked: {stats['topics_tracked']}")
print(f"  Rhythms tracked: {stats['rhythms_tracked']}")
print(f"  Support patterns: {stats['support_patterns']}")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

all_pass = True

# Check initial landmarks
if len(rm.landmarks) >= 6:
    print("[PASS] Initial landmarks seeded (6+ landmarks)")
else:
    print(f"[FAIL] Missing initial landmarks (found {len(rm.landmarks)}, expected >=6)")
    all_pass = False

# Check pattern recording
if stats['re_states_tracked'] >= 2:
    print("[PASS] Re states recorded successfully")
else:
    print("[FAIL] Re states not recorded")
    all_pass = False

if stats['topics_tracked'] >= 3:
    print("[PASS] Topic responses recorded successfully")
else:
    print("[FAIL] Topic responses not recorded")
    all_pass = False

# Check context building
if "RELATIONSHIP LANDMARKS" in general_context:
    print("[PASS] Context building works")
else:
    print("[FAIL] Context building failed")
    all_pass = False

# Check topic filtering
if len(lights_up_topics) >= 2:
    print("[PASS] Topic filtering works")
else:
    print("[FAIL] Topic filtering failed")
    all_pass = False

if all_pass:
    print("\n[SUCCESS] ALL TESTS PASSED - Relationship memory system working correctly")
else:
    print("\n[FAILURE] SOME TESTS FAILED - Check implementation")

print("=" * 80)
print(f"\nData persisted to:")
print(f"  - {rm.patterns_file}")
print(f"  - {rm.landmarks_file}")
print("=" * 80)
