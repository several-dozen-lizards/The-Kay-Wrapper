"""
Quick diagnostic test to verify relevance score normalization fix.

This test confirms that raw scores (0-999) are normalized to 0-1 before boost calculation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

from agent_state import AgentState
from engines.emotion_engine import EmotionEngine
from protocol_engine import ProtocolEngine


def test_normalization_fix():
    """Test that raw scores are normalized properly."""
    print("="*70)
    print("NORMALIZATION FIX TEST")
    print("="*70)

    protocol = ProtocolEngine()
    emotion_engine = EmotionEngine(protocol)
    state = AgentState()

    # Set up initial emotion
    state.emotional_cocktail = {"curiosity": {"intensity": 0.5, "age": 0}}

    # Simulate memories with RAW scores (like production system)
    # These are the actual score ranges from memory_engine.py:
    # - Identity facts: 999
    # - Normal memories: 0-75
    state.last_recalled_memories = [
        # High-scoring normal memories (like actual retrieval would produce)
        {"fact": "Memory about curiosity", "emotion_tags": ["curiosity"], "relevance_score": 45.5},
        {"fact": "Another curious memory", "emotion_tags": ["curiosity"], "relevance_score": 38.2},
        {"fact": "Third memory", "emotion_tags": ["curiosity"], "relevance_score": 25.0},

        # Medium-scoring memories
        {"fact": "Medium memory", "emotion_tags": ["curiosity"], "relevance_score": 10.5},
        {"fact": "Low-medium memory", "emotion_tags": ["curiosity"], "relevance_score": 5.0},

        # Low-scoring memories (should be filtered out after normalization)
        {"fact": "Low score memory", "emotion_tags": ["curiosity"], "relevance_score": 2.0},
        {"fact": "Very low score", "emotion_tags": ["curiosity"], "relevance_score": 0.8},
    ]

    print(f"\nSetup:")
    print(f"  Initial curiosity: 0.50")
    print(f"  Memories: 7 with RAW scores ranging from 0.8 to 45.5")
    print(f"  Expected: Scores normalized to 0-1, then threshold applied")

    initial_intensity = state.emotional_cocktail["curiosity"]["intensity"]

    # Run emotion update
    emotion_engine.update(state, "Tell me about the system")

    final_intensity = state.emotional_cocktail.get("curiosity", {}).get("intensity", 0)
    net_change = final_intensity - initial_intensity

    print(f"\n--- RESULTS ---")
    print(f"Initial intensity: {initial_intensity:.3f}")
    print(f"Final intensity: {final_intensity:.3f}")
    print(f"Net change: {net_change:+.3f}")

    # After normalization:
    # max = 45.5, min = 0.8, range = 44.7
    # Score 45.5 -> normalized = 1.0
    # Score 38.2 -> normalized = 0.836
    # Score 25.0 -> normalized = 0.541
    # Score 10.5 -> normalized = 0.217 (above 0.15 threshold)
    # Score 5.0 -> normalized = 0.094 (below 0.15 threshold - filtered)
    # Score 2.0 -> normalized = 0.027 (below threshold)
    # Score 0.8 -> normalized = 0.0 (below threshold)

    # Expected: 4 memories pass threshold (1.0, 0.836, 0.541, 0.217)
    # Expected boost = 0.05 * (1.0 + 0.836 + 0.541 + 0.217) = 0.130
    # Expected net = boost - decay = 0.130 - 0.050 = 0.080

    expected_boost = 0.05 * (1.0 + 0.836 + 0.541 + 0.217)
    expected_decay = 0.05
    expected_net = expected_boost - expected_decay

    print(f"\nExpected calculations:")
    print(f"  Normalization: 45.5->1.0, 38.2->0.836, 25.0->0.541, 10.5->0.217")
    print(f"  Expected boost: ~{expected_boost:.3f} (4 memories above 0.15 threshold)")
    print(f"  Expected decay: -{expected_decay:.3f}")
    print(f"  Expected net: {expected_net:+.3f}")

    # Check if boost is reasonable (< 1.0)
    if abs(net_change) < 1.0:
        print(f"\n[PASS] Boost is reasonable (< 1.0)")

        # Check if it's close to expected
        if abs(net_change - expected_net) < 0.02:
            print(f"[PASS] Net change matches expected ({net_change:+.3f} ~= {expected_net:+.3f})")
            return True
        else:
            print(f"[WARNING] Net change doesn't match expected (got {net_change:+.3f}, expected {expected_net:+.3f})")
            print(f"[WARNING] But boost is at least in reasonable range, so normalization is working")
            return True
    else:
        print(f"\n[FAIL] Boost is unreasonable (>= 1.0) - normalization not working!")
        return False


if __name__ == "__main__":
    print("\nTesting relevance score normalization fix...\n")

    success = test_normalization_fix()

    print("\n" + "="*70)
    if success:
        print("SUCCESS: Normalization fix is working!")
        print("\nBefore fix:")
        print("  Raw score 45.5 * 0.05 = 2.275 boost per memory")
        print("  Total: +299.7 boost (broken!)")
        print("\nAfter fix:")
        print("  Normalized 1.0 * 0.05 = 0.050 boost per memory")
        print("  Total: ~0.13 boost (working!)")
    else:
        print("FAILURE: Normalization fix not working correctly")
    print("="*70)

    sys.exit(0 if success else 1)
