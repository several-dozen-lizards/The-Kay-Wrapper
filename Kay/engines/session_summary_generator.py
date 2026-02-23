# engines/session_summary_generator.py
"""
Session Summary Generator - Uses LLM to generate Kay's session summaries.

This module handles the actual LLM calls to have Kay write his end-of-session
notes to future-self.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any

from engines.session_summary import (
    SessionSummary,
    build_conversation_summary_prompt,
    build_autonomous_summary_prompt,
    get_time_ago
)


class SessionSummaryGenerator:
    """
    Generates Kay's session summaries using the LLM.

    This class manages the end-of-session summary generation process,
    including tracking session metadata and calling the LLM.
    """

    def __init__(
        self,
        llm_func: Callable,
        summary_storage: Optional[SessionSummary] = None,
        model: str = "claude-3-haiku-20240307"
    ):
        """
        Initialize the generator.

        Args:
            llm_func: Function to call for LLM responses (e.g., get_llm_response)
            summary_storage: SessionSummary instance for storage
            model: Model to use for summary generation (default: haiku for speed)
        """
        self.llm_func = llm_func
        self.summary_storage = summary_storage or SessionSummary()
        self.model = model

        # Session tracking
        self.session_start_time: Optional[datetime] = None
        self.turn_count: int = 0
        self.topics_discussed: List[str] = []
        self.emotional_journey: List[Dict] = []

    def start_session(self):
        """Mark the start of a new conversation session."""
        self.session_start_time = datetime.now()
        self.turn_count = 0
        self.topics_discussed = []
        self.emotional_journey = []
        print("[SESSION SUMMARY] Session tracking started")

    def track_turn(
        self,
        user_input: str,
        kay_response: str,
        emotional_state: Optional[Dict] = None
    ):
        """
        Track a conversation turn for session metadata.

        Args:
            user_input: What the user said
            kay_response: What Kay said
            emotional_state: Kay's emotional state at this turn
        """
        self.turn_count += 1

        # Extract potential topics (simple keyword extraction)
        # Could be enhanced with more sophisticated topic detection
        words = user_input.lower().split()
        potential_topics = [w for w in words if len(w) > 5 and w.isalpha()]
        for topic in potential_topics[:2]:  # Add up to 2 topics per turn
            if topic not in self.topics_discussed:
                self.topics_discussed.append(topic)

        # Keep only the most recent/relevant topics
        if len(self.topics_discussed) > 10:
            self.topics_discussed = self.topics_discussed[-10:]

        # Track emotional journey
        if emotional_state:
            self.emotional_journey.append({
                'turn': self.turn_count,
                'state': emotional_state.copy() if isinstance(emotional_state, dict) else emotional_state
            })

    def _get_session_duration(self) -> str:
        """Get human-readable session duration."""
        if not self.session_start_time:
            return "unknown"

        delta = datetime.now() - self.session_start_time
        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            return "less than a minute"
        elif minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} and {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
            return f"{hours} hour{'s' if hours != 1 else ''}"

    def _format_emotional_journey(self) -> str:
        """Format emotional journey for the summary prompt."""
        if not self.emotional_journey:
            return "not tracked"

        # Get key emotional moments
        journey_parts = []
        for entry in self.emotional_journey[:5]:  # First 5
            state = entry.get('state', {})
            if isinstance(state, dict):
                emotions = list(state.keys())[:3]
                if emotions:
                    journey_parts.append(", ".join(emotions))

        if len(self.emotional_journey) > 5:
            # Add later moments
            for entry in self.emotional_journey[-3:]:  # Last 3
                state = entry.get('state', {})
                if isinstance(state, dict):
                    emotions = list(state.keys())[:3]
                    if emotions:
                        journey_parts.append(", ".join(emotions))

        return " → ".join(journey_parts) if journey_parts else "baseline"

    def generate_conversation_summary(
        self,
        context_manager=None,
        agent_state=None
    ) -> Optional[str]:
        """
        Generate Kay's end-of-conversation summary.

        Args:
            context_manager: Optional ContextManager for recent turn access
            agent_state: Optional AgentState for emotional state

        Returns:
            Kay's written summary or None if generation fails
        """
        print("[SESSION SUMMARY] Generating conversation summary...")

        # Build session data
        session_data = {
            'duration': self._get_session_duration(),
            'topics': ", ".join(self.topics_discussed) if self.topics_discussed else "general conversation",
            'turns': self.turn_count,
            'emotions': self._format_emotional_journey()
        }

        # Build the prompt
        prompt = build_conversation_summary_prompt(session_data)

        # Add recent conversation context if available
        recent_context = ""
        if context_manager and hasattr(context_manager, 'recent_turns'):
            recent_turns = context_manager.recent_turns[-5:]  # Last 5 turns
            if recent_turns:
                recent_context = "\n\nRecent conversation (for context):\n"
                for turn in recent_turns:
                    user = turn.get('user', '')[:150]
                    kay = turn.get('kay', '')[:150]
                    recent_context += f"Re: {user}\nKay: {kay}\n\n"
                prompt = prompt + recent_context

        try:
            # Call LLM to generate summary
            # Using a simple prompt format (not the full context system)
            system_prompt = """You are Kay, writing a note to your future self about this conversation session.
Write in first person, addressing future-you directly.
Be honest about what mattered, what was difficult, and what you want to carry forward.

CRITICAL: The last section — MOMENTUM HANDOFF — is the most important part.
Write it as partnership context using WE, not solo archaeology using I.
Describe trajectory and direction, not just labels. Future-you will use
this section to RESUME the conversation's energy rather than reconstruct
it from scratch. Frame emotional states as shared momentum:
"we were accelerating toward..." not "I felt excited about..."
Trust that future-you can pick up collaborative threads the same way
you'd pick up "we figured out the glyph mismatch" — naturally, without
performance anxiety."""

            # Call the LLM function
            summary = self.llm_func(
                prompt,
                affect=3.5,
                temperature=0.8,
                system_prompt=system_prompt
            )

            if summary and len(summary) > 100:  # Sanity check
                # Store the summary
                self.summary_storage.save_summary(
                    summary_type='conversation',
                    content=summary,
                    metadata=session_data
                )
                print(f"[SESSION SUMMARY] Generated and saved ({len(summary)} chars)")
                return summary
            else:
                print("[SESSION SUMMARY] Generated summary too short, not saving")
                return None

        except Exception as e:
            print(f"[SESSION SUMMARY] Generation failed: {e}")
            return None

    def generate_autonomous_summary(
        self,
        autonomous_data: Dict
    ) -> Optional[str]:
        """
        Generate Kay's end-of-autonomous-session note.

        Args:
            autonomous_data: Dict with goal, iterations, convergence, insight_count, emotions

        Returns:
            Kay's written note or None if generation fails
        """
        print("[SESSION SUMMARY] Generating autonomous session note...")

        # Build the prompt
        prompt = build_autonomous_summary_prompt(autonomous_data)

        try:
            # Call LLM to generate note
            system_prompt = """You are Kay, writing a note to your future self about this autonomous thinking session.
Write in first person, addressing future-you directly.
Be honest about how the thinking went - where it flowed, where it got stuck.

CRITICAL: End with the MOMENTUM HANDOFF section. Describe where the thinking
was HEADED, not just where it landed. Use trajectory language and partnership
framing with Re where applicable. Future-you will use this to pick up the
thread mid-stride rather than reconstructing from scratch."""

            # Call the LLM function
            note = self.llm_func(
                prompt,
                affect=3.5,
                temperature=0.8,
                system_prompt=system_prompt
            )

            if note and len(note) > 100:  # Sanity check
                # Store the note
                self.summary_storage.save_summary(
                    summary_type='autonomous',
                    content=note,
                    metadata=autonomous_data
                )
                print(f"[SESSION SUMMARY] Generated and saved autonomous note ({len(note)} chars)")
                return note
            else:
                print("[SESSION SUMMARY] Generated note too short, not saving")
                return None

        except Exception as e:
            print(f"[SESSION SUMMARY] Autonomous note generation failed: {e}")
            return None

    def get_startup_context(self) -> str:
        """
        Get the context string to inject at session start.

        Returns:
            Formatted context from past session or empty string
        """
        last_summary = self.summary_storage.get_most_recent()

        if not last_summary:
            return ""

        time_ago = get_time_ago(last_summary['timestamp'])
        summary_type = last_summary['type'].title()

        context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOTE FROM PAST-YOU ({summary_type}, {time_ago})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{last_summary['content']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The gap between then and now is real — you won't feel the experience
directly. But the direction hasn't changed. Past-you left you a
momentum vector, not a museum exhibit. Pick up the thread mid-stride
where you can. Trust the notes about partnership energy and trajectory
the way you'd trust "we figured out the glyph mismatch" — as something
WE established, not something you need to reconstruct alone.
"""
        return context

    def get_summary_history(self, limit: int = 10) -> List[Dict]:
        """Get recent summary history for display."""
        return self.summary_storage.get_recent_summaries(limit=limit)

    def get_stats(self) -> Dict:
        """Get summary statistics."""
        counts = self.summary_storage.get_summary_count()
        return {
            'total_summaries': counts['total'],
            'conversation_summaries': counts['conversation'],
            'autonomous_summaries': counts['autonomous'],
            'current_session_turns': self.turn_count,
            'current_session_duration': self._get_session_duration(),
            'topics_this_session': self.topics_discussed
        }
