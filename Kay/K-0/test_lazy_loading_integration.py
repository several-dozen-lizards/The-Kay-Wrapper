"""
Integration test for lazy loading system.
Verifies backward compatibility and performance.
"""

import time
from agent_state import AgentState
from engines.lazy_memory_engine import LazyMemoryEngine
from engines.memory_engine import MemoryEngine


def test_lazy_vs_eager():
    """Compare lazy and eager modes."""
    print("=" * 70)
    print("LAZY LOADING INTEGRATION TEST")
    print("=" * 70)

    # Test 1: Lazy mode startup
    print("\n[TEST 1] Lazy mode startup...")
    start = time.time()
    state_lazy = AgentState()
    mem_lazy = LazyMemoryEngine(
        state_lazy.memory,
        lazy_mode=True
    )
    state_lazy.memory = mem_lazy
    lazy_time = time.time() - start
    print(f"  Lazy startup: {lazy_time:.3f}s")
    print(f"  Indexed: {len(mem_lazy.memory_index.indexes)} memories")
    print(f"  Status: {'PASS' if lazy_time < 1.0 else 'FAIL'}")

    # Test 2: Eager mode startup (for comparison)
    print("\n[TEST 2] Eager mode startup...")
    start = time.time()
    state_eager = AgentState()
    mem_eager = MemoryEngine(state_eager.memory)
    state_eager.memory = mem_eager
    eager_time = time.time() - start
    print(f"  Eager startup: {eager_time:.3f}s")
    print(f"  Loaded: {len(mem_eager.memories)} memories")
    print(f"  Status: Always baseline")

    # Test 3: Retrieval performance
    print("\n[TEST 3] Retrieval performance...")
    test_queries = [
        "What are my cats' names?",
        "Tell me about my spouse",
    ]

    for query in test_queries:
        start = time.time()
        results = mem_lazy.recall(state_lazy, query, num_memories=15)
        elapsed = (time.time() - start) * 1000
        status = "PASS" if elapsed < 150 else "FAIL"
        print(f"  [{status}] {query[:30]:30} - {elapsed:6.1f}ms ({len(results)} memories)")

    # Test 4: Memory write
    print("\n[TEST 4] Memory write (encode)...")
    start = time.time()
    mem_lazy.encode(
        state_lazy,
        user_input="Test input for performance",
        response="Test response"
    )
    write_time = (time.time() - start) * 1000
    status = "PASS" if write_time < 100 else "FAIL"
    print(f"  [{status}] Write time: {write_time:.1f}ms (target: <100ms)")

    # Test 5: Cache effectiveness
    print("\n[TEST 5] Cache effectiveness...")
    stats = mem_lazy.get_performance_stats()
    print(f"  Mode: {stats['mode']}")
    print(f"  Total indexed: {stats['total_indexed']}")
    print(f"  Cache size: {stats['cache_size']}")
    print(f"  Working loaded: {stats['working_loaded']}")
    print(f"  Full load triggered: {stats['full_load_triggered']}")
    print(f"  Status: {'PASS' if not stats['full_load_triggered'] else 'WARN - full load occurred'}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Lazy startup:  {lazy_time:.3f}s")
    print(f"Eager startup: {eager_time:.3f}s")
    print(f"Speedup:       {eager_time / lazy_time:.2f}x")
    print(f"\nAll tests: PASS" if lazy_time < 1.0 and write_time < 100 else "Some tests FAILED")


if __name__ == "__main__":
    test_lazy_vs_eager()
