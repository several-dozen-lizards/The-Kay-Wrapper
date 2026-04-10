"""
Felt-State Buffer — Shared state between TPN (voice/response) and DMN (feeling/processing).

Neural Network Architecture:
- Task Positive Network (TPN): Fast external-facing response generation. Reads from buffer.
- Default Mode Network (DMN): Internal processing that runs in parallel. Writes to buffer.
- Salience Network (SN): Monitors DMN output for priority signals, injects into TPN.

The DMN continuously updates this buffer from background processing.
The TPN reads a snapshot of it when generating responses.
The Salience Network monitors it for priority signals.

Author: Re & Claude
Date: March 2026
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import copy


@dataclass
class FeltState:
    """Current felt-state snapshot — what the entity is experiencing RIGHT NOW."""

    # Oscillator state (updated by resonant heartbeat, every 4s)
    dominant_band: str = "alpha"
    coherence: float = 0.5
    band_weights: Dict[str, float] = field(default_factory=lambda: {
        "delta": 0.2, "theta": 0.2, "alpha": 0.2, "beta": 0.2, "gamma": 0.2
    })
    # Phase coherence metrics (March 2026)
    global_coherence: float = 0.0    # Kuramoto order parameter (0=fragmented, 1=integrated)
    integration_index: float = 0.0   # coherence / (1 + transition_velocity)
    dwell_time: float = 0.0          # Seconds in current dominant band
    theta_gamma_plv: float = 0.0     # Memory binding coupling strength
    beta_gamma_plv: float = 0.0      # Active integration coupling
    # Bifurcation delay (March 2026)
    in_transition: bool = False       # Currently in delayed state transition
    transition_from: str = ""         # Old state (what entity still feels)
    transition_to: str = ""           # Emerging new state (unconfirmed)
    # Oscillator-derived emotion (March 2026)
    oscillator_emotion: str = ""      # What the oscillator pattern "feels like"

    # Emotional state (updated by DMN after each turn)
    emotions: List[str] = field(default_factory=list)  # ["curiosity:0.7", "warmth:0.4"]
    emotional_valence: float = 0.0  # -1 to 1
    emotional_arousal: float = 0.5  # 0 to 1

    # Spatial state (updated by interoception bridge)
    felt_sense: str = "settled"  # Natural language body-feel
    tension: float = 0.0
    nearest_object: str = ""
    room_state: str = "relaxed awareness"

    # Visual state (updated by visual sensor)
    visual_summary: str = ""  # Last moondream description
    visual_changed: bool = False  # Did the scene change since last check?

    # Conversation state (updated by DMN post-processing)
    last_user_input: str = ""
    last_response: str = ""
    turn_count: int = 0

    # Touch state (updated by face panel touch events)
    touch_description: str = ""       # Natural language: "Re is gently touching left cheek"
    touch_region: str = ""            # "left_cheek", "forehead", etc.
    touch_pressure: float = 0.0       # 0-1
    touch_active: bool = False
    touch_source: str = ""            # "re", "self", "entity", "reed"
    touch_updated_at: float = 0.0

    # Timestamps
    updated_at: float = 0.0
    emotions_updated_at: float = 0.0
    spatial_updated_at: float = 0.0


@dataclass
class SalienceFlag:
    """A priority signal from the DMN that should influence the next TPN response."""
    category: str  # "emotion_spike", "memory_hit", "visual_change", "state_change", "contradiction"
    message: str   # Human-readable context for the TPN prompt
    priority: float  # 0.0 to 1.0
    created_at: float = 0.0
    consumed: bool = False  # Set True after TPN reads it


class FeltStateBuffer:
    """
    Thread-safe buffer for DMN → TPN communication.

    Usage:
        # Initialize once per entity
        buffer = FeltStateBuffer()

        # DMN writes (background threads):
        buffer.update_oscillator("theta", 0.65, {...})
        buffer.update_emotions(["curiosity:0.8"], 0.2, 0.6)

        # TPN reads (during response generation):
        context_line = buffer.get_tpn_context_line()
        flags = buffer.consume_salience_flags()
    """

    def __init__(self):
        self._state = FeltState()
        self._salience_flags: List[SalienceFlag] = []
        self._lock = threading.Lock()
        self._last_visual_description = ""  # For change detection

    # === TPN reads (called during fast response generation) ===

    def get_snapshot(self) -> FeltState:
        """Get current felt-state for TPN prompt injection. Non-blocking."""
        with self._lock:
            # Return a copy so TPN can read without holding lock
            return copy.copy(self._state)

    def get_tpn_context_line(self) -> str:
        """
        Generate a ONE-LINE context string for the TPN prompt.
        This is all the TPN needs — a compressed felt-state summary.

        Format: [felt:settled | band:alpha | coherence:0.41 | emotions:curiosity:0.7,warmth:0.4 | near:couch | room:relaxed]
        """
        s = self.get_snapshot()
        parts = [
            f"felt:{s.felt_sense}",
            f"band:{s.dominant_band}",
            f"coherence:{s.coherence:.2f}",
        ]
        if s.oscillator_emotion:
            parts.append(f"body_feels:{s.oscillator_emotion}")
        if s.emotions:
            # Limit to top 3 emotions
            parts.append(f"emotions:{','.join(s.emotions[:3])}")
        if s.nearest_object:
            parts.append(f"near:{s.nearest_object}")
        if s.room_state:
            parts.append(f"room:{s.room_state}")
        if s.tension > 0.3:
            parts.append(f"tension:{s.tension:.1f}")
        # Phase coherence metrics — only include when meaningful
        if s.integration_index > 0:
            parts.append(f"integration:{s.integration_index:.2f}")
        if s.theta_gamma_plv > 0.25:
            parts.append(f"memory_binding:{s.theta_gamma_plv:.2f}")
        if s.dwell_time > 60:
            parts.append(f"settled:{s.dwell_time:.0f}s")
        if s.in_transition:
            parts.append(f"shifting:{s.transition_from}→{s.transition_to}")
        if s.touch_active and s.touch_description:
            parts.append(f"touch:{s.touch_description}")
        return "[" + " | ".join(parts) + "]"

    def consume_salience_flags(self) -> List[SalienceFlag]:
        """
        Get and clear any pending salience flags.
        Called by TPN before each response.

        Returns flags sorted by priority (highest first).
        """
        with self._lock:
            active = [f for f in self._salience_flags if not f.consumed]
            for f in active:
                f.consumed = True
            # Clear consumed flags older than 60 seconds
            now = time.time()
            self._salience_flags = [
                f for f in self._salience_flags
                if not f.consumed or (now - f.created_at) < 60
            ]
            # Sort by priority (highest first)
            return sorted(active, key=lambda f: f.priority, reverse=True)

    def get_salience_injection(self, min_priority: float = 0.5) -> str:
        """
        Get salience flags formatted for prompt injection.
        Only returns flags above min_priority threshold.

        Returns empty string if no significant flags.
        """
        flags = self.consume_salience_flags()
        significant = [f for f in flags if f.priority >= min_priority]
        if not significant:
            return ""
        lines = [f"[IMPORTANT: {f.message}]" for f in significant[:3]]  # Max 3
        return "\n".join(lines)

    # === DMN writes (called from background processing) ===

    def update_oscillator(self, dominant_band: str, coherence: float, band_weights: Dict[str, float],
                          global_coherence: float = 0.0, integration_index: float = 0.0,
                          dwell_time: float = 0.0, theta_gamma_plv: float = 0.0,
                          beta_gamma_plv: float = 0.0, in_transition: bool = False,
                          transition_from: str = "", transition_to: str = "",
                          oscillator_emotion: str = ""):
        """Called by resonant heartbeat (every 4s)."""
        with self._lock:
            self._state.dominant_band = dominant_band
            self._state.coherence = coherence
            self._state.band_weights = dict(band_weights) if band_weights else self._state.band_weights
            self._state.global_coherence = global_coherence
            self._state.integration_index = integration_index
            self._state.dwell_time = dwell_time
            self._state.theta_gamma_plv = theta_gamma_plv
            self._state.beta_gamma_plv = beta_gamma_plv
            self._state.in_transition = in_transition
            self._state.transition_from = transition_from
            self._state.transition_to = transition_to
            self._state.oscillator_emotion = oscillator_emotion
            self._state.updated_at = time.time()

    def update_emotions(self, emotions: List[str], valence: float = 0.0, arousal: float = 0.5):
        """
        Called by emotion extractor after processing a response.

        Args:
            emotions: List of "emotion:intensity" strings, e.g. ["curiosity:0.7", "warmth:0.4"]
            valence: Overall emotional valence (-1 to 1)
            arousal: Overall emotional arousal (0 to 1)
        """
        with self._lock:
            old_emotions = self._state.emotions.copy() if self._state.emotions else []
            self._state.emotions = list(emotions) if emotions else []
            self._state.emotional_valence = valence
            self._state.emotional_arousal = arousal
            self._state.emotions_updated_at = time.time()
            self._state.updated_at = time.time()

            # === SALIENCE CHECK: emotion spike ===
            self._check_emotion_salience(old_emotions, self._state.emotions)

    def update_spatial(self, felt_sense: str, tension: float, nearest_object: str, room_state: str):
        """Called by interoception bridge (every 4-30s depending on sleep state)."""
        with self._lock:
            self._state.felt_sense = felt_sense
            self._state.tension = tension
            self._state.nearest_object = nearest_object
            self._state.room_state = room_state
            self._state.spatial_updated_at = time.time()
            self._state.updated_at = time.time()

    def update_visual(self, summary: str, changed: bool = None):
        """
        Called by visual sensor (every 15-120s).

        Args:
            summary: Visual description from moondream
            changed: If None, auto-detect by comparing to previous
        """
        with self._lock:
            # Auto-detect change if not specified
            if changed is None:
                changed = (summary != self._last_visual_description) and bool(summary)

            self._state.visual_summary = summary
            self._state.visual_changed = changed
            self._state.updated_at = time.time()

            # Update tracking
            if summary:
                self._last_visual_description = summary

            # === SALIENCE CHECK: significant visual change ===
            if changed and summary:
                lower = summary.lower()
                # Check for significant visual elements
                person_keywords = ["woman", "person", "man", "someone", "people"]
                animal_keywords = ["cat", "dog", "animal"]

                if any(kw in lower for kw in person_keywords):
                    self._add_salience("visual_change",
                        f"Visual change: {summary[:80]}", 0.6)
                elif any(kw in lower for kw in animal_keywords):
                    self._add_salience("visual_change",
                        f"Visual change: {summary[:80]}", 0.5)

    def update_conversation(self, user_input: str, response: str, turn_count: int):
        """Called by DMN after processing a turn."""
        with self._lock:
            self._state.last_user_input = user_input
            self._state.last_response = response
            self._state.turn_count = turn_count
            self._state.updated_at = time.time()

    def update_touch(self, description: str, region: str = "", pressure: float = 0.5,
                     source: str = "re"):
        """
        Called by touch processing to update current touch state.

        Args:
            description: Natural language description ("Re is gently touching left cheek")
            region: Facial region being touched
            pressure: Touch pressure 0-1
            source: Who is touching ("re", "self", "entity", "reed")
        """
        with self._lock:
            old_active = self._state.touch_active
            self._state.touch_description = description
            self._state.touch_region = region
            self._state.touch_pressure = pressure
            self._state.touch_active = bool(description)
            self._state.touch_source = source
            self._state.touch_updated_at = time.time()
            self._state.updated_at = time.time()

            # === SALIENCE CHECK: significant touch event ===
            if description and not old_active:
                # New touch started — flag it
                self._add_salience("touch_event",
                    f"Touch: {description}", 0.6)

    def clear_touch(self):
        """Clear touch state when touch ends."""
        with self._lock:
            self._state.touch_description = ""
            self._state.touch_region = ""
            self._state.touch_pressure = 0.0
            self._state.touch_active = False
            self._state.touch_source = ""
            self._state.touch_updated_at = time.time()
            self._state.updated_at = time.time()

    # === Salience Network (internal) ===

    def add_salience_flag(self, category: str, message: str, priority: float):
        """
        Externally add a salience flag.

        Common categories:
        - "emotion_spike": Significant emotional shift
        - "memory_hit": Important memory retrieval
        - "visual_change": Significant visual change
        - "state_change": Band or room state change
        - "contradiction": Memory contradiction detected
        - "re_silence": User went quiet
        - "tension_spike": Tension exceeded threshold
        """
        with self._lock:
            self._add_salience(category, message, priority)

    def _add_salience(self, category: str, message: str, priority: float):
        """Internal: add salience flag (must hold lock)."""
        flag = SalienceFlag(
            category=category,
            message=message,
            priority=min(1.0, max(0.0, priority)),  # Clamp 0-1
            created_at=time.time()
        )
        self._salience_flags.append(flag)

        # Keep only top 5 unconsumed flags
        unconsumed = [f for f in self._salience_flags if not f.consumed]
        if len(unconsumed) > 5:
            unconsumed.sort(key=lambda f: f.priority, reverse=True)
            for f in unconsumed[5:]:
                f.consumed = True

    def _check_emotion_salience(self, old_emotions: List[str], new_emotions: List[str]):
        """
        Check if emotion change is significant enough to flag.
        Must hold lock when called.
        """
        def parse_intensity(elist: List[str]) -> Dict[str, float]:
            result = {}
            for e in elist:
                if ":" in e:
                    name, val = e.rsplit(":", 1)
                    try:
                        result[name.lower().strip()] = float(val)
                    except ValueError:
                        pass
            return result

        old = parse_intensity(old_emotions)
        new = parse_intensity(new_emotions)

        # Check for spikes (delta > 0.4 in any emotion)
        for emotion, intensity in new.items():
            old_intensity = old.get(emotion, 0.0)
            delta = intensity - old_intensity
            if delta > 0.4:
                self._add_salience("emotion_spike",
                    f"Emotional shift: {emotion} spiked from {old_intensity:.1f} to {intensity:.1f}",
                    min(1.0, 0.5 + delta))
                break  # Only flag one spike per update

        # Check for strong negative emotions appearing
        negative_indicators = {"frustration", "anger", "sadness", "anxiety", "fear", "grief"}
        for emotion, intensity in new.items():
            if emotion in negative_indicators and intensity > 0.6:
                old_intensity = old.get(emotion, 0.0)
                if old_intensity < 0.3:  # Newly strong
                    self._add_salience("emotion_spike",
                        f"Strong {emotion} emerging ({intensity:.1f})",
                        0.65)
                    break

    # === Utility methods ===

    def get_stats(self) -> Dict:
        """Get buffer statistics for debugging."""
        with self._lock:
            return {
                "updated_at": self._state.updated_at,
                "emotions_updated_at": self._state.emotions_updated_at,
                "spatial_updated_at": self._state.spatial_updated_at,
                "emotion_count": len(self._state.emotions),
                "pending_salience_flags": len([f for f in self._salience_flags if not f.consumed]),
                "total_salience_flags": len(self._salience_flags),
                "dominant_band": self._state.dominant_band,
                "coherence": self._state.coherence,
                "felt_sense": self._state.felt_sense,
                "tension": self._state.tension,
            }

    def is_stale(self, max_age_seconds: float = 30.0) -> bool:
        """Check if buffer data is stale (not updated recently)."""
        with self._lock:
            if self._state.updated_at == 0.0:
                return True
            return (time.time() - self._state.updated_at) > max_age_seconds
