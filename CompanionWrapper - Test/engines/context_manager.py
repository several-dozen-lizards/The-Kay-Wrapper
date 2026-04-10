# engines/context_manager.py
"""
Context Manager with Adaptive Budget Control

Prevents context bloat by:
1. Applying adaptive limits based on token count
2. Tracking image lifecycle (2-turn aging)
3. Prioritizing content for context inclusion
4. Monitoring and logging context state
"""

import time
from typing import Dict, List, Any, Optional
from engines.context_budget import (
    get_budget_manager,
    ContextBudgetManager,
    prioritize_memories,
    prioritize_rag_chunks
)


class ContextManager:
    def __init__(
        self,
        memory_engine,
        summarizer,
        max_context_turns=15,
        momentum_engine=None,
        meta_awareness_engine=None
    ):
        self.memory_engine = memory_engine
        self.summarizer = summarizer
        self.max_context_turns = max_context_turns
        self.momentum_engine = momentum_engine
        self.meta_awareness_engine = meta_awareness_engine
        self.recent_turns = []  # rolling buffer
        self.current_turn = 0

        # NEW: Budget manager for adaptive limits
        self.budget_manager = get_budget_manager()

    def update_turns(self, user_input, reply):
        """Update conversation turns and track current turn number."""
        self.recent_turns.append({"user": user_input, "entity": reply})

        # DYNAMIC TURN LIMIT: Use budget manager instead of hardcoded max_context_turns
        # Calculate current context size to get adaptive limit
        current_context_chars = sum(
            len(str(turn.get("user", ""))) + len(str(turn.get("entity", "")))
            for turn in self.recent_turns
        )
        limits = self.budget_manager.get_adaptive_limits(
            current_context_chars=current_context_chars,
            has_images=len(self.budget_manager.get_active_images(self.current_turn)) > 0
        )
        effective_max_turns = max(limits.get("working_turns", self.max_context_turns), 5)  # Minimum 5

        # Use the more permissive of adaptive limit or configured max
        actual_max = max(effective_max_turns, self.max_context_turns)

        if len(self.recent_turns) > actual_max:
            self.recent_turns.pop(0)
        self.current_turn += 1

        # Age images at end of each turn
        archived = self.budget_manager.age_images(self.current_turn)
        if archived:
            print(f"[IMAGE LIFECYCLE] Archived {len(archived)} images from active context")

    def track_image(self, image_id: str, description: str = "") -> None:
        """
        Track a new image attached to the conversation.
        Call this when an image is uploaded/attached.
        """
        self.budget_manager.track_image(image_id, self.current_turn, description)

    def update_image_mention(self, image_id: str) -> None:
        """
        Update last mention for an image.
        Call this when user or the entity references an image.
        """
        self.budget_manager.update_image_mention(image_id, self.current_turn)

    def get_active_images(self) -> List[Any]:
        """Get images that should be in active context."""
        return self.budget_manager.get_active_images(self.current_turn)

    def get_image_context_block(self) -> str:
        """Get formatted image status for prompt injection."""
        return self.budget_manager.format_image_status(self.current_turn)

    def detect_images_in_text(self, text: str) -> List[str]:
        """
        Detect image references in text.
        Returns list of image IDs that were mentioned.
        """
        mentioned = []
        for image_id in self.budget_manager.image_states.keys():
            # Check for various reference patterns
            if image_id in text:
                mentioned.append(image_id)
            # Also check for generic image references
            if any(pattern in text.lower() for pattern in [
                'the image', 'this image', 'that image',
                'the picture', 'the diagram', 'the screenshot',
                'as shown', 'you can see', 'look at'
            ]):
                # If we have any active images, consider them mentioned
                active = self.budget_manager.get_active_images(self.current_turn)
                for img in active:
                    if img.image_id not in mentioned:
                        mentioned.append(img.image_id)
        return mentioned

    def build_context(self, agent_state, user_input) -> Dict[str, Any]:
        """
        Build context with adaptive budget control.

        This method now:
        1. Measures current context size
        2. Applies adaptive limits based on token count
        3. Prioritizes content for inclusion
        4. Logs context metrics
        """
        # Check for image mentions in user input
        mentioned_images = self.detect_images_in_text(user_input)
        for img_id in mentioned_images:
            self.update_image_mention(img_id)

        # Get current images for budget calculation
        active_images = self.get_active_images()
        has_images = len(active_images) > 0

        # Get RAG chunks from agent state
        rag_chunks = getattr(agent_state, "rag_chunks", [])

        # ===== PHASE 1: Get adaptive limits based on current state =====
        # Estimate current context size (rough, will be refined)
        estimated_chars = len(str(self.recent_turns)) + len(str(rag_chunks))
        limits = self.budget_manager.get_adaptive_limits(
            estimated_chars,
            has_images=has_images
        )

        print(f"[CONTEXT BUDGET] Tier: {limits['tier'].upper()} | "
              f"Memory limit: {limits['memory_limit']}, RAG limit: {limits['rag_limit']}, "
              f"Turn limit: {limits['working_turns']}")

        if limits.get('warning'):
            print(f"[CONTEXT WARNING] {limits['warning']}")

        # ===== PHASE 2: Recall memories with adaptive limit =====
        recalled = self.memory_engine.retrieve_biased_memories(
            agent_state.emotional_cocktail,
            user_input,
            num_memories=limits['memory_limit']
        )

        # Prioritize memories if still over limit
        if len(recalled) > limits['memory_limit']:
            recalled = prioritize_memories(
                recalled,
                limits['memory_limit'],
                current_turn=self.current_turn
            )

        print(f"[CONTEXT] Recalled {len(recalled)} memories (limit: {limits['memory_limit']})")

        # ===== PHASE 3: Apply RAG limits =====
        if rag_chunks:
            if len(rag_chunks) > limits['rag_limit']:
                rag_chunks = prioritize_rag_chunks(
                    rag_chunks,
                    limits['rag_limit'],
                    query=user_input
                )
            print(f"[CONTEXT] RAG chunks: {len(rag_chunks)} (limit: {limits['rag_limit']})")

        # ===== PHASE 4: Apply working memory turn limits =====
        working_turns = self.recent_turns[-limits['working_turns']:] if self.recent_turns else []
        if len(self.recent_turns) > limits['working_turns']:
            print(f"[CONTEXT] Working memory: {len(working_turns)} turns "
                  f"(trimmed from {len(self.recent_turns)}, limit: {limits['working_turns']})")

        facts = self.memory_engine.facts
        summary = self.summarizer.summarize(self.recent_turns)

        # Generate momentum meta-notes if momentum is high
        momentum_notes = []
        if self.momentum_engine and agent_state.momentum > 0.7:
            momentum_notes = self.momentum_engine.get_momentum_context_notes(agent_state)

        # Generate meta-awareness notes if self-monitoring threshold met
        meta_awareness_notes = []
        if self.meta_awareness_engine and self.meta_awareness_engine.should_inject_awareness(agent_state):
            meta_awareness_notes = self.meta_awareness_engine.get_meta_awareness_notes(agent_state)

        # Detect active conversation threads (Flamekeeper integration)
        active_threads = []
        if hasattr(self.memory_engine, 'detect_threads'):
            active_threads = self.memory_engine.detect_threads(recent_turns=15)
            if active_threads:
                print(f"[THREADS] Detected {len(active_threads)} conversation threads:")
                for thread in active_threads[:3]:  # Show top 3
                    print(f"  - {thread['thread_label']} ({thread['thread_status']}, coherence: {thread['thread_coherence']})")

        # Document provenance for spatial memory
        document_provenance = None
        recent_imports = []
        if hasattr(self.memory_engine, 'get_document_provenance'):
            document_provenance = self.memory_engine.get_document_provenance(user_input)
            if document_provenance:
                print(f"[PROVENANCE] Query matches '{document_provenance['source_document']}' "
                      f"({document_provenance['match_count']} facts, imported {document_provenance['import_time']})")

            recent_imports = self.memory_engine.get_recent_imports(hours=24)
            if recent_imports:
                print(f"[PROVENANCE] {len(recent_imports)} documents imported in last 24h")

        # ===== PHASE 5: Measure and log final context =====
        metrics = self.budget_manager.measure_context(
            memories=recalled,
            rag_chunks=rag_chunks,
            working_turns=working_turns,
            images=active_images,
            other_context=str(summary) + str(momentum_notes) + str(meta_awareness_notes)
        )
        self.budget_manager.log_context_state(metrics)

        # Get image context block for prompt
        image_context = self.get_image_context_block()

        context = {
            "recent_context": working_turns,  # Now limited by budget
            "recalled_memories": recalled,
            "facts": facts,
            "session_summary": summary,
            "emotional_state": agent_state.emotional_cocktail,
            "emotional_patterns": getattr(agent_state, "emotional_patterns", {}),
            "momentum": agent_state.momentum,
            "momentum_notes": momentum_notes,
            "meta_awareness_notes": meta_awareness_notes,
            "consolidated_preferences": getattr(agent_state, "consolidated_preferences", {}),
            "preference_contradictions": getattr(agent_state, "preference_contradictions", []),
            "active_threads": active_threads,
            "rag_chunks": rag_chunks,  # Now limited by budget
            "document_provenance": document_provenance,
            "recent_imports": recent_imports,
            # NEW: Image lifecycle tracking
            "active_images": active_images,
            "image_context": image_context,
            # NEW: Context metrics for debugging
            "context_metrics": {
                "tier": limits['tier'],
                "estimated_tokens": metrics.estimated_tokens,
                "memory_count": len(recalled),
                "rag_count": len(rag_chunks),
                "turn_count": len(working_turns),
                "image_count": len(active_images)
            }
        }
        return context

    def build_context_with_images(
        self,
        agent_state,
        user_input,
        images: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build context with explicit image handling.

        Args:
            agent_state: Current agent state
            user_input: User's message
            images: List of image dicts with 'id' and optional 'description'

        Returns:
            Context dict with image handling
        """
        # Track any new images
        if images:
            for img in images:
                img_id = img.get('id', f'img_{len(self.budget_manager.image_states)}')
                description = img.get('description', '')
                self.track_image(img_id, description)

        # Build context normally (will include image handling)
        return self.build_context(agent_state, user_input)
