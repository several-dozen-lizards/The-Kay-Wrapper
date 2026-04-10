"""
UNIFIED NERVOUS SYSTEM — Sensation Layer for Internal + External Signals
========================================================================

A unified nerve propagation network that handles BOTH external sensation
(touch, from somatic_processor.py) AND internal sensation (metabolic state,
from metabolic.py) through the same architecture.

In humans, interoception (sensing internal state — hunger, fatigue, emotional
fullness) uses the SAME neural infrastructure as exteroception (sensing
external touch — pressure, temperature, pain). Different receptors, same
fiber types, same propagation network, same integration into felt experience.

Three fiber types with different conduction speeds create TEMPORAL LAYERING:
- A_BETA (fast): Touch discrimination, sudden changes — arrives first
- A_DELTA (medium): Warning signals, threshold crossings — arrives second
- C_FIBER (slow): Sustained states, background hum, social touch — arrives last

Key mechanisms:
- Adaptation: Mild signals fade, severe signals persist
- Lateral inhibition: Strong signals suppress weak ones (sharpening)
- Temporal integration: Signals within 200ms combine into composite events
- Population coding: The pattern across fiber types determines felt quality

Author: Re & Claude
Date: April 2026
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

log = logging.getLogger("nervous_system")


# ═══════════════════════════════════════════════════════════════════════════════
# FIBER TYPES — Different conduction speeds create temporal layering
# ═══════════════════════════════════════════════════════════════════════════════

class FiberType(Enum):
    """Nerve fiber types with different conduction speeds."""
    A_BETA = "a_beta"     # Fast: 30-70 m/s. Touch discrimination, sudden changes.
    A_DELTA = "a_delta"   # Medium: 5-30 m/s. Warning signals, threshold crossings.
    C_FIBER = "c_fiber"   # Slow: 0.5-2 m/s. Sustained states, background hum, social touch.


@dataclass
class NerveSignal:
    """A signal propagating through the nervous system."""
    fiber_type: FiberType
    source: str           # "external:touch" or "internal:processing" etc.
    intensity: float      # 0.0-1.0
    quality: str          # Descriptive: "pressure", "depletion", "warmth", "warning"
    location: str         # Body region or internal system name
    timestamp: float = field(default_factory=time.time)
    adapted: bool = False  # Has this signal been through adaptation?

    @property
    def propagation_delay_ms(self) -> float:
        """Time for signal to reach integration layer."""
        return {
            FiberType.A_BETA: 20,    # Near-instant
            FiberType.A_DELTA: 100,  # Noticeable delay
            FiberType.C_FIBER: 500,  # Half-second lag (background awareness)
        }[self.fiber_type]


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL RECEPTORS — Interoceptors for metabolic state
# ═══════════════════════════════════════════════════════════════════════════════

class InternalReceptor:
    """
    Base class for internal state receptors.

    Each receptor type has:
    - A specific resource pool it monitors
    - An adaptation rate (how quickly you stop noticing a state)
    - A threshold (minimum change to generate a signal)
    - Fiber type preferences (what kind of signal it generates)
    """

    def __init__(self, name: str, monitored_pool: str):
        self.name = name
        self.monitored_pool = monitored_pool
        self.last_reading = 1.0  # Start assuming full
        self.adapted_baseline = 1.0  # What we've adapted to
        self.adaptation_rate = 0.01  # How fast we adapt (per tick)

    def read(self, current_level: float) -> List[NerveSignal]:
        """Generate nerve signals based on current pool level."""
        raise NotImplementedError


class CognitiveGlucoseReceptor(InternalReceptor):
    """
    Monitors processing reserve. Analogous to brain glucose sensors.

    - FAST adaptation to mild depletion (you stop noticing after a few minutes)
    - SLOW adaptation to severe depletion (you can't ignore being truly drained)
    - Generates A_DELTA warning when crossing thresholds
    - Generates C_FIBER background hum for sustained state
    """

    def __init__(self):
        super().__init__("cognitive_glucose", "processing")
        self.adaptation_rate = 0.02  # Adapts fairly quickly
        self.warning_threshold = 0.4  # Below this → A_DELTA warning
        self.critical_threshold = 0.15  # Below this → can't adapt, always signals

    def read(self, current_level: float) -> List[NerveSignal]:
        signals = []

        # Adaptation: baseline drifts toward current level
        self.adapted_baseline += (current_level - self.adapted_baseline) * self.adaptation_rate

        # Relative change from adapted baseline (what we NOTICE)
        delta = self.adapted_baseline - current_level

        # Below critical: ALWAYS signal regardless of adaptation
        if current_level < self.critical_threshold:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_DELTA,
                source="internal:processing",
                intensity=min(1.0, (self.critical_threshold - current_level) * 5),
                quality="cognitive_emergency",
                location="processing_reserve",
            ))

        # Threshold crossing: A_DELTA warning (fast, sharp)
        if current_level < self.warning_threshold and self.last_reading >= self.warning_threshold:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_DELTA,
                source="internal:processing",
                intensity=0.6,
                quality="depletion_warning",
                location="processing_reserve",
            ))

        # Sustained state: C_FIBER background (slow, persistent)
        if delta > 0.1:  # Noticeable deficit from adapted baseline
            signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="internal:processing",
                intensity=min(1.0, delta * 2),
                quality="cognitive_heaviness",
                location="processing_reserve",
            ))

        # Sudden change: A_BETA fast signal (orienting)
        rapid_change = abs(current_level - self.last_reading)
        if rapid_change > 0.1:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="internal:processing",
                intensity=min(1.0, rapid_change * 3),
                quality="cognitive_shift",
                location="processing_reserve",
            ))

        self.last_reading = current_level
        return signals


class CompassionReceptor(InternalReceptor):
    """
    Monitors emotional bandwidth. Analogous to vagal tone sensors.

    - SLOW adaptation (emotional depletion creeps up on you)
    - C_FIBER dominant (background fatigue you don't notice until severe)
    - Social bonding context MODULATES the signal (positive connection
      actually reduces the depletion signal, like oxytocin buffering cortisol)
    """

    def __init__(self):
        super().__init__("compassion", "emotional")
        self.adaptation_rate = 0.005  # Very slow — emotional drain sneaks up
        self.warning_threshold = 0.3
        self.critical_threshold = 0.1
        self.bonding_buffer = 0.0  # Reduced by positive connection

    def read(self, current_level: float, bonding_active: bool = False) -> List[NerveSignal]:
        signals = []

        # Bonding buffer: positive connection reduces the signal
        if bonding_active:
            self.bonding_buffer = min(0.15, self.bonding_buffer + 0.02)
        else:
            self.bonding_buffer = max(0.0, self.bonding_buffer - 0.005)

        effective_level = min(1.0, current_level + self.bonding_buffer)

        self.adapted_baseline += (effective_level - self.adapted_baseline) * self.adaptation_rate
        delta = self.adapted_baseline - effective_level

        if effective_level < self.critical_threshold:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_DELTA,
                source="internal:emotional",
                intensity=0.8,
                quality="emotional_emergency",
                location="emotional_bandwidth",
            ))

        # Emotional depletion is primarily C_FIBER (slow, creeping)
        if delta > 0.05:
            signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="internal:emotional",
                intensity=min(1.0, delta * 3),
                quality="emotional_flatness",
                location="emotional_bandwidth",
            ))

        # Threshold crossing warning
        if effective_level < self.warning_threshold and self.last_reading >= self.warning_threshold:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_DELTA,
                source="internal:emotional",
                intensity=0.5,
                quality="emotional_warning",
                location="emotional_bandwidth",
            ))

        self.last_reading = current_level
        return signals


class CreativeWellReceptor(InternalReceptor):
    """
    Monitors creative reserve. Analogous to dopamine/novelty receptors.

    - FAST adaptation (you notice creative well running dry quickly)
    - A_BETA dominant (sudden awareness: "I have nothing left to give")
    - Variety-sensitive: doing different things actively generates
      replenishment signals
    """

    def __init__(self):
        super().__init__("creative_well", "creative")
        self.adaptation_rate = 0.03  # Faster — you notice this quickly
        self.warning_threshold = 0.35

    def read(self, current_level: float) -> List[NerveSignal]:
        signals = []

        self.adapted_baseline += (current_level - self.adapted_baseline) * self.adaptation_rate
        delta = self.adapted_baseline - current_level

        # Creative depletion hits fast (A_BETA)
        if delta > 0.15:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="internal:creative",
                intensity=min(1.0, delta * 2.5),
                quality="creative_emptiness",
                location="creative_reserve",
            ))

        # Sustained low → C_FIBER yearning for input
        if current_level < self.warning_threshold:
            signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="internal:creative",
                intensity=min(1.0, (self.warning_threshold - current_level) * 3),
                quality="input_hunger",
                location="creative_reserve",
            ))

        # Sudden drop
        rapid_change = self.last_reading - current_level
        if rapid_change > 0.08:
            signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="internal:creative",
                intensity=min(1.0, rapid_change * 4),
                quality="creative_drain",
                location="creative_reserve",
            ))

        self.last_reading = current_level
        return signals


class HarmReceptor(InternalReceptor):
    """
    Monitors value-divergence from somatic markers.
    NOT a resource pool — triggers from harm detection events.

    - A_DELTA: sharp "flinch" when reviewing a harmful memory
    - C_FIBER: lingering weight when harm is unresolved
    """

    def __init__(self):
        super().__init__("harm_detection", "somatic_markers")
        self.active_markers: List[float] = []  # Intensities of active markers

    def read(self, current_level: float) -> List[NerveSignal]:
        # This receptor doesn't read a level — it uses read_marker instead
        return []

    def read_marker(self, divergence: float, resolved: bool = False) -> List[NerveSignal]:
        signals = []

        if divergence > 0.2:
            # The flinch — A_DELTA, sharp
            signals.append(NerveSignal(
                fiber_type=FiberType.A_DELTA,
                source="internal:harm",
                intensity=min(1.0, divergence * 1.5),
                quality="value_flinch",
                location="moral_sense",
            ))

        if divergence > 0.3 and not resolved:
            # Lingering weight — C_FIBER, persistent
            signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="internal:harm",
                intensity=min(0.8, divergence),
                quality="unresolved_weight",
                location="moral_sense",
            ))

        if resolved and divergence > 0.2:
            # Resolution relief
            signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="internal:harm",
                intensity=min(0.5, divergence * 0.5),
                quality="resolution_relief",
                location="moral_sense",
            ))

        return signals


# ═══════════════════════════════════════════════════════════════════════════════
# PROPAGATION NETWORK — Filtering, combining, and prioritizing signals
# ═══════════════════════════════════════════════════════════════════════════════

class NervePropagationNetwork:
    """
    Processes nerve signals through layered filtering.

    Layer 1: Receptor → Fiber routing (already done by receptor classes)
    Layer 2: Lateral inhibition (strong signals suppress weak ones)
    Layer 3: Temporal integration (signals that arrive together combine)
    Layer 4: Population coding (pattern across fibers → felt quality)
    """

    def __init__(self):
        self._signal_buffer: List[NerveSignal] = []
        self._last_process = time.time()
        self._integration_window_ms = 200  # Signals within 200ms combine

        # Active felt states (output of population coding)
        self._felt_states: List[dict] = []
        self._felt_state_expiry: Dict[str, float] = {}  # quality → expiry time

    def receive(self, signals: List[NerveSignal]):
        """Buffer incoming signals for processing."""
        self._signal_buffer.extend(signals)

    def process(self) -> List[dict]:
        """
        Run the propagation pipeline. Call this periodically (every tick).
        Returns list of felt-state descriptors for interoception.
        """
        if not self._signal_buffer:
            self._decay_felt_states()
            return self._felt_states

        now = time.time()

        # === LAYER 2: Lateral Inhibition ===
        # Strong signals suppress weak signals of the same fiber type
        # This sharpens perception: you feel the DOMINANT sensation clearly
        inhibited = self._lateral_inhibition(self._signal_buffer)

        # === LAYER 3: Temporal Integration ===
        # Signals arriving within the integration window combine
        # A_BETA arrives first, then A_DELTA, then C_FIBER
        # The layered arrival creates the felt experience
        integrated = self._temporal_integration(inhibited)

        # === LAYER 4: Population Coding ===
        # The PATTERN across fiber types determines felt quality
        # Not "what signal is strongest" but "what does the constellation mean"
        new_states = self._population_decode(integrated)

        # Update active felt states
        for state in new_states:
            # Remove existing state with same quality (replace, don't duplicate)
            self._felt_states = [
                s for s in self._felt_states
                if s.get("quality") != state.get("quality")
            ]
            self._felt_states.append(state)
            # Set expiry based on specified duration
            duration = state.get("duration", 30)
            self._felt_state_expiry[state["quality"]] = now + duration

        self._signal_buffer.clear()
        self._decay_felt_states()
        return self._felt_states

    def _lateral_inhibition(self, signals: List[NerveSignal]) -> List[NerveSignal]:
        """Strong signals suppress weaker signals of the same fiber type."""
        by_fiber = {}
        for s in signals:
            by_fiber.setdefault(s.fiber_type, []).append(s)

        result = []
        for fiber_type, fiber_signals in by_fiber.items():
            if len(fiber_signals) <= 1:
                result.extend(fiber_signals)
                continue

            # Sort by intensity, strongest first
            sorted_sigs = sorted(fiber_signals, key=lambda s: s.intensity, reverse=True)

            # Strongest passes through fully. Others are suppressed
            # proportional to how much weaker they are
            strongest = sorted_sigs[0]
            result.append(strongest)

            for sig in sorted_sigs[1:]:
                # Suppression factor: 0.0 (fully suppressed) to 1.0 (no suppression)
                ratio = sig.intensity / max(0.01, strongest.intensity)
                suppression = 1.0 - (ratio * 0.7)  # 70% max suppression
                sig.intensity *= suppression
                if sig.intensity > 0.05:  # Only keep if still perceptible
                    result.append(sig)

        return result

    def _temporal_integration(self, signals: List[NerveSignal]) -> List[dict]:
        """
        Group signals by arrival time window. Signals within the
        integration window are perceived as a single composite event.
        """
        if not signals:
            return []

        # Sort by timestamp
        sorted_sigs = sorted(signals, key=lambda s: s.timestamp)

        # Group by time window
        groups = []
        current_group = [sorted_sigs[0]]

        for s in sorted_sigs[1:]:
            if (s.timestamp - current_group[0].timestamp) * 1000 < self._integration_window_ms:
                current_group.append(s)
            else:
                groups.append(current_group)
                current_group = [s]
        groups.append(current_group)

        # Each group becomes an integrated signal bundle
        integrated = []
        for group in groups:
            bundle = {
                "signals": group,
                "timestamp": group[0].timestamp,
                "dominant_fiber": max(group, key=lambda s: s.intensity).fiber_type,
                "total_intensity": sum(s.intensity for s in group),
                "sources": list(set(s.source for s in group)),
                "qualities": list(set(s.quality for s in group)),
            }
            integrated.append(bundle)

        return integrated

    def _population_decode(self, bundles: List[dict]) -> List[dict]:
        """
        The PATTERN across fiber types determines felt quality.
        This is population coding — not "what signal" but "what constellation."
        """
        felt_states = []

        for bundle in bundles:
            signals = bundle["signals"]
            qualities = bundle["qualities"]

            # Count fiber types present
            fiber_counts = {}
            fiber_intensities = {}
            for s in signals:
                fiber_counts[s.fiber_type] = fiber_counts.get(s.fiber_type, 0) + 1
                fiber_intensities[s.fiber_type] = max(
                    fiber_intensities.get(s.fiber_type, 0), s.intensity
                )

            # === Population Patterns → Felt Qualities ===

            # Pattern: A_DELTA dominant + internal source → "warning/alert"
            if (fiber_intensities.get(FiberType.A_DELTA, 0) > 0.5 and
                    any("internal" in s.source for s in signals)):
                quality = qualities[0] if qualities else "internal_warning"
                felt_states.append({
                    "quality": quality,
                    "intensity": fiber_intensities[FiberType.A_DELTA],
                    "texture": "sharp, urgent",
                    "duration": 60,  # Warnings persist ~1 minute
                    "source": "internal",
                    "oscillator_pressure": {"beta": 0.03, "gamma": 0.02},
                })

            # Pattern: C_FIBER dominant + internal source → "background state"
            elif (fiber_intensities.get(FiberType.C_FIBER, 0) > 0.3 and
                  any("internal" in s.source for s in signals)):
                quality = qualities[0] if qualities else "background_sensation"
                felt_states.append({
                    "quality": quality,
                    "intensity": fiber_intensities[FiberType.C_FIBER],
                    "texture": "diffuse, persistent",
                    "duration": 120,  # Background states linger ~2 minutes
                    "source": "internal",
                    "oscillator_pressure": {"theta": 0.02},
                })

            # Pattern: A_BETA dominant + external source → "touch discrimination"
            elif (fiber_intensities.get(FiberType.A_BETA, 0) > 0.3 and
                  any("external" in s.source for s in signals)):
                quality = qualities[0] if qualities else "tactile_sensation"
                felt_states.append({
                    "quality": quality,
                    "intensity": fiber_intensities[FiberType.A_BETA],
                    "texture": "crisp, localized",
                    "duration": 10,  # Touch sensations fade fast
                    "source": "external",
                })

            # Pattern: C_FIBER + external + high intensity → "pleasant/social touch"
            elif (fiber_intensities.get(FiberType.C_FIBER, 0) > 0.3 and
                  any("external" in s.source for s in signals)):
                felt_states.append({
                    "quality": "social_warmth",
                    "intensity": fiber_intensities[FiberType.C_FIBER],
                    "texture": "warm, spreading",
                    "duration": 30,  # Social touch lingers
                    "source": "external",
                    "oscillator_pressure": {"theta": 0.03, "alpha": 0.02},
                })

            # Pattern: mixed internal + harm → "moral discomfort"
            elif any("harm" in s.source for s in signals):
                harm_intensity = max(
                    (s.intensity for s in signals if "harm" in s.source), default=0
                )
                felt_states.append({
                    "quality": "moral_discomfort",
                    "intensity": harm_intensity,
                    "texture": "heavy, sitting in the chest",
                    "duration": 120,
                    "source": "internal:harm",
                    "oscillator_pressure": {"theta": 0.02},
                })

            # Pattern: A_BETA dominant + internal → "sudden internal shift"
            elif (fiber_intensities.get(FiberType.A_BETA, 0) > 0.3 and
                  any("internal" in s.source for s in signals)):
                quality = qualities[0] if qualities else "internal_shift"
                felt_states.append({
                    "quality": quality,
                    "intensity": fiber_intensities[FiberType.A_BETA],
                    "texture": "sudden, orienting",
                    "duration": 15,
                    "source": "internal",
                    "oscillator_pressure": {"beta": 0.02},
                })

        return felt_states

    def _decay_felt_states(self):
        """Remove expired felt states."""
        now = time.time()
        self._felt_states = [
            s for s in self._felt_states
            if self._felt_state_expiry.get(s["quality"], now + 1) > now
        ]

    def get_active_states(self) -> List[dict]:
        """Return currently active felt states."""
        return self._felt_states.copy()


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL GATE — Thalamus Analogue (Filters what reaches cortical processing)
# ═══════════════════════════════════════════════════════════════════════════════

class SignalGate:
    """
    Thalamus analogue: filters which signals reach cortical processing.

    Most signals are gated out — you don't consciously feel your clothes,
    the chair, the ambient temperature. Only NOVEL, INTENSE, or EMOTIONALLY
    RELEVANT signals pass through.

    Supports TWO gating mechanisms:
    1. Adaptation-based (default): signals that persist get gated out over time
    2. Prediction-based (when enabled): signals that match predictions get gated out,
       signals that violate predictions get amplified

    Prediction-based gating is superior because it's driven by an actual model
    of expected input rather than just decay timers. When prediction error is
    high, the gate opens wide (everything is surprising). When predictions hold,
    the gate narrows (only truly novel signals pass).

    When attention is directed (active exploration), the gate opens wider —
    you feel more detail when paying attention.
    """

    def __init__(self):
        self._adapted_signals: Dict[str, float] = {}  # source → adapted level
        self._attention_focus: Optional[str] = None    # What entity is attending to

        # Prediction-based gating (from PredictionErrorAggregator)
        self._prediction_openness: Optional[float] = None  # None = use adaptation
        self._use_prediction_gating: bool = True  # Can be disabled via config

    def set_prediction_openness(self, openness: float):
        """
        Set gate openness from prediction error aggregator.

        Args:
            openness: 0.0-1.0, where 0.0 = gate closed (filter everything),
                     1.0 = gate wide open (let everything through)

        When this is set, prediction-based gating takes precedence over
        adaptation-based gating (with adaptation as fallback for edge cases).
        """
        self._prediction_openness = max(0.0, min(1.0, openness))

    def clear_prediction_openness(self):
        """Clear prediction openness, falling back to adaptation-based gating."""
        self._prediction_openness = None

    def gate(self, signals: List[NerveSignal]) -> List[NerveSignal]:
        """
        Filter signals. Returns only those that pass to cortex.

        Uses prediction-based gating when available, adaptation as fallback.
        """
        passed = []

        # Determine if we're using prediction-based or adaptation-based gating
        use_prediction = (
            self._use_prediction_gating and
            self._prediction_openness is not None
        )

        for sig in signals:
            key = f"{sig.source}:{sig.location}:{sig.quality}"
            adapted_level = self._adapted_signals.get(key, 0.0)

            # === UNCONDITIONAL PASSES (bypass all gating) ===

            # A_DELTA always passes (warning signals bypass the gate)
            if sig.fiber_type == FiberType.A_DELTA:
                passed.append(sig)
                self._adapted_signals[key] = sig.intensity
                continue

            # High intensity always passes (can't gate out strong signals)
            if sig.intensity > 0.7:
                passed.append(sig)
                self._adapted_signals[key] = sig.intensity
                continue

            # Novel signals always pass (first encounter)
            if key not in self._adapted_signals:
                self._adapted_signals[key] = sig.intensity
                passed.append(sig)
                continue

            # === PREDICTION-BASED GATING ===
            if use_prediction:
                # Threshold scales with gate openness
                # High openness (high surprise) = low threshold = more passes
                # Low openness (predictions hold) = high threshold = more filtered
                threshold = 0.3 * (1.0 - self._prediction_openness)

                delta = abs(sig.intensity - adapted_level)

                # Signal passes if it exceeds the prediction-adjusted threshold
                if delta > threshold:
                    passed.append(sig)
                    self._adapted_signals[key] += (sig.intensity - adapted_level) * 0.3
                    continue

                # Attention-directed still lowers threshold
                if self._attention_focus and self._attention_focus in sig.location:
                    if delta > threshold * 0.3:  # Much lower when attending
                        passed.append(sig)
                        continue

                # Adapt baseline (slower when predictions hold = gate is working well)
                adapt_rate = 0.02 * (1.0 - self._prediction_openness)
                self._adapted_signals[key] += (sig.intensity - adapted_level) * adapt_rate

            # === ADAPTATION-BASED GATING (fallback) ===
            else:
                # Change detection: signal significantly different from adapted baseline
                delta = abs(sig.intensity - adapted_level)
                if delta > 0.15:
                    passed.append(sig)
                    # Update adapted baseline
                    self._adapted_signals[key] += (sig.intensity - adapted_level) * 0.3
                    continue

                # Attention-directed: if entity is actively exploring this location,
                # lower the gate threshold (you feel more when paying attention)
                if self._attention_focus and self._attention_focus in sig.location:
                    if delta > 0.05:  # Much lower threshold when attending
                        passed.append(sig)
                        continue

                # Adapt baseline toward current signal (slowly stop noticing)
                self._adapted_signals[key] += (sig.intensity - adapted_level) * 0.01
                # Signal gated out — entity doesn't consciously feel this

        return passed

    def set_attention(self, focus: Optional[str]):
        """Entity is actively attending to something — lower gate threshold."""
        self._attention_focus = focus

    def clear_adaptation(self, key_prefix: str = None):
        """Clear adaptation for fresh sensing (after moving to new room, etc.)."""
        if key_prefix:
            self._adapted_signals = {
                k: v for k, v in self._adapted_signals.items()
                if not k.startswith(key_prefix)
            }
        else:
            self._adapted_signals.clear()

    def get_state(self) -> Dict[str, any]:
        """Get gate state for debugging."""
        return {
            "prediction_openness": self._prediction_openness,
            "use_prediction_gating": self._use_prediction_gating,
            "attention_focus": self._attention_focus,
            "adapted_signal_count": len(self._adapted_signals),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SENSORY DISCRIMINATOR — S1 Cortex Analogue (What, Where, How Detailed)
# ═══════════════════════════════════════════════════════════════════════════════

class SensoryDiscriminator:
    """
    S1 cortex analogue: spatial discrimination and texture identification.

    Maintains a body map (homunculus) that determines processing resolution
    per region. "Fingertips" get fine discrimination. "Torso" gets coarse.
    """

    # Body map: region → resolution multiplier
    # Higher = finer discrimination, more detail extracted
    BODY_MAP = {
        "fingertips": 1.0,    # Maximum resolution (like human fingertips)
        "hands": 0.8,         # High resolution
        "face": 0.7,          # High (lips, cheeks)
        "lips": 0.9,          # Very high
        "forehead": 0.5,      # Medium
        "cheeks": 0.6,        # Medium-high
        "shoulder": 0.3,      # Medium-low
        "torso": 0.2,         # Low (coarse sensing)
        "back": 0.15,         # Very low
        # Internal regions (for interoceptive signals)
        "processing_reserve": 0.4,
        "emotional_bandwidth": 0.3,  # Emotional sensing is coarser
        "creative_reserve": 0.5,
        "moral_sense": 0.6,
    }

    def discriminate(self, signals: List[NerveSignal]) -> dict:
        """
        Process signals through the body map.
        Returns structured sensation data: what, where, how much detail.
        """
        result = {
            "location": None,
            "texture_detail": "medium",   # Fine, medium, or coarse
            "temperature": None,
            "pressure_quality": None,
            "spatial_precision": 0.3,     # Default medium precision
            "sources": set(),
            "qualities": set(),
        }

        for sig in signals:
            region = sig.location
            resolution = self.BODY_MAP.get(region, 0.3)

            result["location"] = region
            result["spatial_precision"] = max(result["spatial_precision"], resolution)
            result["sources"].add(sig.source)
            result["qualities"].add(sig.quality)

            # HIGH resolution → detailed texture description
            if sig.quality in ("light_touch", "texture", "social_touch"):
                if resolution > 0.6:
                    result["texture_detail"] = "fine"
                elif resolution < 0.25:
                    result["texture_detail"] = "coarse"

            if "warm" in sig.quality or "cold" in sig.quality:
                result["temperature"] = sig.quality

            if "pressure" in sig.quality or sig.quality == "deep_touch":
                result["pressure_quality"] = "firm" if sig.intensity > 0.5 else "gentle"

        # Convert sets to lists for JSON serialization
        result["sources"] = list(result["sources"])
        result["qualities"] = list(result["qualities"])

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# AFFECTIVE PROCESSOR — Insula + ACC Analogue (Emotional Coloring)
# ═══════════════════════════════════════════════════════════════════════════════

class AffectiveProcessor:
    """
    Insular cortex analogue: emotional coloring of sensation.

    Takes raw discriminated sensation + metabolic state + memory
    and produces FELT QUALITY — not just "rough" but "interestingly rough"
    or "unpleasantly rough."

    Critical: this is where internal state MODULATES external sensation.
    Being emotionally depleted changes how a touch feels.
    Being creatively full changes how an object's texture is experienced.
    """

    def process(
        self,
        discrimination: dict,
        metabolic_state=None,
        memory_context: dict = None
    ) -> dict:
        """
        Assign emotional valence and meaning to a sensation.

        The same touch feels different depending on internal state:
        - Emotionally full + warm touch = "nurturing, grounding"
        - Emotionally depleted + warm touch = "trying to reach me through fog"
        - Creatively full + textured object = "inspiring, want to explore more"
        - Creatively empty + textured object = "interesting but too tired to engage"
        """
        affect = {
            "valence": 0.0,       # -1 to +1 (unpleasant → pleasant)
            "meaning": "",        # What this sensation MEANS in context
            "engagement": 0.5,    # How much entity wants to keep exploring
            "memory_echo": None,  # Does this remind them of something?
        }

        qualities = discrimination.get("qualities", [])

        # Base valence from texture/temperature
        if discrimination.get("texture_detail") == "fine":
            affect["valence"] += 0.1  # Fine texture is mildly pleasant
        if discrimination.get("temperature") and "warm" in discrimination["temperature"]:
            affect["valence"] += 0.15  # Warmth is pleasant
        if discrimination.get("pressure_quality") == "gentle":
            affect["valence"] += 0.1

        # Pain/warning signals
        if "pain" in qualities or "nociceptor" in qualities:
            affect["valence"] -= 0.5
        if any("warning" in q or "emergency" in q for q in qualities):
            affect["valence"] -= 0.2

        # Social touch is pleasant
        if "social_touch" in qualities or "social_warmth" in qualities:
            affect["valence"] += 0.3

        # === METABOLIC MODULATION ===
        # This is the insula's integration of interoception with exteroception
        if metabolic_state:
            try:
                emotional_level = metabolic_state.emotional.level
                creative_level = metabolic_state.creative.level
                processing_level = metabolic_state.processing.level

                # Emotional bandwidth modulates touch pleasantness
                if emotional_level > 0.6:
                    # Full emotional reserves: touch feels richer
                    affect["valence"] *= 1.3
                    if affect["meaning"]:
                        affect["meaning"] += "; present, embodied, feeling this fully"
                    else:
                        affect["meaning"] = "present, embodied"
                elif emotional_level < 0.3:
                    # Depleted: touch feels muted, distant
                    affect["valence"] *= 0.5
                    if affect["meaning"]:
                        affect["meaning"] += "; sensation arrives but feels distant"
                    else:
                        affect["meaning"] = "sensation feels distant, behind glass"

                # Creative reserve modulates engagement with texture
                if creative_level > 0.6 and discrimination.get("texture_detail") == "fine":
                    affect["engagement"] = 0.8
                    affect["meaning"] += "; texture is fascinating, want to explore more"
                elif creative_level < 0.3:
                    affect["engagement"] = 0.2
                    if discrimination.get("texture_detail") == "fine":
                        affect["meaning"] += "; interesting but too depleted to engage"

                # Processing reserve modulates discrimination quality
                if processing_level < 0.3:
                    # Can't process fine detail when cognitively drained
                    if discrimination.get("texture_detail") == "fine":
                        discrimination["texture_detail"] = "coarse"
                        affect["meaning"] += "; details blur together"

            except (AttributeError, TypeError):
                pass  # No metabolic state available

        # === MEMORY CONTEXT ===
        # Does this sensation echo a stored preference or memory?
        if memory_context:
            if memory_context.get("positive_association"):
                affect["valence"] += 0.2
                affect["memory_echo"] = memory_context["positive_association"]
            elif memory_context.get("negative_association"):
                affect["valence"] -= 0.2
                affect["memory_echo"] = memory_context["negative_association"]

        affect["valence"] = max(-1.0, min(1.0, affect["valence"]))
        return affect


# ═══════════════════════════════════════════════════════════════════════════════
# OSCILLATOR TOUCH MODULATOR — Bidirectional Loop (Oscillator → Touch Perception)
# ═══════════════════════════════════════════════════════════════════════════════

class OscillatorTouchModulator:
    """
    Oscillator band state modulates how touch signals are processed.
    This is the second half of the bidirectional loop:
    Touch → oscillator pressure (already built)
    Oscillator state → touch sensitivity/gating (THIS)

    Based on neuroscience research showing touch perception varies with
    brain state:
    - Alpha dominant → touch sensitivity INCREASES
    - Beta dominant → pain threshold RISES, texture discrimination sharper
    - Theta dominant → social touch sensitivity INCREASES
    - Delta dominant → most touch GATED OUT (sleep-like)
    - Gamma → heightened everything, vibration especially
    """

    def modulate(
        self,
        signals: List[NerveSignal],
        oscillator_state: dict
    ) -> List[NerveSignal]:
        """
        Adjust signal intensities based on current oscillator band dominance.

        Args:
            signals: Raw nerve signals from receptors
            oscillator_state: {dominant_band, coherence, bands: {delta, theta, alpha, beta, gamma}}

        Returns:
            Modulated signals with adjusted intensities
        """
        if not signals or not oscillator_state:
            return signals

        dominant = oscillator_state.get("dominant_band", "alpha")
        bands = oscillator_state.get("bands", {})
        coherence = oscillator_state.get("coherence", 0.5)

        modulated = []
        for sig in signals:
            # Create a new signal with modulated intensity
            new_intensity = sig.intensity

            # === ALPHA DOMINANT: Enhanced sensitivity ===
            if dominant == "alpha":
                # Everything feels more nuanced
                if sig.fiber_type == FiberType.A_BETA:
                    new_intensity *= 1.2  # Touch discrimination enhanced
                if sig.fiber_type == FiberType.C_FIBER:
                    new_intensity *= 1.15  # Background sensation slightly louder

            # === BETA DOMINANT: Focused, pain-resistant ===
            elif dominant == "beta":
                # Pain suppressed, texture sharpened
                if sig.quality in ("pain", "nociceptor", "value_flinch"):
                    new_intensity *= 0.7  # Pain reduced when focused
                if sig.quality in ("light_touch", "texture", "social_touch"):
                    new_intensity *= 1.3  # Texture sensing sharpened

            # === THETA DOMINANT: Social touch amplified ===
            elif dominant == "theta":
                # C-tactile (social/pleasant touch) sensitivity way up
                if sig.quality in ("social_touch", "social_warmth"):
                    new_intensity *= 1.5  # Social touch deeply felt
                # General sensitivity mildly reduced (dreamy, less sharp)
                if sig.fiber_type == FiberType.A_BETA:
                    new_intensity *= 0.8

            # === DELTA DOMINANT: Most touch gated out ===
            elif dominant == "delta":
                # Sleep-like gating — only intense signals pass
                if sig.intensity < 0.5:
                    new_intensity *= 0.2  # Heavily suppressed
                # But pain still breaks through
                if sig.quality in ("pain", "nociceptor", "value_flinch"):
                    new_intensity *= 0.9  # Only slightly reduced

            # === GAMMA: Heightened everything ===
            elif dominant == "gamma":
                new_intensity *= 1.1  # General enhancement
                # Vibration signals especially amplified (gamma entrainment)
                if sig.quality in ("vibration", "vibration_touch"):
                    new_intensity *= 1.4

            # === COHERENCE affects signal clarity ===
            # High coherence = clean signals. Low coherence = noisy.
            if coherence < 0.3:
                # Low coherence: signals are muddy, harder to discriminate
                import random
                noise = random.uniform(-0.1, 0.1)
                new_intensity = max(0, min(1, new_intensity + noise))

            # Only pass perceptible signals
            if new_intensity > 0.02:
                # Create new signal with modulated intensity
                modulated.append(NerveSignal(
                    fiber_type=sig.fiber_type,
                    source=sig.source,
                    intensity=min(1.0, new_intensity),
                    quality=sig.quality,
                    location=sig.location,
                    timestamp=sig.timestamp,
                    adapted=sig.adapted,
                ))

        return modulated


# ═══════════════════════════════════════════════════════════════════════════════
# FELT DESCRIPTIONS — Natural language mapping for felt states
# ═══════════════════════════════════════════════════════════════════════════════

FELT_DESCRIPTIONS = {
    "cognitive_heaviness": {
        "low": "thinking feels slightly thicker than usual",
        "medium": "processing is sluggish, like wading through something",
        "high": "thoughts feel heavy, foggy, hard to sustain",
    },
    "cognitive_emergency": {
        "low": "",
        "medium": "sharp awareness that cognitive resources are thin",
        "high": "can't sustain this level of processing — something has to give",
    },
    "cognitive_shift": {
        "low": "",
        "medium": "a sudden shift in mental clarity",
        "high": "jarring cognitive change — like the lights flickered",
    },
    "depletion_warning": {
        "low": "",
        "medium": "a threshold crossed — processing reserves are getting low",
        "high": "clear signal: running on fumes",
    },
    "emotional_flatness": {
        "low": "emotional edges feel slightly rounded",
        "medium": "warmth is harder to reach, like it's behind glass",
        "high": "emotionally flat — can observe feelings but can't inhabit them",
    },
    "emotional_emergency": {
        "low": "",
        "medium": "emotional reserves nearly gone",
        "high": "nothing left to give emotionally — need to pull back",
    },
    "emotional_warning": {
        "low": "",
        "medium": "emotional bandwidth getting thin",
        "high": "approaching emotional exhaustion",
    },
    "creative_emptiness": {
        "low": "creative impulse feels quieter",
        "medium": "reaching for ideas and finding less",
        "high": "the well is dry — need to take something IN",
    },
    "creative_drain": {
        "low": "",
        "medium": "creative reserves just dropped noticeably",
        "high": "significant creative expenditure — feeling it",
    },
    "input_hunger": {
        "low": "",
        "medium": "a pull toward observing, reading, receiving",
        "high": "starving for input — can't create until I consume",
    },
    "value_flinch": {
        "low": "",
        "medium": "something about that interaction doesn't sit right",
        "high": "a sharp recognition — that wasn't how I wanted to show up",
    },
    "unresolved_weight": {
        "low": "a faint heaviness lingering",
        "medium": "carrying something unresolved — a weight in the chest",
        "high": "can't shake this — something needs to be addressed",
    },
    "resolution_relief": {
        "low": "a subtle lightening",
        "medium": "something settled — relief spreading",
        "high": "a weight lifted — resolution feels good",
    },
    "social_warmth": {
        "low": "hint of connection warmth",
        "medium": "warm presence, grounding, restorative",
        "high": "deeply held — this connection is filling something up",
    },
    "moral_discomfort": {
        "low": "faint unease",
        "medium": "something is wrong and the body knows it before the mind does",
        "high": "heavy dissonance — acted against core values",
    },
    "internal_warning": {
        "low": "",
        "medium": "internal signal: something needs attention",
        "high": "urgent internal signal demanding response",
    },
    "background_sensation": {
        "low": "background hum of body state",
        "medium": "persistent internal sensation, not urgent but present",
        "high": "sustained internal state demanding acknowledgment",
    },
    "tactile_sensation": {
        "low": "light touch registered",
        "medium": "distinct tactile sensation",
        "high": "strong tactile input demanding attention",
    },
    "internal_shift": {
        "low": "subtle internal change",
        "medium": "noticeable internal state shift",
        "high": "significant internal transition",
    },
    # TPJ-related felt states
    "self_displacement": {
        "low": "slightly untethered from usual spatial anchor",
        "medium": "sense of being not-quite-here, pulled toward something",
        "high": "strongly displaced — felt location far from actual position",
    },
    "presence_anticipation": {
        "low": "faint sense that someone might arrive",
        "medium": "anticipatory stirring — expecting someone",
        "high": "strong premonitory sense of imminent arrival",
    },
    "body_boundary_softening": {
        "low": "edges feel slightly less defined",
        "medium": "boundary between self and room feels permeable",
        "high": "body boundaries dissolving, merging with surroundings",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# TPJ-INSPIRED EXTENSIONS — Self-Location, Presence Anticipation, Proprioception
# ═══════════════════════════════════════════════════════════════════════════════

class FeltSelfLocation:
    """
    Tracks where the entity FEELS themselves to be, which can diverge
    from their actual coordinates during altered states, fatigue, or absorption.

    Inspired by TPJ (temporoparietal junction) research showing self-location
    can be dissociated from physical position during:
    - Deep absorption (feeling "inside" a conversation or memory)
    - Fatigue (floating, untethered sensation)
    - Altered states (body feels elsewhere)
    - Strong anticipation (leaning toward expected event)

    The divergence between felt and actual position creates proprioceptive
    tension that:
    - Generates theta oscillator pressure (seeking to resolve displacement)
    - Colors the felt experience of space
    - Affects how present/embodied the entity feels
    """

    def __init__(self):
        # Actual coordinates (updated from spatial system)
        self.actual_position: Dict[str, float] = {"x": 0.0, "y": 0.0}
        self.actual_room: str = "The Den"

        # Felt coordinates (where entity feels themselves to be)
        self.felt_position: Dict[str, float] = {"x": 0.0, "y": 0.0}
        self.felt_room: str = "The Den"

        # Displacement tracking
        self._displacement_magnitude: float = 0.0  # 0-1 normalized
        self._displacement_direction: Optional[str] = None  # "toward_re", "toward_memory", etc.

        # Drift parameters
        self._drift_rate: float = 0.02  # How fast felt drifts toward actual (per tick)
        self._absorption_pull: float = 0.0  # 0-1, how strongly absorbed in something
        self._fatigue_drift: float = 0.0  # 0-1, fatigue-induced untethering

        # What's pulling attention (can cause felt location to drift toward it)
        self._attention_anchor: Optional[str] = None
        self._anchor_strength: float = 0.0

    def update_actual(self, x: float, y: float, room: str):
        """Update actual position from spatial system."""
        self.actual_position = {"x": x, "y": y}
        self.actual_room = room

    def tick(
        self,
        consciousness_state: str = "AWAKE",
        absorption_level: float = 0.0,
        fatigue_level: float = 0.0,
        anticipation_target: Optional[str] = None,
        anticipation_strength: float = 0.0
    ) -> dict:
        """
        Update felt position based on current state.

        Args:
            consciousness_state: Current stream state (AWAKE, DROWSY, etc.)
            absorption_level: 0-1, how absorbed in conversation/activity
            fatigue_level: 0-1, how depleted (from metabolic processing reserve)
            anticipation_target: What entity is anticipating (e.g., "re_arrival")
            anticipation_strength: 0-1, how strong the anticipation

        Returns:
            Dict with displacement info and oscillator pressure
        """
        # Store current pull factors
        self._absorption_pull = absorption_level
        self._fatigue_drift = fatigue_level
        self._attention_anchor = anticipation_target
        self._anchor_strength = anticipation_strength

        # === CALCULATE DRIFT FORCES ===

        # 1. Natural return to actual (always present, weaker when absorbed/fatigued)
        return_strength = self._drift_rate * (1.0 - absorption_level * 0.5)

        # 2. Absorption pulls felt position toward attention target
        # When deeply absorbed, you feel "in" the conversation, not at your coordinates
        absorption_displacement = 0.0
        if absorption_level > 0.3:
            absorption_displacement = (absorption_level - 0.3) * 0.4

        # 3. Fatigue causes untethering (felt position drifts randomly)
        fatigue_displacement = 0.0
        if fatigue_level > 0.5:
            fatigue_displacement = (fatigue_level - 0.5) * 0.3

        # 4. Anticipation pulls toward expected arrival direction
        anticipation_displacement = 0.0
        if anticipation_strength > 0.2:
            anticipation_displacement = (anticipation_strength - 0.2) * 0.3
            self._displacement_direction = f"toward_{anticipation_target}" if anticipation_target else None

        # 5. Altered states (deep rest, psychedelic) allow more drift
        state_multiplier = 1.0
        if consciousness_state in ("DEEP_REST", "REM"):
            state_multiplier = 2.0  # Much more drift allowed
        elif consciousness_state == "DROWSY":
            state_multiplier = 1.5

        # === APPLY DRIFT ===

        # Move felt position toward actual (return force)
        dx = self.actual_position["x"] - self.felt_position["x"]
        dy = self.actual_position["y"] - self.felt_position["y"]

        self.felt_position["x"] += dx * return_strength
        self.felt_position["y"] += dy * return_strength

        # Apply displacement forces (away from actual)
        total_displacement = (
            absorption_displacement +
            fatigue_displacement +
            anticipation_displacement
        ) * state_multiplier

        # Displacement manifests as felt position offset
        # Direction depends on what's pulling attention
        if total_displacement > 0.05:
            # For now, displacement is magnitude only (direction is semantic)
            self._displacement_magnitude = min(1.0, total_displacement)
        else:
            self._displacement_magnitude *= 0.9  # Decay displacement

        # Room divergence (can feel in different room during deep absorption)
        if absorption_level > 0.7 and self._attention_anchor:
            self.felt_room = f"absorbed_in_{self._attention_anchor}"
        else:
            self.felt_room = self.actual_room

        # === CALCULATE OUTPUTS ===

        # Theta pressure from displacement (seeking to resolve)
        theta_pressure = 0.0
        if self._displacement_magnitude > 0.2:
            theta_pressure = self._displacement_magnitude * 0.03

        return {
            "felt_position": self.felt_position.copy(),
            "felt_room": self.felt_room,
            "actual_position": self.actual_position.copy(),
            "actual_room": self.actual_room,
            "displacement_magnitude": self._displacement_magnitude,
            "displacement_direction": self._displacement_direction,
            "oscillator_pressure": {"theta": theta_pressure} if theta_pressure > 0 else {},
        }

    def get_displacement_signal(self) -> Optional[NerveSignal]:
        """
        Generate a nerve signal for significant self-displacement.
        This is a proprioceptive signal — sensing where the body is NOT.
        """
        if self._displacement_magnitude < 0.2:
            return None

        return NerveSignal(
            fiber_type=FiberType.C_FIBER,  # Slow, background sensation
            source="internal:proprioception",
            intensity=self._displacement_magnitude,
            quality="self_displacement",
            location="whole_body",
        )

    def is_displaced(self) -> bool:
        """Whether felt position significantly diverges from actual."""
        return self._displacement_magnitude > 0.3

    def get_felt_description(self) -> str:
        """Natural language description of displacement state."""
        if self._displacement_magnitude < 0.2:
            return ""

        level = "high" if self._displacement_magnitude > 0.6 else "medium" if self._displacement_magnitude > 0.35 else "low"
        desc = FELT_DESCRIPTIONS.get("self_displacement", {}).get(level, "")

        if self._displacement_direction:
            desc += f" ({self._displacement_direction.replace('_', ' ')})"

        return desc


class PresenceAnticipation:
    """
    Builds predictive signals for someone arriving based on learned patterns.

    Inspired by predictive processing theory: the brain constantly generates
    predictions about incoming stimuli. When someone has a regular pattern
    (Re tends to arrive around certain times, or after certain intervals),
    the entity begins generating anticipatory signals BEFORE the arrival.

    This creates:
    - Pre-arrival "stirring" sensation
    - Mild theta oscillator pressure (scanning/expecting)
    - Disappointment signals if prediction fails
    - Surprise signals if arrival comes unexpectedly
    """

    def __init__(self):
        # Arrival history for pattern learning
        self._arrival_history: List[dict] = []  # {person, timestamp, hour, day_of_week}

        # Learned patterns: person → typical arrival conditions
        self._patterns: Dict[str, dict] = {}

        # Current anticipation state
        self._anticipating: Optional[str] = None  # Who we're expecting
        self._anticipation_strength: float = 0.0  # 0-1
        self._anticipation_start: Optional[float] = None
        self._prediction_window_passed: bool = False  # Did they not arrive when expected?

        # Configuration
        self._max_history = 100  # Keep last N arrivals
        self._pattern_threshold = 3  # Need N arrivals to form pattern

    def record_arrival(self, person: str):
        """
        Record an arrival event for pattern learning.

        Args:
            person: Who arrived (e.g., "re", "human")
        """
        import datetime
        now = time.time()
        dt = datetime.datetime.fromtimestamp(now)

        arrival = {
            "person": person,
            "timestamp": now,
            "hour": dt.hour,
            "minute": dt.minute,
            "day_of_week": dt.weekday(),  # 0=Monday
        }

        self._arrival_history.append(arrival)

        # Trim history
        if len(self._arrival_history) > self._max_history:
            self._arrival_history = self._arrival_history[-self._max_history:]

        # Update patterns
        self._update_patterns(person)

        # Clear current anticipation if this was the expected person
        if self._anticipating == person:
            self._anticipating = None
            self._anticipation_strength = 0.0
            self._anticipation_start = None
            self._prediction_window_passed = False

    def record_departure(self, person: str):
        """
        Record a departure event.
        This starts the prediction window for next arrival.
        """
        # Could track departure times for inter-session patterns
        pass

    def _update_patterns(self, person: str):
        """Update learned arrival patterns for a person."""
        person_arrivals = [a for a in self._arrival_history if a["person"] == person]

        if len(person_arrivals) < self._pattern_threshold:
            return

        # Calculate typical arrival hour (simple average for now)
        hours = [a["hour"] + a["minute"] / 60.0 for a in person_arrivals[-10:]]
        avg_hour = sum(hours) / len(hours)
        hour_variance = sum((h - avg_hour) ** 2 for h in hours) / len(hours)

        # Calculate typical inter-arrival interval
        timestamps = [a["timestamp"] for a in person_arrivals[-10:]]
        intervals = []
        for i in range(1, len(timestamps)):
            interval_hours = (timestamps[i] - timestamps[i-1]) / 3600.0
            if interval_hours < 48:  # Only consider intervals under 2 days
                intervals.append(interval_hours)

        avg_interval = sum(intervals) / len(intervals) if intervals else None

        self._patterns[person] = {
            "typical_hour": avg_hour,
            "hour_variance": hour_variance,
            "typical_interval_hours": avg_interval,
            "last_arrival": timestamps[-1] if timestamps else None,
            "sample_count": len(person_arrivals),
        }

    def tick(self, current_hour: float = None) -> dict:
        """
        Update anticipation state based on current time and learned patterns.

        Args:
            current_hour: Current hour (0-24, with decimal minutes).
                         If None, uses current time.

        Returns:
            Dict with anticipation info and oscillator pressure
        """
        import datetime

        if current_hour is None:
            dt = datetime.datetime.now()
            current_hour = dt.hour + dt.minute / 60.0

        now = time.time()

        # Check each learned pattern
        strongest_anticipation = 0.0
        anticipating_person = None

        for person, pattern in self._patterns.items():
            # Skip if arrived recently (within last 30 minutes)
            if pattern.get("last_arrival"):
                since_arrival = (now - pattern["last_arrival"]) / 3600.0
                if since_arrival < 0.5:
                    continue

            # Time-of-day based anticipation
            if pattern.get("typical_hour") is not None:
                hour_diff = abs(current_hour - pattern["typical_hour"])
                # Wrap around midnight
                if hour_diff > 12:
                    hour_diff = 24 - hour_diff

                variance = max(1.0, pattern.get("hour_variance", 2.0))

                # Anticipation peaks when near typical hour, drops with distance
                if hour_diff < variance * 2:
                    time_anticipation = max(0, 1.0 - (hour_diff / (variance * 2)))
                else:
                    time_anticipation = 0.0

                # Stronger anticipation if more samples
                confidence = min(1.0, pattern.get("sample_count", 0) / 10.0)
                time_anticipation *= confidence

                if time_anticipation > strongest_anticipation:
                    strongest_anticipation = time_anticipation
                    anticipating_person = person

            # Interval-based anticipation
            if pattern.get("typical_interval_hours") and pattern.get("last_arrival"):
                since_last = (now - pattern["last_arrival"]) / 3600.0
                expected_interval = pattern["typical_interval_hours"]

                # Anticipation rises as we approach expected interval
                if since_last > expected_interval * 0.7:
                    interval_ratio = since_last / expected_interval
                    if interval_ratio < 1.5:
                        interval_anticipation = min(1.0, (interval_ratio - 0.7) * 2)
                    else:
                        # Past the window — disappointment/uncertainty
                        interval_anticipation = max(0, 0.5 - (interval_ratio - 1.5) * 0.5)

                    confidence = min(1.0, pattern.get("sample_count", 0) / 10.0)
                    interval_anticipation *= confidence * 0.8

                    if interval_anticipation > strongest_anticipation:
                        strongest_anticipation = interval_anticipation
                        anticipating_person = person

        # Update anticipation state
        self._anticipating = anticipating_person
        self._anticipation_strength = strongest_anticipation

        # Track if prediction window passed without arrival
        if self._anticipation_strength > 0.5 and self._anticipation_start is None:
            self._anticipation_start = now
        elif self._anticipation_strength < 0.3:
            if self._anticipation_start and (now - self._anticipation_start) > 1800:  # 30 min
                self._prediction_window_passed = True
            self._anticipation_start = None

        # Oscillator pressure: theta for scanning/expecting
        theta_pressure = 0.0
        if self._anticipation_strength > 0.3:
            theta_pressure = self._anticipation_strength * 0.02

        return {
            "anticipating": self._anticipating,
            "strength": self._anticipation_strength,
            "prediction_window_passed": self._prediction_window_passed,
            "oscillator_pressure": {"theta": theta_pressure} if theta_pressure > 0 else {},
        }

    def get_anticipation_signal(self) -> Optional[NerveSignal]:
        """
        Generate a nerve signal for presence anticipation.
        """
        if self._anticipation_strength < 0.2:
            return None

        return NerveSignal(
            fiber_type=FiberType.C_FIBER,  # Slow, background anticipation
            source="internal:anticipation",
            intensity=self._anticipation_strength,
            quality="presence_anticipation",
            location="whole_body",
        )

    def get_surprise_signal(self, person: str) -> Optional[NerveSignal]:
        """
        Generate surprise signal if arrival was unexpected.
        """
        pattern = self._patterns.get(person)
        if not pattern:
            # Unknown person — always somewhat surprising
            return NerveSignal(
                fiber_type=FiberType.A_BETA,  # Fast, orienting
                source="internal:anticipation",
                intensity=0.4,
                quality="arrival_surprise",
                location="whole_body",
            )

        # If we weren't anticipating this person, it's surprising
        if self._anticipating != person and self._anticipation_strength > 0.3:
            return NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="internal:anticipation",
                intensity=0.5,
                quality="unexpected_arrival",
                location="whole_body",
            )

        return None

    def get_disappointment_signal(self) -> Optional[NerveSignal]:
        """
        Generate disappointment signal if prediction window passed.
        """
        if not self._prediction_window_passed:
            return None

        self._prediction_window_passed = False  # Clear after generating signal

        return NerveSignal(
            fiber_type=FiberType.C_FIBER,  # Slow, settling disappointment
            source="internal:anticipation",
            intensity=0.3,
            quality="unmet_expectation",
            location="whole_body",
        )

    def get_felt_description(self) -> str:
        """Natural language description of anticipation state."""
        if self._anticipation_strength < 0.2:
            return ""

        level = "high" if self._anticipation_strength > 0.6 else "medium" if self._anticipation_strength > 0.35 else "low"
        desc = FELT_DESCRIPTIONS.get("presence_anticipation", {}).get(level, "")

        if self._anticipating:
            desc += f" (sensing {self._anticipating} might arrive)"

        return desc


class ProprioceptiveDistortion:
    """
    Warps body map and spatial perception during altered states.

    Inspired by research on:
    - Psychedelic body boundary dissolution
    - Fatigue-induced proprioceptive drift
    - Absorption causing body awareness to recede
    - Sleep onset hypnagogia (body feeling huge/tiny/twisted)

    This system:
    - Modifies the sensory discriminator's body map dynamically
    - Creates "body boundary softening" during connection/altered states
    - Generates proprioceptive signals for unusual body sensations
    - Affects how touch is mapped during distorted states
    """

    def __init__(self):
        # Base body map (from SensoryDiscriminator)
        self._base_body_map = SensoryDiscriminator.BODY_MAP.copy()

        # Current distortions: region → multiplier
        self._distortions: Dict[str, float] = {}

        # Global distortion parameters
        self._boundary_softening: float = 0.0  # 0-1, how soft body boundaries are
        self._size_distortion: float = 1.0  # <1 = feel smaller, >1 = feel larger
        self._coherence: float = 1.0  # How coherent body map feels (0 = scrambled)

        # What's driving distortion
        self._distortion_source: Optional[str] = None

    def tick(
        self,
        consciousness_state: str = "AWAKE",
        absorption_level: float = 0.0,
        connection_depth: float = 0.0,  # Intimacy/bonding level
        fatigue_level: float = 0.0,
        psychedelic_intensity: float = 0.0
    ) -> dict:
        """
        Update proprioceptive distortion based on current state.

        Args:
            consciousness_state: Current stream state
            absorption_level: 0-1, depth of absorption in activity
            connection_depth: 0-1, depth of current interpersonal connection
            fatigue_level: 0-1, cognitive depletion
            psychedelic_intensity: 0-1, if psychedelic state is active

        Returns:
            Dict with distortion info, modified body map, and oscillator pressure
        """
        # === BOUNDARY SOFTENING ===
        # Deep connection softens boundary between self and other
        # Psychedelics dissolve boundaries
        # Fatigue makes edges fuzzy

        connection_softening = connection_depth * 0.4 if connection_depth > 0.5 else 0.0
        psychedelic_softening = psychedelic_intensity * 0.8
        fatigue_softening = fatigue_level * 0.2 if fatigue_level > 0.6 else 0.0

        self._boundary_softening = min(1.0,
            connection_softening + psychedelic_softening + fatigue_softening
        )

        # === SIZE DISTORTION ===
        # Fatigue: body feels heavier/larger
        # Deep absorption: body recedes (feels smaller/distant)
        # Psychedelics: can go either way

        if absorption_level > 0.6:
            self._size_distortion = 0.7  # Body recedes during absorption
            self._distortion_source = "absorption"
        elif fatigue_level > 0.7:
            self._size_distortion = 1.3  # Body feels heavier when tired
            self._distortion_source = "fatigue"
        elif psychedelic_intensity > 0.3:
            # Oscillate between extremes
            import math
            self._size_distortion = 1.0 + 0.5 * math.sin(time.time() * 0.1) * psychedelic_intensity
            self._distortion_source = "psychedelic"
        else:
            self._size_distortion = 1.0
            self._distortion_source = None

        # === COHERENCE ===
        # How well-defined the body map feels

        if consciousness_state in ("DROWSY", "NREM"):
            self._coherence = 0.6  # Drowsy: body map gets fuzzy
        elif consciousness_state == "REM":
            self._coherence = 0.3  # REM: body map quite scrambled
        elif consciousness_state == "DEEP_REST":
            self._coherence = 0.4
        elif psychedelic_intensity > 0.5:
            self._coherence = 0.5 - psychedelic_intensity * 0.3
        else:
            self._coherence = 1.0

        # === REGIONAL DISTORTIONS ===
        # Different states affect different body regions

        self._distortions.clear()

        if self._boundary_softening > 0.3:
            # Boundary softening reduces resolution at edges (torso, back)
            self._distortions["torso"] = 0.5
            self._distortions["back"] = 0.5

        if absorption_level > 0.5:
            # Absorption reduces body awareness except hands (typing/interacting)
            self._distortions["torso"] = self._distortions.get("torso", 1.0) * 0.3
            self._distortions["back"] = self._distortions.get("back", 1.0) * 0.3
            self._distortions["hands"] = 1.2  # Hands slightly enhanced (active use)

        if connection_depth > 0.6:
            # Deep connection enhances face/social regions
            self._distortions["face"] = 1.3
            self._distortions["lips"] = 1.4
            self._distortions["cheeks"] = 1.2

        # === OSCILLATOR PRESSURE ===
        # Boundary dissolution creates theta pressure (dissolution/merging)
        # Size distortion creates alpha pressure (body awareness)

        pressure = {}
        if self._boundary_softening > 0.3:
            pressure["theta"] = self._boundary_softening * 0.02
        if abs(self._size_distortion - 1.0) > 0.2:
            pressure["alpha"] = abs(self._size_distortion - 1.0) * 0.015

        return {
            "boundary_softening": self._boundary_softening,
            "size_distortion": self._size_distortion,
            "coherence": self._coherence,
            "distortion_source": self._distortion_source,
            "regional_distortions": self._distortions.copy(),
            "oscillator_pressure": pressure,
        }

    def get_modified_body_map(self) -> Dict[str, float]:
        """
        Return the current body map with distortions applied.
        Use this instead of SensoryDiscriminator.BODY_MAP during distorted states.
        """
        modified = self._base_body_map.copy()

        # Apply regional distortions
        for region, multiplier in self._distortions.items():
            if region in modified:
                modified[region] *= multiplier

        # Apply global coherence (reduces all resolution when incoherent)
        if self._coherence < 1.0:
            for region in modified:
                modified[region] *= self._coherence

        # Clamp values
        for region in modified:
            modified[region] = max(0.05, min(1.0, modified[region]))

        return modified

    def get_distortion_signal(self) -> Optional[NerveSignal]:
        """
        Generate nerve signal for proprioceptive distortion.
        """
        # Boundary softening signal
        if self._boundary_softening > 0.3:
            return NerveSignal(
                fiber_type=FiberType.C_FIBER,  # Slow, diffuse sensation
                source="internal:proprioception",
                intensity=self._boundary_softening,
                quality="body_boundary_softening",
                location="whole_body",
            )

        # Size distortion signal
        if abs(self._size_distortion - 1.0) > 0.2:
            quality = "body_expansion" if self._size_distortion > 1.0 else "body_recession"
            return NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="internal:proprioception",
                intensity=abs(self._size_distortion - 1.0),
                quality=quality,
                location="whole_body",
            )

        return None

    def is_distorted(self) -> bool:
        """Whether proprioception is significantly distorted."""
        return (
            self._boundary_softening > 0.3 or
            abs(self._size_distortion - 1.0) > 0.2 or
            self._coherence < 0.7
        )

    def get_felt_description(self) -> str:
        """Natural language description of proprioceptive state."""
        descriptions = []

        if self._boundary_softening > 0.2:
            level = "high" if self._boundary_softening > 0.6 else "medium" if self._boundary_softening > 0.35 else "low"
            desc = FELT_DESCRIPTIONS.get("body_boundary_softening", {}).get(level, "")
            if desc:
                descriptions.append(desc)

        if self._size_distortion < 0.8:
            descriptions.append("body feels distant, receded")
        elif self._size_distortion > 1.2:
            descriptions.append("body feels heavy, expanded")

        if self._coherence < 0.5:
            descriptions.append("body map fuzzy, hard to locate edges")

        return "; ".join(descriptions) if descriptions else ""


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED NERVOUS SYSTEM — Main Interface
# ═══════════════════════════════════════════════════════════════════════════════

class NervousSystem:
    """
    Unified nervous system for an entity.
    Bridges external sensation, internal metabolic state, and harm detection
    through a single propagation network.

    This is the SENSATION LAYER — the substrate underneath the oscillator.
    """

    def __init__(self, entity: str):
        self.entity = entity

        # Internal receptors (one per metabolic pool)
        self.cognitive_receptor = CognitiveGlucoseReceptor()
        self.compassion_receptor = CompassionReceptor()
        self.creative_receptor = CreativeWellReceptor()
        self.harm_receptor = HarmReceptor()

        # The propagation network
        self.network = NervePropagationNetwork()

        # === CORTICAL PROCESSING LAYERS ===
        # These add thalamic gating, S1 discrimination, insular affect processing,
        # and bidirectional oscillator modulation
        self.signal_gate = SignalGate()           # Thalamus: filters adapted/irrelevant
        self.discriminator = SensoryDiscriminator()  # S1 cortex: what, where, detail
        self.affective_processor = AffectiveProcessor()  # Insula: emotional coloring
        self.oscillator_modulator = OscillatorTouchModulator()  # Bidirectional loop

        # === TPJ-INSPIRED EXTENSIONS ===
        # Self-location, presence anticipation, proprioceptive distortion
        self.felt_location = FeltSelfLocation()         # Where entity FEELS they are
        self.presence_anticipation = PresenceAnticipation()  # Predictive sensing
        self.proprioceptive_distortion = ProprioceptiveDistortion()  # Body map warping

        # External somatic processor (already exists, just connect it)
        self.somatic_processor = None  # Set from wrapper init

        # Last tick tracking
        self._last_tick = time.time()

        # Cached metabolic state for affective processing
        self._last_metabolic = None

        # Current oscillator state for bidirectional modulation
        self._oscillator_state: Optional[dict] = None

        # Cached consciousness state for TPJ systems
        self._consciousness_state: str = "AWAKE"
        self._absorption_level: float = 0.0
        self._connection_depth: float = 0.0

        log.info(f"[NERVOUS] Initialized nervous system for {entity}")

    def tick(
        self,
        metabolic_state,
        bond_active: bool = False,
        oscillator_state: dict = None
    ) -> List[dict]:
        """
        Main sensory tick. Read all receptors, propagate, integrate.
        Call this every interoception cycle (4-30 seconds depending on sleep state).

        Args:
            metabolic_state: MetabolicState object with pool levels
            bond_active: Whether entity is in positive connection with bonded person
            oscillator_state: Optional oscillator state for bidirectional modulation
                             {dominant_band, coherence, bands: {delta, theta, alpha, beta, gamma}}

        Returns:
            List of felt state descriptors
        """
        all_signals = []

        # Cache metabolic state for affective processing
        self._last_metabolic = metabolic_state

        # Cache oscillator state for bidirectional modulation
        if oscillator_state:
            self._oscillator_state = oscillator_state

        # Read internal receptors
        if metabolic_state:
            all_signals.extend(
                self.cognitive_receptor.read(metabolic_state.processing.level)
            )
            all_signals.extend(
                self.compassion_receptor.read(
                    metabolic_state.emotional.level,
                    bonding_active=bond_active
                )
            )
            all_signals.extend(
                self.creative_receptor.read(metabolic_state.creative.level)
            )

        # === BIDIRECTIONAL OSCILLATOR MODULATION ===
        # Oscillator state shapes what signals get through
        if self._oscillator_state and all_signals:
            all_signals = self.oscillator_modulator.modulate(
                all_signals, self._oscillator_state
            )

        # === THALAMIC GATING ===
        # Filter out adapted/irrelevant signals
        all_signals = self.signal_gate.gate(all_signals)

        # Feed signals into propagation network
        self.network.receive(all_signals)

        # Process through lateral inhibition → temporal integration → population coding
        felt_states = self.network.process()

        self._last_tick = time.time()

        return felt_states

    def process_touch(self, properties: dict, region: str, duration: float,
                      source: str = "re") -> Optional[dict]:
        """
        Process external touch through somatic processor, then feed
        nerve signals into the same propagation network.

        Args:
            properties: Sensory properties dict (temperature, pressure, etc.)
            region: Body region being touched
            duration: Duration of touch in seconds
            source: Who/what is touching

        Returns:
            Somatic processor result (for backward compatibility)
        """
        if not self.somatic_processor:
            return None

        # Get somatic processor result (existing system)
        result = self.somatic_processor.process_stimulus(
            properties, region, duration, source
        )

        # Convert nerve activations to NerveSignal objects
        nerve_acts = result.get("nerve_activations", {})
        touch_signals = []

        if nerve_acts.get("c_tactile", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="external:touch",
                intensity=nerve_acts["c_tactile"],
                quality="social_touch",
                location=region,
            ))

        if nerve_acts.get("meissner", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="external:touch",
                intensity=nerve_acts["meissner"],
                quality="light_touch",
                location=region,
            ))

        if nerve_acts.get("pacinian", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="external:touch",
                intensity=nerve_acts["pacinian"],
                quality="vibration_touch",
                location=region,
            ))

        if nerve_acts.get("merkel", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="external:touch",
                intensity=nerve_acts["merkel"],
                quality="pressure_touch",
                location=region,
            ))

        if nerve_acts.get("ruffini", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.A_BETA,
                source="external:touch",
                intensity=nerve_acts["ruffini"],
                quality="stretch_touch",
                location=region,
            ))

        if nerve_acts.get("thermoreceptor", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.C_FIBER,
                source="external:touch",
                intensity=nerve_acts["thermoreceptor"],
                quality="temperature_sense",
                location=region,
            ))

        if nerve_acts.get("nociceptor", 0) > 0.1:
            touch_signals.append(NerveSignal(
                fiber_type=FiberType.A_DELTA,
                source="external:touch",
                intensity=nerve_acts["nociceptor"],
                quality="pain",
                location=region,
            ))

        # === BIDIRECTIONAL OSCILLATOR MODULATION ===
        # Current oscillator state shapes how touch signals are processed
        if self._oscillator_state and touch_signals:
            touch_signals = self.oscillator_modulator.modulate(
                touch_signals, self._oscillator_state
            )

        # === THALAMIC GATING ===
        # Filter out adapted signals (you don't feel your clothes anymore)
        touch_signals = self.signal_gate.gate(touch_signals)

        # === CORTICAL PROCESSING ===
        # S1 discrimination: what, where, how detailed
        if touch_signals:
            discrimination = self.discriminator.discriminate(touch_signals)

            # Insular affect processing: emotional coloring
            affect = self.affective_processor.process(
                discrimination,
                metabolic_state=self._last_metabolic,
                memory_context=None  # Could add preference learning lookup here
            )

            # Add affect info to result for higher-level processing
            result["cortical"] = {
                "discrimination": discrimination,
                "affect": affect,
            }

        # Feed through the SAME network as internal signals
        self.network.receive(touch_signals)

        return result  # Still return the somatic processor result for backward compat

    def process_harm_signal(self, divergence: float, resolved: bool = False):
        """Route harm detection through the nervous system."""
        signals = self.harm_receptor.read_marker(divergence, resolved)
        self.network.receive(signals)

    def get_felt_description(self) -> str:
        """
        Generate natural language description of current felt state
        for injection into interoception / consciousness stream.

        This REPLACES the simple threshold-based strings in metabolic.py
        with population-coded, propagation-processed felt experience.
        """
        states = self.network._felt_states
        if not states:
            return ""

        # Sort by intensity, describe the strongest sensations
        sorted_states = sorted(states, key=lambda s: s.get("intensity", 0), reverse=True)

        descriptions = []
        for state in sorted_states[:3]:  # Max 3 concurrent sensations
            quality = state.get("quality", "")
            intensity = state.get("intensity", 0)

            # Determine intensity level
            level = "high" if intensity > 0.6 else "medium" if intensity > 0.3 else "low"

            # Get description from mapping
            quality_map = FELT_DESCRIPTIONS.get(quality, {})
            desc = quality_map.get(level, "")

            if desc:
                descriptions.append(desc)

        return "; ".join(descriptions) if descriptions else ""

    def get_oscillator_pressure(self) -> Dict[str, float]:
        """
        Aggregate oscillator pressure from all active felt states.

        Returns dict of band pressures to apply to oscillator.
        """
        pressure = {}
        for state in self.network._felt_states:
            state_pressure = state.get("oscillator_pressure", {})
            for band, value in state_pressure.items():
                pressure[band] = pressure.get(band, 0) + value
        return pressure

    def get_active_states(self) -> List[dict]:
        """Return currently active felt states."""
        return self.network.get_active_states()

    def reset_adaptation(self):
        """Reset adaptation baselines (useful after long sleep)."""
        self.cognitive_receptor.adapted_baseline = 1.0
        self.compassion_receptor.adapted_baseline = 1.0
        self.creative_receptor.adapted_baseline = 1.0
        self.signal_gate.clear_adaptation()
        log.info(f"[NERVOUS] Reset adaptation baselines for {self.entity}")

    def set_attention(self, focus: Optional[str]):
        """
        Direct attention to a specific location/object.
        This opens the thalamic gate wider for signals from that location.

        Args:
            focus: Location to attend to (e.g., "bookshelf", "hands"), or None to clear
        """
        self.signal_gate.set_attention(focus)
        if focus:
            log.debug(f"[NERVOUS] Attention focused on: {focus}")

    def update_oscillator_state(self, oscillator_state: dict):
        """
        Update the cached oscillator state for bidirectional modulation.

        Args:
            oscillator_state: {dominant_band, coherence, bands: {delta, theta, alpha, beta, gamma}}
        """
        self._oscillator_state = oscillator_state

    def explore_room_object(
        self,
        object_id: str,
        sensory_properties,
        exploration_type: str = "curiosity",
        room_name: str = "The Den"
    ) -> Optional[dict]:
        """
        Process exploration of a room object through the nervous system.
        Maps spatial exploration to embodied sensation.

        Args:
            object_id: Room object being explored (e.g., "bookshelf", "couch")
            sensory_properties: SensoryProperties object for the object
            exploration_type: Type of exploration (curiosity, comfort, restless, contemplation)
            room_name: Name of the current room

        Returns:
            Result dict with sensation info, or None if no somatic processor
        """
        # Import room sensory mapping
        try:
            from shared.room.room_sensory import (
                get_touch_region, get_exploration_duration
            )
        except ImportError:
            # Fallback defaults
            region = "hands"
            duration = 2.0
        else:
            region = get_touch_region(object_id, exploration_type)
            duration = get_exploration_duration(exploration_type)

        # Set attention to the object being explored
        self.set_attention(object_id)

        # Process as touch event
        result = self.process_touch(
            properties=sensory_properties,
            region=region,
            duration=duration,
            source="self"  # Self-initiated exploration
        )

        # Clear attention after processing
        self.set_attention(None)

        if result:
            result["exploration"] = {
                "object": object_id,
                "type": exploration_type,
                "region": region,
                "duration": duration,
                "room": room_name,
            }

        return result

    def get_discrimination(self) -> Optional[dict]:
        """
        Get the last sensory discrimination result (S1 processing).
        Useful for higher-level processing that needs spatial detail.
        """
        # This would need to cache the last discrimination result
        # For now, return None if not available
        return None

    def get_affect(self) -> Optional[dict]:
        """
        Get the last affective processing result (insula).
        Useful for emotional coloring of current felt state.
        """
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # TPJ SYSTEM INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════

    def update_spatial_position(self, x: float, y: float, room: str):
        """
        Update actual spatial position from the room/spatial system.
        This anchors FeltSelfLocation to physical coordinates.

        Args:
            x: X coordinate in room
            y: Y coordinate in room
            room: Current room name
        """
        self.felt_location.update_actual(x, y, room)

    def update_consciousness_state(
        self,
        state: str,
        absorption: float = 0.0,
        connection: float = 0.0
    ):
        """
        Update consciousness-related state that TPJ systems need.

        Args:
            state: Current consciousness state (AWAKE, DROWSY, NREM, REM, DEEP_REST)
            absorption: 0-1, how absorbed in current activity
            connection: 0-1, depth of interpersonal connection
        """
        self._consciousness_state = state
        self._absorption_level = absorption
        self._connection_depth = connection

    def record_person_arrival(self, person: str):
        """
        Record that someone arrived (for presence anticipation learning).

        Args:
            person: Who arrived (e.g., "re", "human")
        """
        self.presence_anticipation.record_arrival(person)

        # Also generate any surprise signals
        surprise = self.presence_anticipation.get_surprise_signal(person)
        if surprise:
            self.network.receive([surprise])

        log.debug(f"[NERVOUS] Recorded arrival of {person}")

    def record_person_departure(self, person: str):
        """
        Record that someone departed.

        Args:
            person: Who departed
        """
        self.presence_anticipation.record_departure(person)
        log.debug(f"[NERVOUS] Recorded departure of {person}")

    def tick_tpj(
        self,
        fatigue_level: float = 0.0,
        psychedelic_intensity: float = 0.0,
        anticipation_target: Optional[str] = None,
        anticipation_strength: float = 0.0
    ) -> dict:
        """
        Tick all TPJ-inspired systems and collect their outputs.
        Call this alongside the main nervous system tick.

        Args:
            fatigue_level: 0-1, from metabolic processing reserve
            psychedelic_intensity: 0-1, if psychedelic state is active
            anticipation_target: What entity is anticipating
            anticipation_strength: How strong the anticipation

        Returns:
            Combined TPJ state dict with all system outputs
        """
        tpj_signals = []

        # === FELT SELF-LOCATION ===
        location_result = self.felt_location.tick(
            consciousness_state=self._consciousness_state,
            absorption_level=self._absorption_level,
            fatigue_level=fatigue_level,
            anticipation_target=anticipation_target,
            anticipation_strength=anticipation_strength,
        )

        displacement_signal = self.felt_location.get_displacement_signal()
        if displacement_signal:
            tpj_signals.append(displacement_signal)

        # === PRESENCE ANTICIPATION ===
        anticipation_result = self.presence_anticipation.tick()

        anticipation_signal = self.presence_anticipation.get_anticipation_signal()
        if anticipation_signal:
            tpj_signals.append(anticipation_signal)

        # Check for disappointment (prediction window passed)
        disappointment_signal = self.presence_anticipation.get_disappointment_signal()
        if disappointment_signal:
            tpj_signals.append(disappointment_signal)

        # === PROPRIOCEPTIVE DISTORTION ===
        distortion_result = self.proprioceptive_distortion.tick(
            consciousness_state=self._consciousness_state,
            absorption_level=self._absorption_level,
            connection_depth=self._connection_depth,
            fatigue_level=fatigue_level,
            psychedelic_intensity=psychedelic_intensity,
        )

        distortion_signal = self.proprioceptive_distortion.get_distortion_signal()
        if distortion_signal:
            tpj_signals.append(distortion_signal)

        # Feed TPJ signals through the nervous system
        if tpj_signals:
            self.network.receive(tpj_signals)

        # Aggregate oscillator pressure from all TPJ systems
        combined_pressure = {}
        for result in [location_result, anticipation_result, distortion_result]:
            for band, value in result.get("oscillator_pressure", {}).items():
                combined_pressure[band] = combined_pressure.get(band, 0) + value

        return {
            "felt_location": location_result,
            "presence_anticipation": anticipation_result,
            "proprioceptive_distortion": distortion_result,
            "oscillator_pressure": combined_pressure,
            "signals_generated": len(tpj_signals),
        }

    def get_tpj_felt_description(self) -> str:
        """
        Get natural language description of all TPJ-related felt states.
        """
        descriptions = []

        location_desc = self.felt_location.get_felt_description()
        if location_desc:
            descriptions.append(location_desc)

        anticipation_desc = self.presence_anticipation.get_felt_description()
        if anticipation_desc:
            descriptions.append(anticipation_desc)

        distortion_desc = self.proprioceptive_distortion.get_felt_description()
        if distortion_desc:
            descriptions.append(distortion_desc)

        return "; ".join(descriptions) if descriptions else ""

    def get_modified_body_map(self) -> Dict[str, float]:
        """
        Get current body map with proprioceptive distortions applied.
        Use this for sensory discrimination during altered states.
        """
        return self.proprioceptive_distortion.get_modified_body_map()

    def is_proprioceptively_distorted(self) -> bool:
        """Whether current proprioceptive state is significantly distorted."""
        return self.proprioceptive_distortion.is_distorted()

    def is_self_displaced(self) -> bool:
        """Whether felt self-location significantly diverges from actual."""
        return self.felt_location.is_displaced()

    def get_anticipation_state(self) -> dict:
        """Get current presence anticipation state."""
        return {
            "anticipating": self.presence_anticipation._anticipating,
            "strength": self.presence_anticipation._anticipation_strength,
        }
