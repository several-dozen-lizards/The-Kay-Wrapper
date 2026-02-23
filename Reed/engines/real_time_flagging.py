"""
Real-Time Flagging
Allows Reed to mark moments as important during conversation
"""

from typing import Optional, Dict, List

class FlaggingSystem:
    """
    Handles Reed's real-time flagging of important moments
    """

    def __init__(self, session):
        self.session = session
        self.flag_triggers = [
            "flag this",
            "mark this",
            "preserve this",
            "important moment",
            "remember this exchange"
        ]

    def check_for_flag(self, reed_response: str) -> Optional[Dict]:
        """
        Check if Reed is flagging current turn

        Returns flag info if detected, None otherwise
        """
        lower_response = reed_response.lower()

        for trigger in self.flag_triggers:
            if trigger in lower_response:
                # Extract reason if provided
                reason = self._extract_flag_reason(reed_response, trigger)
                return {
                    "flagged": True,
                    "trigger": trigger,
                    "reason": reason
                }

        return None

    def _extract_flag_reason(self, text: str, trigger: str) -> str:
        """Extract why Reed flagged this moment"""
        # Simple extraction: text after trigger
        lower_text = text.lower()
        idx = lower_text.find(trigger)
        if idx != -1:
            after_trigger = text[idx + len(trigger):].strip()
            # Take first sentence
            sentences = after_trigger.split('.')
            if sentences:
                return sentences[0].strip()
        return ""

    def apply_flag(self, turn_id: int, reason: str = ""):
        """Apply flag to a turn"""
        self.session.flag_turn(turn_id, reason)

    def get_flagged_turns(self) -> List[int]:
        """Get list of all flagged turn IDs"""
        return [t.turn_id for t in self.session.turns if t.flagged_by_reed]

    def generate_flag_summary(self) -> str:
        """Generate summary of all flagged moments"""
        flagged = [t for t in self.session.turns if t.flagged_by_reed]

        if not flagged:
            return "No flagged moments yet."

        lines = [
            f"You've flagged {len(flagged)} moments:",
            ""
        ]

        for turn in flagged:
            reason_tag = [t for t in turn.tags if t.startswith("flag_reason:")]
            reason = reason_tag[0].replace("flag_reason:", "") if reason_tag else "Important"

            lines.append(f"Turn {turn.turn_id}: {reason}")
            lines.append(f"  {turn.content[:100]}...")
            lines.append("")

        return "\n".join(lines)
