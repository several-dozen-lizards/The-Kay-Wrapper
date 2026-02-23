"""
Test Fix #7: Glyph Filter RECENT_TURNS Decision Logic

Tests that the glyph filter correctly recognizes queries that need recent context.
"""

import subprocess
import time

def run_conversation_test(inputs, test_name):
    """Run a conversation and capture output."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}\n")

    # Join inputs with newlines and add quit
    full_input = "\n".join(inputs) + "\nquit\n"

    # Run main.py
    process = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )

    stdout, stderr = process.communicate(input=full_input, timeout=120)

    print("CONVERSATION:")
    for i, inp in enumerate(inputs, 1):
        print(f"  Turn {i}: {inp}")

    print("\n" + "="*80)
    print("CHECKING LOGS...")
    print("="*80 + "\n")

    return stdout, stderr


def check_recent_turns_value(stdout, expected_value, turn_query):
    """Check if RECENT_TURNS value is correct."""
    # Look for the log line: [RECENT TURNS] Filter LLM requested N recent conversation turns
    import re

    # Find all RECENT_TURNS values
    pattern = r'\[RECENT TURNS\] Filter LLM requested (\d+) recent'
    matches = re.findall(pattern, stdout)

    if not matches:
        # Also check for "determined no recent conversation context needed"
        if "determined no recent conversation context needed" in stdout:
            actual_value = 0
        else:
            print(f"❌ FAIL: Could not find RECENT_TURNS value in logs")
            return False
    else:
        # Get the last RECENT_TURNS value (for the query we're testing)
        actual_value = int(matches[-1])

    print(f"Query: \"{turn_query}\"")
    print(f"Expected RECENT_TURNS: {expected_value}")
    print(f"Actual RECENT_TURNS: {actual_value}")

    if actual_value == expected_value:
        print(f"✅ PASS: RECENT_TURNS value is correct\n")
        return True
    else:
        print(f"❌ FAIL: Expected {expected_value}, got {actual_value}\n")
        return False


def main():
    print("\n" + "="*80)
    print("FIX #7: RECENT_TURNS DECISION LOGIC TEST SUITE")
    print("="*80)
    print("\nTesting glyph filter's ability to recognize queries needing recent context")
    print("\n" + "="*80 + "\n")

    results = {}

    # TEST 1: "What did I say..." pattern
    print("\n" + "="*80)
    print("TEST 1: 'What did I say...' pattern")
    print("="*80)

    stdout_1, stderr_1 = run_conversation_test(
        [
            "My favorite color is green",
            "What did I say my favorite color is?"
        ],
        "Explicit recent reference with 'What did I say'"
    )

    results[1] = check_recent_turns_value(
        stdout_1,
        expected_value=5,
        turn_query="What did I say my favorite color is?"
    )

    time.sleep(2)

    # TEST 2: "What else?" pattern
    print("\n" + "="*80)
    print("TEST 2: 'What else?' pattern")
    print("="*80)

    stdout_2, stderr_2 = run_conversation_test(
        [
            "Tell me about dragons",
            "What else?"
        ],
        "Follow-up question with 'What else?'"
    )

    results[2] = check_recent_turns_value(
        stdout_2,
        expected_value=3,
        turn_query="What else?"
    )

    time.sleep(2)

    # TEST 3: Pure factual query (should be 0)
    print("\n" + "="*80)
    print("TEST 3: Pure factual query")
    print("="*80)

    stdout_3, stderr_3 = run_conversation_test(
        [
            "What are the pigeon names?"
        ],
        "Factual query with clear subject"
    )

    results[3] = check_recent_turns_value(
        stdout_3,
        expected_value=0,
        turn_query="What are the pigeon names?"
    )

    time.sleep(2)

    # TEST 4: Pronoun without antecedent
    print("\n" + "="*80)
    print("TEST 4: Pronoun without clear referent")
    print("="*80)

    stdout_4, stderr_4 = run_conversation_test(
        [
            "Tell me about Saga",
            "What color is she?"
        ],
        "Pronoun query requiring context"
    )

    results[4] = check_recent_turns_value(
        stdout_4,
        expected_value=5,  # Should be 3-5
        turn_query="What color is she?"
    )

    time.sleep(2)

    # FINAL SUMMARY
    print("\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80 + "\n")

    test_names = {
        1: "'What did I say...' pattern",
        2: "'What else?' pattern",
        3: "Pure factual query (should be 0)",
        4: "Pronoun without clear referent"
    }

    for test_num, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"Test {test_num} ({test_names[test_num]}): {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Glyph filter correctly recognizes queries needing recent context.")
    else:
        print("\n⚠️  Some tests failed. The glyph filter may need further tuning.")

    print("\n" + "="*80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
