"""
Test Self-Report Emotion System

Verifies that:
1. EmotionEngine no longer prescribes emotions
2. EmotionExtractor extracts self-reports from responses
3. Emotional state is preserved for next turn
4. System runs without prescriptive calculations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.emotion_extractor import EmotionExtractor
from engines.momentum_engine import MomentumEngine


def test_emotion_engine_no_prescription():
    """Test that EmotionEngine.update() no longer prescribes emotions"""
    print("\n" + "="*70)
    print("TEST 1: EmotionEngine No Longer Prescribes")
    print("="*70)

    proto = ProtocolEngine()
    momentum = MomentumEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    state = AgentState()

    # Start with empty cocktail
    state.emotional_cocktail = {}
    print(f"Initial cocktail: {state.emotional_cocktail}")

    # Call update with user input that would have triggered emotions in old system
    user_input = "I'm so angry and frustrated!"
    emotion.update(state, user_input)

    # Verify cocktail is still empty (no prescription)
    print(f"After emotion.update(): {state.emotional_cocktail}")

    if len(state.emotional_cocktail) == 0:
        print("[PASS] EmotionEngine did not prescribe emotions")
        return True
    else:
        print(f"[FAIL] EmotionEngine prescribed {len(state.emotional_cocktail)} emotions")
        return False


def test_emotion_extractor():
    """Test that EmotionExtractor extracts self-reports"""
    print("\n" + "="*70)
    print("TEST 2: EmotionExtractor Extracts Self-Reports")
    print("="*70)

    extractor = EmotionExtractor()
    state = AgentState()

    # Simulate Kay's response with emotional self-report
    kay_response = "I can feel the curiosity sitting at 0.68 right now, tracking it closely."

    # Extract emotions
    extracted = extractor.extract_emotions(kay_response)
    print(f"\nExtracted: {extracted['extracted_states']}")

    # Store in cocktail
    extractor.store_emotional_state(extracted, state.emotional_cocktail)
    print(f"Cocktail after extraction: {state.emotional_cocktail}")

    if 'curiosity' in state.emotional_cocktail or 'curio' in state.emotional_cocktail:
        print("[PASS] EmotionExtractor extracted self-reported emotion")
        return True
    else:
        print("[FAIL] EmotionExtractor did not extract emotion")
        return False


def test_emotion_persistence():
    """Test that extracted emotions persist for next turn"""
    print("\n" + "="*70)
    print("TEST 3: Emotional State Persists Across Turns")
    print("="*70)

    extractor = EmotionExtractor()
    state = AgentState()

    # Turn 1: Extract emotions from Kay's response
    response_1 = "I'm feeling curious about this question."
    extracted_1 = extractor.extract_emotions(response_1)
    extractor.store_emotional_state(extracted_1, state.emotional_cocktail)

    print(f"Turn 1 cocktail: {state.emotional_cocktail}")
    turn_1_cocktail = dict(state.emotional_cocktail)

    # Turn 2: Verify previous emotions are still available
    # (In real system, EmotionEngine.update() would be called but it's now a no-op)
    proto = ProtocolEngine()
    momentum = MomentumEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    emotion.update(state, "user input")  # This should not modify cocktail

    print(f"Turn 2 cocktail (after emotion.update no-op): {state.emotional_cocktail}")

    if state.emotional_cocktail == turn_1_cocktail:
        print("[PASS] Emotional state persists across turns (not overwritten)")
        return True
    else:
        print("[FAIL] Emotional state was modified")
        return False


def test_ultramap_queries():
    """Test that EmotionEngine still provides ULTRAMAP rule queries"""
    print("\n" + "="*70)
    print("TEST 4: ULTRAMAP Rule Queries Still Work")
    print("="*70)

    proto = ProtocolEngine()
    emotion = EmotionEngine(proto)

    # Test getting memory rules for an emotion
    memory_rules = emotion.get_memory_rules("curiosity")
    print(f"\nMemory rules for curiosity: {memory_rules}")

    # Test getting social rules
    social_rules = emotion.get_social_rules("curiosity")
    print(f"Social rules for curiosity: {social_rules}")

    # Test getting body rules
    body_rules = emotion.get_body_rules("curiosity")
    print(f"Body rules for curiosity: {body_rules}")

    if (memory_rules and social_rules and body_rules):
        print("[PASS] ULTRAMAP rule queries work")
        return True
    else:
        print("[FAIL] ULTRAMAP rule queries failed")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SELF-REPORT EMOTION SYSTEM TEST SUITE")
    print("="*70)

    results = []

    results.append(("No Prescription", test_emotion_engine_no_prescription()))
    results.append(("Extraction Works", test_emotion_extractor()))
    results.append(("State Persists", test_emotion_persistence()))
    results.append(("ULTRAMAP Queries", test_ultramap_queries()))

    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED - Self-report system working correctly")
        return True
    else:
        print(f"\n[FAILURE] {total - passed} tests failed - Review output above")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
