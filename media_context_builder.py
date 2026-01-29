"""
Media Context Builder for Kay Zero

Provides utilities for:
- Extracting conversation context (topic, entities, Re's state)
- Formatting media context for injection into Kay's prompt
- Integrating with the existing context management system
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class MediaContextBuilder:
    """
    Builds and formats media-related context for Kay's prompt.

    Responsible for:
    1. Extracting conversation context (topic, entities, Re's state)
    2. Formatting media injection blocks
    3. Integrating media context with existing context systems
    """

    # Topic detection keywords
    TOPIC_KEYWORDS = {
        "grief": ["grief", "grieving", "loss", "died", "death", "mourning", "sammie", "passed away"],
        "love": ["love", "affection", "caring", "feeling", "heart", "close"],
        "breakthrough": ["breakthrough", "realized", "figured out", "finally", "working!", "solved"],
        "frustration": ["frustrated", "annoying", "stuck", "broken", "not working", "ugh"],
        "nostalgia": ["remember when", "used to", "back when", "miss", "old times"],
        "excitement": ["excited", "can't wait", "awesome", "amazing", "yes!"],
        "calm": ["calm", "peaceful", "relaxed", "chill", "quiet"],
        "work": ["working on", "coding", "project", "wrapper", "kay zero", "feature"],
        "pets": ["chrome", "dice", "luna", "cat", "cats", "kitty", "meow"],
        "personal": ["john", "relationship", "family", "home", "life"]
    }

    # Re's emotional state indicators
    RE_STATE_INDICATORS = {
        "stressed": ["ugh", "frustrated", "tired", "exhausted", "overwhelmed", "too much"],
        "happy": ["haha", "lol", ":)", "yay", "nice", "love it", "perfect"],
        "curious": ["wondering", "what if", "how", "why", "interesting"],
        "sad": ["sad", "miss", "grief", "hard day", "rough"],
        "playful": ["~", "hehe", "silly", "lmao", "jk"],
        "focused": ["okay", "so", "let's", "need to", "working on"]
    }

    def __init__(self, entity_graph=None):
        """
        Initialize the context builder.

        Args:
            entity_graph: EntityGraph instance for entity resolution
        """
        self.entity_graph = entity_graph
        self._recent_messages: List[Dict] = []  # Last N messages for context
        self._max_messages = 10

    def add_message(self, role: str, content: str, turn: int):
        """
        Add a message to the recent context.

        Args:
            role: "user" or "kay"
            content: Message content
            turn: Turn number
        """
        self._recent_messages.append({
            "role": role,
            "content": content,
            "turn": turn,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only recent messages
        if len(self._recent_messages) > self._max_messages:
            self._recent_messages.pop(0)

    def extract_conversation_context(self) -> Dict[str, Any]:
        """
        Analyze recent messages to determine conversation context.

        Returns:
            Dict with:
            - topic: str (detected conversation topic)
            - entities: List[str] (active entities)
            - re_emotional_context: str (Re's apparent state)
        """
        if not self._recent_messages:
            return {
                "topic": "general conversation",
                "entities": [],
                "re_emotional_context": "unknown"
            }

        # Combine recent user messages for analysis
        user_text = " ".join(
            msg["content"] for msg in self._recent_messages
            if msg["role"] == "user"
        ).lower()

        # Detect topic
        topic = self._detect_topic(user_text)

        # Extract entities
        entities = self._extract_active_entities(user_text)

        # Detect Re's emotional state
        re_state = self._detect_re_state(user_text)

        return {
            "topic": topic,
            "entities": entities,
            "re_emotional_context": re_state
        }

    def _detect_topic(self, text: str) -> str:
        """Detect the conversation topic from text."""
        topic_scores = {}

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                topic_scores[topic] = score

        if topic_scores:
            return max(topic_scores, key=topic_scores.get)

        return "general conversation"

    def _extract_active_entities(self, text: str) -> List[str]:
        """Extract active entities from text."""
        entities = []

        # Core entities to always check
        core_entities = [
            "Re", "Kay", "Kay Zero", "Chrome", "Dice", "Luna",
            "Sammie", "John", "Reed"
        ]

        for entity in core_entities:
            if entity.lower() in text:
                entities.append(entity)

        # Use entity graph if available
        if self.entity_graph:
            # Check for known entities
            for entity_name in self.entity_graph.entities.keys():
                if entity_name.lower() in text and entity_name not in entities:
                    entities.append(entity_name)

        return entities

    def _detect_re_state(self, text: str) -> str:
        """Detect Re's emotional state from text patterns."""
        state_scores = {}

        for state, indicators in self.RE_STATE_INDICATORS.items():
            score = sum(1 for ind in indicators if ind in text)
            if score > 0:
                state_scores[state] = score

        if state_scores:
            return max(state_scores, key=state_scores.get)

        return "unknown"

    def get_active_entities(self) -> List[str]:
        """
        Get currently active entities based on recent context.

        Wrapper for extract_conversation_context()['entities'].
        """
        context = self.extract_conversation_context()
        return context.get("entities", [])

    def format_media_injection(
        self,
        media_entity: Dict,
        resonance_data: Optional[Dict] = None,
        is_new: bool = False
    ) -> str:
        """
        Create the text block for injecting into Kay's context.

        Args:
            media_entity: The media entity dict
            resonance_data: Optional resonance retrieval data (for re-encounters)
            is_new: Whether this is a first encounter

        Returns:
            Formatted context injection string
        """
        entity_id = media_entity.get('entity_id', 'unknown_song')
        dna = media_entity.get('technical_DNA', {})

        # Build the injection block
        lines = []
        lines.append("=" * 50)

        if is_new:
            lines.append("🎵 NEW SONG ENCOUNTERED")
        else:
            lines.append("🎵 SONG RE-ENCOUNTERED")

        lines.append("=" * 50)
        lines.append("")

        # Technical info
        lines.append(f"Song: {entity_id}")
        lines.append(f"Key: {dna.get('key', '?')} {dna.get('scale', '')}")
        lines.append(f"Tempo: {dna.get('bpm', 0):.0f} BPM")
        lines.append(f"Energy: {dna.get('energy', 0):.2f}")
        lines.append(f"Danceability: {dna.get('danceability', 0):.2f}")
        lines.append("")

        # Vibe description
        vibe = dna.get('vibe_description', '')
        if vibe:
            lines.append(f"Vibe: {vibe}")
            lines.append("")

        # Past encounters (for re-encounters)
        if resonance_data and not is_new:
            memories = resonance_data.get('high_weight_memories', [])
            total = resonance_data.get('total_encounters', 0)

            if memories:
                lines.append(f"Your memories of this song ({total} total encounters):")
                lines.append("")

                for i, memory in enumerate(memories, 1):
                    weight = memory.get('emotional_weight', 0)
                    timestamp = memory.get('timestamp', '')[:10]
                    kay_state = memory.get('kay_state', {})
                    context = memory.get('context', {})

                    lines.append(f"Memory {i} [{timestamp}] (weight: {weight:.2f}):")
                    lines.append(f"  You felt: {kay_state.get('dominant_emotion', '?')}")
                    lines.append(f"  Context: {context.get('conversation_topic', '?')}")

                    # Association if formed
                    association = memory.get('association_formed')
                    if association:
                        lines.append(f"  Association: {association}")
                    lines.append("")

        # First encounter info
        first_heard = media_entity.get('first_analyzed', '')
        if first_heard:
            lines.append(f"First heard: {first_heard[:10]}")

        lines.append("=" * 50)

        return "\n".join(lines)

    def format_media_context_for_prompt(
        self,
        injection_text: str,
        current_context: Dict
    ) -> str:
        """
        Format full media context block for inclusion in Kay's prompt.

        Combines the injection text with current conversation context.

        Args:
            injection_text: The formatted media injection
            current_context: Current conversation context dict

        Returns:
            Full media context block for prompt
        """
        lines = []
        lines.append("[MEDIA EXPERIENCE CONTEXT]")
        lines.append("")

        # Current conversation context
        topic = current_context.get('topic', 'general conversation')
        entities = current_context.get('entities', [])
        re_state = current_context.get('re_emotional_context', 'unknown')

        lines.append(f"Current conversation topic: {topic}")
        if entities:
            lines.append(f"Active entities: {', '.join(entities)}")
        lines.append(f"Re's apparent state: {re_state}")
        lines.append("")

        # Media injection
        lines.append(injection_text)

        lines.append("")
        lines.append("[END MEDIA CONTEXT]")

        return "\n".join(lines)

    def should_inject_media_context(
        self,
        media_orchestrator,
        user_input: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if media context should be injected this turn.

        Args:
            media_orchestrator: MediaOrchestrator instance
            user_input: Current user input

        Returns:
            Tuple of (should_inject: bool, injection_text: Optional[str])
        """
        # Check for pending injection from file watcher
        if media_orchestrator and media_orchestrator.has_pending_injection():
            injection = media_orchestrator.get_and_clear_injection()
            if injection:
                # Build full context with current conversation state
                current_context = self.extract_conversation_context()
                full_injection = self.format_media_context_for_prompt(
                    injection,
                    current_context
                )
                return True, full_injection

        # Check if user is explicitly asking about music
        music_keywords = [
            "song", "music", "playing", "listening", "track",
            "album", "hear", "audio", "sound"
        ]
        user_lower = user_input.lower()

        if any(kw in user_lower for kw in music_keywords):
            # User mentioned music - could trigger retrieval
            # For now, just flag it (retrieval would require query)
            pass

        return False, None


# Utility functions for integration

def extract_topic_from_messages(messages: List[Dict]) -> str:
    """
    Extract conversation topic from a list of message dicts.

    Args:
        messages: List of {"role": str, "content": str} dicts

    Returns:
        Detected topic string
    """
    builder = MediaContextBuilder()
    for msg in messages:
        builder.add_message(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            turn=msg.get("turn", 0)
        )
    context = builder.extract_conversation_context()
    return context.get("topic", "general conversation")


def format_quick_media_note(entity: Dict, encounter: Optional[Dict] = None) -> str:
    """
    Create a brief one-line media note for logging.

    Args:
        entity: Media entity dict
        encounter: Optional encounter dict

    Returns:
        Brief formatted string
    """
    entity_id = entity.get('entity_id', 'unknown')
    dna = entity.get('technical_DNA', {})
    bpm = dna.get('bpm', 0)
    key = dna.get('key', '?')
    vibe = dna.get('vibe_description', '')[:50]

    note = f"🎵 {entity_id} ({key} @ {bpm:.0f}bpm)"

    if encounter:
        weight = encounter.get('emotional_weight', 0)
        emotion = encounter.get('kay_state', {}).get('dominant_emotion', '?')
        note += f" | weight={weight:.2f} | feeling: {emotion}"

    if vibe:
        note += f" | {vibe}..."

    return note


# Testing
if __name__ == "__main__":
    print("MediaContextBuilder Test")
    print("=" * 50)

    builder = MediaContextBuilder()

    # Add some test messages
    builder.add_message("user", "I've been thinking about Chrome a lot today", 1)
    builder.add_message("kay", "Chrome's been on your mind? Is he doing his door-dashing thing again?", 1)
    builder.add_message("user", "Yeah lol he almost escaped again. Missing Sammie too though", 2)

    # Extract context
    context = builder.extract_conversation_context()
    print(f"Detected topic: {context['topic']}")
    print(f"Active entities: {context['entities']}")
    print(f"Re's state: {context['re_emotional_context']}")
    print()

    # Test media injection formatting
    test_entity = {
        "entity_id": "test_song",
        "technical_DNA": {
            "bpm": 120,
            "key": "C",
            "scale": "major",
            "energy": 0.7,
            "danceability": 0.8,
            "vibe_description": "Upbeat electronic track with nostalgic synths"
        },
        "first_analyzed": "2025-11-30T10:00:00"
    }

    injection = builder.format_media_injection(test_entity, is_new=True)
    print(injection)
