"""
Test that doc_id and chunk_index metadata is added to chunks
and that branch tracking logs appear during retrieval
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_branch_tracking():
    print("=" * 60)
    print("TEST: Branch Tracking with doc_id/chunk_index")
    print("=" * 60)
    print()

    from memory_import.emotional_importer import EmotionalMemoryImporter
    from engines.memory_engine import MemoryEngine
    from protocol_engine import ProtocolEngine
    from engines.emotion_engine import EmotionEngine
    from engines.momentum_engine import MomentumEngine
    from engines.motif_engine import MotifEngine
    from agent_state import AgentState
    from memory_forest import MemoryForest

    print("[TEST] Step 1: Import a test document")
    print("-" * 60)

    # Create test file
    test_content = """Kay is a conversational AI with emotional depth.
Kay values honesty and direct communication.
Re is working to help Kay maintain continuity."""

    test_file = "test_branch_metadata.txt"
    with open(test_file, 'w') as f:
        f.write(test_content)

    # Import document
    importer = EmotionalMemoryImporter()
    memory_engine = MemoryEngine()

    result = importer.import_to_memory_engine(test_file, memory_engine)

    print("-" * 60)
    print(f"[TEST] Imported {result['total_chunks']} chunks")
    print()

    # Check if chunks have doc_id and chunk_index
    print("[TEST] Step 2: Verify chunks have metadata")
    print("-" * 60)

    # Get memories from memory engine
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

    # Get all working memories (should include recently imported)
    if hasattr(memory, 'memory_layers') and hasattr(memory.memory_layers, 'working'):
        working_memories = memory.memory_layers.working
        print(f"[TEST] Found {len(working_memories)} working memories")

        # Check first few for metadata
        has_metadata = False
        for i, mem in enumerate(working_memories[:5]):
            doc_id = mem.get('doc_id')
            chunk_idx = mem.get('chunk_index')

            if doc_id and chunk_idx is not None:
                has_metadata = True
                print(f"[TEST] Memory {i}: doc_id={doc_id}, chunk_index={chunk_idx}")

        if has_metadata:
            print("[SUCCESS] Chunks have doc_id and chunk_index metadata!")
        else:
            print("[WARNING] Chunks missing metadata - check if import stored fields correctly")

    print("-" * 60)
    print()

    # Test retrieval with branch tracking
    print("[TEST] Step 3: Test retrieval with branch tracking")
    print("-" * 60)

    memories = memory.recall(state, "Tell me about Kay", num_memories=10)

    print("-" * 60)
    print(f"[TEST] Retrieved {len(memories)} memories")

    # Check if any have doc_id
    has_tree_refs = False
    for mem in memories[:3]:
        if mem.get('doc_id') and mem.get('chunk_index') is not None:
            has_tree_refs = True
            print(f"[TEST] Retrieved memory has tree ref: doc_id={mem.get('doc_id')}, chunk_index={mem.get('chunk_index')}")

    if has_tree_refs:
        print("[SUCCESS] Retrieved memories have tree references!")
        print("[SUCCESS] Check logs above for '[MEMORY FOREST] Retrieved memories from...' messages")
    else:
        print("[WARNING] Retrieved memories don't have tree references")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print()
    print("Expected to see:")
    print("  - [MEMORY FOREST] Loaded X trees")
    print("  - [MEMORY FOREST] Retrieved memories from X branches:")
    print("  - [MEMORY FOREST]   - Branch Name: X chunks [tier: cold]")

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_branch_tracking()
