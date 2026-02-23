"""
Test Phase 2A: Tree-aware retrieval logging
Should show forest loading at startup and branch access during retrieval
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_phase2a():
    print("=" * 60)
    print("TESTING PHASE 2A: TREE-AWARE RETRIEVAL LOGGING")
    print("=" * 60)
    print()

    # Import components
    from protocol_engine import ProtocolEngine
    from engines.memory_engine import MemoryEngine
    from engines.emotion_engine import EmotionEngine
    from engines.momentum_engine import MomentumEngine
    from engines.motif_engine import MotifEngine
    from agent_state import AgentState
    from memory_forest import MemoryForest

    print("[TEST] Initializing engines...")
    print()

    # Initialize minimal system
    state = AgentState()
    proto = ProtocolEngine()
    momentum = MomentumEngine()
    motif = MotifEngine()
    emotion = EmotionEngine(proto, momentum_engine=momentum)

    memory = MemoryEngine(
        state.memory,
        motif_engine=motif,
        momentum_engine=momentum,
        emotion_engine=emotion
    )

    print("[TEST] Loading memory forest...")
    memory_forest = MemoryForest.load_all_trees("data/trees")
    print(f"[TEST] Loaded {len(memory_forest.trees)} trees")
    print()

    # Show what trees we have
    if memory_forest.trees:
        print("[TEST] Available trees:")
        for tree in memory_forest.list_trees():
            print(f"  - {tree.title}: {tree.total_chunks} chunks, {len(tree.branches)} branches")
        print()

    # Test retrieval with a simple query
    print("[TEST] Testing memory retrieval with tree tracking...")
    print("-" * 60)

    # Simulate a query that should trigger memories
    test_query = "Tell me about yourself"

    # Recall memories (this should trigger tree tracking)
    memories = memory.recall(state, test_query, num_memories=10)

    print("-" * 60)
    print()
    print(f"[TEST] Retrieved {len(memories)} memories")

    # Check if any have doc_id and chunk_index
    has_tree_refs = False
    for mem in memories[:3]:  # Check first 3
        if mem.get('doc_id') and mem.get('chunk_index') is not None:
            has_tree_refs = True
            print(f"[TEST] Memory has tree reference: doc_id={mem.get('doc_id')}, chunk_index={mem.get('chunk_index')}")

    if not has_tree_refs:
        print("[TEST] WARNING: Retrieved memories don't have doc_id/chunk_index fields")
        print("[TEST] This means tree tracking won't work yet - need to ensure memories store these fields")

    print()
    print("=" * 60)
    print("PHASE 2A TEST COMPLETE")
    print("=" * 60)
    print()
    print("Expected logs:")
    print("  - [MEMORY FOREST] Loaded X trees")
    print("  - [MEMORY FOREST] Loaded tree: ... (X branches)")
    print("  - [MEMORY FOREST] Retrieved memories from X branches:")
    print("  - [MEMORY FOREST]   - Branch Name (glyphs): X chunks [tier: cold]")
    print()

if __name__ == "__main__":
    test_phase2a()
