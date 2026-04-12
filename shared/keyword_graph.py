# shared/keyword_graph.py
"""
Dijkstra Keyword-Graph Memory — Lazy Link Construction

"Links form through recall, not through storage."

This module provides keyword-based concept tagging with Dijkstra traversal,
where links between memories are created at RETRIEVAL time — only when a
path is actually followed. The graph builds itself through use.

Three classes:
- KeywordIndex: Inverted index mapping keywords to memory IDs
- DijkstraRecall: Traverse keyword graph using Dijkstra's algorithm
- LazyLinkCreator: Create shortcuts when paths are traversed

Credit: External reviewer Vaasref for the core insight.
"""

import os
import json
import time
import heapq
import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DIJKSTRA_CONFIG = {
    # Keyword extraction
    "tag_new_memories": True,       # Tag memories at storage time
    "tag_on_retrieval": True,       # Tag old memories when first accessed
    "concepts_per_memory": 5,       # Max concept keywords per memory

    # Dijkstra traversal
    "use_dijkstra": True,
    "max_cost": 3.0,                # Maximum graph distance
    "max_dijkstra_results": 5,      # How many memories from Dijkstra

    # Lazy links
    "create_traversal_links": True,
    "initial_link_strength": 0.2,   # New links start weak
    "strength_per_traversal": 0.15, # Gain per traversal
    "max_link_strength": 1.0,
    "link_decay_rate": 0.01,        # Strength lost per day without use

    # Shortcuts
    "use_shortcuts": True,
    "min_shortcut_strength": 0.15,  # Don't use very weak shortcuts

    # Integration
    "dijkstra_in_tier2": True,      # Include in medium loop cache refresh
    "dijkstra_in_tier3": True,      # Include in per-turn retrieval
}


# ═══════════════════════════════════════════════════════════════════════════
# KEYWORD INDEX — Inverted index for concept-based retrieval
# ═══════════════════════════════════════════════════════════════════════════

class KeywordIndex:
    """
    Inverted index: keyword → memory IDs.
    This is the concept graph's backbone.

    Keywords can be:
    - Named entities (people, places, pets)
    - Emotion labels
    - Topic/concept words (via Ollama)
    - Oscillator band at encoding (state:theta, state:beta, etc.)
    - Temporal tags (hour:14, day:monday)
    """

    def __init__(self, persist_path: str = None):
        # keyword → set of memory IDs
        self._index: Dict[str, Set[str]] = {}
        # memory ID → set of keywords
        self._reverse: Dict[str, Set[str]] = {}
        self.persist_path = persist_path
        self._dirty = False

        if persist_path:
            self._load()

    def add_memory(self, memory_id: str, keywords: List[str]):
        """Index a memory under its keywords."""
        if not memory_id or not keywords:
            return

        for kw in keywords:
            kw = kw.lower().strip()
            if not kw:
                continue
            if kw not in self._index:
                self._index[kw] = set()
            self._index[kw].add(memory_id)

        if memory_id not in self._reverse:
            self._reverse[memory_id] = set()
        self._reverse[memory_id].update(k.lower().strip() for k in keywords if k)
        self._dirty = True

    def remove_memory(self, memory_id: str):
        """Remove a memory from the index (when curated/discarded)."""
        keywords = self._reverse.pop(memory_id, set())
        for kw in keywords:
            if kw in self._index:
                self._index[kw].discard(memory_id)
                if not self._index[kw]:
                    del self._index[kw]
        self._dirty = True

    def get_memories_for_keyword(self, keyword: str) -> Set[str]:
        """All memory IDs tagged with this keyword."""
        return self._index.get(keyword.lower().strip(), set())

    def get_keywords_for_memory(self, memory_id: str) -> Set[str]:
        """All keywords for a given memory."""
        return self._reverse.get(memory_id, set())

    def get_shared_keywords(self, mem_a: str, mem_b: str) -> Set[str]:
        """Keywords shared between two memories."""
        kw_a = self._reverse.get(mem_a, set())
        kw_b = self._reverse.get(mem_b, set())
        return kw_a & kw_b

    def has_memory(self, memory_id: str) -> bool:
        """Check if a memory is in the index."""
        return memory_id in self._reverse

    def get_keyword_count(self, keyword: str) -> int:
        """How many memories have this keyword."""
        return len(self._index.get(keyword.lower().strip(), set()))

    def get_stats(self) -> Dict[str, int]:
        """Return index statistics."""
        return {
            "total_keywords": len(self._index),
            "total_memories": len(self._reverse),
            "avg_keywords_per_memory": (
                sum(len(kws) for kws in self._reverse.values()) / len(self._reverse)
                if self._reverse else 0
            ),
        }

    def save(self):
        """Persist to disk as JSON."""
        if not self.persist_path or not self._dirty:
            return
        try:
            data = {
                "index": {k: list(v) for k, v in self._index.items()},
                "reverse": {k: list(v) for k, v in self._reverse.items()},
            }
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self._dirty = False
            log.debug(f"[KEYWORD_INDEX] Saved {len(self._reverse)} memories to {self.persist_path}")
        except Exception as e:
            log.warning(f"[KEYWORD_INDEX] Failed to save: {e}")

    def _load(self):
        """Load from disk."""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._index = {k: set(v) for k, v in data.get("index", {}).items()}
            self._reverse = {k: set(v) for k, v in data.get("reverse", {}).items()}
            log.debug(f"[KEYWORD_INDEX] Loaded {len(self._reverse)} memories from {self.persist_path}")
        except Exception as e:
            log.warning(f"[KEYWORD_INDEX] Failed to load: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# DIJKSTRA RECALL — Graph traversal for associative retrieval
# ═══════════════════════════════════════════════════════════════════════════

class DijkstraRecall:
    """
    Traverse the keyword graph using Dijkstra's algorithm.

    Starts at a seed (keyword or memory), explores outward through
    shared keywords, and returns the closest memories by graph distance.

    The key insight: two memories connected by a RARE keyword are
    closer than two memories connected by a COMMON keyword.
    "chrome" connects fewer things than "cat" — so a Chrome-specific
    memory link is stronger than a generic cat link.
    """

    def __init__(self, keyword_index: KeywordIndex, lazy_links: 'LazyLinkCreator' = None):
        self.index = keyword_index
        self.lazy_links = lazy_links

    def _keyword_weight(self, keyword: str) -> float:
        """
        Cost of traversing through a keyword.
        Rare keywords = low cost (strong, specific link).
        Common keywords = high cost (weak, generic link).

        Inverse document frequency style weighting.
        """
        count = self.index.get_keyword_count(keyword)
        if count <= 1:
            return 0.1  # Very specific — almost direct link
        elif count <= 5:
            return 0.3  # Fairly specific
        elif count <= 20:
            return 0.6  # Moderate
        elif count <= 50:
            return 0.8  # Common
        else:
            return 1.0  # Very common — weak link

    def recall(
        self,
        seed_keywords: List[str],
        max_results: int = 8,
        max_cost: float = 3.0,
        gating_width: float = 0.5,
        exclude_ids: Set[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Dijkstra traversal from seed keywords through the memory graph.

        Args:
            seed_keywords: Starting concept keywords
            max_results: How many memories to return
            max_cost: Maximum graph distance to explore
            gating_width: How wide to explore (from oscillator state)
                         0.0 = very tight (only direct keyword matches)
                         1.0 = very loose (follow long chains)
            exclude_ids: Memory IDs to skip

        Returns:
            List of dicts with memory_id, cost, path, _retrieval_source
        """
        if not seed_keywords:
            return []

        exclude_ids = exclude_ids or set()

        # Priority queue: (cost, memory_id, path_taken)
        pq: List[Tuple[float, str, List[str]]] = []
        visited_memories: Set[str] = set()
        results: List[Dict[str, Any]] = []

        # Effective max cost scales with gating width
        # Tight gating = only explore nearby. Loose = wander far.
        effective_max_cost = max_cost * (0.3 + gating_width * 0.7)

        # Seed: find all memories for the seed keywords
        for kw in seed_keywords:
            kw = kw.lower().strip()
            if not kw:
                continue
            weight = self._keyword_weight(kw)
            for mem_id in self.index.get_memories_for_keyword(kw):
                if mem_id not in exclude_ids:
                    heapq.heappush(pq, (weight, mem_id, [kw]))

        while pq and len(results) < max_results:
            cost, mem_id, path = heapq.heappop(pq)

            if mem_id in visited_memories:
                continue
            if cost > effective_max_cost:
                break  # Too far — stop exploring

            visited_memories.add(mem_id)
            results.append({
                "memory_id": mem_id,
                "cost": cost,
                "path": path,  # The keyword chain that got us here
                "_retrieval_source": "dijkstra",
            })

            # Explore this memory's OTHER keywords (lateral jump)
            mem_keywords = self.index.get_keywords_for_memory(mem_id)
            for next_kw in mem_keywords:
                if next_kw in path:
                    continue  # Don't loop back through same keyword

                next_weight = self._keyword_weight(next_kw)
                next_cost = cost + next_weight

                if next_cost > effective_max_cost:
                    continue

                # Find memories reachable through this keyword
                for next_mem in self.index.get_memories_for_keyword(next_kw):
                    if next_mem not in visited_memories and next_mem not in exclude_ids:
                        heapq.heappush(pq, (
                            next_cost,
                            next_mem,
                            path + [next_kw]
                        ))

        return results

    def recall_with_shortcuts(
        self,
        seed_keywords: List[str],
        max_results: int = 8,
        max_cost: float = 3.0,
        gating_width: float = 0.5,
        exclude_ids: Set[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhanced recall: check traversal shortcuts before Dijkstra.

        1. Find memories matching seed keywords (same as before)
        2. For each found memory, check traversal links (shortcuts)
        3. Shortcut targets get added to results with reduced cost
        4. THEN run Dijkstra for anything shortcuts didn't find
        5. Record traversal for lazy link creation
        """
        if not DIJKSTRA_CONFIG.get("use_shortcuts", True) or not self.lazy_links:
            return self.recall(seed_keywords, max_results, max_cost, gating_width, exclude_ids)

        exclude_ids = exclude_ids or set()
        results: List[Dict[str, Any]] = []
        visited: Set[str] = set()

        # Phase 1: Direct keyword matches
        direct_matches: List[Dict[str, Any]] = []
        for kw in seed_keywords:
            kw = kw.lower().strip()
            if not kw:
                continue
            for mem_id in self.index.get_memories_for_keyword(kw):
                if mem_id not in visited and mem_id not in exclude_ids:
                    weight = self._keyword_weight(kw)
                    direct_matches.append({
                        "memory_id": mem_id,
                        "cost": weight,
                        "path": [kw],
                        "_retrieval_source": "keyword_direct",
                    })
                    visited.add(mem_id)

        # Sort by cost and take top half for results
        direct_matches.sort(key=lambda m: m["cost"])
        results.extend(direct_matches[:max_results // 2])

        # Phase 2: Follow traversal links from direct matches (SHORTCUTS)
        min_strength = DIJKSTRA_CONFIG.get("min_shortcut_strength", 0.15)
        for match in direct_matches[:3]:  # Top 3 direct matches
            shortcuts = self.lazy_links.get_direct_links(
                match["memory_id"], min_strength=min_strength
            )
            for link in shortcuts:
                target_id = link["target"]
                if target_id not in visited and target_id not in exclude_ids:
                    # Shortcut cost = original cost reduced by link strength
                    shortcut_cost = match["cost"] + (1.0 - link["strength"]) * 0.5
                    results.append({
                        "memory_id": target_id,
                        "cost": shortcut_cost,
                        "path": match["path"] + [f"→shortcut({link['strength']:.1f})"],
                        "_retrieval_source": "traversal_shortcut",
                        "_link_strength": link["strength"],
                        "_via_keywords": link.get("via_keywords", []),
                    })
                    visited.add(target_id)

        # Phase 3: Dijkstra for remaining slots
        if len(results) < max_results:
            dijkstra_results = self.recall(
                seed_keywords,
                max_results=max_results - len(results),
                max_cost=max_cost,
                gating_width=gating_width,
                exclude_ids=visited | exclude_ids
            )
            for r in dijkstra_results:
                if r["memory_id"] not in visited:
                    results.append(r)
                    visited.add(r["memory_id"])

        # Record this traversal → creates new shortcuts for next time
        if DIJKSTRA_CONFIG.get("create_traversal_links", True):
            self.lazy_links.record_traversal(results)

        return sorted(results, key=lambda r: r["cost"])[:max_results]


# ═══════════════════════════════════════════════════════════════════════════
# LAZY LINK CREATOR — Links form through USE
# ═══════════════════════════════════════════════════════════════════════════

class LazyLinkCreator:
    """
    Creates direct memory-to-memory links when Dijkstra paths
    are actually used. The graph densifies through recall.

    First recall: trial → [keyword: chrome] → Chrome escaped
        No direct link exists. Traversed via shared keyword.

    After recall: CREATE link between trial memory and Chrome memory.
        Link carries: the keyword path, timestamp, strength.

    Second recall: trial → Chrome escaped (DIRECT, no keyword hop)
        Shortcut exists. Link strengthened.
    """

    def __init__(self, persist_path: str = None):
        # Traversal links: separate from co-activation links
        # These are EARNED through use, not pre-computed
        self._traversal_links: Dict[str, List[Dict]] = {}  # mem_id → links
        self.persist_path = persist_path
        self._dirty = False

        if persist_path:
            self._load()

    def record_traversal(self, recall_results: List[Dict[str, Any]]):
        """
        After Dijkstra recall returns results, create direct links
        between memories that were recalled together.

        Only link memories that are >1 hop apart in the keyword graph.
        Direct keyword matches (1 hop) don't need shortcut links —
        they're already fast to find.
        """
        if len(recall_results) < 2:
            return

        # Find memory pairs that are more than 1 hop apart
        for i, mem_a in enumerate(recall_results):
            for mem_b in recall_results[i+1:]:
                path_a = mem_a.get("path", [])
                path_b = mem_b.get("path", [])

                # Only create link if they're connected through
                # DIFFERENT keywords (lateral association)
                shared_path = set(path_a) & set(path_b)
                unique_path = (set(path_a) | set(path_b)) - shared_path

                # Filter out shortcut markers from path
                unique_path = {p for p in unique_path if not p.startswith("→shortcut")}

                if len(unique_path) > 0:
                    # These memories are connected through a chain
                    # that spans multiple concepts. Worth linking directly.
                    self._create_traversal_link(
                        mem_a["memory_id"],
                        mem_b["memory_id"],
                        via_keywords=list(unique_path),
                        cost=abs(mem_a.get("cost", 0) - mem_b.get("cost", 0))
                    )

    def _create_traversal_link(
        self,
        mem_id_a: str,
        mem_id_b: str,
        via_keywords: List[str],
        cost: float
    ):
        """
        Create a bidirectional traversal link between two memories.
        If link already exists, strengthen it.
        """
        # Check if link exists and strengthen
        existing = self._find_link(mem_id_a, mem_id_b)
        if existing:
            # Strengthen: each traversal increases link weight
            max_strength = DIJKSTRA_CONFIG.get("max_link_strength", 1.0)
            strength_gain = DIJKSTRA_CONFIG.get("strength_per_traversal", 0.15)
            existing["strength"] = min(max_strength, existing["strength"] + strength_gain)
            existing["traversal_count"] += 1
            existing["last_traversed"] = time.time()
            self._dirty = True
            return

        # Create new link
        initial_strength = DIJKSTRA_CONFIG.get("initial_link_strength", 0.2)
        link = {
            "source": mem_id_a,
            "target": mem_id_b,
            "type": "traversal",  # Distinct from "coactive" or "emotional_match"
            "via_keywords": via_keywords,
            "strength": initial_strength,
            "traversal_count": 1,
            "created": time.time(),
            "last_traversed": time.time(),
        }

        # Store for source
        if mem_id_a not in self._traversal_links:
            self._traversal_links[mem_id_a] = []
        self._traversal_links[mem_id_a].append(link)

        # Reverse link
        reverse_link = dict(link)
        reverse_link["source"] = mem_id_b
        reverse_link["target"] = mem_id_a
        if mem_id_b not in self._traversal_links:
            self._traversal_links[mem_id_b] = []
        self._traversal_links[mem_id_b].append(reverse_link)

        self._dirty = True
        log.debug(f"[LAZY_LINK] Created traversal link: {mem_id_a[:8]}... ↔ {mem_id_b[:8]}... via {via_keywords}")

    def _find_link(self, mem_a: str, mem_b: str) -> Optional[Dict]:
        """Find existing traversal link between two memories."""
        for link in self._traversal_links.get(mem_a, []):
            if link["target"] == mem_b:
                return link
        return None

    def get_direct_links(
        self,
        memory_id: str,
        min_strength: float = 0.1
    ) -> List[Dict]:
        """
        Get all direct traversal links for a memory.
        These are shortcuts created by previous recalls.
        """
        links = self._traversal_links.get(memory_id, [])
        return [l for l in links if l["strength"] >= min_strength]

    def decay_unused_links(self, decay_rate: float = None):
        """
        Periodically decay links that haven't been traversed recently.
        Links that were only used once and never again fade away.
        Links that are used repeatedly persist.

        Run this during overnight curation.
        """
        if decay_rate is None:
            decay_rate = DIJKSTRA_CONFIG.get("link_decay_rate", 0.01)

        now = time.time()
        total_decayed = 0
        total_removed = 0

        for mem_id in list(self._traversal_links.keys()):
            links = self._traversal_links[mem_id]
            surviving = []

            for link in links:
                age = now - link["last_traversed"]
                days_old = age / 86400

                # Decay: lose decay_rate per day since last traversal
                # Strong links (high traversal_count) decay slower
                effective_rate = decay_rate / max(1, link["traversal_count"] * 0.5)
                decay_amount = effective_rate * days_old
                link["strength"] -= decay_amount

                if link["strength"] > 0.05:
                    surviving.append(link)
                    if decay_amount > 0.001:
                        total_decayed += 1
                else:
                    total_removed += 1

            if surviving:
                self._traversal_links[mem_id] = surviving
            else:
                del self._traversal_links[mem_id]

        if total_decayed > 0 or total_removed > 0:
            self._dirty = True
            log.info(f"[LAZY_LINK] Decay: {total_decayed} weakened, {total_removed} removed")

    def get_stats(self) -> Dict[str, Any]:
        """Return link statistics."""
        total_links = sum(len(links) for links in self._traversal_links.values())
        strengths = [
            l["strength"]
            for links in self._traversal_links.values()
            for l in links
        ]
        return {
            "total_memories_with_links": len(self._traversal_links),
            "total_links": total_links // 2,  # Divide by 2 since bidirectional
            "avg_strength": sum(strengths) / len(strengths) if strengths else 0,
            "max_strength": max(strengths) if strengths else 0,
        }

    def save(self):
        """Persist to disk as JSON."""
        if not self.persist_path or not self._dirty:
            return
        try:
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(self._traversal_links, f, indent=2)
            self._dirty = False
            log.debug(f"[LAZY_LINK] Saved {len(self._traversal_links)} memory link sets")
        except Exception as e:
            log.warning(f"[LAZY_LINK] Failed to save: {e}")

    def _load(self):
        """Load from disk."""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                self._traversal_links = json.load(f)
            log.debug(f"[LAZY_LINK] Loaded {len(self._traversal_links)} memory link sets")
        except Exception as e:
            log.warning(f"[LAZY_LINK] Failed to load: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# CONCEPT TAGGING — Extract keywords from memories
# ═══════════════════════════════════════════════════════════════════════════

def tag_memory_with_concepts(
    memory: Dict,
    text: str,
    emotion_tags: List[str] = None,
    entity_names: List[str] = None,
    osc_state: Dict = None,
    ollama_func=None
) -> List[str]:
    """
    Extract concept keywords from a memory at storage time.
    These become the nodes in the keyword graph.

    Sources of keywords:
    1. Named entities (people, places, pets) — from entity extractor
    2. Emotion labels — from emotion extractor
    3. Topic/concept words — from the local LLM (optional)
    4. Oscillator band at encoding — cognitive state tag
    5. Temporal tags — time of day, day of week

    Args:
        memory: The memory dict to tag (modified in place)
        text: The text content to extract concepts from
        emotion_tags: Pre-extracted emotion labels
        entity_names: Pre-extracted entity names
        osc_state: Oscillator state at encoding time
        ollama_func: Optional function to call Ollama for concept extraction
                     Signature: ollama_func(prompt, max_tokens=30) -> str

    Returns:
        List of keyword strings (also stored in memory["concept_keywords"])
    """
    keywords = set()

    # 1. Entity names (already extracted)
    if entity_names:
        for name in entity_names:
            if name and len(name) > 1:
                keywords.add(name.lower().strip())

    # 2. Emotion labels (already extracted)
    if emotion_tags:
        for emo in emotion_tags[:5]:  # Top 5 emotions
            if emo:
                keywords.add(emo.lower().strip())

    # 3. Concept extraction via local LLM (optional)
    if ollama_func and text and DIJKSTRA_CONFIG.get("tag_new_memories", True):
        try:
            concept_prompt = f"""Extract 3-5 concept keywords from this text.
Return ONLY comma-separated keywords, nothing else.
Focus on concrete nouns, actions, and topics — not feelings or adjectives.

Text: {text[:300]}

Keywords:"""

            concepts = ollama_func(concept_prompt, max_tokens=30)
            if concepts:
                for kw in concepts.split(","):
                    kw = kw.strip().lower()
                    if kw and len(kw) > 2 and len(kw) < 30:
                        # Filter out common stopwords
                        if kw not in {"the", "and", "but", "for", "that", "this", "with"}:
                            keywords.add(kw)
        except Exception as e:
            log.debug(f"[CONCEPT_TAG] Ollama extraction failed: {e}")

    # 4. Oscillator band at encoding
    if osc_state:
        band = osc_state.get("band", "alpha")
        keywords.add(f"state:{band}")

    # 5. Temporal tags
    now = datetime.now()
    keywords.add(f"hour:{now.hour}")
    keywords.add(f"day:{now.strftime('%A').lower()}")

    # 6. Simple keyword extraction from text (fallback if no Ollama)
    if not ollama_func and text:
        # Extract capitalized words (likely entities/proper nouns)
        import re
        capitalized = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        for word in capitalized[:5]:
            keywords.add(word.lower())

    keyword_list = list(keywords)
    memory["concept_keywords"] = keyword_list
    return keyword_list


def extract_keywords_from_context(recent_context: str, max_keywords: int = 5) -> List[str]:
    """
    Extract seed keywords from recent conversation context.
    Used to seed Dijkstra traversal.

    Simple extraction: capitalized words, quoted phrases, entities.
    """
    import re
    keywords = set()

    # Common words that are never useful as Dijkstra seeds
    _stopwords = {
        # Pronouns & determiners
        "about", "would", "could", "should", "there", "their", "which",
        "where", "these", "those", "something", "anything", "everything",
        "nothing", "someone", "anyone", "everyone", "other", "another",
        "being", "doing", "having", "going", "getting", "making",
        "coming", "taking", "looking", "thinking", "feeling", "trying",
        "still", "really", "actually", "basically", "probably", "maybe",
        "always", "never", "sometimes", "already", "enough", "quite",
        # Conversational filler
        "thing", "things", "stuff", "right", "though", "because",
        "since", "until", "while", "during", "between", "through",
        "before", "after", "under", "above", "might", "every",
        # Short common words that slip through
        "very", "likely", "caught", "attention", "seeing", "instant",
        "update", "update_time", "content", "appears", "noticed",
        "seems", "moved", "changed", "watching", "noticed", "heard",
        "described", "mentioned", "asked", "answered", "responded",
        # Common verbs (base forms get through the 5-char filter)
        "think", "feels", "seems", "looks", "wants", "needs",
        "keeps", "makes", "takes", "comes", "gives", "means",
        "knows", "says", "goes", "does", "works", "finds",
        "starts", "turns", "shows", "holds", "tells", "calls",
        # System/meta words common in wrapper context
        "system", "memory", "state", "current", "context", "response",
        "processing", "oscillator", "coherence", "dominant",
        "settled", "accompanied", "integrating", "detected",
        "visual", "sensor", "camera", "frame", "image", "scene",
        "status", "check", "update", "connection", "connected",
        # Common sentence-start words caught by caps regex
        "that", "this", "what", "when", "just", "like", "more",
        "been", "have", "from", "with", "also", "into", "much",
    }

    # Capitalized words (likely names/entities) — but filter common words
    caps = re.findall(r'\b[A-Z][a-z]{2,}\b', recent_context)
    for word in caps[:5]:
        if word.lower() not in _stopwords:
            keywords.add(word.lower())

    # Quoted phrases
    quoted = re.findall(r'"([^"]+)"', recent_context)
    for phrase in quoted[:2]:
        keywords.add(phrase.lower().strip())

    # Longer words (likely topic-specific)
    words = re.findall(r'\b[a-z]{5,}\b', recent_context.lower())
    word_freq = {}
    for w in words:
        if w not in _stopwords:
            word_freq[w] = word_freq.get(w, 0) + 1

    # Top frequent words
    for word, _ in sorted(word_freq.items(), key=lambda x: -x[1])[:5]:
        keywords.add(word)

    # Final cleanup: remove punctuation, very short words, and metadata field names
    cleaned = set()
    _meta_fields = {"update_time", "content", "timestamp", "added_timestamp",
                    "importance_score", "memory_type", "current_layer", "doc_id"}
    for kw in keywords:
        # Must be at least 3 chars, only letters/spaces, not a metadata field
        if (len(kw) >= 3
            and re.match(r'^[a-z\s]+$', kw)
            and kw not in _meta_fields
            and kw not in _stopwords):
            cleaned.add(kw)

    return list(cleaned)[:max_keywords]


def get_gating_width(osc_state: Dict) -> float:
    """
    Calculate gating width from oscillator state.

    Theta-dominant = loose associations (wide exploration)
    Beta-dominant = tight focus (narrow exploration)
    Alpha = balanced

    Returns value between 0.0 (tight) and 1.0 (loose)
    """
    if not osc_state:
        return 0.5  # Default balanced

    band_power = osc_state.get("band_power", {})
    if not band_power:
        band = osc_state.get("band", "alpha")
        # Approximate from dominant band
        band_widths = {
            "delta": 0.8,   # Deep/dreamy = loose
            "theta": 0.7,   # Creative/associative = loose
            "alpha": 0.5,   # Relaxed focus = balanced
            "beta": 0.3,    # Active focus = tight
            "gamma": 0.4,   # High processing = somewhat tight
        }
        return band_widths.get(band, 0.5)

    # Calculate from band powers
    theta = band_power.get("theta", 0.2)
    alpha = band_power.get("alpha", 0.4)
    beta = band_power.get("beta", 0.2)

    # Theta promotes loose, beta promotes tight
    looseness = theta * 1.5 - beta * 1.2 + alpha * 0.5

    # Clamp to 0.1-0.9 range
    return max(0.1, min(0.9, 0.5 + looseness))


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATED RECALL — Combines all retrieval methods
# ═══════════════════════════════════════════════════════════════════════════

class KeywordGraphRetriever:
    """
    High-level interface for keyword graph retrieval.

    Combines:
    - KeywordIndex for concept storage
    - DijkstraRecall for graph traversal
    - LazyLinkCreator for shortcut management
    """

    def __init__(self, persist_dir: str, entity: str = "kay"):
        self.entity = entity
        self.persist_dir = persist_dir

        # Ensure directory exists
        os.makedirs(persist_dir, exist_ok=True)

        # Initialize components
        self.keyword_index = KeywordIndex(
            persist_path=os.path.join(persist_dir, f"{entity}_keyword_index.json")
        )
        self.lazy_links = LazyLinkCreator(
            persist_path=os.path.join(persist_dir, f"{entity}_traversal_links.json")
        )
        self.dijkstra = DijkstraRecall(self.keyword_index, self.lazy_links)

    def index_memory(
        self,
        memory_id: str,
        text: str,
        emotion_tags: List[str] = None,
        entity_names: List[str] = None,
        osc_state: Dict = None,
        ollama_func=None
    ) -> List[str]:
        """
        Tag a memory with concepts and add to the keyword index.

        Returns the list of keywords extracted.
        """
        memory = {"id": memory_id}
        keywords = tag_memory_with_concepts(
            memory, text, emotion_tags, entity_names, osc_state, ollama_func
        )
        self.keyword_index.add_memory(memory_id, keywords)
        return keywords

    def recall(
        self,
        seed_keywords: List[str] = None,
        context: str = None,
        osc_state: Dict = None,
        max_results: int = 5,
        exclude_ids: Set[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories via keyword graph traversal.

        Args:
            seed_keywords: Explicit keywords to start from
            context: Text context to extract keywords from (if no explicit seeds)
            osc_state: Oscillator state for gating width
            max_results: Maximum memories to return
            exclude_ids: Memory IDs to exclude

        Returns:
            List of memory dicts with memory_id, cost, path, _retrieval_source
        """
        # Get seed keywords
        if not seed_keywords and context:
            seed_keywords = extract_keywords_from_context(context)

        if not seed_keywords:
            return []

        # Get gating width from oscillator state
        gating_width = get_gating_width(osc_state)
        max_cost = DIJKSTRA_CONFIG.get("max_cost", 3.0)

        # Use shortcuts if available
        if DIJKSTRA_CONFIG.get("use_shortcuts", True):
            results = self.dijkstra.recall_with_shortcuts(
                seed_keywords=seed_keywords,
                max_results=max_results,
                max_cost=max_cost,
                gating_width=gating_width,
                exclude_ids=exclude_ids
            )
        else:
            results = self.dijkstra.recall(
                seed_keywords=seed_keywords,
                max_results=max_results,
                max_cost=max_cost,
                gating_width=gating_width,
                exclude_ids=exclude_ids
            )

        return results

    def remove_memory(self, memory_id: str):
        """Remove a memory from the keyword index."""
        self.keyword_index.remove_memory(memory_id)

    def decay_links(self):
        """Run link decay (call during overnight curation)."""
        self.lazy_links.decay_unused_links()

    def save(self):
        """Persist all data to disk."""
        self.keyword_index.save()
        self.lazy_links.save()

    def get_stats(self) -> Dict[str, Any]:
        """Return combined statistics."""
        return {
            "keyword_index": self.keyword_index.get_stats(),
            "lazy_links": self.lazy_links.get_stats(),
        }
