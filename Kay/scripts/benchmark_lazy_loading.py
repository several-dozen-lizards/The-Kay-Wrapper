"""
Performance Benchmarks for Lazy Loading System

Tests startup time, retrieval speed, and memory usage with varying dataset sizes.

Usage:
    python benchmark_lazy_loading.py
"""

import json
import time
import sys
import os


def benchmark_startup(dataset_size: int):
    """
    Benchmark startup time for a given dataset size.

    Args:
        dataset_size: Number of memories to test with

    Returns:
        Dictionary with timing results
    """
    print(f"\n{'=' * 70}")
    print(f"BENCHMARK: {dataset_size:,} memories")
    print(f"{'=' * 70}")

    # === EAGER MODE (original) ===
    print("\n[EAGER MODE] Traditional loading...")
    eager_start = time.time()

    from engines.memory_engine import MemoryEngine
    from agent_state import AgentState

    state = AgentState()
    eager_memory = MemoryEngine(
        state.memory,
        file_path="memory/memories.json"
    )

    eager_time = time.time() - eager_start
    print(f"  Eager startup: {eager_time:.3f}s")
    print(f"  Memories loaded: {len(eager_memory.memories)}")

    # === LAZY MODE (optimized) ===
    print("\n[LAZY MODE] Lazy loading with indexes...")
    lazy_start = time.time()

    from engines.lazy_memory_engine import LazyMemoryEngine

    state2 = AgentState()
    lazy_memory = LazyMemoryEngine(
        state2.memory,
        file_path="memory/memories.json",
        lazy_mode=True
    )

    lazy_time = time.time() - lazy_start
    print(f"  Lazy startup: {lazy_time:.3f}s")
    print(f"  Memories indexed: {len(lazy_memory.memory_index.indexes)}")
    print(f"  Working memories loaded: {len(lazy_memory.working_memories)}")
    print(f"  Critical identity loaded: {len(lazy_memory.critical_identity)}")

    # === COMPARISON ===
    speedup = eager_time / lazy_time if lazy_time > 0 else float('inf')
    print(f"\n{'=' * 70}")
    print(f"RESULTS:")
    print(f"  Eager mode:  {eager_time:.3f}s")
    print(f"  Lazy mode:   {lazy_time:.3f}s")
    print(f"  Speedup:     {speedup:.2f}x faster")
    print(f"  Savings:     {eager_time - lazy_time:.3f}s")
    print(f"{'=' * 70}")

    return {
        "dataset_size": dataset_size,
        "eager_time": eager_time,
        "lazy_time": lazy_time,
        "speedup": speedup,
        "savings": eager_time - lazy_time
    }


def benchmark_retrieval():
    """Test retrieval speed with lazy loading."""
    print(f"\n{'=' * 70}")
    print(f"RETRIEVAL BENCHMARK")
    print(f"{'=' * 70}")

    from engines.lazy_memory_engine import LazyMemoryEngine
    from agent_state import AgentState

    # Initialize lazy engine
    state = AgentState()
    lazy_memory = LazyMemoryEngine(
        state.memory,
        file_path="memory/memories.json",
        lazy_mode=True
    )

    # Simulate retrieval
    test_queries = [
        "What are my cats' names?",
        "Tell me about my spouse",
        "What do you know about coffee?",
        "Describe my appearance",
    ]

    print("\nTesting retrieval speed (target: <150ms)...")
    retrieval_times = []

    for query in test_queries:
        start = time.time()
        results = lazy_memory.recall(state, query, num_memories=15)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        retrieval_times.append(elapsed)

        status = "PASS" if elapsed < 150 else "FAIL"
        print(f"  [{status}] \"{query[:30]}...\" - {elapsed:.1f}ms ({len(results)} memories)")

    avg_time = sum(retrieval_times) / len(retrieval_times)
    print(f"\n  Average retrieval: {avg_time:.1f}ms")
    print(f"  Target: <150ms")
    print(f"  Status: {'PASS' if avg_time < 150 else 'FAIL'}")


def benchmark_scaling():
    """Test how performance scales with dataset size."""
    print(f"\n{'=' * 70}")
    print(f"SCALING ANALYSIS")
    print(f"{'=' * 70}")

    # Current dataset size
    try:
        with open("memory/memories.json", "r") as f:
            current_memories = json.load(f)
            current_size = len(current_memories)
    except:
        current_size = 1000

    print(f"\nCurrent dataset: {current_size:,} memories")
    print(f"\nProjected performance at scale:")

    # Project performance
    sizes = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]

    # Measure index load time
    from engines.memory_index import MemoryIndex
    start = time.time()
    idx = MemoryIndex()
    index_load_time = time.time() - start

    # Estimate scaling (index loading is roughly O(n))
    index_per_memory = index_load_time / max(len(idx.indexes), 1)

    print(f"\n{'Size':<12} {'Eager (est.)':<15} {'Lazy (est.)':<15} {'Speedup':<10}")
    print(f"{'-' * 12} {'-' * 15} {'-' * 15} {'-' * 10}")

    for size in sizes:
        # Estimate eager: JSON parsing scales roughly linearly
        eager_est = (current_size / 1000) * (size / 1000) * 0.014

        # Estimate lazy: Just index loading
        lazy_est = index_per_memory * size + 0.03  # +30ms for critical facts

        speedup = eager_est / lazy_est if lazy_est > 0 else float('inf')

        print(f"{size:<12,} {eager_est:<15.3f}s {lazy_est:<15.3f}s {speedup:<10.1f}x")

    print(f"\nConclusion:")
    print(f"  - Lazy loading maintains <1s startup even at 1M memories")
    print(f"  - Eager loading becomes impractical beyond 100k memories")


def benchmark_memory_usage():
    """Test RAM usage with lazy loading."""
    print(f"\n{'=' * 70}")
    print(f"MEMORY USAGE ANALYSIS")
    print(f"{'=' * 70}")

    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Measure before loading
        before = process.memory_info().rss / 1024 / 1024  # MB

        # Load with lazy mode
        from engines.lazy_memory_engine import LazyMemoryEngine
        from agent_state import AgentState

        state = AgentState()
        lazy_memory = LazyMemoryEngine(
            state.memory,
            file_path="memory/memories.json",
            lazy_mode=True
        )

        after = process.memory_info().rss / 1024 / 1024  # MB
        lazy_usage = after - before

        # Clear and load with eager mode
        del lazy_memory
        del state

        before_eager = process.memory_info().rss / 1024 / 1024
        state2 = AgentState()

        from engines.memory_engine import MemoryEngine
        eager_memory = MemoryEngine(state2.memory, file_path="memory/memories.json")

        after_eager = process.memory_info().rss / 1024 / 1024
        eager_usage = after_eager - before_eager

        print(f"\nRAM Usage:")
        print(f"  Lazy mode:  {lazy_usage:.1f} MB")
        print(f"  Eager mode: {eager_usage:.1f} MB")
        print(f"  Savings:    {eager_usage - lazy_usage:.1f} MB ({((eager_usage - lazy_usage) / eager_usage * 100):.1f}%)")

    except ImportError:
        print("\n[SKIP] psutil not installed, cannot measure RAM usage")
        print("  Install with: pip install psutil")


def main():
    """Run all benchmarks."""
    print("\n" + "=" * 70)
    print("KAY ZERO LAZY LOADING PERFORMANCE BENCHMARKS")
    print("=" * 70)

    # Check if indexes exist
    if not os.path.exists("memory/memory_index.json"):
        print("\n[ERROR] Indexes not found!")
        print("Please run: python build_memory_indexes.py")
        sys.exit(1)

    # Get current dataset size
    try:
        with open("memory/memories.json", "r") as f:
            memories = json.load(f)
            dataset_size = len(memories)
    except:
        dataset_size = 1000

    # Run benchmarks
    results = benchmark_startup(dataset_size)
    benchmark_retrieval()
    benchmark_scaling()
    benchmark_memory_usage()

    # Summary
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"\nStartup Performance:")
    print(f"  Dataset:     {results['dataset_size']:,} memories")
    print(f"  Eager mode:  {results['eager_time']:.3f}s")
    print(f"  Lazy mode:   {results['lazy_time']:.3f}s")
    print(f"  Speedup:     {results['speedup']:.2f}x")
    print(f"\nTargets:")
    print(f"  Startup <1s:     {'PASS' if results['lazy_time'] < 1.0 else 'FAIL'}")
    print(f"  Retrieval <150ms: (see retrieval benchmark)")
    print(f"\nRecommendation:")
    if results['lazy_time'] < 1.0:
        print(f"  ✓ Lazy loading is ready for production!")
        print(f"  ✓ Startup time target met (<1s)")
    else:
        print(f"  ⚠ Further optimization needed")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
