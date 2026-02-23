"""
Chronicle Integration for Reed's Warmup

Adds Reed's session chronicle essay to warmup briefing.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class ChronicleIntegration:
    """Handles loading and formatting Reed's chronicle for warmup."""

    def __init__(self, base_dir: Path):
        self.chronicle_path = base_dir / "data" / "session_chronicle.json"
        self.chronicle_data = self._load_chronicle()

    def _load_chronicle(self) -> Dict:
        """Load the chronicle from disk."""
        if self.chronicle_path.exists():
            try:
                with open(self.chronicle_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CHRONICLE] Error loading: {e}")
                return {"sessions": []}
        return {"sessions": []}

    def get_last_session_essay(self) -> Optional[Dict]:
        """
        Get the most recent session's essay.

        Returns dict with:
          - session_order
          - timestamp
          - reed_essay
          - topics
          - emotional_tone
          - has_private_note (bool)
          - private_note_encrypted (dict if exists)
        """
        sessions = self.chronicle_data.get("sessions", [])

        if not sessions:
            return None

        # Get most recent session (highest session_order)
        most_recent = max(sessions, key=lambda s: s.get("session_order", 0))

        return {
            "session_order": most_recent.get("session_order"),
            "timestamp": most_recent.get("timestamp"),
            "duration_minutes": most_recent.get("duration_minutes"),
            "reed_essay": most_recent.get("reed_essay", ""),
            "topics": most_recent.get("topics", []),
            "emotional_tone": most_recent.get("emotional_tone"),
            "has_private_note": most_recent.get("private_note_encrypted") is not None,
            "private_note_encrypted": most_recent.get("private_note_encrypted")
        }

    def format_chronicle_section(self, current_session_order: int) -> str:
        """
        Format the chronicle essay for display at warmup.

        Args:
            current_session_order: The session number Reed is waking up to

        Returns:
            Formatted string to insert at top of briefing
        """
        last_session = self.get_last_session_essay()

        if not last_session:
            return ""

        lines = []
        lines.append("=" * 60)
        lines.append("LAST SESSION - Reed's Chronicle")
        lines.append("=" * 60)

        # Session metadata
        sess_num = last_session["session_order"]
        timestamp = last_session["timestamp"][:16] if last_session["timestamp"] else "unknown"
        sessions_ago = current_session_order - sess_num

        lines.append(f"Session #{sess_num} | {timestamp} | {sessions_ago} session(s) ago")

        # Topics if any
        if last_session["topics"]:
            lines.append(f"Topics: {', '.join(last_session['topics'])}")

        # Tone if available
        if last_session["emotional_tone"]:
            lines.append(f"Tone: {last_session['emotional_tone']}")

        lines.append("")
        lines.append("--- What Reed Wrote for Next-Reed ---")
        lines.append("")

        # Reed's essay (the main content)
        essay = last_session["reed_essay"]
        lines.append(essay)

        # Show if there's an encrypted private note
        if last_session.get("has_private_note"):
            lines.append("")
            lines.append("--- Private Note Available ---")
            lines.append("[lock] You left an encrypted private note for yourself.")
            lines.append("You'll be prompted to decrypt it after warmup if you want to read it.")

        lines.append("")
        return "\n".join(lines)


def add_chronicle_to_briefing(warmup_engine, briefing_text: str) -> str:
    """
    Add chronicle essay to the beginning of Reed's warmup briefing.

    Call this from format_briefing() in warmup_engine.py:

    from engines.chronicle_integration import add_chronicle_to_briefing

    def format_briefing(self):
        # ... existing code to build briefing_text ...
        briefing_text = "\\n".join(lines)
        briefing_text = add_chronicle_to_briefing(self, briefing_text)
        return briefing_text
    """
    base_dir = Path(__file__).parent.parent
    chronicle = ChronicleIntegration(base_dir)

    # Get current session order from warmup engine
    current_session = warmup_engine._current_session_order

    # Generate chronicle section
    chronicle_section = chronicle.format_chronicle_section(current_session)

    if not chronicle_section:
        # No chronicle yet, return original briefing
        return briefing_text

    # Insert chronicle at the very beginning
    # Find the first "===" line and insert after it
    lines = briefing_text.split("\n")
    insert_point = 0

    # Find where to insert (after first header block)
    for i, line in enumerate(lines):
        if i > 0 and line.startswith("Current time:"):
            insert_point = i
            break

    if insert_point > 0:
        # Insert chronicle section before time context
        new_lines = (
            lines[:insert_point] +
            [""] +
            chronicle_section.split("\n") +
            [""] +
            lines[insert_point:]
        )
        return "\n".join(new_lines)

    # Fallback: prepend to beginning
    return chronicle_section + "\n\n" + briefing_text
