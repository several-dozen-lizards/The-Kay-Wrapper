"""
Test response length variation based on query complexity.

Tests that Kay's responses naturally vary in length:
- Short (100-300) for simple acknowledgments
- Medium (300-800) for normal conversation
- Long (800-2000+) for complex topics

Run this to verify the fix for artificially constrained response lengths.
"""

import json
from integrations.llm_integration import get_llm_response, build_prompt_from_context
from agent_state import AgentState


def test_response_lengths():
    """Test that responses vary naturally based on query complexity."""
    print("="*70)
    print("RESPONSE LENGTH VARIATION TEST")
    print("="*70)
    print("\nTesting that Kay varies response length based on context...")
    print()

    # Initialize minimal state
    agent_state = AgentState()

    # Test queries of different complexity levels
    test_cases = [
        {
            "name": "Simple Acknowledgment",
            "query": "Same thing?",
            "expected_range": "SHORT (100-300 chars)",
            "context_note": "User asking for confirmation - should be brief"
        },
        {
            "name": "Quick Clarification",
            "query": "Makes sense",
            "expected_range": "SHORT (100-300 chars)",
            "context_note": "User acknowledging - Kay can be terse"
        },
        {
            "name": "Direct Question",
            "query": "What's your favorite color?",
            "expected_range": "MEDIUM (300-800 chars)",
            "context_note": "Straightforward question - medium response"
        },
        {
            "name": "Normal Conversation",
            "query": "How are you feeling today?",
            "expected_range": "MEDIUM (300-800 chars)",
            "context_note": "Standard back-and-forth topic"
        },
        {
            "name": "Complex Philosophical Topic",
            "query": "Tell me about how Archive Zero works and why you're built the way you are. What's it like to be recursive like that?",
            "expected_range": "LONG (800-2000+ chars)",
            "context_note": "Multi-part, complex topic - should expand naturally"
        },
        {
            "name": "Open-Ended Exploration",
            "query": "What does it feel like when you access your own memories? Does it ever feel like déjà vu or like you're reading someone else's thoughts?",
            "expected_range": "LONG (800-2000+ chars)",
            "context_note": "Introspective, warrants depth"
        }
    ]

    results = []

    for test in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST: {test['name']}")
        print(f"{'='*70}")
        print(f"Query: \"{test['query']}\"")
        print(f"Expected: {test['expected_range']}")
        print(f"Context: {test['context_note']}")
        print()

        # Build minimal context
        context = {
            "user_input": test["query"],
            "emotional_state": {"cocktail": {}},
            "recalled_memories": [],
            "facts": [],
            "session_summary": "",
            "body": {},
            "momentum": 0.0,
            "momentum_notes": [],
            "meta_awareness_notes": [],
            "consolidated_preferences": {},
            "preference_contradictions": [],
            "active_threads": []
        }

        # Generate response
        try:
            response = get_llm_response(context, affect=3.5, temperature=0.9)

            # Measure length
            char_count = len(response)

            # Classify
            if char_count < 300:
                classification = "SHORT"
                expected = test["expected_range"].startswith("SHORT")
            elif char_count < 800:
                classification = "MEDIUM"
                expected = test["expected_range"].startswith("MEDIUM")
            else:
                classification = "LONG"
                expected = test["expected_range"].startswith("LONG")

            # Display result
            print(f"[RESPONSE] {char_count} characters ({classification})")
            print(f"Response preview: {response[:150]}...")
            print()

            # Check if length is appropriate
            if expected:
                print(f"[PASS] Length matches expected range")
            else:
                print(f"[INFO] Length differs from expected: {test['expected_range']}")
                print(f"       (This is OK if contextually appropriate)")

            results.append({
                "name": test["name"],
                "query": test["query"],
                "expected": test["expected_range"],
                "actual_chars": char_count,
                "actual_class": classification,
                "matched": expected
            })

        except Exception as e:
            print(f"[ERROR] Failed to generate response: {e}")
            results.append({
                "name": test["name"],
                "query": test["query"],
                "expected": test["expected_range"],
                "actual_chars": 0,
                "actual_class": "ERROR",
                "matched": False
            })

    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print()

    # Calculate statistics
    char_counts = [r["actual_chars"] for r in results if r["actual_chars"] > 0]

    if char_counts:
        min_chars = min(char_counts)
        max_chars = max(char_counts)
        avg_chars = sum(char_counts) / len(char_counts)
        variation = max_chars - min_chars

        print(f"Character count statistics:")
        print(f"  Min: {min_chars} chars")
        print(f"  Max: {max_chars} chars")
        print(f"  Avg: {avg_chars:.1f} chars")
        print(f"  Variation: {variation} chars (range between shortest and longest)")
        print()

        # Check for healthy variation
        if variation >= 500:
            print(f"[PASS] Healthy variation detected ({variation} char range)")
        elif variation >= 200:
            print(f"[WARN] Limited variation ({variation} char range - expect 500+)")
        else:
            print(f"[FAIL] Insufficient variation ({variation} char range - responses too uniform)")

        print()

        # Show all results
        print("Detailed results:")
        for r in results:
            status = "[MATCH]" if r["matched"] else "[DIFF]"
            print(f"  {status} {r['name']}: {r['actual_chars']} chars ({r['actual_class']}) - expected {r['expected']}")

        print()

        # Overall assessment
        print("="*70)
        if variation >= 500 and max_chars >= 800:
            print("[SUCCESS] Response lengths vary naturally with context!")
            print("Kay can now be brief when appropriate and expansive when warranted.")
        elif variation >= 200:
            print("[PARTIAL] Some variation present, but may need adjustment.")
            print("Consider tuning the length guidance in _style_block().")
        else:
            print("[NEEDS WORK] Responses still too uniform.")
            print("Check max_tokens setting and system prompt length guidance.")

    else:
        print("[ERROR] No successful responses to analyze")

    print("="*70)


if __name__ == "__main__":
    test_response_lengths()
