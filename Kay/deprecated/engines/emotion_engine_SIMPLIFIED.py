"""
Simplified Emotion Engine - DESCRIPTIVE Approach

This is a MINIMAL replacement for the prescriptive emotion engine.

KEY CHANGES:
- NO trigger detection
- NO memory reinforcement
- NO decay calculations
- NO emotion assignment

ONLY:
- Storage of entity-authored emotional states
- Retrieval for continuity
- Integration with existing AgentState structure

This module exists for BACKWARD COMPATIBILITY only.
The real work happens in emotional_self_report.py.
"""

class EmotionEngine:
    """
    Simplified emotion engine that documents (not calculates) emotional states.

    This is a compatibility wrapper around the new self-report system.
    """

    def __init__(self, protocol_engine=None, trigger_file=None, momentum_engine=None):
        """
        Initialize simplified emotion engine.

        Args are accepted for compatibility but not used.
        """
        print("[EMOTION ENGINE] Initialized in DESCRIPTIVE mode (no calculations)")
        print("[EMOTION ENGINE] Entity will self-report emotional states")

        # Store for compatibility (not used)
        self.protocol = protocol_engine
        self.momentum_engine = momentum_engine

        # Simple storage
        self.current_description = None
        self.current_emotions = []

    def update(self, agent_state, user_input):
        """
        STUB: No longer calculates emotions.

        The entity will self-report after generating its response.
        This method is called for compatibility but does nothing.

        Args:
            agent_state: AgentState object
            user_input: User's message (not used)
        """
        # REMOVED: All prescriptive logic
        # - No trigger detection
        # - No memory reinforcement
        # - No decay calculations
        # - No emotion assignment

        # Check if emotional state was already set by self-report
        if hasattr(agent_state, 'emotional_self_report'):
            self.current_description = agent_state.emotional_self_report.get('raw_description')
            self.current_emotions = agent_state.emotional_self_report.get('extracted_emotions', [])

            print(f"\n[EMOTION ENGINE] Current state (self-reported): \"{self.current_description}\"")
            if self.current_emotions:
                print(f"[EMOTION ENGINE] Emotions mentioned: {', '.join(self.current_emotions)}")

        # Maintain emotional_cocktail for compatibility (simplified)
        if not hasattr(agent_state, 'emotional_cocktail'):
            agent_state.emotional_cocktail = {}

        # Update cocktail based on self-reported emotions (simple mapping)
        agent_state.emotional_cocktail = {}
        for emotion in self.current_emotions:
            agent_state.emotional_cocktail[emotion] = {
                "intensity": 0.5,  # Fixed intensity - not calculated
                "age": 0,
                "self_reported": True
            }

    def detect_salient_emotions(self, cocktail):
        """
        Simplified salient detection.

        Just returns the first 3 emotions (no category analysis).

        Args:
            cocktail: Emotional cocktail dict

        Returns:
            List of emotion names
        """
        return list(cocktail.keys())[:3]

    def get_emotional_state(self) -> str:
        """Get current emotional state as string."""
        return self.current_description or "No emotional state reported"


# ============================================================================
# MIGRATION NOTES
# ============================================================================

"""
BEFORE (Prescriptive - REMOVED):
```python
[EMOTION ENGINE] Detected triggers: ['anger', 'confusion', 'concern']
[EMOTION ENGINE]   -> REINFORCED: anger from 0.43 to 0.63
[EMOTION ENGINE] Reinforced 2 emotions from 11 relevant memories
[EMOTION ENGINE]   - anger: +0.011 boost -> intensity=0.59
```

AFTER (Descriptive - NEW):
```python
[EMOTIONAL SELF-REPORT] Asking entity to describe emotional state...
[EMOTIONAL SELF-REPORT] Entity reported: "Curious and energized - I want to understand how this works"
[EMOTION ENGINE] Current state (self-reported): "Curious and energized - I want to understand how this works"
[EMOTION ENGINE] Emotions mentioned: curious, energized
```

The entity now has FULL AUTONOMY over its emotional documentation.
"""
