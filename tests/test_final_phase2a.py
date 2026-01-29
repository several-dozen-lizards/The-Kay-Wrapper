"""
Final Phase 2A Test: Verify branch tracking logs appear during actual retrieval
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_final_phase2a():
    print("=" * 60)
    print("FINAL PHASE 2A TEST: Branch Tracking Logs")
    print("=" * 60)
    print()

    from protocol_engine import ProtocolEngine
    from engines.memory_engine import MemoryEngine
    from engines.emotion_engine import EmotionEngine
    from engines.momentum_engine import MomentumEngine
    from engines.motif_engine import MotifEngine
    from agent_state import AgentState

    print("[TEST] Initializing system...")
    print()

    # Initialize components
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

    print("[TEST] Performing memory retrieval...")
    print("[TEST] Look for '[MEMORY FOREST] Retrieved memories from...' logs below")
    print("=" * 60)

    # Do a retrieval that should trigger branch tracking
    memories = memory.recall(state, "Tell me about Kay and continuity", num_memories=15)

    print("=" * 60)
    print()
    print(f"[TEST] Retrieved {len(memories)} memories")
    print()

    # Count how many have doc_id
    with_doc_id = [m for m in memories if m.get('doc_id')]
    print(f"[TEST] Memories with doc_id: {len(with_doc_id)}")

    if with_doc_id:
        print("[TEST] Examples:")
        for i, m in enumerate(with_doc_id[:3]):
            print(f"  {i+1}. doc_id={m.get('doc_id')}, chunk_index={m.get('chunk_index')}")
            print(f"     text: {m.get('text', m.get('fact', ''))[:60]}...")

    print()
    print("=" * 60)
    print("RESULTS:")
    print("=" * 60)

    if with_doc_id:
        print(f"[SUCCESS] Found {len(with_doc_id)} memories with doc_id/chunk_index")
        print("[CHECK] Did you see '[MEMORY FOREST] Retrieved memories from' logs above?")
        print("[CHECK] If yes: Phase 2A is COMPLETE!")
        print("[CHECK] If no: Branch tracking code may need debugging")
    else:
        print("[INFO] No memories with doc_id were retrieved")
        print("[INFO] This is expected if query doesn't match imported documents")
        print("[INFO] Try a different query that matches test_branch_metadata content")

    print()

if __name__ == "__main__":
    test_final_phase2a()
