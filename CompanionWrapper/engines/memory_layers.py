# engines/memory_layers.py
"""
Two-Tier Memory System for the entityZero
Implements working -> long-term memory transitions
Uses ULTRAMAP pressure x recursion for importance-based persistence
"""

import json
import os
import re
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from config import VERBOSE_DEBUG

# Import LLM for narrative synthesis
try:
    from integrations.llm_integration import client, MODEL
except ImportError:
    client = None
    MODEL = None

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"



class MemoryLayerManager:
    """
    Manages TWO-TIER memory system:
    - Working Memory: Immediate context (last 15 turns)
    - Long-Term Memory: Everything older than working memory

    Memories transition from working to long-term based on:
    - Age (oldest working memories age out to long-term)
    - Capacity management (when working memory is full)

    NO EPISODIC OR SEMANTIC TIERS - This prevents regression to three-tier architecture.
    """

    def __init__(self, file_path: str = None):
        if file_path is None:
            # Check for persona isolation via environment variable (multi-persona mode)
            state_dir = os.environ.get("COMPANION_STATE_DIR")
            if state_dir:
                file_path = os.path.join(state_dir, "memory", "memory_layers.json")
            else:
                # Default: ./memory relative to wrapper root
                file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "memory_layers.json")
        self.file_path = file_path

        # TWO-TIER STORAGE ONLY
        self.working_memory: List[Dict[str, Any]] = []  # Most recent memories (last 15 turns)
        self.long_term_memory: List[Dict[str, Any]] = []  # Everything older

        # REGRESSION PREVENTION: Ensure no three-tier attributes exist
        assert not hasattr(self, 'episodic_memory'), "THREE-TIER REGRESSION DETECTED: episodic_memory exists"
        assert not hasattr(self, 'semantic_memory'), "THREE-TIER REGRESSION DETECTED: semantic_memory exists"

        # Layer configuration
        self.working_capacity = 15  # Max memories in working layer
        # Long-term has no capacity limit

        # Decay configuration
        self.working_decay_halflife = 3  # Days until working memory strength halves
        self.longterm_decay_halflife = 30  # Days until long-term memory strength halves

        # Track file modification time for external change detection
        self._last_file_mtime = None

        # Operation tracking for summary logging
        self._reset_turn_stats()

        # Load from disk
        self._load_from_disk()

        # Confirm two-tier architecture after load
        print(f"{etag('MEMORY')}  Two-tier architecture confirmed (working + long-term)")

    def _reset_turn_stats(self):
        """Reset per-turn operation counters."""
        self.turn_stats = {
            'added': 0,
            'promoted_to_longterm': 0,
            'pruned': 0,
            'accessed': 0
        }

    def print_turn_summary(self):
        """Print summary of memory layer operations for this turn."""
        stats = self.turn_stats

        # Only print if there were operations
        if sum(stats.values()) > 0:
            parts = []
            if stats['added'] > 0:
                parts.append(f"{stats['added']} added")
            if stats['promoted_to_longterm'] > 0:
                parts.append(f"{stats['promoted_to_longterm']} -> long-term")
            if stats['pruned'] > 0:
                parts.append(f"{stats['pruned']} pruned")

            if parts:
                summary = ", ".join(parts)
                print(f"{etag('MEMORY LAYERS')} {summary}")

        # Reset for next turn
        self._reset_turn_stats()

    def _load_from_disk(self):
        """Load memory layers from JSON (with migration from three-tier if needed)."""
        try:
            # Track file modification time for external change detection
            if os.path.exists(self.file_path):
                self._last_file_mtime = os.path.getmtime(self.file_path)

            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # TWO-TIER: Load only working and long-term
            self.working_memory = data.get("working", [])
            self.long_term_memory = data.get("long_term", [])

            # MIGRATION: If old three-tier data exists, migrate it
            if "episodic" in data or "semantic" in data:
                print(f"{etag('MEMORY LAYERS')}  Migrating three-tier -> two-tier architecture...")

                episodic = data.get("episodic", [])
                semantic = data.get("semantic", [])

                # Merge episodic + semantic into long-term
                self.long_term_memory.extend(episodic)
                self.long_term_memory.extend(semantic)

                # Update layer tags
                for mem in self.long_term_memory:
                    mem["current_layer"] = "long_term"

                print(f"{etag('MEMORY LAYERS')} Migrated {len(episodic)} episodic + {len(semantic)} semantic -> {len(self.long_term_memory)} long-term")

                # Save migrated data
                self._save_to_disk()

            print(f"{etag('MEMORY LAYERS')} Loaded {len(self.working_memory)} working, "
                  f"{len(self.long_term_memory)} long-term")

        except FileNotFoundError:
            print(f"{etag('MEMORY LAYERS')}  No existing layers found, starting fresh")
            self._last_file_mtime = None
        except Exception as e:
            print(f"{etag('MEMORY LAYERS')} Error loading layers: {e}")

    def _save_to_disk(self):
        """Save memory layers to JSON (TWO-TIER ONLY).

        Includes external change detection: if another process (like a repair script)
        modified the file since we last loaded/saved, merge those changes instead
        of blindly overwriting them.
        """
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Check for external modifications
        if os.path.exists(self.file_path) and self._last_file_mtime is not None:
            current_mtime = os.path.getmtime(self.file_path)
            if current_mtime > self._last_file_mtime:
                # File was modified externally! Merge instead of overwrite.
                self._merge_external_changes()

        # TWO-TIER STRUCTURE
        data = {
            "working": self.working_memory,
            "long_term": self.long_term_memory
        }

        # CRITICAL: NO episodic or semantic keys
        # This prevents three-tier regression

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Update our tracked mtime
        self._last_file_mtime = os.path.getmtime(self.file_path)

    def _merge_external_changes(self):
        """
        Merge externally-added memories into our in-memory state.

        Called when we detect the file was modified by another process
        (e.g., repair_document_memories.py).

        Strategy: Add any memories from disk that we don't already have.
        Uses doc_id + type as unique identifier for document memories,
        and timestamp + fact hash for other memories.
        """
        print(f"{etag('MEMORY LAYERS')}  External file modification detected - merging changes...")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                disk_data = json.load(f)

            disk_working = disk_data.get("working", [])
            disk_longterm = disk_data.get("long_term", [])

            # Build set of memory identifiers we already have
            def get_memory_id(mem):
                """Generate unique identifier for a memory."""
                doc_id = mem.get('doc_id')
                mem_type = mem.get('type', '')
                if doc_id and mem_type in ['document_content', 'shared_understanding_moment']:
                    # Document memories: use doc_id + type
                    return f"{doc_id}:{mem_type}"
                else:
                    # Other memories: use timestamp + fact hash
                    ts = mem.get('timestamp', mem.get('added_timestamp', ''))
                    fact = mem.get('fact', mem.get('user_input', ''))[:50]
                    return f"{ts}:{hash(fact)}"

            existing_ids = set()
            for mem in self.working_memory + self.long_term_memory:
                existing_ids.add(get_memory_id(mem))

            # Find memories on disk that we don't have
            new_working = 0
            for mem in disk_working:
                mem_id = get_memory_id(mem)
                if mem_id not in existing_ids:
                    self.working_memory.append(mem)
                    existing_ids.add(mem_id)
                    new_working += 1

            new_longterm = 0
            for mem in disk_longterm:
                mem_id = get_memory_id(mem)
                if mem_id not in existing_ids:
                    self.long_term_memory.append(mem)
                    existing_ids.add(mem_id)
                    new_longterm += 1

            if new_working > 0 or new_longterm > 0:
                print(f"{etag('MEMORY LAYERS')} Merged {new_working} working + {new_longterm} long-term memories from external changes")
            else:
                print(f"{etag('MEMORY LAYERS')}  No new memories to merge from external changes")

        except Exception as e:
            print(f"{etag('MEMORY LAYERS')} Error merging external changes: {e}")
            import traceback
            traceback.print_exc()

    def _find_similar_longterm_fact(self, fact: str, entities: List[str], threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        Check if long-term tier already has a similar fact.

        Prevents duplicate long-term memories (e.g., "itself" vs "herself" for same entity).

        Args:
            fact: Fact text to check
            entities: Entities in the fact
            threshold: Minimum similarity to consider duplicate (default 0.7 = 70%)

        Returns:
            Existing similar memory, or None
        """
        if not fact:
            return None

        # Extract keywords from fact
        fact_lower = fact.lower()
        fact_words = set(word.strip(".,!?") for word in fact_lower.split() if len(word.strip(".,!?")) > 3)

        target_entities = set(entities) if entities else set()

        for mem in self.long_term_memory:
            mem_fact = mem.get("fact", mem.get("user_input", ""))
            if not mem_fact:
                continue

            mem_entities = set(mem.get("entities", []))

            # Fast entity overlap check
            entity_overlap = len(target_entities.intersection(mem_entities)) if target_entities and mem_entities else 0
            entity_similarity = entity_overlap / max(len(target_entities), len(mem_entities)) if (target_entities or mem_entities) else 0

            # If entities differ significantly, not a duplicate
            if entity_similarity < 0.5 and target_entities:
                continue

            # Detailed keyword overlap check
            mem_words = set(word.strip(".,!?") for word in mem_fact.lower().split() if len(word.strip(".,!?")) > 3)

            if not fact_words or not mem_words:
                continue

            word_overlap = len(fact_words.intersection(mem_words))
            word_similarity = word_overlap / max(len(fact_words), len(mem_words))

            # Combined similarity: 70% keywords + 30% entities
            combined_similarity = (word_similarity * 0.7) + (entity_similarity * 0.3)

            if combined_similarity >= threshold:
                return mem

        return None

    def add_memory(self, memory: Dict[str, Any], layer: str = "working", session_order: Optional[int] = None, session_id: Optional[str] = None):
        """
        Add a memory to specified layer.

        Args:
            memory: Memory dict with fact, perspective, emotion_tags, etc.
            layer: "working" or "long_term" (NO OTHER OPTIONS)
            session_order: Sequential session number (e.g., 1, 2, 3...)
            session_id: Unique session identifier (timestamp-based)
        """
        # Validate layer
        if layer not in ["working", "long_term"]:
            print(f"{etag('MEMORY LAYERS ERROR')} Invalid layer '{layer}' - must be 'working' or 'long_term'")
            layer = "working"  # Default to working

        # Ensure memory has required metadata
        if "added_timestamp" not in memory:
            memory["added_timestamp"] = datetime.now().isoformat()
        if "access_count" not in memory:
            memory["access_count"] = 0
        if "last_accessed" not in memory:
            memory["last_accessed"] = datetime.now().isoformat()
        if "importance_score" not in memory:
            memory["importance_score"] = 0.0
        if "current_strength" not in memory:
            memory["current_strength"] = 1.0
        if "current_layer" not in memory:
            memory["current_layer"] = layer
        
        # SESSION TAGGING FIX: Add session context for temporal awareness
        if "session_order" not in memory and session_order is not None:
            memory["session_order"] = session_order
        if "session_id" not in memory and session_id is not None:
            memory["session_id"] = session_id

        # Deduplicate long-term memories before adding
        if layer == "long_term":
            fact = memory.get("fact", memory.get("user_input", ""))
            entities = memory.get("entities", [])
            existing = self._find_similar_longterm_fact(fact, entities, threshold=0.7)

            if existing:
                print(f"{etag('MEMORY DEDUP')} Skipping duplicate long-term fact: {fact[:60]}...")
                print(f"{etag('MEMORY DEDUP')} Similar to existing: {existing.get('fact', existing.get('user_input', ''))[:60]}...")
                return  # Don't add duplicate

        # Add to appropriate layer
        if layer == "working":
            self.working_memory.append(memory)
            self._enforce_working_capacity()
        elif layer == "long_term":
            self.long_term_memory.append(memory)

        # Track operation
        self.turn_stats['added'] += 1

        if VERBOSE_DEBUG:
            print(f"{etag('MEMORY LAYERS')} Added to {layer}: {memory.get('fact', memory.get('user_input', ''))[:60]}...")

        self._save_to_disk()

    def _enforce_working_capacity(self):
        """Keep working memory under capacity by aging out to long-term."""
        while len(self.working_memory) > self.working_capacity:
            # Remove oldest memory from working
            oldest_mem = self.working_memory.pop(0)

            # Age out to long-term (no pruning - all memories persist)
            oldest_mem["current_layer"] = "long_term"
            self.long_term_memory.append(oldest_mem)

            # Track operation
            self.turn_stats['promoted_to_longterm'] += 1

            if VERBOSE_DEBUG:
                print(f"{etag('MEMORY LAYERS')} Aged to long-term: {oldest_mem.get('fact', oldest_mem.get('user_input', ''))[:40]}...")

    def access_memory(self, memory: Dict[str, Any]):
        """
        Record that a memory was accessed (retrieved).
        Updates access count and timestamp.
        """
        memory["access_count"] = memory.get("access_count", 0) + 1
        memory["last_accessed"] = datetime.now().isoformat()

        # Track operation
        self.turn_stats['accessed'] += 1

        # Note: No promotion needed in two-tier system
        # Memories stay in their layer until capacity pushes them

        self._save_to_disk()

    def apply_temporal_decay(self):
        """
        Apply time-based decay to both working and long-term memories.

        Decay formula: strength = initial_strength × 0.5^(age_days / halflife)
        Modified by:
        - Importance: effective_halflife = base_halflife × (1 + importance)
        - Entities: Memories about tracked entities get 2x longer retention
        - Emotions: Each emotion tag adds 20% longer retention
        """
        current_time = datetime.now()

        # Decay working memory
        for mem in self.working_memory:
            # Skip if no timestamp (legacy memory)
            if "added_timestamp" not in mem:
                continue
                
            age_days = self._get_age_days(mem["added_timestamp"], current_time)
            importance = mem.get("importance_score", 0.0)

            # Calculate decay protection multipliers
            entity_multiplier = self._calculate_entity_protection(mem)
            emotion_multiplier = self._calculate_emotion_protection(mem)

            # Higher importance + entities + emotions = much slower decay
            effective_halflife = self.working_decay_halflife * (1 + importance) * entity_multiplier * emotion_multiplier
            decay_factor = 0.5 ** (age_days / effective_halflife)

            mem["current_strength"] = decay_factor

        # Decay long-term memory
        for mem in self.long_term_memory:
            # Skip if no timestamp (legacy memory)
            if "added_timestamp" not in mem:
                continue
                
            age_days = self._get_age_days(mem["added_timestamp"], current_time)
            importance = mem.get("importance_score", 0.0)

            # Calculate decay protection multipliers
            entity_multiplier = self._calculate_entity_protection(mem)
            emotion_multiplier = self._calculate_emotion_protection(mem)

            # Higher importance + entities + emotions = much slower decay
            effective_halflife = self.longterm_decay_halflife * (1 + importance) * entity_multiplier * emotion_multiplier
            decay_factor = 0.5 ** (age_days / effective_halflife)

            mem["current_strength"] = decay_factor

        # Prune very weak memories (lowered threshold to be less aggressive)
        # Use .get() with default 1.0 to handle legacy memories missing current_strength
        self.long_term_memory = [m for m in self.long_term_memory if m.get("current_strength", 1.0) > 0.05]
        self.working_memory = [m for m in self.working_memory if m.get("current_strength", 1.0) > 0.05]

        self._save_to_disk()

    def _get_age_days(self, timestamp_str: str, current_time: datetime) -> float:
        """Calculate age in days from ISO timestamp string."""
        try:
            added_time = datetime.fromisoformat(timestamp_str)
            age = current_time - added_time
            return age.total_seconds() / 86400  # Convert to days
        except Exception:
            return 0.0

    def _calculate_entity_protection(self, memory: Dict[str, Any]) -> float:
        """
        Calculate decay protection multiplier based on tracked entities.

        Memories about tracked entities (people, pets, important things) get
        longer retention because they're part of ongoing relationships.

        Returns:
            Multiplier for halflife (1.0 = no boost, 2.0 = 2x longer retention)
        """
        entities = memory.get("entities", [])

        if not entities:
            return 1.0  # No entity protection

        # If memory mentions any tracked entity, protect it
        # 2x retention for entity-related memories
        return 2.0

    def _calculate_emotion_protection(self, memory: Dict[str, Any]) -> float:
        """
        Calculate decay protection multiplier based on emotional significance.

        Memories with more emotion tags are more emotionally significant and
        should last longer. Each emotion tag adds 20% longer retention.

        Returns:
            Multiplier for halflife (1.0 = no boost, 2.0 = 100% longer, etc.)
        """
        emotion_tags = memory.get("emotion_tags", [])

        if not emotion_tags:
            return 1.0  # No emotional protection

        # Each emotion tag adds 20% longer retention
        # 1 tag = 1.2x, 2 tags = 1.4x, 3 tags = 1.6x, etc.
        # Cap at 3.0x for extremely emotional memories (10+ tags)
        multiplier = 1.0 + (len(emotion_tags) * 0.2)
        return min(multiplier, 3.0)

    def _find_similar_narrative(self, entities: List[str], threshold: float = 0.6) -> Optional[Dict[str, Any]]:
        """
        Check if long-term tier already has a narrative covering similar entities.

        Prevents narrative spam by detecting duplicates before generation.

        Args:
            entities: Entities in the new memory
            threshold: Minimum entity overlap to consider duplicate (default 0.6 = 60%)

        Returns:
            Existing memory with similar narrative, or None
        """
        if not entities:
            return None

        target_entities = set(entities)

        for mem in self.long_term_memory:
            # Skip if no narrative
            if "narrative_summary" not in mem:
                continue

            mem_entities = set(mem.get("entities", []))

            # Calculate entity overlap
            if not mem_entities:
                continue

            overlap = len(target_entities.intersection(mem_entities))
            similarity = overlap / max(len(target_entities), len(mem_entities))

            # Found duplicate if high overlap
            if similarity >= threshold:
                return mem

        return None

    def _should_synthesize_narrative(self, memory: Dict[str, Any]) -> bool:
        """
        Check if memory qualifies for narrative synthesis (Flamekeeper integration).

        Narrative synthesis creates story summaries when memories consolidate to long-term tier.

        Args:
            memory: Memory being promoted to long-term

        Returns:
            True if narrative should be generated
        """
        # Only synthesize for memories with:
        # 0. NOT imported from documents (prevents confabulation about "investigating" document content)
        # 1. High importance (> 0.6)
        # 2. Part of a thread (has related memories)
        # 3. Emotional significance (emotion tags present)
        # 4. NO DUPLICATE narrative already exists

        # CRITICAL: Document imports should NEVER get narrative synthesis
        if memory.get("source_document") or memory.get("is_imported") or memory.get("doc_id"):
            print(f"{etag('NARRATIVE')} Skipping document import - narratives are for experiences, not readings")
            return False

        importance = memory.get("importance_score", 0)
        entities = memory.get("entities", [])
        emotion_tags = memory.get("emotion_tags", [])

        # Must be important
        if importance <= 0.6:
            return False

        # Must have entities (part of a story about something/someone)
        if len(entities) < 1:
            return False

        # Must have emotional weight (stories need feeling)
        if len(emotion_tags) < 1:
            return False

        # Check for existing similar narrative (prevents duplicates)
        existing = self._find_similar_narrative(entities, threshold=0.6)
        if existing:
            print(f"{etag('NARRATIVE')} Skipping duplicate - similar narrative already exists: {existing.get('narrative_summary', '')[:60]}...")
            return False

        return True

    def _find_related_memories(self, memory: Dict[str, Any], max_related: int = 5) -> List[Dict[str, Any]]:
        """
        Find memories related to the given memory for narrative synthesis.

        Looks for memories sharing entities and topics.

        Args:
            memory: Target memory
            max_related: Maximum number of related memories to find

        Returns:
            List of related memories
        """
        target_entities = set(memory.get("entities", []))
        target_topic = memory.get("topic", "")

        related = []

        # Search long-term memories (where narratives are synthesized)
        for mem in self.long_term_memory:
            # Skip the memory itself
            if mem == memory:
                continue

            mem_entities = set(mem.get("entities", []))
            mem_topic = mem.get("topic", "")

            # Calculate relatedness
            shared_entities = target_entities.intersection(mem_entities)

            # Related if shares entities OR same topic
            if len(shared_entities) > 0 or mem_topic == target_topic:
                # Calculate relatedness score
                entity_score = len(shared_entities) / max(len(target_entities), 1) if target_entities else 0
                topic_score = 1.0 if mem_topic == target_topic else 0.0
                relatedness = (entity_score * 0.7) + (topic_score * 0.3)

                related.append((relatedness, mem))

        # Sort by relatedness and take top N
        related.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in related[:max_related]]

    def _generate_narrative_synthesis(self, memory: Dict[str, Any]) -> str:
        """
        Generate narrative summary using LLM (Flamekeeper integration).

        Creates a brief story summary from clustered memories.

        Args:
            memory: Memory being promoted to long-term

        Returns:
            Narrative summary string (or empty if generation fails)
        """
        if not client or not MODEL:
            print(f"{etag('NARRATIVE')}  LLM not available, skipping synthesis")
            return ""

        # Find related memories
        related_memories = self._find_related_memories(memory, max_related=5)

        if not related_memories:
            print(f"{etag('NARRATIVE')}  No related memories found, skipping synthesis")
            return ""

        # Collect facts from related memories
        facts = []

        # Add the main memory
        main_fact = memory.get("fact", memory.get("user_input", ""))
        if main_fact:
            facts.append(main_fact)

        # Add related memories
        for mem in related_memories:
            fact = mem.get("fact", mem.get("user_input", ""))
            if fact:
                facts.append(fact)

        # Build synthesis prompt
        entities = memory.get("entities", [])
        entity_str = ", ".join(entities[:3]) if entities else "the conversation"

        prompt = f"""Synthesize a brief narrative summary (2-3 sentences) from these related CONVERSATION facts about {entity_str}:

{chr(10).join(f"- {fact[:200]}" for fact in facts[:5])}

CRITICAL ATTRIBUTION RULES:
1. the entity is an OBSERVER/LISTENER, not a participant in Re's life events
   - Re traveled to Michigan -> "Re returned from Michigan and told the entity about the trip"
   - NOT: "the entity returned from Michigan" or "In this thread, the entity returns from..."
2. Re is the person who DOES things in their life (travels, works, experiences)
3. the entity is the one who LISTENS, LEARNS, and RESPONDS to what Re shares
4. If facts mention reading/documents -> "the entity read about X" not "the entity did X"
5. If Re shared an experience -> "Re [did X] and discussed it with the entity"

WHO DOES WHAT:
- Re: travels, has pets, has relationships, experiences life events, shares stories
- Entity: listens, responds, remembers, reads documents, observes Re's life

Focus on:
- The THREAD or STORY connecting these facts
- Emotional progression or significance
- Unresolved questions or ongoing themes

Format: "In this thread, Re [did something] and [the entity's role as observer/listener]..."

Output ONLY the narrative summary, no preamble."""

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=250,
                temperature=0.5,
                system="You are a narrative synthesizer. Create brief, coherent story summaries from conversation facts. Output only the summary, no preamble or explanation.",
                messages=[{"role": "user", "content": prompt}]
            )

            narrative = resp.content[0].text.strip()
            print(f"{etag('NARRATIVE')} Synthesized: {narrative[:80]}...")
            return narrative

        except Exception as e:
            print(f"{etag('NARRATIVE SYNTHESIS ERROR')} {e}")
            return ""

    def calculate_importance_from_ultramap(self, emotional_cocktail: Dict[str, Any], emotion_tags: List[str]) -> float:
        """
        Calculate importance score from ULTRAMAP emotional data.

        Importance = (average_pressure × average_recursion) × emotional_intensity

        Args:
            emotional_cocktail: Current emotion states with intensity, pressure, recursion
            emotion_tags: Active emotion names for this memory

        Returns:
            Importance score (0.0 to 1.0+)
        """
        if not emotion_tags or not emotional_cocktail:
            return 0.1  # Baseline importance for neutral memories

        total_pressure = 0.0
        total_recursion = 0.0
        total_intensity = 0.0
        count = 0

        for emotion_name in emotion_tags:
            if emotion_name in emotional_cocktail:
                emotion_data = emotional_cocktail[emotion_name]

                pressure = emotion_data.get("pressure", 0.0)
                recursion = emotion_data.get("recursion", 0.0)
                intensity = emotion_data.get("intensity", 0.0)

                total_pressure += pressure
                total_recursion += recursion
                total_intensity += intensity
                count += 1

        if count == 0:
            return 0.1

        # Average values
        avg_pressure = total_pressure / count
        avg_recursion = total_recursion / count
        avg_intensity = total_intensity / count

        # Combined importance score
        importance = (avg_pressure * avg_recursion) * avg_intensity

        return min(importance, 2.0)  # Cap at 2.0 for extremely important memories

    def retrieve_from_all_layers(
        self,
        query: str,
        num_memories: int = 10,
        min_strength: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories from all layers, weighted by strength and recency.

        Args:
            query: Search query
            num_memories: Max memories to return
            min_strength: Minimum strength threshold

        Returns:
            List of memories sorted by relevance
        """
        # Combine both layers
        all_memories = []

        # Working memory (most recent, high retrieval priority)
        all_memories.extend([
            {**mem, "layer_weight": 1.5}  # Boost working memory
            for mem in self.working_memory
            if mem.get("current_strength", 0) >= min_strength
        ])

        # Long-term memory (everything older)
        all_memories.extend([
            {**mem, "layer_weight": 1.0}  # Normal weight
            for mem in self.long_term_memory
            if mem.get("current_strength", 0) >= min_strength
        ])

        # Mark which memories were accessed (for tracking)
        for mem in all_memories[:num_memories]:
            # Find original memory in its layer to update access count
            original_layer = mem.get("current_layer", "working")
            if original_layer == "working":
                layer_list = self.working_memory
            else:  # long_term
                layer_list = self.long_term_memory

            # Find and update original
            for original_mem in layer_list:
                if original_mem.get("fact") == mem.get("fact"):
                    self.access_memory(original_mem)
                    break

        return all_memories[:num_memories]

    def get_layer_stats(self) -> Dict[str, Any]:
        """Get statistics about memory layers."""
        return {
            "working": {
                "count": len(self.working_memory),
                "capacity": self.working_capacity,
                "avg_strength": sum(m.get("current_strength", 0) for m in self.working_memory) / max(len(self.working_memory), 1)
            },
            "long_term": {
                "count": len(self.long_term_memory),
                "capacity": "unlimited",
                "avg_strength": sum(m.get("current_strength", 0) for m in self.long_term_memory) / max(len(self.long_term_memory), 1)
            }
        }

    def migrate_memory_to_layers(self, memory: Dict[str, Any], current_turn: int):
        """
        Migrate an existing flat memory into the layered system.

        Determines appropriate layer based on:
        - How recently it was created
        - Access count (if available)
        - Importance score

        Args:
            memory: Existing memory dict
            current_turn: Current turn index for recency calculation
        """
        # Calculate recency
        added_timestamp = memory.get("added_timestamp")
        if not added_timestamp:
            # Estimate based on current_turn if available
            # Assume 1 turn ≈ 1 minute for estimation
            memory["added_timestamp"] = (datetime.now() - timedelta(minutes=current_turn)).isoformat()

        # Determine layer
        age_days = self._get_age_days(memory["added_timestamp"], datetime.now())

        # Decision logic (TWO-TIER)
        if age_days < 0.1:  # Very recent (< 2.4 hours)
            target_layer = "working"
        else:
            target_layer = "long_term"

        # Add to layer
        self.add_memory(memory, layer=target_layer)

        print(f"{etag('MIGRATION')} Migrated to {target_layer}: {memory.get('fact', '')[:40]}... (age: {age_days:.1f}d)")

    def apply_user_correction(
        self,
        wrong_value: str,
        correct_value: str,
        entity: str = ""
    ) -> Dict[str, Any]:
        """
        Apply a user correction to memories in all layers.

        When the user corrects the entity about a fact (e.g., "those were 2024-2025, not 2020"),
        this method marks memories containing the wrong value as stale.

        Args:
            wrong_value: The incorrect value (e.g., "2020")
            correct_value: The correct value (e.g., "2024-2025")
            entity: Optional entity name to narrow the search

        Returns:
            Dict with correction results
        """
        result = {
            "working_marked": 0,
            "longterm_marked": 0,
            "memories_affected": []
        }

        wrong_value_lower = wrong_value.lower()

        def _check_and_mark_memory(mem, layer_name):
            """Check if memory contains wrong value and mark it if so."""
            fact_text = mem.get("fact", "").lower()
            context_text = (mem.get("user_input", "") + " " + mem.get("response", "")).lower()
            full_text = fact_text + " " + context_text

            if re.search(r'\b' + re.escape(wrong_value_lower) + r'\b', full_text):
                # Check if it also contains the correct value (then it's OK)
                if correct_value.lower() in full_text:
                    return False

                # Mark memory as containing corrected value
                if "correction_metadata" not in mem:
                    mem["correction_metadata"] = {}

                mem["correction_metadata"]["contains_corrected_value"] = True
                mem["correction_metadata"]["wrong_value"] = wrong_value
                mem["correction_metadata"]["correct_value"] = correct_value
                mem["correction_metadata"]["corrected_at"] = datetime.now().isoformat()

                # Reduce strength significantly for corrected memories
                mem["current_strength"] = mem.get("current_strength", 1.0) * 0.3

                return True
            return False

        # Check working memory
        for mem in self.working_memory:
            if _check_and_mark_memory(mem, "working"):
                result["working_marked"] += 1
                result["memories_affected"].append({
                    "layer": "working",
                    "fact": mem.get("fact", "")[:60]
                })

        # Check long-term memory
        for mem in self.long_term_memory:
            if _check_and_mark_memory(mem, "long_term"):
                result["longterm_marked"] += 1
                result["memories_affected"].append({
                    "layer": "long_term",
                    "fact": mem.get("fact", "")[:60]
                })

        total_marked = result["working_marked"] + result["longterm_marked"]
        if total_marked > 0:
            print(f"{etag('MEMORY LAYERS CORRECTION')} Marked {total_marked} memories as containing corrected value '{wrong_value}'")
            self._save_to_disk()

        return result

    def get_memories_with_corrections(self) -> List[Dict[str, Any]]:
        """
        Get all memories that have been marked as containing corrected values.

        Returns:
            List of memories with correction metadata
        """
        corrected = []

        for mem in self.working_memory + self.long_term_memory:
            if mem.get("correction_metadata", {}).get("contains_corrected_value"):
                corrected.append(mem)

        return corrected
