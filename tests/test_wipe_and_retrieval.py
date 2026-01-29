"""
End-to-end test for memory wipe and imported fact retrieval.

Tests:
1. Wipe memory completely
2. Verify all files are empty
3. Import document facts
4. Query for imported content
5. Verify facts are retrieved
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os
from datetime import datetime

from engines.memory_engine import MemoryEngine
from agent_state import AgentState
from aggressive_wipe import aggressive_wipe


def verify_empty_memory():
    """Verify all memory files are empty after wipe."""
    print("\n" + "="*70)
    print("VERIFICATION: Memory files are empty")
    print("="*70)

    checks = []

    # Check memories.json
    with open("memory/memories.json", "r") as f:
        memories = json.load(f)
        is_empty = len(memories) == 0
        checks.append(("memories.json", is_empty, len(memories)))
        print(f"  memories.json: {'[OK]' if is_empty else '[FAIL]'} ({len(memories)} items)")

    # Check memory_layers.json
    with open("memory/memory_layers.json", "r") as f:
        layers = json.load(f)
        total = len(layers.get("working", [])) + len(layers.get("episodic", [])) + len(layers.get("semantic", []))
        is_empty = total == 0
        checks.append(("memory_layers.json", is_empty, total))
        print(f"  memory_layers.json: {'[OK]' if is_empty else '[FAIL]'} ({total} total across layers)")

    # Check entity_graph.json
    with open("memory/entity_graph.json", "r") as f:
        entities = json.load(f)
        count = len(entities.get("entities", {}))
        is_empty = count == 0
        checks.append(("entity_graph.json", is_empty, count))
        print(f"  entity_graph.json: {'[OK]' if is_empty else '[FAIL]'} ({count} entities)")

    # Check identity_memory.json
    with open("memory/identity_memory.json", "r") as f:
        identity = json.load(f)
        re_count = len(identity.get("re", []))
        kay_count = len(identity.get("kay", []))
        entity_count = len(identity.get("entities", {}))
        total = re_count + kay_count + entity_count
        is_empty = total == 0
        checks.append(("identity_memory.json", is_empty, total))
        print(f"  identity_memory.json: {'[OK]' if is_empty else '[FAIL]'} ({total} total facts)")

    all_empty = all(check[1] for check in checks)

    if all_empty:
        print("\n[SUCCESS] All memory files are empty!")
        return True
    else:
        print("\n[FAILURE] Some files still contain data!")
        return False


def import_test_document(memory_engine):
    """Import test document with specific facts."""
    print("\n" + "="*70)
    print("IMPORT: Test document with facts")
    print("="*70)

    # Test facts about different topics
    test_facts = [
        "The sky is blue on clear days",
        "Grass is green because of chlorophyll",
        "Water freezes at zero degrees Celsius",
        "The Earth orbits around the Sun",
        "Python is a programming language created by Guido van Rossum"
    ]

    print(f"\nImporting {len(test_facts)} facts:")
    for fact in test_facts:
        print(f"  - {fact}")

    # Import each fact with is_imported flag
    for fact in test_facts:
        memory = {
            "fact": fact,
            "user_input": fact,
            "response": "",
            "type": "extracted_fact",
            "perspective": "shared",
            "topic": "imported_knowledge",
            "entities": [],
            "emotion_tags": [],
            "emotional_cocktail": {},
            "importance_score": 0.8,
            "turn_index": memory_engine.current_turn,
            "is_imported": True,  # CRITICAL: Mark as imported
            "added_timestamp": datetime.now().isoformat(),
            "access_count": 0,
            "last_accessed": datetime.now().isoformat(),
            "current_strength": 1.0,
            "current_layer": "working"
        }

        memory_engine.memories.append(memory)
        memory_engine.memory_layers.add_memory(memory, layer="working")

    # Save to disk
    memory_engine._save_to_disk()
    memory_engine.memory_layers._save_to_disk()

    print(f"\n[SUCCESS] Imported {len(test_facts)} facts with is_imported=True")
    print(f"[INFO] Current turn: {memory_engine.current_turn}")
    return test_facts


def test_retrieval(memory_engine, agent_state):
    """Test retrieval of imported facts."""
    print("\n" + "="*70)
    print("RETRIEVAL: Query for imported content")
    print("="*70)

    # Test queries
    queries = [
        "What's in what I just imported?",
        "What do you remember from the new document?",
        "Tell me about the recently imported facts",
        "What did I just tell you?",
        "sky blue"  # Direct keyword query
    ]

    results = []

    for query in queries:
        print(f"\n--- Query: '{query}' ---")

        # Perform retrieval
        retrieved = memory_engine.recall(
            agent_state=agent_state,
            user_input=query,
            num_memories=10,
            use_multi_factor=True
        )

        # Check if any imported facts were retrieved
        if retrieved is None:
            retrieved = []
        imported_facts = [m for m in retrieved if m.get("is_imported", False)]

        print(f"Retrieved {len(retrieved)} total memories")
        print(f"  - {len(imported_facts)} are imported facts")

        if imported_facts:
            print("  [SUCCESS] Imported facts retrieved:")
            for fact in imported_facts[:3]:  # Show first 3
                print(f"    • {fact.get('fact', 'N/A')[:60]}")
        else:
            print("  [FAILURE] No imported facts retrieved")
            if retrieved:
                print("  Retrieved instead:")
                for mem in retrieved[:3]:
                    print(f"    • {mem.get('fact', mem.get('user_input', 'N/A'))[:60]}")

        results.append({
            "query": query,
            "success": len(imported_facts) > 0,
            "imported_count": len(imported_facts),
            "total_count": len(retrieved)
        })

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    success_count = sum(1 for r in results if r["success"])
    print(f"Successful queries: {success_count}/{len(results)}")
    for r in results:
        status = "[OK]" if r["success"] else "[FAIL]"
        print(f"  {status} '{r['query'][:50]}...' -> {r['imported_count']}/{r['total_count']} imported")

    return results


def main():
    print("="*70)
    print("MEMORY WIPE AND RETRIEVAL TEST")
    print("="*70)

    # STEP 1: Wipe memory
    print("\n[STEP 1] Wiping memory...")
    backup_dir = aggressive_wipe()

    # STEP 2: Verify wipe
    print("\n[STEP 2] Verifying wipe...")
    if not verify_empty_memory():
        print("\n[ABORT] Wipe verification failed - cannot continue test")
        return

    # STEP 3: Initialize fresh memory engine
    print("\n[STEP 3] Initializing fresh memory engine...")
    memory_engine = MemoryEngine()
    agent_state = AgentState()
    print(f"  Memory engine initialized with {len(memory_engine.memories)} memories")
    print(f"  Current turn: {memory_engine.current_turn}")

    # STEP 4: Import test document
    print("\n[STEP 4] Importing test document...")
    test_facts = import_test_document(memory_engine)

    # Verify import
    print(f"\n[VERIFY] Memory engine now has {len(memory_engine.memories)} memories")
    imported_count = sum(1 for m in memory_engine.memories if m.get("is_imported", False))
    print(f"  - {imported_count} are marked as imported")

    # STEP 5: Test retrieval
    print("\n[STEP 5] Testing retrieval...")
    results = test_retrieval(memory_engine, agent_state)

    # Final verdict
    print("\n" + "="*70)
    print("FINAL VERDICT")
    print("="*70)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    if success_count == total_count:
        print(f"[SUCCESS] All {total_count} retrieval queries returned imported facts")
        print("Memory wipe and retrieval system working correctly!")
    elif success_count > 0:
        print(f"[PARTIAL] {success_count}/{total_count} retrieval queries succeeded")
        print("Some import queries work, but not all patterns detected")
    else:
        print(f"[FAILURE] {success_count}/{total_count} retrieval queries succeeded")
        print("Imported facts are not being retrieved - retrieval system broken")

    print(f"\nBackup saved to: {backup_dir}")


if __name__ == "__main__":
    main()
