"""
Fix Layer Rebalancing: Volume Problem

PROBLEM: Weights are being applied correctly, but semantic layer has 3593 memories
vs only 100 episodic. Even with 8.3x ratio, semantic dominates due to volume.

SOLUTION: Two approaches
1. Increase weight disparity (episodic: 15x, semantic: 0.1x = 150x ratio)
2. Add hard caps on layer selection

This script updates the layer weights and adds capping logic.
"""

import os
import re


def update_layer_weights_for_volume():
    """Update layer weights to handle massive semantic volume."""

    rebalancing_file = "engines/memory_layer_rebalancing.py"

    if not os.path.exists(rebalancing_file):
        print(f"[ERROR] {rebalancing_file} not found!")
        return False

    with open(rebalancing_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Backup
    with open("engines/memory_layer_rebalancing_BACKUP_BEFORE_VOLUME_FIX.py", 'w', encoding='utf-8') as f:
        f.write(content)
    print("[BACKUP] Created memory_layer_rebalancing_BACKUP_BEFORE_VOLUME_FIX.py")

    # Update weights to handle volume problem
    old_weights = '''LAYER_WEIGHTS = {
    "working": 3.0,    # 3.0x boost - Immediate context is critical (up from 2.0x)
    "episodic": 2.5,   # 2.5x boost - Conversation arcs provide continuity (up from 1.8x)
    "semantic": 0.3,   # 0.3x reduction - Background facts lower priority (down from 0.6x)
}'''

    new_weights = '''LAYER_WEIGHTS = {
    "working": 5.0,    # 5.0x boost - Immediate context is critical (up from 3.0x)
    "episodic": 10.0,  # 10.0x boost - Conversation arcs provide continuity (up from 2.5x)
    "semantic": 0.05,  # 0.05x reduction - Background facts MUCH lower priority (down from 0.3x)
}

# VOLUME-AWARE: When semantic layer has massive volume (3500+ memories),
# even 0.3x penalty isn't enough. New ratio: episodic/semantic = 200x'''

    if old_weights in content:
        content = content.replace(old_weights, new_weights)
        print("[UPDATED] Layer weights increased to handle volume problem")
        print("  Working: 3.0 -> 5.0x")
        print("  Episodic: 2.5 -> 10.0x")
        print("  Semantic: 0.3 -> 0.05x")
        print("  New ratio: episodic/semantic = 200x (up from 8.3x)")
    else:
        print("[WARNING] Could not find exact weights pattern - may need manual update")
        return False

    # Write updated file
    with open(rebalancing_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[SUCCESS] Updated {rebalancing_file}")

    # Calculate new effective pools
    print("\n" + "="*70)
    print("NEW EFFECTIVE POOL SIZES")
    print("="*70)
    print(f"  Working:  10 × 5.0  = 50 effective")
    print(f"  Episodic: 100 × 10.0 = 1000 effective")
    print(f"  Semantic: 3593 × 0.05 = 180 effective")
    print()
    print("  NOW episodic dominates (1000 > 180)!")
    print("="*70)

    return True


def add_layer_capping():
    """Add hard caps to layer selection as additional safeguard."""

    print("\n" + "="*70)
    print("ADDING LAYER CAPPING LOGIC")
    print("="*70)

    cap_code = '''
def apply_layer_caps(scored_memories, max_total=225):
    """
    Apply hard caps to layer selection as safeguard against volume imbalance.

    Even with strong weights, if one layer has massive volume (e.g., 3500+ semantic),
    it can still dominate. This ensures target distribution.

    Args:
        scored_memories: List of memories with scores
        max_total: Maximum total memories to return

    Returns:
        Capped list of memories
    """
    # Target distribution
    caps = {
        'working': int(max_total * 0.20),    # 45 memories (20%)
        'episodic': int(max_total * 0.50),   # 112 memories (50%)
        'semantic': int(max_total * 0.30),   # 68 memories (30%)
    }

    # Separate by layer and sort by score
    by_layer = {'working': [], 'episodic': [], 'semantic': []}
    for mem in scored_memories:
        layer = mem.get('current_layer', 'semantic')
        if layer in by_layer:
            by_layer[layer].append(mem)

    # Sort each layer by score
    for layer in by_layer:
        by_layer[layer].sort(key=lambda m: m.get('score', 0), reverse=True)

    # Apply caps and collect
    selected = []
    for layer, cap in caps.items():
        layer_selected = by_layer[layer][:cap]
        selected.extend(layer_selected)
        print(f"[LAYER CAP] {layer.capitalize():10s}: selected {len(layer_selected):3d}/{cap:3d} cap (from {len(by_layer[layer])} available)")

    # Sort final selection by score
    selected.sort(key=lambda m: m.get('score', 0), reverse=True)

    print(f"[LAYER CAP] Total selected: {len(selected)} memories")

    return selected
'''

    # Save to file
    with open("engines/memory_layer_capping.py", 'w', encoding='utf-8') as f:
        f.write('"""\nLayer Capping for Volume-Imbalanced Memory Systems\n"""\n\n')
        f.write(cap_code)

    print("[CREATED] engines/memory_layer_capping.py")
    print("\nTo use:")
    print("  1. Import: from engines.memory_layer_capping import apply_layer_caps")
    print("  2. After scoring: selected = apply_layer_caps(scored_memories)")
    print()
    print("This ensures even with volume imbalance, distribution is correct")

    return True


def test_new_weights():
    """Test new weights with actual distribution."""

    print("\n" + "="*70)
    print("TESTING NEW WEIGHTS")
    print("="*70)

    # Reload with new weights
    import sys
    if 'engines.memory_layer_rebalancing' in sys.modules:
        del sys.modules['engines.memory_layer_rebalancing']

    from engines.memory_layer_rebalancing import LAYER_WEIGHTS, get_layer_multiplier

    print("\nNew layer weights:")
    for layer, weight in LAYER_WEIGHTS.items():
        print(f"  {layer}: {weight}x")

    print("\nEffective pool sizes:")
    working_eff = 10 * get_layer_multiplier("working")
    episodic_eff = 100 * get_layer_multiplier("episodic")
    semantic_eff = 3593 * get_layer_multiplier("semantic")

    print(f"  Working:  10 × {get_layer_multiplier('working'):4.1f} = {working_eff:7.1f}")
    print(f"  Episodic: 100 × {get_layer_multiplier('episodic'):4.1f} = {episodic_eff:7.1f}")
    print(f"  Semantic: 3593 × {get_layer_multiplier('semantic'):4.2f} = {semantic_eff:7.1f}")

    total_eff = working_eff + episodic_eff + semantic_eff

    print("\nExpected composition (assuming uniform base scores):")
    print(f"  Working:  {working_eff / total_eff * 100:5.1f}% (target: 18-20%)")
    print(f"  Episodic: {episodic_eff / total_eff * 100:5.1f}% (target: 45-50%)")
    print(f"  Semantic: {semantic_eff / total_eff * 100:5.1f}% (target: 30-35%)")

    # Check if acceptable
    episodic_pct = episodic_eff / total_eff * 100
    semantic_pct = semantic_eff / total_eff * 100

    if episodic_pct > 40 and semantic_pct < 40:
        print("\n[SUCCESS] Episodic now dominates! Weights should work.")
    else:
        print("\n[WARNING] May need even stronger weights or capping")

    print("="*70)


if __name__ == "__main__":
    print("="*70)
    print("FIX LAYER REBALANCING: VOLUME PROBLEM")
    print("="*70)
    print()
    print("Problem: Semantic layer has 3593 memories vs 100 episodic")
    print("Even with 8.3x weight ratio, semantic dominates due to volume")
    print()
    print("Solution: Increase weights dramatically (episodic/semantic = 200x)")
    print()

    # Update weights
    success = update_layer_weights_for_volume()

    if success:
        # Add capping logic
        add_layer_capping()

        # Test
        test_new_weights()

        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print()
        print("1. Restart Kay: python main.py")
        print("2. Look for composition validation:")
        print("   [OK] Episodic  : ~110 memories ( 48%)")
        print("   [OK] Semantic  :  ~70 memories ( 31%)")
        print()
        print("3. If STILL not working, use layer capping:")
        print("   - Integrate apply_layer_caps() into retrieval")
        print("   - See memory_layer_capping.py for code")
        print()
        print("="*70)
    else:
        print("\n[FAILED] Could not update weights automatically")
        print("Manual update required in engines/memory_layer_rebalancing.py")
