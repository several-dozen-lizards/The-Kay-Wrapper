"""
Emotional Architecture Diagnostic Tests

Tests Reed's ULTRAMAP-based emotional system:
1. Emotion Generation - verify new emotions created from conversation
2. Emotion Decay - verify intensity decreases over time
3. Emotional Cocktail - verify multiple emotions coexist
4. Memory Integration - verify emotions affect memory importance
5. ULTRAMAP Protocols - verify compression detection active

Run this to diagnose emotional system issues.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from agent_state import AgentState
from engines.emotion_engine import EmotionEngine
from protocol_engine import ProtocolEngine


def test_1_emotion_generation():
    """
    Test 1: Verify EmotionEngine creates new emotions from conversation content.

    Expected behavior:
    - Different trigger words should create different emotions
    - Multiple emotions should be generated from rich emotional content
    - Emotion cocktail should contain 3-4 emotions after varied input
    """
    print("\n" + "="*70)
    print("TEST 1: EMOTION GENERATION")
    print("="*70)

    # Initialize engines
    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    print(f"\nInitial state: {state.emotional_cocktail}")

    # Test different emotional triggers
    test_inputs = [
        ("I miss Sammie so much", "grief/longing"),
        ("Chrome did the funniest thing today!", "joy/amusement"),
        ("I wonder how the wrapper works internally?", "curiosity"),
        ("Mike is being unreasonable again", "anger/resentment"),
    ]

    emotions_generated = set()

    for user_input, expected_emotion in test_inputs:
        print(f"\nInput: '{user_input}'")
        print(f"Expected emotion: {expected_emotion}")

        emotion_engine.update(state, user_input)

        current_emotions = list(state.emotional_cocktail.keys())
        print(f"Current cocktail: {current_emotions}")
        print(f"Full state: {state.emotional_cocktail}")

        emotions_generated.update(current_emotions)

    print(f"\n--- RESULTS ---")
    print(f"Total unique emotions generated: {len(emotions_generated)}")
    print(f"Emotions: {emotions_generated}")
    print(f"Final cocktail size: {len(state.emotional_cocktail)}")

    # Test pass/fail criteria
    if len(emotions_generated) >= 3:
        print(f"[PASS] Multiple emotions generated ({len(emotions_generated)} unique)")
        return True
    else:
        print(f"[FAIL] Only {len(emotions_generated)} emotions generated (expected 3+)")
        print(f"ISSUE: Emotion generation may not be working correctly")
        return False


def test_2_emotion_decay():
    """
    Test 2: Verify emotions lose intensity as age increases.

    Expected behavior:
    - Intensity should decrease each turn without reinforcement
    - Age should increase each turn
    - Decay formula: intensity = intensity - (decay_rate / temporal_weight)
    - Emotions below threshold should be removed from cocktail
    """
    print("\n" + "="*70)
    print("TEST 2: EMOTION DECAY")
    print("="*70)

    # Initialize engines
    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Manually add an emotion to track
    state.emotional_cocktail = {
        "curiosity": {"intensity": 1.0, "age": 0}
    }

    print(f"Initial state: {state.emotional_cocktail}")

    # Run multiple turns WITHOUT reinforcement
    decay_history = []

    for turn in range(10):
        # Use neutral input that won't trigger curiosity
        emotion_engine.update(state, "Okay, I see.")

        if "curiosity" in state.emotional_cocktail:
            intensity = state.emotional_cocktail["curiosity"]["intensity"]
            age = state.emotional_cocktail["curiosity"]["age"]
            decay_history.append((turn + 1, intensity, age))
            print(f"Turn {turn + 1}: intensity={intensity:.3f}, age={age}")
        else:
            print(f"Turn {turn + 1}: curiosity removed from cocktail")
            break

    print(f"\n--- RESULTS ---")
    print(f"Decay history:")
    for turn, intensity, age in decay_history:
        print(f"  Turn {turn}: intensity={intensity:.3f}, age={age}")

    # Check if decay is happening
    if len(decay_history) >= 2:
        initial_intensity = decay_history[0][1]
        final_intensity = decay_history[-1][1]

        if final_intensity < initial_intensity:
            decay_amount = initial_intensity - final_intensity
            decay_pct = (decay_amount / initial_intensity) * 100
            print(f"\n[PASS] Decay detected: {initial_intensity:.3f} -> {final_intensity:.3f} ({decay_pct:.1f}% reduction)")

            # Check if age increased
            initial_age = decay_history[0][2]
            final_age = decay_history[-1][2]
            if final_age > initial_age:
                print(f"[PASS] Age incremented: {initial_age} -> {final_age}")
            else:
                print(f"[FAIL] Age not incrementing: {initial_age} -> {final_age}")
                return False

            return True
        else:
            print(f"\n[FAIL] No decay: intensity stayed at {initial_intensity:.3f}")
            print(f"ISSUE: Decay formula may not be working")
            return False
    else:
        print(f"\n[FAIL] Emotion disappeared too quickly (after {len(decay_history)} turns)")
        return False


def test_3_emotional_cocktail():
    """
    Test 3: Verify multiple emotions can exist simultaneously.

    Expected behavior:
    - Cocktail should hold 3-5 emotions simultaneously
    - Each emotion should have independent intensity and age
    - Emotions should not overwrite each other
    """
    print("\n" + "="*70)
    print("TEST 3: EMOTIONAL COCKTAIL CAPACITY")
    print("="*70)

    # Initialize engines
    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Generate 5 different emotional triggers
    triggers = [
        "I'm so happy about this!",          # joy
        "I'm scared something bad will happen",  # fear
        "I'm curious how this works",        # curiosity
        "I'm so angry at this situation",    # anger
        "I feel sad about what happened",    # sadness
    ]

    for trigger in triggers:
        emotion_engine.update(state, trigger)
        print(f"After '{trigger[:30]}...': {list(state.emotional_cocktail.keys())}")

    print(f"\n--- RESULTS ---")
    print(f"Final cocktail: {state.emotional_cocktail}")
    print(f"Emotions present: {len(state.emotional_cocktail)}")

    # Check if multiple emotions coexist
    if len(state.emotional_cocktail) >= 3:
        print(f"\n[PASS] Cocktail holds {len(state.emotional_cocktail)} emotions simultaneously")

        # Verify each has independent state
        for emo, data in state.emotional_cocktail.items():
            print(f"  {emo}: intensity={data['intensity']:.2f}, age={data['age']}")

        return True
    else:
        print(f"\n[FAIL] Only {len(state.emotional_cocktail)} emotions in cocktail (expected 3+)")
        print(f"ISSUE: Emotions may be overwriting each other or being pruned too aggressively")
        return False


def test_4_memory_integration():
    """
    Test 4: Verify emotions affect memory importance scoring.

    This is a simplified test - full integration would require memory_engine.
    We'll check if emotion tags are being used.
    """
    print("\n" + "="*70)
    print("TEST 4: MEMORY-EMOTION INTEGRATION")
    print("="*70)

    # Initialize engines
    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up initial emotion
    state.emotional_cocktail = {"joy": {"intensity": 0.5, "age": 0}}

    # Simulate recalled memories with emotion tags
    state.last_recalled_memories = [
        {"fact": "Happy memory", "emotion_tags": ["joy"]},
        {"fact": "Neutral memory", "emotion_tags": []},
        {"fact": "Another joyful memory", "emotion_tags": ["joy"]},
    ]

    initial_intensity = state.emotional_cocktail["joy"]["intensity"]
    print(f"Initial joy intensity: {initial_intensity:.3f}")
    print(f"Recalled {len(state.last_recalled_memories)} memories (2 tagged with 'joy')")

    # Update should reinforce joy emotion from memories
    emotion_engine.update(state, "How are you?")

    final_intensity = state.emotional_cocktail["joy"]["intensity"]
    print(f"Final joy intensity: {final_intensity:.3f}")

    print(f"\n--- RESULTS ---")
    if final_intensity > initial_intensity:
        boost = final_intensity - initial_intensity
        print(f"[PASS] Joy intensity boosted by {boost:.3f} from tagged memories")
        print(f"Memory-emotion integration is working")
        return True
    else:
        print(f"[FAIL] No boost from emotion-tagged memories")
        print(f"ISSUE: Memory reinforcement may not be working (lines 172-176)")
        return False


def test_5_ultramap_protocols():
    """
    Test 5: Verify ULTRAMAP protocol components are active.

    Checks for:
    - Trigger detection (emotion generation from keywords)
    - Decay rates from ULTRAMAP CSV
    - Mutation/escalation
    - Body chemistry mapping
    - Social effects
    """
    print("\n" + "="*70)
    print("TEST 5: ULTRAMAP PROTOCOL VERIFICATION")
    print("="*70)

    # Initialize engines
    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)

    print("Checking ULTRAMAP components...")

    # 1. Check if triggers loaded
    print(f"\n1. Trigger Detection:")
    if emotion_engine.triggers:
        print(f"   [OK] Loaded {len(emotion_engine.triggers)} emotion triggers")
        print(f"   Sample: {list(emotion_engine.triggers.keys())[:5]}")
    else:
        print(f"   [WARNING] No triggers loaded from CSV")

    # 2. Check protocol rules
    print(f"\n2. ULTRAMAP Protocol Rules:")
    if protocol.protocol:
        print(f"   [OK] Loaded {len(protocol.protocol)} emotion rules")

        # Check for key fields
        sample_emotion = list(protocol.protocol.keys())[0] if protocol.protocol else None
        if sample_emotion:
            rules = protocol.protocol[sample_emotion]
            has_decay = "DecayRate" in rules
            has_mutation = "MutationTarget" in rules or "Escalation/Mutation Protocol" in rules
            has_neurochem = "BodyChem" in rules or "Neurochemical Release" in rules

            print(f"   Sample emotion '{sample_emotion}' has:")
            print(f"     DecayRate: {'[OK]' if has_decay else '[X]'}")
            print(f"     Mutation: {'[OK]' if has_mutation else '[X]'}")
            print(f"     Neurochemical: {'[OK]' if has_neurochem else '[X]'}")
    else:
        print(f"   [ERROR] No protocol rules loaded!")

    # 3. Test emotion detection
    print(f"\n3. Emotion Detection Test:")
    test_text = "I'm so angry and scared right now"
    detected = emotion_engine._detect_triggers(test_text)
    print(f"   Input: '{test_text}'")
    print(f"   Detected: {detected}")

    if detected:
        print(f"   [OK] Emotion detection working")
    else:
        print(f"   [WARNING] No emotions detected")

    # 4. Test full update cycle
    print(f"\n4. Full Update Cycle Test:")
    state = AgentState()
    emotion_engine.update(state, "I wonder what will happen next?")

    if state.emotional_cocktail:
        print(f"   [OK] Emotions generated: {list(state.emotional_cocktail.keys())}")

        # Check for ULTRAMAP protocol application
        for emo, data in state.emotional_cocktail.items():
            proto = protocol.get(emo) or {}
            decay_rate = proto.get("DecayRate", "N/A")
            print(f"   {emo}: DecayRate={decay_rate}, intensity={data['intensity']:.2f}")
    else:
        print(f"   [ERROR] No emotions in cocktail after update")

    print(f"\n--- RESULTS ---")

    # Overall assessment
    components_working = []
    if emotion_engine.triggers:
        components_working.append("Trigger Detection")
    if protocol.protocol:
        components_working.append("Protocol Rules")
    if detected:
        components_working.append("Emotion Recognition")
    if state.emotional_cocktail:
        components_working.append("Emotion Generation")

    if len(components_working) >= 3:
        print(f"[PASS] {len(components_working)}/4 ULTRAMAP components active")
        print(f"Working: {', '.join(components_working)}")
        return True
    else:
        print(f"[FAIL] Only {len(components_working)}/4 components working")
        return False


def run_all_tests():
    """Run all emotional architecture tests."""
    print("="*70)
    print("EMOTIONAL ARCHITECTURE DIAGNOSTIC")
    print("="*70)
    print("\nRunning comprehensive tests of Kay's ULTRAMAP emotional system...")

    results = {
        "Emotion Generation": test_1_emotion_generation(),
        "Emotion Decay": test_2_emotion_decay(),
        "Emotional Cocktail": test_3_emotional_cocktail(),
        "Memory Integration": test_4_memory_integration(),
        "ULTRAMAP Protocols": test_5_ultramap_protocols(),
    }

    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nOVERALL: {passed}/{total} tests passed")

    if passed < total:
        print("\n" + "="*70)
        print("ISSUES DETECTED")
        print("="*70)

        if not results["Emotion Generation"]:
            print("\n[X] Emotion Generation Issue:")
            print("   - Multiple emotions not being created from varied input")
            print("   - Check: emotion_engine.py lines 110-120 (trigger detection)")
            print("   - Possible cause: Triggers not loading or cocktail being overwritten")

        if not results["Emotion Decay"]:
            print("\n[X] Emotion Decay Issue:")
            print("   - Intensity not decreasing over time")
            print("   - Check: emotion_engine.py lines 136-147 (decay formula)")
            print("   - Possible cause: Decay value too small or momentum modifier too high")
            print("   - CRITICAL: No pruning of low-intensity emotions (missing threshold check)")

        if not results["Emotional Cocktail"]:
            print("\n[X] Cocktail Capacity Issue:")
            print("   - Only single emotion present instead of multiple")
            print("   - Check: emotion_engine.py line 108 (cocktail initialization)")
            print("   - Possible cause: Cocktail being reassigned instead of updated")

        if not results["Memory Integration"]:
            print("\n[X] Memory Integration Issue:")
            print("   - Emotions not being reinforced by recalled memories")
            print("   - Check: emotion_engine.py lines 172-176 (memory reinforcement)")

        if not results["ULTRAMAP Protocols"]:
            print("\n[X] ULTRAMAP Protocol Issue:")
            print("   - Core ULTRAMAP components may not be loading")
            print("   - Check: CSV file path and format")
            print("   - Check: protocol_engine.py initialization")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)

    if success:
        print("\n[OK] All tests passed! Emotional architecture is working correctly.")
    else:
        print("\n[WARNING] Issues detected. Review the diagnostic output above.")
        print("\nTo fix issues:")
        print("1. Review the ISSUES DETECTED section")
        print("2. Check the indicated file locations")
        print("3. Apply recommended fixes")
        print("4. Re-run this diagnostic to verify")

    sys.exit(0 if success else 1)
