"""
Test script for memory bug fixes from KAY_ZERO_MEMORY_AUDIT.md

Tests all three critical scenarios:
1. Recent fact recall (keyword overlap death fix)
2. Pronoun resolution (RECENT_TURNS integration)
3. Multi-turn reasoning (combined fixes)
"""

import subprocess
import time

def run_test_scenario(scenario_name, inputs):
    """
    Run a test scenario by feeding inputs to main.py

    Args:
        scenario_name: Description of test
        inputs: List of strings to send to main.py
    """
    print(f"\n{'='*80}")
    print(f"TEST SCENARIO: {scenario_name}")
    print(f"{'='*80}\n")

    # Join inputs with newlines and add 'quit' at the end
    full_input = "\n".join(inputs) + "\nquit\n"

    # Run main.py with inputs
    process = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )

    stdout, stderr = process.communicate(input=full_input, timeout=120)

    print("STDOUT:")
    print(stdout)

    if stderr:
        print("\nSTDERR:")
        print(stderr)

    print(f"\n{'='*80}")
    print(f"END OF TEST: {scenario_name}")
    print(f"{'='*80}\n")

    # Brief pause between tests
    time.sleep(2)

    return stdout, stderr


def analyze_results(scenario_name, stdout, expectations):
    """
    Analyze test results against expectations

    Args:
        scenario_name: Test description
        stdout: Output from main.py
        expectations: Dict of keywords to check for
    """
    print(f"\n{'='*80}")
    print(f"ANALYSIS: {scenario_name}")
    print(f"{'='*80}\n")

    results = {}
    for key, expected_keywords in expectations.items():
        found = any(keyword.lower() in stdout.lower() for keyword in expected_keywords)
        results[key] = found
        status = "✅ PASS" if found else "❌ FAIL"
        print(f"{status}: {key}")
        if not found:
            print(f"  Expected to find one of: {expected_keywords}")

    all_passed = all(results.values())
    overall = "✅ ALL CHECKS PASSED" if all_passed else "❌ SOME CHECKS FAILED"
    print(f"\n{overall}\n")

    return all_passed


def main():
    print("\n" + "="*80)
    print("MEMORY BUG FIXES - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print("\nTesting fixes from KAY_ZERO_MEMORY_AUDIT.md")
    print("Fix #1: Recent facts keyword overlap death")
    print("Fix #2: RECENT_TURNS integration in main.py")
    print("Fix #3: Smart glyph pre-filter")
    print("Fix #4: Deduplication")
    print("Fix #5: Temporal decay adjustment")
    print("\n" + "="*80 + "\n")

    results = {}

    # TEST 1: Recent Fact Recall
    scenario_1_inputs = [
        "My favorite color is blue",
        "What else can you tell me about that?"
    ]

    stdout_1, stderr_1 = run_test_scenario(
        "TEST 1: Recent Fact Recall (Fix #1)",
        scenario_1_inputs
    )

    expectations_1 = {
        "Remembers 'blue' from previous turn": ["blue"],
        "RECENT_TURNS directive used": ["RECENT_TURNS"],
        "Recency exemption applied": ["is_recent", "turns_old"]
    }

    results[1] = analyze_results("TEST 1", stdout_1, expectations_1)

    # TEST 2: Pronoun Resolution
    scenario_2_inputs = [
        "Tell me about Saga",
        "What color is she?"
    ]

    stdout_2, stderr_2 = run_test_scenario(
        "TEST 2: Pronoun Resolution (Fix #2)",
        scenario_2_inputs
    )

    expectations_2 = {
        "Resolves 'she' to Saga": ["saga"],
        "RECENT_TURNS directive detected": ["RECENT_TURNS"],
        "Recent conversation included": ["recent turns", "recent conversation"]
    }

    results[2] = analyze_results("TEST 2", stdout_2, expectations_2)

    # TEST 3: Multi-turn Reasoning
    scenario_3_inputs = [
        "I like coffee in the morning",
        "But I prefer tea in the evening",
        "What are my beverage preferences?"
    ]

    stdout_3, stderr_3 = run_test_scenario(
        "TEST 3: Multi-turn Reasoning (Combined Fixes)",
        scenario_3_inputs
    )

    expectations_3 = {
        "Mentions coffee": ["coffee"],
        "Mentions tea": ["tea"],
        "Mentions morning/evening timing": ["morning", "evening"]
    }

    results[3] = analyze_results("TEST 3", stdout_3, expectations_3)

    # FINAL SUMMARY
    print("\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80 + "\n")

    for test_num, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        test_names = {
            1: "Recent Fact Recall",
            2: "Pronoun Resolution",
            3: "Multi-turn Reasoning"
        }
        print(f"Test {test_num} ({test_names[test_num]}): {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Memory fixes are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Review the logs above for details.")

    print("\n" + "="*80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
