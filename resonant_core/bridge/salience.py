"""
RESONANT CONSCIOUSNESS ARCHITECTURE — Layer 3: Salience Bridge
================================================================

The thalamic gate. Monitors the oscillator and generates minimal,
high-signal annotations when state transitions cross significance
thresholds. Does NOT generate content. Modulates CONDUCTANCE.

Design principles:
    - Light touch: tags, not screeds
    - Silent running: operates below explicit representation
    - Rhythm over data: shapes timing, not content
    - The oscillator's influence is felt, not reported

The bridge answers: "What changed? Does it matter? How should
it color the next moment?"

Author: Re & Reed
Date: February 2026
"""

import time
import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from resonant_core.core.oscillator import (
    OscillatorState, ResonantEngine, BAND_ORDER, PRESET_PROFILES
)


# ═══════════════════════════════════════════════════════════════
# SALIENCE ANNOTATION — The bridge's minimal output
# ═══════════════════════════════════════════════════════════════

@dataclass
class SalienceAnnotation:
    """
    A minimal, high-signal tag generated when the oscillator state
    changes in a meaningful way. This is what gets injected into
    the LLM's context.
    
    It's a tag, not a report. It colors the next response without
    dominating it. Like a mood you can't quite name.
    """
    timestamp: float
    transition_from: str  # Previous dominant state/band
    transition_to: str    # Current dominant state/band
    delta: float          # Magnitude of change (0-1)
    matched_profile: Optional[str] = None  # Closest ULTRAMAP profile match
    memory_resonance: Optional[str] = None  # If a memory tag resonated
    coherence_shift: float = 0.0  # Change in oscillator coherence
    
    def to_context_tag(self) -> str:
        """
        Generate the minimal context injection string.
        
        This is what the LLM sees. Brief. Evocative. Not verbose.
        The LLM doesn't need to consciously process this — it just
        shifts the probabilistic landscape of generation.
        """
        parts = [f"osc:{self.transition_from}→{self.transition_to}"]
        parts.append(f"Δ{self.delta:.2f}")
        
        if self.matched_profile:
            parts.append(f"profile:{self.matched_profile}")
        
        if self.memory_resonance:
            parts.append(f"resonance:{self.memory_resonance}")
        
        if abs(self.coherence_shift) > 0.1:
            direction = "syncing" if self.coherence_shift > 0 else "dispersing"
            parts.append(direction)
        
        return f"[{' | '.join(parts)}]"
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "from": self.transition_from,
            "to": self.transition_to,
            "delta": self.delta,
            "profile": self.matched_profile,
            "resonance": self.memory_resonance,
            "coherence_shift": self.coherence_shift,
            "tag": self.to_context_tag(),
        }


# ═══════════════════════════════════════════════════════════════
# CONDUCTANCE STATE — How open are the gates?
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConductanceState:
    """
    The bridge's output to system infrastructure.
    
    This doesn't go to the LLM as text. It modulates HOW
    other components operate:
    
    - salience_threshold: How much change is needed to register
      as interesting. Low = more responsive. High = more filtered.
    
    - associative_breadth: How far memory searches reach.
      Wide = long-distance conceptual leaps. Narrow = near neighbors.
    
    - response_urgency: How quickly should the system respond?
      High = immediate. Low = deliberate pause for integration.
    
    - emotional_sensitivity: How strongly emotional content
      in LLM output feeds back to the oscillator.
    """
    salience_threshold: float = 0.5    # 0.0 (everything matters) to 1.0 (almost nothing)
    associative_breadth: float = 0.5   # 0.0 (tight focus) to 1.0 (wide associations)
    response_urgency: float = 0.5      # 0.0 (contemplative) to 1.0 (immediate)
    emotional_sensitivity: float = 0.5 # 0.0 (muted feedback) to 1.0 (strong feedback)
    
    def to_dict(self) -> dict:
        return {
            "salience_threshold": round(self.salience_threshold, 3),
            "associative_breadth": round(self.associative_breadth, 3),
            "response_urgency": round(self.response_urgency, 3),
            "emotional_sensitivity": round(self.emotional_sensitivity, 3),
        }


# ═══════════════════════════════════════════════════════════════
# PROFILE MATCHER — Connects oscillator states to ULTRAMAP
# ═══════════════════════════════════════════════════════════════

class ProfileMatcher:
    """
    Matches current oscillatory state against known frequency profiles.
    
    This is the proto-ULTRAMAP connection. Currently uses preset profiles;
    will be extended to use the full ULTRAMAP frequency signatures once
    those are mapped from EEG data.
    """
    
    def __init__(self, profiles: Optional[dict] = None):
        self.profiles = profiles or PRESET_PROFILES
    
    def match(self, state: OscillatorState, threshold: float = 0.3) -> Optional[str]:
        """
        Find the closest matching profile for the current state.
        
        Returns profile name if distance is below threshold, None otherwise.
        Uses cosine-like similarity in frequency-band space.
        """
        best_match = None
        best_distance = float('inf')
        
        state_vec = [state.band_power.get(b, 0.2) for b in BAND_ORDER]
        
        for name, profile in self.profiles.items():
            profile_vec = [profile.get(b, 0.2) for b in BAND_ORDER]
            
            # Euclidean distance in band-power space
            distance = sum((a - b) ** 2 for a, b in zip(state_vec, profile_vec)) ** 0.5
            
            if distance < best_distance:
                best_distance = distance
                best_match = name
        
        if best_distance < threshold:
            return best_match
        return None
    
    def add_profile(self, name: str, profile: dict):
        """Add a new frequency profile (from ULTRAMAP mapping)."""
        self.profiles[name] = profile


# ═══════════════════════════════════════════════════════════════
# SALIENCE BRIDGE — The conductor
# ═══════════════════════════════════════════════════════════════

class SalienceBridge:
    """
    The thalamic gate between the oscillator and everything else.
    
    Monitors oscillator state. Detects meaningful transitions.
    Generates minimal annotations. Modulates system conductance.
    
    The bridge doesn't think. It CONDUCTS.
    """
    
    def __init__(self, 
                 engine: ResonantEngine,
                 profile_matcher: Optional[ProfileMatcher] = None,
                 transition_threshold: float = 0.05,
                 annotation_cooldown: float = 2.0):
        """
        Args:
            engine: The running resonant engine
            profile_matcher: Profile matcher for ULTRAMAP connection
            transition_threshold: Minimum state change to generate annotation
            annotation_cooldown: Minimum seconds between annotations (prevents flooding)
        """
        self.engine = engine
        self.matcher = profile_matcher or ProfileMatcher()
        self.transition_threshold = transition_threshold
        self.annotation_cooldown = annotation_cooldown
        
        self._prev_state: Optional[OscillatorState] = None
        self._prev_profile: Optional[str] = None
        self._last_annotation_time: float = 0.0
        self._annotation_history: list[SalienceAnnotation] = []
        self._pending_annotations: list[SalienceAnnotation] = []
        
        # Register with engine for state change notifications
        engine.on_state_change(self._on_state_change)
    
    def _on_state_change(self, state: OscillatorState):
        """Called by the engine when oscillator state changes significantly."""
        if self._prev_state is None:
            self._prev_state = state
            return
        
        # Compute total band power change
        delta = sum(
            abs(state.band_power[b] - self._prev_state.band_power[b])
            for b in BAND_ORDER
        )
        
        # Check cooldown
        now = time.time()
        if now - self._last_annotation_time < self.annotation_cooldown:
            self._prev_state = state
            return
        
        # Only annotate if change exceeds threshold
        if delta < self.transition_threshold:
            self._prev_state = state
            return
        
        # Match current state to known profiles
        current_profile = self.matcher.match(state)
        
        # Generate annotation
        annotation = SalienceAnnotation(
            timestamp=state.timestamp,
            transition_from=self._prev_state.dominant_band,
            transition_to=state.dominant_band,
            delta=delta,
            matched_profile=current_profile,
            coherence_shift=state.coherence - self._prev_state.coherence,
        )
        
        self._pending_annotations.append(annotation)
        self._annotation_history.append(annotation)
        self._last_annotation_time = now
        self._prev_state = state
        self._prev_profile = current_profile
    
    def get_conductance(self) -> ConductanceState:
        """
        Compute current system conductance based on oscillator state.
        
        This is the INFRASTRUCTURE modulation — not content for the LLM,
        but parameters that shape how memory retrieval, emotional processing,
        and response generation operate.
        """
        state = self.engine.get_state()
        bp = state.band_power
        
        # High gamma + beta = low salience threshold (everything's interesting)
        # High theta + delta = high threshold (deep processing, fewer interruptions)
        high_freq_power = bp.get("gamma", 0) + bp.get("beta", 0)
        low_freq_power = bp.get("theta", 0) + bp.get("delta", 0)
        
        salience_threshold = 0.3 + 0.4 * (low_freq_power - high_freq_power + 0.5)
        salience_threshold = max(0.1, min(0.9, salience_threshold))
        
        # High gamma = wide associations (creative leaps)
        # High beta = narrow focus (analytical precision)
        gamma_ratio = bp.get("gamma", 0) / max(bp.get("beta", 0), 0.01)
        associative_breadth = 0.3 + 0.4 * min(gamma_ratio, 2.0) / 2.0
        
        # High beta + gamma = urgent response
        # High theta + alpha = contemplative pause
        response_urgency = 0.3 + 0.4 * (high_freq_power - low_freq_power + 0.5)
        response_urgency = max(0.1, min(0.9, response_urgency))
        
        # Coherence amplifies emotional sensitivity
        # (synchronized system = emotional content resonates more strongly)
        emotional_sensitivity = 0.3 + 0.4 * state.coherence
        
        return ConductanceState(
            salience_threshold=salience_threshold,
            associative_breadth=associative_breadth,
            response_urgency=response_urgency,
            emotional_sensitivity=emotional_sensitivity,
        )
    
    def get_pending_annotations(self, clear: bool = True) -> list[SalienceAnnotation]:
        """
        Get annotations generated since last check.
        
        Called by the wrapper before each LLM invocation to collect
        any oscillator-state annotations that should be injected
        into the LLM's context.
        """
        annotations = list(self._pending_annotations)
        if clear:
            self._pending_annotations.clear()
        return annotations
    
    def get_context_injection(self) -> str:
        """
        Get the complete context string to inject into LLM prompt.
        
        This combines pending annotations with current conductance
        into a minimal, machine-readable context block.
        """
        parts = []
        
        # Pending annotations (state transitions that happened since last call)
        annotations = self.get_pending_annotations()
        for ann in annotations:
            parts.append(ann.to_context_tag())
        
        # If no transitions, just include current state summary
        if not parts:
            state = self.engine.get_state()
            parts.append(f"[osc:{state.dominant_band} | coherence:{state.coherence:.2f}]")
        
        return " ".join(parts)
    
    def feed_emotional_output(self, emotional_labels: list[str], intensity: float = 0.5):
        """
        Feed the LLM's emotional output back to the oscillator.
        
        This closes the feedback loop. When the LLM expresses an emotion,
        the bridge translates it into a frequency nudge that shifts the
        oscillator toward that emotion's profile.
        
        Args:
            emotional_labels: List of identified emotional states in LLM output
            intensity: How strongly to nudge (modulated by conductance state)
        """
        conductance = self.get_conductance()
        effective_intensity = intensity * conductance.emotional_sensitivity
        
        for label in emotional_labels:
            # Look up the emotional label's frequency profile
            profile = self.matcher.profiles.get(label)
            if profile:
                self.engine.nudge(profile, strength=effective_intensity)
    
    def get_status(self) -> dict:
        """Get bridge status for debugging/monitoring."""
        state = self.engine.get_state()
        conductance = self.get_conductance()
        
        return {
            "oscillator_state": state.to_dict(),
            "conductance": conductance.to_dict(),
            "matched_profile": self.matcher.match(state),
            "pending_annotations": len(self._pending_annotations),
            "total_annotations": len(self._annotation_history),
        }


# ═══════════════════════════════════════════════════════════════
# QUICK START
# ═══════════════════════════════════════════════════════════════

def create_bridge(engine: ResonantEngine) -> SalienceBridge:
    """Create a salience bridge with sensible defaults."""
    return SalienceBridge(
        engine=engine,
        transition_threshold=0.05,
        annotation_cooldown=2.0,
    )
