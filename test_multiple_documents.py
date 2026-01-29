"""
Test script to verify Kay can remember MULTIPLE imported documents simultaneously.

BEFORE FIX:
- Import pigeons.txt -> Kay remembers pigeons [OK]
- Import dragons.txt -> Pigeons VANISH [FAIL]
- Kay can only hold ONE document at a time

AFTER FIX:
- Import pigeons.txt -> Kay remembers pigeons [OK]
- Import dragons.txt -> Kay remembers BOTH [OK]
- Older documents decay naturally but remain accessible
"""

import json
import os
from engines.memory_engine import MemoryEngine
from engines.identity_memory import IdentityMemory
from agent_state import AgentState

def test_multiple_documents():
    """Test that Kay can access multiple imported documents."""

    print("\n" + "="*80)
    print("TEST: Multiple Document Memory")
    print("="*80 + "\n")

    # Initialize memory system
    identity = IdentityMemory()
    memory_engine = MemoryEngine(identity)

    # Create minimal agent state
    agent_state = AgentState()
    agent_state.current_turn = 0
    agent_state.emotional_cocktail = {}

    # === DOCUMENT 1: Pigeons ===
    print("[IMPORT 1] Adding pigeons document...")
    pigeon_facts = [
        {"fact": "Gimpy is a pigeon with a twisted foot", "doc_id": "doc_pigeons_001", "is_imported": True, "turn_index": 0, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
        {"fact": "Bob is a pigeon who steals food from Gimpy", "doc_id": "doc_pigeons_001", "is_imported": True, "turn_index": 0, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
        {"fact": "Fork is a pigeon who shares food with Gimpy", "doc_id": "doc_pigeons_001", "is_imported": True, "turn_index": 0, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
        {"fact": "Zebra is a pigeon with black and white stripes", "doc_id": "doc_pigeons_001", "is_imported": True, "turn_index": 0, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
    ]

    # Add directly to memory layers (simulates import)
    for fact in pigeon_facts:
        memory_engine.memory_layers.working_memory.append(fact)

    agent_state.current_turn = 1
    print(f"   Imported {len(pigeon_facts)} pigeon facts\n")

    # === DOCUMENT 2: Dragons ===
    print("[IMPORT 2] Adding dragons document...")
    dragon_facts = [
        {"fact": "Dragons hoard treasure in mountain caves", "doc_id": "doc_dragons_002", "is_imported": True, "turn_index": 1, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
        {"fact": "Dragons breathe fire to defend their territory", "doc_id": "doc_dragons_002", "is_imported": True, "turn_index": 1, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
        {"fact": "Ancient dragons can live for thousands of years", "doc_id": "doc_dragons_002", "is_imported": True, "turn_index": 1, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
        {"fact": "Dragon scales are nearly impenetrable armor", "doc_id": "doc_dragons_002", "is_imported": True, "turn_index": 1, "type": "extracted_fact", "importance_score": 0.7, "current_layer": "working"},
    ]

    # Add directly to memory layers (simulates import)
    for fact in dragon_facts:
        memory_engine.memory_layers.working_memory.append(fact)

    agent_state.current_turn = 2
    print(f"   Imported {len(dragon_facts)} dragon facts\n")

    # === TEST 1: Query about PIGEONS (older document) ===
    print("[TEST 1] Querying about pigeons (older document)...")
    pigeon_query = "Tell me about the pigeons you know"
    retrieved_pigeons = memory_engine.recall(
        agent_state=agent_state,
        user_input=pigeon_query,
        bias_cocktail={},
        num_memories=100
    )

    pigeon_docs = [m for m in retrieved_pigeons if m.get('doc_id') == 'doc_pigeons_001']
    print(f"   Retrieved {len(pigeon_docs)}/{len(pigeon_facts)} pigeon facts")

    if len(pigeon_docs) > 0:
        print("  Sample pigeon facts:")
        for mem in pigeon_docs[:2]:
            print(f"    - {mem.get('fact', '')[:60]}...")
        print()

    # === TEST 2: Query about DRAGONS (newer document) ===
    print("[TEST 2] Querying about dragons (newer document)...")
    dragon_query = "Tell me about dragons"
    retrieved_dragons = memory_engine.recall(
        agent_state=agent_state,
        user_input=dragon_query,
        bias_cocktail={},
        num_memories=100
    )

    dragon_docs = [m for m in retrieved_dragons if m.get('doc_id') == 'doc_dragons_002']
    print(f"   Retrieved {len(dragon_docs)}/{len(dragon_facts)} dragon facts")

    if len(dragon_docs) > 0:
        print("  Sample dragon facts:")
        for mem in dragon_docs[:2]:
            print(f"    - {mem.get('fact', '')[:60]}...")
        print()

    # === TEST 3: Query about BOTH (comprehensive recall) ===
    print("[TEST 3] Querying about both documents...")
    both_query = "Tell me everything you remember from the documents"
    retrieved_both = memory_engine.recall(
        agent_state=agent_state,
        user_input=both_query,
        bias_cocktail={},
        num_memories=200
    )

    pigeon_docs_both = [m for m in retrieved_both if m.get('doc_id') == 'doc_pigeons_001']
    dragon_docs_both = [m for m in retrieved_both if m.get('doc_id') == 'doc_dragons_002']

    print(f"   Retrieved {len(pigeon_docs_both)} pigeon facts + {len(dragon_docs_both)} dragon facts")
    print(f"  Total: {len(pigeon_docs_both) + len(dragon_docs_both)}/{len(pigeon_facts) + len(dragon_facts)} facts\n")

    # === RESULTS ===
    print("="*80)
    print("RESULTS:")
    print("="*80)

    success = True

    # Check 1: Can retrieve pigeons
    if len(pigeon_docs) >= len(pigeon_facts) * 0.75:  # 75% threshold
        print(f"[PASS] Pigeon recall ({len(pigeon_docs)}/{len(pigeon_facts)})")
    else:
        print(f"[FAIL] Pigeon recall ({len(pigeon_docs)}/{len(pigeon_facts)}) - older document forgotten!")
        success = False

    # Check 2: Can retrieve dragons
    if len(dragon_docs) >= len(dragon_facts) * 0.75:
        print(f"[PASS] Dragon recall ({len(dragon_docs)}/{len(dragon_facts)})")
    else:
        print(f"[FAIL] Dragon recall ({len(dragon_docs)}/{len(dragon_facts)}) - newer document incomplete!")
        success = False

    # Check 3: Can retrieve BOTH simultaneously
    total_recalled = len(pigeon_docs_both) + len(dragon_docs_both)
    total_facts = len(pigeon_facts) + len(dragon_facts)
    if total_recalled >= total_facts * 0.75:
        print(f"[PASS] Simultaneous recall ({total_recalled}/{total_facts})")
    else:
        print(f"[FAIL] Simultaneous recall ({total_recalled}/{total_facts}) - documents interfering!")
        success = False

    print("\n" + "="*80)
    if success:
        print("[SUCCESS] ALL TESTS PASSED: Kay can remember multiple documents!")
        print("  - Older documents remain accessible (natural decay)")
        print("  - Newer documents don't erase older ones")
        print("  - Both can be recalled simultaneously")
    else:
        print("[FAILURE] TESTS FAILED: Kay still has memory cap issues")
        print("  - Check SLOT_ALLOCATION limits in memory_engine.py")
        print("  - Check recency decay formula")
    print("="*80 + "\n")

    return success

if __name__ == "__main__":
    try:
        success = test_multiple_documents()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
