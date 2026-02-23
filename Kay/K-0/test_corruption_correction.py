"""
Test Suite: Corruption Detection and Correction

Tests the corruption detection system's ability to:
1. Detect gibberish and repetition
2. Mark memories as superseded
3. Filter corrupted memories from retrieval
4. Generate corruption statistics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from engines.corruption_detection import (
    CorruptionDetector,
    ensure_corruption_markers,
    filter_corrupted_memories
)


class MockMemoryEngine:
    """Mock memory engine for testing."""

    def __init__(self):
        self.memories = []
        self.current_turn = 10
        self.protocol_engine = None

        # Mock memory layers
        class MockLayers:
            def __init__(self):
                self.working_memory = []
                self.episodic_memory = []
                self.semantic_memory = []

        self.memory_layers = MockLayers()

    def save_memories(self):
        """Mock save."""
        pass


def test_gibberish_detection():
    """Test 1: Detect gibberish patterns."""
    print("\n" + "="*70)
    print("TEST 1: Gibberish Detection")
    print("="*70)

    # Create mock memory engine
    mock_engine = MockMemoryEngine()
    detector = CorruptionDetector(mock_engine)

    # Test cases
    test_cases = [
        {
            'text': 'Kay processes math and Arabic simultaneously aaaaaaa',
            'should_detect': True,
            'reason': 'Repeated character'
        },
        {
            'text': 'This is a normal memory about tea',
            'should_detect': False,
            'reason': 'Clean text'
        },
        {
            'text': 'Kay said said said said said coffee is good',
            'should_detect': True,
            'reason': 'Excessive word repetition'
        },
        {
            'text': 'multilingual processing !@#$%^&*()_+-=[]{}|;:,.<>?',
            'should_detect': True,
            'reason': 'Too many special characters'
        },
        {
            'text': 'bcdfghjklmnpqrstvwxyz',
            'should_detect': True,
            'reason': 'All consonants, no vowels'
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases):
        memory = {'fact': test['text']}
        is_corrupted, reason = detector.detect_corruption(memory)

        expected = test['should_detect']
        status = "PASS" if is_corrupted == expected else "FAIL"

        print(f"\nTest case {i+1}: {test['reason']}")
        print(f"  Text: {test['text'][:60]}...")
        print(f"  Expected corruption: {expected}")
        print(f"  Detected corruption: {is_corrupted}")
        if is_corrupted:
            print(f"  Reason: {reason}")
        print(f"  [{status}]")

        if status == "PASS":
            passed += 1
        else:
            failed += 1

    print(f"\nTest 1 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_memory_supersession():
    """Test 2: Mark memory as superseded and create correction."""
    print("\n" + "="*70)
    print("TEST 2: Memory Supersession")
    print("="*70)

    # Create mock memory engine
    mock_engine = MockMemoryEngine()
    detector = CorruptionDetector(mock_engine)

    # Create two test memories
    wrong_memory = {
        'memory_id': 'mem_100',
        'fact': 'Kay prefers coffee',
        'current_layer': 'semantic',
        'importance_score': 0.6
    }

    correct_memory = {
        'memory_id': 'mem_101',
        'fact': 'Kay prefers tea',
        'current_layer': 'semantic',
        'importance_score': 0.6
    }

    # Add to memory engine
    mock_engine.memory_layers.semantic_memory.append(wrong_memory)
    mock_engine.memory_layers.semantic_memory.append(correct_memory)
    mock_engine.memories.append(wrong_memory)
    mock_engine.memories.append(correct_memory)

    # Test supersession
    print("\nMarking mem_100 as superseded by mem_101...")
    success = detector.mark_memory_superseded('mem_100', 'mem_101', turn_id=10)

    # Verify results
    checks = []

    # Check 1: Supersession successful
    checks.append(("Supersession successful", success == True))

    # Check 2: Old memory marked as corrupted
    checks.append(("Old memory corrupted flag", wrong_memory.get('corrupted') == True))

    # Check 3: Old memory has superseded_by link
    checks.append(("Old memory superseded_by", wrong_memory.get('superseded_by') == 'mem_101'))

    # Check 4: New memory has supersedes link
    checks.append(("New memory supersedes", correct_memory.get('supersedes') == 'mem_100'))

    # Check 5: Correction turn recorded
    checks.append(("Correction turn", wrong_memory.get('correction_turn') == 10))

    # Print results
    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {check_name}: [{status}]")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTest 2 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_filter_corrupted():
    """Test 3: Filter corrupted memories from retrieval."""
    print("\n" + "="*70)
    print("TEST 3: Filter Corrupted Memories")
    print("="*70)

    # Create test memories
    memories = [
        {'fact': 'Clean memory 1', 'corrupted': False},
        {'fact': 'Corrupted memory', 'corrupted': True},
        {'fact': 'Clean memory 2', 'corrupted': False},
        {'fact': 'Superseded memory', 'superseded_by': 'mem_999'},
        {'fact': 'Clean memory 3'},  # No corruption field
    ]

    print(f"\nOriginal memories: {len(memories)}")

    # Filter
    filtered = filter_corrupted_memories(memories)

    print(f"Filtered memories: {len(filtered)}")

    # Verify results
    checks = []

    # Check 1: Correct count (should be 3: clean1, clean2, clean3)
    checks.append(("Correct count", len(filtered) == 3))

    # Check 2: No corrupted memories
    has_corrupted = any(m.get('corrupted', False) for m in filtered)
    checks.append(("No corrupted memories", not has_corrupted))

    # Check 3: No superseded memories
    has_superseded = any(m.get('superseded_by') for m in filtered)
    checks.append(("No superseded memories", not has_superseded))

    # Check 4: All clean memories preserved
    clean_facts = [m['fact'] for m in filtered]
    expected_facts = ['Clean memory 1', 'Clean memory 2', 'Clean memory 3']
    checks.append(("All clean memories preserved", sorted(clean_facts) == sorted(expected_facts)))

    # Print results
    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {check_name}: [{status}]")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTest 3 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_corruption_stats():
    """Test 4: Generate corruption statistics."""
    print("\n" + "="*70)
    print("TEST 4: Corruption Statistics")
    print("="*70)

    # Create mock memory engine
    mock_engine = MockMemoryEngine()
    detector = CorruptionDetector(mock_engine)

    # Create test memories
    memories = [
        {'fact': 'Clean 1', 'corrupted': False},
        {'fact': 'Clean 2', 'corrupted': False},
        {'fact': 'Gibberish aaaaa', 'corrupted': True, 'corruption_reason': 'Gibberish detected'},
        {'fact': 'Wrong fact', 'corrupted': True, 'corruption_reason': 'Superseded by correction', 'superseded_by': 'mem_999'},
        {'fact': 'Correction', 'is_correction': True, 'supersedes': 'mem_3'},
        {'fact': 'Clean 3', 'corrupted': False},
    ]

    # Add to memory engine - use semantic layer so detector finds them
    mock_engine.memory_layers.semantic_memory = memories
    mock_engine.memories = memories

    # Get stats
    stats = detector.get_corruption_stats()

    print(f"\nStatistics:")
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Corrupted: {stats['corrupted_count']}")
    print(f"  Superseded: {stats['superseded_count']}")
    print(f"  Corrections: {stats['corrections_count']}")
    print(f"  Corruption rate: {stats['corruption_rate']*100:.1f}%")

    if stats['corruption_reasons']:
        print(f"  Reasons:")
        for reason, count in stats['corruption_reasons'].items():
            print(f"    - {reason}: {count}")

    # Verify results
    checks = []

    checks.append(("Total count", stats['total_memories'] == 6))
    checks.append(("Corrupted count", stats['corrupted_count'] == 2))
    checks.append(("Superseded count", stats['superseded_count'] == 1))
    checks.append(("Corrections count", stats['corrections_count'] == 1))
    checks.append(("Corruption rate", abs(stats['corruption_rate'] - 2/6) < 0.01))

    # Print results
    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {check_name}: [{status}]")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTest 4 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_correct_memory():
    """Test 5: Create correction and mark supersession."""
    print("\n" + "="*70)
    print("TEST 5: Correct Memory")
    print("="*70)

    # Create mock memory engine
    mock_engine = MockMemoryEngine()
    detector = CorruptionDetector(mock_engine)

    # Create wrong memory
    wrong_memory = {
        'memory_id': 'mem_200',
        'fact': 'Kay likes coffee',
        'current_layer': 'semantic',
        'importance_score': 0.7
    }

    # Add to memory engine
    mock_engine.memory_layers.semantic_memory.append(wrong_memory)
    mock_engine.memories.append(wrong_memory)

    # Correct it
    print("\nCorrecting: 'Kay likes coffee' -> 'Kay likes tea'")
    new_id = detector.correct_memory(
        'mem_200',
        'Kay likes tea, not coffee',
        turn_id=15
    )

    # Verify results
    checks = []

    # Check 1: New memory created
    checks.append(("New memory created", new_id is not None))

    # Check 2: Old memory marked as superseded
    checks.append(("Old memory corrupted", wrong_memory.get('corrupted') == True))
    checks.append(("Old memory superseded_by", wrong_memory.get('superseded_by') == new_id))

    # Check 3: New memory exists
    new_memory = detector._find_memory_by_id(new_id) if new_id else None
    checks.append(("New memory exists", new_memory is not None))

    if new_memory:
        # Check 4: New memory has correct fact
        checks.append(("Correct fact", new_memory.get('fact') == 'Kay likes tea, not coffee'))

        # Check 5: New memory marked as correction
        checks.append(("Is correction", new_memory.get('is_correction') == True))

        # Check 6: New memory supersedes old
        checks.append(("Supersedes old", new_memory.get('supersedes') == 'mem_200'))

    # Print results
    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {check_name}: [{status}]")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTest 5 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_ensure_markers():
    """Test 6: Ensure corruption markers are added."""
    print("\n" + "="*70)
    print("TEST 6: Ensure Corruption Markers")
    print("="*70)

    # Memory without corruption markers
    old_memory = {
        'fact': 'Some old memory',
        'turn_index': 5
    }

    print("\nOriginal memory fields:")
    print(f"  {list(old_memory.keys())}")

    # Add markers
    updated = ensure_corruption_markers(old_memory)

    print("\nUpdated memory fields:")
    print(f"  {list(updated.keys())}")

    # Verify all markers present
    required_markers = [
        'corrupted',
        'corruption_reason',
        'corruption_detected_turn',
        'superseded_by',
        'supersedes',
        'correction_applied',
        'correction_turn'
    ]

    checks = []

    for marker in required_markers:
        present = marker in updated
        checks.append((f"Has {marker}", present))

    # Check defaults
    checks.append(("corrupted defaults to False", updated.get('corrupted') == False))
    checks.append(("corruption_reason defaults to None", updated.get('corruption_reason') is None))

    # Print results
    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {check_name}: [{status}]")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTest 6 Results: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("="*70)
    print("CORRUPTION DETECTION TEST SUITE")
    print("="*70)

    tests = [
        ("Gibberish Detection", test_gibberish_detection),
        ("Memory Supersession", test_memory_supersession),
        ("Filter Corrupted Memories", test_filter_corrupted),
        ("Corruption Statistics", test_corruption_stats),
        ("Correct Memory", test_correct_memory),
        ("Ensure Corruption Markers", test_ensure_markers),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    total_passed = sum(1 for _, passed in results if passed)
    total_failed = len(results) - total_passed

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: [{status}]")

    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_failed == 0:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{total_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
