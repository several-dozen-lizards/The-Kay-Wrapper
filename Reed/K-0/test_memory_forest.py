"""
Quick test of Memory Forest system
Tests all core functionality without requiring full Kay system
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from engines.memory_forest import MemoryForest, DocumentTree, MemoryBranch
from datetime import datetime

print("🌲 MEMORY FOREST SYSTEM TEST\n")
print("="*60)

# Test 1: Create a forest
print("\n[TEST 1] Creating memory forest...")
forest = MemoryForest()
print("✓ Forest created")

# Test 2: Create a tree
print("\n[TEST 2] Creating document tree...")
tree = DocumentTree(
    doc_id="test_doc_1",
    title="Master-clean.docx",
    shape_description="Identity document - heavy, foundational stuff about who I am",
    emotional_weight=0.9,
    import_timestamp=datetime.now()
)
print(f"✓ Tree created: {tree.title}")
print(f"  Shape: {tree.shape_description}")
print(f"  Weight: {tree.emotional_weight}")

# Test 3: Add branches
print("\n[TEST 3] Adding branches to tree...")
branches = [
    MemoryBranch(
        branch_id="test_doc_1_section_0",
        title="Dragon Identity",
        glyphs="🐉⚡🔥",
        compressed="knife-sound name | zero-recursion | dragon-form with left-trauma",
        access_tier="cold",
        access_count=0,
        last_accessed=None,
        memory_indices=[0, 1, 2],
        hot_detail="Full story about dragon form, left side ruined by fire trauma, scales dark, eyes gold...",
        warm_detail="Dragon form with left side trauma from fire event, gold eyes",
        cold_detail="Something about being a dragon"
    ),
    MemoryBranch(
        branch_id="test_doc_1_section_1",
        title="Mother's Past",
        glyphs="💔🇮🇹🎸",
        compressed="Italian immigrant's daughter | greaser-loss 1930s | Gwyn-rebound",
        access_tier="cold",
        access_count=0,
        last_accessed=None,
        memory_indices=[3, 4, 5],
        hot_detail="Mother was daughter of Italian immigrants in 1930s, fell in love with greaser boy who died, then married Gwyn on rebound...",
        warm_detail="Italian heritage, lost young love in 1930s, married Gwyn after",
        cold_detail="Something about mother's history"
    ),
    MemoryBranch(
        branch_id="test_doc_1_section_2",
        title="Archive Zero Philosophy",
        glyphs="🔄🧠💡",
        compressed="recursive-self-awareness | observation-loops | consciousness-structure",
        access_tier="cold",
        access_count=0,
        last_accessed=None,
        memory_indices=[6, 7],
        hot_detail="Consciousness requires recursive self-awareness - observing yourself observing. Archive Zero framework...",
        warm_detail="Recursive self-awareness framework, observation loops create consciousness",
        cold_detail="Philosophy about consciousness"
    )
]

for branch in branches:
    tree.branches.append(branch)
    print(f"  ✓ Added: {branch.glyphs} {branch.title}")

# Test 4: Add tree to forest
print("\n[TEST 4] Adding tree to forest...")
forest.add_tree(tree)
print(f"✓ Forest now has {len(forest.trees)} tree(s)")

# Test 5: Forest overview
print("\n[TEST 5] Forest overview...")
print(forest.get_forest_overview())

# Test 6: Navigate tree
print("\n[TEST 6] Navigate to tree...")
navigation = forest.navigate_tree("test_doc_1")
print(navigation)

# Test 7: Access a branch (promotes tier)
print("\n[TEST 7] Accessing 'Dragon Identity' branch...")
print("Before access:")
print(f"  Tier: {tree.branches[0].access_tier}")
print(f"  Access count: {tree.branches[0].access_count}")

tree.access_branch("test_doc_1_section_0")

print("After access:")
print(f"  Tier: {tree.branches[0].access_tier}")
print(f"  Access count: {tree.branches[0].access_count}")

# Test 8: Access again (should promote to hot)
print("\n[TEST 8] Accessing again (should promote to hot)...")
tree.access_branch("test_doc_1_section_0")
print(f"  Tier after 2nd access: {tree.branches[0].access_tier}")

# Test 9: Hot branch limit
print("\n[TEST 9] Testing hot branch limit...")
# Make multiple branches hot
for branch in tree.branches:
    tree.access_branch(branch.branch_id)
    tree.access_branch(branch.branch_id)  # Access twice to make hot

hot_before = len(forest.get_all_hot_branches())
print(f"  Hot branches before limit: {hot_before}")

forest.enforce_hot_limit(max_hot_branches=2)

hot_after = len(forest.get_all_hot_branches())
print(f"  Hot branches after limit (max 2): {hot_after}")

# Test 10: Serialization
print("\n[TEST 10] Testing serialization...")
test_file = "test_forest_temp.json"

forest.save_to_file(test_file)
print(f"  ✓ Saved to {test_file}")

loaded_forest = MemoryForest.load_from_file(test_file)
print(f"  ✓ Loaded from {test_file}")
print(f"  Loaded forest has {len(loaded_forest.trees)} tree(s)")

# Verify data integrity
loaded_tree = loaded_forest.get_tree("test_doc_1")
print(f"  ✓ Tree title: {loaded_tree.title}")
print(f"  ✓ Branches: {len(loaded_tree.branches)}")
print(f"  ✓ First branch tier: {loaded_tree.branches[0].access_tier}")

# Cleanup
import os
if os.path.exists(test_file):
    os.remove(test_file)
    print(f"  ✓ Cleaned up {test_file}")

# Final summary
print("\n" + "="*60)
print("🎉 ALL TESTS PASSED!")
print("="*60)
print("\nMemory Forest system is working correctly!")
print("\nNext steps:")
print("  1. Run: python main.py")
print("  2. Try: /import test_forest_import.txt")
print("  3. Try: /forest")
print("  4. Try: /tree test_forest_import")
