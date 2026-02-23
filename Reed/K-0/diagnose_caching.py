"""
Diagnostic script to identify caching issue.

This will help us understand:
1. When cache_control blocks are being added
2. When cache is being created vs hit
3. What turn_count values are being used
"""

def diagnose_turn_flow():
    """Simulate the turn counter flow."""
    print("=== DIAGNOSING TURN COUNTER FLOW ===\n")

    # Current implementation
    print("CURRENT IMPLEMENTATION:")
    print("-" * 50)
    turn_count = 0
    print(f"Session starts: turn_count = {turn_count}")

    # First message
    turn_count += 1  # Increment BEFORE LLM call (line 1701)
    print(f"First message arrives")
    print(f"  turn_count incremented to: {turn_count}")
    print(f"  LLM called with turn_count={turn_count}")
    print(f"  Expected: Cache CREATED (first call)")
    print(f"  User sees: 'Turn {turn_count - 1}' in terminal output")

    # Second message
    turn_count += 1
    print(f"\nSecond message arrives")
    print(f"  turn_count incremented to: {turn_count}")
    print(f"  LLM called with turn_count={turn_count}")
    print(f"  Expected: Cache HIT (second call)")
    print(f"  User sees: 'Turn {turn_count - 1}' in terminal output")

    print("\n" + "=" * 50)
    print("PROPOSED FIX:")
    print("-" * 50)
    turn_count = 0
    print(f"Session starts: turn_count = {turn_count}")

    # First message
    print(f"First message arrives")
    print(f"  LLM called with turn_count={turn_count}")
    print(f"  Expected: Cache CREATED (first call, turn 0)")
    print(f"  User sees: 'Turn {turn_count}' in terminal output")
    turn_count += 1  # Increment AFTER LLM call
    print(f"  turn_count incremented to: {turn_count} AFTER response")

    # Second message
    print(f"\nSecond message arrives")
    print(f"  LLM called with turn_count={turn_count}")
    print(f"  Expected: Cache HIT (second call, turn 1)")
    print(f"  User sees: 'Turn {turn_count}' in terminal output")
    turn_count += 1  # Increment AFTER LLM call
    print(f"  turn_count incremented to: {turn_count} AFTER response")


def check_cache_control_condition():
    """Check if cache_control blocks are being added correctly."""
    print("\n\n=== CHECKING CACHE CONTROL LOGIC ===\n")

    # Simulate the condition in query_llm_json line 957
    print("Condition: if use_cache and context_dict:")
    print("-" * 50)

    # Test case 1: Both true (should cache)
    use_cache = True
    context_dict = {"user_input": "test", "recalled_memories": []}
    result = use_cache and context_dict
    print(f"Test 1: use_cache={use_cache}, context_dict={bool(context_dict)}")
    print(f"  Result: {result} - Cache blocks {'ADDED' if result else 'NOT ADDED'}")

    # Test case 2: use_cache False (should not cache)
    use_cache = False
    context_dict = {"user_input": "test"}
    result = use_cache and context_dict
    print(f"\nTest 2: use_cache={use_cache}, context_dict={bool(context_dict)}")
    print(f"  Result: {result} - Cache blocks {'ADDED' if result else 'NOT ADDED'}")

    # Test case 3: context_dict is None (should not cache)
    use_cache = True
    context_dict = None
    result = use_cache and context_dict
    print(f"\nTest 3: use_cache={use_cache}, context_dict={bool(context_dict)}")
    print(f"  Result: {result} - Cache blocks {'ADDED' if result else 'NOT ADDED'}")

    # Test case 4: context_dict is empty dict (might not cache?)
    use_cache = True
    context_dict = {}
    result = use_cache and context_dict
    print(f"\nTest 4: use_cache={use_cache}, context_dict={bool(context_dict)}")
    print(f"  Result: {result} - Cache blocks {'ADDED' if result else 'NOT ADDED'}")
    print(f"  NOTE: Empty dict is falsy in Python!")


if __name__ == "__main__":
    diagnose_turn_flow()
    check_cache_control_condition()

    print("\n\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)

    print("\nKEY FINDINGS:")
    print("1. Turn counter increments BEFORE LLM call (line 1701)")
    print("2. First LLM call happens at turn_count=1, not 0")
    print("3. Cache should still be created on first call (turn 1)")
    print("4. If cache isn't being created, check if context_dict is empty/None")

    print("\nRECOMMENDED FIX:")
    print("Move 'self.turn_count += 1' to AFTER get_llm_response() call")
    print("This ensures first call is turn 0, matching user expectations")
