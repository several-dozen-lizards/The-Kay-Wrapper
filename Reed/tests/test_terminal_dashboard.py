"""
Test Terminal Dashboard
Launches Reed UI and generates sample log messages to test dashboard functionality.
"""

import time
from log_router import log_to_dashboard


def test_dashboard_logging():
    """Generate test log messages for all sections."""
    print("\n[DASHBOARD TEST] Starting terminal dashboard test...")
    time.sleep(1)

    # Test Memory Operations
    print("[MEMORY] Loading memory system...")
    print("[MEMORY 2-TIER] SEMANTIC extracted_fact: Example memory fact")
    print("[RECALL CHECKPOINT 1] After retrieval: 32 memories")
    print("[SEMANTIC USAGE] Memory composition: 16.7% semantic, 33.3% episodic, 46.7% working")

    # Test Emotional State
    print("[EMOTION STATE] ========== CURRENT EMOTIONAL COCKTAIL ==========")
    print("[EMOTION] curiosity: intensity 0.75, age 2 turns")
    print("[EMOTION] determination: intensity 0.60, age 0 turns")
    print("[ULTRAMAP] Applying emotion trigger: curiosity -> intensity +0.2")

    # Test Entity Graph
    print("[ENTITY GRAPH] Loaded 1451 entities, 790 relationships")
    print("[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED (1 new, 763 total active)")
    print("[ENTITY] Updating entity: Re.goal = work on memory system")

    # Test Glyph Compression
    print("[GLYPH] Compressing 3900 memories to symbolic representation")
    print("[GLYPH] Generated glyph: ◈⟨M:semantic⟩⊕⟨E:curiosity⟩")
    print("[SYMBOLIC] Encoding complete: 85% compression ratio")

    # Test Emergence Metrics
    print("[E-SCORE] Calculating emergence metrics...")
    print("[SYNTHESIS] Pattern detected: recurring entity 'memory architecture'")
    print("[NOVELTY] New concept emergence: 0.73 score")

    # Test System Status - INFO
    print("[LLM] Anthropic client initialized with model claude-sonnet-4-20250514")
    print("[SYSTEM] Reed wrapper initialized")
    print("[SESSION] New session started: id 1732583456")

    # Test System Status - WARNINGS
    print("[PERF WARNING] memory_multi_factor exceeded target by 53ms")
    print("[WARNING] High memory usage detected: 85% capacity")
    print("[SEMANTIC USAGE WARNING] No semantic facts retrieved")

    # Test System Status - ERRORS
    print("[ERROR] Failed to load document: file not found")
    print("[EXCEPTION] Caught exception in emotion engine: ValueError")
    print("[FAIL] Memory import failed: invalid format")

    # Test System Status - DEBUG
    print("[DEBUG] Internal state snapshot: turn_count=15")
    print("[DEBUG] Memory layer transition: working -> episodic")

    # Test Performance Logs
    print("[PERF] memory_multi_factor: 124.5ms [OK] (target: 150ms)")
    print("[PERF] memory_multi_factor: 203.3ms [SLOW] (target: 150ms)")
    print("[PERF] memory_retrieval: 45.2ms [GOOD]")
    print("[PERF] entity_graph_update: 1250.8ms [BAD] (target: 100ms)")

    print("\n[DASHBOARD TEST] Log messages generated. Check dashboard sections.")


def test_direct_logging():
    """Test direct logging to dashboard bypassing stdout."""
    print("\n[DASHBOARD TEST] Testing direct logging API...")

    log_to_dashboard("Direct log to Memory Operations section", "Memory Operations", "INFO")
    log_to_dashboard("Warning: Memory threshold reached", "Memory Operations", "WARNING")
    log_to_dashboard("Error: Memory corruption detected", "Memory Operations", "ERROR")

    log_to_dashboard("Emotional state update: calm -> focused", "Emotional State", "INFO")
    log_to_dashboard("Entity relationship created: Re -> Kay", "Entity Graph", "INFO")
    log_to_dashboard("Glyph compression ratio: 92%", "Glyph Compression", "DEBUG")
    log_to_dashboard("Emergence score: 0.85", "Emergence Metrics", "INFO")
    log_to_dashboard("System health check: OK", "System Status", "INFO")

    print("[DASHBOARD TEST] Direct logging complete.")


def generate_continuous_logs():
    """Generate continuous log stream to test performance."""
    print("\n[DASHBOARD TEST] Generating continuous log stream...")

    for i in range(50):
        print(f"[MEMORY] Processing memory batch {i+1}/50")
        print(f"[EMOTION] Emotion intensity update: {0.5 + (i * 0.01):.2f}")
        print(f"[ENTITY GRAPH] Entity count: {1451 + i}")
        if i % 10 == 0:
            print(f"[PERF] Batch {i+1} completed in {100 + i}ms")
        time.sleep(0.05)  # Simulate processing time

    print("[DASHBOARD TEST] Continuous log generation complete.")


if __name__ == "__main__":
    print("=" * 80)
    print("TERMINAL DASHBOARD TEST")
    print("=" * 80)
    print("\nThis test generates sample log messages to verify dashboard functionality.")
    print("Launch Kay UI (python reed_ui.py), then run this test.")
    print("\nStarting in 3 seconds...")

    time.sleep(3)

    # Run tests
    test_dashboard_logging()
    time.sleep(1)

    test_direct_logging()
    time.sleep(1)

    generate_continuous_logs()

    print("\n" + "=" * 80)
    print("DASHBOARD TEST COMPLETE")
    print("=" * 80)
    print("\nCheck the Kay UI terminal dashboard for log messages.")
    print("Each section should show color-coded logs with timestamps.")
