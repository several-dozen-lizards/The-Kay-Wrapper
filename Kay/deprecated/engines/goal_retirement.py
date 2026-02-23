"""
Goal Retirement System

Automatically marks inactive goals as "dormant" to reduce contradiction count.

PROBLEM:
    Kay mentions goal "learn to code" in turn 5
    Never mentioned again for 100+ turns
    System still considers it an "active" goal
    If Kay mentions conflicting goal, system flags contradiction

SOLUTION:
    Goals not mentioned in N turns (default: 10) marked as "dormant"
    Dormant goals:
        - Still stored in memory
        - Excluded from contradiction checking
        - Can be reactivated if mentioned again
        - Marked with retirement metadata
"""

from typing import List, Dict, Any, Set, Optional
from datetime import datetime, timezone


class GoalRetirementManager:
    """
    Manages goal lifecycle: active → dormant → reactivated.

    Goals are tracked memories with specific markers:
    - is_goal: True
    - goal_status: 'active' | 'dormant' | 'completed' | 'abandoned'
    - last_mentioned_turn: int
    - retirement_turn: Optional[int]
    - retirement_reason: Optional[str]
    """

    def __init__(self,
                 memory_engine,
                 dormancy_threshold: int = 10,
                 mention_window: int = 5):
        """
        Initialize goal retirement manager.

        Args:
            memory_engine: Reference to MemoryEngine
            dormancy_threshold: Turns without mention before dormancy (default: 10)
            mention_window: Turns to check for recent mentions (default: 5)
        """
        self.memory_engine = memory_engine
        self.dormancy_threshold = dormancy_threshold
        self.mention_window = mention_window

    def check_goal_activity(self, current_turn: int, user_input: str = "",
                           entity_response: str = "") -> Dict[str, Any]:
        """
        Check all goals for activity and update status.

        Args:
            current_turn: Current turn number
            user_input: User's message (to detect goal mentions)
            entity_response: Entity's response (to detect goal mentions)

        Returns:
            Dict with retirement statistics
        """
        print(f"\n[GOAL RETIREMENT] Checking goal activity (turn {current_turn})...")

        # Get all goal memories
        goals = self._get_all_goals()

        if not goals:
            print("[GOAL RETIREMENT] No goals found")
            return {
                'total_goals': 0,
                'active': 0,
                'dormant': 0,
                'newly_dormant': 0,
                'reactivated': 0
            }

        # Combine conversation text for mention detection
        conversation_text = f"{user_input} {entity_response}".lower()

        newly_dormant = []
        reactivated = []
        active_count = 0
        dormant_count = 0

        for goal in goals:
            # Extract goal text for matching
            goal_text = self._extract_goal_description(goal)
            goal_keywords = self._extract_goal_keywords(goal_text)

            # Check if goal mentioned in current conversation
            mentioned = self._is_goal_mentioned(goal_keywords, conversation_text)

            if mentioned:
                # Update last mentioned turn
                goal['last_mentioned_turn'] = current_turn

                # Reactivate if was dormant
                if goal.get('goal_status') == 'dormant':
                    goal['goal_status'] = 'active'
                    goal['reactivation_turn'] = current_turn
                    reactivated.append(goal)
                    print(f"[GOAL RETIREMENT]   Reactivated: {goal_text[:60]}")

            # Check for dormancy
            last_mentioned = goal.get('last_mentioned_turn', goal.get('turn_index', 0))
            turns_inactive = current_turn - last_mentioned

            current_status = goal.get('goal_status', 'active')

            if current_status == 'active' and turns_inactive >= self.dormancy_threshold:
                # Mark as dormant
                goal['goal_status'] = 'dormant'
                goal['retirement_turn'] = current_turn
                goal['retirement_reason'] = f"Not mentioned for {turns_inactive} turns"
                newly_dormant.append(goal)
                print(f"[GOAL RETIREMENT]   Marked dormant: {goal_text[:60]}")
                print(f"[GOAL RETIREMENT]     Inactive for {turns_inactive} turns")

            # Count current status
            if goal.get('goal_status') == 'dormant':
                dormant_count += 1
            else:
                active_count += 1

        # Save changes
        if newly_dormant or reactivated:
            self.memory_engine.save_memories()

        stats = {
            'total_goals': len(goals),
            'active': active_count,
            'dormant': dormant_count,
            'newly_dormant': len(newly_dormant),
            'reactivated': len(reactivated)
        }

        print(f"[GOAL RETIREMENT] Active: {active_count}, Dormant: {dormant_count}")
        if newly_dormant:
            print(f"[GOAL RETIREMENT] Newly dormant: {len(newly_dormant)}")
        if reactivated:
            print(f"[GOAL RETIREMENT] Reactivated: {len(reactivated)}")

        return stats

    def get_active_goals_only(self) -> List[Dict[str, Any]]:
        """
        Get only active goals (excludes dormant).

        Returns:
            List of active goal memories
        """
        goals = self._get_all_goals()
        active = [
            g for g in goals
            if g.get('goal_status', 'active') == 'active'
        ]
        return active

    def mark_goal_completed(self, goal_id: str, completion_turn: int) -> bool:
        """
        Mark a goal as completed (different from dormant).

        Args:
            goal_id: ID of goal to mark completed
            completion_turn: Turn when completed

        Returns:
            True if successful
        """
        goal = self._find_goal_by_id(goal_id)

        if not goal:
            print(f"[GOAL RETIREMENT] Goal not found: {goal_id}")
            return False

        goal['goal_status'] = 'completed'
        goal['completion_turn'] = completion_turn
        goal['last_mentioned_turn'] = completion_turn

        goal_text = self._extract_goal_description(goal)
        print(f"[GOAL RETIREMENT] Marked completed: {goal_text[:60]}")

        self.memory_engine.save_memories()
        return True

    def mark_goal_abandoned(self, goal_id: str, abandonment_turn: int,
                           reason: str = "Explicitly abandoned") -> bool:
        """
        Mark a goal as explicitly abandoned.

        Args:
            goal_id: ID of goal to mark abandoned
            abandonment_turn: Turn when abandoned
            reason: Reason for abandonment

        Returns:
            True if successful
        """
        goal = self._find_goal_by_id(goal_id)

        if not goal:
            print(f"[GOAL RETIREMENT] Goal not found: {goal_id}")
            return False

        goal['goal_status'] = 'abandoned'
        goal['abandonment_turn'] = abandonment_turn
        goal['abandonment_reason'] = reason

        goal_text = self._extract_goal_description(goal)
        print(f"[GOAL RETIREMENT] Marked abandoned: {goal_text[:60]}")
        print(f"[GOAL RETIREMENT]   Reason: {reason}")

        self.memory_engine.save_memories()
        return True

    def get_goal_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive goal statistics.

        Returns:
            Dict with goal statistics
        """
        goals = self._get_all_goals()

        stats = {
            'total_goals': len(goals),
            'active': 0,
            'dormant': 0,
            'completed': 0,
            'abandoned': 0,
            'by_category': {}
        }

        for goal in goals:
            status = goal.get('goal_status', 'active')

            if status == 'active':
                stats['active'] += 1
            elif status == 'dormant':
                stats['dormant'] += 1
            elif status == 'completed':
                stats['completed'] += 1
            elif status == 'abandoned':
                stats['abandoned'] += 1

            # Count by category if present
            category = goal.get('goal_category', 'uncategorized')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

        return stats

    def ensure_goal_markers(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure memory has goal tracking fields.

        Args:
            memory: Memory to update

        Returns:
            Memory with goal markers
        """
        if not memory.get('is_goal', False):
            return memory

        # Add default fields
        if 'goal_status' not in memory:
            memory['goal_status'] = 'active'

        if 'last_mentioned_turn' not in memory:
            memory['last_mentioned_turn'] = memory.get('turn_index', 0)

        if 'retirement_turn' not in memory:
            memory['retirement_turn'] = None

        if 'retirement_reason' not in memory:
            memory['retirement_reason'] = None

        if 'reactivation_turn' not in memory:
            memory['reactivation_turn'] = None

        if 'completion_turn' not in memory:
            memory['completion_turn'] = None

        if 'abandonment_turn' not in memory:
            memory['abandonment_turn'] = None

        if 'abandonment_reason' not in memory:
            memory['abandonment_reason'] = None

        return memory

    # Private helper methods

    def _get_all_goals(self) -> List[Dict[str, Any]]:
        """Get all goal memories from memory engine."""
        all_memories = []

        if hasattr(self.memory_engine, 'memory_layers'):
            all_memories.extend(self.memory_engine.memory_layers.working_memory)
            all_memories.extend(self.memory_engine.memory_layers.episodic_memory)
            all_memories.extend(self.memory_engine.memory_layers.semantic_memory)
        else:
            all_memories = self.memory_engine.memories

        # Filter for goals
        goals = [m for m in all_memories if m.get('is_goal', False)]

        return goals

    def _find_goal_by_id(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Find goal by ID."""
        goals = self._get_all_goals()

        for goal in goals:
            if goal.get('memory_id') == goal_id:
                return goal
            # Fallback: check fact/text field
            if goal_id in self._extract_goal_description(goal):
                return goal

        return None

    def _extract_goal_description(self, goal: Dict[str, Any]) -> str:
        """Extract goal description text."""
        text = goal.get('fact', '')
        if not text:
            text = goal.get('text', '')
        if not text:
            text = goal.get('goal_text', '')
        return str(text)

    def _extract_goal_keywords(self, goal_text: str) -> Set[str]:
        """
        Extract keywords from goal for mention detection.

        Args:
            goal_text: Goal description

        Returns:
            Set of keywords
        """
        # Simple keyword extraction
        words = goal_text.lower().split()

        # Remove stopwords
        stopwords = {
            'to', 'a', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'for', 'with',
            'by', 'from', 'as', 'is', 'was', 'are', 'want', 'wants', 'wanted'
        }

        keywords = {w for w in words if len(w) > 3 and w not in stopwords}

        return keywords

    def _is_goal_mentioned(self, goal_keywords: Set[str], conversation_text: str) -> bool:
        """
        Check if goal is mentioned in conversation.

        Args:
            goal_keywords: Keywords from goal
            conversation_text: Conversation text to check

        Returns:
            True if mentioned
        """
        if not goal_keywords:
            return False

        conversation_lower = conversation_text.lower()

        # Check if any keyword appears
        for keyword in goal_keywords:
            if keyword in conversation_lower:
                return True

        return False


def filter_active_goals(goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter goals to only active ones (for contradiction checking).

    Use this to exclude dormant/completed/abandoned goals from
    contradiction detection.

    Args:
        goals: List of goal memories

    Returns:
        Filtered list (only active goals)
    """
    active = [
        g for g in goals
        if g.get('goal_status', 'active') == 'active'
    ]

    return active


def format_goal_report(stats: Dict[str, Any]) -> str:
    """
    Format goal statistics for logging.

    Args:
        stats: Statistics from get_goal_statistics()

    Returns:
        Formatted string
    """
    if stats['total_goals'] == 0:
        return "[GOAL RETIREMENT] No goals tracked"

    lines = [
        f"[GOAL RETIREMENT] Statistics:",
        f"  Total goals: {stats['total_goals']}",
        f"  Active: {stats['active']}",
        f"  Dormant: {stats['dormant']}",
        f"  Completed: {stats['completed']}",
        f"  Abandoned: {stats['abandoned']}"
    ]

    if stats['by_category']:
        lines.append("  By category:")
        for category, count in stats['by_category'].items():
            lines.append(f"    - {category}: {count}")

    return "\n".join(lines)
