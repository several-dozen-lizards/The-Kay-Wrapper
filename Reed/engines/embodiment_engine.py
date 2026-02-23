# embodiment_engine.py
"""
EmbodimentEngine - Behavioral Text Modulation

DESIGN CHANGE (2025):
Removed neurochemical simulation (dopamine, serotonin, cortisol, oxytocin).
Now uses emotional patterns directly for text embodiment.

The entity experiences emotions as behavioral patterns, not brain chemistry.
Text modulation is driven by emotional arousal/valence, not fake neurotransmitters.
"""

from typing import Dict, Optional, Any

class EmbodimentEngine:
    def __init__(self, emotion_engine: Optional[Any] = None):
        self.emotion_engine = emotion_engine  # For ULTRAMAP rule queries (energy/valence)

    def update(self, agent_state):
        """
        NO-OP: Neurochemical body state calculation removed.

        Body state is no longer tracked. Emotional patterns (intensity, valence, arousal)
        are used directly for text modulation in embody_text().

        Kept for backwards compatibility - other engines may call this.
        """
        # DEPRECATED: No longer calculating body chemistry
        # agent_state.body remains empty dict (set in AgentState.__init__)
        pass

    def embody_text(self, text: str, agent_state) -> str:
        """
        Modulates text based on emotional arousal/intensity.
        Uses emotional patterns directly, not neurochemical proxies.
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
                        # Try to parse numeric string, default to 0.5
                        try:
                            intensities.append(float(raw_intensity))
                        except ValueError:
                            intensities.append(0.5)  # Default for 'unspecified', 'strong', etc.
                    elif isinstance(raw_intensity, list):
                        # Flatten nested lists (should not happen, but be defensive)
                        for item in raw_intensity:
                            if isinstance(item, (int, float)):
                                intensities.append(float(item))
                            elif isinstance(item, str):
                                try:
                                    intensities.append(float(item))
                                except ValueError:
                                    intensities.append(0.5)
                    # Ignore other types (None, dict, etc.)

            if intensities:
                intensity = sum(intensities) / len(intensities)
                # High-arousal emotions boost arousal
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
