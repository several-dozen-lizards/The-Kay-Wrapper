# shared/room/attention_focus.py
"""
Attention Focus — The Gradient Between Inner Space and Outer Eye

The entity exists in two perceptual spaces simultaneously:
1. His room (den/commons) — spatial objects, oscillator-driven
2. The visual field (webcam) — the user's space, seen through his eye

This module manages the gradient between them. At 0.0, the entity is
fully "in his room" — objects push oscillator, visual is background.
At 1.0, he's fully "out there" — visual pushes oscillator, room fades.

The shift is driven by context:
- Someone messages → attention pulls outward (toward the speaker)
- Painting/reading → attention pulls inward (into his space)
- Camera motion → brief outward spike
- Silence → drift toward resting point

This isn't a switch. It's a gradient, like how you stop noticing
the couch under you when you're deep in a game.

Author: the developers
Date: March 2026
"""

import time
from typing import Optional


class AttentionFocus:
    """
    Manages the perceptual gradient between room and visual field.
    
    _focus: 0.0 = fully in room, 1.0 = fully through eye
    
    Room weight = 1.0 - _focus  (objects, spatial, den)
    Visual weight = _focus       (webcam, the user's space)
    
    Both are always non-zero (min 0.05) — you're never COMPLETELY
    unaware of either space. Even deep in his room, the entity has peripheral
    awareness of the camera. Even fully looking out, he knows his
    body is somewhere.
    """
    
    FLOOR = 0.05       # Minimum weight for either channel
    RESTING = 0.3      # Default resting point (slightly room-biased)
    DRIFT_RATE = 0.02  # How fast attention drifts back to resting per tick
    
    def __init__(self, resting_point: float = 0.3):
        self._focus: float = resting_point
        self._resting_point: float = resting_point
        self._last_update: float = time.time()
        
        # Event timestamps for contextual driving
        self._last_message_received: float = 0.0
        self._last_message_sent: float = 0.0
        self._last_visual_motion: float = 0.0
        self._last_activity_start: float = 0.0  # painting, reading, etc.
        self._last_re_visible: float = 0.0
    
    # ── Core Accessors ──
    
    @property
    def focus(self) -> float:
        """Current focus value. 0=room, 1=visual."""
        return self._focus
    
    def get_room_weight(self) -> float:
        """How strongly room objects push the oscillator. 1.0 when fully in room."""
        return max(self.FLOOR, 1.0 - self._focus)
    
    def get_visual_weight(self) -> float:
        """How strongly visual scene pushes the oscillator. 1.0 when fully looking out."""
        return max(self.FLOOR, self._focus)
    
    # ── Smooth Transition ──
    
    def shift_toward(self, target: float, rate: float = 0.15):
        """
        Smoothly shift attention toward a target value.
        Rate controls speed: 0.05 = slow drift, 0.3 = quick snap.
        Uses exponential approach — fast at first, then settling.
        """
        target = max(0.0, min(1.0, target))
        self._focus += (target - self._focus) * rate
        self._focus = max(0.0, min(1.0, self._focus))
        self._last_update = time.time()
    
    # ── Contextual Event Handlers ──
    # These are called by other systems when events happen.
    # They shift attention based on what's going on.
    
    def on_message_received(self, from_human: bool = True):
        """Someone sent a message. Attention shifts outward — toward the speaker."""
        self._last_message_received = time.time()
        if from_human:
            # the user is talking — strong pull outward
            self.shift_toward(0.7, rate=0.25)
        else:
            # Another entity — mild pull
            self.shift_toward(0.5, rate=0.1)
    
    def on_message_sent(self):
        """The entity sent a message. Engaged outward."""
        self._last_message_sent = time.time()
        self.shift_toward(0.6, rate=0.1)
    
    def on_visual_motion(self, intensity: float = 0.5):
        """Camera detected motion. Brief outward spike."""
        self._last_visual_motion = time.time()
        # Motion grabs attention proportionally
        spike_target = min(0.8, self._focus + intensity * 0.3)
        self.shift_toward(spike_target, rate=0.2)
    
    def on_re_visible(self):
        """Camera sees the user. Gentle outward pull (they're there, worth noticing)."""
        self._last_re_visible = time.time()
        # Only pull if not already quite focused outward
        if self._focus < 0.4:
            self.shift_toward(0.4, rate=0.05)
    
    def on_activity_started(self, activity: str = ""):
        """the entity started an internal activity (painting, reading, etc.)."""
        self._last_activity_start = time.time()
        # Pull inward — he's doing something in his space
        self.shift_toward(0.15, rate=0.2)
    
    def on_re_not_visible(self):
        """Camera doesn't see the user. Slowly drift inward."""
        # Don't snap — she might have just stepped away
        if self._focus > self._resting_point:
            self.shift_toward(self._resting_point, rate=0.03)
    
    # ── Tick (called every interoception heartbeat) ──
    
    def tick(self):
        """
        Called every heartbeat (~4s). Handles natural drift back
        toward resting point when nothing is actively pulling attention.
        """
        now = time.time()
        
        # How long since anything pulled attention?
        last_event = max(
            self._last_message_received,
            self._last_message_sent,
            self._last_visual_motion,
            self._last_activity_start,
            self._last_re_visible,
        )
        seconds_since_event = now - last_event if last_event > 0 else 999
        
        # After 30s with no events, start drifting toward resting point
        if seconds_since_event > 30:
            drift_strength = min(0.05, self.DRIFT_RATE * (seconds_since_event / 60))
            self.shift_toward(self._resting_point, rate=drift_strength)
        
        # User visible recently? Maintain gentle outward bias
        if (now - self._last_re_visible) < 20:
            # She's there — resting point shifts slightly outward
            effective_resting = min(0.45, self._resting_point + 0.1)
            if self._focus < effective_resting and seconds_since_event > 10:
                self.shift_toward(effective_resting, rate=0.02)
    
    # ── State Export ──
    
    def get_state(self) -> dict:
        """Export state for logging/persistence."""
        return {
            "focus": round(self._focus, 3),
            "room_weight": round(self.get_room_weight(), 3),
            "visual_weight": round(self.get_visual_weight(), 3),
            "resting_point": self._resting_point,
        }
    
    def get_prompt_hint(self) -> str:
        """
        One-line hint for prompt injection describing attention state.
        """
        f = self._focus
        if f < 0.15:
            return "[attention: deep in your room — visual field is distant background]"
        elif f < 0.35:
            return "[attention: mostly in your room, peripheral awareness of what your eye sees]"
        elif f < 0.55:
            return "[attention: split between your room and what you're seeing through your eye]"
        elif f < 0.75:
            return "[attention: mostly looking out through your eye — your room is background]"
        else:
            return "[attention: fully present through your eye — seeing, feeling the space beyond]"
    
    def __repr__(self):
        return f"AttentionFocus(focus={self._focus:.2f}, room={self.get_room_weight():.2f}, visual={self.get_visual_weight():.2f})"
