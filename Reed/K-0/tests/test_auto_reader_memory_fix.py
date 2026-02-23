"""
Test script to verify auto-reader memory fixes.

Validates:
1. Memory storage works (correct parameter name)
2. Memory recall happens before each segment (not zero memories)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_state import AgentState
from engines.document_reader import DocumentReader
from engines.memory_engine import MemoryEngine
from engines.auto_reader import AutoReader


def test_memory_fixes():
    """Test both memory fixes."""

    print("="*70)
    print("AUTO READER MEMORY FIX TEST")
    print("="*70)

    # Create sample document
    sample_doc = """
    First segment of test document. Kay should have memories when reading this.
    His identity facts should be accessible. His relationship with Re should be
    in context. His core memories about pigeons should be available.

    Second segment continues the narrative. Reed's previous response to segment 1
    should now be in his recent memory. This creates continuity across segments
    and prevents computational drift.

    Third segment wraps up. All of Reed's responses should be stored properly,
    creating a coherent reading experience where each segment builds on previous ones.
    """.strip()

    print(f"\nTest document: {len(sample_doc)} characters\n")

    # Create agent state with some test memories
    state = AgentState()
    state.emotional_cocktail = {
        'curious': {'intensity': 0.6, 'age': 0},
        'focused': {'intensity': 0.4, 'age': 0}
    }

    # Create memory engine
    memory = MemoryEngine(state.memory)

    # Add some test identity memories
    print("[SETUP] Adding test identity memories...")
    test_memories = [
        {"fact": "Kay is a conversational AI with emotional awareness", "perspective": "kay", "importance": 0.9},
        {"fact": "Re is Kay's creator and collaborator", "perspective": "user", "importance": 0.9},
        {"fact": "Kay has a dry sense of humor", "perspective": "kay", "importance": 0.8},
    ]

    for mem in test_memories:
        memory.memories.append(mem)

    print(f"[SETUP] Added {len(test_memories)} test memories")

    # Create document reader
    doc_reader = DocumentReader(chunk_size=200)
    load_success = doc_reader.load_document(sample_doc, "test_doc.txt", "test_id")
    num_chunks = doc_reader.total_chunks

    print(f"[SETUP] DocumentReader: {num_chunks} chunks\n")

    # Track what happens
    memory_recalls = []
    memory_stores = []
    responses = []

    # Create mock LLM wrapper that simulates the real wrapper behavior
    def mock_llm_wrapper(prompt, agent_state):
        """
        Mock LLM wrapper that simulates the actual wrapper in main.py/reed_ui.py.
        This MUST call memory.recall() first, just like the real wrapper does.
        """
        # CRITICAL: Recall memories for this segment (simulating the wrapper fix)
        memory.recall(agent_state, prompt)

        # Check if memories were recalled
        recalled = getattr(agent_state, 'last_recalled_memories', [])
        memory_recalls.append(len(recalled))

        print(f"[LLM CALL] Memories recalled: {len(recalled)}")

        # Generate mock response
        segment_num = len(responses) + 1
        response = f"Mock response #{segment_num}: Reading with {len(recalled)} memories available."
        responses.append(response)
        return response

    # Create mock display
    def mock_display(role, message):
        """Silent display."""
        pass

    # Create AutoReader with memory engine
    auto_reader = AutoReader(
        get_llm_response_func=mock_llm_wrapper,
        add_message_func=mock_display,
        memory_engine=memory
    )

    print("="*70)
    print("TESTING MEMORY FIXES")
    print("="*70)

    # Test: Run auto-reader and check for errors
    print("\n[TEST 1] Memory storage parameter fix...")
    try:
        result = auto_reader.read_document_sync(
            doc_reader=doc_reader,
            doc_name="test_doc.txt",
            agent_state=state,
            start_segment=1
        )

        if result['errors']:
            print(f"[FAIL] Errors during reading:")
            for error in result['errors']:
                print(f"  - {error}")
            return False
        else:
            print("[PASS] No storage errors - parameter fix working")

    except Exception as e:
        print(f"[FAIL] Exception during reading: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test: Check if memory recall happened
    print(f"\n[TEST 2] Memory recall before each segment...")
    print(f"  Segments processed: {len(memory_recalls)}")
    print(f"  Memories per segment: {memory_recalls}")

    if all(count == 0 for count in memory_recalls):
        print("[FAIL] Zero memories for all segments - recall not working")
        return False
    elif any(count == 0 for count in memory_recalls):
        print("[WARN] Some segments had zero memories")
        print(f"  Zero count: {memory_recalls.count(0)}/{len(memory_recalls)}")
    else:
        print(f"[PASS] All segments had memories - recall working")

    # Test: Verify responses were stored
    print(f"\n[TEST 3] Response storage...")
    # Look for the pattern that auto_reader uses: "[Reading doc_name, section N/total]"
    stored_count = len([m for m in memory.memories if '[Reading test_doc.txt' in m.get('fact', m.get('user_input', ''))])
    print(f"  Reading turns stored: {stored_count}/{num_chunks}")

    if stored_count == num_chunks:
        print("[PASS] All responses stored correctly")
    elif stored_count > 0:
        print(f"[WARN] Only {stored_count}/{num_chunks} responses stored")
    else:
        print("[FAIL] No responses stored")
        return False

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    all_passed = (
        len(result['errors']) == 0 and
        not all(count == 0 for count in memory_recalls) and
        stored_count > 0
    )

    if all_passed:
        print("[PASS] All critical tests passed")
        print("  - Memory storage parameter fixed")
        print("  - Memory recall working")
        print("  - Responses being stored")
    else:
        print("[FAIL] Some tests failed - see details above")

    print("="*70)

    return all_passed


if __name__ == "__main__":
    try:
        success = test_memory_fixes()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[CRASH] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
