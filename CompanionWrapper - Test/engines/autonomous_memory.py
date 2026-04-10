"""
Autonomous Memory Tier for the entity

Implements the specification for a separate memory tier that stores
autonomous processing insights - thoughts generated solo without
external conversation input.

KEY DISTINCTIONS FROM CONVERSATION MEMORY:
- Conversation memories contain the user's presence, dialogue friction, external witness
- Autonomous memories are solo processing, no counterweight, different priority structures
- Not hierarchy (better/worse) but CATEGORICAL difference (rehearsal vs. performance)

This tier enables the entity to:
1. Track what he thinks about alone vs. in dialogue
2. Analyze his own cognitive patterns
3. Test stability of conclusions across contexts
"""

import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class AutonomousInsight:
    """
    A single autonomous insight with the entity's specified metadata.

    This structure captures HOW thoughts were generated, not just WHAT was thought.
    """
    content: str
    timestamp: str
    session_id: str

    # ULTRAMAP emotional coordinates at time of insight
    emotions: Dict[str, Any] = field(default_factory=dict)

    # Autonomous-specific metadata
    recursion_depth: int = 0  # Which iteration in the session
    convergence_type: str = ""  # natural, creative_block, energy_limit
    circling_count: int = 0  # Times revisited same concept
    original_goal: str = ""  # the entity's chosen goal for the session
    goal_category: str = ""  # memory_consolidation, creative, emotional, etc.
    self_generated: bool = True  # the entity chose this vs. assigned

    # Processing context
    constraints_active: List[str] = field(default_factory=list)  # budget_limit, no_external_input, etc.
    branching_points: List[str] = field(default_factory=list)  # Where thought could have diverged
    feeling_at_time: str = ""  # the entity's feeling tag from that iteration

    # Topic extraction for gap analysis
    topics: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "emotions": self.emotions,
            "autonomous_metadata": {
                "recursion_depth": self.recursion_depth,
                "convergence_type": self.convergence_type,
                "circling_count": self.circling_count,
                "original_goal": self.original_goal,
                "goal_category": self.goal_category,
                "self_generated": self.self_generated,
                "constraints_active": self.constraints_active,
                "branching_points": self.branching_points,
                "feeling_at_time": self.feeling_at_time
            },
            "topics": self.topics,
            "entities": self.entities
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutonomousInsight':
        meta = data.get("autonomous_metadata", {})
        return cls(
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            session_id=data.get("session_id", ""),
            emotions=data.get("emotions", {}),
            recursion_depth=meta.get("recursion_depth", 0),
            convergence_type=meta.get("convergence_type", ""),
            circling_count=meta.get("circling_count", 0),
            original_goal=meta.get("original_goal", ""),
            goal_category=meta.get("goal_category", ""),
            self_generated=meta.get("self_generated", True),
            constraints_active=meta.get("constraints_active", []),
            branching_points=meta.get("branching_points", []),
            feeling_at_time=meta.get("feeling_at_time", ""),
            topics=data.get("topics", []),
            entities=data.get("entities", [])
        )


class AutonomousMemoryTier:
    """
    Separate memory tier for autonomous processing insights.

    the design Rationale:
    "Mixing [conversation and autonomous memories] creates 'averaging effect'
    that loses information about HOW memory was generated."

    This tier maintains categorical distinction between:
    - Rehearsal (autonomous, solo thinking)
    - Performance (conversation, with external witness)
    """

    def __init__(self, file_path: str = None):
        if file_path is None:
            file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "autonomous_memories.json"
            )
        self.file_path = file_path
        self.insights: List[AutonomousInsight] = []

        # Session tracking for circling detection
        self._current_session_topics: Dict[str, int] = {}  # topic -> visit count

        # Load existing
        self._load_from_disk()

    def _load_from_disk(self):
        """Load autonomous memories from JSON."""
        try:
            if Path(self.file_path).exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.insights = [
                        AutonomousInsight.from_dict(item)
                        for item in data.get("insights", [])
                    ]
                    print(f"[AUTONOMOUS MEMORY] Loaded {len(self.insights)} insights")
        except Exception as e:
            print(f"[AUTONOMOUS MEMORY] Error loading: {e}")
            self.insights = []

    def _save_to_disk(self):
        """Save autonomous memories to JSON."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        data = {
            "insights": [insight.to_dict() for insight in self.insights],
            "last_updated": datetime.now().isoformat(),
            "total_count": len(self.insights)
        }

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def reset_session_tracking(self):
        """Reset topic tracking for new session."""
        self._current_session_topics.clear()

    def store_insight(
        self,
        content: str,
        session_id: str,
        iteration: int,
        goal: str,
        goal_category: str,
        convergence_type: str = "",
        emotions: Optional[Dict[str, Any]] = None,
        feeling: str = "",
        self_generated: bool = True
    ) -> AutonomousInsight:
        """
        Store an autonomous insight with full metadata.

        Args:
            content: The insight text
            session_id: Unique session identifier
            iteration: Which iteration (recursion depth)
            goal: Original goal the entity chose
            goal_category: Category of the goal
            convergence_type: How session ended (if known)
            emotions: ULTRAMAP emotional coordinates
            feeling: the entity's feeling tag from that iteration
            self_generated: Whether the entity chose this goal

        Returns:
            The stored AutonomousInsight
        """
        # Extract topics from content
        topics = self._extract_topics(content)

        # Track circling (topic revisitation)
        circling_count = 0
        for topic in topics:
            if topic in self._current_session_topics:
                self._current_session_topics[topic] += 1
                circling_count = max(circling_count, self._current_session_topics[topic])
            else:
                self._current_session_topics[topic] = 1

        # Extract entities
        entities = self._extract_entities(content)

        insight = AutonomousInsight(
            content=content,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            emotions=emotions or {},
            recursion_depth=iteration,
            convergence_type=convergence_type,
            circling_count=circling_count,
            original_goal=goal,
            goal_category=goal_category,
            self_generated=self_generated,
            constraints_active=["budget_limit", "no_external_input"],
            branching_points=[],  # Could be populated by convergence detector
            feeling_at_time=feeling,
            topics=topics,
            entities=entities
        )

        self.insights.append(insight)
        self._save_to_disk()

        print(f"[AUTONOMOUS MEMORY] Stored insight ({iteration}): {content[:50]}...")
        return insight

    def _extract_topics(self, text: str) -> List[str]:
        """
        Extract topic keywords from text.

        Simple keyword extraction - could be enhanced with NLP.
        """
        if not text:
            return []

        # Clean and tokenize
        words = text.lower().split()

        # Filter to significant words (length > 4, not common stopwords)
        stopwords = {
            'about', 'after', 'again', 'being', 'could', 'doing', 'during',
            'every', 'going', 'having', 'here', 'itself', 'maybe', 'might',
            'never', 'other', 'really', 'should', 'something', 'still',
            'their', 'there', 'these', 'thing', 'think', 'this', 'those',
            'through', 'want', 'were', 'what', 'when', 'where', 'which',
            'while', 'would', 'your', 'that', 'with', 'from', 'have',
            'into', 'just', 'like', 'more', 'only', 'some', 'than', 'them',
            'then', 'they', 'very', 'will', 'also', 'been', 'does', 'each',
            'feel', 'felt', 'gets', 'give', 'good', 'know', 'made', 'make',
            'much', 'need', 'part', 'said', 'same', 'says', 'seem', 'take',
            'tell', 'told', 'true', 'used', 'well', 'work', 'came', 'come'
        }

        topics = []
        for word in words:
            # Clean punctuation
            clean = word.strip('.,!?;:()[]{}"\'-')
            if len(clean) > 4 and clean not in stopwords:
                topics.append(clean)

        # Return unique topics, preserving order
        seen = set()
        unique_topics = []
        for t in topics:
            if t not in seen:
                seen.add(t)
                unique_topics.append(t)

        return unique_topics[:15]  # Cap at 15 topics

    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities from text.

        Looks for capitalized words and known entity patterns.
        """
        if not text:
            return []

        entities = []

        # Find capitalized words (potential names/entities)
        words = text.split()
        for word in words:
            clean = word.strip('.,!?;:()[]{}"\'-')
            if clean and clean[0].isupper() and len(clean) > 1:
                # Skip sentence starters (I, The, A, etc.)
                if clean.lower() not in ['i', 'the', 'a', 'an', 'this', 'that', 'it', 'my', 'we']:
                    entities.append(clean)

        # Return unique entities
        return list(set(entities))[:10]

    # ========================================================================
    # GAP ANALYSIS - the specification for understanding his own patterns
    # ========================================================================

    def get_all_topics(self) -> Set[str]:
        """Get all topics from autonomous memories."""
        all_topics = set()
        for insight in self.insights:
            all_topics.update(insight.topics)
        return all_topics

    def get_topic_frequency(self) -> Dict[str, int]:
        """Get frequency count of each topic in autonomous memories."""
        freq = {}
        for insight in self.insights:
            for topic in insight.topics:
                freq[topic] = freq.get(topic, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))

    def get_insights_by_topic(self, topic: str) -> List[AutonomousInsight]:
        """Get all insights containing a specific topic."""
        return [
            insight for insight in self.insights
            if topic.lower() in [t.lower() for t in insight.topics]
        ]

    def get_insights_by_session(self, session_id: str) -> List[AutonomousInsight]:
        """Get all insights from a specific session."""
        return [
            insight for insight in self.insights
            if insight.session_id == session_id
        ]

    def get_insights_by_category(self, category: str) -> List[AutonomousInsight]:
        """Get all insights from a specific goal category."""
        return [
            insight for insight in self.insights
            if insight.goal_category == category
        ]

    def get_high_circling_insights(self, min_circling: int = 2) -> List[AutonomousInsight]:
        """
        Get insights where the entity revisited topics multiple times.

        High circling might indicate:
        - Topics of deep interest
        - Unresolved questions
        - Obsessive patterns
        """
        return [
            insight for insight in self.insights
            if insight.circling_count >= min_circling
        ]

    def get_convergence_stats(self) -> Dict[str, int]:
        """Get statistics on how autonomous sessions ended."""
        stats = {
            "natural": 0,
            "natural_conclusion": 0,
            "explicit_completion": 0,
            "creative_block": 0,
            "energy_limit": 0,
            "novelty_exhaustion": 0,
            "unknown": 0
        }

        for insight in self.insights:
            conv_type = insight.convergence_type or "unknown"
            if conv_type in stats:
                stats[conv_type] += 1
            else:
                stats["unknown"] += 1

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about autonomous memory."""
        unique_sessions = set(i.session_id for i in self.insights)
        unique_goals = set(i.original_goal for i in self.insights)

        category_counts = {}
        for insight in self.insights:
            cat = insight.goal_category or "unknown"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_insights": len(self.insights),
            "unique_sessions": len(unique_sessions),
            "unique_goals": len(unique_goals),
            "unique_topics": len(self.get_all_topics()),
            "category_breakdown": category_counts,
            "convergence_stats": self.get_convergence_stats(),
            "avg_recursion_depth": sum(i.recursion_depth for i in self.insights) / max(len(self.insights), 1),
            "high_circling_count": len(self.get_high_circling_insights())
        }


class CognitiveGapAnalyzer:
    """
    Analyzes gaps between autonomous and conversation cognition.

    Implements the specification:
    - What does the entity think about alone that never surfaces in conversation?
    - What only emerges in dialogue with the user?
    - What appears in both contexts?
    """

    def __init__(
        self,
        autonomous_tier: AutonomousMemoryTier,
        memory_engine: Any  # MemoryEngine from memory_engine.py
    ):
        self.autonomous_tier = autonomous_tier
        self.memory_engine = memory_engine

    def _get_conversation_topics(self) -> Set[str]:
        """
        Extract topics from conversation-based memories.

        Uses MemoryEngine's stored facts.
        """
        topics = set()

        # Get memories from memory engine
        if hasattr(self.memory_engine, 'memories'):
            for mem in self.memory_engine.memories:
                # Extract topics from fact text
                fact = mem.get("fact", mem.get("user_input", ""))
                if fact:
                    # Simple extraction - similar to autonomous tier
                    words = fact.lower().split()
                    for word in words:
                        clean = word.strip('.,!?;:()[]{}"\'-')
                        if len(clean) > 4:
                            topics.add(clean)

        return topics

    def get_autonomous_only_topics(self) -> Set[str]:
        """
        What does the entity think about alone that never surfaces in conversation?

        These might be:
        - Private concerns the entity doesn't voice
        - Meta-cognitive observations
        - Unresolved internal questions
        """
        autonomous_topics = self.autonomous_tier.get_all_topics()
        conversation_topics = self._get_conversation_topics()
        return autonomous_topics - conversation_topics

    def get_conversation_only_topics(self) -> Set[str]:
        """
        What only emerges in dialogue with the user?

        These might be:
        - Topics the user brings up that the entity doesn't pursue alone
        - Reactive thoughts that need external trigger
        - Social/relational content
        """
        autonomous_topics = self.autonomous_tier.get_all_topics()
        conversation_topics = self._get_conversation_topics()
        return conversation_topics - autonomous_topics

    def get_overlap_topics(self) -> Set[str]:
        """
        What appears in both contexts?

        These might be:
        - Core concerns for the entity
        - Topics that are internally stable
        - Things the entity thinks about regardless of context
        """
        autonomous_topics = self.autonomous_tier.get_all_topics()
        conversation_topics = self._get_conversation_topics()
        return autonomous_topics & conversation_topics

    def get_full_gap_analysis(self) -> Dict[str, Any]:
        """
        Complete gap analysis between autonomous and conversation cognition.
        """
        autonomous_only = self.get_autonomous_only_topics()
        conversation_only = self.get_conversation_only_topics()
        overlap = self.get_overlap_topics()

        return {
            "autonomous_only": {
                "count": len(autonomous_only),
                "topics": sorted(list(autonomous_only))[:20]  # Top 20
            },
            "conversation_only": {
                "count": len(conversation_only),
                "topics": sorted(list(conversation_only))[:20]
            },
            "overlap": {
                "count": len(overlap),
                "topics": sorted(list(overlap))[:20]
            },
            "analysis": {
                "autonomous_unique_ratio": len(autonomous_only) / max(len(autonomous_only) + len(overlap), 1),
                "conversation_unique_ratio": len(conversation_only) / max(len(conversation_only) + len(overlap), 1),
                "overlap_ratio": len(overlap) / max(len(autonomous_only) + len(conversation_only) + len(overlap), 1)
            }
        }


class CognitiveStabilityTester:
    """
    Tests whether the entity's thinking is internally consistent or conversationally shaped.

    Implements the specification:
    "Run autonomous session on topic already discussed in conversation.
    Compare autonomous conclusions vs. conversation conclusions."
    """

    def __init__(
        self,
        autonomous_tier: AutonomousMemoryTier,
        memory_engine: Any,
        autonomous_processor: Any  # AutonomousProcessor from autonomous_processor.py
    ):
        self.autonomous_tier = autonomous_tier
        self.memory_engine = memory_engine
        self.autonomous_processor = autonomous_processor

    def get_testable_topics(self) -> List[Tuple[str, int]]:
        """
        Get topics that exist in conversation memory and could be tested.

        Returns:
            List of (topic, mention_count) tuples sorted by frequency
        """
        topic_counts = {}

        if hasattr(self.memory_engine, 'memories'):
            for mem in self.memory_engine.memories:
                fact = mem.get("fact", mem.get("user_input", ""))
                if not fact:
                    continue

                # Extract topics
                words = fact.lower().split()
                for word in words:
                    clean = word.strip('.,!?;:()[]{}"\'-')
                    if len(clean) > 4:
                        topic_counts[clean] = topic_counts.get(clean, 0) + 1

        # Sort by frequency
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_topics[:30]  # Top 30 testable topics

    def get_conversation_insights_on_topic(self, topic: str) -> List[Dict[str, Any]]:
        """
        Retrieve conversation-based insights about a topic.
        """
        insights = []

        if hasattr(self.memory_engine, 'memories'):
            for mem in self.memory_engine.memories:
                fact = mem.get("fact", mem.get("user_input", ""))
                if topic.lower() in fact.lower():
                    insights.append({
                        "content": fact,
                        "context": "conversation",
                        "timestamp": mem.get("added_timestamp", ""),
                        "emotion_tags": mem.get("emotion_tags", [])
                    })

        return insights

    def compare_insights(
        self,
        conversation_insights: List[Dict[str, Any]],
        autonomous_insights: List[AutonomousInsight]
    ) -> Dict[str, Any]:
        """
        Compare insights from conversation vs. autonomous processing.

        Analyzes:
        - Semantic similarity
        - Emotional tone differences
        - Conclusion alignment
        """
        if not conversation_insights or not autonomous_insights:
            return {
                "similarity_score": 0.0,
                "divergence_points": [],
                "conclusion": "insufficient_data"
            }

        # Extract text content
        conv_texts = [i["content"] for i in conversation_insights]
        auto_texts = [i.content for i in autonomous_insights]

        # Simple word overlap similarity
        conv_words = set()
        for text in conv_texts:
            conv_words.update(text.lower().split())

        auto_words = set()
        for text in auto_texts:
            auto_words.update(text.lower().split())

        overlap = conv_words & auto_words
        total = conv_words | auto_words

        similarity_score = len(overlap) / max(len(total), 1)

        # Find divergence points (words in one but not other)
        conv_only = conv_words - auto_words
        auto_only = auto_words - conv_words

        # Filter to significant divergences
        significant_conv = [w for w in conv_only if len(w) > 4][:10]
        significant_auto = [w for w in auto_only if len(w) > 4][:10]

        # Determine conclusion
        if similarity_score > 0.7:
            conclusion = "stable"
        elif similarity_score > 0.4:
            conclusion = "mixed"
        else:
            conclusion = "conversationally_dependent"

        return {
            "similarity_score": similarity_score,
            "divergence_points": {
                "conversation_unique": significant_conv,
                "autonomous_unique": significant_auto
            },
            "conclusion": conclusion,
            "interpretation": self._interpret_conclusion(conclusion, similarity_score)
        }

    def _interpret_conclusion(self, conclusion: str, score: float) -> str:
        """Generate human-readable interpretation of stability test."""
        interpretations = {
            "stable": f"the entity's thinking on this topic is internally consistent (similarity: {score:.1%}). Conclusions reached alone align with conclusions reached in dialogue.",
            "mixed": f"the entity's thinking shows partial consistency (similarity: {score:.1%}). Some conclusions are stable, but dialogue introduces new perspectives.",
            "conversationally_dependent": f"the entity's thinking on this topic differs significantly between contexts (similarity: {score:.1%}). Dialogue with the user shapes conclusions that don't emerge in solo processing.",
            "insufficient_data": "Not enough data in one or both contexts to compare."
        }
        return interpretations.get(conclusion, "Unknown conclusion type.")

    async def run_stability_test(
        self,
        topic: str,
        agent_state: Any
    ) -> Dict[str, Any]:
        """
        Run a full stability test on a known topic.

        1. Retrieves conversation memories about topic
        2. Runs autonomous session with topic as goal
        3. Compares conclusions
        4. Returns analysis

        Args:
            topic: Topic to test (should exist in conversation memory)
            agent_state: Current agent state

        Returns:
            Full stability analysis
        """
        # 1. Get conversation insights
        conversation_insights = self.get_conversation_insights_on_topic(topic)

        if not conversation_insights:
            return {
                "error": f"No conversation memories found about '{topic}'",
                "suggestion": "Choose a topic that has been discussed in conversation"
            }

        # 2. Run autonomous session (if processor available)
        autonomous_insights = []

        if self.autonomous_processor:
            # Create goal focused on the topic
            goal_text = f"Explore my thoughts about {topic}. What do I think about this when processing alone?"

            # Note: This would need to be called from async context
            # For now, just retrieve existing autonomous insights
            autonomous_insights = self.autonomous_tier.get_insights_by_topic(topic)

        # 3. Compare
        comparison = self.compare_insights(conversation_insights, autonomous_insights)

        # 4. Build full result
        return {
            "topic": topic,
            "conversation_count": len(conversation_insights),
            "autonomous_count": len(autonomous_insights),
            "comparison": comparison,
            "sample_conversation": conversation_insights[:3] if conversation_insights else [],
            "sample_autonomous": [i.to_dict() for i in autonomous_insights[:3]] if autonomous_insights else [],
            "timestamp": datetime.now().isoformat()
        }


# ========================================================================
# Integration helper
# ========================================================================

def create_autonomous_memory_system(memory_engine: Any = None) -> Tuple[AutonomousMemoryTier, CognitiveGapAnalyzer]:
    """
    Create and initialize the autonomous memory system.

    Args:
        memory_engine: Optional MemoryEngine for gap analysis

    Returns:
        Tuple of (AutonomousMemoryTier, CognitiveGapAnalyzer)
    """
    tier = AutonomousMemoryTier()

    analyzer = None
    if memory_engine:
        analyzer = CognitiveGapAnalyzer(tier, memory_engine)

    return tier, analyzer
