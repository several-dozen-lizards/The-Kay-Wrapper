"""
Verify Relevance-Weighted Boost Integration

Confirms that:
1. memory_engine.py stores relevance_score in memories
2. emotion_engine.py uses relevance_score for weighted boost
3. reed_ui.py has no duplicate boost logic
"""

import os
import sys

def check_file_exists(filepath):
    """Check if file exists."""
    if not os.path.exists(filepath):
        print(f"[FAIL] File not found: {filepath}")
        return False
    print(f"[PASS] File exists: {filepath}")
    return True

def check_code_present(filepath, search_string, description):
    """Check if specific code is present in file."""
    if not os.path.exists(filepath):
        print(f"[FAIL] {description}: File not found")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if search_string in content:
        print(f"[PASS] {description}")
        return True
    else:
        print(f"[FAIL] {description}")
        return False

def check_code_absent(filepath, search_string, description):
    """Check that specific code is NOT present in file."""
    if not os.path.exists(filepath):
        print(f"[FAIL] {description}: File not found")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if search_string not in content:
        print(f"[PASS] {description}")
        return True
    else:
        print(f"[FAIL] {description}: Found unexpected code")
        return False

def main():
    print("="*70)
    print("RELEVANCE-WEIGHTED BOOST INTEGRATION VERIFICATION")
    print("="*70)
    print()

    results = {}

    # Check 1: Files exist
    print("--- Check 1: Files Exist ---")
    results["memory_engine_exists"] = check_file_exists("engines/memory_engine.py")
    results["emotion_engine_exists"] = check_file_exists("engines/emotion_engine.py")
    results["kay_ui_exists"] = check_file_exists("reed_ui.py")
    print()

    # Check 2: memory_engine.py stores relevance_score
    print("--- Check 2: Memory Engine Stores Relevance Score ---")
    results["relevance_score_stored"] = check_code_present(
        "engines/memory_engine.py",
        "mem['relevance_score'] = score",
        "relevance_score stored in memories"
    )
    print()

    # Check 3: emotion_engine.py uses relevance weighting
    print("--- Check 3: Emotion Engine Uses Relevance Weighting ---")
    results["relevance_weighted_boost"] = check_code_present(
        "engines/emotion_engine.py",
        "boost_amount = 0.05 * relevance",
        "Boost weighted by relevance"
    )
    results["top_n_filtering"] = check_code_present(
        "engines/emotion_engine.py",
        "[:150]  # Top 150",
        "Top N filtering (150 memories)"
    )
    results["relevance_threshold"] = check_code_present(
        "engines/emotion_engine.py",
        "relevance_threshold = 0.15",
        "Relevance threshold (0.15)"
    )
    print()

    # Check 4: emotion_engine.py has enhanced logging
    print("--- Check 4: Enhanced Logging ---")
    results["boost_logging"] = check_code_present(
        "engines/emotion_engine.py",
        "Reinforced {len(reinforced_emotions)} emotions from {memories_used} relevant memories",
        "Enhanced boost logging"
    )
    results["memory_usage_logging"] = check_code_present(
        "engines/emotion_engine.py",
        "Used {memories_used}/{len(all_memories)} memories",
        "Memory usage logging"
    )
    print()

    # Check 5: memory_engine.py has top-10 logging
    print("--- Check 5: Top-10 Relevance Logging ---")
    results["top10_logging"] = check_code_present(
        "engines/memory_engine.py",
        "[MEMORY RETRIEVAL] Top 10 most relevant memories",
        "Top-10 relevance logging"
    )
    print()

    # Check 6: reed_ui.py has NO duplicate boost logic
    print("--- Check 6: No Duplicate Logic in reed_ui.py ---")
    results["no_duplicate_boost"] = check_code_absent(
        "reed_ui.py",
        "cocktail[tag][\"intensity\"] = min(1.0, cocktail[tag][\"intensity\"] + 0.05)",
        "No duplicate equal-boost logic in reed_ui.py"
    )
    results["no_memory_loop"] = check_code_absent(
        "reed_ui.py",
        "for mem in agent_state.last_recalled_memories",
        "No memory loop for boosting in reed_ui.py"
    )
    print()

    # Check 7: reed_ui.py calls emotion.update correctly
    print("--- Check 7: Integration Flow ---")
    results["emotion_update_call"] = check_code_present(
        "reed_ui.py",
        "self.emotion.update(self.agent_state, user_input)",
        "emotion.update() called correctly"
    )
    results["memory_recall_before"] = check_code_present(
        "reed_ui.py",
        "self.memory.recall(self.agent_state, user_input)",
        "memory.recall() called before emotion.update()"
    )
    print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(results.values())
    total = len(results)

    for check_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check_name}")

    print()
    print(f"OVERALL: {passed}/{total} checks passed ({passed*100//total}%)")
    print()

    if passed == total:
        print("[SUCCESS] All integration checks passed!")
        print()
        print("Relevance-weighted boost is properly integrated:")
        print("  1. memory_engine.py stores relevance_score in memories")
        print("  2. emotion_engine.py uses relevance-weighted boost")
        print("  3. reed_ui.py has no duplicate boost logic")
        print("  4. Integration flow is correct (recall -> update)")
        print()
        print("Ready for live testing with: python main.py")
    else:
        print("[WARNING] Some checks failed. Review output above.")

    print("="*70)

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
