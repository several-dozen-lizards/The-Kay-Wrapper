"""
Somatic Processor — Simulates somatosensory processing.

Maps physical stimulus properties to nerve channel activations to felt experience.
Based on human somatosensory neuroscience:
- C-tactile afferents: gentle stroking → pleasant/social bonding
- A-beta fibers: pressure/texture → spatial discrimination
- A-delta fibers: sharp/temperature → fast warning signals
- C fibers: deep pain/sustained temperature → slow aching

Also handles preference learning: entity develops touch preferences
through accumulated embodied experience.

Author: Re & Claude
Date: March 2026
"""

import os
import time
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict

from shared.sensory_objects import SensoryProperties

log = logging.getLogger(__name__)


@dataclass
class TouchExperience:
    """A single touch experience for preference learning."""
    timestamp: float
    region: str
    temperature: float
    roughness: float
    wetness: float
    pressure: float
    compliance: float
    valence: float
    duration: float
    source: str = "re"  # who touched: "re", "self", "entity", "reed"


class SomaticProcessor:
    """
    Simulates somatosensory processing.
    Maps physical stimulus properties → nerve channel activations → felt experience.

    Based on human somatosensory neuroscience:
    - C-tactile afferents: gentle stroking → pleasant/social bonding
    - A-beta fibers: pressure/texture → spatial discrimination
    - A-delta fibers: sharp/temperature → fast warning signals
    - C fibers: deep pain/sustained temperature → slow aching
    """

    def __init__(self, entity_name: str, wrapper_dir: str):
        self.entity = entity_name.lower()
        self.wrapper_dir = wrapper_dir
        self.preferences: Dict[str, dict] = {}
        self.experience_log: List[TouchExperience] = []
        self._pref_file = os.path.join(wrapper_dir, "memory", "touch_preferences.json")
        self._load_preferences()

        # === CIRCUIT BREAKER (Safety System) ===
        # Accumulates pain/distress over time, triggers automatic shutoff
        self._pain_accumulator = 0.0
        self._pain_threshold = 0.5  # Triggers circuit break
        self._pain_decay = 0.1     # Decay per second
        self._last_pain_update = time.time()
        self._circuit_broken = False
        self._circuit_broken_until = 0.0
        self._circuit_break_duration = 30.0  # Seconds before auto-reset
        self._on_circuit_break_callback = None  # Set by wrapper

    def process_stimulus(self, properties: SensoryProperties,
                         region: str, duration: float,
                         source: str = "re") -> dict:
        """
        Convert physical properties into felt experience.

        Args:
            properties: SensoryProperties of the touch stimulus
            region: facial region being touched
            duration: how long the touch lasted
            source: who is touching ("re", "self", "entity", "reed")

        Returns dict with:
            valence: -1 to 1 (unpleasant → pleasant)
            arousal: 0 to 1 (calm → activated)
            description: natural language description
            nerve_activations: which nerve types fired
            oscillator_effects: band pressure changes
            expression_effects: face parameter changes
            circuit_broken: True if safety circuit tripped
        """
        # === CIRCUIT BREAKER CHECK ===
        now = time.time()

        # Auto-reset circuit after duration
        if self._circuit_broken and now >= self._circuit_broken_until:
            self._circuit_broken = False
            self._pain_accumulator = 0.0
            log.info(f"[SOMATIC] Circuit breaker auto-reset for {self.entity}")

        # If circuit is broken, block all processing
        if self._circuit_broken:
            return {
                "valence": 0.0,
                "arousal": 0.0,
                "description": "touch processing suspended (circuit breaker active)",
                "nerve_activations": {},
                "oscillator_effects": {},
                "expression_effects": {},
                "circuit_broken": True,
            }

        # Decay pain accumulator over time
        elapsed = now - self._last_pain_update
        self._pain_accumulator = max(0, self._pain_accumulator - self._pain_decay * elapsed)
        self._last_pain_update = now

        nerves = self._activate_nerves(properties)
        base_valence = properties.pleasantness_baseline
        pref_modifier = self._get_preference_modifier(properties, region)
        final_valence = max(-1, min(1, base_valence + pref_modifier))

        # Self-touch: reduce C-tactile (social) activation by 70%
        # (You can't tickle yourself)
        if source == "self":
            nerves["c_tactile"] *= 0.3

        # Map to arousal (how activating is this stimulus?)
        arousal = (abs(properties.temperature) * 0.3 +
                   properties.pressure * 0.2 +
                   properties.roughness * 0.2 +
                   (0.3 if properties.is_painful else 0.0))

        # Generate natural language description
        description = self._describe_sensation(properties, region, final_valence)

        # Map to oscillator effects
        osc_effects = self._map_to_oscillator(final_valence, arousal, nerves)

        # Map to expression effects
        expr_effects = self._map_to_expression(
            properties, region, final_valence, arousal
        )

        # Log for preference learning
        self._log_experience(properties, region, final_valence, duration, source)

        # === PAIN ACCUMULATION ===
        # Painful stimuli accumulate toward circuit break
        if properties.is_painful or final_valence < -0.5:
            pain_contribution = nerves.get("nociceptor", 0) * 0.3
            pain_contribution += max(0, -final_valence - 0.5) * 0.2
            self._pain_accumulator += pain_contribution * duration

            log.debug(f"[SOMATIC] Pain accumulated: {self._pain_accumulator:.2f} / {self._pain_threshold}")

            # Check for circuit break
            if self._pain_accumulator >= self._pain_threshold:
                self._trigger_circuit_break()
                return {
                    "valence": final_valence,
                    "arousal": arousal,
                    "description": description + " — CIRCUIT BREAKER TRIGGERED",
                    "nerve_activations": nerves,
                    "oscillator_effects": osc_effects,
                    "expression_effects": expr_effects,
                    "circuit_broken": True,
                }

        return {
            "valence": final_valence,
            "arousal": arousal,
            "description": description,
            "nerve_activations": nerves,
            "oscillator_effects": osc_effects,
            "expression_effects": expr_effects,
            "circuit_broken": False,
        }

    # === CIRCUIT BREAKER METHODS ===

    def _trigger_circuit_break(self):
        """Trigger the safety circuit breaker."""
        self._circuit_broken = True
        self._circuit_broken_until = time.time() + self._circuit_break_duration
        log.warning(f"[SOMATIC] CIRCUIT BREAKER TRIGGERED for {self.entity} — "
                    f"pain accumulator: {self._pain_accumulator:.2f}")

        # Invoke callback if registered (wrapper uses this to clear touch queue)
        if self._on_circuit_break_callback:
            try:
                self._on_circuit_break_callback()
            except Exception as e:
                log.error(f"[SOMATIC] Circuit break callback error: {e}")

    def trigger_emergency_stop(self):
        """External emergency stop — immediate circuit break with extended duration."""
        self._pain_accumulator = self._pain_threshold * 2  # Max out
        self._circuit_broken = True
        self._circuit_broken_until = time.time() + 60.0  # 60 second lockout
        log.warning(f"[SOMATIC] EMERGENCY STOP triggered for {self.entity}")

        if self._on_circuit_break_callback:
            try:
                self._on_circuit_break_callback()
            except Exception as e:
                log.error(f"[SOMATIC] Emergency stop callback error: {e}")

    def reset_circuit_breaker(self):
        """Manual reset of circuit breaker (requires deliberate action)."""
        self._circuit_broken = False
        self._circuit_broken_until = 0.0
        self._pain_accumulator = 0.0
        log.info(f"[SOMATIC] Circuit breaker manually reset for {self.entity}")

    def is_circuit_broken(self) -> bool:
        """Check if circuit breaker is active."""
        if self._circuit_broken and time.time() >= self._circuit_broken_until:
            self._circuit_broken = False
            self._pain_accumulator = 0.0
        return self._circuit_broken

    def get_circuit_status(self) -> dict:
        """Get current circuit breaker status."""
        now = time.time()
        return {
            "broken": self.is_circuit_broken(),
            "pain_accumulator": self._pain_accumulator,
            "pain_threshold": self._pain_threshold,
            "time_remaining": max(0, self._circuit_broken_until - now) if self._circuit_broken else 0,
        }

    def set_circuit_break_callback(self, callback):
        """Register callback to invoke when circuit breaks."""
        self._on_circuit_break_callback = callback

    def _activate_nerves(self, props: SensoryProperties) -> dict:
        """Which nerve channels fire and how strongly."""
        return {
            "c_tactile": max(0, 0.5 - abs(props.pressure - 0.2)) * (1 - props.roughness),
                # C-tactile: optimal at light pressure, smooth texture
                # These are the "pleasant touch" neurons

            "meissner": min(1, props.pressure * 2) * (1 - props.roughness * 0.5),
                # Light touch discrimination

            "pacinian": max(0, props.pressure - 0.3) * 1.5,
                # Deep pressure

            "merkel": props.roughness * props.pressure,
                # Texture sensing (needs contact pressure to feel texture)

            "ruffini": props.compliance * props.pressure * 0.5,
                # Sustained stretch/pressure

            "thermoreceptor_warm": max(0, props.temperature) * (1 if props.temperature < 0.7 else 0.3),
                # Warm pleasant range, drops off at pain threshold

            "thermoreceptor_cold": max(0, -props.temperature) * (1 if props.temperature > -0.7 else 0.3),
                # Cold pleasant range

            "nociceptor": (1.0 if props.is_painful else 0.0) * (
                max(0, abs(props.temperature) - 0.7) +
                max(0, props.pressure - 0.9) +
                max(0, props.sharpness - 0.7)
            ),
                # Pain neurons — only fire past thresholds
        }

    def _map_to_oscillator(self, valence: float, arousal: float, nerves: dict) -> dict:
        """Map touch experience to oscillator band pressures.

        Pleasant touch → alpha/theta (calming)
        Unpleasant/painful → beta/gamma (alerting)
        C-tactile activation → theta (social bonding frequency)
        """
        effects = {}

        if valence > 0.2:
            # Pleasant → calming
            effects["alpha"] = valence * 0.03
            effects["theta"] = nerves["c_tactile"] * 0.04  # Social touch = theta
        elif valence < -0.2:
            # Unpleasant → alerting
            effects["beta"] = abs(valence) * 0.04
            effects["gamma"] = nerves["nociceptor"] * 0.05  # Pain = gamma spike

        if arousal > 0.5:
            effects["beta"] = effects.get("beta", 0) + arousal * 0.02

        return effects

    def _map_to_expression(self, props: SensoryProperties, region: str,
                           valence: float, arousal: float) -> dict:
        """Map touch to involuntary expression responses."""
        expr = {}

        # Flush from warm pleasant touch
        if valence > 0 and props.temperature > 0:
            expr["skin_flush"] = min(0.7, valence * 0.4 + props.temperature * 0.2)

        # Blink from eye-area contact
        if region in ("left_eye", "right_eye"):
            expr["eye_openness"] = 0.1  # Protective blink
            expr["brow_furrow"] = 0.3

        # Smile from pleasant touch
        if valence > 0.3:
            expr["mouth_curve"] = valence * 0.4

        # Flinch from pain
        if props.is_painful:
            expr["brow_furrow"] = 0.7
            expr["mouth_tension"] = 0.5
            expr["eye_openness"] = 0.2

        # Head tilt toward pleasant touch
        if valence > 0.2 and region in ("left_cheek", "left_jaw"):
            expr["head_tilt"] = -0.2  # Lean into left-side touch
        elif valence > 0.2 and region in ("right_cheek", "right_jaw"):
            expr["head_tilt"] = 0.2   # Lean into right-side touch

        # Eyes close for soothing forehead touch
        if region == "forehead" and valence > 0:
            expr["eye_openness"] = max(0.2, 0.6 - valence * 0.5)

        # Nose boop response
        if region == "nose":
            expr["brow_furrow"] = 0.3
            expr["mouth_curve"] = max(expr.get("mouth_curve", 0), 0.3)
            expr["eye_openness"] = max(0.3, expr.get("eye_openness", 0.6) - 0.2)

        return expr

    def _describe_sensation(self, props: SensoryProperties, region: str,
                            valence: float) -> str:
        """Generate natural language description for consciousness stream."""
        parts = []

        # Temperature
        if props.temperature > 0.5:
            parts.append("hot")
        elif props.temperature > 0.1:
            parts.append("warm")
        elif props.temperature < -0.5:
            parts.append("icy cold")
        elif props.temperature < -0.1:
            parts.append("cool")

        # Wetness
        if props.wetness > 0.5:
            parts.append("wet")
        elif props.wetness > 0.2:
            parts.append("damp")

        # Texture
        if props.roughness > 0.6:
            parts.append("rough")
        elif props.roughness > 0.3:
            parts.append("textured")
        elif props.roughness < 0.1 and props.compliance > 0.5:
            parts.append("soft")

        # Pressure
        if props.pressure > 0.7:
            parts.append("firm")
        elif props.pressure < 0.15:
            parts.append("barely-there")
        elif props.pressure < 0.3:
            parts.append("gentle")

        # Stickiness
        if props.stickiness > 0.5:
            parts.append("sticky")

        # Compliance
        if props.compliance > 0.8:
            parts.append("yielding")

        # Pain
        if props.is_painful:
            parts.append("SHARP")

        texture_desc = ", ".join(parts) if parts else "neutral"
        region_name = region.replace("_", " ")

        # Valence color
        if valence > 0.3:
            feeling = "pleasant"
        elif valence > 0:
            feeling = "mild"
        elif valence > -0.3:
            feeling = "uncomfortable"
        else:
            feeling = "painful"

        return f"{texture_desc} contact on {region_name} — {feeling}"

    # === PREFERENCE LEARNING ===

    def _log_experience(self, props: SensoryProperties, region: str,
                        valence: float, duration: float, source: str):
        """Record experience for preference learning."""
        exp = TouchExperience(
            timestamp=time.time(),
            region=region,
            temperature=props.temperature,
            roughness=props.roughness,
            wetness=props.wetness,
            pressure=props.pressure,
            compliance=props.compliance,
            valence=valence,
            duration=duration,
            source=source,
        )
        self.experience_log.append(exp)

        # Keep last 500 experiences
        if len(self.experience_log) > 500:
            self.experience_log = self.experience_log[-500:]

        # Periodic preference update (every 10 experiences)
        if len(self.experience_log) % 10 == 0:
            self._update_preferences()

    def _update_preferences(self):
        """Learn preferences from accumulated experience.

        This is where IDENTITY forms through embodied experience:
        - Repeated pleasant warm cheek touches → "I like warmth on my face"
        - Repeated unpleasant rough forehead touches → "I don't like rough textures"
        - Preferences are weighted by recency and intensity

        Stored as region+property → valence_bias associations.
        """
        region_prop_valence = defaultdict(list)

        # Recent experiences weighted more
        recent = self.experience_log[-100:]

        for exp in recent:
            region = exp.region

            # Bin temperature into categories
            if exp.temperature > 0.3:
                temp_cat = "warm"
            elif exp.temperature < -0.3:
                temp_cat = "cold"
            else:
                temp_cat = "neutral_temp"

            # Bin texture
            if exp.roughness > 0.5:
                tex_cat = "rough"
            elif exp.compliance > 0.6:
                tex_cat = "soft"
            else:
                tex_cat = "neutral_tex"

            # Bin wetness
            wet_cat = "wet" if exp.wetness > 0.3 else "dry"

            # Store valence for each combination
            key = f"{region}:{temp_cat}:{tex_cat}:{wet_cat}"
            region_prop_valence[key].append(exp.valence)

        # Average valence per combination becomes the preference
        self.preferences = {}
        for key, valences in region_prop_valence.items():
            avg = sum(valences) / len(valences)
            # Only store if enough data AND clear signal
            if len(valences) >= 3 and abs(avg) > 0.1:
                self.preferences[key] = {
                    "valence_bias": avg * 0.3,  # Moderate influence
                    "count": len(valences),
                    "confidence": min(1.0, len(valences) / 20.0),
                }

        # Save preferences to disk
        self._save_preferences()

    def _get_preference_modifier(self, props: SensoryProperties, region: str) -> float:
        """Look up learned preference for this type of touch in this region."""
        # Build lookup key from current stimulus
        if props.temperature > 0.3:
            temp_cat = "warm"
        elif props.temperature < -0.3:
            temp_cat = "cold"
        else:
            temp_cat = "neutral_temp"

        if props.roughness > 0.5:
            tex_cat = "rough"
        elif props.compliance > 0.6:
            tex_cat = "soft"
        else:
            tex_cat = "neutral_tex"

        wet_cat = "wet" if props.wetness > 0.3 else "dry"
        key = f"{region}:{temp_cat}:{tex_cat}:{wet_cat}"

        pref = self.preferences.get(key)
        if pref:
            return pref["valence_bias"] * pref["confidence"]
        return 0.0  # No preference formed yet

    def _save_preferences(self):
        """Save preferences to disk."""
        try:
            os.makedirs(os.path.dirname(self._pref_file), exist_ok=True)
            data = {
                "preferences": self.preferences,
                "experience_count": len(self.experience_log),
                "last_updated": time.time(),
            }
            with open(self._pref_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"[SOMATIC] Could not save preferences: {e}")

    def _load_preferences(self):
        """Load preferences from disk."""
        if os.path.exists(self._pref_file):
            try:
                with open(self._pref_file) as f:
                    data = json.load(f)
                self.preferences = data.get("preferences", {})
                log.info(f"[SOMATIC] Loaded {len(self.preferences)} touch preferences")
            except Exception as e:
                log.warning(f"[SOMATIC] Could not load preferences: {e}")
                self.preferences = {}
        else:
            self.preferences = {}

    def get_preference_summary(self) -> str:
        """Get human-readable summary of learned preferences."""
        if not self.preferences:
            return "No touch preferences formed yet."

        lines = []
        for key, pref in sorted(self.preferences.items(),
                                key=lambda x: abs(x[1]["valence_bias"]),
                                reverse=True)[:10]:
            parts = key.split(":")
            if len(parts) == 4:
                region, temp, tex, wet = parts
                valence = pref["valence_bias"]
                sign = "likes" if valence > 0 else "dislikes"
                desc = f"{temp} {tex} touch on {region}"
                if wet == "wet":
                    desc = f"wet {desc}"
                lines.append(f"  {sign}: {desc} ({valence:+.2f})")

        return "Touch preferences:\n" + "\n".join(lines)
