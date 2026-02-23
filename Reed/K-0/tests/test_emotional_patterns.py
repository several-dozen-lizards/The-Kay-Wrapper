"""
Test Emotional Pattern Engine
Verifies behavioral emotion tracking without neurochemistry.
"""

from engines.emotional_patterns import EmotionalPatternEngine

print("=" * 80)
print("EMOTIONAL PATTERN ENGINE TEST")
print("=" * 80)

# Initialize
print("\n[STEP 1] Initialize emotional pattern engine")
emotions = EmotionalPatternEngine()
print(f"  Engine initialized")
print(f"  Data directory: {emotions.data_dir}")

# Test setting current state
print("\n[STEP 2] Set current emotional state")
state = emotions.set_current_state(
    emotions=["curiosity", "calm"],
    intensity=0.7,
    valence=0.6,
    arousal=0.4,
    stability=0.8,
    notes="Working on system integration"
)

print(f"  Emotions: {state['primary_emotions']}")
print(f"  Intensity: {state['intensity']}")
print(f"  Valence: {state['valence']}")
print(f"  Arousal: {state['arousal']}")
print(f"  Stability: {state['stability']}")
print(f"  Notes: {state['notes']}")

# Test state summary
print("\n[STEP 3] Get state summary")
summary = emotions.get_state_summary()
print(f"  Summary: {summary}")

# Test emotion extraction
print("\n[STEP 4] Extract emotions from response text")
test_responses = [
    "I'm feeling intensely curious about how this works",
    "This is frustrating - I can't quite get it",
    "There's a calm underneath the uncertainty",
    "I'm excited and a little anxious about this"
]

for i, response in enumerate(test_responses, 1):
    extraction = emotions.extract_from_response(response)
    print(f"  Test {i}: \"{response[:50]}...\"")
    print(f"    Detected: {extraction['detected_emotions']}")
    print(f"    Valence: {extraction['suggested_valence']:.2f}")

# Test trigger recording
print("\n[STEP 5] Record emotional triggers")
emotions.record_trigger(
    trigger="complex technical problem",
    resulting_emotions=["curiosity", "frustration", "determination"],
    context="Working on memory system"
)
print(f"  Trigger recorded: complex technical problem")

emotions.record_trigger(
    trigger="meaningful conversation",
    resulting_emotions=["warmth", "contentment", "curiosity"],
    context="Deep discussion with Re"
)
print(f"  Trigger recorded: meaningful conversation")

# Test context signature
print("\n[STEP 6] Record context signatures")
emotions.record_context_signature(
    context="coding session",
    emotions=["focus", "determination", "mild frustration"],
    notes="Typical working state"
)
print(f"  Context signature: coding session")

emotions.record_context_signature(
    context="reading documents",
    emotions=["curiosity", "calm", "analytical"],
    notes="Learning mode"
)
print(f"  Context signature: reading documents")

# Test progression tracking
print("\n[STEP 7] Set new state to track progression")
emotions.set_current_state(
    emotions=["determination", "clarity"],
    intensity=0.8,
    valence=0.7,
    arousal=0.7
)
print(f"  New state set: determination, clarity")
print(f"  Progression tracked: curiosity/calm -> determination/clarity")

# Test context building
print("\n[STEP 8] Build emotional context for prompt")
context = emotions.build_emotion_context()
print(f"  Context built:")
print("  " + context.replace("\n", "\n  "))

# Test frequent emotions
print("\n[STEP 9] Get frequent emotions")
frequent = emotions.get_frequent_emotions(days=7, top_n=5)
print(f"  Frequent emotions (past 7 days): {', '.join(frequent) if frequent else 'none yet'}")

# Test stats
print("\n[STEP 10] Get engine stats")
stats = emotions.get_stats()
print(f"  Current emotions: {stats['current_emotions']}")
print(f"  Emotions tracked: {stats['emotions_tracked']}")
print(f"  Triggers mapped: {stats['triggers_mapped']}")
print(f"  Progressions recorded: {stats['progressions_recorded']}")
print(f"  Context signatures: {stats['context_signatures']}")

# Test category awareness
print("\n[STEP 11] Emotion categories")
for category, emotion_list in emotions.CATEGORIES.items():
    print(f"  {category}: {', '.join(emotion_list[:3])}...")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

all_passed = True

# Check state setting (check current state, not old variable)
current_state = emotions.get_current_state()
if current_state['primary_emotions'] == ["determination", "clarity"]:
    print("[PASS] State setting works")
else:
    print(f"[FAIL] State setting failed - got {current_state['primary_emotions']}")
    all_passed = False

# Check extraction
extraction_test = emotions.extract_from_response("I'm curious and excited")
if "curiosity" in extraction_test["detected_emotions"] or "excitement" in extraction_test["detected_emotions"]:
    print("[PASS] Emotion extraction works")
else:
    print("[FAIL] Emotion extraction failed")
    all_passed = False

# Check trigger recording
if stats['triggers_mapped'] >= 2:
    print("[PASS] Trigger recording works")
else:
    print("[FAIL] Trigger recording failed")
    all_passed = False

# Check context building
if context and "EMOTIONAL STATE" in context:
    print("[PASS] Context building works")
else:
    print("[FAIL] Context building failed")
    all_passed = False

# Check progression tracking
if stats['progressions_recorded'] >= 1:
    print("[PASS] Progression tracking works")
else:
    print("[FAIL] Progression tracking failed")
    all_passed = False

if all_passed:
    print("\n[SUCCESS] ALL TESTS PASSED - Emotional pattern engine working correctly")
else:
    print("\n[FAILURE] SOME TESTS FAILED - Check implementation")

print("=" * 80)
print(f"\nData persisted to:")
print(f"  - {emotions.patterns_file}")
print(f"  - {emotions.current_file}")
print("=" * 80)
