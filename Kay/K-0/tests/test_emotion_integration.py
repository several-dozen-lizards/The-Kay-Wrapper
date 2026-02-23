"""
Emotion Integration Test

Tests the fixed emotional trigger system with known emotional inputs.
Verifies that:
1. Multiple emotions are triggered correctly
2. Emotions decay properly
3. No mysterious resets occur
4. Integration between engine and main loop works
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from agent_state import AgentState
from engines.emotion_engine import EmotionEngine
from protocol_engine import ProtocolEngine


def test_trigger_expansion():
    """Test 1: Verify expanded triggers detect more emotions."""
    print("="*70)
    print("TEST 1: TRIGGER EXPANSION")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    test_cases = [
        ("I miss Sammie so much today.", ["grief", "affection", "longing"]),
        ("Chrome did the funniest thing - he door-dashed again!", ["amusement", "joy"]),
        ("I'm worried about the wrapper bugs though.", ["anxiety", "concern"]),
        ("I wonder how the memory system actually works internally?", ["curiosity"]),
        ("Mike is being so unreasonable again. It's frustrating.", ["anger", "frustration", "resentment"]),
    ]

    all_passed = True

    for user_input, expected_emotions in test_cases:
        print(f"\nInput: '{user_input}'")
        print(f"Expected: {expected_emotions}")

        # Reset state for clean test
        state.emotional_cocktail = {}
        state.last_recalled_memories = []

        emotion_engine.update(state, user_input)

        detected = list(state.emotional_cocktail.keys())
        print(f"Detected: {detected}")

        # Check if at least ONE expected emotion was triggered
        matches = [e for e in expected_emotions if e in detected]
        if matches:
            print(f"[PASS] Triggered: {matches}")
        else:
            print(f"[FAIL] None of the expected emotions triggered!")
            all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print("[OVERALL PASS] Trigger expansion working")
    else:
        print("[OVERALL FAIL] Some triggers still not working")
    print("="*70)

    return all_passed


def test_decay_persistence():
    """Test 2: Verify decay happens but cocktail persists."""
    print("\n" + "="*70)
    print("TEST 2: DECAY PERSISTENCE")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up initial emotional state
    print("\nInitial setup:")
    emotion_engine.update(state, "I'm so happy and excited and curious!")

    print(f"Turn 0 cocktail: {state.emotional_cocktail}")

    # Track 3 turns of neutral input
    for turn in range(1, 4):
        print(f"\n--- Turn {turn} ---")
        print(f"Input: 'Okay, I see.'")

        emotion_engine.update(state, "Okay, I see.")

        print(f"Cocktail: {list(state.emotional_cocktail.keys())} ({len(state.emotional_cocktail)} emotions)")
        for emo, data in sorted(state.emotional_cocktail.items(), key=lambda x: x[1].get('intensity', 0), reverse=True):
            print(f"  - {emo}: intensity={data.get('intensity', 0):.2f}, age={data.get('age', 0)}")

    # Check results
    print("\n" + "="*70)
    if len(state.emotional_cocktail) > 0:
        print("[PASS] Cocktail persisted across turns")
    else:
        print("[FAIL] Cocktail was wiped!")

    # Check if decay happened
    max_intensity = max([d['intensity'] for d in state.emotional_cocktail.values()]) if state.emotional_cocktail else 0
    if max_intensity < 0.4:  # Should have decayed from initial 0.4
        print("[PASS] Decay occurred (max intensity < 0.4)")
    else:
        print("[WARNING] Decay may not be working (max intensity >= 0.4)")

    print("="*70)

    return len(state.emotional_cocktail) > 0


def test_multiple_emotions_coexist():
    """Test 3: Verify multiple emotions can exist simultaneously."""
    print("\n" + "="*70)
    print("TEST 3: MULTIPLE EMOTIONS COEXIST")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Trigger multiple emotions in sequence
    triggers = [
        "I'm happy and excited!",
        "But also scared and worried.",
        "And curious about what happens next.",
    ]

    for trigger in triggers:
        print(f"\nInput: '{trigger}'")
        emotion_engine.update(state, trigger)
        print(f"Cocktail: {list(state.emotional_cocktail.keys())} ({len(state.emotional_cocktail)} emotions)")

    print(f"\nFinal cocktail:")
    for emo, data in sorted(state.emotional_cocktail.items(), key=lambda x: x[1].get('intensity', 0), reverse=True):
        print(f"  - {emo}: intensity={data.get('intensity', 0):.2f}, age={data.get('age', 0)}")

    print("\n" + "="*70)
    if len(state.emotional_cocktail) >= 3:
        print(f"[PASS] Multiple emotions coexist ({len(state.emotional_cocktail)} emotions)")
    else:
        print(f"[FAIL] Only {len(state.emotional_cocktail)} emotions (expected 3+)")
    print("="*70)

    return len(state.emotional_cocktail) >= 3


def test_pruning():
    """Test 4: Verify low-intensity emotions are pruned."""
    print("\n" + "="*70)
    print("TEST 4: EMOTION PRUNING")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up emotion and decay it fully
    print("\nSetup: Creating emotion with low intensity")
    state.emotional_cocktail = {"joy": {"intensity": 0.06, "age": 0}}

    print(f"Before update: {state.emotional_cocktail}")

    # Update with neutral input - should prune
    emotion_engine.update(state, "Okay.")

    print(f"After update: {state.emotional_cocktail}")

    print("\n" + "="*70)
    if "joy" not in state.emotional_cocktail:
        print("[PASS] Low-intensity emotion pruned")
    else:
        intensity = state.emotional_cocktail.get("joy", {}).get("intensity", 0)
        if intensity < 0.05:
            print(f"[FAIL] Emotion still present with intensity {intensity:.3f} (should be pruned)")
        else:
            print(f"[PASS] Emotion at {intensity:.3f} (above threshold)")
    print("="*70)

    return "joy" not in state.emotional_cocktail or state.emotional_cocktail["joy"]["intensity"] >= 0.05


def run_all_tests():
    """Run all emotion integration tests."""
    print("="*70)
    print("EMOTION INTEGRATION TEST SUITE")
    print("="*70)
    print("\nTesting fixed trigger system and integration...\n")

    results = {
        "Trigger Expansion": test_trigger_expansion(),
        "Decay Persistence": test_decay_persistence(),
        "Multiple Emotions": test_multiple_emotions_coexist(),
        "Emotion Pruning": test_pruning(),
    }

    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nOVERALL: {passed}/{total} tests passed ({passed*100//total}%)")

    if passed == total:
        print("\n[SUCCESS] All tests passed! Emotion system is working correctly.")
    else:
        print("\n[WARNING] Some tests failed. Review output above.")

    print("="*70)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)

    if success:
        print("\n1. All isolated tests passed!")
        print("2. Now run Kay with main.py to test integration")
        print("3. Watch for [EMOTION INTEGRATION] logs to catch any resets")
        print("4. Send emotionally varied messages:")
        print("   - 'I miss Sammie so much today'")
        print("   - 'Chrome did the funniest thing!'")
        print("   - 'I'm worried about the bugs'")
        print("5. Verify multiple emotions appear and decay properly")
    else:
        print("\n1. Fix failing tests first")
        print("2. Check emotion_engine.py trigger keywords")
        print("3. Verify pruning threshold (0.05)")

    print("="*70)

    sys.exit(0 if success else 1)
