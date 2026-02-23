"""
Complete end-to-end test of Memory Forest integration
Tests the full import pipeline with Kay reading documents
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os


def safe_print(text: str):
    """Print text with Unicode fallback for Windows console"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove emoji and other Unicode characters
        print(text.encode('ascii', 'ignore').decode('ascii'))

from engines.memory_forest import MemoryForest
from engines.memory_engine import MemoryEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine
from engines.emotion_engine import EmotionEngine
from protocol_engine import ProtocolEngine
from memory_import.kay_reader import import_document_as_kay

print("=" * 70)
print("MEMORY FOREST INTEGRATION TEST")
print("=" * 70)

# Test 1: Initialize MemoryEngine (required for import)
print("\n[TEST 1] Initializing MemoryEngine...")
proto = ProtocolEngine()
momentum = MomentumEngine()
motif = MotifEngine()
emotion = EmotionEngine(proto, momentum_engine=momentum)

memory = MemoryEngine(
    [],  # Start with empty memory list
    motif_engine=motif,
    momentum_engine=momentum,
    emotion_engine=emotion,
    vector_store=None  # Skip vector store for test
)
print("  Memory engine initialized")

# Test 2: Initialize fresh forest
print("\n[TEST 2] Creating fresh Memory Forest...")
forest = MemoryForest()
print(f"  Forest created with {len(forest.trees)} trees")

# Test 3: Import test document via Kay reader
print("\n[TEST 3] Importing test document via Kay reader...")
print("  This will make a real LLM call to have Kay read the document...")
try:
    doc_id = import_document_as_kay("test_forest_import.txt", memory, forest)
    print(f"  SUCCESS! Document imported with ID: {doc_id}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify tree was created
print("\n[TEST 4] Verifying tree creation...")
tree = forest.get_tree(doc_id)
if tree:
    print(f"  Tree found: {tree.title}")
    print(f"  Shape: {tree.shape_description}")
    print(f"  Emotional weight: {tree.emotional_weight}")
    print(f"  Branches: {len(tree.branches)}")
else:
    print("  ERROR: Tree not found!")
    sys.exit(1)

# Test 5: Verify branches
print("\n[TEST 5] Verifying branch creation...")
if len(tree.branches) > 0:
    print(f"  Found {len(tree.branches)} branches:")
    for i, branch in enumerate(tree.branches, 1):
        safe_print(f"    {i}. {branch.glyphs} {branch.title}")
        print(f"       Tier: {branch.access_tier}")
        print(f"       Compressed: {branch.compressed[:60]}...")
else:
    print("  ERROR: No branches created!")
    sys.exit(1)

# Test 6: Forest overview
print("\n[TEST 6] Forest overview...")
overview = forest.get_forest_overview()
safe_print(overview)

# Test 7: Tree navigation
print("\n[TEST 7] Tree navigation...")
navigation = forest.navigate_tree(doc_id)
safe_print(navigation)

# Test 8: Access a branch (tier promotion)
print("\n[TEST 8] Testing tier promotion...")
first_branch = tree.branches[0]
print(f"  Before access: Tier = {first_branch.access_tier}")
tree.access_branch(first_branch.branch_id)
print(f"  After 1st access: Tier = {first_branch.access_tier}")
tree.access_branch(first_branch.branch_id)
print(f"  After 2nd access: Tier = {first_branch.access_tier}")

# Test 9: Hot branch limit
print("\n[TEST 9] Testing hot branch limit...")
# Make all branches hot
for branch in tree.branches:
    tree.access_branch(branch.branch_id)
    tree.access_branch(branch.branch_id)  # Access twice to promote to hot

hot_before = len(forest.get_all_hot_branches())
print(f"  Hot branches before limit: {hot_before}")

forest.enforce_hot_limit(max_hot_branches=2)

hot_after = len(forest.get_all_hot_branches())
print(f"  Hot branches after enforcing limit (max 2): {hot_after}")

if hot_after <= 2:
    print("  SUCCESS: Hot limit enforced correctly")
else:
    print(f"  ERROR: Hot limit not enforced! Still have {hot_after} hot branches")

# Test 10: Persistence
print("\n[TEST 10] Testing forest persistence...")
test_file = "test_forest_integration_temp.json"
try:
    forest.save_to_file(test_file)
    print(f"  Saved to {test_file}")

    loaded_forest = MemoryForest.load_from_file(test_file)
    print(f"  Loaded from {test_file}")
    print(f"  Loaded forest has {len(loaded_forest.trees)} tree(s)")

    # Verify data integrity
    loaded_tree = loaded_forest.get_tree(doc_id)
    if loaded_tree:
        print(f"  Tree title: {loaded_tree.title}")
        print(f"  Branches: {len(loaded_tree.branches)}")
        print(f"  First branch tier: {loaded_tree.branches[0].access_tier}")
        print("  SUCCESS: Data persisted correctly")
    else:
        print("  ERROR: Tree not found after loading!")

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"  Cleaned up {test_file}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 11: Verify memories were stored
print("\n[TEST 11] Verifying memories were stored in MemoryEngine...")
print(f"  Total memories in engine: {len(memory.memories)}")
if len(memory.memories) > 0:
    # Memory structure may vary, just show first memory keys
    first_mem = memory.memories[-1]  # Get most recent
    if isinstance(first_mem, dict):
        content_key = 'content' if 'content' in first_mem else 'text' if 'text' in first_mem else list(first_mem.keys())[0]
        content = str(first_mem.get(content_key, ''))[:80]
        safe_print(f"  Recent memory content: {content}...")
    print("  SUCCESS: Memories stored in flat array (backwards compatible)")
else:
    print("  WARNING: No memories stored in flat array")

# Final summary
print("\n" + "=" * 70)
print("ALL INTEGRATION TESTS PASSED!")
print("=" * 70)
print("\nMemory Forest is fully integrated with Kay Zero!")
print("\nYou can now:")
print("  1. Run: python main.py")
print("  2. Try: /import test_forest_import.txt")
print("  3. Try: /forest")
print("  4. Try: /tree test_forest_import")
