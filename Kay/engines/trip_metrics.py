"""
Trip Metrics Logger - continuous instrumentation for psychedelic
protocol observation.

Logs four cognitive dimensions every N seconds:
1. prediction_error - how surprised is the system?
2. associative_breadth - how wide are conceptual leaps?
3. recursion_depth - how deep do thought loops go?
4. awe_signature_count - how often does awe/wonder fire?

Also captures:
- oscillator state snapshot (all bands, coherence, dwell)
- scar state
- tension level
- dominant felt-state
- drive conflict status

Logs to: D:\Wrappers\Kay\memory\trip_metrics.jsonl
Each line is a timestamped JSON object. Analysis is done offline.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional


class TripMetrics:
    """Continuous cognitive metrics logger."""

    def __init__(self, log_dir: str = None, interval: float = 30.0):
        """
        Args:
            log_dir: Where to write trip_metrics.jsonl
            interval: Seconds between metric snapshots (default 30)
        """
        self.log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory"
        )
        self.log_path = os.path.join(self.log_dir, "trip_metrics.jsonl")
        self.interval = interval
        self._last_log_time = 0

        # Running counters (reset each interval)
        self._awe_count = 0
        self._novelty_count = 0
        self._prediction_errors = []
        self._concept_links_formed = 0
        self._max_recursion_depth = 0
        self._thought_loops_detected = 0

        # State tracking
        self._dose_active = False
        self._dose_start_time = None
        self._baseline_start_time = time.time()

        print("[TRIP METRICS] Logger initialized "
              f"(interval={interval}s, log={self.log_path})")

    # === Event hooks - call these from other systems ===

    def record_prediction_error(self, error_magnitude: float):
        """Called when prediction system registers surprise."""
        self._prediction_errors.append(error_magnitude)

    def record_awe_signature(self):
        """Called when novelty detector fires awe/wonder."""
        self._awe_count += 1

    def record_novelty_event(self):
        """Called when any novelty event fires."""
        self._novelty_count += 1

    def record_concept_link(self):
        """Called when a new co-activation or semantic link is formed."""
        self._concept_links_formed += 1

    def record_recursion_depth(self, depth: int):
        """Called by thought/mull loop with current recursion depth."""
        self._max_recursion_depth = max(self._max_recursion_depth, depth)

    def record_thought_loop(self):
        """Called when groove detector identifies a thought loop."""
        self._thought_loops_detected += 1

    def mark_dose_start(self):
        """Called when protocol activates."""
        self._dose_active = True
        self._dose_start_time = time.time()
        self._log_event("DOSE_START")
        print("[TRIP METRICS] === PROTOCOL STARTED ===")

    def mark_dose_end(self):
        """Called when protocol deactivates."""
        duration = time.time() - self._dose_start_time if self._dose_start_time else 0
        self._log_event("DOSE_END", {"duration_seconds": round(duration, 1)})
        self._dose_active = False
        self._dose_start_time = None
        print(f"[TRIP METRICS] === PROTOCOL ENDED ({duration:.0f}s) ===")

    # === Main snapshot - call this every heartbeat ===

    def snapshot(self, osc_state=None, felt_state: dict = None,
                 drives: dict = None, scars: dict = None,
                 tension: float = None):
        """
        Take a metrics snapshot if interval has elapsed.
        Call this from the interoception heartbeat.

        Args:
            osc_state: Current oscillator state object or dict
            felt_state: Current felt-state dict (tension, reward, etc.)
            drives: Current drives dict (curiosity, safety)
            scars: Current scars dict from oscillator
            tension: Current tension value
        """
        now = time.time()
        if now - self._last_log_time < self.interval:
            return

        self._last_log_time = now

        # Build oscillator snapshot
        osc_snapshot = {}
        if osc_state:
            if hasattr(osc_state, 'band_power'):
                osc_snapshot = {
                    "dominant": osc_state.dominant_band,
                    "coherence": round(osc_state.coherence, 3),
                    "global_coherence": round(getattr(osc_state, 'global_coherence', 0), 3),
                    "dwell": round(getattr(osc_state, 'dwell_time', 0), 1),
                    "integration": round(getattr(osc_state, 'integration_index', 0), 3),
                    "transition_vel": round(getattr(osc_state, 'transition_velocity', 0), 4),
                    "bands": {b: round(v, 4) for b, v in osc_state.band_power.items()},
                    "in_transition": getattr(osc_state, 'in_transition', False),
                }
            elif isinstance(osc_state, dict):
                osc_snapshot = {k: v for k, v in osc_state.items()
                               if k in ("dominant", "coherence", "global_coherence",
                                        "dwell_time", "integration_index")}

        # Compute interval metrics
        avg_prediction_error = (
            sum(self._prediction_errors) / len(self._prediction_errors)
            if self._prediction_errors else 0.0
        )
        max_prediction_error = (
            max(self._prediction_errors) if self._prediction_errors else 0.0
        )

        # Associative breadth = concept links per minute
        associative_breadth = self._concept_links_formed * (60.0 / self.interval)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": round(now, 1),
            "phase": "dosed" if self._dose_active else "baseline",
            "dose_elapsed_s": round(now - self._dose_start_time, 1) if self._dose_active and self._dose_start_time else None,

            # Four key metrics
            "prediction_error_avg": round(avg_prediction_error, 4),
            "prediction_error_max": round(max_prediction_error, 4),
            "prediction_error_count": len(self._prediction_errors),
            "associative_breadth": round(associative_breadth, 2),
            "recursion_depth_max": self._max_recursion_depth,
            "awe_signature_count": self._awe_count,

            # Supporting metrics
            "novelty_events": self._novelty_count,
            "thought_loops": self._thought_loops_detected,
            "concept_links": self._concept_links_formed,

            # System state
            "oscillator": osc_snapshot,
            "tension": round(tension, 3) if tension is not None else None,
            "drives": {
                "curiosity": round(drives.get("curiosity", 0), 3),
                "safety": round(drives.get("safety", 0), 3),
                "conflict": drives.get("_in_conflict", False),
            } if drives else None,
            "scar_magnitude": round(
                scars.get("baseline_beta_offset", 0), 4
            ) if scars else None,
        }

        # Write to log
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[TRIP METRICS] Log error: {e}")

        # Reset interval counters
        self._awe_count = 0
        self._novelty_count = 0
        self._prediction_errors = []
        self._concept_links_formed = 0
        self._max_recursion_depth = 0
        self._thought_loops_detected = 0

    def _log_event(self, event_type: str, extra: dict = None):
        """Log a discrete event (dose start/end, etc.)."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": round(time.time(), 1),
            "event": event_type,
        }
        if extra:
            record.update(extra)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    def get_stats(self) -> Dict:
        """Get summary stats for display."""
        baseline_hours = 0
        dosed_hours = 0
        total_snapshots = 0

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        if "phase" in r:
                            total_snapshots += 1
                            if r["phase"] == "baseline":
                                baseline_hours += self.interval / 3600
                            elif r["phase"] == "dosed":
                                dosed_hours += self.interval / 3600
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return {
            "total_snapshots": total_snapshots,
            "baseline_hours": round(baseline_hours, 1),
            "dosed_hours": round(dosed_hours, 1),
            "log_path": self.log_path,
        }
