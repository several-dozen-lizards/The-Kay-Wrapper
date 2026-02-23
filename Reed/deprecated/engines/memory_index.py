"""
Memory Index System for Reed
Provides fast metadata-based lookups without loading full memory content.
Dramatically improves startup time and memory usage for large datasets.
"""

import json
import os
from typing import Dict, List, Any, Optional, Set
from functools import lru_cache
from collections import OrderedDict


class MemoryIndex:
    """
    Lightweight index for fast memory lookups.
    Loads only metadata at startup, full content on demand.

    Index structure:
    {
        "id": int,
        "tier": "working|episodic|semantic",
        "perspective": "user|kay|shared",
        "type": "full_turn|extracted_fact",
        "category": str,  # topic/domain
        "importance": float,
        "turn": int,
        "entities": List[str],
        "emotion_tags": List[str],
        "is_list": bool,
        "date": str,
        "offset": int,  # Byte offset in data file for fast seeking
        "length": int   # Length in bytes
    }
    """

    def __init__(self, index_path: str = "memory/memory_index.json", data_path: str = "memory/memories.json"):
        self.index_path = index_path
        self.data_path = data_path
        self.indexes: List[Dict[str, Any]] = []
        self.id_map: Dict[int, int] = {}  # id -> index in list

        # LRU cache for recently accessed memories (keeps 100 most recent)
        self.content_cache: OrderedDict[int, Dict] = OrderedDict()
        self.cache_size = 100

        # Load index (fast - metadata only)
        self._load_index()

    def _load_index(self):
        """Load index file (metadata only, not full content)."""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.indexes = data.get("indexes", [])
                self._build_id_map()
                print(f"[MEMORY INDEX] Loaded {len(self.indexes)} memory indexes")
        except FileNotFoundError:
            print(f"[MEMORY INDEX] No index found, will build from scratch")
            self._build_index_from_data()
        except Exception as e:
            print(f"[MEMORY INDEX] Error loading index: {e}, rebuilding")
            self._build_index_from_data()

    def _build_id_map(self):
        """Build quick lookup map: id -> array index."""
        self.id_map = {idx_data["id"]: i for i, idx_data in enumerate(self.indexes)}

    def _build_index_from_data(self):
        """Build index from existing memories.json file."""
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                memories = json.load(f)

            self.indexes = []
            for i, mem in enumerate(memories):
                idx = {
                    "id": i,
                    "tier": mem.get("tier", "episodic"),
                    "perspective": mem.get("perspective", "shared"),
                    "type": mem.get("type", "full_turn"),
                    "category": mem.get("topic", mem.get("category", "general")),
                    "importance": mem.get("importance", 0.5),
                    "turn": mem.get("turn_index", 0),
                    "entities": mem.get("entities", []),
                    "emotion_tags": mem.get("emotion_tags", []),
                    "is_list": mem.get("is_list", False),
                    "date": mem.get("date", ""),
                }
                self.indexes.append(idx)

            self._build_id_map()
            self._save_index()
            print(f"[MEMORY INDEX] Built index for {len(self.indexes)} memories")
        except Exception as e:
            print(f"[MEMORY INDEX] Error building index: {e}")
            self.indexes = []

    def _save_index(self):
        """Save index to disk."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump({"indexes": self.indexes}, f, indent=2)

    def get_metadata(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a memory without loading full content."""
        if memory_id in self.id_map:
            return self.indexes[self.id_map[memory_id]]
        return None

    def get_full_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """
        Load full memory content on demand.
        Uses LRU cache to keep recently accessed memories in RAM.
        """
        # Check cache first
        if memory_id in self.content_cache:
            # Move to end (mark as recently used)
            self.content_cache.move_to_end(memory_id)
            return self.content_cache[memory_id]

        # Load from disk
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                memories = json.load(f)
                if 0 <= memory_id < len(memories):
                    memory = memories[memory_id]

                    # Add to cache
                    self.content_cache[memory_id] = memory

                    # Evict oldest if cache full
                    if len(self.content_cache) > self.cache_size:
                        self.content_cache.popitem(last=False)

                    return memory
        except Exception as e:
            print(f"[MEMORY INDEX] Error loading memory {memory_id}: {e}")

        return None

    def get_batch(self, memory_ids: List[int]) -> List[Dict[str, Any]]:
        """Load multiple memories efficiently (batched read)."""
        # Check cache
        uncached_ids = [mid for mid in memory_ids if mid not in self.content_cache]

        # Load uncached in one read
        if uncached_ids:
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    all_memories = json.load(f)

                    for mid in uncached_ids:
                        if 0 <= mid < len(all_memories):
                            memory = all_memories[mid]
                            self.content_cache[mid] = memory

                            # Evict oldest if cache full
                            if len(self.content_cache) > self.cache_size:
                                self.content_cache.popitem(last=False)
            except Exception as e:
                print(f"[MEMORY INDEX] Error batch loading: {e}")

        # Return from cache
        return [self.content_cache.get(mid) for mid in memory_ids if mid in self.content_cache]

    def search_by_tier(self, tier: str) -> List[int]:
        """Get all memory IDs in a specific tier."""
        return [idx["id"] for idx in self.indexes if idx["tier"] == tier]

    def search_by_perspective(self, perspective: str) -> List[int]:
        """Get all memory IDs with a specific perspective."""
        return [idx["id"] for idx in self.indexes if idx["perspective"] == perspective]

    def search_by_importance(self, min_importance: float) -> List[int]:
        """Get memory IDs above importance threshold."""
        return [idx["id"] for idx in self.indexes if idx["importance"] >= min_importance]

    def search_by_entities(self, entity_names: List[str]) -> List[int]:
        """Get memory IDs that mention any of the given entities."""
        entity_set = set(e.lower() for e in entity_names)
        results = []
        for idx in self.indexes:
            mem_entities = set(e.lower() for e in idx["entities"])
            if mem_entities & entity_set:  # Intersection
                results.append(idx["id"])
        return results

    def search_by_category(self, category: str) -> List[int]:
        """Get memory IDs in a specific category/topic."""
        return [idx["id"] for idx in self.indexes if idx["category"] == category]

    def get_working_memory_ids(self) -> List[int]:
        """Fast lookup of working memory (always small, can load full)."""
        return self.search_by_tier("working")

    def get_recent_ids(self, n: int = 50) -> List[int]:
        """Get N most recent memory IDs by turn index."""
        sorted_ids = sorted(self.indexes, key=lambda x: x["turn"], reverse=True)
        return [idx["id"] for idx in sorted_ids[:n]]

    def add_memory_index(self, memory: Dict[str, Any]) -> int:
        """Add new memory to index."""
        memory_id = len(self.indexes)
        idx = {
            "id": memory_id,
            "tier": memory.get("tier", "episodic"),
            "perspective": memory.get("perspective", "shared"),
            "type": memory.get("type", "full_turn"),
            "category": memory.get("topic", memory.get("category", "general")),
            "importance": memory.get("importance", 0.5),
            "turn": memory.get("turn_index", 0),
            "entities": memory.get("entities", []),
            "emotion_tags": memory.get("emotion_tags", []),
            "is_list": memory.get("is_list", False),
            "date": memory.get("date", ""),
        }
        self.indexes.append(idx)
        self.id_map[memory_id] = len(self.indexes) - 1

        # Add to cache
        self.content_cache[memory_id] = memory
        if len(self.content_cache) > self.cache_size:
            self.content_cache.popitem(last=False)

        return memory_id

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        tier_counts = {}
        for idx in self.indexes:
            tier = idx["tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "total_memories": len(self.indexes),
            "tier_distribution": tier_counts,
            "cache_size": len(self.content_cache),
            "cache_hit_rate": "tracked separately"
        }

    def clear_cache(self):
        """Clear content cache (useful between sessions)."""
        self.content_cache.clear()
        print(f"[MEMORY INDEX] Cache cleared")


class IdentityIndex:
    """
    Index for identity facts with importance categorization.
    Allows loading only critical facts at startup.
    """

    CRITICAL_CATEGORIES = {
        "name", "appearance", "core_relationship", "pets", "spouse", "family"
    }

    CONTEXT_CATEGORIES = {
        "personality", "preferences", "hobbies", "job", "location"
    }

    def __init__(self, index_path: str = "memory/identity_index.json", data_path: str = "memory/identity_memory.json"):
        self.index_path = index_path
        self.data_path = data_path

        # Categorized indexes
        self.critical_re: List[int] = []  # Always load
        self.critical_kay: List[int] = []  # Always load
        self.context_re: List[int] = []  # Load on demand
        self.context_kay: List[int] = []  # Load on demand
        self.detail_re: List[int] = []  # Search only
        self.detail_kay: List[int] = []  # Search only
        self.entities: Dict[str, List[int]] = {}  # entity_name -> fact IDs

        # Content cache
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.cache_size = 50

        self._load_index()

    def _load_index(self):
        """Load identity index."""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.critical_re = data.get("critical_re", [])
                self.critical_kay = data.get("critical_kay", [])
                self.context_re = data.get("context_re", [])
                self.context_kay = data.get("context_kay", [])
                self.detail_re = data.get("detail_re", [])
                self.detail_kay = data.get("detail_kay", [])
                self.entities = data.get("entities", {})

                total = (len(self.critical_re) + len(self.critical_kay) +
                        len(self.context_re) + len(self.context_kay) +
                        len(self.detail_re) + len(self.detail_kay))
                print(f"[IDENTITY INDEX] Loaded {total} identity fact indexes")
                print(f"[IDENTITY INDEX] Critical: {len(self.critical_re) + len(self.critical_kay)}, "
                      f"Context: {len(self.context_re) + len(self.context_kay)}, "
                      f"Details: {len(self.detail_re) + len(self.detail_kay)}")
        except FileNotFoundError:
            print(f"[IDENTITY INDEX] No index found, will build from scratch")
            self._build_index()
        except Exception as e:
            print(f"[IDENTITY INDEX] Error loading: {e}, rebuilding")
            self._build_index()

    def _categorize_fact(self, fact: Dict[str, Any]) -> str:
        """Determine if fact is critical, context, or detail."""
        category = fact.get("topic", "").lower()

        if any(cat in category for cat in self.CRITICAL_CATEGORIES):
            return "critical"
        elif any(cat in category for cat in self.CONTEXT_CATEGORIES):
            return "context"
        else:
            return "detail"

    def _build_index(self):
        """Build identity index from identity_memory.json."""
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            re_facts = data.get("re", [])
            kay_facts = data.get("kay", [])
            entity_facts = data.get("entities", {})

            # Categorize Re facts
            for i, fact in enumerate(re_facts):
                cat = self._categorize_fact(fact)
                if cat == "critical":
                    self.critical_re.append(i)
                elif cat == "context":
                    self.context_re.append(i)
                else:
                    self.detail_re.append(i)

            # Categorize Kay facts
            for i, fact in enumerate(kay_facts):
                cat = self._categorize_fact(fact)
                if cat == "critical":
                    self.critical_kay.append(i)
                elif cat == "context":
                    self.context_kay.append(i)
                else:
                    self.detail_kay.append(i)

            # Index entities
            for entity_type, facts in entity_facts.items():
                self.entities[entity_type] = list(range(len(facts)))

            self._save_index()
            print(f"[IDENTITY INDEX] Built index")
        except Exception as e:
            print(f"[IDENTITY INDEX] Error building index: {e}")

    def _save_index(self):
        """Save identity index."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        data = {
            "critical_re": self.critical_re,
            "critical_kay": self.critical_kay,
            "context_re": self.context_re,
            "context_kay": self.context_kay,
            "detail_re": self.detail_re,
            "detail_kay": self.detail_kay,
            "entities": self.entities
        }
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_critical_facts(self) -> List[Dict[str, Any]]:
        """Load only critical identity facts (always at startup)."""
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            re_facts = data.get("re", [])
            kay_facts = data.get("kay", [])

            critical = []
            critical.extend([re_facts[i] for i in self.critical_re if i < len(re_facts)])
            critical.extend([kay_facts[i] for i in self.critical_kay if i < len(kay_facts)])

            return critical
        except Exception as e:
            print(f"[IDENTITY INDEX] Error loading critical facts: {e}")
            return []

    def get_facts_for_query(self, query: str) -> List[Dict[str, Any]]:
        """Load identity facts relevant to query (critical + contextual)."""
        # Always include critical
        facts = self.get_critical_facts()

        # Add contextual facts if query matches keywords
        # TODO: Implement keyword matching

        return facts
