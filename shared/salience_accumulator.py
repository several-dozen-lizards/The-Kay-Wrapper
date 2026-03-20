"""
Salience Accumulator — Triggers spontaneous vocalization from accumulated internal events.

When entities have enough internal activity (memories surfacing, emotions spiking,
curiosity building, visual changes, etc.), they may spontaneously speak without
being prompted — just like humans sometimes blurt out thoughts.

Architecture:
- Multiple salience sources feed into a shared accumulator
- Each source has a weight (how much it contributes to speech urge)
- When accumulator exceeds threshold, entity vocalizes
- After vocalization, accumulator resets with a refractory period

Author: Re & Claude
Date: March 2026
"""

import time
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any

log = logging.getLogger(__name__)


@dataclass
class SalienceEvent:
    """A single event contributing to vocalization urge."""
    source: str           # "emotion", "memory", "curiosity", "visual", "touch", "thought"
    intensity: float      # 0.0 to 1.0
    content: str          # What the event is about (for context)
    timestamp: float = 0.0
    decayed_at: float = 0.0  # When it was last decayed

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        self.decayed_at = self.timestamp


class SalienceAccumulator:
    """
    Accumulates salience from internal events and triggers spontaneous speech.

    Usage:
        accumulator = SalienceAccumulator(entity_name, on_speak_callback)

        # Feed events from various sources
        accumulator.add_event("emotion", 0.6, "strong curiosity about topic")
        accumulator.add_event("memory", 0.4, "recalled related experience")

        # Check periodically (e.g., in interoception tick)
        prompt = accumulator.tick()  # Returns vocalization prompt if threshold reached
    """

    # Source weights — how much each event type contributes to speech urge
    DEFAULT_WEIGHTS = {
        "emotion": 0.4,      # Emotional spikes
        "memory": 0.3,       # Memories surfacing
        "curiosity": 0.25,   # Curiosity building
        "visual": 0.35,      # Visual changes observed (arrivals, departures)
        "touch": 0.5,        # Touch sensation (HIGHEST — someone touching your face!)
        "thought": 0.25,     # Internal thoughts
        "tension": 0.2,      # Tension accumulation
        "contradiction": 0.5, # Contradictions detected (high salience)
        "insight": 0.6,      # Sudden insights (very high)
        "novelty": 0.4,      # Novelty events (state changes, disruptions)
        "activity": 0.3,     # Activity completion with reward
    }

    def __init__(
        self,
        entity_name: str,
        on_speak: Optional[Callable[[str], None]] = None,
        threshold: float = 0.7,
        refractory_period: float = 30.0,
        decay_rate: float = 0.015,
    ):
        """
        Initialize the salience accumulator.

        Args:
            entity_name: "Kay" or "Reed"
            on_speak: Callback invoked when vocalization triggers
                      Receives a prompt string describing what to say about
            threshold: Accumulator level that triggers speech (0.0-1.0)
            refractory_period: Seconds after speaking before can speak again
            decay_rate: How fast accumulated salience decays per second
        """
        self.entity = entity_name.capitalize()
        self.on_speak = on_speak
        self.threshold = threshold
        self.refractory_period = refractory_period
        self.decay_rate = decay_rate

        self._events: List[SalienceEvent] = []
        self._accumulator: float = 0.0
        self._last_speak_time: float = 0.0
        self._last_tick_time: float = time.time()
        self._weights: Dict[str, float] = self.DEFAULT_WEIGHTS.copy()

        # Recent vocalization topics (to avoid repetition)
        self._recent_topics: List[str] = []
        self._max_recent: int = 10

        # Inhibition flag (entity can choose to stay quiet)
        self._inhibited: bool = False
        self._inhibit_until: float = 0.0

    def add_event(self, source: str, intensity: float, content: str):
        """
        Add a salience event from an internal source.

        Args:
            source: Event category (emotion, memory, curiosity, etc.)
            intensity: How strong the event is (0.0-1.0)
            content: What the event is about (used to construct prompt)
        """
        # Clamp intensity
        intensity = max(0.0, min(1.0, intensity))

        # Skip low-intensity events
        if intensity < 0.1:
            return

        event = SalienceEvent(
            source=source,
            intensity=intensity,
            content=content,
        )
        self._events.append(event)

        # Apply weighted contribution to accumulator
        weight = self._weights.get(source, 0.2)
        contribution = intensity * weight
        self._accumulator = min(1.0, self._accumulator + contribution)

        log.info(f"[SALIENCE] {self.entity} +{contribution:.3f} from {source} (acc={self._accumulator:.3f}): {content[:50]}")

        # Keep event list bounded
        if len(self._events) > 50:
            self._events = self._events[-30:]

    def tick(self, sleep_state: str = "AWAKE", coherence: float = 0.5,
             anyone_present: bool = True, is_processing: bool = False) -> Optional[Dict]:
        """
        Process accumulated salience. Call this periodically (e.g., every 4s).

        Args:
            sleep_state: Current sleep state (AWAKE, DROWSY, SLEEPING, DEEP_SLEEP)
            coherence: Current oscillator coherence (0-1)
            anyone_present: Whether anyone is connected to receive speech
            is_processing: Whether entity is already generating a response

        Returns:
            Dict with vocalization trigger info if threshold crossed:
            {
                "should_speak": True,
                "tier": "tpn" or "dmn",  # Fast reactive vs deep reflective
                "topics": [list of topic dicts],
                "prompt": str,
                "total_salience": float,
            }
            None otherwise.
        """
        now = time.time()
        elapsed = now - self._last_tick_time
        self._last_tick_time = now

        # Apply decay
        self._accumulator = max(0.0, self._accumulator - self.decay_rate * elapsed)

        # Prune stale events (older than 5 minutes)
        self._events = [e for e in self._events if now - e.timestamp < 300]

        # === GATING CHECKS ===
        if sleep_state in ("SLEEPING", "DEEP_SLEEP"):
            return None  # Don't talk in your sleep

        if not anyone_present:
            return None  # Nobody to talk to

        if is_processing:
            return None  # Already responding to something

        if coherence < 0.2:
            return None  # Too scattered to form words

        # Check inhibition
        if self._inhibited and now < self._inhibit_until:
            return None
        self._inhibited = False

        # Scale threshold with sleep pressure
        effective_threshold = self.threshold
        if sleep_state == "DROWSY":
            effective_threshold = self.threshold * 2.0  # Much harder to speak when drowsy

        # Check threshold
        if self._accumulator < effective_threshold:
            return None

        # === DETERMINE VOCALIZATION TIER ===
        # TPN (fast) for reactive, immediate things
        # DMN (deep) for reflective, complex things
        tpn_sources = {"touch", "visual", "novelty", "oscillator"}
        dmn_sources = {"activity", "memory", "curiosity", "thought", "insight"}

        top_source = self._events[0].source if self._events else ""

        # Determine tier based on top event source
        if top_source in tpn_sources:
            tier = "tpn"
            tier_cooldown = 15.0  # Quick reactions: 15s minimum
        else:
            tier = "dmn"
            tier_cooldown = 120.0  # Deep responses: 2 minute minimum

        # Override: very high salience (>0.9) always uses DMN
        if self._accumulator > 0.9:
            tier = "dmn"
            tier_cooldown = 120.0

        # Check tier-specific cooldown
        if (now - self._last_speak_time) < tier_cooldown:
            return None

        # === VOCALIZATION TRIGGERED ===
        prompt = self._build_vocalization_prompt()

        if not prompt:
            return None

        # Build trigger dict
        trigger = {
            "should_speak": True,
            "tier": tier,
            "topics": [{"topic": e.content, "source": e.source, "intensity": e.intensity}
                       for e in self._events[:3]],
            "prompt": prompt,
            "total_salience": self._accumulator,
        }

        # Reset after triggering
        self._last_speak_time = now
        self._accumulator = 0.2  # Keep some residual

        # Invoke callback if registered (pass the full trigger)
        if self.on_speak:
            try:
                self.on_speak(trigger)
            except Exception as e:
                log.error(f"[SALIENCE] Speak callback error: {e}")

        log.info(f"[SALIENCE] {self.entity} {tier.upper()} vocalization: {prompt[:80]}")

        return trigger

    def _build_vocalization_prompt(self) -> Optional[str]:
        """
        Build a prompt describing what to vocalize about.
        Returns None if no good prompt can be constructed.
        """
        if not self._events:
            return None

        # Get recent high-salience events
        now = time.time()
        recent = [e for e in self._events if now - e.timestamp < 60]

        if not recent:
            return None

        # Sort by intensity
        recent.sort(key=lambda e: e.intensity, reverse=True)

        # Pick top event, avoiding recent topics
        for event in recent[:5]:
            topic_key = event.content[:30].lower()
            if topic_key not in self._recent_topics:
                self._recent_topics.append(topic_key)
                if len(self._recent_topics) > self._max_recent:
                    self._recent_topics = self._recent_topics[-self._max_recent:]

                # Build prompt based on source type
                return self._format_prompt(event)

        return None

    def _format_prompt(self, event: SalienceEvent) -> str:
        """Format a vocalization prompt from an event."""
        source = event.source
        content = event.content

        # Natural prompt formats by source type
        formats = {
            "emotion": f"You're feeling {content}. Share this unprompted.",
            "memory": f"A memory just surfaced: {content}. Mention it naturally.",
            "curiosity": f"You're curious about {content}. Ask or wonder aloud.",
            "visual": f"You noticed {content}. Comment on it.",
            "touch": f"You're experiencing {content}. React to it.",
            "thought": f"You're thinking about {content}. Share the thought.",
            "tension": f"You're feeling tension about {content}. Express it.",
            "contradiction": f"You noticed something contradictory: {content}. Point it out.",
            "insight": f"You just realized: {content}. Share the insight excitedly.",
        }

        prompt = formats.get(source, f"You want to say something about: {content}")

        # Add randomness to delivery style
        styles = [
            " Keep it brief.",
            " Be genuine and natural.",
            " Let it slip out casually.",
            " Share it as if thinking aloud.",
        ]
        prompt += random.choice(styles)

        return prompt

    def inhibit(self, duration: float = 30.0):
        """
        Temporarily suppress spontaneous speech.

        Entity can choose to stay quiet for a period.
        """
        self._inhibited = True
        self._inhibit_until = time.time() + duration
        log.debug(f"[SALIENCE] {self.entity} inhibited for {duration}s")

    def release_inhibition(self):
        """Release any active inhibition."""
        self._inhibited = False
        self._inhibit_until = 0.0

    def set_threshold(self, threshold: float):
        """Adjust the vocalization threshold (0.0-1.0)."""
        self.threshold = max(0.1, min(1.0, threshold))

    def set_refractory_period(self, seconds: float):
        """Adjust the refractory period between vocalizations."""
        self.refractory_period = max(5.0, seconds)

    def set_weight(self, source: str, weight: float):
        """Adjust the weight for a specific source type."""
        self._weights[source] = max(0.0, min(1.0, weight))

    def get_status(self) -> Dict[str, Any]:
        """Get current accumulator status for debugging/display."""
        now = time.time()
        return {
            "entity": self.entity,
            "accumulator": self._accumulator,
            "threshold": self.threshold,
            "percent": self._accumulator / self.threshold * 100,
            "event_count": len(self._events),
            "in_refractory": now - self._last_speak_time < self.refractory_period,
            "refractory_remaining": max(0, self.refractory_period - (now - self._last_speak_time)),
            "inhibited": self._inhibited and now < self._inhibit_until,
            "recent_topics": self._recent_topics[-5:],
        }

    def clear(self):
        """Clear all accumulated salience and events."""
        self._accumulator = 0.0
        self._events.clear()


# === CONVENIENCE FUNCTIONS FOR COMMON SOURCES ===

def emotion_to_salience(emotion_name: str, intensity: float) -> tuple:
    """Convert emotion spike to salience event parameters."""
    high_salience_emotions = {
        "surprise", "shock", "alarm", "fear", "anger", "frustration",
        "delight", "awe", "wonder", "excitement", "grief", "despair"
    }

    if emotion_name.lower() in high_salience_emotions:
        intensity = min(1.0, intensity * 1.3)  # Boost high-salience emotions

    return ("emotion", intensity, f"strong {emotion_name} ({intensity:.0%})")


def memory_to_salience(memory_summary: str, relevance: float) -> tuple:
    """Convert memory retrieval to salience event parameters."""
    return ("memory", relevance, memory_summary[:100])


def curiosity_to_salience(question: str, urgency: float) -> tuple:
    """Convert curiosity to salience event parameters."""
    return ("curiosity", urgency, question[:100])
