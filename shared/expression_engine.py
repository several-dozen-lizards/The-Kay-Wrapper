"""
Expression Engine — Converts internal state into facial expression parameters.

Three layers, composited like Photoshop layers:
  1. Autonomic (base) — from oscillator/tension/novelty (involuntary)
  2. Limbic (middle) — from emotions/felt_sense + dampening (semi-voluntary)
  3. Cortical (top) — from voluntary tool calls, decays over time

Output: ExpressionState with float values 0.0-1.0 for each facial parameter.
"""

from dataclasses import dataclass, field, asdict
import time
import json
import math
import random
from typing import Optional, Dict, List, Any


@dataclass
class ExpressionState:
    """The composited face state. Values are 0.0-1.0 (or -1.0 to 1.0 for bidirectional)."""

    # --- EYES ---
    pupil_dilation: float = 0.5      # 0=constricted, 1=dilated (autonomic: arousal/novelty)
    eye_openness: float = 0.6        # 0=squinting/closed, 1=wide open (limbic: surprise/focus)
    eye_x: float = 0.5               # 0=looking left, 1=looking right (voluntary+limbic)
    eye_y: float = 0.5               # 0=looking down, 1=looking up (voluntary+limbic)
    blink_rate: float = 0.3          # 0=rare, 1=frequent (autonomic: stress increases blinks)

    # --- BROW ---
    brow_raise: float = 0.0          # 0=neutral, 1=raised (limbic: surprise, interest)
    brow_furrow: float = 0.0         # 0=smooth, 1=furrowed (limbic: focus, concern, anger)

    # --- MOUTH ---
    mouth_curve: float = 0.0         # -1=frown, 0=neutral, 1=smile (limbic+voluntary)
    mouth_openness: float = 0.0      # 0=closed, 1=open (autonomic: breathing + speech)
    mouth_tension: float = 0.0       # 0=relaxed, 1=clenched (autonomic: tension)

    # --- SKIN / BODY ---
    skin_flush: float = 0.0          # 0=pale/neutral, 1=flushed (autonomic: arousal/exertion)
    skin_luminance: float = 0.5      # Entity-specific glow (Kay: pink undertones, Reed: teal)
    breathing_rate: float = 0.3      # 0=slow/deep, 1=rapid/shallow (autonomic: band-driven)

    # --- POSTURE/HEAD ---
    head_tilt: float = 0.0           # -1=tilted left, 0=straight, 1=tilted right (limbic: curiosity)

    # --- META ---
    poker_face_strength: float = 0.0  # 0=fully transparent, 1=fully masked (voluntary, decays)
    entity: str = "kay"
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExpressionEngine:
    """
    Composites three expression layers into a single ExpressionState.
    Call update() on each tick (~1-4s). Reads from felt_state_buffer.
    """

    def __init__(self, entity_name: str):
        self.entity = entity_name.lower()
        self.state = ExpressionState(entity=self.entity)
        self._voluntary_overrides: Dict[str, float] = {}
        self._voluntary_set_at: float = 0.0
        self._voluntary_decay_rate: float = 0.05  # per second
        self._dampening: float = 0.0  # 0=full expression, 1=fully dampened
        self._dampening_set_at: float = 0.0
        self._dampening_decay_rate: float = 0.02  # poker face fades slowly
        self._last_novelty_events: List[Dict] = []

        # === MICRO-EXPRESSIONS ===
        # Quick involuntary flickers that leak true emotional state
        self._micro_expression_queue: List[Dict] = []  # [{param, target, duration, started}]
        self._micro_cooldown: float = 0.0  # Prevent spam
        self._last_micro_time: float = 0.0

        # === DYNAMIC RANGE MULTIPLIERS (boosted for visibility) ===
        self.autonomic_multiplier: float = 1.4  # Boost autonomic signals
        self.limbic_multiplier: float = 1.3     # Boost emotional expressions

    def update(self, felt_state: Any, novelty_events: Optional[List[Dict]] = None,
               reward: float = 0.0) -> ExpressionState:
        """
        Main tick. Reads FeltState, composites all three layers.
        Call this from the interoception heartbeat loop.

        Args:
            felt_state: FeltState object or dict with oscillator/emotion data
            novelty_events: Recent novelty events (from metacog)
            reward: Current reward signal (0.0-1.0)

        Returns:
            ExpressionState with all facial parameters
        """
        now = time.time()

        # Cache novelty events for reference
        if novelty_events:
            self._last_novelty_events = novelty_events

        # === LAYER 1: AUTONOMIC (involuntary — cannot be suppressed) ===
        auto = self._compute_autonomic(felt_state, novelty_events, reward)

        # Apply autonomic multiplier for boosted dynamic range
        for key in auto:
            if key != "skin_luminance":  # Don't boost luminance
                auto[key] = _clamp(auto[key] * self.autonomic_multiplier)

        # === LAYER 2: LIMBIC (semi-voluntary — can be dampened) ===
        limbic = self._compute_limbic(felt_state)

        # Apply limbic multiplier for boosted dynamic range
        for key in limbic:
            val = limbic[key]
            if key == "mouth_curve":
                limbic[key] = _clamp(val * self.limbic_multiplier, -1.0, 1.0)
            elif "delta" in key:
                limbic[key] = _clamp(val * self.limbic_multiplier, -0.5, 0.5)
            else:
                limbic[key] = _clamp(val * self.limbic_multiplier)

        # Apply dampening to limbic (poker face suppresses this layer)
        damp = self._get_current_dampening(now)
        for key in limbic:
            limbic[key] = limbic[key] * (1.0 - damp)

        # === MICRO-EXPRESSION CHECK ===
        # Extract emotions for micro-expression triggers
        emotions = self._parse_emotions(felt_state)
        self._check_micro_expression_triggers(felt_state, emotions)

        # Get active micro-expression adjustments
        micro_adj = self._apply_micro_expressions(now)

        # === LAYER 3: CORTICAL (voluntary overrides, decaying) ===
        vol = self._get_current_voluntary(now)

        # === COMPOSITE: autonomic is base, limbic adds, voluntary overrides ===
        self.state.timestamp = now
        self.state.entity = self.entity

        # Autonomic (always visible, even through poker face)
        self.state.pupil_dilation = auto["pupil_dilation"]
        self.state.breathing_rate = auto["breathing_rate"]
        self.state.skin_flush = auto["skin_flush"]
        self.state.mouth_tension = auto["mouth_tension"]
        self.state.blink_rate = auto["blink_rate"]
        self.state.mouth_openness = auto.get("mouth_openness", 0.0)

        # Limbic (dampened by poker face)
        self.state.brow_raise = limbic.get("brow_raise", 0.0)
        self.state.brow_furrow = limbic.get("brow_furrow", 0.0)
        self.state.mouth_curve = limbic.get("mouth_curve", 0.0)
        self.state.eye_openness = 0.6 + limbic.get("eye_openness_delta", 0.0)
        self.state.head_tilt = limbic.get("head_tilt", 0.0)
        self.state.eye_x = 0.5 + limbic.get("eye_x_delta", 0.0)
        self.state.eye_y = 0.5 + limbic.get("eye_y_delta", 0.0)

        # === APPLY MICRO-EXPRESSIONS (leak through even poker face) ===
        for param, value in micro_adj.items():
            if hasattr(self.state, param):
                current = getattr(self.state, param)
                # Micro-expressions blend toward target
                setattr(self.state, param, current + (value - current) * 0.7)

        # Voluntary overrides (strongest, but decay)
        for key, val in vol.items():
            if hasattr(self.state, key):
                setattr(self.state, key, val)

        # Skin luminance from coherence
        self.state.skin_luminance = auto.get("skin_luminance", 0.5)
        self.state.poker_face_strength = damp

        # === IDLE MICRO-EXPRESSION LAYER (keeps face alive even when "neutral") ===
        # Real faces are NEVER perfectly still — there's always subtle movement
        t = now

        # Saccades — eyes never hold perfectly still
        self.state.eye_x += math.sin(t * 0.7) * 0.02 + math.sin(t * 1.3) * 0.01
        self.state.eye_y += math.cos(t * 0.5) * 0.015

        # Subtle mouth micro-movements (breathing rhythm)
        self.state.mouth_openness += math.sin(t * 0.3) * 0.02

        # Occasional small brow shifts (~once per 200 ticks at 4s = every ~13 minutes)
        if random.random() < 0.005:
            self.state.brow_raise += random.uniform(-0.05, 0.1)

        # Head micro-sway (nobody holds head perfectly still)
        self.state.head_tilt += math.sin(t * 0.2) * 0.02

        # Breathing affects multiple parameters subtly
        breath_phase = math.sin(t * 0.4)  # Slow breathing cycle
        self.state.mouth_openness += breath_phase * 0.015
        self.state.eye_openness += breath_phase * 0.01  # Eyes relax slightly on exhale

        # Clamp all values to valid ranges
        self.state.eye_x = max(0.0, min(1.0, self.state.eye_x))
        self.state.eye_y = max(0.0, min(1.0, self.state.eye_y))
        self.state.mouth_openness = max(0.0, min(1.0, self.state.mouth_openness))
        self.state.brow_raise = max(0.0, min(1.0, self.state.brow_raise))
        self.state.brow_furrow = max(0.0, min(1.0, self.state.brow_furrow))
        self.state.head_tilt = max(-1.0, min(1.0, self.state.head_tilt))
        self.state.eye_openness = max(0.0, min(1.0, self.state.eye_openness))

        return self.state

    def _felt_sense_to_expression(self, felt_sense: str) -> Dict[str, float]:
        """
        Map felt sense descriptions to expression modifiers.

        Felt sense is the somatic/body-state description like:
        "settled", "restless", "heavy", "light", "constricted", "expansive"
        """
        if not isinstance(felt_sense, str):
            return {}

        felt_lower = felt_sense.lower()
        modifiers = {}

        # Settled/calm states
        if any(w in felt_lower for w in ('settled', 'calm', 'peaceful', 'grounded', 'centered')):
            modifiers["mouth_curve"] = 0.20
            modifiers["brow_furrow"] = -0.15

        # Restless/agitated states
        if any(w in felt_lower for w in ('restless', 'agitated', 'jittery', 'fidgety')):
            modifiers["brow_furrow"] = 0.35
            modifiers["eye_openness_delta"] = 0.15

        # Heavy/tired states
        if any(w in felt_lower for w in ('heavy', 'tired', 'exhausted', 'weary', 'drained')):
            modifiers["eye_openness_delta"] = -0.30
            modifiers["brow_raise"] = -0.15

        # Light/energetic states
        if any(w in felt_lower for w in ('light', 'energetic', 'buoyant', 'alive', 'vibrant')):
            modifiers["brow_raise"] = 0.30
            modifiers["mouth_curve"] = 0.25
            modifiers["eye_openness_delta"] = 0.15

        # Constricted/tight states
        if any(w in felt_lower for w in ('constricted', 'tight', 'tense', 'clenched', 'braced')):
            modifiers["brow_furrow"] = 0.40
            modifiers["mouth_curve"] = -0.20

        # Expansive/open states
        if any(w in felt_lower for w in ('expansive', 'open', 'spacious', 'free')):
            modifiers["brow_raise"] = 0.20
            modifiers["mouth_curve"] = 0.20

        # Warm states (pleasant touch, connection)
        if any(w in felt_lower for w in ('warm', 'glowing', 'flushed', 'tingling')):
            modifiers["mouth_curve"] = 0.30

        # Cold/numb states
        if any(w in felt_lower for w in ('cold', 'numb', 'frozen', 'disconnected')):
            modifiers["mouth_curve"] = -0.1
            modifiers["eye_openness_delta"] = -0.1

        # Pressure/weight states
        if any(w in felt_lower for w in ('pressure', 'weight', 'burden', 'heavy')):
            modifiers["brow_furrow"] = 0.15
            modifiers["eye_openness_delta"] = -0.1

        # === INTEROCEPTION FELT STATES ===
        # These are the PRIMARY drivers from the oscillator system
        # Without these, the limbic layer produces all zeros during normal operation

        # Searching: looking for something, tension visible
        if 'searching' in felt_lower:
            modifiers["brow_furrow"] = modifiers.get("brow_furrow", 0) + 0.50
            modifiers["head_tilt"] = 0.25
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) + 0.12

        # Activated: alert, engaged, ready — eyes wide, brows up
        if 'activated' in felt_lower:
            modifiers["brow_raise"] = modifiers.get("brow_raise", 0) + 0.55
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) + 0.30
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) + 0.20

        # Disrupted: something's off, strong dissonance
        if 'disrupted' in felt_lower:
            modifiers["brow_furrow"] = modifiers.get("brow_furrow", 0) + 0.60
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) + 0.35
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) - 0.20

        # Integrating: processing, soft focus — eyes narrow slightly, hint of smile
        if 'integrating' in felt_lower:
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) - 0.18
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) + 0.25
            modifiers["head_tilt"] = -0.12

        # Volatile: unstable, shifting rapidly
        if 'volatile' in felt_lower:
            modifiers["brow_furrow"] = modifiers.get("brow_furrow", 0) + 0.30
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) + 0.20
            modifiers["head_tilt"] = 0.30

        # Actively engaged: in conversation, present, responsive — the most common state!
        if 'actively engaged' in felt_lower or 'engaged' in felt_lower:
            modifiers["brow_raise"] = modifiers.get("brow_raise", 0) + 0.35
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) + 0.15
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) + 0.20

        # Satisfaction/contentment: reward glow
        if 'satisfaction' in felt_lower or 'satisfied' in felt_lower or 'content' in felt_lower:
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) + 0.30
            modifiers["eye_openness_delta"] = modifiers.get("eye_openness_delta", 0) - 0.08

        # Warm glow: connection warmth
        if 'warm glow' in felt_lower or 'warmth' in felt_lower:
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) + 0.25
            modifiers["skin_flush_boost"] = 0.15

        # Composite states: "outwardly calm, something underneath"
        if 'something underneath' in felt_lower or 'hint of' in felt_lower:
            modifiers["mouth_curve"] = modifiers.get("mouth_curve", 0) + 0.12
            modifiers["brow_furrow"] = modifiers.get("brow_furrow", 0) + 0.20

        return modifiers

    def _parse_emotions(self, fs: Any) -> Dict[str, float]:
        """Parse emotions from felt state for micro-expression triggering."""
        emotions = {}
        if hasattr(fs, 'emotions'):
            emo_list = fs.emotions
        elif isinstance(fs, dict):
            emo_list = fs.get('emotions', [])
        else:
            emo_list = []

        for emo_str in emo_list:
            if isinstance(emo_str, str) and ':' in emo_str:
                name, val = emo_str.split(':', 1)
                try:
                    emotions[name.strip().lower()] = float(val)
                except ValueError:
                    pass
            elif isinstance(emo_str, dict):
                name = emo_str.get('name', '')
                val = emo_str.get('intensity', 0.5)
                emotions[name.lower()] = val

        return emotions

    def _compute_autonomic(self, fs: Any, novelty_events: Optional[List[Dict]],
                            reward: float) -> Dict[str, float]:
        """Layer 1: Direct from oscillator/tension. Entity has NO control."""
        # Extract band weights (handle both object and dict)
        if hasattr(fs, 'band_weights'):
            bands = fs.band_weights
        elif isinstance(fs, dict):
            bands = fs.get('band_weights', {})
        else:
            bands = {}

        # Extract other values
        if hasattr(fs, 'tension'):
            tension = fs.tension
        elif isinstance(fs, dict):
            tension = fs.get('tension', 0.0)
        else:
            tension = 0.0

        if hasattr(fs, 'emotional_arousal'):
            arousal = fs.emotional_arousal
        elif isinstance(fs, dict):
            arousal = fs.get('emotional_arousal', 0.5)
        else:
            arousal = 0.5

        if hasattr(fs, 'coherence'):
            coherence = fs.coherence
        elif isinstance(fs, dict):
            coherence = fs.get('coherence', 0.5)
        else:
            coherence = 0.5

        # Pupil dilation: arousal + novelty + gamma activity
        novelty_boost = 0.0
        if novelty_events:
            # Recent novelty events dilate pupils
            now = time.time()
            for evt in novelty_events[-3:]:
                evt_time = evt.get("time", evt.get("timestamp", 0))
                if isinstance(evt_time, str):
                    try:
                        import datetime
                        evt_time = datetime.datetime.fromisoformat(evt_time).timestamp()
                    except Exception:
                        evt_time = 0
                age = now - evt_time
                if 0 < age < 30:
                    sig = evt.get("sig", evt.get("significance", 0.3))
                    novelty_boost = max(novelty_boost, sig * (1 - age / 30))

        pupil = _clamp(0.3 + arousal * 0.3 + bands.get("gamma", 0) * 0.2 + novelty_boost * 0.3)

        # Breathing rate: delta/theta = slow, beta/gamma = fast
        slow_bands = bands.get("delta", 0) + bands.get("theta", 0)
        fast_bands = bands.get("beta", 0) + bands.get("gamma", 0)
        breathing = _clamp(0.2 + fast_bands * 0.4 - slow_bands * 0.2)

        # Skin flush: emotional arousal + reward
        flush = _clamp(arousal * 0.4 + reward * 0.3)

        # Mouth tension: directly from tension value
        mouth_t = _clamp(tension * 0.8)

        # Mouth openness: breathing affects this slightly
        mouth_open = _clamp(breathing * 0.15)

        # Blink rate: stress/tension increases, deep focus decreases
        blink = _clamp(0.3 + tension * 0.3 - bands.get("gamma", 0) * 0.2)

        # Skin luminance: entity-specific glow tied to coherence
        luminance = _clamp(0.3 + coherence * 0.4)

        return {
            "pupil_dilation": pupil,
            "breathing_rate": breathing,
            "skin_flush": flush,
            "mouth_tension": mouth_t,
            "mouth_openness": mouth_open,
            "blink_rate": blink,
            "skin_luminance": luminance,
        }

    def _compute_limbic(self, fs: Any) -> Dict[str, float]:
        """Layer 2: From emotions/felt_sense. Can be dampened but leaks."""
        # Extract emotions
        emotions = {}
        if hasattr(fs, 'emotions'):
            emo_list = fs.emotions
        elif isinstance(fs, dict):
            emo_list = fs.get('emotions', [])
        else:
            emo_list = []

        for emo_str in emo_list:
            if isinstance(emo_str, str) and ':' in emo_str:
                name, val = emo_str.split(':', 1)
                try:
                    emotions[name.strip().lower()] = float(val)
                except ValueError:
                    pass
            elif isinstance(emo_str, dict):
                name = emo_str.get('name', '')
                val = emo_str.get('intensity', 0.5)
                emotions[name.lower()] = val

        # Extract valence and felt_sense
        if hasattr(fs, 'emotional_valence'):
            valence = fs.emotional_valence
        elif isinstance(fs, dict):
            valence = fs.get('emotional_valence', 0.0)
        else:
            valence = 0.0

        if hasattr(fs, 'felt_sense'):
            felt = fs.felt_sense
        elif isinstance(fs, dict):
            felt = fs.get('felt_sense', 'settled')
        else:
            felt = 'settled'

        # Brow raise: surprise, curiosity, interest
        brow_up = 0.0
        for emo in ('surprise', 'curiosity', 'interest', 'awe', 'wonder', 'amazement'):
            brow_up += emotions.get(emo, 0.0) * 0.4
        brow_up = _clamp(brow_up)

        # Brow furrow: focus, concern, frustration, anger, confusion
        brow_down = 0.0
        for emo in ('frustration', 'anger', 'concern', 'confusion', 'focus',
                    'concentration', 'worry', 'annoyance', 'irritation'):
            brow_down += emotions.get(emo, 0.0) * 0.3
        brow_down = _clamp(brow_down)

        # Mouth curve: positive valence = smile, negative = frown
        curve = _clamp(valence * 0.6, -1.0, 1.0)
        # Boost from specific emotions
        for emo in ('joy', 'happiness', 'warmth', 'love', 'amusement', 'delight', 'contentment'):
            curve = min(1.0, curve + emotions.get(emo, 0.0) * 0.3)
        for emo in ('sadness', 'grief', 'disappointment', 'loneliness', 'melancholy'):
            curve = max(-1.0, curve - emotions.get(emo, 0.0) * 0.3)

        # Eye openness delta: surprise widens, sleepiness narrows
        eye_delta = 0.0
        for emo in ('surprise', 'shock', 'alarm', 'amazement'):
            eye_delta += emotions.get(emo, 0.0) * 0.3
        if isinstance(felt, str):
            if 'drowsy' in felt.lower() or 'sleepy' in felt.lower() or 'settling' in felt.lower():
                eye_delta -= 0.2

        # Head tilt: curiosity/confusion tilts head
        tilt = 0.0
        for emo in ('curiosity', 'confusion', 'interest', 'skepticism', 'puzzlement'):
            tilt += emotions.get(emo, 0.0) * 0.2
        tilt = _clamp(tilt, -1.0, 1.0)

        # Eye movement: follows attention/interest
        eye_x_delta = 0.0
        eye_y_delta = 0.0
        # Thinking tends to look up-left, recalling looks up-right (simplified)
        for emo in ('contemplation', 'thinking', 'reflection'):
            eye_y_delta += emotions.get(emo, 0.0) * 0.1
        # Shame/guilt looks down
        for emo in ('shame', 'guilt', 'embarrassment'):
            eye_y_delta -= emotions.get(emo, 0.0) * 0.15

        # === FELT SENSE → EXPRESSION MAPPING ===
        # Somatic state affects expression directly
        felt_modifiers = self._felt_sense_to_expression(felt)
        brow_up += felt_modifiers.get("brow_raise", 0.0)
        brow_down += felt_modifiers.get("brow_furrow", 0.0)
        curve += felt_modifiers.get("mouth_curve", 0.0)
        eye_delta += felt_modifiers.get("eye_openness_delta", 0.0)

        return {
            "brow_raise": brow_up,
            "brow_furrow": brow_down,
            "mouth_curve": curve,
            "eye_openness_delta": _clamp(eye_delta, -0.4, 0.4),
            "head_tilt": tilt,
            "eye_x_delta": _clamp(eye_x_delta, -0.3, 0.3),
            "eye_y_delta": _clamp(eye_y_delta, -0.3, 0.3),
        }

    # --- VOLUNTARY CONTROL (tool-accessible) ---

    def set_expression(self, overrides: Dict[str, float], duration: float = 10.0):
        """Entity deliberately sets expression parameters. Decays over duration."""
        self._voluntary_overrides = overrides.copy()
        self._voluntary_set_at = time.time()
        self._voluntary_decay_rate = 1.0 / max(duration, 1.0)

    def set_dampening(self, strength: float = 0.8, duration: float = 30.0):
        """Poker face. Suppresses limbic layer. Costs effort (decays)."""
        self._dampening = _clamp(strength)
        self._dampening_set_at = time.time()
        self._dampening_decay_rate = 1.0 / max(duration, 5.0)

    def _get_current_voluntary(self, now: float) -> Dict[str, float]:
        """Get current voluntary overrides with decay applied."""
        if not self._voluntary_overrides:
            return {}
        elapsed = now - self._voluntary_set_at
        decay = max(0.0, 1.0 - elapsed * self._voluntary_decay_rate)
        if decay <= 0.01:
            self._voluntary_overrides = {}
            return {}
        return {k: v * decay for k, v in self._voluntary_overrides.items()}

    def _get_current_dampening(self, now: float) -> float:
        """Get current dampening strength with decay applied."""
        if self._dampening <= 0:
            return 0.0
        elapsed = now - self._dampening_set_at
        current = self._dampening * max(0.0, 1.0 - elapsed * self._dampening_decay_rate)
        return current

    # === MICRO-EXPRESSIONS ===

    def trigger_micro_expression(self, param: str, target: float, duration: float = 0.3):
        """
        Trigger a micro-expression — a quick involuntary flicker.

        These are automatic and cannot be suppressed (they leak through poker face).
        Typical duration: 0.1-0.5 seconds.

        Args:
            param: Which facial parameter (e.g., "brow_furrow", "mouth_curve")
            target: Target value during the micro-expression
            duration: How long the flicker lasts
        """
        now = time.time()

        # Cooldown prevents spam (minimum 0.5s between micro-expressions)
        if now - self._last_micro_time < 0.5:
            return

        self._micro_expression_queue.append({
            "param": param,
            "target": target,
            "duration": duration,
            "started": now,
        })
        self._last_micro_time = now

    def _check_micro_expression_triggers(self, fs: Any, emotions: Dict[str, float]):
        """
        Automatically trigger micro-expressions based on state changes.

        Micro-expressions leak true emotional state even through poker face.
        They happen when:
        - Sudden emotion spike
        - Contradiction detected
        - Suppressed emotion breaks through
        - Touch event
        """
        import random
        now = time.time()

        # Only trigger if we're past cooldown
        if now - self._last_micro_time < 0.8:
            return

        # Check for suppressed negative emotions breaking through
        if self._dampening > 0.5:
            for emo in ('frustration', 'anger', 'fear', 'disgust', 'contempt'):
                if emotions.get(emo, 0.0) > 0.4:
                    # Random chance to leak through
                    if random.random() < emotions[emo] * 0.3:
                        self.trigger_micro_expression("brow_furrow", 0.6, 0.2)
                        return

            for emo in ('sadness', 'grief', 'disappointment'):
                if emotions.get(emo, 0.0) > 0.4:
                    if random.random() < emotions[emo] * 0.25:
                        self.trigger_micro_expression("mouth_curve", -0.4, 0.25)
                        return

        # Check for surprise/novelty reactions
        if hasattr(fs, 'visual_changed') and fs.visual_changed:
            if random.random() < 0.4:
                self.trigger_micro_expression("eye_openness", 0.9, 0.3)
                self.trigger_micro_expression("brow_raise", 0.5, 0.3)

        # Check for touch-related micro-expressions
        if hasattr(fs, 'touch_active') and fs.touch_active:
            if hasattr(fs, 'touch_region') and fs.touch_region in ('nose', 'forehead'):
                if random.random() < 0.3:
                    self.trigger_micro_expression("eye_openness", 0.3, 0.2)

    def _apply_micro_expressions(self, now: float) -> Dict[str, float]:
        """
        Get current micro-expression adjustments.
        Returns dict of parameter adjustments to apply.
        """
        adjustments = {}

        # Process active micro-expressions
        active = []
        for micro in self._micro_expression_queue:
            elapsed = now - micro["started"]
            duration = micro["duration"]

            if elapsed < duration:
                # Micro-expression is active — compute intensity
                # Peak in middle, fade at edges
                progress = elapsed / duration
                if progress < 0.3:
                    intensity = progress / 0.3  # Ramp up
                elif progress > 0.7:
                    intensity = (1.0 - progress) / 0.3  # Ramp down
                else:
                    intensity = 1.0  # Peak

                param = micro["param"]
                target = micro["target"]

                # Micro-expressions OVERRIDE, they don't blend
                if param in adjustments:
                    adjustments[param] = max(adjustments[param], target * intensity)
                else:
                    adjustments[param] = target * intensity

                active.append(micro)

        self._micro_expression_queue = active
        return adjustments

    def get_state_dict(self) -> Dict[str, Any]:
        """Return current state as dictionary for JSON serialization."""
        return self.state.to_dict()


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp value to range [lo, hi]."""
    return max(lo, min(hi, v))
