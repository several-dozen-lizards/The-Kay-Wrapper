"""
Session Loader
Loads previous sessions into current memory context for Kay to review
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class SessionLoader:
    """
    Converts saved sessions into episodic memories that can be loaded into
    Kay's current context for review
    """

    def __init__(self, memory_engine=None):
        """
        Args:
            memory_engine: MemoryEngine instance for storing episodic memories
        """
        self.memory_engine = memory_engine

    def load_session_for_review(
        self,
        session_data: Dict[str, Any],
        current_turn: int,
        compression_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Convert session into episodic memories for Kay to review

        Args:
            session_data: Full session data dict
            current_turn: Current turn number (for memory metadata)
            compression_level: "low", "medium", or "high"
                - low: Store every turn as separate memory
                - medium: Store summary + important turns
                - high: Store only summary

        Returns:
            List of memory dicts ready to be added to memory system
        """

        memories = []

        conversation = session_data.get("conversation", [])
        metadata = session_data.get("metadata", {})
        session_id = session_data.get("session_id", "unknown")

        # Session summary memory (always included)
        summary_memory = self._create_summary_memory(
            session_data,
            current_turn
        )
        memories.append(summary_memory)

        if compression_level == "high":
            # Only summary
            return memories

        elif compression_level == "medium":
            # Summary + important moments
            important_moments = metadata.get("important_moments", [])

            for moment in important_moments:
                turn_idx = moment.get("turn_index")
                if turn_idx is not None and turn_idx < len(conversation):
                    turn = conversation[turn_idx]
                    memory = self._create_turn_memory(
                        turn,
                        turn_idx,
                        session_id,
                        current_turn,
                        is_important=True
                    )
                    memories.append(memory)

            # If no important moments flagged, use key turns
            if not important_moments:
                key_turns = self._select_key_turns(conversation, max_turns=5)
                for turn_idx in key_turns:
                    memory = self._create_turn_memory(
                        conversation[turn_idx],
                        turn_idx,
                        session_id,
                        current_turn,
                        is_important=True
                    )
                    memories.append(memory)

        else:  # low compression
            # Store every turn
            for idx, turn in enumerate(conversation):
                memory = self._create_turn_memory(
                    turn,
                    idx,
                    session_id,
                    current_turn,
                    is_important=False
                )
                memories.append(memory)

        return memories

    def _create_summary_memory(
        self,
        session_data: Dict[str, Any],
        current_turn: int
    ) -> Dict[str, Any]:
        """Create memory for session summary"""

        metadata = session_data.get("metadata", {})
        session_id = session_data.get("session_id", "unknown")
        start_time = session_data.get("start_time", "")

        # Build summary text
        summary_parts = []

        if metadata.get("title"):
            summary_parts.append(f"Session: {metadata['title']}")

        if start_time:
            try:
                dt = datetime.fromisoformat(start_time)
                date_str = dt.strftime("%B %d, %Y")
                summary_parts.append(f"Date: {date_str}")
            except ValueError:
                pass

        if metadata.get("summary"):
            summary_parts.append(f"\n{metadata['summary']}")

        if metadata.get("key_topics"):
            topics = ", ".join(metadata['key_topics'])
            summary_parts.append(f"\nTopics discussed: {topics}")

        if metadata.get("emotional_arc"):
            summary_parts.append(f"Emotional arc: {metadata['emotional_arc']}")

        content = "\n".join(summary_parts)

        return {
            "content": content,
            "perspective": "shared",
            "importance": 0.8,  # High importance
            "layer": "episodic",
            "turn": current_turn,
            "timestamp": datetime.now().isoformat(),
            "source": "session_review",
            "session_id": session_id,
            "review_type": "summary",
            "entities": metadata.get("key_topics", []),
            "emotional_tags": self._extract_emotional_tags(metadata.get("emotional_arc", ""))
        }

    def _create_turn_memory(
        self,
        turn: Dict[str, str],
        turn_idx: int,
        session_id: str,
        current_turn: int,
        is_important: bool
    ) -> Dict[str, Any]:
        """Create memory for individual turn"""

        role = turn.get("role", "unknown")
        content = turn.get("content", "")

        # Format content with context
        if role == "user":
            formatted_content = f"[Past session] User said: {content}"
            perspective = "user"
        else:
            formatted_content = f"[Past session] I said: {content}"
            perspective = "kay"

        importance = 0.7 if is_important else 0.5

        return {
            "content": formatted_content,
            "perspective": perspective,
            "importance": importance,
            "layer": "episodic",
            "turn": current_turn,
            "timestamp": datetime.now().isoformat(),
            "source": "session_review",
            "session_id": session_id,
            "original_turn_index": turn_idx,
            "review_type": "turn",
            "is_important": is_important
        }

    def _select_key_turns(
        self,
        conversation: List[Dict[str, str]],
        max_turns: int = 5
    ) -> List[int]:
        """
        Select key turns from conversation using heuristics

        Returns:
            List of turn indices
        """

        key_turns = []

        # Always include first and last
        if len(conversation) > 0:
            key_turns.append(0)
        if len(conversation) > 1:
            key_turns.append(len(conversation) - 1)

        # Score middle turns
        scores = []
        for idx in range(1, len(conversation) - 1):
            turn = conversation[idx]
            content = turn.get("content", "")

            score = 0

            # Long messages
            if len(content) > 200:
                score += 2

            # Questions
            if "?" in content:
                score += 1

            # Emotional indicators
            emotional_words = {"realize", "understand", "feel", "important", "interesting"}
            if any(word in content.lower() for word in emotional_words):
                score += 1

            scores.append((idx, score))

        # Sort by score and take top N
        scores.sort(key=lambda x: x[1], reverse=True)
        key_turns.extend([idx for idx, score in scores[:max_turns - 2]])

        # Sort by index
        key_turns.sort()

        return key_turns

    def _extract_emotional_tags(self, emotional_arc: str) -> List[str]:
        """Extract emotion tags from emotional arc string"""

        if not emotional_arc:
            return []

        # Split on " -> " and clean
        emotions = emotional_arc.replace("->", " ").split()
        return [e.strip().lower() for e in emotions if len(e.strip()) > 2]

    def create_review_summary_for_prompt(
        self,
        session_data: Dict[str, Any]
    ) -> str:
        """
        Create a formatted summary for injecting into LLM prompt

        Use this when you want Kay to be aware of a past session without
        storing it as memories

        Args:
            session_data: Full session data

        Returns:
            Formatted string for LLM context
        """

        metadata = session_data.get("metadata", {})
        conversation = session_data.get("conversation", [])

        lines = []

        lines.append("=== PAST SESSION FOR REVIEW ===")

        if metadata.get("title"):
            lines.append(f"Session: {metadata['title']}")

        start_time = session_data.get("start_time", "")
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time)
                date_str = dt.strftime("%B %d, %Y at %H:%M")
                lines.append(f"Date: {date_str}")
            except ValueError:
                pass

        if metadata.get("summary"):
            lines.append(f"\nSummary: {metadata['summary']}")

        if metadata.get("key_topics"):
            topics = ", ".join(metadata['key_topics'])
            lines.append(f"Topics: {topics}")

        if metadata.get("emotional_arc"):
            lines.append(f"Emotional Arc: {metadata['emotional_arc']}")

        # Include important moments
        important_moments = metadata.get("important_moments", [])
        if important_moments:
            lines.append("\nKey Moments:")
            for moment in important_moments[:5]:
                role = "User" if moment["role"] == "user" else "You"
                lines.append(f"  • {role}: {moment['preview']}")

        # Include first and last exchanges
        lines.append("\nFirst Exchange:")
        if len(conversation) > 0:
            first_user = next((t for t in conversation if t["role"] == "user"), None)
            if first_user:
                lines.append(f"  User: {first_user['content'][:150]}...")

        if len(conversation) > 2:
            lines.append("\nLast Exchange:")
            last_turns = conversation[-2:]
            for turn in last_turns:
                role = "User" if turn["role"] == "user" else "You"
                content = turn['content'][:150]
                if len(turn['content']) > 150:
                    content += "..."
                lines.append(f"  {role}: {content}")

        lines.append("=" * 50)

        return "\n".join(lines)

    def load_multiple_sessions_for_review(
        self,
        session_data_list: List[Dict[str, Any]],
        current_turn: int,
        max_total_memories: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Load multiple sessions for review with memory budget

        Args:
            session_data_list: List of session data dicts
            current_turn: Current turn number
            max_total_memories: Maximum total memories to create

        Returns:
            List of memories from all sessions (prioritized)
        """

        all_memories = []

        # Budget per session
        budget_per_session = max(3, max_total_memories // len(session_data_list))

        for session_data in session_data_list:
            # Use high compression for multiple sessions
            memories = self.load_session_for_review(
                session_data,
                current_turn,
                compression_level="high"
            )

            # Limit to budget
            all_memories.extend(memories[:budget_per_session])

        # Sort by importance
        all_memories.sort(key=lambda m: m.get("importance", 0), reverse=True)

        return all_memories[:max_total_memories]

    def integrate_with_memory_engine(
        self,
        session_data: Dict[str, Any],
        current_turn: int,
        compression_level: str = "medium"
    ) -> int:
        """
        Load session directly into memory engine

        Args:
            session_data: Session data to load
            current_turn: Current turn
            compression_level: Compression level

        Returns:
            Number of memories added
        """

        if not self.memory_engine:
            raise ValueError("No memory engine configured")

        memories = self.load_session_for_review(
            session_data,
            current_turn,
            compression_level
        )

        # Add to memory engine directly
        count = 0
        for memory in memories:
            # Ensure required fields for memory engine compatibility
            memory_record = {
                "type": "session_review",
                "content": memory["content"],
                "perspective": memory.get("perspective", "shared"),
                "importance_score": memory.get("importance", 0.5),
                "timestamp": memory.get("timestamp", datetime.now().isoformat()),
                "current_layer": memory.get("layer", "episodic"),
                "source": memory.get("source", "session_review"),
                "session_id": memory.get("session_id", "unknown"),
                "entities": memory.get("entities", []),
                "emotion_tags": memory.get("emotional_tags", []),
            }

            # Add directly to memory engine's memory list
            self.memory_engine.memories.append(memory_record)

            # Add to appropriate memory layer
            target_layer = memory.get("layer", "episodic")
            if hasattr(self.memory_engine, 'memory_layers') and self.memory_engine.memory_layers:
                self.memory_engine.memory_layers.add_memory(memory_record, layer=target_layer)

            count += 1

        # Save to disk
        if hasattr(self.memory_engine, '_save_to_disk'):
            self.memory_engine._save_to_disk()

        return count

    def get_session_reference_string(
        self,
        session_data: Dict[str, Any]
    ) -> str:
        """
        Generate short reference string for session

        Useful for logging or quick identification

        Returns:
            String like "Nov 17, 2024: Memory Architecture Discussion (12 turns)"
        """

        metadata = session_data.get("metadata", {})
        start_time = session_data.get("start_time", "")

        parts = []

        if start_time:
            try:
                dt = datetime.fromisoformat(start_time)
                parts.append(dt.strftime("%b %d, %Y"))
            except ValueError:
                pass

        if metadata.get("title"):
            parts.append(metadata["title"])

        turn_count = metadata.get("turn_count", 0)
        if turn_count:
            parts.append(f"({turn_count} turns)")

        return ": ".join(parts) if parts else "Unknown Session"
