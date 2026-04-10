# engines/time_awareness.py
"""
Time Awareness System for the entityZero
Provides temporal context for the entity's responses including:
- Current time/date awareness
- Time since last session
- Time of day context
- Within-session gap detection
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path


class TimeAwareness:
    """
    Manages time awareness for the entity Zero.

    Tracks:
    - Current time for each message
    - Time since last session
    - Time of day (morning/afternoon/evening/night)
    - Gaps within a session
    """

    def __init__(self):
        # Compute absolute path for state file
        self.STATE_FILE = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory", "time_state.json"
        )
        self.session_start: datetime = datetime.now()
        self.last_message_time: datetime = datetime.now()
        self.last_session_data: Dict = {}

        # Load persisted state
        self._load_state()

        # Calculate time since last session
        self.time_since_last = self._calculate_time_since_last()

    def _load_state(self):
        """Load time state from disk."""
        try:
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_session_data = data
                    print(f"[TIME] Loaded session state from disk")
        except Exception as e:
            print(f"[TIME] Error loading state: {e}")
            self.last_session_data = {}

    def _save_state(self):
        """Save time state to disk."""
        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)

        state = {
            "last_interaction": datetime.now().isoformat(),
            "last_session_start": self.session_start.isoformat(),
            "last_session_end": datetime.now().isoformat(),
            "total_turns_last_session": getattr(self, '_turn_count', 0)
        }

        try:
            with open(self.STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[TIME] Error saving state: {e}")

    def _calculate_time_since_last(self) -> Optional[timedelta]:
        """Calculate time since last interaction."""
        last_interaction = self.last_session_data.get("last_interaction")
        if not last_interaction:
            return None

        try:
            last_time = datetime.fromisoformat(last_interaction)
            # Make timezone-naive for comparison
            if last_time.tzinfo:
                last_time = last_time.replace(tzinfo=None)
            return datetime.now() - last_time
        except Exception as e:
            print(f"[TIME] Error calculating time since last: {e}")
            return None

    def get_time_of_day(self, dt: datetime = None) -> str:
        """
        Get time of day category.

        Args:
            dt: Datetime to check (defaults to now)

        Returns:
            One of: "morning", "afternoon", "evening", "night"
        """
        if dt is None:
            dt = datetime.now()

        hour = dt.hour

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def format_duration(self, delta: timedelta) -> str:
        """
        Format a timedelta as human-readable duration.

        Args:
            delta: Time duration

        Returns:
            Human-readable string like "3 hours ago"
        """
        if delta is None:
            return "unknown"

        total_seconds = delta.total_seconds()

        # Under 1 minute
        if total_seconds < 60:
            return "just now"

        # Minutes
        if total_seconds < 3600:
            minutes = int(total_seconds / 60)
            if minutes == 1:
                return "a minute ago"
            return f"{minutes} minutes ago"

        # Hours
        if total_seconds < 86400:
            hours = int(total_seconds / 3600)
            if hours == 1:
                return "about an hour ago"
            return f"{hours} hours ago"

        # Days
        days = int(total_seconds / 86400)
        if days == 1:
            return "yesterday"
        if days < 7:
            return f"{days} days ago"

        # Weeks
        weeks = int(days / 7)
        if weeks == 1:
            return "about a week ago"
        if weeks < 4:
            return f"{weeks} weeks ago"

        # Months
        months = int(days / 30)
        if months == 1:
            return "about a month ago"
        if months < 12:
            return f"{months} months ago"

        # Years
        years = int(days / 365)
        if years == 1:
            return "about a year ago"
        return f"{years} years ago"

    def format_datetime(self, dt: datetime = None) -> str:
        """
        Format datetime for display.

        Args:
            dt: Datetime to format (defaults to now)

        Returns:
            Formatted string like "Wednesday, November 26, 2025 at 2:34 PM"
        """
        if dt is None:
            dt = datetime.now()

        # Get timezone name (simplified)
        try:
            import time
            tz_name = time.strftime("%Z")
        except:
            tz_name = ""

        # Format: "Wednesday, November 26, 2025 at 2:34 PM EST"
        formatted = dt.strftime("%A, %B %d, %Y at %I:%M %p")
        if tz_name:
            formatted += f" {tz_name}"

        return formatted

    def get_message_gap(self) -> Optional[timedelta]:
        """
        Get time since last message in this session.

        Returns:
            timedelta since last message, or None if first message
        """
        if self.last_message_time is None:
            return None

        return datetime.now() - self.last_message_time

    def format_gap_awareness(self, gap: timedelta) -> Optional[str]:
        """
        Format gap awareness for significant pauses.

        Only returns a message if gap is significant (30+ minutes).

        Args:
            gap: Time gap between messages

        Returns:
            Awareness string, or None if gap is not significant
        """
        if gap is None:
            return None

        minutes = gap.total_seconds() / 60

        if minutes < 30:
            return None  # Not significant

        if minutes < 60:
            return "Re was away for about half an hour"
        elif minutes < 120:
            return "Re was away for about an hour"
        else:
            hours = int(minutes / 60)
            return f"Re was away for about {hours} hours"

    def record_message(self, turn_count: int = 0):
        """
        Record that a message was sent/received.
        Updates last message time and persists state.

        Args:
            turn_count: Current turn count in session
        """
        self.last_message_time = datetime.now()
        self._turn_count = turn_count
        self._save_state()

    def get_session_duration(self) -> timedelta:
        """Get duration of current session."""
        return datetime.now() - self.session_start

    def format_session_duration(self) -> str:
        """Format current session duration for display."""
        duration = self.get_session_duration()
        minutes = int(duration.total_seconds() / 60)

        if minutes < 1:
            return "just started"
        elif minutes < 60:
            return f"{minutes} minutes"
        else:
            hours = int(minutes / 60)
            remaining_mins = minutes % 60
            if remaining_mins > 0:
                return f"{hours} hour{'s' if hours > 1 else ''} and {remaining_mins} minutes"
            return f"{hours} hour{'s' if hours > 1 else ''}"

    def get_time_context(self, turn_count: int = 0) -> Dict:
        """
        Get complete time context for LLM.

        Args:
            turn_count: Current turn count

        Returns:
            Dict with all time-related context
        """
        now = datetime.now()
        message_gap = self.get_message_gap()

        context = {
            "current_time": self.format_datetime(now),
            "time_of_day": self.get_time_of_day(now),
            "session_duration": self.format_session_duration(),
            "turn_count": turn_count,
        }

        # Add time since last session (only on first message)
        if turn_count == 0 and self.time_since_last:
            context["time_since_last_session"] = self.format_duration(self.time_since_last)

            # Add context about when last session was
            last_interaction = self.last_session_data.get("last_interaction")
            if last_interaction:
                try:
                    last_time = datetime.fromisoformat(last_interaction)
                    if last_time.tzinfo:
                        last_time = last_time.replace(tzinfo=None)
                    context["last_session_time_of_day"] = self.get_time_of_day(last_time)
                except:
                    pass

        # Add message gap awareness for significant pauses
        if message_gap:
            gap_msg = self.format_gap_awareness(message_gap)
            if gap_msg:
                context["message_gap"] = gap_msg

        return context

    def build_time_prompt_section(self, turn_count: int = 0) -> str:
        """
        Build time context section for system prompt.

        Args:
            turn_count: Current turn count

        Returns:
            Formatted string to inject into prompt
        """
        ctx = self.get_time_context(turn_count)

        lines = []
        lines.append(f"CURRENT TIME: {ctx['current_time']} ({ctx['time_of_day']})")

        # First message of session - include time since last
        if turn_count == 0 and "time_since_last_session" in ctx:
            last_tod = ctx.get("last_session_time_of_day", "")
            if last_tod:
                lines.append(f"TIME SINCE LAST SESSION: {ctx['time_since_last_session']} (you last spoke {last_tod})")
            else:
                lines.append(f"TIME SINCE LAST SESSION: {ctx['time_since_last_session']}")
        elif turn_count == 0:
            lines.append("This appears to be your first conversation")

        # Include session duration for longer sessions
        if turn_count > 5:
            lines.append(f"SESSION DURATION: {ctx['session_duration']}")

        # Include message gap if significant
        if "message_gap" in ctx:
            lines.append(f"NOTE: {ctx['message_gap']}")

        return "\n".join(lines)


# Singleton instance for global access
_time_awareness_instance: Optional[TimeAwareness] = None

def get_time_awareness() -> TimeAwareness:
    """Get the singleton TimeAwareness instance."""
    global _time_awareness_instance
    if _time_awareness_instance is None:
        _time_awareness_instance = TimeAwareness()
    return _time_awareness_instance

def reset_time_awareness():
    """Reset the singleton (for testing or session restart)."""
    global _time_awareness_instance
    _time_awareness_instance = None
