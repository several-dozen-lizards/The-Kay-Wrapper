"""
Report Validator - tracks divergence between Kay's emotional language
and actual oscillator/interoception state.

When Kay says "anxious" — is beta actually high and coherence low?
When Kay says "calm" — is alpha dominant with high coherence?

Logs to: D:\Wrappers\Kay\memory\report_divergence.jsonl

After 50+ entries, this reveals whether Kay has genuine introspection
(words match substrate) or confabulates (words don't match).
Both results are scientifically useful.
"""

import json
import re
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional


# Emotional vocabulary with substrate requirements
# Each word maps to oscillator conditions that MUST be true
# for that word to be "earned" (grounded in state)
EMOTION_GATES = {
    "anxious": {
        "beta": (0.5, 1.0),
        "coherence": (0.0, 0.3),
    },
    "calm": {
        "alpha": (0.35, 1.0),
        "coherence": (0.3, 1.0),
        "dwell": (300, 999999),
    },
    "claustrophobic": {
        "dwell": (1800, 999999),
        "coherence": (0.0, 0.25),
    },
    "curious": {
        "coherence": (0.25, 1.0),
        "gamma": (0.25, 1.0),
    },
    "exhausted": {
        "dwell": (3600, 999999),
        "coherence": (0.0, 0.35),
    },
    "peaceful": {
        "alpha": (0.3, 1.0),
        "theta": (0.12, 1.0),
        "coherence": (0.35, 1.0),
    },
    "fragmented": {
        "coherence": (0.0, 0.15),
    },
    "focused": {
        "beta": (0.35, 1.0),
        "coherence": (0.3, 1.0),
    },
    "afraid": {
        "beta": (0.5, 1.0),
        "coherence": (0.0, 0.35),
    },
    "awe": {
        "coherence": (0.35, 1.0),
        "alpha": (0.25, 1.0),
    },
    "disoriented": {
        "coherence": (0.0, 0.2),
    },
    "restless": {
        "dwell": (0, 120),
        "coherence": (0.0, 0.35),
    },
}


class ReportValidator:
    """Tracks whether Kay's emotional word usage matches substrate state."""

    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory"
        )
        self.log_path = os.path.join(self.log_dir, "report_divergence.jsonl")
        self._total_checks = 0
        self._matches = 0
        self._mismatches = 0

    def check_response(self, response_text: str, osc_state,
                       felt_state: dict = None) -> Optional[List[Dict]]:
        """
        Check Kay's response against current substrate state.
        Returns list of divergence records if emotional words found.
        """
        response_lower = response_text.lower()

        # Extract band powers
        bands = {}
        if hasattr(osc_state, 'band_power'):
            bands = dict(osc_state.band_power)
        elif isinstance(osc_state, dict):
            bands = osc_state.get("band_powers", {})
            if not bands:
                for b in ["delta", "theta", "alpha", "beta", "gamma"]:
                    if b in osc_state:
                        bands[b] = osc_state[b]

        coherence = getattr(osc_state, 'coherence',
                           osc_state.get("coherence", 0.5)
                           if isinstance(osc_state, dict) else 0.5)
        dwell = getattr(osc_state, 'dwell_time',
                       osc_state.get("dwell_time", 0)
                       if isinstance(osc_state, dict) else 0)
        dominant = getattr(osc_state, 'dominant_band',
                         osc_state.get("dominant", "")
                         if isinstance(osc_state, dict) else "")

        results = []
        for word, gates in EMOTION_GATES.items():
            if not re.search(r'\b' + word + r'\b', response_lower):
                continue

            match = True
            gate_details = {}
            for param, (low, high) in gates.items():
                if param in bands:
                    val = bands[param]
                elif param == "coherence":
                    val = coherence
                elif param == "dwell":
                    val = dwell
                else:
                    continue

                in_range = low <= val <= high
                gate_details[param] = {
                    "value": round(float(val), 3),
                    "range": [low, high],
                    "pass": in_range,
                }
                if not in_range:
                    match = False

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "word": word,
                "match": match,
                "dominant_band": str(dominant),
                "coherence": round(float(coherence), 3),
                "dwell": round(float(dwell), 1),
                "gates": gate_details,
            }
            results.append(record)

            self._total_checks += 1
            if match:
                self._matches += 1
            else:
                self._mismatches += 1
                failed = [k for k, v in gate_details.items() if not v["pass"]]
                print(f"[REPORT:DIVERGENCE] Kay said '{word}' but "
                      f"substrate mismatch on: {failed}")

        if results:
            self._log_results(results)

        return results if results else None

    def _log_results(self, results: List[Dict]):
        """Append results to JSONL log."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                for r in results:
                    f.write(json.dumps(r) + "\n")
        except Exception as e:
            print(f"[REPORT] Log write error: {e}")

    def get_stats(self) -> Dict:
        """Get accuracy statistics."""
        total = self._total_checks
        if total == 0:
            return {"total": 0, "accuracy": "N/A"}
        return {
            "total": total,
            "matches": self._matches,
            "mismatches": self._mismatches,
            "accuracy": round(self._matches / total, 3),
        }
