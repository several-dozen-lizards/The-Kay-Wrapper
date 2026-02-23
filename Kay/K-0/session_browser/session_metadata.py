"""
Session Metadata Generator
Automatically generates titles, summaries, and metadata for saved sessions
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class SessionMetadata:
    """Metadata for a conversation session"""
    title: str  # 3-5 word summary
    summary: str  # 1-2 sentence summary
    key_topics: List[str]  # Main topics discussed
    emotional_arc: str  # Emotional progression
    important_moments: List[Dict[str, Any]]  # Flagged high-importance turns
    tags: List[str]  # Auto-generated or manual tags
    turn_count: int
    duration_minutes: float
    generated_at: str


class SessionMetadataGenerator:
    """
    Generates metadata for conversation sessions using LLM
    """

    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM client with query() method
        """
        self.llm = llm_client

    async def generate_metadata(
        self,
        conversation: List[Dict[str, str]],
        session_data: Dict[str, Any]
    ) -> SessionMetadata:
        """
        Generate comprehensive metadata for a session

        Args:
            conversation: List of conversation turns
            session_data: Full session data including timestamps, entity state

        Returns:
            SessionMetadata object
        """

        # Calculate basic stats
        turn_count = len(conversation) // 2  # Divide by 2 for user/assistant pairs
        duration = self._calculate_duration(conversation)

        # Generate LLM-based metadata
        title = await self._generate_title(conversation)
        summary = await self._generate_summary(conversation)
        key_topics = await self._extract_topics(conversation)
        emotional_arc = await self._extract_emotional_arc(conversation, session_data)
        important_moments = self._identify_important_moments(conversation)
        tags = self._generate_tags(key_topics, emotional_arc)

        return SessionMetadata(
            title=title,
            summary=summary,
            key_topics=key_topics,
            emotional_arc=emotional_arc,
            important_moments=important_moments,
            tags=tags,
            turn_count=turn_count,
            duration_minutes=duration,
            generated_at=datetime.now().isoformat()
        )

    async def _generate_title(self, conversation: List[Dict[str, str]]) -> str:
        """Generate 3-5 word title for session"""

        # Get conversation sample
        sample = self._get_conversation_sample(conversation, max_turns=10)

        prompt = f"""Generate a concise 3-5 word title for this conversation.

Conversation:
{sample}

Requirements:
- 3-5 words maximum
- Capture the main topic/theme
- Use title case
- Be specific, not generic

Return only the title, nothing else."""

        try:
            response = await self.llm.query(prompt, max_tokens=20, temperature=0.3)
            title = response.strip().strip('"\'')

            # Fallback if response is too long
            if len(title.split()) > 6:
                title = " ".join(title.split()[:5])

            return title
        except Exception as e:
            # Fallback: use first message preview
            first_user_msg = next(
                (msg["content"] for msg in conversation if msg["role"] == "user"),
                "Untitled Session"
            )
            return first_user_msg[:30] + "..." if len(first_user_msg) > 30 else first_user_msg

    async def _generate_summary(self, conversation: List[Dict[str, str]]) -> str:
        """Generate 1-2 sentence summary"""

        sample = self._get_conversation_sample(conversation, max_turns=15)

        prompt = f"""Summarize this conversation in 1-2 clear sentences.

Conversation:
{sample}

Requirements:
- 1-2 sentences maximum
- Capture main topics and outcomes
- Be concise and informative

Return only the summary:"""

        try:
            response = await self.llm.query(prompt, max_tokens=80, temperature=0.3)
            return response.strip()
        except Exception:
            return "Conversation summary unavailable."

    async def _extract_topics(self, conversation: List[Dict[str, str]]) -> List[str]:
        """Extract key topics discussed"""

        sample = self._get_conversation_sample(conversation, max_turns=20)

        prompt = f"""Extract the 3-5 main topics discussed in this conversation.

Conversation:
{sample}

Return as JSON list of topic strings:
["topic1", "topic2", ...]

Requirements:
- 3-5 topics maximum
- Use concise phrases (2-4 words)
- Focus on substantive topics, not small talk

Return only the JSON list:"""

        try:
            response = await self.llm.query(prompt, max_tokens=100, temperature=0.3)
            topics = json.loads(response.strip())
            return topics[:5]  # Limit to 5
        except Exception:
            # Fallback: extract from first few messages
            return self._extract_topics_simple(conversation)

    async def _extract_emotional_arc(
        self,
        conversation: List[Dict[str, str]],
        session_data: Dict[str, Any]
    ) -> str:
        """Extract emotional progression through conversation"""

        # Try to use emotional_state from session data
        emotional_state = session_data.get("emotional_state", {})

        sample = self._get_conversation_sample(conversation, max_turns=15)

        prompt = f"""Describe the emotional arc of this conversation in a brief phrase.

Conversation:
{sample}

Current emotional state: {json.dumps(emotional_state) if emotional_state else "N/A"}

Format: "emotion1 -> emotion2 -> emotion3" (2-4 emotions max)
Examples:
- "curiosity -> understanding"
- "confusion -> frustration -> resolution"
- "interest -> excitement -> satisfaction"

Return only the emotional arc phrase:"""

        try:
            response = await self.llm.query(prompt, max_tokens=30, temperature=0.4)
            return response.strip()
        except Exception:
            # Fallback: use session emotional state if available
            if emotional_state:
                top_emotions = sorted(
                    emotional_state.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:2]
                return " -> ".join([e[0] for e in top_emotions])
            return "neutral"

    def _identify_important_moments(
        self,
        conversation: List[Dict[str, str]],
        threshold: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Identify important moments in conversation

        Uses heuristics:
        - Long messages (>200 chars)
        - Questions asked
        - Emotional indicators
        - New topics introduced
        """

        important = []
        emotional_words = {
            "realize", "understand", "feel", "think", "important",
            "interesting", "surprised", "excited", "concerned"
        }

        for idx, turn in enumerate(conversation):
            content = turn["content"].lower()
            score = 0

            # Long messages
            if len(turn["content"]) > 200:
                score += 1

            # Questions
            if "?" in turn["content"]:
                score += 1

            # Emotional indicators
            if any(word in content for word in emotional_words):
                score += 1

            # First and last turns
            if idx < 2 or idx >= len(conversation) - 2:
                score += 1

            if score >= 2:
                important.append({
                    "turn_index": idx,
                    "role": turn["role"],
                    "preview": turn["content"][:100] + "..." if len(turn["content"]) > 100 else turn["content"],
                    "timestamp": turn.get("timestamp", "")
                })

        # Limit to top N most important
        return important[:threshold]

    def _generate_tags(
        self,
        topics: List[str],
        emotional_arc: str
    ) -> List[str]:
        """Generate tags from topics and emotional arc"""

        tags = []

        # Add topic-based tags
        for topic in topics:
            # Split multi-word topics into individual tags
            words = topic.lower().split()
            tags.extend([w for w in words if len(w) > 3])

        # Add emotion tags
        emotions = emotional_arc.lower().replace("->", " ").split()
        tags.extend([e.strip() for e in emotions if len(e.strip()) > 3])

        # Remove duplicates and limit
        unique_tags = list(set(tags))
        return unique_tags[:8]

    def _calculate_duration(self, conversation: List[Dict[str, str]]) -> float:
        """Calculate session duration in minutes"""

        if len(conversation) < 2:
            return 0.0

        timestamps = [
            turn.get("timestamp")
            for turn in conversation
            if turn.get("timestamp")
        ]

        if len(timestamps) < 2:
            return 0.0

        try:
            start = datetime.fromisoformat(timestamps[0])
            end = datetime.fromisoformat(timestamps[-1])
            duration = (end - start).total_seconds() / 60.0
            return round(duration, 1)
        except (ValueError, TypeError):
            return 0.0

    def _get_conversation_sample(
        self,
        conversation: List[Dict[str, str]],
        max_turns: int = 10
    ) -> str:
        """Get formatted sample of conversation for LLM prompts"""

        # Take first N/2 and last N/2 turns
        half = max_turns // 2
        if len(conversation) <= max_turns:
            sample_turns = conversation
        else:
            sample_turns = conversation[:half] + conversation[-half:]

        formatted = []
        for turn in sample_turns:
            role = "User" if turn["role"] == "user" else "Kay"
            content = turn["content"]
            # Truncate very long messages
            if len(content) > 300:
                content = content[:300] + "..."
            formatted.append(f"{role}: {content}")

        return "\n\n".join(formatted)

    def _extract_topics_simple(self, conversation: List[Dict[str, str]]) -> List[str]:
        """Fallback topic extraction using simple heuristics"""

        # Collect capitalized words and noun phrases
        topics = set()

        for turn in conversation[:10]:  # First 10 turns
            words = turn["content"].split()
            for word in words:
                # Capitalized words (potential topics)
                if word and word[0].isupper() and len(word) > 3:
                    topics.add(word.strip('.,!?;:'))

        return list(topics)[:5]

    def update_metadata(
        self,
        existing_metadata: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update existing metadata with new information

        Args:
            existing_metadata: Current metadata dict
            updates: Dict of fields to update

        Returns:
            Updated metadata dict
        """

        metadata = existing_metadata.copy()

        # Update fields
        for key, value in updates.items():
            if key == "tags":
                # Merge tags
                existing_tags = set(metadata.get("tags", []))
                new_tags = set(value)
                metadata["tags"] = list(existing_tags | new_tags)
            elif key == "important_moments":
                # Append new moments
                metadata["important_moments"] = (
                    metadata.get("important_moments", []) + value
                )
            else:
                # Direct update
                metadata[key] = value

        metadata["updated_at"] = datetime.now().isoformat()

        return metadata

    def to_dict(self, metadata: SessionMetadata) -> Dict[str, Any]:
        """Convert SessionMetadata to dict"""
        return asdict(metadata)

    def from_dict(self, data: Dict[str, Any]) -> SessionMetadata:
        """Create SessionMetadata from dict"""
        return SessionMetadata(**data)
