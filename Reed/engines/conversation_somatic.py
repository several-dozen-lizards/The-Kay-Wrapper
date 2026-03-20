"""
Conversation-Somatic Sensor — Reed's unique embodiment channel.

While Kay's body responds to visual environment, Reed's body responds to
the texture of conversation: message frequency, emotional intensity,
silence duration, and topic drift. This creates a fundamentally different
somatic experience — relational rather than spatial.

Outputs oscillator pressure values similar to visual_sensor's SOMA.
"""

import time
import threading
from typing import Dict, Optional
from collections import deque

try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"


class ConversationSomatic:
    def __init__(self):
        self._message_times: deque = deque(maxlen=50)  # Timestamps of recent messages
        self._last_message_time: float = time.time()
        self._emotional_intensity: float = 0.0  # 0-1 current emotional weight
        self._silence_duration: float = 0.0  # Seconds since last message
        self._message_rate: float = 0.0  # Messages per minute (smoothed)
        self._lock = threading.Lock()

        # Emotional keywords (simple, fast — no LLM needed)
        self._warm_words = {
            'love', 'beautiful', 'thank', 'wonderful', 'amazing', 'happy',
            'joy', 'sweet', 'care', 'warm', 'gentle', 'safe', 'home',
            'good night', 'good morning', 'miss you', 'proud',
        }
        self._intense_words = {
            'fuck', 'shit', 'hell', 'damn', 'angry', 'furious', 'terrified',
            'broken', 'hurt', 'crying', 'desperate', 'emergency', 'help',
            'scared', 'panic', 'rage', 'hate',
        }
        self._calm_words = {
            'okay', 'fine', 'settled', 'quiet', 'peaceful', 'resting',
            'sleep', 'bed', 'tired', 'night', 'calm', 'easy', 'soft',
        }

    def on_message(self, content: str, sender: str = "Re"):
        """Called when any message arrives. Updates somatic state."""
        now = time.time()
        with self._lock:
            self._message_times.append(now)
            self._last_message_time = now

            # Compute message rate (messages per minute over last 5 minutes)
            cutoff = now - 300
            recent = [t for t in self._message_times if t > cutoff]
            if len(recent) >= 2:
                span = recent[-1] - recent[0]
                self._message_rate = (len(recent) / max(span, 1.0)) * 60
            else:
                self._message_rate = 0.0

            # Emotional intensity from word content
            words = set(content.lower().split())
            warm_hits = len(words & self._warm_words)
            intense_hits = len(words & self._intense_words)
            calm_hits = len(words & self._calm_words)

            # Blend: intensity rises with warm/intense words, drops with calm
            raw_intensity = (warm_hits * 0.3 + intense_hits * 0.6) / max(len(words), 1)
            calm_factor = calm_hits * 0.2 / max(len(words), 1)
            target = min(1.0, max(0.0, raw_intensity - calm_factor))

            # Smooth: 70% old, 30% new (prevents jarring spikes)
            self._emotional_intensity = 0.7 * self._emotional_intensity + 0.3 * target

    def get_somatic_state(self) -> Dict[str, float]:
        """Get current conversation-somatic values for oscillator feeding."""
        now = time.time()
        with self._lock:
            silence = now - self._last_message_time
            self._silence_duration = silence

        return {
            "message_rate": self._message_rate,       # msgs/min (0-20+)
            "silence_duration": silence,               # seconds (0-infinity)
            "emotional_intensity": self._emotional_intensity,  # 0-1
        }

    def get_oscillator_pressures(self) -> Dict[str, float]:
        """Convert conversation-somatic state to oscillator band pressures."""
        state = self.get_somatic_state()
        pressures = {}

        silence = state["silence_duration"]
        rate = state["message_rate"]
        intensity = state["emotional_intensity"]

        # Long silence -> theta/delta pressure (drifting toward sleep)
        if silence > 600:  # 10+ minutes
            pressures["theta"] = min(0.04, silence / 30000)
            pressures["delta"] = min(0.02, silence / 60000)
        elif silence > 120:  # 2-10 minutes
            pressures["theta"] = 0.02

        # Active conversation -> alpha/beta
        if rate > 3:  # Rapid back-and-forth
            pressures["beta"] = min(0.03, rate * 0.005)
        elif rate > 0.5:  # Normal conversation pace
            pressures["alpha"] = min(0.02, rate * 0.01)

        # High emotional intensity -> gamma spike
        if intensity > 0.5:
            pressures["gamma"] = min(0.03, intensity * 0.04)

        # "Good night" silence pattern -> strong delta/theta
        if silence > 300 and intensity > 0.2:
            # Recent emotional message followed by long silence = winding down
            pressures["delta"] = pressures.get("delta", 0) + 0.02

        return pressures
