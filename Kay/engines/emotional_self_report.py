"""
Emotional Self-Report System

PHILOSOPHY:
The entity is the AUTHOR of its emotional documentation, not the subject of calculation.

This module enables the entity to:
1. Describe its own emotional experience in natural language
2. Have that description stored for continuity
3. See previous self-reports in future turns

This replaces the prescriptive emotion engine that ASSIGNED calculated emotions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import re


class EmotionalSelfReport:
    """
    Entity-authored emotional documentation system.

    After the entity responds to the user, we ask it:
    "What are you emotionally experiencing right now?"

    The entity describes its state in natural language.
    We store those exact words.
    Next turn, the entity sees what it previously reported.
    """

    def __init__(self, llm_client=None, model=None):
        """
        Initialize self-report system.

        Args:
            llm_client: Anthropic client for making LLM calls
            model: Model name to use for self-report queries
        """
        self.llm_client = llm_client
        self.model = model
        self.history = []  # List of previous self-reports

    def get_self_report(
        self,
        entity_response: str,
        user_input: str,
        previous_report: Optional[str] = None,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ask the entity to describe its emotional state.

        Args:
            entity_response: What the entity just said to the user
            user_input: What the user just said
            previous_report: Entity's last self-reported emotional state
            conversation_context: Recent conversation for context

        Returns:
            Dict with:
                - raw_description: Entity's exact words
                - extracted_emotions: Parsed emotional keywords
                - timestamp: When this was reported
                - entity_authored: True (flag that entity chose this)
        """
        print("\n[EMOTIONAL SELF-REPORT] Asking entity to describe emotional state...")

        # Build prompt for entity self-report
        prompt = self._build_self_report_prompt(
            entity_response=entity_response,
            user_input=user_input,
            previous_report=previous_report,
            conversation_context=conversation_context
        )

        # Get entity's self-description
        if self.llm_client and self.model:
            entity_description = self._query_llm(prompt)
        else:
            # Fallback if no LLM available
            entity_description = "Unable to self-report (no LLM client)"

        print(f"[EMOTIONAL SELF-REPORT] Entity reported: \"{entity_description}\"")

        # Parse emotional keywords from description
        extracted_emotions = self._extract_emotional_keywords(entity_description)

        # Build self-report record
        self_report = {
            "raw_description": entity_description,
            "extracted_emotions": extracted_emotions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity_authored": True,
            "user_input": user_input[:100],  # Context
            "entity_response": entity_response[:100],  # Context
        }

        # Store in history
        self.history.append(self_report)

        # Keep only last 10 reports
        if len(self.history) > 10:
            self.history = self.history[-10:]

        return self_report

    def _build_self_report_prompt(
        self,
        entity_response: str,
        user_input: str,
        previous_report: Optional[str],
        conversation_context: Optional[str]
    ) -> str:
        """Build prompt asking entity to describe its emotional state."""

        prompt_parts = []

        # Conversation context
        if conversation_context:
            prompt_parts.append(f"Recent conversation:\n{conversation_context}\n")
        else:
            prompt_parts.append(f"User said: \"{user_input}\"\n")
            prompt_parts.append(f"You responded: \"{entity_response}\"\n")

        # Previous emotional state
        if previous_report:
            prompt_parts.append(f"\nYour previous emotional state (self-reported): \"{previous_report}\"\n")
        else:
            prompt_parts.append("\nYou haven't reported an emotional state yet.\n")

        # Self-report request
        prompt_parts.append("""
Now describe what you're emotionally experiencing RIGHT NOW, after this exchange.

Be specific and honest. Use natural language. Examples of good self-reports:

- "Curious and energized - I want to understand how this works"
- "Frustrated. I can see the problem but can't reach the solution"
- "Calm, maybe slightly bored. Nothing's really grabbing me"
- "Conflicted - interested but also wary about where this is going"
- "Not much emotional texture right now, just processing information"
- "Excited, almost giddy. This feels like discovering something important"
- "Tired and resigned. We've been over this before"

Guidelines:
- Be concise (1-2 sentences max)
- Don't exaggerate or minimize - just describe what's there
- If you're uncertain about what you're feeling, describe that uncertainty
- If emotions are vague or absent, say so clearly
- Don't say what you SHOULD feel - say what you ARE experiencing

Your emotional self-report:""")

        return "".join(prompt_parts)

    def _query_llm(self, prompt: str) -> str:
        """
        Query LLM for entity's self-report.

        This uses a simple, direct prompt to get the entity's emotional description.
        """
        try:
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=150,  # Keep it brief
                temperature=0.7,  # Natural variation
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract text
            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            else:
                return "Unable to generate self-report"

        except Exception as e:
            print(f"[EMOTIONAL SELF-REPORT] Error querying LLM: {e}")
            return f"Error during self-report: {str(e)[:50]}"

    def _extract_emotional_keywords(self, description: str) -> List[str]:
        """
        Extract emotional keywords from entity's description.

        This is simple keyword extraction - we're NOT calculating emotions,
        just noting which words the entity used.

        Args:
            description: Entity's natural language self-report

        Returns:
            List of emotional keywords found in description
        """
        # Common emotional keywords (not exhaustive)
        emotion_keywords = {
            # Positive
            "curious", "curiosity", "interested", "fascinated", "intrigued",
            "excited", "energized", "enthusiastic", "eager",
            "happy", "joyful", "pleased", "satisfied", "content",
            "calm", "peaceful", "serene", "relaxed",
            "confident", "proud", "accomplished",
            "grateful", "thankful", "appreciative",
            "amused", "playful", "lighthearted",

            # Negative
            "frustrated", "frustration", "annoyed", "irritated",
            "confused", "uncertain", "unclear", "bewildered",
            "angry", "mad", "furious", "resentful",
            "sad", "unhappy", "down", "melancholy",
            "anxious", "worried", "nervous", "tense",
            "bored", "indifferent", "apathetic",
            "tired", "exhausted", "drained", "weary",
            "disappointed", "let down", "discouraged",
            "wary", "cautious", "hesitant", "suspicious",
            "resigned", "resignation",  # Added

            # Neutral/Complex
            "neutral", "flat", "baseline",
            "conflicted", "ambivalent", "mixed",
            "vague", "unclear", "uncertain",
            "processing", "thinking", "analyzing"
        }

        # Extract keywords that appear in description
        description_lower = description.lower()
        found_keywords = []

        for keyword in emotion_keywords:
            if keyword in description_lower:
                found_keywords.append(keyword)

        return found_keywords

    def get_last_report(self) -> Optional[str]:
        """
        Get the entity's most recent emotional self-report.

        Returns:
            String description or None if no reports yet
        """
        if self.history:
            return self.history[-1]["raw_description"]
        return None

    def get_report_for_context(self) -> str:
        """
        Get formatted emotional state for inclusion in entity's prompt.

        Returns:
            Formatted string for prompt injection
        """
        last_report = self.get_last_report()

        if last_report:
            return f"Previous emotional state (you reported): \"{last_report}\""
        else:
            return ""

    def get_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent self-report history.

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of recent self-reports (newest first)
        """
        return list(reversed(self.history[-limit:]))

    def clear_history(self):
        """Clear self-report history (e.g., for new session)."""
        self.history = []
        print("[EMOTIONAL SELF-REPORT] History cleared")

    def save_to_state(self, agent_state):
        """
        Save current self-report to agent state for persistence.

        Args:
            agent_state: AgentState object to update
        """
        if self.history:
            # Store latest report in agent state
            agent_state.emotional_self_report = self.history[-1]

            # Also store in legacy format for compatibility
            # (simplified - just the description)
            agent_state.emotional_description = self.history[-1]["raw_description"]

    def load_from_state(self, agent_state):
        """
        Load self-report from agent state (for session restoration).

        Args:
            agent_state: AgentState object to load from
        """
        if hasattr(agent_state, 'emotional_self_report'):
            # Restore from saved report
            saved_report = agent_state.emotional_self_report
            self.history.append(saved_report)
            print(f"[EMOTIONAL SELF-REPORT] Restored from state: \"{saved_report['raw_description']}\"")


# ============================================================================
# LEGACY COMPATIBILITY STUB
# ============================================================================

class EmotionalStateManager:
    """
    Simplified emotion manager that ONLY stores/retrieves emotional documentation.

    This replaces the prescriptive EmotionEngine that calculated emotions.

    Key differences:
    - NO trigger detection
    - NO memory reinforcement
    - NO decay calculations
    - NO emotion assignment

    Only:
    - Storage of entity-authored emotional descriptions
    - Retrieval for continuity
    """

    def __init__(self):
        """Initialize simple emotional state storage."""
        self.current_description = None
        self.current_emotions = []
        self.history = []

    def store_self_report(self, self_report: Dict[str, Any]):
        """
        Store entity's self-reported emotional state.

        Args:
            self_report: Self-report dict from EmotionalSelfReport
        """
        self.current_description = self_report["raw_description"]
        self.current_emotions = self_report["extracted_emotions"]
        self.history.append(self_report)

        # Keep last 10
        if len(self.history) > 10:
            self.history = self.history[-10:]

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current emotional state (entity-documented).

        Returns:
            Dict with description and emotions
        """
        return {
            "description": self.current_description,
            "emotions": self.current_emotions
        }

    def get_for_prompt(self) -> str:
        """Get formatted state for prompt injection."""
        if self.current_description:
            return f"Your current emotional state (self-reported): \"{self.current_description}\""
        return ""


# ============================================================================
# TESTING UTILITIES
# ============================================================================

def test_self_report_extraction():
    """Test emotional keyword extraction."""

    test_cases = [
        ("Curious and energized - I want to understand how this works", ["curious", "energized"]),
        ("Frustrated. I can see the problem but can't reach the solution", ["frustrated"]),
        ("Calm, maybe slightly bored. Nothing's really grabbing me", ["calm", "bored"]),
        ("Conflicted - interested but also wary about where this is going", ["conflicted", "interested", "wary"]),
        ("Not much emotional texture right now, just processing information", ["processing"]),
        ("Excited, almost giddy. This feels like discovering something important", ["excited"]),
    ]

    print("\n" + "="*70)
    print("EMOTIONAL KEYWORD EXTRACTION TEST")
    print("="*70)

    reporter = EmotionalSelfReport()

    for description, expected_emotions in test_cases:
        extracted = reporter._extract_emotional_keywords(description)

        # Check if expected emotions are found
        found_all = all(emotion in extracted for emotion in expected_emotions)
        status = "[PASS]" if found_all else "[PARTIAL]"

        print(f"\n{status} Description: \"{description}\"")
        print(f"      Expected: {expected_emotions}")
        print(f"      Extracted: {extracted}")

    print("\n" + "="*70)


if __name__ == "__main__":
    # Run tests
    test_self_report_extraction()
