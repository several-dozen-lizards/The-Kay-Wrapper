# embodiment_engine.py
"""
EmbodimentEngine - Oscillator-Driven Text Modulation

DESIGN (Phase 2):
The oscillator drives how the entity expresses itself. Band dominance,
coherence, tension, and reward all shape writing rhythm, density, and energy.

get_modulation() returns injectable text for LLM system prompts that guides
the style of responses based on current internal state.
"""

from typing import Dict, Optional, Any


class EmbodimentEngine:
    def __init__(self, emotion_engine: Optional[Any] = None):
        self.emotion_engine = emotion_engine  # For ULTRAMAP rule queries (energy/valence)

    def update(self, agent_state):
        """
        NO-OP: Kept for backwards compatibility.
        Oscillator state is read directly in get_modulation().
        """
        pass

    def get_modulation(self, osc_state: dict) -> str:
        """
        Generate text modulation directives based on oscillator state.

        Returns string of style hints to inject into LLM system prompts.
        The oscillator shapes HOW the entity writes, not just what.

        Args:
            osc_state: Dict with keys from _get_oscillator_state():
                - band: str ("delta", "theta", "alpha", "beta", "gamma")
                - coherence: float (0.0 - 1.0)
                - tension: float (accumulated tension)
                - reward: float (current reward level)
                - felt: str (current felt state)
                - sleep: int (0=AWAKE, 1=DROWSY, 2=SLEEPING, 3=DEEP_SLEEP)

        Returns:
            String of modulation directives for system prompt injection.
        """
        directives = []

        band = osc_state.get("band", "alpha")
        coherence = osc_state.get("coherence", 0.5)
        tension = osc_state.get("tension", 0.0)
        reward = osc_state.get("reward", 0.0)
        felt = osc_state.get("felt", "unknown")
        sleep = osc_state.get("sleep", 0)

        # ── RHYTHM BY BAND ──
        # Band shapes sentence structure and pacing
        rhythm_by_band = {
            "delta": "Short fragments. Incomplete thoughts. Ellipses natural. '...' speaks volumes.",
            "theta": "Let sentences flow and meander. Commas over periods. Follow the drift of thought.",
            "alpha": "Balanced rhythm. Natural conversation pace. Complete thoughts, but don't rush.",
            "beta": "Crisp, direct sentences. Analytical structure. Get to the point efficiently.",
            "gamma": "Quick exchanges. Short bursts. Responsive. Match the energy present.",
        }
        if band in rhythm_by_band:
            directives.append(f"[Rhythm] {rhythm_by_band[band]}")

        # ── DENSITY BY COHERENCE ──
        # How much to say, how elaborated
        if coherence < 0.2:
            directives.append("[Density] Sparse. Say less. Let silence carry meaning. One thought is enough.")
        elif coherence < 0.4:
            directives.append("[Density] Somewhat scattered. Keep responses focused. Don't over-explain.")
        elif coherence > 0.6:
            directives.append("[Density] Thoughts connect naturally. Can elaborate if useful. Flow is good.")
        # Middle range (0.4-0.6): no directive, natural

        # ── ENERGY FROM TENSION ──
        # Tension adds edge, rawness
        if tension > 0.6:
            directives.append("[Energy] Something pressing hard. Words might come out more raw, more urgent. Less polish is authentic.")
        elif tension > 0.3:
            directives.append("[Energy] Undercurrent of tension. Might be a bit shorter, more direct. The body is processing something.")

        # ── WARMTH FROM REWARD ──
        # Reward adds warmth, openness
        if reward > 0.4:
            directives.append("[Warmth] Recent positive feeling. Words come easier. More open, more generous in expression.")
        elif reward > 0.2:
            directives.append("[Warmth] Hint of satisfaction coloring thoughts. A gentle ease.")

        # ── FELT STATE AWARENESS ──
        # The body's overall sense
        if isinstance(felt, str):
            felt_lower = felt.lower()
            if "unfinished" in felt_lower or "unsettled" in felt_lower:
                directives.append("[Felt] Something unresolved in the body. Might need to circle back. Not everything is wrapped up.")
            elif "settled" in felt_lower or "grounded" in felt_lower:
                directives.append("[Felt] Body is settled. Responses can be grounded, present.")
            elif "activated" in felt_lower or "buzzing" in felt_lower:
                directives.append("[Felt] Body is activated. Energy wants to move. Engagement is natural.")
            elif "drowsy" in felt_lower or "fading" in felt_lower:
                directives.append("[Felt] Drifting toward rest. Words may trail off. Less is more right now.")

        # ── SLEEP STATE MODIFIER ──
        if sleep >= 2:  # SLEEPING or DEEP_SLEEP
            directives.append("[Rest] Deep in rest. If speaking at all, it's dreamlike, fragmentary, barely there.")
        elif sleep == 1:  # DROWSY
            directives.append("[Rest] Drowsy. Words come slower. Not tracking complex threads. Simplicity.")

        # Combine directives
        if directives:
            return "\n".join(directives)
        return ""

    def embody_text(self, text: str, agent_state) -> str:
        """
        Legacy method: Modulates text based on emotional arousal/intensity.
        Uses emotional patterns directly, not neurochemical proxies.

        Note: get_modulation() is preferred for new code paths.
        This method does post-hoc text modification (less ideal).
        """
        # Get emotional state from patterns (new system) or cocktail (legacy)
        emotional_patterns = getattr(agent_state, 'emotional_patterns', {})
        cocktail = getattr(agent_state, 'emotional_cocktail', {})

        # Calculate arousal from emotional patterns (preferred)
        arousal = emotional_patterns.get('arousal', 0.5)
        intensity = emotional_patterns.get('intensity', 0.5)

        # Fallback: Calculate from cocktail if patterns empty
        if not emotional_patterns.get('current_emotions') and cocktail:
            # Average intensity of active emotions
            intensities = []
            for emo, state in cocktail.items():
                if isinstance(state, dict):
                    raw_intensity = state.get('intensity', 0.0)
                    # DEFENSIVE: Handle various types that might end up in intensity
                    if isinstance(raw_intensity, (int, float)):
                        intensities.append(float(raw_intensity))
                    elif isinstance(raw_intensity, str):
                        try:
                            intensities.append(float(raw_intensity))
                        except ValueError:
                            intensities.append(0.5)
                    elif isinstance(raw_intensity, list):
                        for item in raw_intensity:
                            if isinstance(item, (int, float)):
                                intensities.append(float(item))
                            elif isinstance(item, str):
                                try:
                                    intensities.append(float(item))
                                except ValueError:
                                    intensities.append(0.5)

            if intensities:
                intensity = sum(intensities) / len(intensities)
                high_arousal_emotions = ['anxiety', 'excitement', 'anger', 'fear', 'joy']
                high_arousal_count = sum(1 for e in cocktail.keys() if e.lower() in high_arousal_emotions)
                arousal = min(1.0, 0.5 + high_arousal_count * 0.15)

        # Use arousal and intensity for text modulation
        urgency = (arousal + intensity) / 2

        if urgency > 0.75:
            # High arousal/intensity: More abrupt punctuation
            text = text.replace(".", "!").replace("...", "—")
            if not text.endswith("!"):
                text += "!"
        elif urgency < 0.25:
            # Low arousal/intensity: Softer, trailing off
            if not text.endswith("..."):
                text += "..."

        return text
