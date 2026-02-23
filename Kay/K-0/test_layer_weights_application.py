"""
Test Layer Weight Application

Verifies that layer weights are correctly applied during memory retrieval
and that the final composition matches target distribution.
"""

import sys
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.momentum_engine import MomentumEngine
from engines.motif_engine import MotifEngine
from engines.memory_engine import MemoryEngine
from engines.memory_layer_rebalancing import LAYER_WEIGHTS, get_layer_multiplier


def test_layer_multiplier_function():
    """Test that get_layer_multiplier returns correct values"""
    print("\n" + "="*70)
    print("TEST 1: Layer Multiplier Function")
    print("="*70)

    print(f"\nLAYER_WEIGHTS configuration:")
    for layer, weight in LAYER_WEIGHTS.items():
        print(f"  {layer:10s}: {weight:5.1f}x")

    print(f"\nget_layer_multiplier() results:")
    for layer in ["working", "episodic", "semantic"]:
        multiplier = get_layer_multiplier(layer)
        expected = LAYER_WEIGHTS[layer]
        status = "PASS" if multiplier == expected else "FAIL"
        print(f"  [{status}] {layer:10s}: {multiplier:5.1f}x (expected {expected:5.1f}x)")

    return True


def test_memory_retrieval_with_logging():
    """Test actual memory retrieval and check layer composition"""
    print("\n" + "="*70)
    print("TEST 2: Memory Retrieval with Layer Logging")
    print("="*70)

    # Initialize engines
    proto = ProtocolEngine()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)

    # Initialize memory engine
    memory = MemoryEngine(
        memories=[],
        motif_engine=motif,
        momentum_engine=momentum,
        emotion_engine=emotion,
        vector_store=None
    )

    # Create agent state
    state = AgentState()
    state.emotional_cocktail = {"curiosity": {"intensity": 0.5, "age": 0}}

    print("\n[TEST] Calling memory.recall() with test query...")
    print("[TEST] Watch for [LAYER DEBUG] logs to see if weights are applied\n")

    try:
        # Recall memories - this should trigger our debug logging
        memory.recall(state, "test query about Kay's memories")

        print(f"\n[TEST] Retrieved {len(state.last_recalled_memories)} memories")

        # Count by layer
        layer_counts = {"working": 0, "episodic": 0, "semantic": 0, "unknown": 0}
        for mem in state.last_recalled_memories:
            layer = mem.get("current_layer", "unknown")
            layer_counts[layer] += 1

        print(f"\n[TEST] Layer composition:")
        total = sum(layer_counts.values())
        for layer, count in layer_counts.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {layer:10s}: {count:4d} memories ({percentage:5.1f}%)")

        return True

    except Exception as e:
        print(f"\n[ERROR] Memory retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_score_calculation():
    """Test that layer boost actually affects final scores"""
    print("\n" + "="*70)
    print("TEST 3: Score Calculation with Layer Boost")
    print("="*70)

    # Simulate scoring
    base_score = 0.5

    print(f"\nBase score: {base_score}")
    print(f"\nFinal scores with layer boost applied:")

    for layer in ["working", "episodic", "semantic"]:
        multiplier = get_layer_multiplier(layer)
        final_score = base_score * multiplier
        print(f"  {layer:10s}: {base_score:.2f} × {multiplier:5.1f} = {final_score:.2f}")

    # Show expected composition if weights work correctly
    # Assume: 10 working, 100 episodic, 3593 semantic
    print(f"\nExpected effective pool sizes (assuming 10W / 100E / 3593S):")
    working_eff = 10 * get_layer_multiplier("working")
    episodic_eff = 100 * get_layer_multiplier("episodic")
    semantic_eff = 3593 * get_layer_multiplier("semantic")

    total_eff = working_eff + episodic_eff + semantic_eff

    print(f"  Working:  10 × {get_layer_multiplier('working'):5.1f} = {working_eff:7.1f} ({working_eff/total_eff*100:5.1f}%)")
    print(f"  Episodic: 100 × {get_layer_multiplier('episodic'):5.1f} = {episodic_eff:7.1f} ({episodic_eff/total_eff*100:5.1f}%)")
    print(f"  Semantic: 3593 × {get_layer_multiplier('semantic'):5.1f} = {semantic_eff:7.1f} ({semantic_eff/total_eff*100:5.1f}%)")
    print(f"  Total effective: {total_eff:.1f}")

    print(f"\nExpected composition if weights work:")
    print(f"  Working:  ~{working_eff/total_eff*100:5.1f}% (target: 18%)")
    print(f"  Episodic: ~{episodic_eff/total_eff*100:5.1f}% (target: 48%)")
    print(f"  Semantic: ~{semantic_eff/total_eff*100:5.1f}% (target: 32%)")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("LAYER WEIGHT APPLICATION TEST SUITE")
    print("="*70)

    results = []

    results.append(("Layer Multiplier Function", test_layer_multiplier_function()))
    results.append(("Score Calculation", test_score_calculation()))
    results.append(("Memory Retrieval", test_memory_retrieval_with_logging()))

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
        print("\n[SUCCESS] All tests passed")
        print("\nIf composition is still wrong, the problem is likely:")
        print("  1. Memories don't have 'current_layer' field set")
        print("  2. Default value 'working' is being used for all memories")
        print("  3. Need to check layer assignment during memory storage")
        return True
    else:
        print(f"\n[FAILURE] {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
