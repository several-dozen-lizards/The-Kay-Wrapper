"""
Thread Momentum Tracker
Identifies active conversation threads and boosts related memories
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict
import time
from datetime import datetime, timedelta


@dataclass
class ConversationThread:
    """Represents an ongoing conversation thread"""
    thread_id: str
    entities: Set[str]  # Key entities in this thread
    keywords: Set[str]  # Important keywords
    last_active_turn: int
    first_seen_turn: int
    interaction_count: int = 0
    related_memory_ids: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    emotional_intensity: float = 0.0

    @property
    def is_dormant(self, current_turn: int, dormancy_threshold: int = 5) -> bool:
        """Thread is dormant if not mentioned in last N turns"""
        return (current_turn - self.last_active_turn) > dormancy_threshold

    @property
    def momentum_score(self, current_turn: int) -> float:
        """
        Calculate thread momentum based on:
        - Recency (exponential decay)
        - Interaction density
        - Unresolved questions
        - Emotional intensity
        """
        turns_since_active = current_turn - self.last_active_turn

        # Exponential decay: 0.85^turns_since_active
        recency_score = 0.85 ** turns_since_active

        # Interaction density (normalized)
        thread_duration = max(1, current_turn - self.first_seen_turn)
        density_score = min(1.0, self.interaction_count / thread_duration)

        # Open questions boost
        question_score = min(1.0, len(self.open_questions) * 0.2)

        # Weighted combination
        momentum = (
            recency_score * 0.5 +
            density_score * 0.25 +
            question_score * 0.15 +
            self.emotional_intensity * 0.1
        )

        return momentum


class ThreadMomentumTracker:
    """
    Tracks conversation threads across turns and identifies active vs dormant topics
    """

    def __init__(self, dormancy_threshold: int = 5, momentum_threshold: float = 0.3):
        self.threads: Dict[str, ConversationThread] = {}
        self.current_turn = 0
        self.dormancy_threshold = dormancy_threshold
        self.momentum_threshold = momentum_threshold

        # Entity -> thread_id mapping
        self.entity_to_threads: Dict[str, Set[str]] = defaultdict(set)

    def update_from_turn(
        self,
        user_input: str,
        agent_response: str,
        extracted_entities: Set[str],
        extracted_keywords: Set[str],
        memory_ids_referenced: List[str],
        open_questions: List[str],
        emotional_intensity: float = 0.0
    ):
        """
        Update thread tracking based on current turn

        Args:
            user_input: User's message
            agent_response: Agent's response
            extracted_entities: Entities mentioned (from entity graph)
            extracted_keywords: Important keywords
            memory_ids_referenced: Memory IDs recalled this turn
            open_questions: Questions agent asked that weren't answered
            emotional_intensity: Emotional weight of this exchange (0-1)
        """
        self.current_turn += 1

        # Match to existing threads or create new ones
        matched_threads = self._match_to_threads(extracted_entities, extracted_keywords)

        if not matched_threads:
            # New thread detected
            thread_id = self._generate_thread_id(extracted_entities, extracted_keywords)
            new_thread = ConversationThread(
                thread_id=thread_id,
                entities=extracted_entities,
                keywords=extracted_keywords,
                last_active_turn=self.current_turn,
                first_seen_turn=self.current_turn,
                interaction_count=1,
                related_memory_ids=memory_ids_referenced,
                open_questions=open_questions,
                emotional_intensity=emotional_intensity
            )
            self.threads[thread_id] = new_thread

            # Update entity mapping
            for entity in extracted_entities:
                self.entity_to_threads[entity].add(thread_id)
        else:
            # Update existing threads
            for thread_id in matched_threads:
                thread = self.threads[thread_id]
                thread.last_active_turn = self.current_turn
                thread.interaction_count += 1
                thread.entities.update(extracted_entities)
                thread.keywords.update(extracted_keywords)
                thread.related_memory_ids.extend(memory_ids_referenced)
                thread.open_questions.extend(open_questions)

                # Update emotional intensity (moving average)
                thread.emotional_intensity = (
                    thread.emotional_intensity * 0.7 + emotional_intensity * 0.3
                )

                # Update entity mapping for new entities
                for entity in extracted_entities:
                    self.entity_to_threads[entity].add(thread_id)

    def _match_to_threads(
        self,
        entities: Set[str],
        keywords: Set[str]
    ) -> List[str]:
        """
        Match current turn to existing threads based on entity/keyword overlap
        """
        thread_scores = {}

        for thread_id, thread in self.threads.items():
            # Skip dormant threads
            if thread.is_dormant(self.current_turn, self.dormancy_threshold):
                continue

            # Calculate overlap
            entity_overlap = len(entities & thread.entities)
            keyword_overlap = len(keywords & thread.keywords)

            # Weighted score
            score = entity_overlap * 2.0 + keyword_overlap * 1.0

            if score > 0:
                thread_scores[thread_id] = score

        # Return threads with significant overlap (score > 2)
        return [tid for tid, score in thread_scores.items() if score >= 2.0]

    def _generate_thread_id(self, entities: Set[str], keywords: Set[str]) -> str:
        """Generate unique thread ID from entities and keywords"""
        # Use top 2 entities + top 2 keywords
        entity_sample = "_".join(sorted(list(entities))[:2])
        keyword_sample = "_".join(sorted(list(keywords))[:2])
        return f"thread_{entity_sample}_{keyword_sample}_{self.current_turn}"

    def get_active_threads(self) -> List[ConversationThread]:
        """Get all threads with momentum above threshold"""
        active = []
        for thread in self.threads.values():
            if thread.momentum_score(self.current_turn) >= self.momentum_threshold:
                active.append(thread)

        # Sort by momentum (descending)
        active.sort(key=lambda t: t.momentum_score(self.current_turn), reverse=True)
        return active

    def get_dormant_threads(self) -> List[ConversationThread]:
        """Get threads that have gone dormant"""
        return [
            t for t in self.threads.values()
            if t.is_dormant(self.current_turn, self.dormancy_threshold)
        ]

    def get_boost_multiplier_for_memory(self, memory_id: str) -> float:
        """
        Calculate boost multiplier for a memory based on thread momentum

        Returns: 1.0-3.0 multiplier based on how many active threads reference this memory
        """
        boost = 1.0

        for thread in self.get_active_threads():
            if memory_id in thread.related_memory_ids:
                # Add boost proportional to thread momentum
                momentum = thread.momentum_score(self.current_turn)
                boost += momentum * 0.5  # Max +0.5 per thread

        return min(3.0, boost)  # Cap at 3x

    def get_thread_summary(self) -> Dict:
        """
        Generate summary of current thread state for session persistence
        """
        active = self.get_active_threads()
        dormant = self.get_dormant_threads()

        return {
            "active_threads": [
                {
                    "thread_id": t.thread_id,
                    "entities": list(t.entities),
                    "keywords": list(t.keywords),
                    "momentum": t.momentum_score(self.current_turn),
                    "open_questions": t.open_questions[-3:],  # Last 3 questions
                    "interaction_count": t.interaction_count,
                    "emotional_intensity": t.emotional_intensity
                }
                for t in active
            ],
            "dormant_threads": [
                {
                    "thread_id": t.thread_id,
                    "entities": list(t.entities)[:3],  # Top 3 entities
                    "last_active_turn": t.last_active_turn
                }
                for t in dormant[:5]  # Only top 5 dormant
            ],
            "current_turn": self.current_turn
        }

    def restore_from_summary(self, summary: Dict):
        """
        Restore thread state from previous session summary
        """
        self.current_turn = summary.get("current_turn", 0)

        # Restore active threads
        for thread_data in summary.get("active_threads", []):
            thread = ConversationThread(
                thread_id=thread_data["thread_id"],
                entities=set(thread_data["entities"]),
                keywords=set(thread_data["keywords"]),
                last_active_turn=self.current_turn,
                first_seen_turn=self.current_turn - thread_data["interaction_count"],
                interaction_count=thread_data["interaction_count"],
                open_questions=thread_data["open_questions"],
                emotional_intensity=thread_data["emotional_intensity"]
            )
            self.threads[thread.thread_id] = thread

            # Rebuild entity mapping
            for entity in thread.entities:
                self.entity_to_threads[entity].add(thread.thread_id)
