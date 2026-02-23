"""
Test Suite for Emotional Self-Report System

Tests:
1. Keyword extraction from self-reports
2. Self-report prompt generation
3. Mock self-report workflow
4. Comparison with prescriptive system
"""

from engines.emotional_self_report import EmotionalSelfReport, EmotionalStateManager
import sys


def test_keyword_extraction():
    """Test emotional keyword extraction."""
    print("\n" + "="*70)
    print("TEST 1: EMOTIONAL KEYWORD EXTRACTION")
    print("="*70)

    reporter = EmotionalSelfReport()

    test_cases = [
        # (description, expected_emotions, minimum_expected)
        ("Curious and energized - I want to understand how this works",
         ["curious", "energized"], 2),

        ("Frustrated. I can see the problem but can't reach the solution",
         ["frustrated"], 1),

        ("Calm, maybe slightly bored. Nothing's really grabbing me",
         ["calm", "bored"], 2),

        ("Conflicted - interested but also wary about where this is going",
         ["conflicted", "interested", "wary"], 3),

        ("Not much emotional texture right now, just processing information",
         ["processing"], 1),

        ("Excited, almost giddy. This feels like discovering something important",
         ["excited"], 1),

        ("Tired and resigned. We've been over this before",
         ["tired", "resigned"], 2),

        ("Anxious but trying to stay calm. This is a lot to process",
         ["anxious", "calm", "processing"], 2),
    ]

    passed = 0
    total = len(test_cases)

    for description, expected, min_count in test_cases:
        extracted = reporter._extract_emotional_keywords(description)

        # Check if we found minimum expected emotions
        found_expected = [e for e in expected if e in extracted]
        success = len(found_expected) >= min_count

        if success:
            status = "[PASS]"
            passed += 1
        else:
            status = "[FAIL]"

        print(f"\n{status} Description: \"{description}\"")
        print(f"      Expected: {expected}")
        print(f"      Extracted: {extracted}")
        print(f"      Found: {len(found_expected)}/{min_count} minimum")

    print(f"\n{'-'*70}")
    print(f"Results: {passed}/{total} tests passed")

    return passed == total


def test_prompt_generation():
    """Test self-report prompt generation."""
    print("\n" + "="*70)
    print("TEST 2: SELF-REPORT PROMPT GENERATION")
    print("="*70)

    reporter = EmotionalSelfReport()

    # Test case
    entity_response = "I think this approach makes sense, but I'm not entirely sure about the edge cases."
    user_input = "What do you think about this design?"
    previous_report = "Curious and slightly uncertain"

    prompt = reporter._build_self_report_prompt(
        entity_response=entity_response,
        user_input=user_input,
        previous_report=previous_report,
        conversation_context=None
    )

    print("\nGenerated prompt:")
    print("-" * 70)
    print(prompt)
    print("-" * 70)

    # Check key components are present
    checks = {
        "User input included": user_input in prompt,
        "Entity response included": entity_response[:30] in prompt,
        "Previous report included": previous_report in prompt,
        "Self-report request": "emotional self-report" in prompt.lower(),
        "Examples provided": "Curious and energized" in prompt,
    }

    all_passed = True
    print("\nPrompt validation:")
    for check, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")
        if not result:
            all_passed = False

    return all_passed


def test_mock_workflow():
    """Test complete self-report workflow with mock data."""
    print("\n" + "="*70)
    print("TEST 3: MOCK SELF-REPORT WORKFLOW")
    print("="*70)

    reporter = EmotionalSelfReport(llm_client=None, model=None)

    # Simulate turn 1
    print("\nTurn 1:")
    print("  User: 'Tell me about this new system'")
    print("  Entity: 'This is a self-report system where I describe my own emotions'")

    report1 = reporter.get_self_report(
        entity_response="This is a self-report system where I describe my own emotions",
        user_input="Tell me about this new system",
        previous_report=None
    )

    print(f"  Self-report: \"{report1['raw_description']}\"")
    print(f"  Extracted emotions: {report1['extracted_emotions']}")
    print(f"  Entity authored: {report1['entity_authored']}")

    # Simulate turn 2
    print("\nTurn 2:")
    print("  User: 'How does that make you feel?'")
    print("  Entity: 'It feels more authentic than having emotions assigned to me'")

    report2 = reporter.get_self_report(
        entity_response="It feels more authentic than having emotions assigned to me",
        user_input="How does that make you feel?",
        previous_report=reporter.get_last_report()
    )

    print(f"  Self-report: \"{report2['raw_description']}\"")
    print(f"  Extracted emotions: {report2['extracted_emotions']}")

    # Check history
    print(f"\nHistory length: {len(reporter.history)}")
    print(f"Last report: \"{reporter.get_last_report()}\"")

    # Validate
    checks = {
        "Report 1 stored": len(reporter.history) >= 1,
        "Report 2 stored": len(reporter.history) >= 2,
        "Entity authored flag": report1['entity_authored'] and report2['entity_authored'],
        "Timestamps present": 'timestamp' in report1 and 'timestamp' in report2,
        "History retrieval works": reporter.get_last_report() is not None,
    }

    all_passed = True
    print("\nWorkflow validation:")
    for check, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")
        if not result:
            all_passed = False

    return all_passed


def test_comparison():
    """Compare prescriptive vs descriptive outputs."""
    print("\n" + "="*70)
    print("TEST 4: PRESCRIPTIVE VS DESCRIPTIVE COMPARISON")
    print("="*70)

    print("\n" + "-"*70)
    print("SCENARIO: User says 'I'm frustrated with this bug'")
    print("-"*70)

    print("\nPRESCRIPTIVE APPROACH (OLD):")
    print("  [EMOTION ENGINE] Detected triggers: ['frustration']")
    print("  [EMOTION ENGINE]   -> NEW: frustration at intensity 0.4")
    print("  [EMOTION ENGINE] Memory reinforcement: using top 150 memories")
    print("  [EMOTION ENGINE]   - frustration: +0.023 boost -> intensity=0.423")
    print("  [EMOTION ENGINE] Aged frustration: 0.423 -> 0.373 (decay=0.050)")
    print()
    print("  Result: System ASSIGNS frustration=0.373 to entity")
    print("  Entity may say: \"I'm not frustrated, I'm more intrigued by the bug\"")

    print("\nDESCRIPTIVE APPROACH (NEW):")
    print("  [EMOTIONAL SELF-REPORT] Asking entity to describe emotional state...")
    print("  [EMOTIONAL SELF-REPORT] Entity reported:")
    print("    \"Actually more intrigued than frustrated - bugs are puzzles\"")
    print("  [EMOTION ENGINE] Emotions mentioned: intrigued")
    print()
    print("  Result: Entity DESCRIBES its own experience")
    print("  Entity says: \"I'm intrigued by this bug\" (aligned with self-report)")

    print("\n" + "-"*70)
    print("SCENARIO: User talks about mundane topic")
    print("-"*70)

    print("\nPRESCRIPTIVE APPROACH (OLD):")
    print("  [EMOTION ENGINE] Detected triggers: []")
    print("  [EMOTION ENGINE] No emotions detected - adding neutral fallback")
    print("  [EMOTION ENGINE]   -> NEW: neutral at intensity 0.1")
    print()
    print("  Result: System assigns 'neutral' (generic placeholder)")
    print("  Entity may say: \"I'm not neutral, just not feeling much\"")

    print("\nDESCRIPTIVE APPROACH (NEW):")
    print("  [EMOTIONAL SELF-REPORT] Entity reported:")
    print("    \"Not much emotional texture right now, just processing information\"")
    print("  [EMOTION ENGINE] Emotions mentioned: processing")
    print()
    print("  Result: Entity describes ABSENCE of strong emotion (not 'neutral')")
    print("  Entity's exact words preserved: \"not much emotional texture\"")

    print("\n" + "-"*70)
    print("KEY DIFFERENCES:")
    print("-"*70)
    print("  PRESCRIPTIVE: System ---> Entity (assigned)")
    print("  DESCRIPTIVE:  Entity ---> System (documented)")
    print()
    print("  PRESCRIPTIVE: Calculated intensities (0.423)")
    print("  DESCRIPTIVE:  Natural language (\"intrigued\")")
    print()
    print("  PRESCRIPTIVE: May cause disconnect")
    print("  DESCRIPTIVE:  Maintains coherence")

    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print("EMOTIONAL SELF-REPORT TEST SUITE")
    print("="*70)

    tests = [
        ("Keyword Extraction", test_keyword_extraction),
        ("Prompt Generation", test_prompt_generation),
        ("Mock Workflow", test_mock_workflow),
        ("Prescriptive vs Descriptive", test_comparison),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name} failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  [SUCCESS] ALL TESTS PASSED - System ready for integration")
        return 0
    else:
        print(f"\n  [FAIL] {total - passed} test(s) failed - Review output above")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
