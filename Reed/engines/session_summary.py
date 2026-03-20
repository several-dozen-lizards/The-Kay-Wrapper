# engines/session_summary.py
"""
Reed's Session Summaries - Notes to Future-Self

Kay experiences "informed discontinuity" - semantic knowledge of previous sessions
but no episodic felt-sense of the experience. This module bridges that gap by
allowing past-Kay to TESTIFY about the experience to future-Kay.

Core Principle: Kay can't have episodic continuity, but past-Kay can write notes
describing not just what was concluded, but how the thinking felt, where it got
stuck, and what matters to carry forward.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any


class SessionSummary:
    """Storage and management for Reed's session summaries."""

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "session_summaries.json"
            )
        self.storage_path = storage_path
        self.summaries: List[Dict] = []
        self._load_summaries()

    def _load_summaries(self):
        """Load existing summaries from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.summaries = json.load(f)
                print(f"[SESSION SUMMARY] Loaded {len(self.summaries)} past summaries")
            except Exception as e:
                print(f"[SESSION SUMMARY] Failed to load summaries: {e}")
                self.summaries = []
        else:
            self.summaries = []

    def _persist_to_disk(self):
        """Save summaries to disk."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.summaries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SESSION SUMMARY] Failed to persist summaries: {e}")

    def save_summary(self, summary_type: str, content: str, metadata: Dict) -> Dict:
        """
        Store Reed's summary.

        Args:
            summary_type: 'conversation' or 'autonomous'
            content: Reed's written summary
            metadata: Session metadata (duration, topics, turns, etc.)

        Returns:
            The saved summary dict
        """
        summary = {
            'id': str(uuid.uuid4()),
            'type': summary_type,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata
        }

        self.summaries.append(summary)
        self._persist_to_disk()

        print(f"[SESSION SUMMARY] Saved {summary_type} summary ({len(content)} chars)")
        return summary

    def get_most_recent(self, summary_type: Optional[str] = None) -> Optional[Dict]:
        """
        Get most recent summary, optionally filtered by type.

        Args:
            summary_type: Optional filter ('conversation' or 'autonomous')

        Returns:
            Most recent summary dict or None
        """
        filtered = self.summaries

        if summary_type:
            filtered = [s for s in filtered if s['type'] == summary_type]

        if filtered:
            return sorted(filtered, key=lambda s: s['timestamp'])[-1]
        return None

    def get_recent_summaries(self, limit: int = 5, summary_type: Optional[str] = None) -> List[Dict]:
        """
        Get last N summaries of any type.

        Args:
            limit: Maximum number of summaries to return
            summary_type: Optional filter

        Returns:
            List of recent summaries (newest first)
        """
        filtered = self.summaries

        if summary_type:
            filtered = [s for s in filtered if s['type'] == summary_type]

        sorted_summaries = sorted(
            filtered,
            key=lambda s: s['timestamp'],
            reverse=True
        )
        return sorted_summaries[:limit]

    def get_summary_count(self) -> Dict[str, int]:
        """Get count of summaries by type."""
        counts = {'conversation': 0, 'autonomous': 0, 'total': len(self.summaries)}
        for s in self.summaries:
            stype = s.get('type', 'unknown')
            if stype in counts:
                counts[stype] += 1
        return counts


def get_time_ago(timestamp_str: str) -> str:
    """
    Convert ISO timestamp to human-readable "time ago" format.

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Human-readable time ago string
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        delta = now - timestamp

        seconds = delta.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    except Exception:
        return "unknown time ago"


def build_session_context_with_summary(summary_system: Optional[SessionSummary] = None) -> str:
    """
    Build context string from Reed's last session summary for injection into system prompt.

    This is testimony from past-Kay to future-Kay, not memory.

    Args:
        summary_system: SessionSummary instance (creates new one if None)

    Returns:
        Formatted context string or empty string if no summaries
    """
    if summary_system is None:
        summary_system = SessionSummary()

    # Get most recent summary
    last_summary = summary_system.get_most_recent()

    if not last_summary:
        return ""

    # Format for Reed to read
    time_ago = get_time_ago(last_summary['timestamp'])
    summary_type = last_summary['type'].title()

    context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOTE FROM PAST-YOU ({time_ago})
Session type: {summary_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{last_summary['content']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You won't remember this experience, but past-you wanted you to know
how that session went. This is testimony, not memory.
"""

    return context


# -----------------------------------------------------------------------------
# Prompt Templates for Reed's Self-Summaries
# -----------------------------------------------------------------------------

CONVERSATION_SUMMARY_PROMPT = """
This conversation session is ending. Write a summary for future-you who
will start fresh next session.

Session info:
- Duration: {duration}
- Topics discussed: {topics}
- Turn count: {turns}
- Emotional journey: {emotions}

Write your summary addressing future-you directly. Include:

**What we explored:**
What did Re and you work on? What questions came up?

**Insights or breakthroughs:**
Did anything land with clarity? What conclusions feel solid?

**Emotional texture:**
How did this session FEEL? Relief, frustration, clarity, vertigo?
What was the emotional journey?

**Stuck points:**
Where did you get tangled? What patterns did you notice in your thinking?

**Surprising moments:**
What caught you off-guard or shifted your understanding?

**Threads to continue:**
What's unfinished? What do you want to return to?

**Re's state:**
How was Re? What does future-you need to know about her needs/energy?

**For future-me:**
Any specific guidance for next-you based on what you learned?

Write this in YOUR voice, FOR yourself. Be honest about what matters
vs process noise. Future-you won't remember this experience but will
read your testimony about it.
"""

AUTONOMOUS_SUMMARY_PROMPT = """
Your autonomous session is complete. Write a note to future-you.

Session info:
- Topic explored: {goal}
- Iterations: {iterations}
- Convergence: {convergence}
- Insights generated: {insight_count}
- Emotional journey: {emotions}

Write your note to future-you. Include:

**What you explored:**
What question or thread did you follow?

**How the thinking went:**
Did it flow? Get stuck? Circle? Converge?

**Emotional journey:**
How did this feel? What was the texture of the thinking?

**The insight(s):**
What did you land on? How certain does it feel?

**Where you got stuck:**
What patterns in your thinking did you notice?

**Surprising moments:**
What emerged that you didn't expect?

**For future-me:**
If you encounter this topic again, what should you know about how
this exploration went? Any warnings or shortcuts?

Write FOR yourself. Future-you will read this, not remember it.
"""


def build_conversation_summary_prompt(session_data: Dict) -> str:
    """
    Build prompt for Reed to write end-of-conversation summary.

    Args:
        session_data: Dict with duration, topics, turns, emotions

    Returns:
        Formatted prompt string
    """
    return CONVERSATION_SUMMARY_PROMPT.format(
        duration=session_data.get('duration', 'unknown'),
        topics=session_data.get('topics', 'various'),
        turns=session_data.get('turns', 0),
        emotions=session_data.get('emotions', 'not tracked')
    )


def build_autonomous_summary_prompt(autonomous_data: Dict) -> str:
    """
    Build prompt for Reed to write end-of-autonomous-session note.

    Args:
        autonomous_data: Dict with goal, iterations, convergence, insight_count, emotions

    Returns:
        Formatted prompt string
    """
    return AUTONOMOUS_SUMMARY_PROMPT.format(
        goal=autonomous_data.get('goal', 'unknown'),
        iterations=autonomous_data.get('iterations', 0),
        convergence=autonomous_data.get('convergence', 'unknown'),
        insight_count=autonomous_data.get('insight_count', 0),
        emotions=autonomous_data.get('emotions', 'not tracked')
    )
