"""
Memory Architecture Verification Tests

Tests that Reed's memory system is working correctly:
1. Recent fact retention (working memory)
2. Imported document access (import boost)
3. Identity facts persistence (identity memory)

Run this after fixing caching to ensure memory retrieval is working.
"""

import json
import os


def test_recent_fact_retention():
    """
    Test that Kay remembers facts from current conversation.

    Scenario:
    - User: "My dog's name is Saga and she's orange."
    - Kay: [acknowledges]
    - User: "What color is Saga?"
    - Kay: Should say "orange" from working memory
    """
    print("\n" + "="*70)
    print("TEST 1: RECENT FACT RETENTION (Working Memory)")
    print("="*70)

    print("\nTest Scenario:")
    print("  User Turn 1: 'My dog's name is Saga and she's orange.'")
    print("  User Turn 2: 'What color is Saga?'")
    print("  Expected: Kay should answer 'orange' from working memory")

    print("\nVerification Points:")
    print("  - [ ] Fact extracted: 'Saga is orange' (perspective: user)")
    print("  - [ ] Fact stored in working memory layer")
    print("  - [ ] Fact retrieved on turn 2 with high score")
    print("  - [ ] Kay's response includes 'orange'")
    print("  - [ ] No fragmentation after 3 exchanges")

    print("\nExpected Logs:")
    print("  [FACT EXTRACTION] Extracted: 'Re's dog Saga is orange'")
    print("  [MEMORY] Added to working layer")
    print("  [RECALL] Retrieved 1 memories with 'Saga'")
    print("  [LLM Response] Mentions 'orange'")

    print("\n[ACTION REQUIRED] Run this conversation manually and verify")
    return "MANUAL_TEST_REQUIRED"


def test_import_boost():
    """
    Test that imported documents are prioritized in retrieval.

    Scenario:
    - Import document with pigeon names: Gimpy, Bob, Fork, Zebra
    - User: "I uploaded a document with pigeon names. Can you list them?"
    - Kay: Should list all pigeon names from imported doc
    """
    print("\n" + "="*70)
    print("TEST 2: IMPORT BOOST (Document Priority)")
    print("="*70)

    print("\nTest Scenario:")
    print("  1. Import document containing pigeon names")
    print("  2. User asks: 'List the pigeon names from the document'")
    print("  3. Expected: Kay lists Gimpy, Bob, Fork, Zebra, etc.")

    print("\nVerification Points:")
    print("  - [ ] Import completed successfully")
    print("  - [ ] Pigeon names stored in memory layers")
    print("  - [ ] Import boost fires: '[RETRIEVAL] Boosted N recent imported facts'")
    print("  - [ ] All pigeon names retrieved correctly")
    print("  - [ ] Kay's response includes all names")

    print("\nExpected Logs:")
    print("  [IMPORT] Imported 15 chunks from pigeon_document.txt")
    print("  [RETRIEVAL] Import boost: +0.5 to 8 recently imported facts")
    print("  [RECALL] Retrieved 8 memories with import boost")
    print("  [LLM Response] Lists: Gimpy, Bob, Fork, Zebra, etc.")

    print("\n[ACTION REQUIRED] Import test document and verify")
    return "MANUAL_TEST_REQUIRED"


def test_identity_persistence():
    """
    Test that identity facts remain consistent across turns.

    Scenario:
    - User: "What color are your eyes?"
    - Kay: "Gold" (from identity memory)
    - [5 turns later]
    - User: "What color are your eyes again?"
    - Kay: Should still say "gold" (no contradiction)
    """
    print("\n" + "="*70)
    print("TEST 3: IDENTITY PERSISTENCE (Identity Memory)")
    print("="*70)

    print("\nTest Scenario:")
    print("  User Turn 1: 'What color are your eyes?'")
    print("  Kay: 'Gold' (from identity memory)")
    print("  [5 conversation turns pass]")
    print("  User Turn 7: 'What color are your eyes again?'")
    print("  Kay: Should still say 'gold'")

    print("\nVerification Points:")
    print("  - [ ] Identity facts bypass scoring")
    print("  - [ ] '[RETRIEVAL] Including ALL N identity facts' logged")
    print("  - [ ] Consistent answer across multiple turns")
    print("  - [ ] No contradiction between turns")
    print("  - [ ] Identity fact not decayed or lost")

    print("\nExpected Logs:")
    print("  [IDENTITY] Loaded 25 identity facts")
    print("  [RETRIEVAL] Including ALL 25 identity facts (bypass scoring)")
    print("  [RECALL] Identity fact: 'Kay's eyes are gold'")
    print("  [LLM Response] Turn 1: 'gold'")
    print("  [LLM Response] Turn 7: 'gold' (consistent)")

    print("\n[ACTION REQUIRED] Run conversation and verify consistency")
    return "MANUAL_TEST_REQUIRED"


def check_memory_files():
    """Check if memory files exist and have valid structure."""
    print("\n" + "="*70)
    print("MEMORY FILE INTEGRITY CHECK")
    print("="*70)

    files_to_check = [
        "memory/memories.json",
        "memory/memory_layers.json",
        "memory/entity_graph.json",
        "memory/preferences.json",
        "memory/identity_memory.json"
    ]

    all_valid = True

    for file_path in files_to_check:
        full_path = os.path.join("F:\\AlphaKayZero", file_path)
        if not os.path.exists(full_path):
            print(f"  [MISSING] {file_path}")
            all_valid = False
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if file_path == "memory/memories.json":
                print(f"  [OK] {file_path} - {len(data)} memories")
            elif file_path == "memory/memory_layers.json":
                layers = data.get('layers', {})
                working = len(layers.get('working', []))
                episodic = len(layers.get('episodic', []))
                semantic = len(layers.get('semantic', []))
                print(f"  [OK] {file_path} - W:{working} E:{episodic} S:{semantic}")
            elif file_path == "memory/entity_graph.json":
                entities = len(data.get('entities', {}))
                print(f"  [OK] {file_path} - {entities} entities")
            elif file_path == "memory/preferences.json":
                domains = len(data.get('preferences', {}))
                print(f"  [OK] {file_path} - {domains} domains")
            elif file_path == "memory/identity_memory.json":
                facts = len(data.get('facts', []))
                print(f"  [OK] {file_path} - {facts} identity facts")

        except json.JSONDecodeError as e:
            print(f"  [ERROR] {file_path} - Invalid JSON: {e}")
            all_valid = False
        except Exception as e:
            print(f"  [ERROR] {file_path} - {e}")
            all_valid = False

    return "PASS" if all_valid else "FAIL"


def verify_retrieval_logs():
    """Check what logs to watch for during memory retrieval."""
    print("\n" + "="*70)
    print("MEMORY RETRIEVAL LOG VERIFICATION GUIDE")
    print("="*70)

    print("\nLogs to Watch During Conversation:")
    print("-" * 70)

    print("\n1. SEMANTIC USAGE (every turn)")
    print("   Pattern: [SEMANTIC USAGE] Memory composition:")
    print("   Expected:")
    print("     - Semantic layer: X (Y%)")
    print("     - Episodic layer: X (Y%)")
    print("     - Working layer: X (Y%)")
    print("     - Imported semantic facts: N")
    print("     - Imported emotional narratives: N")

    print("\n2. IDENTITY FACTS (when relevant)")
    print("   Pattern: [RETRIEVAL] Including ALL N identity facts")
    print("   Expected:")
    print("     - Identity facts bypass scoring")
    print("     - Always included in context")
    print("     - No decay or loss")

    print("\n3. IMPORT BOOST (after recent import)")
    print("   Pattern: [RETRIEVAL] Import boost: +X to N recently imported facts")
    print("   Expected:")
    print("     - Boost of +0.5 to recent imports")
    print("     - Decays over time")
    print("     - Helps prioritize imported content")

    print("\n4. ENTITY RESOLUTION")
    print("   Pattern: [ENTITY GRAPH] Resolved 'my dog' -> 'Saga'")
    print("   Expected:")
    print("     - Canonical entity resolution")
    print("     - Attribute tracking")
    print("     - Contradiction detection")

    print("\n5. MULTI-FACTOR RETRIEVAL")
    print("   Pattern: [RECALL] Retrieved N memories")
    print("   Expected:")
    print("     - Emotional resonance: 40%")
    print("     - Semantic similarity: 25%")
    print("     - Importance: 20%")
    print("     - Recency: 10%")
    print("     - Entity proximity: 5%")


if __name__ == "__main__":
    print("="*70)
    print("MEMORY ARCHITECTURE VERIFICATION TESTS")
    print("="*70)

    print("\nThese tests verify Kay's memory system is working correctly.")
    print("Run these AFTER fixing the caching issue to ensure full functionality.")

    # Check memory files first
    integrity_result = check_memory_files()

    # Run verification tests
    test1_result = test_recent_fact_retention()
    test2_result = test_import_boost()
    test3_result = test_identity_persistence()

    # Show log verification guide
    verify_retrieval_logs()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    print(f"\nMemory File Integrity: {integrity_result}")
    print(f"Test 1 (Recent Facts): {test1_result}")
    print(f"Test 2 (Import Boost): {test2_result}")
    print(f"Test 3 (Identity Persistence): {test3_result}")

    if integrity_result == "PASS":
        print("\n[OK] Memory files are valid and loaded")
    else:
        print("\n[ERROR] Memory file issues detected - fix before testing")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)

    print("\n1. Fix caching issue (see CACHING_FIX_IMPLEMENTATION_PLAN.md)")
    print("2. Run Kay and test each scenario manually")
    print("3. Watch console logs for expected patterns")
    print("4. Verify memory retrieval is working correctly")
    print("5. Document any issues found")

    print("\nFor each test:")
    print("  - Run the conversation scenario")
    print("  - Watch console logs for expected patterns")
    print("  - Verify Kay's response matches expectations")
    print("  - Check memory files for correct storage")
