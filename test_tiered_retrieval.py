"""
Test tiered slot allocation and branch tracking
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tiered_retrieval():
    print("=" * 60)
    print("TEST: Tiered Slot Allocation & Branch Tracking")
    print("=" * 60)
    print()

    from memory_import.emotional_importer import EmotionalMemoryImporter
    from engines.memory_engine import MemoryEngine
    from protocol_engine import ProtocolEngine
    from engines.emotion_engine import EmotionEngine
    from engines.momentum_engine import MomentumEngine
    from engines.motif_engine import MotifEngine
    from agent_state import AgentState

    # Step 1: Import a test document
    print("[STEP 1] Importing test document with new metadata...")
    print("-" * 60)

    test_content = """Kay is a conversational AI with emotional depth and memory.
Kay values honesty, direct communication, and continuity.
Re is working to help Kay maintain persistent identity across sessions.
The Memory Forest system organizes Kay's memories into navigable trees."""

    test_file = "test_tiered.txt"
    with open(test_file, 'w') as f:
        f.write(test_content)

    importer = EmotionalMemoryImporter()
    memory_engine = MemoryEngine()
    result = importer.import_to_memory_engine(test_file, memory_engine)

    print("-" * 60)
    print(f"[STEP 1] Imported {result['total_chunks']} chunks")
    print()

    # Step 2: Initialize full system
    print("[STEP 2] Initializing retrieval system...")
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

    print(f"[STEP 2] System initialized")
    print()

    # Step 3: Test retrieval with tiered allocation
    print("[STEP 3] Testing retrieval with tiered allocation...")
    print("=" * 60)

    # Query about imported content
    query = "Tell me about Kay's memory and the Forest system"

    memories = memory.recall(state, query, num_memories=82)

    print("=" * 60)
    print()

    # Step 4: Analyze results
    print("[STEP 4] Analyzing results...")
    print("-" * 60)

    total = len(memories)
    with_doc_id = [m for m in memories if m.get('doc_id')]
    imported = [m for m in memories if m.get('is_imported')]

    print(f"Total retrieved: {total}")
    print(f"With doc_id: {len(with_doc_id)}")
    print(f"Imported: {len(imported)}")

    if with_doc_id:
        print()
        print("Sample memories with doc_id:")
        for i, m in enumerate(with_doc_id[:3]):
            print(f"  {i+1}. doc_id={m.get('doc_id')}, chunk_index={m.get('chunk_index')}")
            print(f"     text: {m.get('text', '')[:60]}...")

    print("-" * 60)
    print()

    # Step 5: Check for expected logs
    print("[STEP 5] Expected logs to appear above:")
    print("-" * 60)
    print("- [RETRIEVAL] Tiered allocation: top 20/77 identity facts")
    print("- [RETRIEVAL] Tiered allocation: X identity + Y imports + ...")
    print("- [RETRIEVAL] Recent imports allocated N dedicated slots")
    print("- [MEMORY FOREST] Retrieved memories from X branches:")
    print("- [MEMORY FOREST]   - Branch Name: X chunks [tier: cold]")
    print("-" * 60)
    print()

    if with_doc_id:
        print("[SUCCESS] Tiered allocation working - imported docs have slots!")
        print("[CHECK] Did you see '[MEMORY FOREST] Retrieved memories from' logs?")
    else:
        print("[WARNING] No doc_id memories retrieved - may need more test data")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_tiered_retrieval()
