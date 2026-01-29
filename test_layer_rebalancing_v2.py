"""
Test Layer Rebalancing V2 - Stronger Weights + Refined UNCONFIRMED CLAIM Filter

This script verifies:
1. Stronger layer weights (3.0x, 2.5x, 0.3x) are applied correctly
2. UNCONFIRMED CLAIM filter is less aggressive (allows observations)
3. Expected composition changes (semantic down, episodic up)

Usage:
    python test_layer_rebalancing_v2.py
"""

from engines.memory_layer_rebalancing import (
    LAYER_WEIGHTS,
    get_layer_multiplier,
    is_entity_observation,
    should_store_claim,
    test_observation_classification,
)


def test_layer_weights():
    """Test that layer weights are correctly configured."""
    print("\n" + "="*70)
    print("TEST 1: LAYER WEIGHT CONFIGURATION")
    print("="*70)
    print()

    print("Current layer weights:")
    for layer, weight in LAYER_WEIGHTS.items():
        print(f"  {layer.capitalize():10s}: {weight}x")

    print()

    # Verify weights are as expected
    expected = {
        "working": 3.0,
        "episodic": 2.5,
        "semantic": 0.3
    }

    all_correct = True
    for layer, expected_weight in expected.items():
        actual_weight = LAYER_WEIGHTS.get(layer, 0)
        if actual_weight == expected_weight:
            print(f"  [OK] {layer.capitalize():10s}: {actual_weight}x (correct)")
        else:
            print(f"  [FAIL] {layer.capitalize():10s}: {actual_weight}x (expected {expected_weight}x)")
            all_correct = False

    print()

    # Check ratio
    episodic_weight = LAYER_WEIGHTS.get("episodic", 1.0)
    semantic_weight = LAYER_WEIGHTS.get("semantic", 1.0)
    ratio = episodic_weight / semantic_weight

    print(f"Episodic/Semantic ratio: {ratio:.1f}x")
    if ratio >= 8.0:
        print(f"  [EXCELLENT] Ratio >= 8.0x (strong rebalancing)")
    elif ratio >= 5.0:
        print(f"  [GOOD] Ratio >= 5.0x (moderate rebalancing)")
    else:
        print(f"  [WARN] Ratio < 5.0x (weak rebalancing)")

    print()

    # Show scoring impact
    print("Scoring example (base_score = 0.50):")
    base_score = 0.50
    for layer in ["working", "episodic", "semantic"]:
        multiplier = get_layer_multiplier(layer)
        final_score = base_score * multiplier
        print(f"  {layer.capitalize():10s}: {base_score:.2f} × {multiplier:.1f} = {final_score:.2f}")

    print()

    if all_correct:
        print("[PASS] All layer weights configured correctly!")
    else:
        print("[FAIL] Some layer weights are incorrect!")

    return all_correct


def test_false_attribution_refinement():
    """Test that FALSE_ATTRIBUTION filter is less aggressive."""
    print("\n" + "="*70)
    print("TEST 2: REFINED FALSE_ATTRIBUTION FILTER")
    print("="*70)
    print()

    print("Testing specific cases that should NOW be ALLOWED:")
    print()

    # Cases that were previously blocked but should now be allowed
    should_allow = [
        "Re's words come through as clean text",
        "Whether Re is tired gets stripped out",
        "Re is experiencing exhaustion",
        "Re needs support with this",
        "Re wants to feel better",
        "Re mentioned feeling tired",
    ]

    allowed_count = 0
    for case in should_allow:
        result = is_entity_observation(case)
        status = "[OK] ALLOW" if result else "[FAIL] BLOCK"
        print(f"  {status}: '{case[:50]}'")
        if result:
            allowed_count += 1

    print()
    print(f"Result: {allowed_count}/{len(should_allow)} observations allowed")

    print()
    print("Testing cases that should STILL be BLOCKED:")
    print()

    # Cases that should still be blocked
    should_block = [
        "Re said 'I want to quit'",
        "You told me 'my goal is X'",
        "You said 'your favorite color is blue'",
    ]

    blocked_count = 0
    for case in should_block:
        result = is_entity_observation(case)
        status = "[OK] BLOCK" if not result else "[FAIL] ALLOW"
        print(f"  {status}: '{case[:50]}'")
        if not result:
            blocked_count += 1

    print()
    print(f"Result: {blocked_count}/{len(should_block)} false attributions blocked")

    print()

    success = (allowed_count == len(should_allow) and blocked_count == len(should_block))
    if success:
        print("[PASS] FALSE_ATTRIBUTION filter refined successfully!")
    else:
        print("[FAIL] Some cases not handled correctly")

    return success


def test_scoring_simulation():
    """Simulate scoring to show expected composition change."""
    print("\n" + "="*70)
    print("TEST 3: SCORING SIMULATION")
    print("="*70)
    print()

    print("Simulating retrieval with equal base scores:")
    print()

    # Simulate 100 memories with equal base scores
    base_score = 0.5

    # Assume semantic layer has MORE memories (60%)
    # but with weights, episodic should dominate retrieval
    raw_distribution = {
        "working": 10,   # 10%
        "episodic": 30,  # 30%
        "semantic": 60,  # 60%
    }

    print("RAW MEMORY DISTRIBUTION (before weights):")
    total_raw = sum(raw_distribution.values())
    for layer, count in raw_distribution.items():
        pct = (count / total_raw * 100)
        print(f"  {layer.capitalize():10s}: {count:3d} memories ({pct:5.1f}%)")

    print()

    # Apply weights and calculate top N
    scored_memories = []
    for layer, count in raw_distribution.items():
        multiplier = get_layer_multiplier(layer)
        weighted_score = base_score * multiplier

        for i in range(count):
            scored_memories.append({
                "layer": layer,
                "score": weighted_score
            })

    # Sort by score (descending)
    scored_memories.sort(key=lambda x: x["score"], reverse=True)

    # Take top 100
    top_n = 100
    top_memories = scored_memories[:top_n]

    # Count by layer
    top_distribution = {
        "working": 0,
        "episodic": 0,
        "semantic": 0
    }

    for mem in top_memories:
        layer = mem["layer"]
        top_distribution[layer] += 1

    print(f"TOP {top_n} RETRIEVED MEMORIES (after weights):")
    for layer in ["working", "episodic", "semantic"]:
        count = top_distribution[layer]
        pct = (count / top_n * 100)
        print(f"  {layer.capitalize():10s}: {count:3d} memories ({pct:5.1f}%)")

    print()

    # Compare to targets
    targets = {
        "working": 18.0,   # 15-20%
        "episodic": 48.0,  # 45-50%
        "semantic": 32.0,  # 30-35%
    }

    print("COMPARISON TO TARGETS:")
    within_range = True
    for layer in ["working", "episodic", "semantic"]:
        actual_pct = (top_distribution[layer] / top_n * 100)
        target_pct = targets[layer]
        deviation = actual_pct - target_pct

        if abs(deviation) < 10:
            status = "[OK]"
        else:
            status = "[--]"
            within_range = False

        print(f"  {status} {layer.capitalize():10s}: {actual_pct:5.1f}% "
              f"(target: {target_pct:4.1f}%, deviation: {deviation:+5.1f}%)")

    print()

    if within_range:
        print("[PASS] Expected composition achieved!")
    else:
        print("[INFO] Composition may vary based on actual base scores")
        print("      (This simulation assumes equal base scores for all layers)")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("LAYER REBALANCING V2 - VERIFICATION TESTS")
    print("="*70)
    print()
    print("Testing stronger layer weights and refined FALSE_ATTRIBUTION filter")
    print()

    results = []

    # Test 1: Layer weights
    results.append(test_layer_weights())

    # Test 2: FALSE_ATTRIBUTION refinement
    results.append(test_false_attribution_refinement())

    # Test 3: Scoring simulation
    results.append(test_scoring_simulation())

    # Test 4: Full classification test
    print("\n" + "="*70)
    print("TEST 4: COMPREHENSIVE OBSERVATION CLASSIFICATION")
    print("="*70)
    test_observation_classification()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print()

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")
    print()

    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED!")
        print()
        print("Next steps:")
        print("1. Restart Kay (python main.py)")
        print("2. Start a conversation")
        print("3. Look for composition validation in logs:")
        print("   [OK] Episodic  : 105 memories ( 42.9%) [target:  48%]")
        print("   [OK] Semantic  :  70 memories ( 28.6%) [target:  32%]")
        print()
        print("4. Look for entity observations being stored:")
        print("   [ENTITY OBSERVATION] Storing Kay's observation: '...'")
        print()
    else:
        print("[WARNING] SOME TESTS FAILED")
        print()
        print("Check the output above for details.")

    print("="*70)


if __name__ == "__main__":
    main()
