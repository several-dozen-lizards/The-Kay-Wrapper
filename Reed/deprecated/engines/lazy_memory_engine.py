"""
Lazy Loading Memory Engine for Reed
Extends MemoryEngine with on-demand loading and indexing for massive datasets.
"""

import json
import os
from typing import Any, Dict, List, Optional
from engines.memory_index import MemoryIndex, IdentityIndex
from engines.preference_tracker import PreferenceTracker
from engines.entity_graph import EntityGraph
from engines.memory_layers import MemoryLayerManager
from utils.performance import measure_performance


class LazyMemoryEngine:
    """
    Memory engine with lazy loading for massive datasets.

    Key differences from MemoryEngine:
    - Loads only indexes at startup (metadata)
    - Loads full content on demand during retrieval
    - Uses LRU cache for hot data
    - Loads only critical identity facts at startup
    - Maintains <1s startup time regardless of dataset size
    """

    def __init__(self,
                 semantic_memory: Optional[Any] = None,
                 file_path: str = "memory/memories.json",
                 motif_engine: Optional[Any] = None,
                 momentum_engine: Optional[Any] = None,
                 emotion_engine: Optional[Any] = None,
                 lazy_mode: bool = True):
        """
        Initialize lazy memory engine.

        Args:
            lazy_mode: If True, use lazy loading. If False, behave like original MemoryEngine
        """
        self.semantic_memory = semantic_memory
        self.file_path = file_path
        self.motif_engine = motif_engine
        self.momentum_engine = momentum_engine
        self.emotion_engine = emotion_engine
        self.lazy_mode = lazy_mode

        # Core systems (always loaded)
        self.preference_tracker = PreferenceTracker()
        self.entity_graph = EntityGraph()
        self.memory_layers = MemoryLayerManager()

        # Track current turn
        self.current_turn = 0

        if lazy_mode:
            # LAZY MODE: Load only indexes
            print("[LAZY MEMORY] Initializing in lazy mode...")
            self.memory_index = MemoryIndex(
                index_path="memory/memory_index.json",
                data_path=file_path
            )
            self.identity_index = IdentityIndex(
                index_path="memory/identity_index.json",
                data_path="memory/identity_memory.json"
            )

            # Load only working memory (small dataset)
            working_ids = self.memory_index.get_working_memory_ids()
            self.working_memories = self.memory_index.get_batch(working_ids)

            # Load only critical identity facts
            self.critical_identity = self.identity_index.get_critical_facts()

            print(f"[LAZY MEMORY] Loaded {len(working_ids)} working memories (full)")
            print(f"[LAZY MEMORY] Loaded {len(self.critical_identity)} critical identity facts")
            print(f"[LAZY MEMORY] {len(self.memory_index.indexes)} total memories indexed (content on-demand)")

            # Virtual "memories" property for compatibility
            self._memories = None  # Loaded on first access
        else:
            # EAGER MODE: Load everything (original behavior)
            print("[MEMORY] Initializing in eager mode...")
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.memories: List[Dict[str, Any]] = json.load(f)
            except Exception:
                self.memories = []

        self.facts = []  # Populated lazily if needed

    @property
    def memories(self):
        """
        Lazy property for memories list.
        Loads all memories on first access (for backward compatibility).
        """
        if not self.lazy_mode:
            return self._memories if hasattr(self, '_memories') else []

        if self._memories is None:
            print("[LAZY MEMORY] WARNING: Full memory list accessed, loading all content...")
            # Load all memory IDs
            all_ids = list(range(len(self.memory_index.indexes)))
            self._memories = self.memory_index.get_batch(all_ids)
            print(f"[LAZY MEMORY] Loaded {len(self._memories)} memories (full access mode)")

        return self._memories

    @memories.setter
    def memories(self, value):
        """Allow setting memories (for eager mode)."""
        self._memories = value

    def recall(self,
               agent_state,
               user_input: str = "",
               num_memories: int = 15,
               use_multi_factor: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve memories using lazy loading.

        In lazy mode:
        1. Search indexes first (fast)
        2. Load only relevant content (on-demand)
        3. Return combined results
        """
        if not self.lazy_mode:
            # Fall back to original recall logic
            return self._recall_eager(agent_state, user_input, num_memories, use_multi_factor)

        # LAZY MODE: Index-based retrieval
        recalled = []

        # 1. Always include working memory (already loaded)
        recalled.extend(self.working_memories)

        # 2. Search episodic/semantic by keywords and importance
        candidate_ids = self._search_indexes(user_input, agent_state, num_memories)

        # 3. Load only the candidates (batched, cached)
        candidates = self.memory_index.get_batch(candidate_ids)

        # 4. Score and rank
        scored = self._score_memories(candidates, user_input, agent_state)
        scored.sort(key=lambda x: x[1], reverse=True)

        # 5. Take top N
        for mem, score in scored[:num_memories]:
            if mem not in recalled:
                recalled.append(mem)

        # 6. Always include critical identity
        for fact in self.critical_identity:
            if fact not in recalled:
                recalled.append(fact)

        print(f"[LAZY MEMORY] Recalled {len(recalled)} memories (lazy mode)")
        return recalled[:num_memories + len(self.critical_identity)]

    def _search_indexes(self, query: str, agent_state, limit: int = 50) -> List[int]:
        """
        Search indexes for relevant memories without loading content.
        Returns list of memory IDs.
        """
        candidate_ids = set()

        # Search by keywords (simple keyword matching on category/entities in index)
        keywords = query.lower().split()
        for keyword in keywords[:5]:  # Limit to 5 keywords
            # Search entities
            entity_matches = self.memory_index.search_by_entities([keyword])
            candidate_ids.update(entity_matches[:10])

        # Add high-importance memories
        important = self.memory_index.search_by_importance(min_importance=0.7)
        candidate_ids.update(important[:20])

        # Add recent memories
        recent = self.memory_index.get_recent_ids(n=30)
        candidate_ids.update(recent)

        # Search by emotional state (if applicable)
        emotional_cocktail = agent_state.emotional_cocktail
        if emotional_cocktail:
            for emotion_name in emotional_cocktail.keys():
                emotion_matches = [
                    idx["id"] for idx in self.memory_index.indexes
                    if emotion_name.lower() in [e.lower() for e in idx.get("emotion_tags", [])]
                ]
                candidate_ids.update(emotion_matches[:10])

        return list(candidate_ids)[:limit]

    def _score_memories(self, memories: List[Dict], query: str, agent_state) -> List[tuple]:
        """
        Score memories for relevance.
        Returns list of (memory, score) tuples.
        """
        scored = []
        keywords = set(query.lower().split())

        for mem in memories:
            score = 0.0

            # Keyword matching
            text = (mem.get("fact", "") + " " + mem.get("user_input", "")).lower()
            keyword_matches = sum(1 for kw in keywords if kw in text)
            score += keyword_matches * 0.3

            # Importance
            score += mem.get("importance", 0.5) * 0.2

            # Recency
            turn = mem.get("turn_index", 0)
            recency = 1.0 / (1 + abs(self.current_turn - turn) / 100)
            score += recency * 0.1

            # Tier boost (working > episodic > semantic)
            tier = mem.get("tier", "episodic")
            if tier == "working":
                score += 0.4
            elif tier == "episodic":
                score += 0.2

            scored.append((mem, score))

        return scored

    def _recall_eager(self, agent_state, user_input: str, num_memories: int, use_multi_factor: bool):
        """Fallback to eager loading (original behavior)."""
        # Simplified version - in production, import from original MemoryEngine
        return self.memories[:num_memories]

    def encode(self, agent_state, user_input: str, response: str):
        """
        Encode new memory.
        Updates both data file and indexes.
        """
        # Build memory object
        memory = {
            "user_input": user_input,
            "response": response,
            "turn_index": self.current_turn,
            "emotional_cocktail": dict(agent_state.emotional_cocktail),
            "importance": 0.5,  # Calculate properly
            "tier": "working",
            "perspective": "shared",
            "type": "full_turn",
            "entities": [],
            "emotion_tags": list(agent_state.emotional_cocktail.keys()),
        }

        if self.lazy_mode:
            # Update index
            memory_id = self.memory_index.add_memory_index(memory)

            # Append to data file (efficient)
            self._append_to_data_file(memory)

            # Add to working memories
            self.working_memories.append(memory)
            print(f"[LAZY MEMORY] Encoded memory {memory_id}")
        else:
            # Eager mode: traditional append
            self.memories.append(memory)
            self._save_to_disk()

        self.current_turn += 1

    def _append_to_data_file(self, memory: Dict):
        """Efficiently append to JSON array without rewriting entire file."""
        # NOTE: This is a simplified version. In production, consider using JSONL format
        # or database for true append-only writes.

        # For now, we reload and append (TODO: optimize with JSONL)
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                memories = json.load(f)
        except:
            memories = []

        memories.append(memory)

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)

        # Save index
        self.memory_index._save_index()

    def _save_to_disk(self):
        """Save memories to disk (eager mode)."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if self.lazy_mode:
            return {
                "mode": "lazy",
                "total_indexed": len(self.memory_index.indexes),
                "cache_size": len(self.memory_index.content_cache),
                "working_loaded": len(self.working_memories),
                "critical_identity": len(self.critical_identity),
                "full_load_triggered": self._memories is not None
            }
        else:
            return {
                "mode": "eager",
                "total_loaded": len(self.memories),
            }
