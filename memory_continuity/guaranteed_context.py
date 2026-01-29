"""
Guaranteed Context Loader
Ensures specific memory types always load at session start regardless of retrieval scoring
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GuaranteedMemory:
    """
    Memory that must be loaded regardless of retrieval score
    """
    memory_id: str
    content: str
    metadata: Dict[str, Any]
    reason: str  # Why this memory is guaranteed (for debugging)
    priority: int  # 1-5, higher = more important


class GuaranteedContextLoader:
    """
    Manages guaranteed memory loading at session start and during conversation
    """

    def __init__(self, chroma_collection):
        """
        Args:
            chroma_collection: ChromaDB collection instance
        """
        self.collection = chroma_collection

    def load_session_start_context(
        self,
        session_summary: Optional[Any],  # SessionSummary from session_boundary.py
        current_turn: int,
        entity_graph,
        max_guaranteed: int = 50
    ) -> List[GuaranteedMemory]:
        """
        Load guaranteed memories at session start

        This ensures critical context loads before any retrieval scoring

        Args:
            session_summary: Previous session summary (if exists)
            current_turn: Current turn number
            entity_graph: Entity graph for core identity
            max_guaranteed: Maximum guaranteed memories to load

        Returns:
            List of GuaranteedMemory objects to inject into context
        """

        guaranteed = []

        # 1. Last session exchange (highest priority)
        if session_summary:
            guaranteed.extend(
                self._load_last_exchange(session_summary, priority=5)
            )

        # 2. Recent reactions (from last session)
        if session_summary:
            guaranteed.extend(
                self._load_session_reactions(session_summary, priority=4)
            )

        # 3. Active thread summaries
        if session_summary and hasattr(session_summary, "open_threads"):
            guaranteed.extend(
                self._load_thread_summaries(session_summary, priority=4)
            )

        # 4. Core identity/preferences
        guaranteed.extend(
            self._load_core_identity(entity_graph, priority=3)
        )

        # 5. Very recent memories (last 5 turns if continuing session)
        if current_turn > 0:
            guaranteed.extend(
                self._load_recent_working_memory(current_turn, priority=4)
            )

        # 6. Import reactions from last session
        if session_summary and hasattr(session_summary, "import_reactions"):
            guaranteed.extend(
                self._load_import_reactions(session_summary, priority=3)
            )

        # Sort by priority (highest first) and limit
        guaranteed.sort(key=lambda m: m.priority, reverse=True)

        return guaranteed[:max_guaranteed]

    def _load_last_exchange(
        self,
        session_summary,
        priority: int
    ) -> List[GuaranteedMemory]:
        """
        Load the last conversation exchange from previous session
        """

        # Create synthetic memories from session summary
        # (These may not exist as actual stored memories)

        memories = []

        if hasattr(session_summary, "last_user_message") and session_summary.last_user_message:
            memories.append(GuaranteedMemory(
                memory_id="session_last_user",
                content=session_summary.last_user_message,
                metadata={
                    "type": "user_message",
                    "layer": "working",
                    "session_id": session_summary.session_id,
                    "timestamp": session_summary.timestamp
                },
                reason="Last user message from previous session",
                priority=priority
            ))

        if hasattr(session_summary, "last_agent_response") and session_summary.last_agent_response:
            memories.append(GuaranteedMemory(
                memory_id="session_last_agent",
                content=session_summary.last_agent_response,
                metadata={
                    "type": "agent_response",
                    "layer": "working",
                    "session_id": session_summary.session_id,
                    "timestamp": session_summary.timestamp
                },
                reason="Last agent response from previous session",
                priority=priority
            ))

        return memories

    def _load_session_reactions(
        self,
        session_summary,
        priority: int,
        max_reactions: int = 5
    ) -> List[GuaranteedMemory]:
        """
        Load key reactions from previous session
        """

        if not hasattr(session_summary, "key_reactions"):
            return []

        memories = []

        for idx, reaction in enumerate(session_summary.key_reactions[:max_reactions]):
            content = f"{reaction['trigger']} → {reaction['reaction']}"

            memories.append(GuaranteedMemory(
                memory_id=f"session_reaction_{idx}",
                content=content,
                metadata={
                    "type": "reaction",
                    "layer": "episodic",
                    "trigger": reaction["trigger"],
                    "reaction": reaction["reaction"],
                    "timestamp": reaction.get("timestamp", session_summary.timestamp)
                },
                reason="Key reaction from previous session",
                priority=priority
            ))

        return memories

    def _load_thread_summaries(
        self,
        session_summary,
        priority: int,
        max_threads: int = 3
    ) -> List[GuaranteedMemory]:
        """
        Load active thread summaries from previous session
        """

        memories = []

        for idx, thread in enumerate(session_summary.open_threads[:max_threads]):
            # Create summary of thread
            entities_str = ", ".join(thread["entities"][:3])
            summary = f"Active thread: {entities_str}"

            if thread.get("open_questions"):
                summary += f" | Open question: {thread['open_questions'][0]}"

            memories.append(GuaranteedMemory(
                memory_id=f"thread_summary_{thread['thread_id']}",
                content=summary,
                metadata={
                    "type": "thread_summary",
                    "layer": "episodic",
                    "thread_id": thread["thread_id"],
                    "entities": thread["entities"],
                    "momentum": thread.get("momentum", 0.0)
                },
                reason="Active conversation thread from previous session",
                priority=priority
            ))

        return memories

    def _load_core_identity(
        self,
        entity_graph,
        priority: int,
        max_preferences: int = 5
    ) -> List[GuaranteedMemory]:
        """
        Load core identity preferences
        """

        if not entity_graph:
            return []

        memories = []

        # Get top stable preferences
        try:
            top_prefs = entity_graph.get_top_preferences(limit=max_preferences)

            for idx, pref in enumerate(top_prefs):
                memories.append(GuaranteedMemory(
                    memory_id=f"core_pref_{idx}",
                    content=pref.get("description", str(pref)),
                    metadata={
                        "type": "core_preference",
                        "layer": "semantic",
                        "stability": pref.get("stability", 1.0)
                    },
                    reason="Core identity preference",
                    priority=priority
                ))
        except (AttributeError, TypeError):
            # Fallback if entity_graph doesn't have get_top_preferences
            pass

        return memories

    def _load_recent_working_memory(
        self,
        current_turn: int,
        priority: int,
        lookback_turns: int = 5
    ) -> List[GuaranteedMemory]:
        """
        Load very recent working memories
        """

        # Query for memories from last N turns
        results = self.collection.get(
            where={
                "$and": [
                    {"layer": "working"},
                    {"turn": {"$gte": current_turn - lookback_turns}}
                ]
            },
            include=["documents", "metadatas"]
        )

        memories = []

        for idx in range(len(results["ids"])):
            memories.append(GuaranteedMemory(
                memory_id=results["ids"][idx],
                content=results["documents"][idx],
                metadata=results["metadatas"][idx],
                reason=f"Recent working memory (turn {results['metadatas'][idx].get('turn', '?')})",
                priority=priority
            ))

        return memories

    def _load_import_reactions(
        self,
        session_summary,
        priority: int,
        max_imports: int = 3
    ) -> List[GuaranteedMemory]:
        """
        Load reactions to imported documents from previous session
        """

        if not hasattr(session_summary, "import_reactions"):
            return []

        memories = []

        for import_id, reaction in list(session_summary.import_reactions.items())[:max_imports]:
            memories.append(GuaranteedMemory(
                memory_id=f"import_reaction_{import_id}",
                content=reaction,
                metadata={
                    "type": "import_reaction",
                    "layer": "episodic",
                    "import_id": import_id
                },
                reason="Import reaction from previous session",
                priority=priority
            ))

        return memories

    def load_turn_guaranteed_context(
        self,
        current_turn: int,
        user_input: str,
        thread_tracker,
        emotional_state: Dict[str, float]
    ) -> List[GuaranteedMemory]:
        """
        Load guaranteed memories for current turn (not just session start)

        Args:
            current_turn: Current turn
            user_input: User's current message
            thread_tracker: ThreadMomentumTracker instance
            emotional_state: Current emotional state

        Returns:
            Guaranteed memories for this specific turn
        """

        guaranteed = []

        # 1. High-momentum thread memories
        if thread_tracker:
            active_threads = thread_tracker.get_active_threads()
            for thread in active_threads[:2]:  # Top 2 threads
                if thread.momentum_score(current_turn) > 0.7:
                    # Load most recent memories from this thread
                    thread_memories = self._load_thread_memories(
                        thread,
                        max_memories=3,
                        priority=4
                    )
                    guaranteed.extend(thread_memories)

        # 2. Emotionally resonant memories if strong emotion
        strong_emotions = {
            emotion: intensity
            for emotion, intensity in emotional_state.items()
            if intensity > 0.7
        }

        if strong_emotions:
            resonant = self._load_emotionally_resonant(
                strong_emotions,
                max_memories=3,
                priority=3
            )
            guaranteed.extend(resonant)

        # 3. Unresolved questions
        if thread_tracker:
            all_questions = []
            for thread in thread_tracker.get_active_threads():
                all_questions.extend(thread.open_questions)

            if all_questions:
                question_memories = self._load_question_context(
                    all_questions[:3],
                    priority=3
                )
                guaranteed.extend(question_memories)

        return guaranteed

    def _load_thread_memories(
        self,
        thread,
        max_memories: int,
        priority: int
    ) -> List[GuaranteedMemory]:
        """
        Load memories associated with a specific thread
        """

        # Get memories by IDs
        if not thread.related_memory_ids:
            return []

        # Get most recent ones
        memory_ids = thread.related_memory_ids[-max_memories:]

        try:
            results = self.collection.get(
                ids=memory_ids,
                include=["documents", "metadatas"]
            )

            memories = []
            for idx in range(len(results["ids"])):
                memories.append(GuaranteedMemory(
                    memory_id=results["ids"][idx],
                    content=results["documents"][idx],
                    metadata=results["metadatas"][idx],
                    reason=f"High-momentum thread: {thread.thread_id}",
                    priority=priority
                ))

            return memories
        except Exception:
            return []

    def _load_emotionally_resonant(
        self,
        strong_emotions: Dict[str, float],
        max_memories: int,
        priority: int
    ) -> List[GuaranteedMemory]:
        """
        Load memories that resonate with current strong emotions
        """

        emotion_tags = list(strong_emotions.keys())

        # Query for memories with matching emotional tags
        results = self.collection.get(
            where={
                "emotional_tags": {"$in": emotion_tags}
            },
            include=["documents", "metadatas"],
            limit=max_memories
        )

        memories = []

        for idx in range(len(results["ids"])):
            memories.append(GuaranteedMemory(
                memory_id=results["ids"][idx],
                content=results["documents"][idx],
                metadata=results["metadatas"][idx],
                reason=f"Emotionally resonant ({', '.join(emotion_tags[:2])})",
                priority=priority
            ))

        return memories

    def _load_question_context(
        self,
        open_questions: List[str],
        priority: int
    ) -> List[GuaranteedMemory]:
        """
        Load context for unresolved questions
        """

        # Create synthetic memories for tracking questions
        memories = []

        for idx, question in enumerate(open_questions):
            memories.append(GuaranteedMemory(
                memory_id=f"unresolved_q_{idx}",
                content=f"Unresolved question: {question}",
                metadata={
                    "type": "unresolved_question",
                    "layer": "working"
                },
                reason="Unresolved question from active thread",
                priority=priority
            ))

        return memories

    def convert_to_retrieval_format(
        self,
        guaranteed_memories: List[GuaranteedMemory]
    ) -> List[Dict[str, Any]]:
        """
        Convert GuaranteedMemory objects to standard retrieval format

        Returns:
            List of memory dicts compatible with LayeredMemoryRetriever
        """

        converted = []

        for gm in guaranteed_memories:
            converted.append({
                "id": gm.memory_id,
                "content": gm.content,
                "metadata": gm.metadata,
                "layer": gm.metadata.get("layer", "episodic"),
                "final_score": 10.0 + gm.priority,  # Guarantee high score
                "age": 0,
                "guaranteed": True,
                "guarantee_reason": gm.reason
            })

        return converted

    def merge_with_retrieved(
        self,
        guaranteed_memories: List[GuaranteedMemory],
        retrieved_memories: List[Dict[str, Any]],
        max_total: int = 225
    ) -> List[Dict[str, Any]]:
        """
        Merge guaranteed memories with retrieved memories

        Guaranteed memories are inserted at top, then filled with retrieved

        Args:
            guaranteed_memories: Guaranteed memories to include
            retrieved_memories: Memories from normal retrieval
            max_total: Maximum total memories to return

        Returns:
            Merged list of memories
        """

        # Convert guaranteed to retrieval format
        guaranteed_formatted = self.convert_to_retrieval_format(guaranteed_memories)

        # Get IDs of guaranteed memories
        guaranteed_ids = set(gm.memory_id for gm in guaranteed_memories)

        # Filter retrieved to exclude duplicates
        filtered_retrieved = [
            m for m in retrieved_memories
            if m["id"] not in guaranteed_ids
        ]

        # Combine: guaranteed first, then retrieved
        merged = guaranteed_formatted + filtered_retrieved

        # Limit to max_total
        return merged[:max_total]

    def get_guaranteed_summary(
        self,
        guaranteed_memories: List[GuaranteedMemory]
    ) -> str:
        """
        Generate human-readable summary of guaranteed memories

        Useful for debugging/transparency

        Returns:
            Formatted summary string
        """

        if not guaranteed_memories:
            return "No guaranteed memories loaded."

        summary_parts = [f"Loaded {len(guaranteed_memories)} guaranteed memories:\n"]

        # Group by reason
        by_reason = {}
        for gm in guaranteed_memories:
            by_reason.setdefault(gm.reason, []).append(gm)

        for reason, memories in by_reason.items():
            summary_parts.append(f"\n{reason} ({len(memories)}):")
            for gm in memories[:3]:  # Show first 3 of each type
                preview = gm.content[:80] + "..." if len(gm.content) > 80 else gm.content
                summary_parts.append(f"  - {preview}")

            if len(memories) > 3:
                summary_parts.append(f"  ... and {len(memories) - 3} more")

        return "\n".join(summary_parts)
