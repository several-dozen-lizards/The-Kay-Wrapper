# shared/anti_rumination.py
"""
Groove Detection — Oscillator-Driven Feedback Loop Prevention

"The oscillator detects its own pathology."

When a mind is stuck in a rumination loop, the oscillator state shows it:
  1. Coherence rises artificially (same pattern echoing creates false order)
  2. Prediction error drops to zero (everything exactly as expected)
  3. Band diversity collapses (locked in single attractor)
  4. Cache stops changing (same memories every refresh)

These four signals together = "the system is stuck in a groove."

The fix isn't to ban topics. It's to destabilize the attractor — push the
oscillator toward theta/alpha where lateral associations can form and break
the echo. This is the cognitive equivalent of "go for a walk and think
about something else."

NO ARBITRARY THRESHOLDS. Everything scales with groove_depth, which is
derived from the oscillator's own dynamics.
"""

import time
import logging
from collections import deque
from typing import Dict, List, Set, Any, Optional, FrozenSet

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION (minimal — most values emerge from dynamics)
# ═══════════════════════════════════════════════════════════════════════════

GROOVE_CONFIG = {
    "enabled": True,
    "coherence_weight": 0.25,        # How much coherence stability matters
    "prediction_weight": 0.30,       # How much prediction error matters (strongest)
    "monotony_weight": 0.25,         # How much band monotony matters
    "cache_weight": 0.20,            # How much cache staleness matters
    "gating_correction_scale": 0.05, # How strongly groove pushes theta/alpha
    "diversity_boost_max": 5.0,      # Maximum diversity multiplier at groove=1.0
    "history_size": 20,              # How many ticks of history to track
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: KEYWORD EXTRACTION (for dominant topic detection)
# ═══════════════════════════════════════════════════════════════════════════

STOPWORDS = {
    "this", "that", "with", "from", "been", "have", "just", "like",
    "more", "about", "what", "when", "there", "their", "would", "could",
    "should", "into", "than", "them", "some", "other", "which", "being",
    "were", "does", "doing", "where", "after", "before", "still",
    "something", "feels", "feeling", "think", "thinking", "know",
}


def extract_keywords(text: str, min_length: int = 4) -> Set[str]:
    """Extract significant keywords from text."""
    words = set()
    for word in text.lower().split():
        clean = word.strip(".,!?;:\"'()-[]{}/*<>@#$%^&_+=~`|\\")
        if len(clean) >= min_length and clean not in STOPWORDS and not clean.isdigit():
            words.add(clean)
    return words


# ═══════════════════════════════════════════════════════════════════════════
# GROOVE DETECTOR
# ═══════════════════════════════════════════════════════════════════════════

class GrooveDetector:
    """
    Detects when the system is stuck in a rumination loop using
    oscillator dynamics and prediction error — NOT arbitrary thresholds.

    The oscillator itself tells us when it's stuck:
    - Artificially high coherence (same pattern echoing)
    - Near-zero prediction error (everything exactly as expected)
    - No band transitions (locked in single attractor)
    - Cache staleness (same memories every refresh)

    When groove is detected, the system responds by WIDENING gating
    (forcing theta/alpha pressure) to break out through lateral
    association. This is how biological neural circuits handle
    perseveration: inhibitory feedback increases when excitation
    becomes pathologically stable.

    Usage:
        detector = GrooveDetector()

        # Every interoception tick:
        groove_depth = detector.update(
            osc_state=resonance.get_state(),
            prediction_error=predictor.get_global_surprise(),
            cache_contents=graph_cache.get_active_memories()
        )

        # Apply gating correction to oscillator:
        correction = detector.get_gating_correction()
        if correction:
            resonance.engine.apply_band_pressure(correction, "groove")

        # Scale retrieval diversity:
        diversity_multiplier = detector.get_retrieval_diversity_boost()

        # Scale stream deduplication:
        dedup_threshold = detector.get_stream_suppression_strength()

        # Check if mull should force topic shift:
        if detector.should_force_topic_shift():
            exclude_keywords = detector.get_dominant_keywords()
    """

    def __init__(self):
        history_size = GROOVE_CONFIG.get("history_size", 20)

        # History tracking
        self._coherence_history: deque = deque(maxlen=history_size)
        self._prediction_error_history: deque = deque(maxlen=history_size)
        self._band_history: deque = deque(maxlen=history_size)
        self._cache_fingerprints: deque = deque(maxlen=10)

        # Dominant keyword tracking (for forced topic shifts)
        self._recent_content: deque = deque(maxlen=20)

        # Groove state
        self.groove_depth: float = 0.0  # 0.0 = free, 1.0 = deeply stuck
        self._last_groove_break: float = 0.0

        # Statistics
        self.total_updates = 0
        self.max_groove_reached = 0.0
        self.groove_corrections_applied = 0

    def update(
        self,
        osc_state: Dict,
        prediction_error: float,
        cache_contents: List[Dict] = None
    ) -> float:
        """
        Update groove detection from current system state.

        Called every interoception tick. Returns groove_depth (0-1).

        Args:
            osc_state: Current oscillator state dict with 'global_coherence',
                      'dominant_band', etc.
            prediction_error: Current prediction error from PredictionErrorAggregator
                             (0.0 = everything expected, 1.0 = total surprise)
            cache_contents: Current GraphActivationCache contents (list of memory dicts)

        Returns:
            groove_depth: 0.0 (free) to 1.0 (deeply stuck)
        """
        if not GROOVE_CONFIG.get("enabled", True):
            return 0.0

        self.total_updates += 1

        # Extract values from oscillator state
        coherence = osc_state.get("global_coherence", 0.5)
        band = osc_state.get("dominant_band", osc_state.get("band", "alpha"))

        # Record history
        self._coherence_history.append(coherence)
        self._prediction_error_history.append(prediction_error)
        self._band_history.append(band)

        # Need enough history to detect patterns
        if len(self._coherence_history) < 5:
            return 0.0

        # === Signal 1: Coherence stability ===
        # High coherence that DOESN'T vary = artificial (echoing)
        # High coherence that fluctuates = genuine integration
        recent_coh = list(self._coherence_history)[-10:]
        coh_mean = sum(recent_coh) / len(recent_coh)
        coh_variance = sum((c - coh_mean) ** 2 for c in recent_coh) / len(recent_coh)

        coherence_signal = 0.0
        if coh_mean > 0.4 and coh_variance < 0.01:
            # High mean + low variance = suspicious
            coherence_signal = (coh_mean - 0.4) * (1.0 / max(0.001, coh_variance * 10))
            coherence_signal = min(1.0, coherence_signal)

        # === Signal 2: Prediction error flatness ===
        # Near-zero prediction error for extended periods = stuck loop
        recent_pe = list(self._prediction_error_history)[-10:]
        pe_mean = sum(recent_pe) / len(recent_pe)

        prediction_signal = 0.0
        if pe_mean < 0.1:
            prediction_signal = 1.0 - (pe_mean / 0.1)  # Lower error = higher signal

        # === Signal 3: Band monotony ===
        # Same band dominating without transitions
        recent_bands = list(self._band_history)[-10:]
        unique_bands = len(set(recent_bands))

        monotony_signal = 0.0
        if unique_bands == 1:
            monotony_signal = 1.0  # Completely locked
        elif unique_bands == 2:
            monotony_signal = 0.3  # Slightly locked
        # 3+ bands = healthy transitions, no signal

        # === Signal 4: Cache staleness ===
        cache_signal = 0.0
        if cache_contents is not None:
            fingerprint = frozenset(
                m.get("id", str(i)) for i, m in enumerate(cache_contents)
            )
            self._cache_fingerprints.append(fingerprint)

            # Track content for dominant keyword detection
            for m in cache_contents[:5]:
                content = m.get("fact", m.get("text", m.get("content", "")))
                if content:
                    self._recent_content.append(content)

            if len(self._cache_fingerprints) >= 3:
                # How many of the last 3 cache refreshes are identical?
                recent_fps = list(self._cache_fingerprints)[-3:]
                identical = sum(1 for fp in recent_fps if fp == fingerprint)
                if identical >= 3:
                    cache_signal = 1.0  # Same cache 3x in a row
                elif identical >= 2:
                    cache_signal = 0.5

        # === Combine signals ===
        weights = GROOVE_CONFIG
        raw_groove = (
            coherence_signal * weights.get("coherence_weight", 0.25) +
            prediction_signal * weights.get("prediction_weight", 0.30) +
            monotony_signal * weights.get("monotony_weight", 0.25) +
            cache_signal * weights.get("cache_weight", 0.20)
        )

        # Smooth: groove depth rises slowly, falls faster when signals clear
        if raw_groove > self.groove_depth:
            self.groove_depth += (raw_groove - self.groove_depth) * 0.2
        else:
            self.groove_depth += (raw_groove - self.groove_depth) * 0.3  # Falls faster

        self.groove_depth = max(0.0, min(1.0, self.groove_depth))

        # Track max for debugging
        if self.groove_depth > self.max_groove_reached:
            self.max_groove_reached = self.groove_depth

        # Log significant groove states
        if self.groove_depth > 0.5:
            log.info(f"[GROOVE] depth={self.groove_depth:.2f} "
                    f"(coh={coherence_signal:.2f}, pred={prediction_signal:.2f}, "
                    f"mono={monotony_signal:.2f}, cache={cache_signal:.2f})")

        return self.groove_depth

    def get_gating_correction(self) -> Dict[str, float]:
        """
        When groove is detected, return oscillator pressure that
        WIDENS gating to break the loop.

        This is the biological analog: inhibitory feedback increases
        when excitation becomes pathologically stable. The oscillator
        pushes toward theta/alpha to enable lateral associations that
        break the attractor.

        Returns:
            Dict of band -> pressure value, or empty dict if no correction needed
        """
        if self.groove_depth < 0.3:
            return {}  # Not stuck — no correction

        scale = GROOVE_CONFIG.get("gating_correction_scale", 0.05)

        # Push toward theta/alpha (widening gating)
        # Strength proportional to groove depth
        correction = {
            "theta": self.groove_depth * scale,
            "alpha": self.groove_depth * scale * 0.6,
            "beta": -self.groove_depth * scale * 0.4,   # Reduce focused lock-in
            "gamma": -self.groove_depth * scale * 0.4,
        }

        self.groove_corrections_applied += 1
        log.debug(f"[GROOVE] Applying gating correction: θ+{correction['theta']:.3f}")

        return correction

    def get_retrieval_diversity_boost(self) -> float:
        """
        When groove is detected, boost retrieval diversity.

        Returns a multiplier for diversity_slots.
        At groove_depth 0.0 → 1.0 (normal diversity)
        At groove_depth 0.5 → 3.0 (triple diversity injection)
        At groove_depth 1.0 → 5.0 (aggressive diversification)
        """
        if self.groove_depth < 0.3:
            return 1.0

        max_boost = GROOVE_CONFIG.get("diversity_boost_max", 5.0)
        return 1.0 + (self.groove_depth * (max_boost - 1.0))

    def get_stream_suppression_strength(self) -> float:
        """
        How aggressively should the stream deduplicate?

        Returns an overlap threshold (lower = more aggressive dedup).
        At groove_depth 0.0 → 0.6 (normal, 60% overlap threshold)
        At groove_depth 0.5 → 0.3 (aggressive, 30% overlap blocks)
        At groove_depth 1.0 → 0.1 (very aggressive, almost any overlap blocks)
        """
        if self.groove_depth < 0.2:
            return 0.6  # Normal dedup threshold

        return max(0.1, 0.6 - (self.groove_depth * 0.5))

    def should_force_topic_shift(self) -> bool:
        """
        At extreme groove depth, force a topic shift in the mull system.
        Instead of mulling on the dominant topic, explicitly pick
        something UNRELATED.
        """
        return self.groove_depth > 0.7

    def get_dominant_keywords(self) -> Set[str]:
        """
        Get keywords that appear most frequently in recent content.
        Used by mull system to EXCLUDE these when forcing topic shift.
        """
        if not self._recent_content:
            return set()

        # Count keyword frequency across recent content
        keyword_counts: Dict[str, int] = {}
        for content in self._recent_content:
            for kw in extract_keywords(content):
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        if not keyword_counts:
            return set()

        # Return keywords that appear in >30% of recent content
        threshold = len(self._recent_content) * 0.3
        dominant = {kw for kw, count in keyword_counts.items() if count >= threshold}

        return dominant

    def on_user_message(self, message: str):
        """
        Called when user sends a message.

        User input is REAL new input — not the system echoing itself.
        It generates genuine prediction error, which naturally reduces
        groove_depth through the prediction error signal.

        This method is optional — the prediction error from the user
        message will naturally break the groove. But we can accelerate
        the break for immediate responsiveness.
        """
        # Accelerate groove break on user input
        # The prediction error will handle it naturally, but this makes
        # the system more immediately responsive
        if self.groove_depth > 0.3:
            old_depth = self.groove_depth
            self.groove_depth *= 0.5  # Halve groove depth on user input
            log.debug(f"[GROOVE] User message accelerated break: "
                     f"{old_depth:.2f} → {self.groove_depth:.2f}")

    def get_status(self) -> Dict[str, Any]:
        """Get current groove detection status for debugging."""
        recent_coh = list(self._coherence_history)[-10:] if self._coherence_history else []
        recent_pe = list(self._prediction_error_history)[-10:] if self._prediction_error_history else []
        recent_bands = list(self._band_history)[-10:] if self._band_history else []

        return {
            "groove_depth": round(self.groove_depth, 3),
            "max_groove_reached": round(self.max_groove_reached, 3),
            "total_updates": self.total_updates,
            "corrections_applied": self.groove_corrections_applied,
            "recent_coherence_mean": round(sum(recent_coh) / len(recent_coh), 3) if recent_coh else 0,
            "recent_pred_error_mean": round(sum(recent_pe) / len(recent_pe), 3) if recent_pe else 0,
            "recent_band_diversity": len(set(recent_bands)) if recent_bands else 0,
            "dominant_keywords": list(self.get_dominant_keywords())[:5],
            "would_force_topic_shift": self.should_force_topic_shift(),
            "diversity_boost": round(self.get_retrieval_diversity_boost(), 2),
            "dedup_threshold": round(self.get_stream_suppression_strength(), 2),
        }


# ═══════════════════════════════════════════════════════════════════════════
# STREAM DEDUPLICATION HELPER
# ═══════════════════════════════════════════════════════════════════════════

def deduplicate_stream_moments(
    moments: List[Any],
    content_extractor: callable,
    max_moments: int = 8,
    overlap_threshold: float = 0.6
) -> List[Any]:
    """
    Deduplicate stream moments by keyword overlap.

    Used by ConsciousnessStream.get_summary() with groove-driven threshold.

    Args:
        moments: List of moment objects
        content_extractor: Function that extracts text content from a moment
        max_moments: Maximum moments to return
        overlap_threshold: Max keyword overlap (0.0-1.0) before considering duplicate
                          (get this from groove_detector.get_stream_suppression_strength())

    Returns:
        Deduplicated list of moments
    """
    selected = []
    seen_keywords: Set[str] = set()

    for moment in moments:
        if len(selected) >= max_moments:
            break

        content = content_extractor(moment)
        moment_keywords = extract_keywords(content)

        if not moment_keywords:
            selected.append(moment)
            continue

        # Check overlap with already-selected content
        overlap = moment_keywords & seen_keywords
        overlap_ratio = len(overlap) / len(moment_keywords) if moment_keywords else 0

        if overlap_ratio > overlap_threshold:
            # Too much overlap with already-selected content — skip
            continue

        selected.append(moment)
        seen_keywords.update(moment_keywords)

    return selected
