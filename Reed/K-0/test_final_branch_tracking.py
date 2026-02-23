"""
Final test: Verify branch tracking works when doc_id is present
Uses SAME memory engine for import and retrieval
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_branch_tracking_complete():
    print("=" * 60)
    print("FINAL TEST: Branch Tracking with doc_id")
    print("=" * 60)
    print()

    from memory_import.emotional_importer import EmotionalMemoryImporter
    from protocol_engine import ProtocolEngine
    from engines.memory_engine import MemoryEngine
    from engines.emotion_engine import EmotionEngine
    from engines.momentum_engine import MomentumEngine
    from engines.motif_engine import MotifEngine
    from agent_state import AgentState

    # Step 1: Initialize SINGLE memory engine
    print("[STEP 1] Initializing memory engine...")
    print("-" * 60)

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

    print(f"[STEP 1] Memory engine initialized")
    print()

    # Step 2: Import document to THIS memory engine
    print("[STEP 2] Importing document...")
    print("-" * 60)

    test_content = """Gimpy is a one-legged pigeon who lives near the park.
Kay remembers Gimpy fondly and often thinks about the resilient bird.
The Memory Forest system helps Kay organize these memories into trees."""

    test_file = "test_gimpy.txt"
    with open(test_file, 'w') as f:
        f.write(test_content)

    importer = EmotionalMemoryImporter()
    result = importer.import_to_memory_engine(test_file, memory)

    print("-" * 60)
    print(f"[STEP 2] Imported {result['total_chunks']} chunks")
    print()

    # Step 3: Verify chunks have doc_id BEFORE retrieval
    print("[STEP 3] Verifying chunks in memory layers...")
    print("-" * 60)

    # Check if chunks are in memory layers with doc_id
    all_memories = (memory.memory_layers.working_memory +
                   memory.memory_layers.episodic_memory +
                   memory.memory_layers.semantic_memory)

    gimpy_memories = [m for m in all_memories if 'gimpy' in m.get('text', '').lower()]
    gimpy_with_doc_id = [m for m in gimpy_memories if m.get('doc_id')]

    print(f"Total Gimpy memories: {len(gimpy_memories)}")
    print(f"Gimpy memories with doc_id: {len(gimpy_with_doc_id)}")

    if gimpy_with_doc_id:
        print(f"Sample doc_id: {gimpy_with_doc_id[0].get('doc_id')}")
        print(f"Sample chunk_index: {gimpy_with_doc_id[0].get('chunk_index')}")
    else:
        print("[WARNING] No Gimpy memories have doc_id!")

    print("-" * 60)
    print()

    # Step 4: Retrieve memories about Gimpy
    print("[STEP 4] Retrieving memories about Gimpy...")
    print("=" * 60)

    memories = memory.recall(state, "Tell me about Gimpy the pigeon", num_memories=82)

    print("=" * 60)
    print()

    # Step 5: Check results
    print("[STEP 5] Analyzing results...")
    print("-" * 60)

    total = len(memories)
    gimpy_retrieved = [m for m in memories if 'gimpy' in str(m.get('text', '')).lower()]
    with_doc_id = [m for m in gimpy_retrieved if m.get('doc_id')]

    print(f"Total retrieved: {total}")
    print(f"Gimpy memories retrieved: {len(gimpy_retrieved)}")
    print(f"Gimpy memories with doc_id: {len(with_doc_id)}")

    if with_doc_id:
        print()
        print("SUCCESS! Gimpy memories with doc_id:")
        for i, m in enumerate(with_doc_id[:3]):
            print(f"  {i+1}. doc_id={m.get('doc_id')}, chunk_index={m.get('chunk_index')}")
            print(f"     text: {m.get('text', '')[:60]}...")
    else:
        print()
        print("[WARNING] No Gimpy memories retrieved with doc_id")
        if gimpy_retrieved:
            print("  - Gimpy memories were retrieved, but lack doc_id field")
        else:
            print("  - No Gimpy memories retrieved at all")

    print("-" * 60)
    print()

    # Step 6: Expected logs
    print("[STEP 6] Expected logs above:")
    print("-" * 60)
    print("- [RETRIEVAL] Tiered allocation: 20 identity + N imports + ...")
    print("- [MEMORY FOREST] Retrieved memories from X branches:")
    print("- [MEMORY FOREST]   - Branch Name: X chunks [tier: cold]")
    print("-" * 60)
    print()

    if with_doc_id:
        print("[SUCCESS] Branch tracking should be visible!")
        print("[CHECK] Did you see '[MEMORY FOREST] Retrieved memories from' logs?")
    else:
        print("[INCOMPLETE] doc_id not making it to retrieved memories")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_branch_tracking_complete()
