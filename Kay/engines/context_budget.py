# engines/context_budget.py
"""
CONTEXT BUDGET MANAGEMENT

Prevents context bloat that causes:
- Hallucinations (Kay responding to old recalled content)
- Token drain ($0.08/turn, 11+ second response times)
- Attention collapse (85K chars by turn 6)

This module provides:
1. Adaptive limits based on current context size
2. Image lifecycle tracking (2-turn aging)
3. Token estimation and monitoring
4. Priority-based content trimming
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import math

# Import config values if available
try:
    from config import (
        BASE_MEMORY_LIMIT as CONFIG_MEMORY_LIMIT,
        BASE_RAG_LIMIT as CONFIG_RAG_LIMIT,
        BASE_WORKING_TURNS as CONFIG_WORKING_TURNS,
        IMAGE_AGING_TURNS as CONFIG_IMAGE_AGING
    )
except ImportError:
    CONFIG_MEMORY_LIMIT = 100
    CONFIG_RAG_LIMIT = 20
    CONFIG_WORKING_TURNS = 3
    CONFIG_IMAGE_AGING = 2


@dataclass
class ContextBudget:
    """
    Defines adaptive limits based on current context size.
    All limits are adjusted dynamically based on token estimates.
    """
    # Token thresholds (chars / 4 ≈ tokens)
    NORMAL_THRESHOLD = 10000  # <10K tokens = normal limits
    REDUCED_THRESHOLD = 15000  # 10-15K tokens = reduced limits
    MINIMAL_THRESHOLD = 20000  # 15-20K tokens = minimal limits
    CRITICAL_THRESHOLD = 25000  # >20K tokens = critical warning, strip aggressively

    # Base limits (NORMAL tier) - from config
    BASE_MEMORY_LIMIT = CONFIG_MEMORY_LIMIT
    BASE_RAG_LIMIT = CONFIG_RAG_LIMIT
    BASE_WORKING_TURNS = CONFIG_WORKING_TURNS

    # Reduced limits (when images present OR context 10-15K)
    REDUCED_MEMORY_LIMIT = CONFIG_MEMORY_LIMIT // 2  # 50% of base
    REDUCED_RAG_LIMIT = CONFIG_RAG_LIMIT // 2
    REDUCED_WORKING_TURNS = max(2, CONFIG_WORKING_TURNS - 1)

    # Minimal limits (context 15-20K)
    MINIMAL_MEMORY_LIMIT = CONFIG_MEMORY_LIMIT // 3  # 33% of base
    MINIMAL_RAG_LIMIT = max(5, CONFIG_RAG_LIMIT // 4)
    MINIMAL_WORKING_TURNS = 2

    # Critical limits (context >20K)
    CRITICAL_MEMORY_LIMIT = max(20, CONFIG_MEMORY_LIMIT // 5)  # 20% of base
    CRITICAL_RAG_LIMIT = 0  # Strip RAG entirely
    CRITICAL_WORKING_TURNS = 1


@dataclass
class ImageState:
    """Tracks an image's lifecycle in context."""
    image_id: str
    attached_turn: int
    last_mentioned_turn: int
    description: str = ""
    is_active: bool = True  # In active context
    is_archived: bool = False  # Moved to gallery


@dataclass
class ContextMetrics:
    """Metrics about current context state."""
    total_chars: int = 0
    estimated_tokens: int = 0
    memory_count: int = 0
    rag_chunk_count: int = 0
    working_turn_count: int = 0
    image_count: int = 0
    tier: str = "normal"
    warnings: List[str] = field(default_factory=list)

    def to_log_string(self) -> str:
        """Format metrics for logging."""
        return (
            f"[CONTEXT SIZE] {self.estimated_tokens:,} tokens (~{self.total_chars:,} chars) | "
            f"Tier: {self.tier.upper()} | "
            f"Memories: {self.memory_count}, RAG: {self.rag_chunk_count}, "
            f"Turns: {self.working_turn_count}, Images: {self.image_count}"
        )


class ContextBudgetManager:
    """
    Manages context budget with adaptive limits and image lifecycle.

    Usage:
        budget_manager = ContextBudgetManager()

        # At start of turn
        limits = budget_manager.get_adaptive_limits(current_context_chars, has_images=True)

        # Track images
        budget_manager.track_image("img_123", turn_number, "architecture diagram")
        budget_manager.update_image_mentions("img_123", turn_number)

        # Get active images (for inclusion in context)
        active_images = budget_manager.get_active_images(current_turn)
    """

    def __init__(self):
        self.budget = ContextBudget()
        self.image_states: Dict[str, ImageState] = {}
        self.metrics_history: List[ContextMetrics] = []
        self._image_aging_turns = CONFIG_IMAGE_AGING  # Images age out after N turns of no mention

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from character count (chars/4 is rough approximation)."""
        if not text:
            return 0
        return len(text) // 4

    def get_context_tier(self, token_count: int, has_images: bool = False) -> str:
        """
        Determine the context tier based on token count.
        Images automatically bump us down one tier.
        """
        # Images present = start at reduced tier
        effective_tokens = token_count
        if has_images:
            effective_tokens += 5000  # Treat images as +5K tokens for budgeting

        if effective_tokens >= self.budget.CRITICAL_THRESHOLD:
            return "critical"
        elif effective_tokens >= self.budget.MINIMAL_THRESHOLD:
            return "minimal"
        elif effective_tokens >= self.budget.REDUCED_THRESHOLD:
            return "reduced"
        else:
            return "normal"

    def get_adaptive_limits(
        self,
        current_context_chars: int = 0,
        has_images: bool = False,
        force_tier: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get adaptive limits based on current context size.

        Args:
            current_context_chars: Current context size in characters
            has_images: Whether images are present in context
            force_tier: Override tier detection (for testing)

        Returns:
            Dict with keys: memory_limit, rag_limit, working_turns
        """
        token_estimate = self.estimate_tokens(str(current_context_chars) if isinstance(current_context_chars, int) else current_context_chars)
        if isinstance(current_context_chars, int):
            token_estimate = current_context_chars // 4

        tier = force_tier or self.get_context_tier(token_estimate, has_images)

        if tier == "critical":
            return {
                "memory_limit": self.budget.CRITICAL_MEMORY_LIMIT,
                "rag_limit": self.budget.CRITICAL_RAG_LIMIT,
                "working_turns": self.budget.CRITICAL_WORKING_TURNS,
                "tier": tier,
                "warning": f"CRITICAL: Context at {token_estimate:,} tokens. Stripping aggressively."
            }
        elif tier == "minimal":
            return {
                "memory_limit": self.budget.MINIMAL_MEMORY_LIMIT,
                "rag_limit": self.budget.MINIMAL_RAG_LIMIT,
                "working_turns": self.budget.MINIMAL_WORKING_TURNS,
                "tier": tier,
                "warning": f"Context at {token_estimate:,} tokens. Using minimal limits."
            }
        elif tier == "reduced":
            return {
                "memory_limit": self.budget.REDUCED_MEMORY_LIMIT,
                "rag_limit": self.budget.REDUCED_RAG_LIMIT,
                "working_turns": self.budget.REDUCED_WORKING_TURNS,
                "tier": tier,
                "warning": None
            }
        else:  # normal
            return {
                "memory_limit": self.budget.BASE_MEMORY_LIMIT,
                "rag_limit": self.budget.BASE_RAG_LIMIT,
                "working_turns": self.budget.BASE_WORKING_TURNS,
                "tier": tier,
                "warning": None
            }

    # =========================================================================
    # IMAGE LIFECYCLE MANAGEMENT
    # =========================================================================

    def track_image(self, image_id: str, turn_number: int, description: str = "") -> None:
        """
        Track a new image attached to the conversation.

        Args:
            image_id: Unique identifier for the image
            turn_number: Turn when image was attached
            description: Optional description of the image
        """
        self.image_states[image_id] = ImageState(
            image_id=image_id,
            attached_turn=turn_number,
            last_mentioned_turn=turn_number,
            description=description,
            is_active=True,
            is_archived=False
        )
        print(f"[IMAGE LIFECYCLE] Tracked new image: {image_id} (turn {turn_number})")

    def update_image_mention(self, image_id: str, turn_number: int) -> None:
        """
        Update last mention turn for an image.
        Call this when user or Kay references an image.
        """
        if image_id in self.image_states:
            self.image_states[image_id].last_mentioned_turn = turn_number
            # Re-activate if it was archived
            if self.image_states[image_id].is_archived:
                self.image_states[image_id].is_archived = False
                self.image_states[image_id].is_active = True
                print(f"[IMAGE LIFECYCLE] Re-activated image: {image_id}")

    def age_images(self, current_turn: int) -> List[str]:
        """
        Age out images that haven't been mentioned recently.
        Returns list of image IDs that were archived.

        Should be called at end of each turn.
        """
        archived = []

        for image_id, state in self.image_states.items():
            if not state.is_active:
                continue

            turns_since_mention = current_turn - state.last_mentioned_turn

            if turns_since_mention >= self._image_aging_turns:
                state.is_active = False
                state.is_archived = True
                archived.append(image_id)
                print(f"[IMAGE LIFECYCLE] Archived image: {image_id} ({turns_since_mention} turns since last mention)")

        return archived

    def get_active_images(self, current_turn: int) -> List[ImageState]:
        """
        Get images that should be in active context.

        Returns images that:
        - Were attached recently (within 2 turns)
        - OR were explicitly mentioned recently
        """
        active = []
        for state in self.image_states.values():
            if state.is_active and not state.is_archived:
                active.append(state)
        return active

    def get_archived_images(self) -> List[ImageState]:
        """Get images that have been moved to gallery (available but not in context)."""
        return [s for s in self.image_states.values() if s.is_archived]

    def format_image_status(self, current_turn: int) -> str:
        """
        Format image status for inclusion in prompt.
        Shows active images with age indicators.
        """
        active = self.get_active_images(current_turn)
        archived = self.get_archived_images()

        if not active and not archived:
            return ""

        lines = []

        if active:
            lines.append("--- Active Images (Currently in Context) ---")
            for img in active:
                turns_ago = current_turn - img.attached_turn
                if turns_ago == 0:
                    age_note = "attached THIS turn"
                elif turns_ago == 1:
                    age_note = "attached 1 turn ago"
                else:
                    age_note = f"attached {turns_ago} turns ago"

                desc = f" - {img.description}" if img.description else ""
                lines.append(f"[ACTIVE IMAGE] {img.image_id} ({age_note}){desc}")

        if archived:
            lines.append(f"\n[Gallery: {len(archived)} images from earlier - available if Re references them]")

        return "\n".join(lines)

    # =========================================================================
    # CONTEXT METRICS AND MONITORING
    # =========================================================================

    def measure_context(
        self,
        memories: List[Dict],
        rag_chunks: List[Dict],
        working_turns: List[Dict],
        images: List[Any],
        other_context: str = ""
    ) -> ContextMetrics:
        """
        Measure current context and return metrics.

        Args:
            memories: Retrieved memories list
            rag_chunks: RAG document chunks
            working_turns: Recent conversation turns
            images: Active images
            other_context: Any other context strings

        Returns:
            ContextMetrics with full breakdown
        """
        # Estimate sizes
        memory_chars = sum(len(str(m)) for m in memories)
        rag_chars = sum(len(str(c)) for c in rag_chunks)
        turn_chars = sum(len(str(t)) for t in working_turns)
        image_chars = len(images) * 1000  # Rough estimate for image descriptions
        other_chars = len(other_context)

        total_chars = memory_chars + rag_chars + turn_chars + image_chars + other_chars
        estimated_tokens = total_chars // 4

        # Determine tier
        tier = self.get_context_tier(estimated_tokens, has_images=len(images) > 0)

        # Build warnings
        warnings = []
        if tier == "critical":
            warnings.append(f"CRITICAL: Context at {estimated_tokens:,} tokens - attention collapse likely")
        elif tier == "minimal":
            warnings.append(f"WARNING: Context at {estimated_tokens:,} tokens - reduced retrieval active")

        if len(memories) > 100:
            warnings.append(f"High memory count: {len(memories)} memories (target: <100)")

        if len(rag_chunks) > 20:
            warnings.append(f"High RAG count: {len(rag_chunks)} chunks (target: <20)")

        metrics = ContextMetrics(
            total_chars=total_chars,
            estimated_tokens=estimated_tokens,
            memory_count=len(memories),
            rag_chunk_count=len(rag_chunks),
            working_turn_count=len(working_turns),
            image_count=len(images),
            tier=tier,
            warnings=warnings
        )

        # Store in history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:
            self.metrics_history.pop(0)

        return metrics

    def log_context_state(self, metrics: ContextMetrics) -> None:
        """Log context state with appropriate warning level."""
        log_line = metrics.to_log_string()
        print(log_line)

        for warning in metrics.warnings:
            print(f"[CONTEXT WARNING] {warning}")

    def get_trimming_recommendations(
        self,
        metrics: ContextMetrics,
        has_images: bool = False
    ) -> Dict[str, Any]:
        """
        Get recommendations for trimming context to fit budget.

        Returns dict with recommended counts and what to trim.
        """
        limits = self.get_adaptive_limits(
            metrics.total_chars,
            has_images=has_images
        )

        recs = {
            "should_trim_memories": metrics.memory_count > limits["memory_limit"],
            "should_trim_rag": metrics.rag_chunk_count > limits["rag_limit"],
            "should_trim_turns": metrics.working_turn_count > limits["working_turns"],
            "target_memory_count": limits["memory_limit"],
            "target_rag_count": limits["rag_limit"],
            "target_turn_count": limits["working_turns"],
            "tier": limits["tier"],
            "trim_memories_by": max(0, metrics.memory_count - limits["memory_limit"]),
            "trim_rag_by": max(0, metrics.rag_chunk_count - limits["rag_limit"]),
            "trim_turns_by": max(0, metrics.working_turn_count - limits["working_turns"])
        }

        return recs


# =============================================================================
# PRIORITY-BASED MEMORY TRIMMING
# =============================================================================

def prioritize_memories(
    memories: List[Dict],
    limit: int,
    current_turn: int = 0
) -> List[Dict]:
    """
    Trim memories to limit using priority-based selection.

    Priority order:
    1. Working layer memories (most recent)
    2. Identity facts (always important)
    3. Recent episodic memories
    4. High-importance semantic memories
    5. Everything else

    Args:
        memories: Full list of retrieved memories
        limit: Target count
        current_turn: Current turn number for recency calculation

    Returns:
        Prioritized and trimmed memory list
    """
    if len(memories) <= limit:
        return memories

    # Categorize memories
    working = []
    identity = []
    episodic = []
    semantic = []
    other = []

    for mem in memories:
        layer = mem.get("layer", "")
        mem_type = mem.get("type", "")
        is_identity = mem.get("is_identity", False) or mem.get("topic") in [
            "identity", "appearance", "name", "core_preferences", "relationships"
        ]

        if layer == "working":
            working.append(mem)
        elif is_identity:
            identity.append(mem)
        elif mem_type == "full_turn":
            episodic.append(mem)
        elif layer == "semantic" or mem_type == "extracted_fact":
            semantic.append(mem)
        else:
            other.append(mem)

    # Sort each category by importance/recency
    def sort_key(m):
        importance = m.get("importance", 0.5)
        recency = 1.0 / (1 + (current_turn - m.get("turn_index", 0)))
        return importance * 0.6 + recency * 0.4

    working.sort(key=sort_key, reverse=True)
    identity.sort(key=sort_key, reverse=True)
    episodic.sort(key=sort_key, reverse=True)
    semantic.sort(key=sort_key, reverse=True)
    other.sort(key=sort_key, reverse=True)

    # Assemble in priority order up to limit
    result = []
    remaining = limit

    # Always include working memories first
    take_working = min(len(working), remaining)
    result.extend(working[:take_working])
    remaining -= take_working

    # Then identity facts
    take_identity = min(len(identity), remaining)
    result.extend(identity[:take_identity])
    remaining -= take_identity

    # Then recent episodic
    take_episodic = min(len(episodic), remaining // 2)  # Cap at half remaining
    result.extend(episodic[:take_episodic])
    remaining -= take_episodic

    # Then semantic
    take_semantic = min(len(semantic), remaining)
    result.extend(semantic[:take_semantic])
    remaining -= take_semantic

    # Finally other
    if remaining > 0:
        result.extend(other[:remaining])

    print(f"[MEMORY TRIM] {len(memories)} -> {len(result)} memories "
          f"(working:{take_working}, identity:{take_identity}, "
          f"episodic:{take_episodic}, semantic:{take_semantic})")

    return result


def prioritize_rag_chunks(
    chunks: List[Dict],
    limit: int,
    query: str = ""
) -> List[Dict]:
    """
    Trim RAG chunks to limit using relevance scoring.

    Args:
        chunks: Full list of RAG chunks
        limit: Target count
        query: Current user query for relevance scoring

    Returns:
        Prioritized and trimmed chunk list
    """
    if len(chunks) <= limit:
        return chunks

    # Score each chunk
    query_words = set(query.lower().split()) if query else set()

    def score_chunk(chunk):
        text = chunk.get("text", "").lower()

        # Distance score (from vector search)
        distance = chunk.get("distance", 1.0)
        distance_score = 1.0 - min(distance, 1.0)

        # Query relevance (keyword overlap)
        if query_words:
            chunk_words = set(text.split())
            overlap = len(query_words & chunk_words)
            relevance_score = overlap / len(query_words)
        else:
            relevance_score = 0.5

        # Combine scores
        return distance_score * 0.6 + relevance_score * 0.4

    # Sort by score and take top N
    scored = [(score_chunk(c), c) for c in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)

    result = [c for _, c in scored[:limit]]
    print(f"[RAG TRIM] {len(chunks)} -> {len(result)} chunks")

    return result


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global instance for easy access
_budget_manager: Optional[ContextBudgetManager] = None

def get_budget_manager() -> ContextBudgetManager:
    """Get or create the global budget manager instance."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = ContextBudgetManager()
    return _budget_manager
