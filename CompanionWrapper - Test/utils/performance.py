# utils/performance.py
"""
Performance monitoring and timing utilities for the entityZero.
Non-blocking decorators that log execution time and warn when targets are exceeded.
"""

import time
import functools
from typing import Callable, Optional, Dict, Any

# Performance targets (in seconds)
TARGETS = {
    "memory_retrieval": 0.150,      # 150ms for memory recall
    "memory_multi_factor": 0.150,   # 150ms for multi-factor retrieval
    "llm_response": 0.500,          # 500ms for LLM call (Haiku target)
    "llm_filter": 0.500,            # 500ms for filter LLM
    "total_turn": 2.0,              # 2s for complete turn processing
}

# Global metrics storage (last turn only)
_last_metrics: Dict[str, float] = {}
_warnings: list = []


def measure_performance(metric_name: str, target: Optional[float] = None) -> Callable:
    """
    Decorator to measure and log function performance.

    Non-blocking: Always executes function, logs timing afterward.
    Warns if performance target exceeded but does not raise errors.

    Args:
        metric_name: Name of the metric (e.g., "memory_retrieval")
        target: Optional target time in seconds (default from TARGETS)

    Example:
        @measure_performance("memory_retrieval", target=0.150)
        def recall(self, agent_state, user_input):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            # Get target time
            target_time = target if target is not None else TARGETS.get(metric_name, float('inf'))

            # Store metric
            _last_metrics[metric_name] = elapsed

            # Log with status indicator
            status = "[OK]" if elapsed < target_time else "[SLOW]"
            print(f"[PERF] {metric_name}: {elapsed*1000:.1f}ms {status} (target: {target_time*1000:.0f}ms)")

            # Warn if exceeded (but don't block)
            if elapsed > target_time:
                overage_ms = (elapsed - target_time) * 1000
                warning = f"{metric_name} exceeded target by {overage_ms:.0f}ms"
                _warnings.append(warning)
                print(f"[PERF WARNING] {warning}")

            return result
        return wrapper
    return decorator


async def measure_performance_async(metric_name: str, target: Optional[float] = None) -> Callable:
    """
    Async version of measure_performance decorator.

    Args:
        metric_name: Name of the metric
        target: Optional target time in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start

            # Get target time
            target_time = target if target is not None else TARGETS.get(metric_name, float('inf'))

            # Store metric
            _last_metrics[metric_name] = elapsed

            # Log with status indicator
            status = "[OK]" if elapsed < target_time else "[SLOW]"
            print(f"[PERF] {metric_name}: {elapsed*1000:.1f}ms {status} (target: {target_time*1000:.0f}ms)")

            # Warn if exceeded (but don't block)
            if elapsed > target_time:
                overage_ms = (elapsed - target_time) * 1000
                warning = f"{metric_name} exceeded target by {overage_ms:.0f}ms"
                _warnings.append(warning)
                print(f"[PERF WARNING] {warning}")

            return result
        return wrapper
    return decorator


def get_last_metrics() -> Dict[str, float]:
    """Get metrics from last turn."""
    return _last_metrics.copy()


def get_warnings() -> list:
    """Get performance warnings from last turn."""
    return _warnings.copy()


def reset_metrics():
    """Clear metrics for new turn."""
    global _last_metrics, _warnings
    _last_metrics = {}
    _warnings = []


def get_summary() -> Dict[str, Any]:
    """Get performance summary for last turn."""
    return {
        "metrics": _last_metrics.copy(),
        "warnings": _warnings.copy(),
        "total_time": sum(_last_metrics.values()),
        "within_targets": len(_warnings) == 0
    }
