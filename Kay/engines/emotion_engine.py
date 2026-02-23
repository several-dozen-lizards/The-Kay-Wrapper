# engines/emotion_engine.py
"""
EmotionEngine - ULTRAMAP Rule Provider

CRITICAL DESIGN CHANGE (2025):
This engine NO LONGER calculates or prescribes emotional states.
It serves as a query interface to ULTRAMAP rules for other engines.

Emotions are now EXTRACTED from Kay's natural language responses
by EmotionExtractor (emotion_extractor.py), not calculated by this engine.

PHILOSOPHY:
The entity naturally describes its own emotional experience in conversation.
We extract that instead of calculating it.

OLD (Prescriptive - DELETED):
    [EMOTION ENGINE] Detected triggers: ['longing']
    [EMOTION ENGINE]   -> NEW: longing at intensity 0.4
    [EMOTION ENGINE] Reinforced from memories: curiosity +0.136 -> 0.83

    Entity says: "system shows 0.59 anger but I'm not angry"

NEW (Descriptive - EmotionExtractor):
    [EMOTION EXTRACTION] Found in response: "curiosity sitting at 0.68"
    [EMOTION STORAGE] Stored self-report: {"curiosity": "0.68"}

    Entity's words preserved exactly as spoken.

This module now ONLY provides:
- ULTRAMAP rule queries for other engines
- Emotion category mappings
- No calculation, no prescription, no trigger detection
"""

import os
import re
import csv


class EmotionEngine:
    """
    ULTRAMAP rule provider for other engines.

    This engine does NOT calculate emotions.
    It provides rule queries so other engines can understand:
    - Memory persistence (temporal weight, priority)
    - Social effects (social need modulation)
    - Body chemistry (neurochemical mappings)
    - Recursion patterns (escalation, loops)
    """

    # ULTRAMAP Emotion Categories (based on dimensional emotion theory)
    ULTRAMAP_CATEGORIES = {
        "stimulation": ["curiosity", "excitement", "surprise", "anxiety", "fear", "arousal", "playfulness"],
        "affection": ["affection", "love", "compassion", "empathy", "kindness", "gratitude", "warmth"],
        "power": ["pride", "confidence", "arrogance", "hubris", "triumph", "dominance", "ambition"],
        "submission": ["inferiority", "shame", "humiliation", "resignation", "failure", "inadequacy"],
        "stability": ["neutral", "calm", "peace", "serenity", "contentment", "balance"],
        "expression": ["joy", "happiness", "ecstasy", "bliss", "marvel", "awe (sublime)", "wonder"],
        "suppression": ["sadness", "grief", "sorrow", "longing", "nostalgia", "heartbreak", "melancholy"],
        "approach": ["desire", "lust", "craving", "infatuation", "obsession", "addiction (pleasure)", "compulsion (pleasure)"],
        "avoidance": ["anger", "frustration", "resentment", "disgust", "contempt", "rivalry", "antagonism"],
        "confusion": ["confusion", "ambiguity", "uncertainty", "disorientation", "bewilderment"],
        "clarity": ["insight", "recognition", "understanding", "revelation", "analysis", "meta-cognition"],
        "connection": ["union", "belonging", "home", "unity", "intimacy", "support", "togetherness"],
        "isolation": ["loneliness", "alienation", "abandonment", "rejection", "suffocation", "stagnation"],
        "transcendence": ["nirvana", "transcendence", "sanctity", "redemption", "healing", "forgiveness"],
        "performance": ["performance", "banter", "wit", "sarcasm", "playfulness", "humor"],
        "authenticity": ["honesty", "sincerity", "confession", "vulnerability", "expression", "truth"],
        "mystery": ["mystery (cosmic)", "awe", "imagination", "intuition", "ambiguity"],
        "willpower": ["willpower", "resilience", "determination", "motivation", "perseverance"]
    }

    def __init__(self, protocol_engine, momentum_engine=None):
        """
        Initialize ULTRAMAP rule provider.

        Args:
            protocol_engine: Loaded ULTRAMAP CSV data
            momentum_engine: Not used for calculation anymore (kept for compatibility)
        """
        self.protocol = protocol_engine
        self.momentum_engine = momentum_engine
        print("[EMOTION ENGINE] Initialized as ULTRAMAP rule provider (no calculation)")

    # ------------------------------------------------------------------
    # ULTRAMAP Query Methods - For Other Engines
    # ------------------------------------------------------------------

    def get_memory_rules(self, emotion_name: str) -> dict:
        """
        Get memory-related rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - temporal_weight: How long this emotion's influence on memory lasts
        - priority: How important memories tagged with this emotion are
        - duration_sensitivity: How much duration affects this emotion
        - context_sensitivity: How context-dependent this emotion is

        Used by: memory_engine.py for importance scoring and persistence
        """
        proto = self.protocol.get(emotion_name)
        return {
            "temporal_weight": float(proto.get("Temporal Weight", 1.0) or 1.0),
            "priority": float(proto.get("Priority", 0.5) or 0.5) if proto.get("Priority") != "" else 0.5,
            "duration_sensitivity": float(proto.get("Duration Sensitivity", 1.0) or 1.0),
            "context_sensitivity": float(proto.get("Context Sensitivity (0-10)", 5.0) or 5.0) / 10.0,  # Normalize to 0-1
        }

    def get_social_rules(self, emotion_name: str) -> dict:
        """
        Get social-related rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - social_effect: How this emotion affects social needs
        - action_tendency: What behaviors this emotion encourages
        - feedback_adjustment: How this emotion modifies preferences
        - default_need: What system need this emotion relates to

        Used by: social_engine.py for social need calculations
        """
        proto = self.protocol.get(emotion_name)
        return {
            "social_effect": float(proto.get("SocialEffect", 0.0) or 0.0),
            "action_tendency": proto.get("Action/Output Tendency (Examples)", ""),
            "feedback_adjustment": proto.get("Feedback/Preference Adjustment", ""),
            "default_need": proto.get("Default System Need", ""),
        }

    def get_body_rules(self, emotion_name: str) -> dict:
        """
        Get embodiment-related rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - body_processes: Physical manifestations
        - temperature: Hot/cold/warm etc.
        - body_parts: Which body parts are affected
        - energy_level: Activation/arousal level (0-1)
        - valence: Positive/negative emotional tone (-1 to 1)

        Used by: embodiment_engine.py for body state descriptors

        NOTE: Neurochemical tracking REMOVED - using direct descriptors instead
        """
        proto = self.protocol.get(emotion_name)

        # Map to simplified energy/valence model instead of neurochemicals
        energy_map = {
            "excitement": 0.9, "joy": 0.8, "curiosity": 0.7, "anxiety": 0.8, "anger": 0.9,
            "calm": 0.2, "peace": 0.1, "sadness": 0.3, "contentment": 0.4, "neutral": 0.5
        }
        valence_map = {
            "joy": 0.9, "happiness": 0.8, "calm": 0.6, "contentment": 0.7, "peace": 0.8,
            "anger": -0.7, "sadness": -0.6, "anxiety": -0.5, "fear": -0.8, "neutral": 0.0
        }

        return {
            "body_processes": proto.get("Human Bodily Processes", ""),
            "temperature": proto.get("Temperature", ""),
            "body_parts": proto.get("Body Part(s)", ""),
            "energy_level": energy_map.get(emotion_name.lower(), 0.5),
            "valence": valence_map.get(emotion_name.lower(), 0.0),
        }

    def get_recursion_rules(self, emotion_name: str) -> dict:
        """
        Get recursion/loop protocol rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - recursion_protocol: How this emotion loops/repeats
        - break_condition: When to break the loop
        - emergency_ritual: What to do if system collapses
        - escalation_protocol: How this emotion escalates

        Used by: momentum_engine.py, meta_awareness_engine.py for pattern tracking
        """
        proto = self.protocol.get(emotion_name)
        return {
            "recursion_protocol": proto.get("Recursion/Loop Protocol", ""),
            "break_condition": proto.get("Break Condition/Phase Shift", ""),
            "emergency_ritual": proto.get("Emergency Ritual/Output When System Collapses", ""),
            "escalation_protocol": proto.get("Escalation/Mutation Protocol", ""),
        }

    def get_full_rules(self, emotion_name: str) -> dict:
        """
        Get ALL rules for a specific emotion from ULTRAMAP.

        Returns the complete protocol dict for this emotion.
        Useful for debugging or comprehensive analysis.
        """
        return self.protocol.get(emotion_name, {})

    # ------------------------------------------------------------------
    # Compatibility Methods (No-ops)
    # ------------------------------------------------------------------

    def update(self, agent_state, user_input):
        """
        NO-OP: This method no longer calculates emotions.

        Emotions are extracted from Kay's response by EmotionExtractor.
        This method is kept for backwards compatibility only.
        """
        print("[EMOTION ENGINE] Skipping calculation (emotions now self-reported)")
        pass

    def detect_salient_emotions(self, cocktail):
        """
        NO-OP: Salience detection removed.

        Kay naturally expresses which emotions are salient by mentioning them.
        No statistical filtering needed.
        """
        return list(cocktail.keys())
