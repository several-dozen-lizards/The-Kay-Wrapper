"""
Test Relevance-Weighted Memory Boost

Verifies that memory boost is now weighted by relevance instead of equal for all memories.

Expected behavior:
- Emotions from highly relevant memories get strong boost
- Emotions from barely relevant memories get weak boost
- Total boost is proportional to relevance distribution
- Decay actually works (emotions decrease when not reinforced)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from agent_state import AgentState
from engines.emotion_engine import EmotionEngine
from protocol_engine import ProtocolEngine


def test_relevance_weighting():
    """Test 1: Verify boost is weighted by relevance, not equal for all."""
    print("="*70)
    print("TEST 1: RELEVANCE-WEIGHTED BOOST")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up initial emotion
    state.emotional_cocktail = {"curiosity": {"intensity": 0.5, "age": 0}}

    # Simulate memory recall with varying relevance scores
    state.last_recalled_memories = [
        # High relevance memories (should boost strongly)
        {"fact": "Memory system works", "emotion_tags": ["curiosity"], "relevance_score": 0.9},
        {"fact": "How does it work?", "emotion_tags": ["curiosity"], "relevance_score": 0.85},

        # Medium relevance memories (should boost moderately)
        {"fact": "Wrapper handles exceptions", "emotion_tags": ["curiosity"], "relevance_score": 0.5},
        {"fact": "Architecture design", "emotion_tags": ["curiosity"], "relevance_score": 0.4},

        # Low relevance memories (should boost weakly or not at all)
        {"fact": "Re has green eyes", "emotion_tags": ["curiosity"], "relevance_score": 0.1},
        {"fact": "Chrome is a dog", "emotion_tags": ["curiosity"], "relevance_score": 0.08},

        # Below threshold (should not boost)
        {"fact": "Random fact", "emotion_tags": ["curiosity"], "relevance_score": 0.05},
    ]

    initial_intensity = state.emotional_cocktail["curiosity"]["intensity"]
    print(f"\nInitial curiosity intensity: {initial_intensity:.3f}")
    print(f"Total memories: {len(state.last_recalled_memories)}")
    print(f"  High relevance (>0.7): 2 memories")
    print(f"  Medium relevance (0.3-0.7): 2 memories")
    print(f"  Low relevance (0.15-0.3): 0 memories")
    print(f"  Very low (<0.15): 3 memories (should be ignored)")

    # Update should boost based on relevance
    emotion_engine.update(state, "Tell me about the system")

    final_intensity = state.emotional_cocktail["curiosity"]["intensity"]
    total_boost = final_intensity - initial_intensity

    print(f"\n--- RESULTS ---")
    print(f"Initial intensity: {initial_intensity:.3f}")
    print(f"Final intensity: {final_intensity:.3f}")
    print(f"Net change: {total_boost:.3f}")

    # Calculate expected boost (weighted by relevance)
    expected_boost = (0.05 * 0.9) + (0.05 * 0.85) + (0.05 * 0.5) + (0.05 * 0.4)
    decay_amount = 0.05  # Base decay for curiosity
    expected_net = expected_boost - decay_amount
    # Low relevance memories below threshold (0.15) should be ignored

    print(f"\nExpected weighted boost: ~{expected_boost:.3f}")
    print(f"  0.9 x 0.05 = {0.9*0.05:.3f}")
    print(f"  0.85 x 0.05 = {0.85*0.05:.3f}")
    print(f"  0.5 x 0.05 = {0.5*0.05:.3f}")
    print(f"  0.4 x 0.05 = {0.4*0.05:.3f}")
    print(f"  (0.1, 0.08, 0.05 ignored - below threshold)")
    print(f"Expected decay: -{decay_amount:.3f}")
    print(f"Expected net change: {expected_net:.3f} (boost - decay)")

    # Test passes if net change is close to expected (boost - decay)
    if abs(total_boost - expected_net) < 0.01:
        print(f"\n[PASS] Boost matches expected weighted amount")
        return True
    else:
        print(f"\n[FAIL] Net change doesn't match expected (got {total_boost:.3f}, expected {expected_net:.3f})")
        return False


def test_decay_now_works():
    """Test 2: Verify decay actually works with relevance-weighted boost."""
    print("\n" + "="*70)
    print("TEST 2: DECAY WORKS WITH RELEVANCE WEIGHTING")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up initial emotion
    state.emotional_cocktail = {"curiosity": {"intensity": 0.7, "age": 0}}

    # Simulate LOW relevance memories (should not prevent decay)
    state.last_recalled_memories = [
        {"fact": "Unrelated fact 1", "emotion_tags": ["curiosity"], "relevance_score": 0.1},
        {"fact": "Unrelated fact 2", "emotion_tags": ["curiosity"], "relevance_score": 0.08},
        {"fact": "Unrelated fact 3", "emotion_tags": ["curiosity"], "relevance_score": 0.05},
    ]

    print(f"\nSetup:")
    print(f"  Initial curiosity: 0.70")
    print(f"  Memories: 3 with LOW relevance (all <0.15 threshold)")
    print(f"  Expected: Decay should work (no boost from irrelevant memories)")

    # Track decay over 3 turns
    history = []

    for turn in range(3):
        initial = state.emotional_cocktail.get("curiosity", {}).get("intensity", 0)

        emotion_engine.update(state, "Okay, I see")

        final = state.emotional_cocktail.get("curiosity", {}).get("intensity", 0)
        age = state.emotional_cocktail.get("curiosity", {}).get("age", 0)

        history.append((turn + 1, initial, final, age))
        print(f"\nTurn {turn + 1}:")
        print(f"  Before: {initial:.3f}")
        print(f"  After: {final:.3f}")
        print(f"  Change: {final - initial:.3f}")
        print(f"  Age: {age}")

    print(f"\n--- RESULTS ---")
    print(f"Decay history:")
    for turn, before, after, age in history:
        change = after - before
        print(f"  Turn {turn}: {before:.3f} -> {after:.3f} (change: {change:+.3f}, age: {age})")

    # Check if decay is happening
    first_intensity = history[0][1]
    last_intensity = history[-1][2]

    if last_intensity < first_intensity:
        decay_amount = first_intensity - last_intensity
        print(f"\n[PASS] Decay detected: {first_intensity:.3f} -> {last_intensity:.3f} (reduced by {decay_amount:.3f})")
        print(f"[PASS] Irrelevant memories did NOT prevent decay!")
        return True
    else:
        print(f"\n[FAIL] No decay: intensity stayed at {first_intensity:.3f}")
        print(f"[FAIL] Boost still overwhelming decay")
        return False


def test_high_relevance_boosts():
    """Test 3: Verify high relevance memories DO boost appropriately."""
    print("\n" + "="*70)
    print("TEST 3: HIGH RELEVANCE MEMORIES BOOST")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up initial emotion
    state.emotional_cocktail = {"curiosity": {"intensity": 0.5, "age": 0}}

    # Simulate HIGH relevance memories (should boost)
    state.last_recalled_memories = [
        {"fact": "Very relevant 1", "emotion_tags": ["curiosity"], "relevance_score": 0.95},
        {"fact": "Very relevant 2", "emotion_tags": ["curiosity"], "relevance_score": 0.90},
        {"fact": "Very relevant 3", "emotion_tags": ["curiosity"], "relevance_score": 0.85},
    ]

    initial_intensity = state.emotional_cocktail["curiosity"]["intensity"]
    print(f"\nSetup:")
    print(f"  Initial curiosity: {initial_intensity:.3f}")
    print(f"  Memories: 3 with HIGH relevance (all >0.85)")
    print(f"  Expected: Strong boost from relevant memories")

    emotion_engine.update(state, "Tell me more")

    final_intensity = state.emotional_cocktail.get("curiosity", {}).get("intensity", 0)
    boost = final_intensity - initial_intensity

    print(f"\n--- RESULTS ---")
    print(f"Initial: {initial_intensity:.3f}")
    print(f"Final: {final_intensity:.3f}")
    print(f"Net change: +{boost:.3f}")

    # Expected boost: (0.95 + 0.90 + 0.85) * 0.05 = 0.135
    expected_boost = (0.95 + 0.90 + 0.85) * 0.05
    decay_amount = 0.05  # Base decay for curiosity
    expected_net = expected_boost - decay_amount

    print(f"\nExpected boost: ~{expected_boost:.3f}")
    print(f"  (0.95 + 0.90 + 0.85) x 0.05 = {expected_boost:.3f}")
    print(f"Expected decay: -{decay_amount:.3f}")
    print(f"Expected net change: {expected_net:.3f} (boost - decay)")

    if abs(boost - expected_net) < 0.01:
        print(f"\n[PASS] High relevance memories boosted appropriately")
        return True
    else:
        print(f"\n[FAIL] Net change mismatch (got {boost:.3f}, expected {expected_net:.3f})")
        return False


def run_all_tests():
    """Run all relevance-weighted boost tests."""
    print("="*70)
    print("RELEVANCE-WEIGHTED BOOST TEST SUITE")
    print("="*70)
    print("\nTesting that memory boost is weighted by relevance...\n")

    results = {
        "Relevance Weighting": test_relevance_weighting(),
        "Decay Works": test_decay_now_works(),
        "High Relevance Boosts": test_high_relevance_boosts(),
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
        print("\n[SUCCESS] All tests passed! Relevance-weighted boost is working.")
        print("\nKey improvements:")
        print("  - Boost weighted by relevance (not equal for all)")
        print("  - Irrelevant memories ignored (below threshold)")
        print("  - Decay actually works (emotions decrease)")
        print("  - High relevance memories boost appropriately")
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
        print("2. Now run Kay with: python main.py")
        print("3. Watch for new logging:")
        print("   [MEMORY RETRIEVAL] Top 10 most relevant memories")
        print("   [EMOTION ENGINE] Used XX/310 memories (relevance >= 0.15)")
        print("   [EMOTION ENGINE]   - emotion: +0.XXX boost -> intensity=X.XX")
        print("4. Verify decay works in live system")
    else:
        print("\n1. Fix failing tests first")
        print("2. Check relevance_score is being stored")
        print("3. Check boost calculation formula")

    print("="*70)

    sys.exit(0 if success else 1)
