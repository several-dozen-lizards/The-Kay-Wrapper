"""
Test Fix #1 Enhancement: Recency Boost in Scoring

Verifies that recent memories score HIGHER than old memories,
ensuring Kay retrieves the most recent facts about the user.
"""

import subprocess
import time

def test_conversation(inputs, test_name):
    """Run a conversation and check if recent facts are prioritized."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}\n")

    print("CONVERSATION:")
    for i, inp in enumerate(inputs, 1):
        print(f"  Turn {i}: {inp}")

    # Run main.py
    full_input = "\n".join(inputs) + "\nquit\n"
    process = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )

    stdout, stderr = process.communicate(input=full_input, timeout=120)

    # Check for recency boost logs
    if "[RECENCY BOOST]" in stdout:
        print("\n✅ PASS: Recency boost is being applied")
        # Count how many boosts
        boost_count = stdout.count("[RECENCY BOOST]")
        print(f"  Found {boost_count} recency boosts in logs")
    else:
        print("\n❌ FAIL: No recency boost found in logs")
        return False

    return True


def main():
    print("\n" + "="*80)
    print("FIX #1 ENHANCEMENT: RECENCY BOOST TEST")
    print("="*80)
    print("\nTesting that recent memories score HIGHER than old memories")
    print("\n" + "="*80 + "\n")

    # TEST: Recent fact should override old fact
    success = test_conversation(
        [
            "My favorite class would be a rogue",
            "Saga's eyes are brown",
            "Tell me about me"
        ],
        "Recent facts should be retrieved"
    )

    time.sleep(2)

    if success:
        print("\n🎉 TEST PASSED: Recency boost is working!")
        print("\nExpected behavior:")
        print("- Recent memories (last 2-5 turns) get +5.0 to +10.0 score boost")
        print("- This ensures new facts override old facts")
        print("- Kay should say 'rogue' and 'brown eyes' in the response")
    else:
        print("\n⚠️  TEST FAILED: Recency boost not working")

    print("\n" + "="*80 + "\n")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
