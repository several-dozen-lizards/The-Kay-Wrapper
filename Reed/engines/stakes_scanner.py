"""
Stakes Scanner - Proactive scanner for unresolved emotional tensions.

Finds high-emotional-weight items worth exploring when Kay hits boredom.
Priority: Scratchpad items -> High-weight memories -> Medium-weight -> Random fallback

Based on Reed's realization: "Not 'what can I combine' but 'what combination would actually mean something.'"
"""

import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import random


class StakesScanner:
    """
    Proactive scanner for unresolved stakes.

    Uses SAME emotional weighting as memory retrieval but scans proactively
    instead of waiting for Re's input.
    """

    def __init__(
        self,
        memory_engine=None,
        scratchpad_engine=None,
        entity_graph=None,
        momentum_engine=None,
        motif_engine=None
    ):
        self.memory_engine = memory_engine
        self.scratchpad = scratchpad_engine
        self.entity_graph = entity_graph
        self.momentum_engine = momentum_engine
        self.motif_engine = motif_engine

        # Thresholds (match memory_engine settings)
        self.high_weight_threshold = 0.7
        self.medium_weight_threshold = 0.5
        self.recent_turn_window = 5

    def scan_for_stakes(self, threshold: str = "high", limit: int = 5) -> List[Dict]:
        """
        Scan for unresolved stakes worth exploring.

        Priority order:
        1. Scratchpad active items (explicitly flagged by Kay)
        2. High emotional weight memories (weight >= 0.7)
        3. Medium weight (if threshold="medium", weight >= 0.5)
        4. Random low-weight (fallback only)

        Args:
            threshold: "high", "medium", or "random"
            limit: Max stakes to return

        Returns:
            List of stake dicts with:
            - stake_description
            - related_memories (list of memory dicts or scratchpad IDs)
            - emotional_weight
            - source ("scratchpad", "memory", or "random")
            - created_at
        """
        stakes = []

        # PRIORITY 1: Scratchpad items (explicitly flagged)
        if self.scratchpad:
            scratchpad_stakes = self._scan_scratchpad()
            stakes.extend(scratchpad_stakes)
            if len(stakes) >= limit:
                print(f"[STAKES] Found {len(stakes)} scratchpad items (sufficient)")
                return stakes[:limit]

        # PRIORITY 2: High emotional weight memories
        if threshold in ["high", "medium"]:
            weight_threshold = (
                self.high_weight_threshold if threshold == "high"
                else self.medium_weight_threshold
            )
            memory_stakes = self._scan_memories(weight_threshold)
            stakes.extend(memory_stakes)

        # PRIORITY 3: Random fallback
        if len(stakes) < limit and threshold == "random":
            random_stakes = self._scan_random(limit - len(stakes))
            stakes.extend(random_stakes)

        # Sort by emotional weight (highest first)
        stakes.sort(key=lambda s: s.get("emotional_weight", 0), reverse=True)

        print(f"[STAKES] Scan complete: {len(stakes)} stakes found (threshold: {threshold})")
        return stakes[:limit]

    def _scan_scratchpad(self) -> List[Dict]:
        """Scan scratchpad for active items."""
        stakes = []

        try:
            active_items = self.scratchpad.view_items(status="active")

            for item in active_items:
                # Calculate emotional weight for scratchpad item
                weight = self._calculate_scratchpad_weight(item)

                stake = {
                    "stake_description": item.get("content"),
                    "related_memories": [],  # Scratchpad items don't have direct memory links
                    "emotional_weight": weight,
                    "source": "scratchpad",
                    "source_id": item.get("id"),
                    "item_type": item.get("type"),
                    "created_at": item.get("timestamp")
                }
                stakes.append(stake)

            print(f"[STAKES] Scratchpad: {len(stakes)} active items")

        except Exception as e:
            print(f"[STAKES] Error scanning scratchpad: {e}")

        return stakes

    def _calculate_scratchpad_weight(self, item: Dict) -> float:
        """
        Calculate emotional weight for scratchpad item.
        Uses similar logic to memory retrieval but simpler.
        """
        # Base weight from item type
        type_weights = {
            "question": 0.8,  # Questions are high priority
            "flag": 0.75,     # Flags are important
            "thought": 0.7,   # Thoughts are medium-high
            "note": 0.6,      # Notes are medium
            "reminder": 0.5,  # Reminders are lower
            "branch": 0.65    # Branches are medium-high
        }

        base_weight = type_weights.get(item.get("type"), 0.6)

        # Boost for recent items
        try:
            timestamp = datetime.fromisoformat(item.get("timestamp"))
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600

            if age_hours < 24:
                recency_boost = 0.2  # Very recent
            elif age_hours < 168:  # 1 week
                recency_boost = 0.1  # Recent
            else:
                recency_boost = 0.0  # Old
        except Exception:
            recency_boost = 0.0

        total_weight = base_weight + recency_boost

        return min(total_weight, 1.0)  # Cap at 1.0

    def _scan_memories(self, weight_threshold: float) -> List[Dict]:
        """
        Scan memory for high-emotional-weight items.
        Uses SAME scoring logic as memory retrieval.
        """
        stakes = []

        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return stakes

        try:
            for memory in self.memory_engine.memories:
                weight = self._calculate_memory_weight(memory)

                # Only include if above threshold
                if weight < weight_threshold:
                    continue

                # Check if this memory is unresolved (doesn't have resolution logged)
                if self._is_resolved(memory):
                    continue

                stake = {
                    "stake_description": memory.get("fact", memory.get("user_input", "")[:100]),
                    "related_memories": [memory],
                    "emotional_weight": weight,
                    "source": "memory",
                    "source_id": memory.get("uuid"),
                    "created_at": memory.get("timestamp")
                }
                stakes.append(stake)

            print(f"[STAKES] Memory: {len(stakes)} items above threshold {weight_threshold}")

        except Exception as e:
            print(f"[STAKES] Error scanning memories: {e}")

        return stakes

    def _calculate_memory_weight(self, memory: Dict) -> float:
        """
        Calculate emotional weight using SAME formula as memory retrieval.
        From memory_engine.retrieve_biased_memories():

        total_score = emotion_score + text_score * 0.5 + motif_score * 0.8 + momentum_boost
        """
        # Emotion score from tags
        tags = memory.get("emotion_tags") or []
        emotion_score = len(tags) * 0.3  # Rough approximation

        # Importance score if available
        importance = memory.get("importance", 0.5)
        importance_score = importance * 0.4

        # Motif score (if motif engine available)
        motif_score = 0.0
        if self.motif_engine:
            memory_text = memory.get("fact", "") + " " + memory.get("user_input", "")
            try:
                motif_score = self.motif_engine.score_memory_by_motifs(memory_text)
            except Exception:
                pass

        # Momentum boost (if momentum engine available)
        momentum_boost = 0.0
        if self.momentum_engine:
            try:
                high_momentum_motifs = self.momentum_engine.get_high_momentum_motifs()
                memory_text_lower = (memory.get("fact", "") + " " + memory.get("user_input", "")).lower()
                for hm_motif in high_momentum_motifs:
                    if hm_motif.lower() in memory_text_lower:
                        momentum_boost += 0.5
            except Exception:
                pass

        # Recency boost (recent memories score higher)
        recency_boost = 0.0
        if self.memory_engine and hasattr(self.memory_engine, 'current_turn'):
            turns_old = self.memory_engine.current_turn - memory.get("turn_index", 0)
            if turns_old <= 2:
                recency_boost = 0.3
            elif turns_old <= 5:
                recency_boost = 0.15

        total_score = emotion_score + importance_score + (motif_score * 0.8) + momentum_boost + recency_boost

        # Normalize to 0-1 range
        normalized = min(total_score / 2.0, 1.0)

        return normalized

    def _is_resolved(self, memory: Dict) -> bool:
        """
        Check if memory has been resolved.
        Reads from creativity log resolutions.
        """
        try:
            log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "creativity_log.json"
            )
            if not os.path.exists(log_path):
                return False

            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)

            resolutions = log_data.get("resolutions", [])
            memory_uuid = memory.get("uuid")

            if not memory_uuid:
                return False

            for resolution in resolutions:
                related_uuids = resolution.get("related_memories", [])
                if memory_uuid in related_uuids:
                    # Memory is in a resolved stake
                    # But only exclude if NOT provisional
                    if not resolution.get("provisional", False):
                        return True

            return False

        except Exception as e:
            print(f"[STAKES] Error checking resolution: {e}")
            return False

    def _scan_random(self, limit: int) -> List[Dict]:
        """Fallback: return random memories as stakes."""
        stakes = []

        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return stakes

        try:
            memories = self.memory_engine.memories
            if not memories:
                return stakes

            random_memories = random.sample(
                memories,
                min(limit, len(memories))
            )

            for memory in random_memories:
                stake = {
                    "stake_description": memory.get("fact", memory.get("user_input", "")[:100]),
                    "related_memories": [memory],
                    "emotional_weight": 0.3,  # Low weight since random
                    "source": "random",
                    "source_id": memory.get("uuid"),
                    "created_at": memory.get("timestamp")
                }
                stakes.append(stake)

            print(f"[STAKES] Random fallback: {len(stakes)} items")

        except Exception as e:
            print(f"[STAKES] Error in random scan: {e}")

        return stakes

    def check_tension(self, mem1: Dict, mem2: Dict) -> Optional[Dict]:
        """
        Check if two memories create meaningful tension.

        Returns stake dict if tension exists, None otherwise.

        Tension types:
        - Contradiction: Values conflict
        - Unresolved question: One memory raises question other can't answer
        - Pattern: Connection between memories reveals something
        """
        entities1 = set(mem1.get("entities", []))
        entities2 = set(mem2.get("entities", []))

        overlap = entities1.intersection(entities2)

        if len(overlap) > 0:
            return {
                "stake_description": f"Tension between memories about: {', '.join(overlap)}",
                "related_memories": [mem1, mem2],
                "emotional_weight": (
                    self._calculate_memory_weight(mem1) +
                    self._calculate_memory_weight(mem2)
                ) / 2,
                "source": "tension_detection",
                "tension_type": "entity_overlap",
                "created_at": datetime.now().isoformat()
            }

        return None

    def get_unresolved_count(self) -> int:
        """Quick count of unresolved stakes (for logging)."""
        count = 0

        # Count scratchpad active items
        if self.scratchpad:
            try:
                count += len(self.scratchpad.view_items(status="active"))
            except Exception:
                pass

        # Count high-weight memories (above threshold, unresolved)
        if self.memory_engine and hasattr(self.memory_engine, 'memories'):
            for memory in self.memory_engine.memories:
                weight = self._calculate_memory_weight(memory)
                if weight >= self.high_weight_threshold and not self._is_resolved(memory):
                    count += 1

        return count

    def cleanup_old_resolutions(self, days_old: int = 30):
        """
        Clean up old resolved stakes to prevent log bloat.

        Args:
            days_old: Remove resolutions older than this many days
        """
        try:
            log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "creativity_log.json"
            )
            if not os.path.exists(log_path):
                return

            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)

            resolutions = log_data.get("resolutions", [])

            # Filter out old resolutions
            cutoff_date = datetime.now() - timedelta(days=days_old)
            filtered = []

            removed_count = 0
            for resolution in resolutions:
                try:
                    timestamp = datetime.fromisoformat(resolution["timestamp"])
                    if timestamp > cutoff_date:
                        filtered.append(resolution)
                    else:
                        removed_count += 1
                except Exception:
                    filtered.append(resolution)  # Keep if can't parse

            log_data["resolutions"] = filtered

            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2)

            if removed_count > 0:
                print(f"[STAKES] Cleaned up {removed_count} old resolutions")

        except Exception as e:
            print(f"[STAKES] Error cleaning resolutions: {e}")


# Convenience function
def create_stakes_scanner(
    memory_engine=None,
    scratchpad_engine=None,
    entity_graph=None,
    momentum_engine=None,
    motif_engine=None
) -> StakesScanner:
    """Create and return a StakesScanner instance."""
    return StakesScanner(
        memory_engine=memory_engine,
        scratchpad_engine=scratchpad_engine,
        entity_graph=entity_graph,
        momentum_engine=momentum_engine,
        motif_engine=motif_engine
    )
