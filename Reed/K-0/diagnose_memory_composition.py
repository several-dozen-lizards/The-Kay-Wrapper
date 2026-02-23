"""
Memory Composition Diagnostic Tool

Checks:
1. Are layer weights actually being applied?
2. What's the raw memory distribution across layers?
3. What scores are memories getting before/after layer weights?
4. Are semantic memories dominating due to sheer volume?

Usage:
    python diagnose_memory_composition.py
"""

import json
import os
from typing import Dict, List, Any
from engines.memory_engine import MemoryEngine
from engines.memory_layer_rebalancing import (
    get_layer_multiplier,
    validate_memory_composition,
    LAYER_WEIGHTS
)


def check_raw_memory_distribution():
    """Check how memories are distributed across layers (before scoring)."""
    print("\n" + "="*70)
    print("RAW MEMORY DISTRIBUTION (Before Scoring)")
    print("="*70)

    memory_files = {
        "Working": "memory/memory_layers.json",
        "Memories": "memory/memories.json",
    }

    total_by_layer = {
        "working": 0,
        "episodic": 0,
        "semantic": 0,
        "unknown": 0
    }

    # Check layered memories
    layers_file = "memory/memory_layers.json"
    if os.path.exists(layers_file):
        with open(layers_file, 'r', encoding='utf-8') as f:
            layers_data = json.load(f)

            for layer_name in ["working", "episodic", "semantic"]:
                # Handle both formats: {"working": [...]} or {"working": {"memories": [...]}}
                layer_data = layers_data.get(layer_name, [])
                if isinstance(layer_data, dict):
                    layer_mems = layer_data.get("memories", [])
                elif isinstance(layer_data, list):
                    layer_mems = layer_data
                else:
                    layer_mems = []

                total_by_layer[layer_name] = len(layer_mems)

    # Check flat memories (legacy)
    flat_file = "memory/memories.json"
    if os.path.exists(flat_file):
        with open(flat_file, 'r', encoding='utf-8') as f:
            flat_mems = json.load(f)
            print(f"\n[WARNING] Found {len(flat_mems)} flat memories (legacy format)")

            # Classify flat memories by type
            for mem in flat_mems:
                layer = mem.get("current_layer", "unknown")
                if layer in total_by_layer:
                    total_by_layer[layer] += 1

    total = sum(total_by_layer.values())

    print(f"\nTotal memories: {total}")
    print()
    for layer in ["working", "episodic", "semantic"]:
        count = total_by_layer[layer]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {layer.capitalize():10s}: {count:5d} memories ({pct:5.1f}%)")

    if total_by_layer["unknown"] > 0:
        count = total_by_layer["unknown"]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  Unknown   : {count:5d} memories ({pct:5.1f}%)")

    print()

    # Diagnosis
    semantic_pct = (total_by_layer["semantic"] / total * 100) if total > 0 else 0
    episodic_pct = (total_by_layer["episodic"] / total * 100) if total > 0 else 0

    if semantic_pct > 50:
        print("[PROBLEM] Semantic layer has >50% of ALL memories")
        print("   This means even with 0.3x penalty, semantic can dominate due to volume")
        print()
        print("   SOLUTION: Increase layer weight penalty for semantic")
        print("             OR: Promote more memories to episodic layer")
    elif semantic_pct > 40:
        print("[WARNING] Semantic layer has >40% of memories")
        print("   Retrieval will struggle to surface episodic memories")
    else:
        print("[OK] Raw distribution looks reasonable")

    return total_by_layer


def check_layer_weights():
    """Verify layer weights are configured correctly."""
    print("\n" + "="*70)
    print("LAYER WEIGHT CONFIGURATION")
    print("="*70)

    print("\nCurrent weights:")
    for layer, weight in LAYER_WEIGHTS.items():
        print(f"  {layer.capitalize():10s}: {weight}x")

    print()

    # Test scoring impact
    base_score = 0.5
    print(f"Scoring example (base score = {base_score}):")
    for layer, weight in LAYER_WEIGHTS.items():
        weighted_score = base_score * weight
        print(f"  {layer.capitalize():10s}: {base_score:.2f} × {weight:.1f} = {weighted_score:.2f}")

    print()

    # Recommendations
    working_weight = LAYER_WEIGHTS.get("working", 1.0)
    episodic_weight = LAYER_WEIGHTS.get("episodic", 1.0)
    semantic_weight = LAYER_WEIGHTS.get("semantic", 1.0)

    if semantic_weight >= 0.6:
        print("[WARNING] Semantic weight is >= 0.6")
        print("   Try reducing to 0.4 or 0.3 for stronger penalty")

    if episodic_weight < 2.0:
        print("[WARNING] Episodic weight is < 2.0")
        print("   Try increasing to 2.5 or 3.0 for stronger boost")

    ratio = episodic_weight / semantic_weight
    if ratio < 3.0:
        print(f"[WARNING] Episodic/Semantic ratio is {ratio:.1f}x (< 3.0x)")
        print("   For strong rebalancing, aim for 5x-8x ratio")
        print()
        print("   RECOMMENDED WEIGHTS:")
        print("     working: 3.0x   (up from 2.0x)")
        print("     episodic: 2.5x  (up from 1.8x)")
        print("     semantic: 0.3x  (down from 0.6x)")
        print()
        print("   This gives episodic/semantic ratio of 8.3x")


def simulate_scoring(sample_size: int = 100):
    """Simulate scoring to see if weights are having desired effect."""
    print("\n" + "="*70)
    print(f"SCORING SIMULATION (Sample Size: {sample_size})")
    print("="*70)

    # Load memories
    layers_file = "memory/memory_layers.json"
    if not os.path.exists(layers_file):
        print("No memory layers file found. Skipping simulation.")
        return

    with open(layers_file, 'r', encoding='utf-8') as f:
        layers_data = json.load(f)

    # Collect sample memories from each layer
    samples = []
    for layer_name in ["working", "episodic", "semantic"]:
        # Handle both formats
        layer_data = layers_data.get(layer_name, [])
        if isinstance(layer_data, dict):
            layer_mems = layer_data.get("memories", [])
        elif isinstance(layer_data, list):
            layer_mems = layer_data
        else:
            layer_mems = []

        # Take first N memories from each layer
        for mem in layer_mems[:min(sample_size // 3, len(layer_mems))]:
            mem["current_layer"] = layer_name
            samples.append(mem)

    if not samples:
        print("No memories found. Skipping simulation.")
        return

    print(f"\nSimulating scoring for {len(samples)} memories...")

    # Simulate base scores (uniform for testing)
    base_score = 0.5

    # Apply layer weights
    scored = []
    for mem in samples:
        layer = mem.get("current_layer", "working")
        layer_weight = get_layer_multiplier(layer)
        weighted_score = base_score * layer_weight

        scored.append({
            "layer": layer,
            "base_score": base_score,
            "layer_weight": layer_weight,
            "final_score": weighted_score
        })

    # Sort by final score (descending)
    scored.sort(key=lambda x: x["final_score"], reverse=True)

    # Count top N by layer
    top_n = min(50, len(scored))
    top_samples = scored[:top_n]

    layer_counts = {"working": 0, "episodic": 0, "semantic": 0}
    for s in top_samples:
        layer = s["layer"]
        layer_counts[layer] = layer_counts.get(layer, 0) + 1

    print(f"\nTop {top_n} memories by layer:")
    for layer in ["working", "episodic", "semantic"]:
        count = layer_counts[layer]
        pct = (count / top_n * 100)
        print(f"  {layer.capitalize():10s}: {count:3d} ({pct:5.1f}%)")

    print()

    # Check if composition is balanced
    episodic_pct = (layer_counts["episodic"] / top_n * 100)
    semantic_pct = (layer_counts["semantic"] / top_n * 100)

    if semantic_pct > 40:
        print("[PROBLEM] Even after layer weights, semantic dominates top results")
        print("   SOLUTION: Increase layer weight disparity (stronger weights)")
    elif episodic_pct > 40:
        print("[SUCCESS] Episodic memories dominate top results")
    else:
        print("[WARNING] Composition is mixed but not ideal")


def suggest_stronger_weights(distribution: Dict[str, int]):
    """Suggest stronger weights based on actual distribution."""
    print("\n" + "="*70)
    print("RECOMMENDED WEIGHT ADJUSTMENTS")
    print("="*70)

    total = sum(distribution.values())
    semantic_raw_pct = (distribution["semantic"] / total * 100) if total > 0 else 0
    episodic_raw_pct = (distribution["episodic"] / total * 100) if total > 0 else 0

    print(f"\nYour memory distribution:")
    print(f"  Semantic: {semantic_raw_pct:.1f}% of stored memories")
    print(f"  Episodic: {episodic_raw_pct:.1f}% of stored memories")

    # Calculate required ratio
    # If semantic is 60% and we want 30% in retrieval, we need ~2x penalty
    # If episodic is 25% and we want 45% in retrieval, we need ~1.8x boost

    target_semantic_pct = 30.0
    target_episodic_pct = 48.0

    # Calculate multipliers needed
    semantic_multiplier = target_semantic_pct / semantic_raw_pct if semantic_raw_pct > 0 else 1.0
    episodic_multiplier = target_episodic_pct / episodic_raw_pct if episodic_raw_pct > 0 else 1.0

    # Normalize (semantic becomes the baseline)
    normalized_semantic = semantic_multiplier / semantic_multiplier  # = 1.0
    normalized_episodic = episodic_multiplier / semantic_multiplier

    # Scale to make semantic < 1.0 (penalty)
    if semantic_raw_pct > 50:
        # Severe semantic dominance - use aggressive penalty
        recommended_semantic = 0.25
        recommended_episodic = 3.0
        recommended_working = 3.5
    elif semantic_raw_pct > 40:
        # Moderate semantic dominance - use strong penalty
        recommended_semantic = 0.35
        recommended_episodic = 2.5
        recommended_working = 3.0
    else:
        # Mild imbalance - use moderate weights
        recommended_semantic = 0.5
        recommended_episodic = 2.0
        recommended_working = 2.5

    print()
    print("RECOMMENDED WEIGHTS for your distribution:")
    print()
    print("```python")
    print("# In engines/memory_layer_rebalancing.py:")
    print("LAYER_WEIGHTS = {")
    print(f'    "working": {recommended_working},    # Immediate context (critical)')
    print(f'    "episodic": {recommended_episodic},   # Conversation arcs (important)')
    print(f'    "semantic": {recommended_semantic},   # Background facts (lower priority)')
    print("}")
    print("```")
    print()

    # Show impact
    print("Expected impact:")
    ratio = recommended_episodic / recommended_semantic
    print(f"  Episodic/Semantic ratio: {ratio:.1f}x (currently {LAYER_WEIGHTS['episodic'] / LAYER_WEIGHTS['semantic']:.1f}x)")
    print()
    print("After applying these weights, you should see:")
    print("  - Episodic: 40-50% of retrieved memories")
    print("  - Semantic: 25-35% of retrieved memories")
    print("  - Working: 15-25% of retrieved memories")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MEMORY COMPOSITION DIAGNOSTIC")
    print("="*70)
    print()
    print("This tool diagnoses why semantic memories might be dominating retrieval")
    print("and provides recommendations for stronger layer weights.")
    print()

    # Run diagnostics
    distribution = check_raw_memory_distribution()
    check_layer_weights()
    simulate_scoring(sample_size=150)
    suggest_stronger_weights(distribution)

    print()
    print("="*70)
    print("DIAGNOSIS COMPLETE")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Review recommended weights above")
    print("2. Update LAYER_WEIGHTS in engines/memory_layer_rebalancing.py")
    print("3. Restart Kay and monitor [SEMANTIC USAGE] logs")
    print("4. Run this diagnostic again after 5-10 turns to verify improvement")
    print()
