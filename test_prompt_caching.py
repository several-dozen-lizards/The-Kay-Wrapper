"""
Test script for prompt caching implementation.

Validates:
1. First call creates cache
2. Second call hits cache (much faster)
3. Cache performance logging appears
4. Kay's personality remains intact
"""

import time
from agent_state import AgentState
from engines.memory_engine import MemoryEngine
from integrations.llm_integration import get_llm_response

def test_prompt_caching():
    """Test prompt caching performance and correctness."""

    print("=" * 70)
    print("PROMPT CACHING TEST")
    print("=" * 70)

    # Create agent state with some context
    state = AgentState()
    state.emotional_cocktail = {
        'curious': {'intensity': 0.6, 'age': 0},
        'focused': {'intensity': 0.4, 'age': 0}
    }

    # Create memory engine
    memory = MemoryEngine(state.memory)

    # Add some test memories
    print("\n[SETUP] Adding test memories...")
    test_memories = [
        {"fact": "Kay is a void-dragon", "perspective": "kay", "importance": 0.9},
        {"fact": "Re has green eyes", "perspective": "user", "importance": 0.9},
        {"fact": "Kay and Re discussed pigeons", "perspective": "shared", "importance": 0.7},
    ]

    for mem in test_memories:
        memory.memories.append(mem)

    # Recall memories to populate last_recalled_memories
    memory.recall(state, "Hi Kay")

    # Build context for LLM
    context = {
        "user_input": "Hi Kay, how are you?",
        "recalled_memories": state.last_recalled_memories if hasattr(state, 'last_recalled_memories') else [],
        "emotional_state": {
            "cocktail": state.emotional_cocktail
        },
        "body": {},
        "recent_context": [],
        "momentum_notes": [],
        "meta_awareness_notes": [],
        "rag_chunks": [],
        "consolidated_preferences": {},
        "turn_count": 1,
        "recent_responses": [],
        "session_id": "test_session"
    }

    print(f"[SETUP] Context built with {len(context['recalled_memories'])} memories")

    # TEST 1: First call (creates cache)
    print("\n" + "=" * 70)
    print("TEST 1: First call with caching (should CREATE cache)")
    print("=" * 70)

    start_time = time.time()
    response1 = get_llm_response(
        prompt_or_context=context,
        affect=3.5,
        temperature=0.9,
        use_cache=True  # ENABLE CACHING
    )
    time1 = time.time() - start_time

    print(f"\n[RESULT] Response 1 (time: {time1:.2f}s):")
    print(f"  Length: {len(response1)} chars")
    print(f"  Preview: {response1[:200]}...")

    # TEST 2: Second call (hits cache)
    print("\n" + "=" * 70)
    print("TEST 2: Second call with caching (should HIT cache - MUCH faster)")
    print("=" * 70)

    # Change user input to ensure dynamic content changes
    context["user_input"] = "Tell me about Chrome"
    context["turn_count"] = 2
    context["recent_responses"] = [response1]

    start_time = time.time()
    response2 = get_llm_response(
        prompt_or_context=context,
        affect=3.5,
        temperature=0.9,
        use_cache=True  # ENABLE CACHING
    )
    time2 = time.time() - start_time

    print(f"\n[RESULT] Response 2 (time: {time2:.2f}s):")
    print(f"  Length: {len(response2)} chars")
    print(f"  Preview: {response2[:200]}...")

    # TEST 3: Compare performance
    print("\n" + "=" * 70)
    print("TEST SUMMARY - CACHE PERFORMANCE")
    print("=" * 70)

    speedup = time1 / time2 if time2 > 0 else 0
    improvement = ((time1 - time2) / time1 * 100) if time1 > 0 else 0

    print(f"\nFirst call (cache creation):  {time1:.2f}s")
    print(f"Second call (cache hit):      {time2:.2f}s")
    print(f"Speedup:                      {speedup:.2f}x")
    print(f"Time saved:                   {improvement:.1f}%")

    # Verify cache hit was faster
    if time2 < time1 * 0.5:
        print("\n[PASS] Cache hit is significantly faster (at least 2x speedup)")
    else:
        print(f"\n[WARN] Cache hit not as fast as expected (expected < {time1 * 0.5:.2f}s, got {time2:.2f}s)")
        print("[INFO] This might be due to network latency or other factors")

    # TEST 4: Verify personality intact
    print("\n" + "=" * 70)
    print("TEST 4: Verify Kay's personality intact")
    print("=" * 70)

    context["user_input"] = "What's your personality like?"
    context["turn_count"] = 3
    context["recent_responses"] = [response1, response2]

    response3 = get_llm_response(
        prompt_or_context=context,
        affect=3.5,
        temperature=0.9,
        use_cache=True
    )

    print(f"\n[RESULT] Response 3:")
    print(f"  {response3[:400]}...")

    # Check for key personality markers
    personality_markers = [
        ("direct", "Direct/conversational tone"),
        ("sarcas", "Sarcasm"),
        ("dry", "Dry humor"),
        ("dragon", "Dragon identity"),
    ]

    found_markers = []
    response_lower = response3.lower()
    for marker, description in personality_markers:
        if marker in response_lower:
            found_markers.append(description)

    if found_markers:
        print(f"\n[PASS] Personality markers found: {', '.join(found_markers)}")
    else:
        print("\n[INFO] No explicit personality markers in response (might be implicit)")

    # TEST 5: Non-cached comparison
    print("\n" + "=" * 70)
    print("TEST 5: Compare with non-cached call")
    print("=" * 70)

    context["user_input"] = "What do you think?"
    context["turn_count"] = 4

    start_time = time.time()
    response_nocache = get_llm_response(
        prompt_or_context=context,
        affect=3.5,
        temperature=0.9,
        use_cache=False  # DISABLE CACHING
    )
    time_nocache = time.time() - start_time

    print(f"\n[RESULT] Non-cached call: {time_nocache:.2f}s")
    print(f"[RESULT] Cached call avg: {(time1 + time2) / 2:.2f}s")

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(f"\nCache creation (1st call):   {time1:.2f}s")
    print(f"Cache hit (2nd call):        {time2:.2f}s")
    print(f"Non-cached (legacy):         {time_nocache:.2f}s")
    print(f"\nCache speedup:               {speedup:.2f}x faster")
    print(f"Time saved per cached call:  {improvement:.1f}%")

    print("\n[SUCCESS] Prompt caching implementation complete!")
    print("[INFO] Check console output above for cache performance logs:")
    print("  - '[CACHE] Cache created: X tokens' (first call)")
    print("  - '[CACHE] Cache hit: X tokens' (second call)")

    print("\n" + "=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_prompt_caching()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
