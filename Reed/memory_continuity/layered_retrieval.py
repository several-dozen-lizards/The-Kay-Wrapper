"""
Layer-Weighted Memory Retrieval
Rebalances retrieval to prioritize working/episodic over semantic for continuity
"""

from typing import List, Dict, Any, Optional, Set
import numpy as np
from dataclasses import dataclass


@dataclass
class RetrievalConfig:
    """
    Configuration for layer-weighted retrieval
    """
    # Layer multipliers (applied to base relevance score)
    working_multiplier: float = 3.0  # Strongly boost working memory
    episodic_multiplier: float = 2.0  # Boost episodic memory
    semantic_multiplier: float = 0.8  # Slightly reduce semantic memory

    # Target distribution (soft targets, not hard limits)
    target_working_ratio: float = 0.20  # Aim for 20% working
    target_episodic_ratio: float = 0.50  # Aim for 50% episodic
    target_semantic_ratio: float = 0.30  # Aim for 30% semantic

    # Diversity enforcement
    enforce_diversity: bool = True
    min_layer_representation: int = 5  # Min memories per layer if available

    # Recency bonuses (in addition to layer multiplier)
    recent_turn_threshold: int = 10  # Turns considered "recent"
    recent_turn_boost: float = 0.5  # Additional boost for recent memories


class LayeredMemoryRetriever:
    """
    Retrieves memories with layer-aware weighting to ensure proper distribution
    """

    def __init__(
        self,
        chroma_collection,
        config: Optional[RetrievalConfig] = None
    ):
        """
        Args:
            chroma_collection: ChromaDB collection instance
            config: Retrieval configuration (uses defaults if None)
        """
        self.collection = chroma_collection
        self.config = config or RetrievalConfig()

    def retrieve(
        self,
        query: str,
        current_turn: int,
        n_results: int = 225,
        thread_tracker=None,
        emotional_state: Optional[Dict[str, float]] = None,
        guaranteed_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories with layer weighting and thread momentum

        Args:
            query: Search query
            current_turn: Current conversation turn
            n_results: Target number of memories to return
            thread_tracker: Optional ThreadMomentumTracker for momentum boosting
            emotional_state: Optional emotional state for resonance scoring
            guaranteed_ids: Memory IDs that must be included (from session loader)

        Returns:
            List of memory dicts with rebalanced layer distribution
        """

        # Step 1: Initial retrieval (get more than needed for reranking)
        initial_results = self._initial_retrieval(
            query,
            n_results=int(n_results * 2)  # Over-retrieve for reranking
        )

        # Step 2: Score and rerank with layer weighting
        scored_memories = self._score_memories(
            initial_results,
            query,
            current_turn,
            thread_tracker,
            emotional_state
        )

        # Step 3: Ensure guaranteed memories are included
        if guaranteed_ids:
            scored_memories = self._inject_guaranteed_memories(
                scored_memories,
                guaranteed_ids
            )

        # Step 4: Select final set with diversity enforcement
        final_memories = self._select_with_diversity(
            scored_memories,
            n_results
        )

        return final_memories

    def _initial_retrieval(
        self,
        query: str,
        n_results: int
    ) -> List[Dict[str, Any]]:
        """
        Initial vector similarity retrieval from ChromaDB
        """

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        memories = []
        for idx in range(len(results["ids"][0])):
            memory = {
                "id": results["ids"][0][idx],
                "content": results["documents"][0][idx],
                "metadata": results["metadatas"][0][idx],
                "distance": results["distances"][0][idx],
                "base_score": 1.0 - results["distances"][0][idx]  # Convert distance to similarity
            }
            memories.append(memory)

        return memories

    def _score_memories(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        current_turn: int,
        thread_tracker,
        emotional_state: Optional[Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Score memories with layer weighting, thread momentum, and emotional resonance
        """

        scored = []

        for memory in memories:
            metadata = memory["metadata"]
            base_score = memory["base_score"]

            # Layer multiplier
            layer = metadata.get("layer", "semantic")
            if layer == "working":
                layer_mult = self.config.working_multiplier
            elif layer == "episodic":
                layer_mult = self.config.episodic_multiplier
            else:  # semantic
                layer_mult = self.config.semantic_multiplier

            # Recency boost
            memory_turn = metadata.get("turn", 0)
            age = current_turn - memory_turn
            recency_boost = 0.0
            if age <= self.config.recent_turn_threshold:
                recency_boost = self.config.recent_turn_boost * (
                    1.0 - age / self.config.recent_turn_threshold
                )

            # Thread momentum boost
            momentum_boost = 0.0
            if thread_tracker:
                momentum_boost = thread_tracker.get_boost_multiplier_for_memory(
                    memory["id"]
                ) - 1.0  # Convert 1.0-3.0 to 0.0-2.0

            # Emotional resonance boost
            emotion_boost = 0.0
            if emotional_state and "emotional_tags" in metadata:
                emotion_boost = self._calculate_emotional_resonance(
                    metadata["emotional_tags"],
                    emotional_state
                )

            # Importance from metadata
            importance = metadata.get("importance", 0.5)

            # Combined score
            final_score = (
                base_score * layer_mult +
                recency_boost +
                momentum_boost * 0.5 +
                emotion_boost * 0.3 +
                importance * 0.2
            )

            memory["final_score"] = final_score
            memory["layer"] = layer
            memory["age"] = age

            scored.append(memory)

        # Sort by final score
        scored.sort(key=lambda m: m["final_score"], reverse=True)

        return scored

    def _calculate_emotional_resonance(
        self,
        memory_emotions: List[str],
        current_emotions: Dict[str, float]
    ) -> float:
        """
        Calculate emotional resonance between memory and current state
        """

        if not memory_emotions or not current_emotions:
            return 0.0

        # Sum of matching emotion intensities
        resonance = sum(
            current_emotions.get(emotion, 0.0)
            for emotion in memory_emotions
        )

        # Normalize by number of emotions in memory
        return resonance / max(1, len(memory_emotions))

    def _inject_guaranteed_memories(
        self,
        scored_memories: List[Dict[str, Any]],
        guaranteed_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Ensure guaranteed memories are included with high scores
        """

        # Find guaranteed memories
        guaranteed = []
        other = []

        guaranteed_set = set(guaranteed_ids)

        for memory in scored_memories:
            if memory["id"] in guaranteed_set:
                # Boost score to ensure inclusion
                memory["final_score"] += 10.0
                guaranteed.append(memory)
            else:
                other.append(memory)

        # Combine and re-sort
        all_memories = guaranteed + other
        all_memories.sort(key=lambda m: m["final_score"], reverse=True)

        return all_memories

    def _select_with_diversity(
        self,
        scored_memories: List[Dict[str, Any]],
        n_results: int
    ) -> List[Dict[str, Any]]:
        """
        Select final memories while enforcing layer diversity
        """

        if not self.config.enforce_diversity:
            return scored_memories[:n_results]

        # Track layer counts
        layer_counts = {"working": 0, "episodic": 0, "semantic": 0}
        layer_memories = {"working": [], "episodic": [], "semantic": []}

        # Separate by layer
        for memory in scored_memories:
            layer = memory["layer"]
            layer_memories[layer].append(memory)

        # Calculate target counts
        target_working = int(n_results * self.config.target_working_ratio)
        target_episodic = int(n_results * self.config.target_episodic_ratio)
        target_semantic = n_results - target_working - target_episodic

        selected = []

        # Phase 1: Fill minimum representations
        min_rep = self.config.min_layer_representation
        for layer in ["working", "episodic", "semantic"]:
            available = layer_memories[layer][:min_rep]
            selected.extend(available)
            layer_counts[layer] += len(available)
            layer_memories[layer] = layer_memories[layer][min_rep:]

        # Phase 2: Fill to target ratios
        targets = {
            "working": target_working,
            "episodic": target_episodic,
            "semantic": target_semantic
        }

        for layer, target in targets.items():
            needed = max(0, target - layer_counts[layer])
            available = layer_memories[layer][:needed]
            selected.extend(available)
            layer_counts[layer] += len(available)
            layer_memories[layer] = layer_memories[layer][needed:]

        # Phase 3: Fill remaining slots with highest-scoring memories
        remaining_slots = n_results - len(selected)
        if remaining_slots > 0:
            # Combine remaining memories from all layers
            remaining = []
            for layer in ["working", "episodic", "semantic"]:
                remaining.extend(layer_memories[layer])

            # Sort by score and take top N
            remaining.sort(key=lambda m: m["final_score"], reverse=True)
            selected.extend(remaining[:remaining_slots])

        # Final sort by score
        selected.sort(key=lambda m: m["final_score"], reverse=True)

        return selected[:n_results]

    def get_layer_distribution(
        self,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze layer distribution of retrieved memories
        """

        layer_counts = {"working": 0, "episodic": 0, "semantic": 0}

        for memory in memories:
            layer = memory.get("layer", "semantic")
            layer_counts[layer] += 1

        total = len(memories)

        return {
            "total": total,
            "working": layer_counts["working"],
            "episodic": layer_counts["episodic"],
            "semantic": layer_counts["semantic"],
            "working_pct": (layer_counts["working"] / total * 100) if total > 0 else 0,
            "episodic_pct": (layer_counts["episodic"] / total * 100) if total > 0 else 0,
            "semantic_pct": (layer_counts["semantic"] / total * 100) if total > 0 else 0,
        }

    def analyze_retrieval_quality(
        self,
        memories: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Analyze quality of retrieved memories
        """

        distribution = self.get_layer_distribution(memories)

        # Age analysis
        ages = [m.get("age", 0) for m in memories]
        avg_age = np.mean(ages) if ages else 0
        median_age = np.median(ages) if ages else 0

        # Score analysis
        scores = [m.get("final_score", 0) for m in memories]
        avg_score = np.mean(scores) if scores else 0

        # Thread coverage (if memories have thread tags)
        threads = set()
        for m in memories:
            if "thread_relevance" in m.get("metadata", {}):
                threads.update(m["metadata"]["thread_relevance"])

        return {
            "distribution": distribution,
            "avg_age_turns": float(avg_age),
            "median_age_turns": float(median_age),
            "avg_score": float(avg_score),
            "thread_coverage": len(threads),
            "total_memories": len(memories)
        }


class LayerBalancer:
    """
    Monitors and adjusts layer distribution over time
    """

    def __init__(self, target_ratios: Optional[Dict[str, float]] = None):
        self.target_ratios = target_ratios or {
            "working": 0.15,
            "episodic": 0.55,
            "semantic": 0.30
        }

    def analyze_storage(self, chroma_collection) -> Dict[str, Any]:
        """
        Analyze current storage layer distribution
        """

        # Get all metadata
        all_data = chroma_collection.get(include=["metadatas"])

        layer_counts = {"working": 0, "episodic": 0, "semantic": 0}

        for metadata in all_data["metadatas"]:
            layer = metadata.get("layer", "semantic")
            layer_counts[layer] += 1

        total = sum(layer_counts.values())

        return {
            "total_memories": total,
            "working": layer_counts["working"],
            "episodic": layer_counts["episodic"],
            "semantic": layer_counts["semantic"],
            "working_pct": (layer_counts["working"] / total * 100) if total > 0 else 0,
            "episodic_pct": (layer_counts["episodic"] / total * 100) if total > 0 else 0,
            "semantic_pct": (layer_counts["semantic"] / total * 100) if total > 0 else 0,
            "imbalance_score": self._calculate_imbalance(layer_counts, total)
        }

    def _calculate_imbalance(
        self,
        layer_counts: Dict[str, int],
        total: int
    ) -> float:
        """
        Calculate how far distribution is from target (0.0 = perfect, 1.0 = very imbalanced)
        """

        if total == 0:
            return 0.0

        imbalance = 0.0
        for layer, target_ratio in self.target_ratios.items():
            actual_ratio = layer_counts[layer] / total
            imbalance += abs(actual_ratio - target_ratio)

        # Normalize to 0-1
        return min(1.0, imbalance)

    def recommend_promotions_demotions(
        self,
        chroma_collection,
        current_turn: int
    ) -> Dict[str, List[str]]:
        """
        Recommend which memories to promote/demote to rebalance layers
        """

        # Get all memories with metadata
        all_data = chroma_collection.get(include=["metadatas"])

        recommendations = {
            "promote_to_episodic": [],  # Working -> Episodic
            "promote_to_semantic": [],  # Episodic -> Semantic
            "demote_to_episodic": [],   # Semantic -> Episodic (rare facts back to context)
        }

        for idx, metadata in enumerate(all_data["metadatas"]):
            memory_id = all_data["ids"][idx]
            layer = metadata.get("layer", "semantic")
            importance = metadata.get("importance", 0.5)
            age = current_turn - metadata.get("turn", 0)
            access_count = metadata.get("access_count", 0)

            # Promote working -> episodic if accessed multiple times
            if layer == "working" and access_count >= 3:
                recommendations["promote_to_episodic"].append(memory_id)

            # Promote episodic -> semantic if old, important, and frequently accessed
            if layer == "episodic" and age > 50 and importance > 0.7 and access_count >= 5:
                recommendations["promote_to_semantic"].append(memory_id)

            # Demote semantic -> episodic if low importance and never accessed
            if layer == "semantic" and importance < 0.4 and access_count == 0 and age < 20:
                recommendations["demote_to_episodic"].append(memory_id)

        return recommendations
