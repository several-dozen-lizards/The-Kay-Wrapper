# engines/social_engine.py
from typing import Dict, Any, Optional

class SocialEngine:
    def __init__(self, social_rules: Optional[Dict[str, Any]] = None, emotion_engine: Optional[Any] = None):
        self.social_rules = social_rules or {}
        self.attachments = {}
        self.emotion_engine = emotion_engine  # NEW: For ULTRAMAP rule queries

    def detect_event(self, user_input: str, response: str) -> Optional[str]:
        lowered = (response.lower() + " " + user_input.lower())
        if any(x in lowered for x in ["thank", "good job", "that's right", "proud of you"]):
            return "praised"
        elif any(x in lowered for x in ["welcome", "glad", "happy for you", "same to you", "accepted"]):
            return "accepted"
        elif any(x in user_input.lower() for x in ["ignore", "not listening", "left me out", "no response"]):
            return "ignored"
        elif any(x in lowered for x in ["no ", "go away", "don't want you", "rejected", "humiliated"]):
            return "rejected"
        elif any(x in lowered for x in ["belong", "with you", "part of group", "in this together"]):
            return "belonging affirmed"
        elif any(x in lowered for x in ["laugh with", "inside joke", "us too", "camaraderie"]):
            return "reciprocated"
        elif any(x in lowered for x in ["humiliated", "ashamed", "everyone saw", "blush", "burned"]):
            return "humiliated"
        return None

    def update(self, agent_state, user_input: str, response: Optional[str] = None):
        """
        Update social state based on detected events and current emotions.

        NEW: Uses ULTRAMAP social rules from emotion_engine to apply
        emotion-specific social effects beyond basic event detection.
        """
        event = self.detect_event(user_input, response or "")
        if event:
            agent_state.social['events'].append(event)
            if event in ("praised", "accepted", "reciprocated", "belonging affirmed"):
                agent_state.social['needs']['social'] = agent_state.social['needs'].get('social', 0.5) + 0.1
            elif event in ("rejected", "ignored", "humiliated"):
                agent_state.social['needs']['social'] = agent_state.social['needs'].get('social', 0.5) - 0.1
            agent_state.social['needs']['social'] = max(0, min(1, agent_state.social['needs']['social']))
        else:
            agent_state.social['needs']['social'] = agent_state.social['needs'].get('social', 0.5) * 0.99

        # NEW: Apply emotion-specific social modulation from ULTRAMAP
        if self.emotion_engine and hasattr(agent_state, 'emotional_cocktail'):
            self._apply_emotional_social_effects(agent_state)

    def _apply_emotional_social_effects(self, agent_state):
        """
        Apply ULTRAMAP social effects based on current emotional state.

        Each emotion in ULTRAMAP has social rules that modify social needs
        based on the emotion's action tendencies and default system needs.
        """
        cocktail = agent_state.emotional_cocktail or {}

        for emotion_name, emotion_data in cocktail.items():
            intensity = emotion_data.get("intensity", 0.0)
            if intensity < 0.1:
                continue  # Skip weak emotions

            # Get ULTRAMAP social rules for this emotion
            social_rules = self.emotion_engine.get_social_rules(emotion_name)

            # Apply social_effect (already done in emotion_engine, but can layer here)
            social_effect = social_rules.get("social_effect", 0.0)

            # Check default_need to understand what this emotion seeks
            default_need = social_rules.get("default_need", "")

            # Adjust social needs based on emotion's system needs
            if "Connection" in default_need or "Belonging" in default_need:
                # Emotions seeking connection increase social need
                agent_state.social['needs']['social'] = min(1.0,
                    agent_state.social['needs'].get('social', 0.5) + (intensity * 0.05))
            elif "Stability" in default_need or "Safety" in default_need:
                # Emotions seeking stability may withdraw socially
                agent_state.social['needs']['social'] = max(0.0,
                    agent_state.social['needs'].get('social', 0.5) - (intensity * 0.03))

            # Clamp values
            agent_state.social['needs']['social'] = max(0, min(1, agent_state.social['needs']['social']))

    def prioritize_users(self, user_id: str, weight: float = 1.0):
        self.attachments[user_id] = self.attachments.get(user_id, 0.0) + weight
