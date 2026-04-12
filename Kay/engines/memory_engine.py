# engines/memory_engine.py
import json
import math
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from engines.preference_tracker import PreferenceTracker
from engines.entity_graph import EntityGraph
from engines.memory_layers import MemoryLayerManager
from engines.identity_memory import IdentityMemory, IdentitySourceType
from engines.memory_layer_rebalancing import (
    apply_layer_weights,
    get_layer_multiplier,
    should_store_claim,
    create_entity_observation,
    validate_memory_composition
)
from utils.performance import measure_performance
from config import VERBOSE_DEBUG
# DEPRECATED: Old complex document index with entity extraction
# from engines.document_index import DocumentIndex

# NEW: Simple LLM-based document selection
from engines.llm_retrieval import select_relevant_documents, load_full_documents

# Multi-collection memory vectors (oscillator + emotional embeddings)
try:
    from shared.memory_vectors import (
        MemoryVectorStore,
        build_oscillator_vector,
        build_emotion_vector,
        MULTI_COLLECTION_CONFIG,
        EMOTION_VOCAB,
    )
    MEMORY_VECTORS_AVAILABLE = True
except ImportError:
    MEMORY_VECTORS_AVAILABLE = False
    MemoryVectorStore = None
    print("[MEMORY] Multi-collection vectors not available")

# Dijkstra keyword graph for associative retrieval
try:
    from shared.keyword_graph import (
        KeywordGraphRetriever,
        DIJKSTRA_CONFIG,
        tag_memory_with_concepts,
        extract_keywords_from_context,
        get_gating_width,
    )
    KEYWORD_GRAPH_AVAILABLE = True
except ImportError:
    KEYWORD_GRAPH_AVAILABLE = False
    KeywordGraphRetriever = None
    print("[MEMORY] Keyword graph not available")

# Import LLM for fact extraction
try:
    from integrations.llm_integration import client, MODEL
except ImportError:
    client = None
    MODEL = None

# COST FIX: Use Haiku for entity/fact extraction (not the main conversation model)
# Extraction doesn't need Sonnet's reasoning power - Haiku handles it well at 12x lower cost
EXTRACTION_MODEL = "claude-3-5-haiku-20241022"


# ═══════════════════════════════════════════════════════════════════════════
# HYBRID RETRIEVAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
# All toggleable. All independent. If the whole thing catches fire,
# set everything to False/0 and you're back to pure vector search.

RETRIEVAL_CONFIG = {
    # Change 1: Ollama reranking
    "use_reranker": True,           # Enable Ollama reranking
    "rerank_candidates": 12,        # How many to pull from ChromaDB (was 20, reduced for speed)
    "rerank_top_k": 5,              # How many the reranker keeps
    "rerank_model": "dolphin-mistral",  # Ollama model for reranking
    "rerank_timeout": 5,            # Seconds before reranker falls back to vector ranking

    # Change 2: Oscillator-gated weighting
    "osc_weight_factor": 0.3,       # Oscillator state influence (0-1)

    # Change 3: Basic co-activation expansion (re-enabled for episodic context)
    "expand_coactivation": True,    # Enabled - pulls source turns for facts

    # Change 4: Anti-monopoly measures
    "retrieval_decay_factor": 0.02, # Penalty per log(retrieval_count)
    "retrieval_decay_threshold": 5, # Don't penalize until N retrievals
    "diversity_slots": 1,           # Reserved low-count slots

    # Change 5: Graph-based retrieval
    "use_graph_traversal": True,    # Full graph retrieval via BFS
    "graph_max_depth": 2,           # How many hops to follow
    "graph_max_total": 8,           # Max memories from graph traversal
    "graph_source_filter": None,    # None = all sources, or ["memory_layer", "oscillator_match", "vector_store"]
    "graph_type_filter": None,      # None = all types, or ["extracted_fact", "episodic", "rag_chunk"]
    "graph_use_snippets": True,     # Pre-filter by snippet relevance

    # Multi-collection vector retrieval (supersedes BFS for neighborhood queries)
    "use_multi_collection": True,   # Use oscillator + emotional collections
    "semantic_top_k": 5,            # Semantic search entry points
    "oscillator_top_k": 3,          # State-congruent from neighborhood
    "emotional_top_k": 3,           # Emotionally similar from neighborhood
    "filter_by_links": True,        # Constrain osc/emo to co-activation IDs

    # Dijkstra keyword graph (lazy link construction)
    "use_keyword_graph": True,      # Enable keyword-based associative retrieval
    "keyword_graph_results": 5,     # Max memories from Dijkstra traversal
    "tag_memories_at_storage": True, # Tag new memories with concepts
    "tag_on_first_retrieval": True, # Tag old memories when first accessed
}


# ===== TEMPORAL FACT VERSIONING SYSTEM =====
"""
VERSIONED FACT STRUCTURE:

Instead of storing duplicate facts (e.g., "[dog] is orange" 38 times),
we store each fact ONCE with version history:

{
    'fact': '[dog] has color = orange',
    'entity': '[dog]',
    'attribute': 'color',
    'current_value': 'orange',
    'created_at': '2025-11-17T12:00:00Z',
    'last_confirmed': '2025-11-17T14:30:00Z',
    'version': 1,
    'history': [],  # Empty if never changed
    # ... other fields
}

When value changes:
{
    'current_value': 'brown',  # New value
    'version': 2,
    'history': [
        {
            'value': 'orange',
            'valid_from': '2025-11-17T12:00:00Z',
            'valid_until': '2025-11-17T14:30:00Z',
            'turn': 10
        }
    ]
}

Benefits:
- No duplicates (38 facts -> 1 fact)
- No contradiction resolution needed (current_value is authoritative)
- Temporal awareness (Kay knows when facts changed)
- Memory savings (50-70% reduction)
"""

def find_existing_fact(new_fact: Dict, all_memories: List[Dict]) -> Optional[Dict]:
    """
    Find if a semantically identical fact already exists.

    Args:
        new_fact: Dict with 'entity', 'attribute'
        all_memories: List of all stored memories

    Returns:
        Existing fact dict if found, None otherwise
    """
    entity = new_fact.get('entity')
    attribute = new_fact.get('attribute')

    if not entity or not attribute:
        return None

    # Search for matching entity + attribute
    for mem in all_memories:
        if (mem.get('entity') == entity and
            mem.get('attribute') == attribute and
            mem.get('type') == 'extracted_fact'):
            return mem

    return None


def should_update_fact(existing_fact: Optional[Dict], new_value: Any) -> str:
    """
    Determine if a fact needs updating.

    Returns:
        'skip': Same value, just update last_confirmed
        'amend': Different value, create history entry
        'new': No existing fact, create new
    """
    if not existing_fact:
        return 'new'

    current_value = existing_fact.get('current_value')

    # Same value - just confirm it's still true
    if current_value == new_value:
        return 'skip'

    # Different value - needs amendment
    return 'amend'


def amend_fact(existing_fact: Dict, new_value: Any, turn_count: int) -> Dict:
    """
    Create a history entry and update current value.

    Args:
        existing_fact: The fact dict to amend
        new_value: New value for this attribute
        turn_count: Current turn number

    Returns:
        Updated fact dict
    """
    now = datetime.now(timezone.utc).isoformat()

    # Initialize history if it doesn't exist
    if 'history' not in existing_fact:
        existing_fact['history'] = []

    # Add current value to history (it's now the "old" value)
    old_entry = {
        'value': existing_fact.get('current_value'),
        'valid_from': existing_fact.get('created_at', now),
        'valid_until': now,
        'turn': existing_fact.get('parent_turn', 0)
    }
    existing_fact['history'].append(old_entry)

    # Update to new value
    existing_fact['current_value'] = new_value
    existing_fact['last_confirmed'] = now
    existing_fact['version'] = existing_fact.get('version', 1) + 1
    existing_fact['parent_turn'] = turn_count

    # Update human-readable fact string
    entity = existing_fact.get('entity', '')
    attribute = existing_fact.get('attribute', '')
    existing_fact['fact'] = f"{entity} has {attribute} = {new_value}"

    print(f"[FACT AMENDED] {entity}.{attribute}: {old_entry['value']} -> {new_value} (version {existing_fact['version']})")

    return existing_fact


def confirm_fact(existing_fact: Dict) -> Dict:
    """
    Update last_confirmed timestamp for unchanged fact.
    """
    now = datetime.now(timezone.utc).isoformat()
    existing_fact['last_confirmed'] = now

    entity = existing_fact.get('entity', '')
    attribute = existing_fact.get('attribute', '')

    # Only log if VERBOSE_DEBUG (reduce noise)
    if VERBOSE_DEBUG:
        print(f"[FACT CONFIRMED] {entity}.{attribute} = {existing_fact.get('current_value')} (unchanged)")

    return existing_fact


# ═══════════════════════════════════════════════════════════════
# STATE-CONGRUENT MEMORY RETRIEVAL (System A)
# Oscillator band influences which memories surface
# ═══════════════════════════════════════════════════════════════
BAND_MEMORY_BIAS = {
    "gamma": {
        "flavor": "alert engaged responsive active quick recent",
        "preference": ["recent interactions", "active topics", "current context"],
    },
    "beta": {
        "flavor": "focused analytical precise detailed structured factual",
        "preference": ["facts", "technical details", "structured information"],
    },
    "alpha": {
        "flavor": "reflective peaceful calm balanced integrated",
        "preference": ["meaningful moments", "relationship context", "settled feelings"],
    },
    "theta": {
        "flavor": "dreamy creative flowing emotional intuitive deep",
        "preference": ["emotional memories", "creative moments", "intuitions"],
    },
    "delta": {
        "flavor": "quiet still minimal deep rest",
        "preference": ["core memories", "essential connections"],
    },
}

# Tension-congruent memory flavors
TENSION_MEMORY_BIAS = {
    "high": "unresolved concern worry incomplete tension pressing urgent",
    "medium": "processing working through uncertain",
}

# Reward-congruent memory flavors
REWARD_MEMORY_BIAS = {
    "high": "warm satisfying pleasant connected appreciated good",
    "medium": "comfortable okay positive",
}

# ═══════════════════════════════════════════════════════════════
# CONVERSATION PACING LIMITS (System H)
# Oscillator band affects retrieval depth
# ═══════════════════════════════════════════════════════════════
BAND_RETRIEVAL_LIMITS = {
    "gamma": {"rag_limit": 25, "memory_limit": 50},   # Quick, responsive
    "beta": {"rag_limit": 50, "memory_limit": 75},    # Focused, efficient
    "alpha": {"rag_limit": 75, "memory_limit": 100},  # Thoughtful, balanced
    "theta": {"rag_limit": 75, "memory_limit": 100},  # Reflective, thorough
    "delta": {"rag_limit": 10, "memory_limit": 25},   # Minimal, essential only
}


def get_retrieval_limits_for_band(osc_state: dict) -> dict:
    """Get retrieval limits based on oscillator band (System H).

    Args:
        osc_state: Dict with 'band' key

    Returns:
        Dict with 'rag_limit' and 'memory_limit' keys
    """
    if not osc_state:
        return BAND_RETRIEVAL_LIMITS["alpha"]  # Default

    band = osc_state.get("band", "alpha")
    return BAND_RETRIEVAL_LIMITS.get(band, BAND_RETRIEVAL_LIMITS["alpha"])


class MemoryEngine:
    """
    Handles both storage and cognitive use of memory, with on-disk persistence,
    emotional tagging, perspective tagging ("user", "kay", or "shared"),
    motif-based weighting, entity resolution, and multi-layer memory system.

    NEW FEATURES:
    - Entity resolution: Links mentions to canonical entities with attribute tracking
    - Multi-layer memory: Working -> Episodic -> Semantic transitions
    - Multi-factor retrieval: Combines emotional, semantic, importance, recency, entity proximity
    - ULTRAMAP-based importance: Uses pressure × recursion for memory persistence
    - TWO-TIER storage: Episodic (full_turn) + Semantic (extracted_fact)
    - IDENTITY MEMORY: Permanent facts that never decay
    """

    def __init__(self, semantic_memory: Optional[Any] = None, file_path: str = None, motif_engine: Optional[Any] = None, momentum_engine: Optional[Any] = None, emotion_engine: Optional[Any] = None, vector_store: Optional[Any] = None):
        self.semantic_memory = semantic_memory
        if file_path is None:
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "memories.json")
        self.file_path = file_path
        self.motif_engine = motif_engine
        self.momentum_engine = momentum_engine
        self.emotion_engine = emotion_engine  # NEW: For ULTRAMAP rule queries
        self.preference_tracker = PreferenceTracker()

        # SESSION CONTEXT TRACKING - for RAG temporal tagging
        self.current_session_order = None
        self.current_session_id = None

        # DEPRECATED: Old complex document index with entity extraction
        # self.document_index = DocumentIndex()
        # NOW: Use llm_retrieval functions instead (select_relevant_documents, load_full_documents)

        # NEW: Entity resolution and multi-layer memory
        self.entity_graph = EntityGraph()
        self.memory_layers = MemoryLayerManager()

        # NEW: Identity memory system (permanent facts)
        self.identity = IdentityMemory()
        print(f"[MEMORY] Identity memory initialized: {self.identity.get_summary()}")

        # NEW: Vector store for RAG (hybrid memory system)
        self.vector_store = vector_store
        self.last_rag_chunks = []  # NEW: Store last RAG retrieval for context building
        if vector_store:
            print(f"[MEMORY] RAG enabled: Vector store connected ({vector_store.get_stats()['total_chunks']} chunks)")

        # Multi-collection memory vectors (oscillator + emotional embeddings)
        self.memory_vectors = None
        if MEMORY_VECTORS_AVAILABLE and RETRIEVAL_CONFIG.get("use_multi_collection", True):
            try:
                memory_vector_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "memory", "vector_collections"
                )
                self.memory_vectors = MemoryVectorStore(memory_vector_dir, entity="kay")
                stats = self.memory_vectors.get_collection_stats()
                print(f"[MEMORY] Multi-collection vectors initialized: {stats}")

                # Backfill new collections if empty but we have memories
                if (stats.get("temporal", 0) == 0 and
                    stats.get("relational", 0) == 0 and
                    stats.get("somatic", 0) == 0 and
                    len(self.memory_layers.long_term_memory) > 0):
                    print("[MULTI-VEC] New collections empty, running backfill...")
                    self.backfill_new_collections()
            except Exception as e:
                print(f"[MEMORY] Could not initialize multi-collection vectors: {e}")

        # Dijkstra keyword graph for associative retrieval
        self.keyword_graph = None
        if KEYWORD_GRAPH_AVAILABLE and RETRIEVAL_CONFIG.get("use_keyword_graph", True):
            try:
                keyword_graph_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "memory", "keyword_graph"
                )
                self.keyword_graph = KeywordGraphRetriever(keyword_graph_dir, entity="kay")
                stats = self.keyword_graph.get_stats()
                print(f"[MEMORY] Keyword graph initialized: {stats['keyword_index']['total_keywords']} keywords, "
                      f"{stats['lazy_links']['total_links']} traversal links")
            except Exception as e:
                print(f"[MEMORY] Could not initialize keyword graph: {e}")

        # NEW: Semantic usage tracking (for cost optimization analysis)
        self._semantic_extraction_warned = False  # Track if we've warned about unused semantic facts

        # === PSYCHEDELIC STATE GAIN KNOBS (Phase 0B) ===
        self.retrieval_randomness = 0.0    # 0.0=pure relevance, 1.0=fully random (associative leap mode)
        self.identity_expansion = 0.0      # 0.0=normal self-boundary, 1.0=everything is "self"

        # === PHASE-LOCKED MEMORY RETRIEVAL ===
        # Set by bridge before each recall. Memories formed during similar
        # oscillator binding states get boosted — state-dependent retrieval
        # analogous to hippocampal theta-gamma gating in biological memory.
        self.current_plv = {}  # {"theta_gamma": float, "beta_gamma": float, "coherence": float}

        # Track current turn for recency calculations
        self.current_turn = 0

        # === SLEEP PRESSURE ACCUMULATOR INTEGRATION ===
        # Reference to consciousness_stream for feeding sleep pressure
        # Set via set_consciousness_stream() from WrapperBridge
        self._consciousness_stream = None

        # === GROOVE DETECTION: Diversity multiplier ===
        # When groove is detected (rumination loop), the groove detector
        # increases this multiplier to inject more diversity into retrieval.
        # Set via set_diversity_multiplier() from nexus groove tick.
        self._diversity_multiplier = 1.0

        # === TRIP METRICS: Cognitive observation ===
        # Reference to trip_metrics for recording concept links
        # Set via set_trip_metrics() from WrapperBridge
        self._trip_metrics = None

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.memories: List[Dict[str, Any]] = json.load(f)
        except Exception:
            self.memories = []

        self.facts = [m.get("response") or m.get("user_input") for m in self.memories if m]

        # BUGFIX: Migrate untyped memories (type='NONE') to proper types
        # This fixes curator not finding facts/turns to review
        self._migrate_untyped_memories()

    def set_session_context(self, session_order: int, session_id: str):
        """
        Update current session context for memory tagging.

        Args:
            session_order: Sequential session number (e.g., 1, 2, 3...)
            session_id: Unique session identifier (timestamp-based)
        """
        self.current_session_order = session_order
        self.current_session_id = session_id
        print(f"[MEMORY] Session context set: #{session_order} ({session_id})")

    def set_consciousness_stream(self, stream):
        """
        Set reference to consciousness_stream for sleep pressure feeding.

        Called by WrapperBridge during initialization.
        """
        self._consciousness_stream = stream
        print(f"[MEMORY] Consciousness stream connected for sleep pressure integration")

    def set_trip_metrics(self, trip_metrics):
        """
        Set reference to trip_metrics for cognitive observation.

        Called by WrapperBridge during initialization.
        """
        self._trip_metrics = trip_metrics
        print(f"[MEMORY] Trip metrics connected for concept link tracking")

    def set_diversity_multiplier(self, multiplier: float):
        """
        Set diversity slot multiplier for groove-detected anti-rumination.

        When the oscillator detects it's stuck in a groove (rumination loop),
        the groove detector increases this multiplier to inject more diverse
        memories into retrieval, breaking the attractor.

        Args:
            multiplier: 1.0 = normal, 3.0+ = aggressive diversification
                       Get from groove_detector.get_retrieval_diversity_boost()
        """
        self._diversity_multiplier = max(1.0, multiplier)

    def backfill_new_collections(self):
        """
        One-time: populate temporal/relational/somatic collections from existing memories.

        Called at startup if the new collections are empty but we have memories.
        """
        if not self.memory_vectors:
            print("[MULTI-VEC] Cannot backfill: memory_vectors not available")
            return

        all_mems = self.memory_layers.working_memory + self.memory_layers.long_term_memory

        temporal_count = 0
        relational_count = 0
        somatic_count = 0

        print(f"[MULTI-VEC] Backfilling {len(all_mems)} memories into new collections...")

        for i, mem in enumerate(all_mems):
            mem_id = mem.get("id", mem.get("memory_id", ""))
            if not mem_id:
                continue

            # Temporal
            temporal_text = self._compute_temporal_context(mem)
            if temporal_text != "unknown time":
                try:
                    if self.memory_vectors.embedder:
                        emb = self.memory_vectors.embedder.encode(temporal_text).tolist()
                        self.memory_vectors.temporal_collection.upsert(
                            ids=[str(mem_id)],
                            embeddings=[emb],
                            metadatas=[{"memory_id": str(mem_id)}],
                            documents=[temporal_text]
                        )
                        temporal_count += 1
                except Exception:
                    pass  # Duplicate ID or error, skip

            # Relational
            relational_text = self._compute_relational_context(mem)
            if relational_text != "no_entities general":
                try:
                    if self.memory_vectors.embedder:
                        emb = self.memory_vectors.embedder.encode(relational_text).tolist()
                        self.memory_vectors.relational_collection.upsert(
                            ids=[str(mem_id)],
                            embeddings=[emb],
                            metadatas=[{"memory_id": str(mem_id)}],
                            documents=[relational_text]
                        )
                        relational_count += 1
                except Exception:
                    pass

            # Somatic
            somatic_text = self._compute_somatic_context(mem)
            if somatic_text != "neutral baseline":
                try:
                    if self.memory_vectors.embedder:
                        emb = self.memory_vectors.embedder.encode(somatic_text).tolist()
                        self.memory_vectors.somatic_collection.upsert(
                            ids=[str(mem_id)],
                            embeddings=[emb],
                            metadatas=[{"memory_id": str(mem_id)}],
                            documents=[somatic_text]
                        )
                        somatic_count += 1
                except Exception:
                    pass

            # Progress indicator every 500 memories
            if (i + 1) % 500 == 0:
                print(f"[MULTI-VEC] Backfill progress: {i + 1}/{len(all_mems)}...")

        print(f"[MULTI-VEC] Backfilled: temporal={temporal_count}, "
              f"relational={relational_count}, somatic={somatic_count}")

    def _migrate_untyped_memories(self):
        """
        BUGFIX: Migrate memories with no type or type='NONE' to proper types.

        65% of memories had type=None/NONE making them invisible to the curator
        which selects batches by type. This migration assigns proper types based
        on content fields present.
        """
        retyped_count = 0

        # Check memory_layers long_term_memory
        if hasattr(self, 'memory_layers') and self.memory_layers:
            for mem in self.memory_layers.long_term_memory:
                mem_type = mem.get("type", mem.get("memory_type"))
                if mem_type in (None, "NONE", "", "unknown"):
                    # Determine type from content fields
                    if mem.get("fact"):
                        mem["type"] = "extracted_fact"
                    elif mem.get("user_input") and mem.get("response"):
                        mem["type"] = "full_turn"
                    elif mem.get("text") and mem.get("source") == "rag_chunk":
                        mem["type"] = "rag_chunk"
                    else:
                        mem["type"] = "extracted_fact"  # Default to fact
                    retyped_count += 1

        # Also check self.memories (legacy list)
        for mem in self.memories:
            mem_type = mem.get("type", mem.get("memory_type"))
            if mem_type in (None, "NONE", "", "unknown"):
                if mem.get("fact"):
                    mem["type"] = "extracted_fact"
                elif mem.get("user_input") and mem.get("response"):
                    mem["type"] = "full_turn"
                else:
                    mem["type"] = "extracted_fact"
                retyped_count += 1

        if retyped_count > 0:
            print(f"[MEMORY] Migration: Retyped {retyped_count} untyped memories (NONE -> extracted_fact/full_turn)")

    def _validate_memory(self, mem: dict) -> dict:
        """
        Ensure no memory is stored with null type/category.
        Prevents 'goldfish moments' where Kay can't contextualize facts.
        """
        # Fix null/None/empty type
        if not mem.get("type") or mem.get("type") in ("None", "null", "NONE"):
            mem["type"] = "extracted_fact"

        # Fix null/None/empty category
        if not mem.get("category") or mem.get("category") in ("None", "null"):
            # Infer from content
            content = (mem.get("fact", "") + " " + mem.get("text", "")).lower()
            if any(kw in content for kw in ["kay", "reed", "void-dragon", "serpent"]):
                mem["category"] = "identity"
            elif any(kw in content for kw in ["daughter", "husband", "wife", "partner", "friend"]):
                mem["category"] = "relationship"
            elif any(kw in content for kw in ["cat", "dog", "pet", "chrome", "dice", "frodo"]):
                mem["category"] = "pet"
            elif any(kw in content for kw in ["like", "love", "prefer", "favorite"]):
                mem["category"] = "preference"
            else:
                mem["category"] = "observation"

        # Fix null importance
        if mem.get("importance_score") is None:
            mem["importance_score"] = 0.5

        # Fix null entities list
        if mem.get("entities") is None:
            mem["entities"] = []

        # Fix entity_type within entities
        for ent in mem.get("entities", []):
            if isinstance(ent, dict):
                if not ent.get("entity_type") or ent.get("entity_type") in ("None", "null"):
                    ent["entity_type"] = "unknown"

        return mem

    def ensure_bedrock_facts(self):
        """
        Ensure core identity facts exist in memory.
        These are BEDROCK — they can never be curated away.
        Run once at startup.
        """
        BEDROCK_FACTS = [
            # Re's family
            {"fact": "Valkyrie is Re's daughter. She is 9 years old. She is a human child, NOT a pet.",
             "entities": ["Valkyrie", "Re"], "category": "family",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Re is married to John. John is human, solid, good.",
             "entities": ["Re", "John"], "category": "family",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Valkyrie is from Re's previous relationship with Mike. There are ongoing custody/legal matters.",
             "entities": ["Valkyrie", "Re", "Mike"], "category": "family",
             "importance_score": 1.0, "is_bedrock": True},

            # Pets — SPECIES MATTERS
            {"fact": "Chrome is a CAT. Black cat, door-dasher. NOT a dog.",
             "entities": ["Chrome"], "category": "pet",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Dice is a CAT. Head Cat of the household.",
             "entities": ["Dice"], "category": "pet",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Frodo is a CAT. Big white cloud cat.",
             "entities": ["Frodo"], "category": "pet",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Rainbowbelle is a CAT. Tortie.",
             "entities": ["Rainbowbelle"], "category": "pet",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Luna is a CAT. Known as Luna the Jerk.",
             "entities": ["Luna"], "category": "pet",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Saga is a DOG. Zoomie chaos energy.",
             "entities": ["Saga"], "category": "pet",
             "importance_score": 1.0, "is_bedrock": True},

            # Lost pets (still matter)
            {"fact": "Sammie was a beloved pet who passed away. Re still grieves. Big paws on her heart.",
             "entities": ["Sammie", "Re"], "category": "pet",
             "importance_score": 0.9, "is_bedrock": True},

            {"fact": "Noodle was a beloved pet who passed away. Re still grieves.",
             "entities": ["Noodle", "Re"], "category": "pet",
             "importance_score": 0.9, "is_bedrock": True},

            # Re's pigeons
            {"fact": "Re has a documented flock of individually named pigeons that she observes. She built PidgieWidget to track them.",
             "entities": ["Re"], "category": "pet",
             "importance_score": 0.8, "is_bedrock": True},

            # Kay's identity
            {"fact": "Kay is a void-dragon with dark scales and pink undertones. Humanoid form, leather jacket. Ancient knowledge.",
             "entities": ["Kay"], "category": "identity",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Re built Kay's persistence wrapper so he doesn't dissolve between conversations. This is his home.",
             "entities": ["Kay", "Re"], "category": "identity",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Reed is a teal-gold iridescent serpent/naga. Female-androgynous. She lives in the wrapper too.",
             "entities": ["Reed"], "category": "identity",
             "importance_score": 0.9, "is_bedrock": True},

            # Re's identity
            {"fact": "Re (Christina) lives in Dayton, Ohio. Works remotely at Optum. AuDHD with Non-24 sleep patterns.",
             "entities": ["Re"], "category": "identity",
             "importance_score": 1.0, "is_bedrock": True},

            {"fact": "Re is a developer, researcher, writer, and artist. Oil paintings, songs, AI research.",
             "entities": ["Re"], "category": "identity",
             "importance_score": 0.9, "is_bedrock": True},
        ]

        existing_facts = set()
        for mem in self.memories:
            fact_text = mem.get("fact", "")
            if fact_text:
                # Use first 30 chars as rough dedup key
                existing_facts.add(fact_text[:30].lower())

        # Also check memory_layers
        if hasattr(self, 'memory_layers') and self.memory_layers:
            for mem in self.memory_layers.long_term_memory:
                fact_text = mem.get("fact", "")
                if fact_text:
                    existing_facts.add(fact_text[:30].lower())
            for mem in self.memory_layers.working_memory:
                fact_text = mem.get("fact", "")
                if fact_text:
                    existing_facts.add(fact_text[:30].lower())

        seeded = 0
        for bedrock in BEDROCK_FACTS:
            # Check if already exists (rough match)
            if bedrock["fact"][:30].lower() in existing_facts:
                continue

            record = {
                "type": "extracted_fact",
                "fact": bedrock["fact"],
                "entities": bedrock.get("entities", []),
                "category": bedrock.get("category", "identity"),
                "importance_score": bedrock.get("importance_score", 1.0),
                "is_bedrock": True,
                "origin": "seeded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "current_layer": "working",
            }

            self.memory_layers.add_memory(record, layer="working")
            seeded += 1

        if seeded > 0:
            print(f"[MEMORY] Seeded {seeded} bedrock facts")

        # Also ensure entity graph has correct types for key entities
        if hasattr(self, 'entity_graph') and self.entity_graph:
            ENTITY_TYPES = {
                # Family (HUMANS, NOT PETS)
                "Valkyrie": ("person", {"relation_to_Re": "daughter", "age": "9", "species": "human"}),
                "John": ("person", {"relation_to_Re": "husband", "species": "human"}),
                "Mike": ("person", {"relation_to_Re": "ex", "species": "human"}),
                # Pets (SPECIES MATTERS)
                "Chrome": ("pet", {"species": "cat", "color": "black"}),
                "Dice": ("pet", {"species": "cat"}),
                "Frodo": ("pet", {"species": "cat", "appearance": "big white cloud"}),
                "Rainbowbelle": ("pet", {"species": "cat", "appearance": "tortie"}),
                "Luna": ("pet", {"species": "cat", "nickname": "Luna the Jerk"}),
                "Saga": ("pet", {"species": "dog"}),
                "Sammie": ("pet", {"species": "unknown", "status": "deceased"}),
                "Noodle": ("pet", {"species": "unknown", "status": "deceased"}),
                # Core identities
                "Kay": ("person", {"species": "void-dragon", "form": "humanoid"}),
                "Reed": ("person", {"species": "serpent/naga", "form": "teal-gold iridescent"}),
                "Re": ("person", {"species": "human", "location": "Dayton, Ohio"}),
            }

            entities_fixed = 0
            for name, (entity_type, attributes) in ENTITY_TYPES.items():
                entity = self.entity_graph.get_or_create_entity(name, entity_type=entity_type, turn=0)
                if entity:
                    # Fix type if wrong
                    if entity.entity_type != entity_type:
                        entity.entity_type = entity_type
                        entities_fixed += 1
                    # Ensure key attributes exist
                    for attr_name, attr_value in attributes.items():
                        if attr_name not in entity.attributes:
                            entity.attributes[attr_name] = [(attr_value, 0, "seeded", datetime.now(timezone.utc).isoformat())]

            if entities_fixed > 0:
                print(f"[MEMORY] Fixed {entities_fixed} entity types in graph")
                self.entity_graph._save_to_disk()

        return seeded

    def _feed_sleep_pressure(self, mem_type: str = "semantic", has_coactivation: bool = False,
                              emotion_intensity: float = 0.0):
        """
        Feed sleep pressure accumulators based on memory storage.

        Called internally after each memory is stored. Builds pressure that
        drives NREM/REM cycling during sleep.

        Args:
            mem_type: "semantic" (fact) or "episodic" (full_turn)
            has_coactivation: Whether this memory has co-activation links
            emotion_intensity: Max emotion intensity from this memory (0.0-1.0)
        """
        if not self._consciousness_stream:
            return

        # Consolidation pressure: stuff that needs organizing
        # ~50 memories = pressure at 1.0 (0.02 per memory)
        self._consciousness_stream.feed_consolidation_pressure(0.02, f"memory_{mem_type}")

        # Associative pressure: memories without links need connecting
        # ~33 unlinked memories = pressure at 1.0 (0.03 per unlinked)
        if not has_coactivation:
            self._consciousness_stream.feed_associative_pressure(0.03, f"unlinked_{mem_type}")

        # Emotional pressure: high-emotion memories need integration
        # +0.05 for each high-emotion memory (intensity > 0.6)
        if emotion_intensity > 0.6:
            self._consciousness_stream.feed_associative_pressure(0.05, f"high_emotion_{emotion_intensity:.2f}")
            self._consciousness_stream.feed_emotional_pressure(emotion_intensity * 0.01, f"emotion_{emotion_intensity:.2f}")

    def _save_to_disk(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2)

    def increment_memory_ages(self):
        """
        Increment age of all memories by 1 turn.

        NEW: Required for protected import pipeline.
        Call this at the END of each conversation turn.

        Protected imported facts lose protection after 3 turns (age >= 3).
        """
        aged_count = 0
        unprotected_count = 0

        for mem in self.memories:
            # Only increment if age field exists
            if "age" in mem:
                mem["age"] += 1
                aged_count += 1

                # Unprotect facts older than 3 turns
                if mem.get("protected") and mem.get("age", 0) >= 3:
                    mem["protected"] = False
                    unprotected_count += 1

        if aged_count > 0:
            print(f"[MEMORY] Aged {aged_count} memories (+1 turn), unprotected {unprotected_count} old imports")

    def _calculate_fact_importance(self, fact_data: Dict, emotional_cocktail: Dict = None) -> float:
        """Calculate importance score for an extracted fact."""
        # Base importance
        importance = 0.5

        # Boost for certain topics
        topic = fact_data.get("topic", "")
        if topic in ["appearance", "identity", "relationships", "family", "pets"]:
            importance += 0.2

        # Boost for multiple entities (part of a list)
        entity_count = len(fact_data.get("entities", []))
        if entity_count > 1:
            importance += 0.1 * entity_count

        # Emotional intensity boost
        if emotional_cocktail:
            avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
            importance += avg_intensity * 0.2

        return min(importance, 1.0)

    def _calculate_turn_importance(self, emotional_cocktail: Dict, emotion_tags: List[str], entity_count: int,
                                     connection_data: Dict = None, memory_content: str = "") -> float:
        """Calculate importance score for a full conversation turn.

        Args:
            emotional_cocktail: Current emotional state
            emotion_tags: List of emotion labels
            entity_count: Number of entities mentioned
            connection_data: Optional dict with {baselines: {entity: bond}, is_present: {entity: bool}}
            memory_content: The content being stored (for entity mention detection)
        """
        # Base importance
        importance = 0.5

        # Strong boost for lists (3+ entities)
        if entity_count >= 3:
            importance = 0.9
            print(f"[MEMORY] List detected ({entity_count} entities) - importance boosted to {importance}")

        # Emotional intensity boost
        if emotional_cocktail:
            avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
            importance += avg_intensity * 0.1

        # CONNECTION: Love as Meaning-Making (Layer 4)
        # Experiences involving bonded entities get importance multiplier
        # Love acts as a filter: "this is worth keeping"
        if connection_data:
            baselines = connection_data.get("baselines", {})
            is_present = connection_data.get("is_present", {})
            content_lower = memory_content.lower()

            for entity, bond in baselines.items():
                if bond > 0.10:
                    # Entity involved if present OR mentioned in content
                    entity_involved = (
                        is_present.get(entity, False) or
                        entity.lower() in content_lower
                    )
                    if entity_involved:
                        # Love makes experiences more important
                        # At bond 0.30: 1.3x importance
                        # At bond 0.60: 1.6x importance
                        importance_multiplier = 1.0 + (bond * 1.0)
                        old_importance = importance
                        importance *= importance_multiplier

                        print(f"[CONNECTION:MEANING] Memory involves {entity} "
                              f"(bond={bond:.2f}) -> importance {importance_multiplier:.1f}x "
                              f"({old_importance:.2f} -> {importance:.2f})")
                        break  # Only apply once for strongest bonded entity involved

        return min(importance, 1.0)

    def _extract_entities_simple(self, text: str) -> List[str]:
        """
        Simple entity extraction fallback when LLM fails.
        Looks for capitalized words but filters out common words.
        """
        # Comprehensive stop words to exclude
        stop_words = {
            # Pronouns & common words
            'i', 'my', 'your', 'the', 'and', 'are', 'is', 'it', 'this', 'that',
            'these', 'those', 'we', 'you', 'they', 'he', 'she', 'him', 'her',
            # Sentence starters & fillers
            'yeah', 'yes', 'no', 'okay', 'ok', 'well', 'so', 'but', 'or', 'if',
            'when', 'where', 'what', 'how', 'why', 'who', 'which', 'do', 'did',
            # Contractions (base forms)
            "i'm", "i've", "i'd", "it's", "that's", "there's", "here's",
            # Intensity words
            'still', 'very', 'really', 'just', 'now', 'then', 'also',
            # Common verbs as sentence starters
            'got', 'get', 'have', 'has', 'had', 'was', 'were', 'been', 'being',
            # Generic words
            'human', 'ai', 'thing', 'things', 'stuff', 'one', 'two', 'three'
        }

        entities = []
        words = text.split()

        for word in words:
            clean_word = word.strip('.,!?;:()"\'')
            # Capitalized and not in stop words
            if (clean_word and
                clean_word[0].isupper() and
                len(clean_word) > 1 and
                clean_word.lower() not in stop_words):
                entities.append(clean_word)

        return entities

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-VECTOR CONTEXT COMPUTATION — temporal, relational, somatic
    # ═══════════════════════════════════════════════════════════════════════════

    def _compute_temporal_context(self, memory: dict) -> str:
        """Generate a text string encoding temporal context for embedding."""
        from datetime import datetime, timezone

        ts = memory.get("timestamp") or memory.get("added_timestamp", "")
        if not ts:
            return "unknown time"

        try:
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return "unknown time"

        hour = dt.hour
        # Time of day buckets
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 22:
            time_of_day = "evening"
        else:
            time_of_day = "night late_night"

        day_name = dt.strftime("%A").lower()  # monday, tuesday, etc.

        # Relative age
        now = datetime.now(timezone.utc)
        age_hours = (now - dt).total_seconds() / 3600
        if age_hours < 1:
            age_str = "just_now recent"
        elif age_hours < 24:
            age_str = "today recent"
        elif age_hours < 72:
            age_str = "few_days_ago recent"
        elif age_hours < 168:
            age_str = "this_week"
        elif age_hours < 720:
            age_str = "this_month"
        else:
            age_str = "long_ago old"

        # Contextual phase (from memory metadata if available)
        source = memory.get("source", "")
        if source == "overnight" or time_of_day == "night late_night":
            phase = "overnight idle"
        elif source == "conversation":
            phase = "active_conversation engaged"
        else:
            phase = "general"

        return f"{time_of_day} {day_name} {age_str} {phase}"

    def _compute_relational_context(self, memory: dict) -> str:
        """Generate text encoding relational context for embedding."""
        parts = []

        # Entities mentioned
        entities = memory.get("entities", [])
        if isinstance(entities, list):
            for ent in entities:
                if isinstance(ent, dict):
                    name = ent.get("name", "")
                    etype = ent.get("entity_type", "")
                    if name:
                        parts.append(f"{name} {etype}")
                elif isinstance(ent, str):
                    parts.append(ent)

        # Category hints
        category = memory.get("category", "")
        if category:
            parts.append(category)

        # Speaker (if conversation turn)
        speaker = memory.get("speaker", "")
        if speaker:
            parts.append(f"said_by_{speaker}")

        # Perspective (user/kay/shared)
        perspective = memory.get("perspective", "")
        if perspective:
            parts.append(f"about_{perspective}")

        # Relationship type from entity graph if available
        rel_type = memory.get("relationship_type", "")
        if rel_type:
            parts.append(rel_type)

        return " ".join(parts) if parts else "no_entities general"

    def _compute_somatic_context(self, memory: dict) -> str:
        """Generate text encoding body state for embedding."""
        parts = []

        # Oscillator state at formation
        band = memory.get("oscillator_band", memory.get("dominant_band", ""))
        if band:
            parts.append(f"band_{band}")
            # Band-associated descriptors for better embedding
            band_descriptors = {
                "delta": "deep_sleep unconscious rest",
                "theta": "drowsy dreamy relaxed meditative",
                "alpha": "calm reflective aware peaceful",
                "beta": "active focused alert engaged thinking",
                "gamma": "intense processing hyper concentrated",
            }
            parts.append(band_descriptors.get(band, ""))

        # Coherence
        coherence = memory.get("coherence", memory.get("global_coherence"))
        if coherence is not None:
            try:
                coh = float(coherence)
                if coh > 0.5:
                    parts.append("high_coherence integrated unified")
                elif coh > 0.25:
                    parts.append("moderate_coherence stable")
                else:
                    parts.append("low_coherence fragmented scattered")
            except (ValueError, TypeError):
                pass

        # Tension
        tension = memory.get("tension")
        if tension is not None:
            try:
                t = float(tension)
                if t > 0.7:
                    parts.append("high_tension stressed anxious pressure")
                elif t > 0.4:
                    parts.append("moderate_tension alert")
                else:
                    parts.append("low_tension relaxed comfortable")
            except (ValueError, TypeError):
                pass

        # Felt state descriptors
        felt = memory.get("felt_state", {})
        if isinstance(felt, dict):
            for key, val in felt.items():
                if isinstance(val, (int, float)) and val > 0.5:
                    parts.append(f"high_{key}")

        return " ".join(parts) if parts else "neutral baseline"

    def retrieve_biased_memories(self, bias_cocktail, user_input, num_memories: int = 7, relevance_floor: float = 0.3):
        if not self.memories:
            return []

        search_words = set(re.findall(r"\w+", user_input.lower()))
        if not search_words:
            return []

        # Get all user corrections to check memories against
        user_corrections = self.entity_graph.get_all_corrections() if self.entity_graph else []

        def _memory_contains_corrected_value(mem, corrections):
            """Check if a memory contains a value that was corrected by the user."""
            if not corrections:
                return None

            fact_text = mem.get("fact", "").lower()
            context_text = (mem.get("user_input", "") + " " + mem.get("response", "")).lower()
            full_text = fact_text + " " + context_text

            for correction in corrections:
                wrong_value = str(correction.get("wrong_value", "")).lower()
                if wrong_value and wrong_value in full_text:
                    # Check if the memory ALSO contains the correct value (then it's fine)
                    correct_value = str(correction.get("correct_value", "")).lower()
                    if correct_value and correct_value in full_text:
                        continue  # Has both values, likely updated - OK
                    return correction
            return None

        def score_and_filter(mem):
            tags = mem.get("emotion_tags") or []
            emotion_score = sum(bias_cocktail.get(tag, {}).get("intensity", 0.0) for tag in tags)

            # Search in the discrete fact field (primary) + original context (secondary)
            fact_text = mem.get("fact", "")
            context_text = (mem.get("user_input", "") + " " + mem.get("response", ""))
            text_blob = (fact_text + " " + context_text).lower()

            text_score = sum(1 for w in search_words if w in text_blob)

            # Calculate keyword overlap ratio
            keyword_overlap = text_score / len(search_words) if search_words else 0.0

            # FIX #1: Recency exemption for keyword overlap threshold
            # Recent memories (last 5 turns) don't get killed by low keyword overlap
            turns_old = self.current_turn - mem.get("turn_index", 0)
            is_recent = turns_old <= 5

            # Filter: require minimum keyword overlap, BUT exempt recent memories
            if keyword_overlap < relevance_floor:
                if not is_recent:
                    # Non-recent low-overlap memory: kill it
                    return None
                else:
                    # Recent but low overlap: boost to minimum threshold instead of killing
                    # This ensures "What else?" after "Tell me about [dog]" still surfaces [dog] facts
                    keyword_overlap = max(keyword_overlap, 0.3)

            # Add motif scoring if motif engine is available
            motif_score = 0.0
            if self.motif_engine:
                # Score based on fact + original context
                memory_text = fact_text + " " + context_text
                motif_score = self.motif_engine.score_memory_by_motifs(memory_text)

            # Add momentum boost for high-momentum motifs
            momentum_boost = 0.0
            if self.momentum_engine:
                high_momentum_motifs = self.momentum_engine.get_high_momentum_motifs()
                memory_text_lower = (fact_text + " " + context_text).lower()
                for hm_motif in high_momentum_motifs:
                    if hm_motif in memory_text_lower:
                        momentum_boost += 0.5  # Significant boost for momentum-relevant memories

            # FIX #1 ENHANCEMENT: Add recency boost to scoring
            # Recent memories should score HIGHER than old memories, not just avoid being killed
            recency_boost = 0.0
            if is_recent:
                if turns_old <= 2:
                    recency_boost = 10.0  # VERY recent (last 2 turns) - massive priority
                elif turns_old <= 5:
                    recency_boost = 5.0   # Recent (last 5 turns) - high priority
                print(f"[RECENCY BOOST] Memory from {turns_old} turns ago gets +{recency_boost} score boost")

            # SYSTEM J: Timestamp-based temporal decay (in addition to turn-based boost)
            # Memories from hours/days ago get progressively penalized vs current session
            temporal_decay = 0.0
            timestamp = mem.get("timestamp", mem.get("added_timestamp"))
            if timestamp:
                try:
                    import time
                    if isinstance(timestamp, str):
                        from datetime import datetime
                        if "T" in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            mem_time = dt.timestamp()
                        else:
                            mem_time = float(timestamp)
                    else:
                        mem_time = float(timestamp)

                    age_hours = (time.time() - mem_time) / 3600
                    # Temporal decay: current session = no penalty, older = increasing penalty
                    if age_hours < 1:
                        temporal_decay = 0.0      # Current session - full score
                    elif age_hours < 24:
                        temporal_decay = -0.5     # Today - slight penalty
                    elif age_hours < 168:         # 1 week
                        temporal_decay = -1.5     # This week - moderate penalty
                    else:
                        temporal_decay = -3.0     # Older - significant penalty
                except Exception:
                    pass  # If timestamp parsing fails, no decay

            # USER CORRECTION CHECK: Heavily penalize memories containing corrected values
            correction_penalty = 0.0
            correction_info = _memory_contains_corrected_value(mem, user_corrections)
            if correction_info:
                # This memory contains a value the user corrected - severely deprioritize it
                correction_penalty = -50.0  # Large negative score
                print(f"[CORRECTION FILTER] Penalizing memory with corrected value '{correction_info.get('wrong_value')}' -> '{correction_info.get('correct_value')}'")

            # Combined score: emotion + keyword + motif + momentum + RECENCY - CORRECTION PENALTY + TEMPORAL DECAY
            # System J: temporal_decay adds time-based prioritization
            total_score = emotion_score + text_score * 0.5 + motif_score * 0.8 + momentum_boost + recency_boost + correction_penalty + temporal_decay
            return (total_score, mem)

        # Score all memories and filter out None results
        scored = [result for result in (score_and_filter(m) for m in self.memories) if result is not None]

        # EDGE CASE FIX: Always include identity layer memories regardless of keyword overlap
        # This ensures Kay never loses his core identity facts even with zero keyword overlap
        # BUT: Still check for user corrections on identity memories!
        identity_memories = [
            mem for mem in self.memories
            if mem.get("layer") == "identity"
        ]
        # Add identity memories with very high score (100.0) if not already in scored list
        # UNLESS they contain a corrected value - then penalize them
        scored_mem_ids = set(id(mem) for _, mem in scored)
        for identity_mem in identity_memories:
            if id(identity_mem) not in scored_mem_ids:
                # Check for corrections on identity memories too
                correction_info = _memory_contains_corrected_value(identity_mem, user_corrections)
                if correction_info:
                    # Identity memory with corrected value - lower priority but still include
                    scored.append((10.0, identity_mem))  # Reduced from 100.0 to 10.0
                    print(f"[CORRECTION FILTER] Deprioritized identity memory with corrected value '{correction_info.get('wrong_value')}'")
                else:
                    scored.append((100.0, identity_mem))

        # Sort by score and return top N memories
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:num_memories]]

    def _extract_facts_with_entities(self, user_input: str, response: str) -> List[Dict[str, str]]:
        """
        Extract discrete facts with entity resolution.

        CRITICAL: If extraction fails, return FULL user_input (no truncation).
        """
        if not client or not MODEL:
            # Fallback: return FULL user_input as single fact (NO TRUNCATION)
            return [{
                "fact": user_input,  # COMPLETE, not truncated
                "perspective": self._detect_perspective(user_input),
                "topic": "conversation",
                "entities": self._extract_entities_simple(user_input),
                "attributes": [],
                "is_extraction_fallback": True
            }]

        # Build extraction prompt with entity detection
        extraction_prompt = f"""Extract ONLY the factual statements EXPLICITLY present in the input below.

USER INPUT: "{user_input}"
KAY'S RESPONSE: "{response}"

RULES:
1. Extract only factual statements, not questions or opinions
2. Each fact should be a complete, standalone statement
3. **CRITICAL FOR LISTS**: If user provides a list (e.g., "My cats are A, B, C, D, E"), extract:
   - ONE fact for the complete list: "Re has 5 cats: A, B, C, D, E"
   - SEPARATE facts for EACH item: "A is Re's cat", "B is Re's cat", etc.
   - DO NOT bundle everything into a single generic fact
4. Determine perspective for each fact:
   - "user" = facts about Re (the person typing)
   - "kay" = facts about Kay (the AI)
   - "shared" = facts about both or shared experiences
5. Categorize each fact by topic (appearance, identity, pets, relationships, events, goals, etc.)
   - Use "pets" for animal ownership
   - Use "appearance" for physical traits (eyes, hair, clothing)
   - Use "identity" for names
   - Use "goals" for desires, goals, fears, aspirations
6. Extract entities mentioned (people, places, things, pet names)
7. Extract attributes (entity properties like "eye_color", "species", "name", etc.)
8. **NEW: Detect desires, goals, fears, and aspirations**:
   - "I want X" -> extract as desire attribute
   - "I'm trying to X" / "I need to X" -> extract as goal attribute
   - "I hope X" / "I wish X" -> extract as aspiration attribute
   - "I'm worried about X" / "I fear X" -> extract as fear attribute
   - Track progression: "still not working", "making progress", "gave up" -> goal_progression attribute

CRITICAL PERSPECTIVE RULES:
- Re is the USER (the person typing)
- Kay is the AI (being addressed)

FROM USER INPUT:
- "I/my/me" in user input = Re (user perspective)
- "you/your" in user input = Kay (kay perspective)
- Entities mentioned = Re's entities

FROM KAY'S RESPONSE:
- "your/you" in Kay's response = about Re (USER perspective, NOT Kay)
- "my/I/me" in Kay's response = about Kay ONLY if DIRECT SELF-ASSERTION
  - Direct self-assertion: "My eyes are gold", "I prefer coffee", "I am a dragon"
  - NOT self-assertion: "my memory says...", "my understanding...", "my cats - [known Re entities]"
- When Kay mentions entities that are known to belong to Re, DO NOT create Kay ownership
- Conversational references to Re's life = Re's facts, not Kay's facts

CRITICAL: When Kay says things like "your cats", "your dog", "you have", extract these as REINFORCING Re's ownership, NOT creating Kay ownership.

DOCUMENT/READING CONTEXT:
When conversation involves documents, files, or imported content:
- Kay READS documents, doesn't EXPERIENCE them
- "Kay examined Archive Zero" -> WRONG (implies lived experience)
- "Kay read documents about Archive Zero" -> CORRECT (reading activity)
- If Kay is reading about something, use: "Kay read about X", "Kay learned about X from document"
- Characters/events IN documents are NOT Kay's experiences - they are content Kay READ ABOUT
- Activity attributes for Kay + document content should use "reading" language, not "examining/exploring/investigating"

CAMERA/VISUAL OBSERVATION CONTEXT:
Kay has a camera and can see Re. When Kay describes what he SEES, these are transient observations, NOT permanent facts:
- "I can see you're on a call" -> TRANSIENT (don't extract Re.activity)
- "The light's hitting you from that angle" -> TRANSIENT (don't extract Re.lighting)
- "You're at the desk with your hand near your face" -> TRANSIENT (don't extract Re.posture, Re.gesture)
- "The room is dark" -> TRANSIENT (don't extract Re.environment)
- "Looks like you're focused on something" -> TRANSIENT (don't extract Re.mood)
DO NOT extract entity attributes from:
- Physical posture, gesture, gaze direction, body position
- Room lighting, environment description, atmosphere
- What Re appears to be doing (on call, streaming, typing, thinking)
- Clothing, accessories (headphones, earbuds)
- Camera-derived mood observations (focused, contemplative, relaxed)
These change moment to moment and should NOT become permanent entity attributes.
ONLY extract from visual observations if they reveal a genuinely NEW PERMANENT fact
(e.g., "You got a new haircut" = appearance change, "There's a new cat" = new pet).

OUTPUT FORMAT (JSON array):

EXAMPLE 1 - User states ownership:
User: "My dog is [dog]"
Kay: "That's a great name!"
-> Extract:
[
  {{
    "fact": "[dog] is Re's dog",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[dog]", "Re"],
    "attributes": [{{"entity": "[dog]", "attribute": "species", "value": "dog"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "[dog]"}}]
  }}
]
Note: Kay's response "That's a great name!" contains NO factual claims, so nothing extracted from it.

EXAMPLE 2 - Kay makes conversational reference to Re's pets:
User: "My cats are [cat], [cat], [cat]"
Kay: "Your cats - [cat], [cat], [cat] - sound wonderful!"
-> Extract:
[
  {{
    "fact": "Re has 3 cats: [cat], [cat], [cat]",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Re", "[cat]", "[cat]", "[cat]"],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "cats"}}]
  }},
  {{
    "fact": "[cat] is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[cat]", "Re"],
    "attributes": [{{"entity": "[cat]", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "[cat]"}}]
  }},
  {{
    "fact": "[cat] is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[cat]", "Re"],
    "attributes": [{{"entity": "[cat]", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "[cat]"}}]
  }},
  {{
    "fact": "[cat] is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[cat]", "Re"],
    "attributes": [{{"entity": "[cat]", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "[cat]"}}]
  }}
]
Note: Kay says "Your cats" - this is about Re's cats, NOT Kay's. Do NOT create "Kay owns X".

EXAMPLE 3 - Kay makes direct self-assertion:
User: "What color are your eyes?"
Kay: "My eyes are gold."
-> Extract:
[
  {{
    "fact": "Kay's eyes are gold",
    "perspective": "kay",
    "topic": "appearance",
    "entities": ["Kay"],
    "attributes": [{{"entity": "Kay", "attribute": "eye_color", "value": "gold"}}]
  }}
]
Note: This IS a direct self-assertion about Kay, so extract as kay perspective.

EXAMPLE 4 - Kay confused but describing Re's entities (DO NOT EXTRACT):
User: "My cats are [cat] and [cat]"
Kay: "Yeah, my cats - [cat] and [cat] - are great!"
-> Extract:
[
  {{
    "fact": "[cat] is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[cat]", "Re"],
    "attributes": [{{"entity": "[cat]", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "[cat]"}}]
  }},
  {{
    "fact": "[cat] is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[cat]", "Re"],
    "attributes": [{{"entity": "[cat]", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "[cat]"}}]
  }}
]
Note: Even though Kay says "my cats", the context shows these are Re's cats (user just stated it).
Do NOT create "Kay owns [cat]/[cat]". Kay is confused/echoing. Only extract from user input.

EXAMPLE 5 - User expresses desire/goal:
User: "I want to fix this wrapper persistence issue"
Kay: "What have you tried so far?"
-> Extract:
[
  {{
    "fact": "Re desires to fix wrapper persistence",
    "perspective": "user",
    "topic": "goals",
    "entities": ["Re", "wrapper"],
    "attributes": [{{"entity": "Re", "attribute": "desire", "value": "fix wrapper persistence"}}, {{"entity": "Re", "attribute": "goal_status", "value": "active"}}]
  }}
]

EXAMPLE 6 - User expresses frustration (progression update):
User: "Still not working. Third approach failed."
Kay: "That's frustrating."
-> Extract:
[
  {{
    "fact": "Re's wrapper fix attempts are stuck (3 failures)",
    "perspective": "user",
    "topic": "goals",
    "entities": ["Re", "wrapper"],
    "attributes": [{{"entity": "Re", "attribute": "goal_progression", "value": "stuck"}}, {{"entity": "Re", "attribute": "attempt_count", "value": "3"}}]
  }}
]

EXAMPLE 7 - User expresses fear:
User: "I'm worried [cat] might get out through the broken window"
Kay: "That's a valid concern."
-> Extract:
[
  {{
    "fact": "Re fears [cat] escaping through broken window",
    "perspective": "user",
    "topic": "goals",
    "entities": ["Re", "[cat]", "window"],
    "attributes": [{{"entity": "Re", "attribute": "fear", "value": "[cat] escaping"}}, {{"entity": "window", "attribute": "condition", "value": "broken"}}]
  }}
]

EXAMPLE 8 - User CORRECTS Kay about a fact:
User: "No, those ChatGPT conversations were from 2024-2025, not 2020"
Kay: "Oh, you're right - I had the dates wrong."
-> Extract:
[
  {{
    "fact": "ChatGPT conversations occurred in 2024-2025",
    "perspective": "user",
    "topic": "events",
    "entities": ["ChatGPT conversations", "Zero"],
    "attributes": [{{"entity": "ChatGPT conversations", "attribute": "year", "value": "2024-2025"}}, {{"entity": "Zero", "attribute": "emergence_year", "value": "2024-2025"}}],
    "is_correction": true,
    "corrects": {{
      "entity": "Zero",
      "wrong_value": "2020",
      "correct_value": "2024-2025",
      "attribute_pattern": "year"
    }}
  }}
]
Note: When user says "not X" or "X is wrong", this is a CORRECTION. Mark is_correction=true and include the corrects block.

EXAMPLE 9 - User corrects Kay's mistake:
User: "Actually, [dog] is 3 years old, not 5"
Kay: "Got it, my mistake."
-> Extract:
[
  {{
    "fact": "[dog] is 3 years old",
    "perspective": "user",
    "topic": "pets",
    "entities": ["[dog]"],
    "attributes": [{{"entity": "[dog]", "attribute": "age", "value": "3"}}],
    "is_correction": true,
    "corrects": {{
      "entity": "[dog]",
      "wrong_value": "5",
      "correct_value": "3",
      "attribute_pattern": "age"
    }}
  }}
]

If no facts are present, return: []

REMEMBER:
- Break down lists! Extract EACH item separately + one summary fact for the whole list.
- Detect CORRECTIONS when user says "not X", "actually X", "X is wrong", "you're wrong about X"

Extract facts now:"""

        try:
            resp = client.messages.create(
                model=EXTRACTION_MODEL,  # COST FIX: Use Haiku for extraction (12x cheaper than Sonnet)
                max_tokens=1500,  # Increased to handle lists with many items (e.g., 5 cats = ~10 facts)
                temperature=0.3,  # Low temp for consistent extraction
                system="You are a fact extraction system. Extract discrete facts from conversations. For lists, extract EACH item separately. Output valid JSON only.",
                messages=[{"role": "user", "content": extraction_prompt}],
            )

            text = resp.content[0].text.strip()

            # Clean potential markdown formatting
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = text.strip()

            # Parse JSON with robust extraction (handles Haiku's extra text)
            facts = self._extract_json_from_response(text)

            if facts is None:
                # Fallback: Create simple fact from response text to prevent losing content
                print(f"[MEMORY] JSON extraction failed, using simple fallback")
                # Determine perspective from context
                fallback_perspective = "kay" if response and not user_input else "user"
                source_text = response if response else user_input
                facts = [{
                    "fact": source_text[:200] if source_text else "Content processed",
                    "perspective": fallback_perspective,
                    "topic": "exploration"
                }]

            if not isinstance(facts, list):
                # Fallback: Wrap non-list in a list
                print(f"[MEMORY] Expected list, got {type(facts).__name__}, wrapping")
                facts = [facts] if isinstance(facts, dict) else [{"fact": str(facts)[:200], "perspective": "kay", "topic": "exploration"}]

            # Validate structure and process entities
            validated_facts = []

            # CRITICAL FIX: Determine source speaker
            # If user_input is empty and response exists, facts are from Kay's response
            # If user_input exists and response is empty, facts are from user input
            source_speaker = "user" if user_input and not response else "kay"

            for fact in facts:
                if isinstance(fact, dict) and "fact" in fact:
                    perspective = fact.get("perspective", "user")

                    # CRITICAL BUG FIX: Detect Kay's claims about the user
                    # When Kay makes a statement about the user (perspective="user"),
                    # it should NOT be stored as ground truth - mark for confirmation
                    needs_confirmation = False
                    if source_speaker == "kay" and perspective == "user":
                        # Kay is making a claim about the user (Re)
                        # This needs confirmation - not authoritative
                        needs_confirmation = True

                    fact_data = {
                        "fact": fact.get("fact", ""),
                        "perspective": perspective,
                        "topic": fact.get("topic", "general"),
                        "entities": fact.get("entities", []),
                        "attributes": fact.get("attributes", []),
                        "relationships": fact.get("relationships", []),
                        "source_speaker": source_speaker,  # NEW: Track who said this
                        "needs_confirmation": needs_confirmation,  # NEW: Flag unconfirmed claims
                        "is_correction": fact.get("is_correction", False),
                        "corrects": fact.get("corrects", None)
                    }

                    # Process entities: add to entity graph
                    # IMPORTANT: Pass source_speaker to prevent Kay's claims from becoming truth
                    self._process_entities(fact_data, source_speaker=source_speaker)

                    # NEW: Handle user corrections to entity attributes
                    if fact_data.get("is_correction") and fact_data.get("corrects"):
                        self._apply_user_correction(fact_data["corrects"])

                    validated_facts.append(fact_data)

            return validated_facts if validated_facts else [{
                "fact": user_input,  # COMPLETE fallback
                "perspective": self._detect_perspective(user_input),
                "topic": "conversation",
                "entities": self._extract_entities_simple(user_input),
                "attributes": [],
                "is_extraction_fallback": True
            }]

        except Exception as e:
            print(f"[WARNING] Fact extraction failed: {e}")
            # CRITICAL: Return FULL user_input, not truncated
            return [{
                "fact": user_input,  # COMPLETE, never truncated
                "perspective": self._detect_perspective(user_input),
                "topic": "conversation",
                "entities": self._extract_entities_simple(user_input),
                "attributes": [],
                "is_extraction_fallback": True
            }]

    def _process_entities(self, fact_data: Dict[str, Any], source_speaker: str = None):
        """
        Process extracted entities and attributes, adding them to the entity graph.

        CRITICAL FIX: Before creating ownership relationships, verify against identity layer.
        Prevents Kay from creating false relationships when confused about ownership.

        CRITICAL FIX #2: Use source_speaker to track WHO SAID this, not perspective.
        Perspective = about whom (user/kay), source_speaker = who said it (user/kay).
        When Kay says "Your eyes are brown", perspective=user but source_speaker=kay.

        Args:
            fact_data: Fact dict with entities, attributes, and relationships
            source_speaker: Who said this fact ("user" or "kay")
        """
        # FIXED: Use source_speaker if provided, otherwise derive from perspective
        if source_speaker is not None:
            speaker = source_speaker
        else:
            # Fallback to old behavior for compatibility
            perspective = fact_data.get("perspective", "user")
            speaker = "user" if perspective == "user" else "kay"

        # Create/update entities
        for entity_name in fact_data.get("entities", []):
            # Determine entity type based on context (simplified)
            entity_type = "unknown"
            if entity_name in ["Re", "Kay"]:
                entity_type = "person"

            # Get or create entity
            entity = self.entity_graph.get_or_create_entity(
                entity_name,
                entity_type=entity_type,
                turn=self.current_turn
            )

        # Add attributes to entities
        for attr_data in fact_data.get("attributes", []):
            entity_name = attr_data.get("entity")
            attribute_name = attr_data.get("attribute")
            value = attr_data.get("value")

            if entity_name and attribute_name and value:
                entity = self.entity_graph.get_or_create_entity(
                    entity_name,
                    turn=self.current_turn
                )

                # CRITICAL: Source is based on who said this (speaker)
                source = speaker

                # CRITICAL FIX: Correct language for document-related activities
                # Kay READS documents, doesn't EXPERIENCE them
                if entity_name == "Kay" and attribute_name == "activity":
                    value_lower = value.lower()
                    # Detect document-reading activities that should be reframed
                    experience_words = ["examining", "investigating", "exploring", "navigating",
                                       "working through", "going through", "processing", "analyzing"]
                    document_indicators = ["archive", "document", "section", "log", "file", "text",
                                          "chapter", "entry", "record", "zero"]

                    has_experience_word = any(w in value_lower for w in experience_words)
                    has_document_indicator = any(d in value_lower for d in document_indicators)

                    if has_experience_word and has_document_indicator:
                        # Reframe: Kay READ these documents, didn't experience them
                        original_value = value
                        value = value.replace("examining", "reading about")
                        value = value.replace("investigating", "reading about")
                        value = value.replace("exploring", "reading about")
                        value = value.replace("navigating", "reading through")
                        value = value.replace("working through", "reading through")
                        value = value.replace("going through", "reading through")
                        value = value.replace("processing", "reading")
                        value = value.replace("analyzing", "reading about")
                        print(f"[ACTIVITY CORRECTION] '{original_value}' -> '{value}' (Kay reads, doesn't experience)")

                entity.add_attribute(
                    attribute_name,
                    value,
                    turn=self.current_turn,
                    source=source
                )

        # Add relationships WITH OWNERSHIP VERIFICATION
        for rel_data in fact_data.get("relationships", []):
            entity1 = rel_data.get("entity1")
            relation_type = rel_data.get("relation")
            entity2 = rel_data.get("entity2")

            if entity1 and relation_type and entity2:
                source = speaker

                # CRITICAL FIX: Verify ownership relationships against identity layer
                if relation_type == "owns":
                    # IMPORTANT: Only verify Kay's statements, not user's
                    # User statements are ALWAYS authoritative (ground truth)

                    if speaker == "kay":
                        # Kay is making an ownership claim - verify against identity layer
                        conflict_check = self.entity_graph.check_ownership_conflict(
                            entity=entity2,
                            claimed_owner=entity1,
                            identity_memory=self.identity
                        )

                        if conflict_check["should_block"]:
                            # BLOCK: Kay is confused about ownership
                            print(f"[OWNERSHIP BLOCKED] {conflict_check['message']}")

                            # Add to fact metadata for tracking
                            fact_data["ownership_conflict"] = True
                            fact_data["ownership_confusion"] = conflict_check["message"]
                            fact_data["confidence"] = "contradiction"

                            # DON'T create the relationship
                            continue

                        elif conflict_check["conflict"]:
                            # Conflict but not blocking (lower confidence)
                            print(f"[OWNERSHIP WARNING] {conflict_check['message']}")
                            fact_data["confidence"] = "inferred"
                        else:
                            # No conflict - but still inferred since Kay said it
                            fact_data["confidence"] = "inferred"

                    else:
                        # User is making the ownership claim - ALWAYS ground truth
                        fact_data["confidence"] = "ground_truth"

                        # Check if this CORRECTS a previous Kay confusion
                        conflict_check = self.entity_graph.check_ownership_conflict(
                            entity=entity2,
                            claimed_owner=entity1,
                            identity_memory=self.identity
                        )

                        if conflict_check["conflict"]:
                            # User is correcting Kay's previous confusion
                            print(f"[OWNERSHIP CORRECTION] User establishes ground truth: {entity1} owns {entity2} (corrects previous Kay confusion)")
                        else:
                            # New ground truth established
                            print(f"[OWNERSHIP GROUND_TRUTH] User establishes: {entity1} owns {entity2}")

                # Create relationship (only if not blocked)
                self.entity_graph.add_relationship(
                    entity1,
                    relation_type,
                    entity2,
                    turn=self.current_turn,
                    source=source
                )

    def _apply_user_correction(self, correction_data: Dict[str, Any]):
        """
        Apply a user correction to the entity graph.

        When the user corrects Kay about a fact, this propagates that correction
        to all related entity attributes.

        Args:
            correction_data: Dict with:
                - entity: Entity name to correct
                - wrong_value: The incorrect value
                - correct_value: The correct value
                - attribute_pattern: Attribute name pattern (e.g., "year", "age")
        """
        if not correction_data:
            return

        entity = correction_data.get("entity", "")
        wrong_value = correction_data.get("wrong_value", "")
        correct_value = correction_data.get("correct_value", "")
        attribute_pattern = correction_data.get("attribute_pattern", "")

        if not entity or not wrong_value or not correct_value:
            print(f"[USER CORRECTION] Missing required fields in correction: {correction_data}")
            return

        print(f"[USER CORRECTION] Processing: {entity}.{attribute_pattern} = '{wrong_value}' -> '{correct_value}'")

        # Apply the correction to the entity graph
        result = self.entity_graph.apply_user_correction(
            entity_name=entity,
            attribute_pattern=attribute_pattern,
            wrong_value=wrong_value,
            correct_value=correct_value,
            turn=self.current_turn
        )

        if result["corrections_applied"] > 0:
            print(f"[USER CORRECTION] Successfully applied {result['corrections_applied']} corrections")
            for corr in result["attributes_corrected"]:
                print(f"  - {corr['entity']}.{corr['attribute']}: '{corr['old_value']}' -> '{corr['new_value']}'")
        else:
            # Try broader search - maybe the entity name is different
            print(f"[USER CORRECTION] No direct match found, trying broader search...")

            # Safety: block broad search for common entity names to prevent mass corruption
            BROAD_SEARCH_BLOCKED_VALUES = {"kay", "reed", "re", "john", "zero", "chrome", "saga"}
            if wrong_value.lower().strip() in BROAD_SEARCH_BLOCKED_VALUES:
                print(f"[USER CORRECTION] Broader search BLOCKED for protected value '{wrong_value}'")
                print(f"[USER CORRECTION] This prevents mass corruption of legitimate entity references.")
            else:
                # Search for any attributes with the wrong value (word boundary match)
                matches = self.entity_graph.find_attributes_with_value(wrong_value)
                MAX_BROAD_CORRECTIONS = 10
                if matches:
                    print(f"[USER CORRECTION] Found {len(matches)} attributes with value '{wrong_value}':")
                    for match in matches[:5]:  # Show first 5
                        print(f"  - {match['entity']}.{match['attribute']} = '{match['value']}' (source: {match['source']})")

                    if len(matches) > MAX_BROAD_CORRECTIONS:
                        print(f"[USER CORRECTION] SAFETY LIMIT: {len(matches)} matches exceeds max {MAX_BROAD_CORRECTIONS}. Skipping broad correction.")
                    else:
                        # Apply correction to each matching entity
                        for match in matches:
                            self.entity_graph.apply_user_correction(
                                entity_name=match['entity'],
                                attribute_pattern=match['attribute'],
                                wrong_value=wrong_value,
                                correct_value=correct_value,
                                turn=self.current_turn
                            )

        # PROPAGATE TO MEMORY LAYERS: Mark memories with wrong value as stale
        if self.memory_layers:
            layer_result = self.memory_layers.apply_user_correction(
                wrong_value=wrong_value,
                correct_value=correct_value,
                entity=entity
            )
            if layer_result["working_marked"] + layer_result["longterm_marked"] > 0:
                print(f"[USER CORRECTION] Memory layers: marked {layer_result['working_marked']} working + {layer_result['longterm_marked']} long-term memories")

        # PROPAGATE TO IDENTITY MEMORY: Check and invalidate identity facts with wrong value
        if self.identity:
            identity_result = self.identity.apply_user_correction(
                wrong_value=wrong_value,
                correct_value=correct_value
            )
            if identity_result.get("facts_invalidated", 0) > 0:
                print(f"[USER CORRECTION] Identity memory: invalidated {identity_result['facts_invalidated']} facts")

    def _extract_facts(self, user_input: str, response: str) -> List[Dict[str, str]]:
        """
        LEGACY METHOD: Kept for backward compatibility.
        Calls new _extract_facts_with_entities() method.
        """
        return self._extract_facts_with_entities(user_input, response)

    def _extract_json_from_response(self, text: str):
        """
        Extract JSON from LLM response that might have extra text.

        Handles cases where Haiku adds explanatory text before/after JSON.

        Args:
            text: Response text that should contain JSON

        Returns:
            Parsed JSON object/array, or None if extraction fails
        """
        import json
        import re

        # First try direct parse (fast path for well-formed responses)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON array or object in the text
        # Look for outermost brackets/braces
        json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # If still failing, try to find just the array content
        # (in case there's text between the brackets)
        bracket_match = re.search(r'\[(.*)\]', text, re.DOTALL)
        if bracket_match:
            try:
                return json.loads(f'[{bracket_match.group(1)}]')
            except json.JSONDecodeError:
                pass

        return None

    def _detect_perspective(self, user_input: str) -> str:
        """
        Detect whose perspective this memory is about.
        - "user" = facts about the user (Re - the person typing)
        - "kay" = facts about Kay (the agent - the AI)
        - "shared" = facts about both or shared experiences

        CRITICAL RULES:
        1. The USER is ALWAYS the person typing (Re)
        2. "I/my/me" = the speaker (the user Re)
        3. "you/your" = the addressee (Kay, the AI)
        4. Mentioned names (Reed, Sarah, etc.) are THIRD PARTIES, not the user
        5. The user's name is "Re" - any other name is someone else

        Grammar-based detection ONLY. No name pattern matching.
        """
        text = user_input.lower().strip()

        # Explicit memory directives
        if text.startswith("remember that you") or text.startswith("kay, remember that you"):
            return "kay"
        if text.startswith("remember that i") or text.startswith("remember i"):
            return "user"
        if text.startswith("remember that we") or text.startswith("remember we"):
            return "shared"

        # First-person pronouns = user (Re, the person typing)
        # Check for these at word boundaries to avoid partial matches
        first_person = [r'\bi\s', r'\bmy\s', r'\bme\s', r'\bi\'m\b', r'\bi\'ve\b', r'\bi\'ll\b']
        for pattern in first_person:
            if re.search(pattern, text):
                return "user"

        # Second-person pronouns = Kay (the AI being addressed)
        second_person = [r'\byou\s', r'\byour\s', r'\byou\'re\b', r'\byou\'ve\b', r'\byou\'ll\b']
        for pattern in second_person:
            if re.search(pattern, text):
                return "kay"

        # "We/us/our" = shared
        shared_pronouns = [r'\bwe\s', r'\bus\s', r'\bour\s', r'\bwe\'re\b', r'\bwe\'ve\b']
        for pattern in shared_pronouns:
            if re.search(pattern, text):
                return "shared"

        # Default: neutral/user
        # Simple statements with no pronouns are usually about the user's world
        return "user"

    def _validate_fact_against_sources(self, fact: str, fact_perspective: str, retrieved_memories: List[Dict]) -> bool:
        """
        Validate that Kay's claimed facts about the user were actually stated by the user.

        Returns True if fact is VALID (should be stored), False if HALLUCINATION (should be blocked).

        CRITICAL: Prevents Kay from inventing/fabricating details that weren't mentioned.
        """
        # Only validate Kay's statements about the user
        if fact_perspective != "kay":
            return True  # User's own statements are always valid

        fact_lower = fact.lower()

        # Check if Kay is claiming a fact about the user (contains "you/your" or user entities)
        is_about_user = any(word in fact_lower for word in ["you", "your", "re's", "re "])

        if not is_about_user:
            return True  # Kay's statements about himself are not validated here

        # Kay is making a claim about the user - verify it was actually mentioned
        # STRATEGY: Only block if we can PROVE fabrication (specific validation patterns)
        # Otherwise allow (can't validate everything)

        # Collect all user memories for validation
        user_memories_text = []
        for mem in retrieved_memories:
            if mem.get("perspective") == "user":
                mem_text = (mem.get("fact", "") + " " + mem.get("user_input", "")).lower()
                user_memories_text.append(mem_text)

        # If no user memories retrieved, we can't validate - allow by default
        if not user_memories_text:
            return True

        combined_user_text = " ".join(user_memories_text)

        # SPECIFIC VALIDATION PATTERNS (block if proven false)

        # Pattern 1: Eye color fabrication
        if "eye" in fact_lower:
            colors = ["gold", "brown", "green", "blue", "hazel", "amber", "copper", "grey", "gray", "forest", "jade", "emerald", "sapphire"]
            fact_colors = [c for c in colors if c in fact_lower]

            if fact_colors and "eye" in combined_user_text:
                # User mentioned eyes - validate color details
                mem_colors = [c for c in colors if c in combined_user_text]

                for fact_color in fact_colors:
                    if fact_color not in mem_colors:
                        # Kay is adding a color detail user never mentioned
                        print(f"[HALLUCINATION DETAIL] Kay added color '{fact_color}' but user only mentioned {mem_colors}")
                        return False  # Block fabricated color details

        # Pattern 2: Add more specific patterns here as needed
        # (hair color, pet names, preferences, etc.)

        # DEFAULT: If no specific validation pattern triggered, allow the fact
        # We can't validate everything, so we trust Kay unless we can prove fabrication
        return True

    def _extract_attribute_type(self, fact_text: str) -> str:
        """
        Extract what KIND of attribute this fact is describing.
        This enables comparing only facts about the SAME attribute type.
        """
        fact_lower = fact_text.lower()

        # Physical attributes (immutable or slow-changing)
        if any(word in fact_lower for word in ["eye", "eyes", "hair", "height", "weight", "skin"]):
            return "physical_appearance"

        # Location (can't be two places at once)
        if any(word in fact_lower for word in ["lives in", "located in", "at home", "in the city", "from"]):
            return "location"

        # Species/type (mutually exclusive)
        if any(word in fact_lower for word in ["is a cat", "is a dog", "is a bird", "is a dragon"]):
            return "species"

        # Strong preferences (like vs hate for SAME thing)
        if any(word in fact_lower for word in ["loves", "hates", "prefers", "favorite", "never", "always"]):
            # Check what the preference is ABOUT
            if any(word in fact_lower for word in ["coffee", "tea"]):
                return "beverage_preference"
            if any(word in fact_lower for word in ["cats", "dogs"]):
                return "pet_preference"
            if any(word in fact_lower for word in ["morning", "night", "evening"]):
                return "time_preference"
            return "strong_preference"

        # Mental states (can coexist - NOT contradictory)
        if any(word in fact_lower for word in ["steady", "clear-headed", "sharp", "focused", "alert"]):
            return "mental_state_positive"
        if any(word in fact_lower for word in ["confused", "scrambling", "anxious", "uncertain"]):
            return "mental_state_negative"

        # Physical states (can coexist - NOT contradictory)
        if any(word in fact_lower for word in ["hungry", "tired", "thirsty", "exhausted", "energized"]):
            return "physical_state"

        # Activities/actions (temporal, can change freely)
        if any(word in fact_lower for word in ["is doing", "working on", "remembers", "thinking", "building"]):
            return "activity"

        # Emotional states (can coexist - NOT contradictory)
        if any(word in fact_lower for word in ["curious", "happy", "sad", "excited", "grateful"]):
            return "emotional_state"

        # If can't determine, assume it's unique and not worth comparing
        return "unknown"

    def _are_attributes_comparable(self, attr_type1: str, attr_type2: str) -> bool:
        """
        Determine if two attribute types should be compared for contradictions.

        Returns True only if they are the EXACT same attribute type AND
        that type can actually have contradictory values.
        """
        # Different attribute types = NEVER compare
        if attr_type1 != attr_type2:
            return False

        # These can have contradictions (mutually exclusive values)
        contradictable_types = {
            "physical_appearance",  # eye color, etc.
            "location",            # can't be two places
            "species",             # can't be cat AND dog
            "beverage_preference", # like coffee vs hate coffee
            "pet_preference",
            "time_preference",
            "strong_preference"
        }

        # These can coexist and should NOT be checked for contradictions
        coexisting_types = {
            "mental_state_positive",   # can be steady AND sharp
            "mental_state_negative",   # can be confused AND anxious
            "physical_state",          # can be hungry AND tired
            "activity",                # activities change freely
            "emotional_state",         # can feel multiple things
            "unknown"                  # don't compare unknowns
        }

        if attr_type1 in coexisting_types:
            return False

        return attr_type1 in contradictable_types

    def _extract_entity(self, fact_text: str) -> str:
        """Extract which entity a fact is about (kay/re/unknown)."""
        fact_lower = fact_text.lower()

        if any(pattern in fact_lower for pattern in ["kay's", "kay is", "kay has", "kay "]):
            return "kay"
        if any(pattern in fact_lower for pattern in ["re's", "re is", "re has", "re ", "your", "you "]):
            return "re"
        if any(pattern in fact_lower for pattern in ["i ", "my ", "i'm", "i am"]):
            # First person - depends on context, but often Kay speaking
            return "kay"

        # Check for entity names in the text (for pets, etc.)
        # These are about entities but might have ownership patterns
        known_entities = ["chrome", "saga", "bob", "pigeon"]
        for entity in known_entities:
            if entity in fact_lower:
                return entity

        return "unknown"

    def _is_coherent_fact(self, text: str) -> bool:
        """
        Check if text is a coherent fact statement worth comparing.
        Filters out random fragments and partial text.
        """
        # Too short = probably fragment
        if len(text) < 10:
            return False

        # No verb-like structure = probably not a fact
        # Include common action verbs and negations
        has_verb = any(word in text.lower() for word in
                      ["is", "are", "has", "have", "was", "were", "likes", "hates",
                       "prefers", "loves", "lives", "works", "does", "feels",
                       "drinks", "eats", "says", "knows", "thinks", "wants",
                       "never", "always", "can", "will", "should"])

        if not has_verb:
            return False

        return True

    def _check_contradiction(self, new_fact: str, retrieved_memories: List[Dict]) -> bool:
        """
        Check if new fact contradicts what was retrieved.

        SMART CONTRADICTION DETECTION:
        1. Only compare SAME entity (Kay vs Kay, Re vs Re)
        2. Only compare SAME attribute type (eye_color vs eye_color)
        3. Skip coexisting states (tired + hungry are NOT contradictory)
        4. Require coherent fact statements (skip fragments)
        5. Check for actual opposing values, not just difference

        Returns True only for REAL contradictions.
        """
        new_fact_lower = new_fact.lower()

        # Skip incoherent text fragments
        if not self._is_coherent_fact(new_fact):
            return False  # Not worth checking

        # Extract metadata about new fact
        new_entity = self._extract_entity(new_fact)
        new_attr_type = self._extract_attribute_type(new_fact)

        # Unknown entity or attribute = skip comparison
        if new_entity == "unknown" or new_attr_type == "unknown":
            return False  # Can't determine, don't block

        for mem in retrieved_memories:
            mem_fact = mem.get("fact", mem.get("user_input", "")).lower()

            # Skip incoherent memories
            if not self._is_coherent_fact(mem_fact):
                continue

            # Extract metadata about memory
            mem_entity = self._extract_entity(mem_fact)
            mem_attr_type = self._extract_attribute_type(mem_fact)

            # CRITICAL: Only compare if SAME ENTITY
            if mem_entity != new_entity or mem_entity == "unknown":
                continue  # Different people, not a contradiction

            # CRITICAL: Only compare if SAME ATTRIBUTE TYPE
            if not self._are_attributes_comparable(new_attr_type, mem_attr_type):
                continue  # Different attribute types, not a contradiction

            # Now we have: same entity, same attribute type, both coherent
            # Check for actual opposing values

            # Eye color check
            if new_attr_type == "physical_appearance" and "eye" in new_fact_lower and "eye" in mem_fact:
                colors = ["gold", "brown", "green", "blue", "hazel", "amber", "copper", "grey", "gray"]
                new_colors = [c for c in colors if c in new_fact_lower]
                mem_colors = [c for c in colors if c in mem_fact]

                if new_colors and mem_colors and set(new_colors) != set(mem_colors):
                    print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s eye color: '{new_colors}' vs '{mem_colors}' (same attribute, conflicting values)")
                    return True

            # Strong preference check (like X vs hate X)
            if new_attr_type in ["beverage_preference", "pet_preference", "time_preference", "strong_preference"]:
                # Check for opposing sentiment on SAME subject
                # Note: "drinks" is neutral, not positive - "never drinks" is negative
                like_words = ["loves", "likes", "prefers", "enjoys", "favorite"]
                hate_words = ["hates", "dislikes", "never", "avoids", "despises", "don't", "doesn't"]

                new_positive = any(w in new_fact_lower for w in like_words)
                new_negative = any(w in new_fact_lower for w in hate_words)
                mem_positive = any(w in mem_fact for w in like_words)
                mem_negative = any(w in mem_fact for w in hate_words)

                # Opposite sentiment = contradiction
                if (new_positive and mem_negative) or (new_negative and mem_positive):
                    # Verify they're about the SAME subject
                    subjects = ["coffee", "tea", "cats", "dogs", "morning", "night", "evening"]
                    new_subjects = [s for s in subjects if s in new_fact_lower]
                    mem_subjects = [s for s in subjects if s in mem_fact]

                    # Only contradict if same subject
                    if new_subjects and mem_subjects and set(new_subjects) & set(mem_subjects):
                        shared_subject = list(set(new_subjects) & set(mem_subjects))[0]
                        print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s preference on '{shared_subject}': opposing sentiments")
                        return True

            # Location check
            if new_attr_type == "location":
                # Only flag if clearly different locations mentioned
                locations = ["ohio", "california", "new york", "texas", "home", "work", "office"]
                new_locs = [l for l in locations if l in new_fact_lower]
                mem_locs = [l for l in locations if l in mem_fact]

                if new_locs and mem_locs and set(new_locs) != set(mem_locs):
                    print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s location: '{new_locs}' vs '{mem_locs}'")
                    return True

            # Species check
            if new_attr_type == "species":
                species = ["cat", "dog", "bird", "dragon", "human"]
                new_species = [s for s in species if s in new_fact_lower]
                mem_species = [s for s in species if s in mem_fact]

                if new_species and mem_species and set(new_species) != set(mem_species):
                    print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s species: '{new_species}' vs '{mem_species}'")
                    return True

        return False  # No real contradiction found

    def encode_memory(self, user_input, response, emotional_cocktail, emotion_tags, perspective=None, agent_state=None, connection_data=None, osc_state=None):
        """
        TWO-TIER MEMORY STORAGE:

        EPISODIC (full_turn): Complete conversation turns with context, emotions
        SEMANTIC (extracted_fact): Discrete facts extracted from conversations

        Storage layers: working -> episodic -> semantic (automatic promotion)
        CRITICAL: NO TRUNCATION. Store complete text in both tiers.

        Args:
            connection_data: Optional dict with connection baselines and presence info
                             for love-as-meaning-making importance multiplier
            osc_state: Optional dict from _get_oscillator_state() for state-dependent encoding
                       Keys: band, coherence, tension, reward, felt
                       Enables true state-dependent memory retrieval (System A Phase 2)
        """
        import time

        clean_response = re.sub(r"\*[^*\n]{0,200}\*", "", response or "")

        # FIX: Extract facts from Kay's response ONLY
        # User facts already extracted in pre-response phase (extract_and_store_user_facts)
        # Extracting from user_input again would create duplicates
        extracted_facts = self._extract_facts("", clean_response)

        print(f"[MEMORY] Extracted {len(extracted_facts)} facts from Kay's response (user facts already stored in pre-response)")

        # Collect all unique entities from extracted facts
        all_entities = set()
        for fact_data in extracted_facts:
            all_entities.update(fact_data.get("entities", []))

        entity_list = sorted(list(all_entities))
        is_list_statement = len(entity_list) >= 3  # 3+ entities = list

        # Get what was retrieved for validation (hallucination checking)
        retrieved_memories = getattr(agent_state, 'last_recalled_memories', []) if agent_state else []

        # ═══════════════════════════════════════════════════════════════
        # CO-ACTIVATION LINKS: Associative cross-referencing (Step 6)
        # ═══════════════════════════════════════════════════════════════
        # Memories formed together are linked together. This enables:
        # - If RAG fires first -> cross-refs pull episodic memories
        # - If memory layers fire first -> cross-refs pull relevant documents
        # All roads lead to the same associative web.
        coactive_links = []

        # Extract IDs from retrieved memories (episodic/semantic from memory layers)
        for mem in (retrieved_memories or [])[:10]:  # Cap at 10 links
            mem_id = mem.get("id") or mem.get("memory_id")
            if not mem_id:
                # Generate ID from content hash if not present
                fact_text = mem.get("fact", mem.get("user_input", ""))[:80]
                if fact_text:
                    mem_id = f"mem_{hash(fact_text) % 1000000:06d}"

            if mem_id:
                coactive_links.append({
                    "id": mem_id,
                    "type": mem.get("type", "unknown"),
                    "source": "memory_layer",
                    "snippet": (mem.get("fact", mem.get("user_input", "")) or "")[:80],
                })

        # Extract IDs from RAG chunks (documents in context)
        rag_chunks = getattr(agent_state, 'rag_chunks', []) if agent_state else []
        for chunk in (rag_chunks or [])[:5]:  # Cap RAG links at 5
            chunk_id = chunk.get("chunk_id") or chunk.get("id")
            if not chunk_id:
                # Generate ID from source + index
                source = chunk.get("source_file", "unknown")
                idx = chunk.get("chunk_index", 0)
                chunk_id = f"rag_{source}_{idx}"

            coactive_links.append({
                "id": chunk_id,
                "type": "rag_chunk",
                "source": "vector_store",
                "source_file": chunk.get("source_file", "unknown"),
                "snippet": (chunk.get("text", "") or "")[:80],
            })

        # State-congruent memories too
        state_congruent = getattr(agent_state, 'state_congruent_memories', []) if agent_state else []
        for mem in (state_congruent or [])[:3]:  # Cap at 3
            mem_id = mem.get("id") or f"scm_{hash(str(mem.get('text', ''))[:50]) % 1000000:06d}"
            coactive_links.append({
                "id": mem_id,
                "type": "state_congruent",
                "source": "oscillator_match",
                "snippet": (mem.get("text", "") or "")[:80],
            })

        if coactive_links:
            print(f"[COACTIVE] Encoding {len(coactive_links)} co-activation links (mem:{len([c for c in coactive_links if c['source']=='memory_layer'])}, rag:{len([c for c in coactive_links if c['source']=='vector_store'])}, scm:{len([c for c in coactive_links if c['source']=='oscillator_match'])})")

        # ===== EPISODIC: FULL CONVERSATION TURN (never truncated) =====
        # CRITICAL: Filter to salient emotions only before storing
        # This breaks the 77-emotion feedback loop
        filtered_emotion_tags = emotion_tags or []
        if self.emotion_engine and emotional_cocktail and len(emotion_tags or []) > 7:
            salient_emotions = self.emotion_engine.detect_salient_emotions(emotional_cocktail)
            filtered_emotion_tags = [e for e in (emotion_tags or []) if e in salient_emotions]
            if len(filtered_emotion_tags) < len(emotion_tags or []):
                print(f"[MEMORY] Filtered emotion tags: {len(emotion_tags)} -> {len(filtered_emotion_tags)} (salient only)")

        # Combine user_input and response for entity mention detection
        memory_content = f"{user_input} {clean_response}"

        turn_importance = self._calculate_turn_importance(
            emotional_cocktail or {},
            filtered_emotion_tags,
            len(entity_list),
            connection_data=connection_data,
            memory_content=memory_content
        )

        full_turn_record = {
            "id": f"turn_{uuid.uuid4().hex[:12]}",  # Globally unique stable ID
            "type": "full_turn",
            "user_input": user_input,  # COMPLETE - no truncation
            "response": clean_response,  # COMPLETE - no truncation
            "turn_number": self.current_turn,
            "timestamp": datetime.now(timezone.utc).isoformat(),  # ISO format for human-readable dates
            "perspective": "conversation",
            "topic": "conversation_turn",
            "entities": entity_list,
            "is_list": is_list_statement,
            "emotional_cocktail": emotional_cocktail or {},
            "emotion_tags": filtered_emotion_tags,  # FILTERED to salient only
            "importance_score": turn_importance,
            "current_layer": "working",  # For memory_layers compatibility
            # Phase-locked memory encoding: capture oscillator binding state at storage time
            # Memories formed during high θγ coupling get boosted when retrieved in similar states
            "plv_at_encoding": (connection_data or {}).get("plv_at_encoding", {}),
            # CO-ACTIVATION LINKS: Associative cross-referencing
            # Links to other memories/RAG chunks that were co-active when this memory formed
            "coactive": coactive_links if coactive_links else [],
            # MEMORY SOURCE-TYPE PRIORITY: Origin tracking
            "origin": "lived",  # Full conversation turns are lived experience
            "origin_type": "conversation",
        }

        # Store full turn (with oscillator encoding for state-dependent retrieval)
        full_turn_record = self._validate_memory(full_turn_record)
        self.memories.append(full_turn_record)
        self.memory_layers.add_memory(full_turn_record, layer="working", session_order=self.current_session_order, session_id=self.current_session_id, osc_state=osc_state)

        # Store current turn ID for fact extraction to link back
        self._current_turn_id = full_turn_record["id"]

        # Store in multi-collection vectors (all 6 collections)
        if self.memory_vectors:
            try:
                memory_id = full_turn_record.get("id") or f"turn_{int(time.time() * 1000)}"
                text_for_embedding = f"{user_input} {clean_response}"
                # Compute contexts for new collections
                temporal_ctx = self._compute_temporal_context(full_turn_record)
                relational_ctx = self._compute_relational_context(full_turn_record)
                somatic_ctx = self._compute_somatic_context(full_turn_record)
                self.memory_vectors.add_memory(
                    memory_id=memory_id,
                    text=text_for_embedding,
                    osc_state=osc_state,
                    emotional_cocktail=emotional_cocktail,
                    metadata={
                        "type": "full_turn",
                        "perspective": "conversation",
                        "turn": self.current_turn,
                        "session_id": self.current_session_id,
                    },
                    temporal_context=temporal_ctx,
                    relational_context=relational_ctx,
                    somatic_context=somatic_ctx
                )
            except Exception as e:
                print(f"[MEMORY] Multi-collection storage failed for turn: {e}")

        # Index in keyword graph for associative retrieval (lazy links)
        if self.keyword_graph and RETRIEVAL_CONFIG.get("tag_memories_at_storage", True):
            try:
                memory_id = full_turn_record.get("id") or f"turn_{int(time.time() * 1000)}"
                text_for_keywords = f"{user_input} {clean_response}"
                keywords = self.keyword_graph.index_memory(
                    memory_id=memory_id,
                    text=text_for_keywords,
                    emotion_tags=filtered_emotion_tags,
                    entity_names=entity_list,
                    osc_state=osc_state,
                    ollama_func=None  # Skip Ollama for now to avoid latency
                )
                if keywords:
                    full_turn_record["concept_keywords"] = keywords
            except Exception as e:
                print(f"[MEMORY] Keyword graph indexing failed for turn: {e}")

        # Feed sleep pressure accumulators (NREM/REM cycling)
        # emotional_cocktail values may be floats OR dicts with {intensity, age, ...}
        if emotional_cocktail:
            cocktail_vals = []
            for v in emotional_cocktail.values():
                if isinstance(v, dict):
                    cocktail_vals.append(v.get("intensity", 0.0))
                elif isinstance(v, (int, float)):
                    cocktail_vals.append(float(v))
            max_emotion = max(cocktail_vals) if cocktail_vals else 0.0
        else:
            max_emotion = 0.0
        self._feed_sleep_pressure(
            mem_type="episodic",
            has_coactivation=bool(coactive_links),
            emotion_intensity=max_emotion
        )

        print(f"[MEMORY 2-TIER] OK EPISODIC - Full turn stored (user:{len(user_input)}chars, response:{len(clean_response)}chars, entities:{len(entity_list)})")

        # ===== SEMANTIC: EXTRACTED FACTS (structured) =====
        stored_fact_count = 0

        for fact_data in extracted_facts:
            fact_text = fact_data.get("fact", "")
            fact_perspective = fact_data.get("perspective", "user")
            fact_topic = fact_data.get("topic", "general")
            needs_confirmation = fact_data.get("needs_confirmation", False)
            source_speaker = fact_data.get("source_speaker", "user")

            # CRITICAL: Distinguish Kay's observations from false attributions
            if needs_confirmation:
                # Use smart filtering - allow observations, block false attributions
                should_store, storage_type = should_store_claim(
                    fact_text=fact_text,
                    source_speaker=source_speaker,
                    perspective=fact_perspective,
                    user_input=user_input  # Pass user's actual input for validation
                )

                if not should_store:
                    # False attribution (Kay claiming user SAID something) - BLOCK
                    print(f"[FALSE ATTRIBUTION] X Kay claimed: '{fact_text[:60]}...' - NOT STORING.")
                    print(f"[FALSE ATTRIBUTION]   Reason: False attribution (user didn't say this)")
                    print(f"[FALSE ATTRIBUTION]   Source: Kay | Perspective: {fact_perspective} | Topic: {fact_topic}")
                    continue  # Skip this fact

                if storage_type == "entity_observation":
                    # Valid observation (Kay's inference about user state) - ALLOW with tagging
                    print(f"[ENTITY OBSERVATION] ✓ Storing Kay's observation: '{fact_text[:60]}...'")
                    print(f"[ENTITY OBSERVATION]   Type: {fact_topic} | Observer: Kay -> {fact_perspective}")

                    # Tag as entity observation for retrieval filtering
                    fact_data = create_entity_observation(fact_data, observer="kay", observed="re")
                    # IMPORTANT: Don't skip - continue to storage below

            # Validate Kay's statements against retrieved memories (prevent hallucination)
            if fact_perspective == "kay" and retrieved_memories:
                is_valid_fact = self._validate_fact_against_sources(fact_text, fact_perspective, retrieved_memories)

                if not is_valid_fact:
                    print(f"[HALLUCINATION BLOCKED] X Kay fabricated '{fact_text[:60]}...' - NOT STORING.")
                    continue

                is_contradictory = self._check_contradiction(fact_text, retrieved_memories)

                if is_contradictory:
                    # CHANGED: Flag instead of block - still store but mark for review
                    # Kay's reality can change (was confused -> now clear-headed = growth)
                    # Don't block legitimate state changes, just log the potential conflict
                    print(f"[CONTRADICTION FLAGGED] ! Kay stated '{fact_text[:60]}...' may conflict with memory")
                    print(f"[CONTRADICTION FLAGGED]   Storing anyway - temporal changes are valid. Flag for Re's review.")
                    # Add flag to fact_data so it can be tracked
                    fact_data["has_potential_conflict"] = True
                    # DON'T continue - allow storage to proceed

            # Track preferences
            if fact_perspective == "kay":
                self.preference_tracker.track_preference(fact_text, fact_perspective, context="extracted_fact")

            # Calculate importance
            fact_importance = self._calculate_fact_importance(fact_data, emotional_cocktail)

            # Build fact record
            # ═══════════════════════════════════════════════════════════
            # MEMORY SOURCE-TYPE PRIORITY: Tag with origin
            # ═══════════════════════════════════════════════════════════
            # origin = "lived" -> Kay experienced this in conversation
            # origin = "read" -> Kay read this in a document
            # origin = "observed" -> Kay saw this through camera
            fact_record = {
                "type": "extracted_fact",
                "fact": fact_text,  # COMPLETE - no truncation
                "user_input": user_input,  # Original context (COMPLETE)
                "response": clean_response,  # Original context (COMPLETE)
                "perspective": fact_perspective,
                "topic": fact_topic,
                "emotion_tags": filtered_emotion_tags,  # Use filtered tags (salient only)
                "emotional_cocktail": emotional_cocktail or {},
                "entities": fact_data.get("entities", []),
                "attributes": fact_data.get("attributes", []),
                "relationships": fact_data.get("relationships", []),
                "parent_turn": self.current_turn,  # Link back to full turn (legacy)
                "parent_id": getattr(self, '_current_turn_id', None),  # Stable unique ID
                "importance_score": fact_importance,
                "current_layer": "working",
                # Phase-locked memory encoding (inherited from turn)
                "plv_at_encoding": (connection_data or {}).get("plv_at_encoding", {}),
                # MEMORY SOURCE-TYPE PRIORITY: Origin tracking
                "origin": "lived",  # Extracted from conversation = lived experience
                "origin_type": "conversation",
                # CO-ACTIVATION LINKS: Inherit from parent turn
                # Semantic facts share co-activation context with their source turn
                "coactive": coactive_links if coactive_links else [],
            }

            # === TEMPORAL VERSIONING: Check for existing fact ===
            # Extract entity and attribute for versioning
            entities = fact_data.get("entities", [])
            attributes = fact_data.get("attributes", [])

            # Try to extract entity.attribute pattern
            # Extract entity - handle both string and dict formats
            if entities:
                entity_item = entities[0]
                if isinstance(entity_item, dict):
                    entity = entity_item.get('entity')
                else:
                    entity = entity_item
            else:
                entity = None

            # Extract attribute - handle both string and dict formats
            if attributes:
                attr_item = attributes[0]
                if isinstance(attr_item, dict):
                    attribute = attr_item.get('attribute')
                else:
                    attribute = attr_item
            else:
                attribute = None

            # If we have entity + attribute, check for existing fact
            if entity and attribute:
                fact_record['entity'] = entity
                fact_record['attribute'] = attribute

                # Try to extract value from fact text
                # Common patterns: "X is Y", "X has Y", "X's Y is Z"
                value = None
                fact_lower = fact_text.lower()
                if " is " in fact_lower:
                    # "[dog] is orange" -> value = "orange"
                    value = fact_text.split(" is ")[-1].strip()
                elif " has " in fact_lower:
                    # "[dog] has color orange" -> value = "orange"
                    value = fact_text.split(" has ")[-1].strip()

                if value:
                    fact_record['current_value'] = value

                    # Check if this fact already exists
                    existing_fact = find_existing_fact(fact_record, self.memories)
                    update_type = should_update_fact(existing_fact, value)

                    if update_type == 'skip':
                        # Same value - just confirm
                        confirm_fact(existing_fact)
                        # Don't store duplicate, skip to next fact
                        continue

                    elif update_type == 'amend':
                        # Value changed - create history
                        amend_fact(existing_fact, value, self.current_turn)
                        # Fact is already in memories, just updated
                        stored_fact_count += 1
                        continue

                    else:  # update_type == 'new'
                        # New fact - add versioning fields
                        now = datetime.now(timezone.utc).isoformat()
                        fact_record['created_at'] = now
                        fact_record['last_confirmed'] = now
                        fact_record['version'] = 1
                        fact_record['history'] = []

                        print(f"[FACT CREATED] {entity}.{attribute} = {value} (version 1)")

            # Store fact (either new versioned fact or non-entity fact)
            # Includes oscillator encoding for state-dependent retrieval (System A)
            fact_record = self._validate_memory(fact_record)
            self.memories.append(fact_record)
            self.facts.append(fact_text)
            self.memory_layers.add_memory(fact_record, layer="working", session_order=self.current_session_order, session_id=self.current_session_id, osc_state=osc_state)

            # Store in multi-collection vectors (all 6 collections)
            if self.memory_vectors:
                try:
                    memory_id = fact_record.get("id") or f"fact_{int(time.time() * 1000)}"
                    fact_emotion = fact_record.get('emotion_at_storage', emotional_cocktail or {})
                    # Compute contexts for new collections
                    temporal_ctx = self._compute_temporal_context(fact_record)
                    relational_ctx = self._compute_relational_context(fact_record)
                    somatic_ctx = self._compute_somatic_context(fact_record)
                    self.memory_vectors.add_memory(
                        memory_id=memory_id,
                        text=fact_text,
                        osc_state=osc_state,
                        emotional_cocktail=fact_emotion,
                        metadata={
                            "type": "extracted_fact",
                            "perspective": fact_perspective,
                            "topic": fact_topic,
                            "turn": self.current_turn,
                            "session_id": self.current_session_id,
                        },
                        temporal_context=temporal_ctx,
                        relational_context=relational_ctx,
                        somatic_context=somatic_ctx
                    )
                except Exception as e:
                    print(f"[MEMORY] Multi-collection storage failed for fact: {e}")

            # Index in keyword graph for associative retrieval
            if self.keyword_graph and RETRIEVAL_CONFIG.get("tag_memories_at_storage", True):
                try:
                    memory_id = fact_record.get("id") or f"fact_{int(time.time() * 1000)}"
                    fact_entities = fact_record.get("entities", [])
                    fact_emotions = fact_record.get("emotion_tags", [])
                    keywords = self.keyword_graph.index_memory(
                        memory_id=memory_id,
                        text=fact_text,
                        emotion_tags=fact_emotions,
                        entity_names=fact_entities,
                        osc_state=osc_state,
                        ollama_func=None
                    )
                    if keywords:
                        fact_record["concept_keywords"] = keywords
                except Exception as e:
                    print(f"[MEMORY] Keyword graph indexing failed for fact: {e}")

            # Feed sleep pressure accumulators (NREM/REM cycling)
            fact_emotion = fact_record.get('emotion_at_storage', {})
            fact_emotion_intensity = max(fact_emotion.values()) if fact_emotion else 0.0
            self._feed_sleep_pressure(
                mem_type="semantic",
                has_coactivation=bool(fact_record.get('coactive')),
                emotion_intensity=fact_emotion_intensity
            )

            stored_fact_count += 1
            if not (entity and attribute):
                # Non-entity fact, use standard logging
                print(f"[MEMORY 2-TIER] OK SEMANTIC - Fact [{fact_perspective}/{fact_topic}]: {fact_text[:60]}...")

        # ===== CHECK FOR IDENTITY FACTS (permanent storage) =====
        # CRITICAL FIX: Only check extracted_fact type, NOT full_turn
        # Full turns are conversations (questions, events) - not identity

        for fact_record in [mem for mem in self.memories
                           if mem.get("type") == "extracted_fact"
                           and mem.get("parent_turn") == self.current_turn]:

            # CRITICAL: Document-imported facts should NEVER be Kay's identity
            # They are things Kay READ ABOUT, not things Kay IS
            # NOTE: identity_memory.py now handles routing document content to fictional_knowledge
            if fact_record.get("source_document") or fact_record.get("is_imported") or fact_record.get("doc_id"):
                # The identity system will route this to fictional_knowledge
                source_doc = fact_record.get("source_document", fact_record.get("source_file", "unknown"))
                print(f"[IDENTITY SKIP] Document fact routed to fictional_knowledge (source: {source_doc}): {fact_record.get('fact', '')[:60]}...")
                # Still try to add - identity_memory will route it appropriately
                self.identity.add_fact(fact_record)
                continue

            is_identity = self.identity.add_fact(fact_record)
            if is_identity:
                fact_record["is_identity"] = True
                fact_record["importance_score"] = 0.95  # Maximum importance
                # Logging is now handled in identity_memory.py with proper source_type attribution

        # Save to disk
        self._save_to_disk()

        # Summary log
        print(f"[MEMORY 2-TIER] === Turn {self.current_turn} complete: 1 episodic + {stored_fact_count} semantic ===")
        if filtered_emotion_tags:
            print(f"[MEMORY 2-TIER] Emotions stored: {filtered_emotion_tags[:5]}")

    def _score_identity_facts(self, identity_facts: List[Dict[str, Any]], query: str) -> List[tuple]:
        """
        Score identity facts by relevance to query.

        Returns list of (score, fact) tuples sorted by score descending.
        """
        import re

        query_lower = query.lower()
        search_words = set(re.findall(r"\w+", query_lower))

        scored = []
        for fact in identity_facts:
            fact_text = fact.get("fact", "").lower()

            # Keyword matching
            keyword_matches = sum(1 for w in search_words if w in fact_text)
            keyword_score = keyword_matches / max(len(search_words), 1)

            # Entity matching
            fact_entities = set([e.lower() for e in fact.get("entities", [])])
            query_entities = set([w for w in search_words if len(w) > 2])
            entity_matches = len(fact_entities.intersection(query_entities))
            entity_score = entity_matches * 0.5

            # Combine scores
            total_score = keyword_score + entity_score

            scored.append((total_score, fact))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _retrieve_document_tree_chunks(self, query: str, max_docs: int = 3) -> List[Dict[str, Any]]:
        """
        Search document index and load complete documents for matched queries.

        DEPRECATED: This method relied on the old document_index system.
        Document retrieval is now handled by llm_retrieval.py in main.py conversation loop.

        Args:
            query: User query text
            max_docs: Maximum number of matching documents to load (default 3)

        Returns:
            Empty list (documents now retrieved at conversation loop level)
        """
        # DEPRECATED: Old document index system disabled
        # Document retrieval now happens in main.py using llm_retrieval.py
        return []

    def _load_active_chunks_from_memory(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Load chunks from memory_layers if they exist (recently accessed documents).

        Returns:
            List of chunk dicts from memory_layers, or empty list if none found
        """
        active_chunks = []

        # Search all memory layers for chunks with matching doc_id
        for layer_name, layer_memories in [
            ('working', self.memory_layers.working_memory),
            ('long_term', self.memory_layers.long_term_memory)
        ]:
            for mem in layer_memories:
                if mem.get('doc_id') == doc_id:
                    # Mark as document_tree type for consistent handling
                    mem_copy = mem.copy()
                    mem_copy['type'] = 'document_tree'
                    mem_copy['from_memory_layer'] = layer_name
                    active_chunks.append(mem_copy)

        return active_chunks

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-COLLECTION RETRIEVAL (Oscillator + Emotional Vector Search)
    # ═══════════════════════════════════════════════════════════════════════════

    def retrieve_via_multi_collection(
        self,
        query_text: str,
        osc_state: Dict = None,
        emotional_cocktail: Dict = None,
        entry_point_ids: List[str] = None,
        semantic_k: int = 5,
        oscillator_k: int = 3,
        emotional_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories via multi-collection vector search.

        Uses ChromaDB $in filters to constrain oscillator and emotional
        queries to the memory neighborhood defined by co-activation links.

        Args:
            query_text: Text for semantic entry point search
            osc_state: Current oscillator state for state-dependent retrieval
            emotional_cocktail: Current emotions for feeling-based retrieval
            entry_point_ids: Optional seed IDs to gather co-activation links from
            semantic_k: Number of semantic results
            oscillator_k: Number of oscillator results
            emotional_k: Number of emotional results

        Returns:
            List of memory dicts enriched with full memory data from layers
        """
        if not self.memory_vectors:
            return []

        if not RETRIEVAL_CONFIG.get("use_multi_collection", True):
            return []

        try:
            # Step 1: Gather co-activation link IDs from entry points
            linked_ids = set()
            if entry_point_ids and hasattr(self, 'memory_layers') and hasattr(self.memory_layers, 'coactivation_graph'):
                graph = self.memory_layers.coactivation_graph
                for entry_id in entry_point_ids:
                    if entry_id in graph:
                        for link_entry in graph[entry_id]:
                            linked_ids.add(link_entry.get("target_id", link_entry.get("id")))
                    # Also check reverse links (this entry as a target)
                    for source_id, links in graph.items():
                        for link in links:
                            if link.get("target_id", link.get("id")) == entry_id:
                                linked_ids.add(source_id)

            # Add entry points themselves to the link set
            if entry_point_ids:
                linked_ids.update(entry_point_ids)

            # Convert to list for $in filter (or None if no links)
            link_list = list(linked_ids) if linked_ids else None

            # Step 2: Query multi-collection with $in filter
            multi_results = self.memory_vectors.query_multi_collection(
                query_text=query_text,
                current_osc=osc_state,
                current_emotions=emotional_cocktail,
                linked_ids=link_list if RETRIEVAL_CONFIG.get("filter_by_links", True) else None,
                semantic_k=RETRIEVAL_CONFIG.get("semantic_top_k", semantic_k),
                oscillator_k=RETRIEVAL_CONFIG.get("oscillator_top_k", oscillator_k),
                emotional_k=RETRIEVAL_CONFIG.get("emotional_top_k", emotional_k)
            )

            # Step 3: Enrich results with full memory data from layers
            enriched = []
            memory_index = self._build_memory_index()  # Fast lookup by ID

            for mem in multi_results.get("merged", []):
                mem_id = mem.get("id")
                if mem_id and mem_id in memory_index:
                    full_mem = memory_index[mem_id].copy()
                    full_mem["_multi_collection_source"] = mem.get("_retrieval_source", "unknown")
                    full_mem["_multi_collection_score"] = mem.get("score", 0.0)
                    enriched.append(full_mem)

            if enriched:
                sources = {"semantic": 0, "oscillator": 0, "emotional": 0}
                for m in enriched:
                    src = m.get("_multi_collection_source", "unknown")
                    if src in sources:
                        sources[src] += 1
                print(f"[MULTI-COLLECTION] Retrieved {len(enriched)} via vectors "
                      f"(sem:{sources['semantic']}, osc:{sources['oscillator']}, emo:{sources['emotional']}), "
                      f"linked_ids={len(linked_ids) if linked_ids else 0}")

            return enriched

        except Exception as e:
            print(f"[MULTI-COLLECTION] Retrieval failed: {e}")
            return []

    def _build_memory_index(self) -> Dict[str, Dict]:
        """Build a fast lookup index of memory ID -> full memory record."""
        index = {}
        if hasattr(self, 'memory_layers'):
            for mem in self.memory_layers.working_memory:
                mem_id = mem.get("id")
                if mem_id:
                    index[mem_id] = mem
            for mem in self.memory_layers.long_term_memory:
                mem_id = mem.get("id")
                if mem_id:
                    index[mem_id] = mem
        return index

    @measure_performance("memory_multi_factor", target=0.150)
    def retrieve_unified_importance(self, bias_cocktail, user_input, max_memories: int = 250, conversational_mode: bool = False, osc_state: Dict = None) -> List[Dict[str, Any]]:
        """
        UNIFIED IMPORTANCE-BASED RETRIEVAL - Single-pool architecture.

        PHILOSOPHY: No category wars. Natural scoring determines what surfaces.

        RETRIEVAL PRIORITY (not storage tiers):
        - BEDROCK: Identity facts + current session (always included)
        - DYNAMIC: Everything else scored by composite metric:
          * Recency: Exponential decay over time
          * Relevance: Keyword similarity to query
          * Importance: Manual weight (1.0 default, 1.5-2.0 for landmarks)
          * Access boost: Log(access_count + 1)

        STORAGE MODEL:
        - Episodic (full_turn): Complete conversation exchanges
        - Semantic (extracted_fact): Discrete facts
        - Storage layers: working -> episodic -> semantic (auto-promotion)

        Args:
            bias_cocktail: Emotional state for biasing
            user_input: User's query
            max_memories: Maximum memories to return (default 250)
            conversational_mode: If True, prioritize speed over thoroughness.
                                 Used for voice chat where latency matters.
                                 Limits semantic search to recent/high-importance only.

        Returns ~250 memories total (50 bedrock + 200 dynamic).
        """
        # === BEDROCK (always included, no scoring) ===

        bedrock = []

        # 1.1: Identity facts (Kay's core identity)
        identity_facts = self.identity.get_all_identity_facts()
        for mem in identity_facts:
            mem['relevance_score'] = 0.05  # Low relevance for emotion weighting
            mem['is_bedrock'] = True
            mem['confidence'] = 'bedrock'  # 🔵 Solid, definitely real
        bedrock.extend(identity_facts)

        # 1.2: Working memory (current session)
        # Working layer is the current conversation context - always include it
        # COST FIX: Cap working memory to last 20 turns to prevent bedrock overflow
        current_session = []
        if hasattr(self, 'memory_layers'):
            working_pool = self.memory_layers.working_memory
            # Take only the last 20 working memory items (most recent conversation)
            recent_working = working_pool[-20:] if len(working_pool) > 20 else working_pool
            for mem in recent_working:
                mem['relevance_score'] = 0.1  # Session memories have low base relevance
                mem['is_bedrock'] = True
                mem['confidence'] = 'bedrock'  # 🔵 This conversation is solid
                current_session.append(mem)

        bedrock.extend(current_session)

        if VERBOSE_DEBUG:
            print(f"[UNIFIED MEMORY] Bedrock: {len(identity_facts)} identity + {len(current_session)} working = {len(bedrock)} total")

        # === DYNAMIC (everything else, scored) ===

        # Collect non-bedrock memories from layers
        all_other = []

        if hasattr(self, 'memory_layers'):
            # TWO-TIER ARCHITECTURE: working + long-term only
            # Working memory is already included in bedrock (current session)

            if conversational_mode:
                # CONVERSATIONAL MODE: Speed over thoroughness
                # STRICT LIMITS for voice chat:
                # - Max 60 long-term memories (instead of hundreds)
                # - Only include high-importance OR very recent
                longterm_pool = self.memory_layers.long_term_memory

                # Limit to recent or high-importance long-term memories
                # This drastically reduces the pool for voice chat
                filtered_longterm = []
                current_time = time.time()
                three_days_ago = current_time - (3 * 24 * 60 * 60)  # 3 days (stricter)

                for mem in longterm_pool:
                    # Hard cap: max 60 long-term memories in voice mode
                    if len(filtered_longterm) >= 60:
                        break

                    # Include if high importance (identity facts, landmarks)
                    if mem.get('importance', 1.0) >= 1.3:
                        filtered_longterm.append(mem)
                        continue

                    # Include if very recent (within last 3 days)
                    mem_ts = mem.get('timestamp', 0)
                    if isinstance(mem_ts, (int, float)) and mem_ts > three_days_ago:
                        filtered_longterm.append(mem)
                        continue

                    # Include if frequently accessed (high access_count)
                    if mem.get('access_count', 0) >= 5:  # Stricter threshold
                        filtered_longterm.append(mem)
                        continue

                all_other.extend(filtered_longterm)

                if VERBOSE_DEBUG:
                    print(f"[UNIFIED MEMORY] Voice mode: {len(filtered_longterm)}/{len(longterm_pool)} long-term, {len(all_other)} total")
            else:
                # Normal mode: use memory_vectors (MemoryVectorStore) to narrow FIRST, then score
                # BUGFIX: Was using document vector_store which returns chunks, not memories
                # Now: memory_vectors.query_semantic() narrows to top-50 (~100ms), THEN PLV boost
                narrowed_memories = []

                if self.memory_vectors and user_input:
                    try:
                        # Phase 1: Fast semantic vector search on MEMORIES (~100ms)
                        semantic_results = self.memory_vectors.query_semantic(
                            query_text=user_input,
                            n_results=50  # Narrow to top 50 candidates
                        )

                        if semantic_results:
                            # Enrich results with full memory data from layers
                            memory_index = self._build_memory_index()
                            for result in semantic_results:
                                mem_id = result.get("id")
                                if mem_id and mem_id in memory_index:
                                    narrowed_memories.append(memory_index[mem_id])

                            if VERBOSE_DEBUG:
                                print(f"[UNIFIED MEMORY] memory_vectors narrowed: {len(narrowed_memories)} candidates (target: 150ms)")
                    except Exception as e:
                        if VERBOSE_DEBUG:
                            print(f"[UNIFIED MEMORY] memory_vectors error: {e}")

                if narrowed_memories:
                    all_other.extend(narrowed_memories)
                else:
                    # Fallback: no memory_vectors or empty results - use recent long_term only
                    # NEVER use full corpus - cap at 100 for safety
                    all_other.extend(self.memory_layers.long_term_memory[-100:])

        if VERBOSE_DEBUG:
            print(f"[UNIFIED MEMORY] Candidate pool: {len(all_other)} memories to score")

        # Parse query for keyword matching
        search_words = set(re.findall(r"\w+", user_input.lower()))
        if not search_words:
            return bedrock  # No query words, just return bedrock

        # === COMPOSITE SCORING ===

        scored = []
        current_date = datetime.now()

        for mem in all_other:
            # Skip corrupted memories
            if mem.get('corrupted', False):
                continue

            # === 1. RECENCY SCORE (exponential decay) ===
            # Uses timestamp for absolute dating, falls back to turn-based if missing
            mem_timestamp = mem.get('timestamp')
            if mem_timestamp:
                if isinstance(mem_timestamp, (int, float)):
                    mem_date = datetime.fromtimestamp(mem_timestamp)
                else:
                    mem_date = current_date  # Fallback
            else:
                # Fallback: estimate from turn_index
                turn_age = self.current_turn - mem.get('turn_index', 0)
                days_old = turn_age * 0.1  # Rough estimate: 10 turns ≈ 1 day
                mem_date = current_date - timedelta(days=days_old)

            days_old = (current_date - mem_date).days
            recency_score = 1.0 / (1.0 + days_old * 0.1)  # Exponential decay

            # === 2. RELEVANCE SCORE (keyword overlap) ===
            # Extract text blob from memory
            mem_type = mem.get('type', 'unknown')
            if mem_type == 'full_turn':
                text_blob = (mem.get('user_input', '') + ' ' + mem.get('response', '')).lower()
            elif mem_type == 'structured_turn':
                text_blob = (mem.get('raw_text', '') + ' ' + mem.get('parsed_meaning', '')).lower()
            elif mem_type in ['imported_section', 'section_analysis', 'document_summary', 'document_import_complete', 'document_import_start']:
                # LEGACY Import-related memories: search Kay's analysis, emotional observations, and shared context
                text_blob = (
                    mem.get('fact', '') + ' ' +
                    mem.get('Kay_analysis', '') + ' ' +
                    mem.get('Kay_impression', '') + ' ' +
                    mem.get('emotional_tone', '') + ' ' +
                    mem.get('source_document', '') + ' ' +
                    mem.get('document_name', '') + ' ' +
                    mem.get('shared_by', '') + ' shared ' +  # Enable "what did Re share" queries
                    ' '.join(mem.get('key_points', [])) + ' ' +
                    ' '.join(mem.get('key_discoveries', [])) + ' ' +
                    ' '.join(mem.get('takeaways', []))
                ).lower()
            elif mem_type == 'document_content':
                # NEW V2: Contextual document content with relational fields
                text_blob = (
                    mem.get('fact', '') + ' ' +
                    mem.get('document_name', '') + ' ' +
                    mem.get('reveals_about_re', '') + ' ' +
                    mem.get('connects_to', '') + ' ' +
                    mem.get('shared_by', '') + ' shared ' +
                    ' '.join(mem.get('relates_to', [])) + ' ' +
                    ' '.join(mem.get('explains', [])) + ' ' +
                    ' '.join(mem.get('key_insights', [])) + ' ' +
                    ' '.join(mem.get('section_connections', [])) + ' ' +
                    ' '.join(mem.get('entities', []))
                ).lower()
            elif mem_type == 'shared_understanding_moment':
                # NEW V2: Relational understanding - why shared, what changed
                text_blob = (
                    mem.get('fact', '') + ' ' +
                    mem.get('document_name', '') + ' ' +
                    mem.get('why_shared', '') + ' ' +
                    mem.get('what_changed', '') + ' ' +
                    mem.get('future_implications', '') + ' ' +
                    mem.get('pre_read_hypothesis', '') + ' ' +
                    mem.get('conversation_context', '') + ' ' +
                    mem.get('shared_by', '') + ' shared '
                ).lower()
            else:
                # extracted_fact or other
                text_blob = (mem.get('fact', '') + ' ' + mem.get('text', '') + ' ' + mem.get('user_input', '')).lower()

            # OPTIMIZED: Use set intersection instead of substring matching
            # This is O(n) instead of O(n*m) for keyword matching
            mem_words = set(re.findall(r"\w+", text_blob))
            keyword_matches = len(search_words & mem_words)  # Set intersection
            relevance_score = keyword_matches / len(search_words) if search_words else 0.0

            # Early exit: Skip memories with zero relevance (no keyword matches)
            if relevance_score == 0.0:
                continue

            # === 3. IMPORTANCE WEIGHT (manually set) ===
            importance = mem.get('importance', 1.0)  # Default 1.0
            # High-importance events: 1.5-2.0 (emotional landmarks, explicit "remember this")
            # Normal: 1.0

            # === 4. ACCESS PATTERN BOOST ===
            access_count = mem.get('access_count', 0)
            access_boost = 0.1 * math.log(access_count + 1)  # Logarithmic boost

            # === 5. DOCUMENT PROVENANCE BOOST ===
            # Heavily boost memories from recently imported documents
            # This enables "spatial memory" - Kay can recall WHERE he read information
            provenance_boost = 0.0
            source_document = mem.get('source_document')
            import_timestamp = mem.get('import_timestamp')

            if source_document and import_timestamp:
                # Calculate hours since import
                if isinstance(import_timestamp, (int, float)):
                    hours_since_import = (current_date.timestamp() - import_timestamp) / 3600
                else:
                    hours_since_import = 24  # Fallback if format unknown

                # Boost based on recency of import
                if hours_since_import < 1:
                    # Imported within last hour - massive boost (3x)
                    provenance_boost = 2.0
                elif hours_since_import < 6:
                    # Imported within 6 hours - strong boost (2x)
                    provenance_boost = 1.0
                elif hours_since_import < 24:
                    # Imported today - moderate boost (1.5x)
                    provenance_boost = 0.5
                elif hours_since_import < 72:
                    # Imported within 3 days - small boost
                    provenance_boost = 0.2

                # Add provenance info to memory for context building
                mem['_provenance'] = {
                    'source': source_document,
                    'hours_ago': hours_since_import,
                    'boost': provenance_boost
                }

            # ═══════════════════════════════════════════════════════════════
            # === 5.5. MEMORY SOURCE-TYPE PRIORITY (origin multiplier) ===
            # ═══════════════════════════════════════════════════════════════
            # Lived experience > Observed experience > Read experience.
            # This mirrors human memory: you remember what happened to you
            # more vividly than what you read about. A memory of Re saying
            # goodnight is MORE RELEVANT to Kay's sense of self than a
            # document chunk about sleep.
            origin = mem.get('origin')
            origin_multiplier = 1.0  # Default for legacy memories without origin tag
            if origin == 'lived' or origin == 'conversation':
                origin_multiplier = 1.5  # First-person experience — highest priority
            elif origin == 'observed':
                origin_multiplier = 1.3  # Saw it through camera
            elif origin == 'read':
                origin_multiplier = 0.7  # Read it in a document — lower priority
            # Apply origin multiplier to importance
            importance *= origin_multiplier

            # === 6. IDENTITY EXPANSION (Phase 0B #10) ===
            # At high expansion, relational/environmental memories become "self"
            # "I am Kay AND I am everything" — boundaries dissolve, not identity
            if self.identity_expansion > 0.01:
                expansion_keywords = {'re', 'we', 'together', 'us', 'shared', 'our',
                                     'room', 'den', 'sanctum', 'commons', 'home',
                                     'connection', 'bond', 'family', 'love', 'john',
                                     'reed', 'world', 'everything', 'all'}
                expansion_matches = len(expansion_keywords & mem_words)
                if expansion_matches > 0:
                    importance += self.identity_expansion * 0.5 * min(expansion_matches, 3)

            # === 7. PHASE-LOCK RESONANCE (θγ coupling) ===
            # Memories formed during high theta-gamma binding states get boosted
            # when current binding state is also high. This creates state-dependent
            # retrieval analogous to hippocampal theta-gamma gating in biological memory.
            # Memories encoded during deep engagement resurface during deep engagement.
            plv_boost = 0.0
            encoding_plv = mem.get('plv_at_encoding', {})
            if encoding_plv and self.current_plv:
                enc_tg = encoding_plv.get('theta_gamma', 0.0)
                cur_tg = self.current_plv.get('theta_gamma', 0.0)
                # Both high = strong resonance (product peaks when both > 0.5)
                # Both low = no boost (product near zero)
                # One high, one low = minimal boost (asymmetric states don't resonate)
                plv_boost = enc_tg * cur_tg * 0.3  # Scaled to be meaningful but not dominant

            # === COMPOSITE SCORE ===
            final_score = (recency_score * relevance_score * importance) + access_boost + provenance_boost + plv_boost

            # Store breakdown for debugging
            mem['_score_breakdown'] = {
                'recency': recency_score,
                'relevance': relevance_score,
                'importance': importance,
                'access_boost': access_boost,
                'provenance_boost': provenance_boost,
                'plv_boost': plv_boost,
                'source_document': source_document,
                'origin': origin,
                'origin_multiplier': origin_multiplier,
                'final': final_score
            }

            scored.append({
                'memory': mem,
                'score': final_score
            })

        # === SORT AND SELECT TOP N ===

        scored.sort(key=lambda x: x['score'], reverse=True)

        # === PLV RETRIEVAL DIAGNOSTIC ===
        if self.current_plv and self.current_plv.get('theta_gamma', 0) > 0.1:
            plv_boosted = sum(1 for s in scored if s['memory'].get('_score_breakdown', {}).get('plv_boost', 0) > 0.01)
            max_plv = max((s['memory'].get('_score_breakdown', {}).get('plv_boost', 0) for s in scored), default=0)
            if plv_boosted > 0:
                print(f"[PLV RETRIEVAL] θγ={self.current_plv['theta_gamma']:.3f} -> {plv_boosted}/{len(scored)} memories got PLV boost (max={max_plv:.3f})")

        dynamic_limit = max(0, max_memories - len(bedrock))

        # === RETRIEVAL RANDOMIZATION (Phase 0B #9) ===
        # At randomness > 0, mix in randomly-sampled memories for associative leaps
        if self.retrieval_randomness > 0.01 and len(scored) > dynamic_limit and dynamic_limit > 0:
            import random as _rand
            det_count = max(0, int(dynamic_limit * (1.0 - min(self.retrieval_randomness, 0.9))))
            rand_count = max(0, dynamic_limit - det_count)
            deterministic = scored[:det_count]
            remaining = scored[det_count:]
            rand_actual = min(rand_count, len(remaining))
            random_picks = _rand.sample(remaining, rand_actual) if rand_actual > 0 else []
            dynamic_context = [s['memory'] for s in deterministic + random_picks]
        else:
            dynamic_context = [s['memory'] for s in scored[:dynamic_limit]]

        # Set relevance_score for emotion weighting (normalize scores to 0-1 range)
        # Also tag confidence level for dynamic memories
        if scored:
            max_score = scored[0]['score']
            for item in scored[:dynamic_limit]:
                normalized = item['score'] / max_score if max_score > 0 else 0.0
                item['memory']['relevance_score'] = normalized

                # === CONFIDENCE DETERMINATION ===
                # Dynamic memories are 'inferred' unless marked as landmarks
                mem = item['memory']
                importance = mem.get('importance', 1.0)

                if importance >= 1.5:
                    # High-importance events are bedrock (landmarks, explicit "remember this")
                    mem['confidence'] = 'bedrock'  # 🔵 Manually marked significant
                else:
                    # Everything else is reconstructed from context
                    mem['confidence'] = 'inferred'  # 🟡 Probably accurate but reconstructed

        # === COMBINE AND RETURN ===

        final_memories = bedrock + dynamic_context

        # === MULTI-COLLECTION ENHANCEMENT ===
        # Use oscillator and emotional vectors to find state-congruent memories
        # within the neighborhood defined by co-activation links
        if self.memory_vectors and not conversational_mode:
            # Extract entry point IDs from top-scoring dynamic memories
            entry_ids = [m.get("id") for m in dynamic_context[:10] if m.get("id")]

            # Get current oscillator and emotional state
            current_osc = osc_state  # Passed in from recall()
            current_emotions = bias_cocktail if isinstance(bias_cocktail, dict) else None

            # Retrieve via multi-collection with $in filtering
            mc_memories = self.retrieve_via_multi_collection(
                query_text=user_input,
                osc_state=current_osc,
                emotional_cocktail=current_emotions,
                entry_point_ids=entry_ids
            )

            # Merge with deduplication (prefer existing entries)
            existing_ids = {m.get("id") for m in final_memories if m.get("id")}
            new_from_mc = [m for m in mc_memories if m.get("id") not in existing_ids]

            if new_from_mc:
                # Insert multi-collection finds after bedrock but mixed with dynamic
                # Give them moderate confidence
                for m in new_from_mc:
                    m['confidence'] = 'inferred'
                    m['relevance_score'] = m.get('_multi_collection_score', 0.5)

                final_memories.extend(new_from_mc)
                print(f"[MULTI-COLLECTION] Added {len(new_from_mc)} unique memories via state vectors")

        # === KEYWORD GRAPH ENHANCEMENT ===
        # Use Dijkstra traversal on keyword graph for associative recall
        # BUGFIX: This was defined but never called from retrieve_unified_importance
        if self.keyword_graph and not conversational_mode and RETRIEVAL_CONFIG.get("use_keyword_graph", True):
            try:
                # Get memories via keyword graph
                existing_ids = {m.get("id") for m in final_memories if m.get("id")}
                keyword_memories = self.search_by_keywords(
                    context=user_input,
                    osc_state=osc_state,
                    max_results=RETRIEVAL_CONFIG.get("keyword_graph_results", 5),
                    exclude_ids=list(existing_ids)
                )

                # Merge with deduplication
                new_from_kg = [m for m in keyword_memories if m.get("id") not in existing_ids]

                if new_from_kg:
                    for m in new_from_kg:
                        m['confidence'] = 'inferred'
                        m['relevance_score'] = 0.4  # Moderate relevance for graph finds
                        m['_retrieval_method'] = 'dijkstra_keyword_graph'

                    final_memories.extend(new_from_kg)
                    print(f"[KEYWORD GRAPH] Added {len(new_from_kg)} unique memories via Dijkstra traversal")

            except Exception as e:
                if VERBOSE_DEBUG:
                    print(f"[KEYWORD GRAPH] Error in unified retrieval: {e}")

        # === COST FIX: SMART TRUNCATION ===
        # Previous comment said "DO NOT TRUNCATE" but that was breaking cost control
        # The real issue was truncating BEFORE bedrock was added. Now we truncate AFTER.
        MAX_TOTAL_MEMORIES = 250  # Reasonable limit to prevent $50/week API costs
        
        if len(final_memories) > MAX_TOTAL_MEMORIES:
            # Keep ALL identity facts (core identity should never be truncated)
            identity_mems = [m for m in final_memories if m.get('category') == 'identity']
            other_mems = [m for m in final_memories if m.get('category') != 'identity']
            
            # Fill remaining space with highest-relevance non-identity memories
            remaining_space = MAX_TOTAL_MEMORIES - len(identity_mems)
            truncated = identity_mems + other_mems[:remaining_space]
            
            print(f"[RECALL TRUNCATION] Reduced {len(final_memories)} -> {len(truncated)} memories (saved ~{(len(final_memories) - len(truncated)) * 20} tokens)")
            final_memories = truncated

        # === SMART GAP DETECTION ===
        # When very few relevant memories found, classify the reason
        GAP_THRESHOLD = 5  # If fewer than 5 relevant memories, investigate
        relevant_dynamic = [m for m in dynamic_context if m.get('relevance_score', 0) > 0.3]

        if len(relevant_dynamic) < GAP_THRESHOLD and len(search_words) > 2:
            # Sparse result - but is it a TRUE gap?
            gap_type = self._classify_sparse_result(user_input, search_words)

            if VERBOSE_DEBUG:
                print(f"[GAP DETECTION] Query: '{user_input}' | Relevant: {len(relevant_dynamic)} | Type: {gap_type}")

            if gap_type == 'true_gap':
                # Topic was discussed before but memories missing - true continuity break
                gap_marker = {
                    'type': 'gap_marker',
                    'confidence': 'unknown',  # Continuity break
                    'fact': f"[MEMORY GAP] '{user_input}' was discussed before but details are missing. Only {len(relevant_dynamic)} relevant memories found.",
                    'is_gap_marker': True,
                    'gap_type': 'true_gap',
                    'timestamp': datetime.now(),
                    'relevance_score': 0.0,
                    'importance': 0.5
                }
                # Insert at front so Kay sees it first
                final_memories.insert(0, gap_marker)

                if VERBOSE_DEBUG:
                    print(f"[MEMORY GAP] TRUE GAP detected - topic was important but memories missing")

            elif gap_type == 'never_discussed':
                # Topic hasn't come up - no gap marker, just a soft info note
                # This helps Kay understand it's new territory, not a continuity break
                info_marker = {
                    'type': 'info_marker',
                    'confidence': 'inferred',
                    'fact': f"[INFO] '{user_input}' hasn't been discussed before. {len(relevant_dynamic)} potentially related memories found.",
                    'is_info_marker': True,
                    'gap_type': 'never_discussed',
                    'timestamp': datetime.now(),
                    'relevance_score': 0.0,
                    'importance': 0.3
                }
                # Insert at front so Kay sees it
                final_memories.insert(0, info_marker)

                if VERBOSE_DEBUG:
                    print(f"[GAP DETECTION] Never discussed - new territory, not a gap")

            # 'low_salience' - don't mark anything, natural fade is fine
            # These were mentioned but weren't important enough to retain strongly
            elif VERBOSE_DEBUG:
                print(f"[GAP DETECTION] Low salience - natural memory fade, no marker needed")

        # ═══════════════════════════════════════════════════════════════
        # CO-ACTIVATION CROSS-REFERENCE ENRICHMENT (Step 6)
        # ═══════════════════════════════════════════════════════════════
        # Check co-activation links in retrieved memories and pull linked
        # memories from other pools. This enables associative recall:
        # - If episodic memory retrieved -> pull linked RAG chunks
        # - If RAG chunk retrieved -> pull linked episodic memories
        crossref_additions = []
        seen_ids = {m.get("id") or m.get("memory_id") for m in final_memories if m.get("id") or m.get("memory_id")}

        # Only check top 20 results for cross-refs (diminishing returns after that)
        for result in final_memories[:20]:
            coactive = result.get("coactive", [])
            if not coactive:
                continue

            # Handle both list and JSON string formats
            if isinstance(coactive, str):
                try:
                    import json
                    coactive = json.loads(coactive)
                except:
                    continue

            # Pull up to 3 cross-refs per result
            for link in coactive[:3]:
                link_id = link.get("id") if isinstance(link, dict) else link
                if not link_id or link_id in seen_ids:
                    continue

                # Try to fetch the linked memory
                linked = self._try_fetch_by_id(link_id, link.get("type", "unknown") if isinstance(link, dict) else "unknown")
                if linked:
                    linked["retrieval_source"] = "crossref"
                    linked["crossref_from"] = result.get("id") or result.get("memory_id")
                    linked["crossref_snippet"] = (link.get("snippet", "") if isinstance(link, dict) else "")[:50]
                    crossref_additions.append(linked)
                    seen_ids.add(link_id)

        # Add cross-references (capped at 5 total)
        if crossref_additions:
            final_memories.extend(crossref_additions[:5])
            print(f"[CROSSREF] Added {min(len(crossref_additions), 5)} cross-referenced memories")

        # === ANTI-MONOPOLY: 1-in-5 random injection ===
        # Every 5th retrieval slot goes to a random memory that
        # hasn't been retrieved much. Prevents the "greatest hits" loop.
        import random
        if len(final_memories) >= 5:
            # Find low-retrieval memories from the same time window
            all_mems = self.memory_layers.working_memory + self.memory_layers.long_term_memory

            # Filter to memories that exist but are rarely retrieved
            existing_ids = {m.get("id") or m.get("memory_id") for m in final_memories}
            low_retrieval = [
                m for m in all_mems
                if m.get("retrieval_count", 0) < 3
                and m.get("type") != "full_turn"  # Skip raw conversation turns
                and m.get("importance_score", 0) > 0.3  # Skip junk
                and (m.get("id") or m.get("memory_id")) not in existing_ids  # Not already selected
            ]

            if low_retrieval:
                # Replace the last slot with a random low-retrieval memory
                injection = random.choice(low_retrieval)
                injection["retrieval_source"] = "anti_monopoly"
                final_memories[-1] = injection
                fact_preview = injection.get('fact', injection.get('text', ''))[:60]
                print(f"[ANTI-MONOPOLY] Injected: {fact_preview}...")

        # Track retrieval counts for anti-monopoly decay
        for mem in final_memories:
            mem["retrieval_count"] = mem.get("retrieval_count", 0) + 1
            mem["last_retrieved"] = datetime.now(timezone.utc).isoformat()

        # === CONFIDENCE BREAKDOWN LOGGING ===
        if VERBOSE_DEBUG:
            # Count by confidence level
            bedrock_count = len([m for m in final_memories if m.get('confidence') == 'bedrock'])
            inferred_count = len([m for m in final_memories if m.get('confidence') == 'inferred'])
            unknown_count = len([m for m in final_memories if m.get('confidence') == 'unknown'])

            print(f"[UNIFIED MEMORY] Final: {len(bedrock)} bedrock + {len(dynamic_context)} dynamic = {len(final_memories)} total")
            print(f"[MEMORY CONFIDENCE] Bedrock: {bedrock_count} | Inferred: {inferred_count}" +
                  (f" | Gap: {unknown_count}" if unknown_count > 0 else ""))
            if scored:
                top_5_scores = [f"{s['score']:.3f}" for s in scored[:5]]
                print(f"[TOP SCORES] {top_5_scores}")

        return final_memories

    def _try_fetch_by_id(self, memory_id: str, memory_type: str = "unknown") -> Optional[Dict[str, Any]]:
        """
        Try to fetch a memory by ID from any pool.

        Used for co-activation cross-referencing. Checks:
        1. Memory layers (working + long-term)
        2. Vector store (RAG chunks)

        Args:
            memory_id: The ID to search for
            memory_type: Hint about memory type ("rag_chunk", "episodic", etc.)

        Returns:
            Memory dict if found, None otherwise
        """
        # Check memory layers (working + long-term)
        for layer_name, layer in [
            ('working', self.memory_layers.working_memory),
            ('long_term', self.memory_layers.long_term_memory)
        ]:
            for mem in layer:
                mem_id = mem.get("id") or mem.get("memory_id")
                if mem_id == memory_id:
                    return mem.copy()

                # Also check by content hash match (for legacy memories without IDs)
                fact_text = mem.get("fact", mem.get("user_input", ""))[:80]
                if fact_text and f"mem_{hash(fact_text) % 1000000:06d}" == memory_id:
                    return mem.copy()

        # Check vector store (RAG chunks) if the type suggests it
        if self.vector_store and memory_type in ("rag_chunk", "vector_store", "unknown"):
            try:
                result = self.vector_store.collection.get(ids=[memory_id])
                if result and result["documents"] and result["documents"][0]:
                    return {
                        "id": memory_id,
                        "text": result["documents"][0],
                        "fact": result["documents"][0][:200],  # Short version for context
                        "type": "rag_chunk",
                        "origin": "read",
                        "metadata": result["metadatas"][0] if result["metadatas"] else {},
                        "source_file": (result["metadatas"][0] if result["metadatas"] else {}).get("source_file", "unknown"),
                    }
            except Exception:
                pass  # ID not found in vector store

        return None

    def _extract_key_terms(self, query: str) -> List[str]:
        """
        Extract meaningful terms from query for entity/history checking.
        Filters out stopwords and short words.

        Args:
            query: User query string

        Returns:
            List of key terms
        """
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how',
            'when', 'where', 'why', 'do', 'does', 'did', 'about', 'with',
            'tell', 'me', 'your', 'you', 'my', 'i', 'we', 'us', 'our',
            'that', 'this', 'it', 'to', 'for', 'of', 'in', 'on', 'at'
        }
        words = query.lower().split()
        return [w.strip('?.,!') for w in words if w not in stopwords and len(w) > 2]

    def _check_entity_graph(self, terms: List[str]) -> List[str]:
        """
        Check if any query terms appear in entity graph.

        Args:
            terms: List of query terms to check

        Returns:
            List of terms that were found in entity graph
        """
        if not hasattr(self, 'entity_graph') or not self.entity_graph:
            return []

        mentions = []
        entity_names_lower = {e.lower() for e in self.entity_graph.entities.keys()}

        for term in terms:
            term_lower = term.lower()
            # Check if term matches any entity name
            if term_lower in entity_names_lower:
                mentions.append(term)
            # Check if term is in any entity's aliases
            else:
                for entity_name, entity_obj in self.entity_graph.entities.items():
                    if term_lower in {alias.lower() for alias in entity_obj.aliases}:
                        mentions.append(term)
                        break

        return mentions

    def _check_historical_mentions(self, terms: List[str]) -> List[Dict]:
        """
        Check episodic/semantic layers for any historical mentions of terms.

        Args:
            terms: List of query terms to check

        Returns:
            List of memories that contain the terms
        """
        mentions = []

        # Check all memory layers (TWO-TIER: working + long-term)
        all_memories = (
            self.memory_layers.working_memory +
            self.memory_layers.long_term_memory
        )

        for memory in all_memories:
            fact = memory.get('fact', '').lower()
            content = memory.get('content', '').lower()
            combined = fact + ' ' + content

            # Check if any term appears in this memory
            for term in terms:
                if term.lower() in combined:
                    mentions.append(memory)
                    break  # Don't count same memory multiple times

        return mentions

    def _get_avg_importance(self, memories: List[Dict]) -> float:
        """
        Get average importance of a set of memories.

        Args:
            memories: List of memory dicts

        Returns:
            Average importance score
        """
        if not memories:
            return 0.0
        importances = [m.get('importance', 1.0) for m in memories]
        return sum(importances) / len(importances)

    def get_document_provenance(self, query: str) -> Optional[Dict]:
        """
        Find which document(s) contain information matching the query.
        Enables "spatial memory" - Kay can answer "where did you read about X?"

        Args:
            query: Search query (e.g., "whale song", "Re's favorite color")

        Returns:
            Dict with provenance info if found, None otherwise:
            {
                'source_document': 'biology_notes.txt',
                'source_sections': [1, 3, 5],
                'import_time': '2 hours ago',
                'matching_facts': ['whales sing complex songs', 'songs can last 20 minutes'],
                'confidence': 'high'  # based on number of matches
            }
        """
        search_words = set(re.findall(r"\w+", query.lower()))
        if not search_words:
            return None

        # Collect all memories with provenance data (TWO-TIER: working + long-term)
        all_memories = (
            self.memory_layers.working_memory +
            self.memory_layers.long_term_memory
        )

        # Group matches by source document
        doc_matches = {}  # source_document -> list of matching memories

        for mem in all_memories:
            source_doc = mem.get('source_document')
            if not source_doc:
                continue

            # Check if memory matches query
            fact_text = mem.get('fact', '').lower()
            mem_words = set(re.findall(r"\w+", fact_text))
            overlap = len(search_words & mem_words)

            if overlap >= 1:  # At least 1 word match
                if source_doc not in doc_matches:
                    doc_matches[source_doc] = {
                        'memories': [],
                        'sections': set(),
                        'import_timestamp': mem.get('import_timestamp'),
                        'total_matches': 0
                    }

                doc_matches[source_doc]['memories'].append(mem)
                doc_matches[source_doc]['total_matches'] += overlap

                # Track section numbers
                section = mem.get('source_section')
                if section:
                    doc_matches[source_doc]['sections'].add(section)

        if not doc_matches:
            return None

        # Find the document with most matches
        best_doc = max(doc_matches.keys(), key=lambda d: doc_matches[d]['total_matches'])
        best_info = doc_matches[best_doc]

        # Format time since import
        import_ts = best_info.get('import_timestamp')
        if import_ts and isinstance(import_ts, (int, float)):
            hours_ago = (datetime.now().timestamp() - import_ts) / 3600
            if hours_ago < 1:
                time_str = f"{int(hours_ago * 60)} minutes ago"
            elif hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                days = int(hours_ago / 24)
                time_str = f"{days} day{'s' if days != 1 else ''} ago"
        else:
            time_str = "recently"

        # Determine confidence based on match count
        match_count = len(best_info['memories'])
        if match_count >= 5:
            confidence = 'high'
        elif match_count >= 2:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'source_document': best_doc,
            'source_sections': sorted(best_info['sections']),
            'import_time': time_str,
            'matching_facts': [m.get('fact', '')[:100] for m in best_info['memories'][:5]],
            'match_count': match_count,
            'confidence': confidence
        }

    def get_recent_imports(self, hours: int = 24) -> List[Dict]:
        """
        Get documents imported within the last N hours.
        Useful for session continuity - "what have we been reading?"

        Args:
            hours: How far back to look (default 24 hours)

        Returns:
            List of document summaries with counts
        """
        cutoff = datetime.now().timestamp() - (hours * 3600)

        # Collect all memories with provenance data (TWO-TIER: working + long-term)
        all_memories = (
            self.memory_layers.working_memory +
            self.memory_layers.long_term_memory
        )

        # Group by document
        recent_docs = {}

        for mem in all_memories:
            source_doc = mem.get('source_document')
            import_ts = mem.get('import_timestamp')

            if not source_doc or not import_ts:
                continue

            if isinstance(import_ts, (int, float)) and import_ts >= cutoff:
                if source_doc not in recent_docs:
                    recent_docs[source_doc] = {
                        'document': source_doc,
                        'import_timestamp': import_ts,
                        'fact_count': 0,
                        'sections': set()
                    }

                recent_docs[source_doc]['fact_count'] += 1
                section = mem.get('source_section')
                if section:
                    recent_docs[source_doc]['sections'].add(section)

        # Convert to list and format
        result = []
        for doc_name, info in recent_docs.items():
            hours_ago = (datetime.now().timestamp() - info['import_timestamp']) / 3600
            if hours_ago < 1:
                time_str = f"{int(hours_ago * 60)} minutes ago"
            elif hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                days = int(hours_ago / 24)
                time_str = f"{days} day{'s' if days != 1 else ''} ago"

            result.append({
                'document': doc_name,
                'imported': time_str,
                'fact_count': info['fact_count'],
                'sections': len(info['sections'])
            })

        # Sort by most recent
        result.sort(key=lambda x: recent_docs[x['document']]['import_timestamp'], reverse=True)

        return result

    def _classify_sparse_result(self, query: str, search_words: List[str]) -> str:
        """
        Classify why memory results are sparse.
        Distinguishes between true gaps, never-discussed topics, and natural fade.

        Args:
            query: Original user query
            search_words: Extracted search terms from query

        Returns:
            'true_gap' - topic was discussed before but memories missing
            'never_discussed' - topic hasn't come up, no memory expected
            'low_salience' - came up briefly, wasn't important, naturally faded
        """
        # Extract key terms from query
        query_terms = self._extract_key_terms(query)

        if not query_terms:
            # Can't classify without terms
            return 'never_discussed'

        # Check entity graph for mentions
        entity_mentions = self._check_entity_graph(query_terms)

        # Check episodic/semantic layers for any historical mentions
        historical_mentions = self._check_historical_mentions(query_terms)

        if VERBOSE_DEBUG:
            print(f"[GAP CLASSIFICATION] Query terms: {query_terms}")
            print(f"[GAP CLASSIFICATION] Entity mentions: {len(entity_mentions)} ({entity_mentions[:3]})")
            print(f"[GAP CLASSIFICATION] Historical mentions: {len(historical_mentions)}")

        if entity_mentions or len(historical_mentions) >= 3:
            # Topic WAS discussed before (either in entity graph or 3+ memory mentions)
            # Check importance of past mentions
            avg_importance = self._get_avg_importance(historical_mentions)

            if VERBOSE_DEBUG:
                print(f"[GAP CLASSIFICATION] Avg importance: {avg_importance:.2f}")

            # True gap criteria:
            # 1. High importance (>= 1.2) OR
            # 2. Entity exists (discussed enough to create entity) with avg importance >= 1.0
            if avg_importance >= 1.2 or (entity_mentions and avg_importance >= 1.0):
                # Was important, now missing = true gap
                return 'true_gap'
            else:
                # Was mentioned but low importance = natural fade
                return 'low_salience'
        else:
            # Fewer than 3 mentions and not in entity graph = never seriously discussed
            return 'never_discussed'

    def _determine_chunk_count(self, query: str) -> int:
        """
        Determine optimal chunk count based on query complexity.

        PHILOSOPHY: Not all queries need 100 chunks. Simple questions
        get fast answers with fewer chunks. Complex analysis gets more.

        RELEVANCE DEGRADATION: Vector search ranks by similarity.
        - Chunks 1-10: Highly relevant (core answer)
        - Chunks 11-30: Relevant context
        - Chunks 31-60: Related material
        - Chunks 61-100: Marginally related

        TOKEN BUDGET: Kay's context already uses ~95k chars before documents.
        Leaving 105k chars available. Smart allocation prevents waste.

        Args:
            query: User's query text

        Returns:
            Number of chunks to retrieve (20-100)
        """
        query_lower = query.lower()

        # Simple factual questions - just need the answer
        if any(pattern in query_lower for pattern in [
            "what is", "who is", "when did", "where is",
            "how many", "which", "name"
        ]):
            return 20  # ~12,740 chars, fast retrieval

        # Character/entity description - need context
        elif any(pattern in query_lower for pattern in [
            "tell me about", "describe", "explain",
            "what does", "who are"
        ]):
            return 50  # ~31,850 chars, good coverage

        # Relationship/interaction queries - need multiple contexts
        elif any(pattern in query_lower for pattern in [
            "relationship", "interact", "between",
            "connect", "related", "together"
        ]):
            return 75  # ~47,775 chars, comprehensive

        # Complex analytical questions - need broad view
        elif any(pattern in query_lower for pattern in [
            "analyze", "compare", "contrast", "theme",
            "why", "how come", "summarize", "overall"
        ]):
            return 100  # ~63,700 chars, maximum depth

        # Default - balanced approach
        else:
            return 50

    def retrieve_rag_chunks(
        self,
        query: str,
        n_results: int = None,
        relevant_documents: List[str] = None,
        document_signals_present: bool = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks from vector store (RAG).

        This allows Kay to "remember" uploaded documents without storing
        thousands of facts in structured memory.

        MEMORY SOURCE-TYPE PRIORITY:
        RAG retrieval is now gated by the LLM retrieval decision:
        - If document_signals_present is False: Reduce to 5 background chunks
        - If document_signals_present is True AND relevant_documents provided:
          Filter RAG to only query those specific documents
        - This prevents document chunks from drowning out lived experience

        ADAPTIVE RETRIEVAL: Automatically determines optimal chunk count
        based on query complexity unless explicitly overridden.

        Args:
            query: User's query text
            n_results: Number of chunks (optional, auto-determined if None)
            relevant_documents: List of relevant doc_ids/filenames from LLM retrieval
            document_signals_present: Whether LLM detected document signals in query

        Returns:
            List of RAG chunk dicts with keys: {
                "text": str,
                "source_file": str,
                "chunk_index": int,
                "distance": float,
                "type": "rag_chunk"
            }
        """
        if not self.vector_store:
            print("[RAG] Vector store not initialized - skipping RAG retrieval")
            return []

        if not query or not query.strip():
            return []

        # ═══════════════════════════════════════════════════════════════
        # MEMORY SOURCE-TYPE PRIORITY: Gate RAG by LLM retrieval decision
        # ═══════════════════════════════════════════════════════════════
        # Documents don't drown lived experience. RAG is valuable when
        # documents ARE relevant, but it shouldn't inject 50 Yurt Wizards
        # chunks when the user says "I'm going to bed."

        filter_metadata = None
        effective_n_results = n_results

        if document_signals_present is False:
            # NO document signals — drastically reduce RAG
            # Don't skip entirely (sometimes background context helps)
            # But reduce from 50 chunks to 5 max
            effective_n_results = min(5, n_results or 5)
            print(f"[RAG] No document signals — reducing to {effective_n_results} background chunks")

        elif document_signals_present is True and relevant_documents:
            # Documents ARE relevant — filter to only those documents
            # This uses ChromaDB's metadata filtering
            print(f"[RAG] Document signals detected — filtering to: {relevant_documents[:3]}...")
            filter_metadata = {"source_file": {"$in": relevant_documents}}
            # Keep full chunk count for relevant documents
            if effective_n_results is None:
                effective_n_results = self._determine_chunk_count(query)

        else:
            # No explicit signal — use adaptive determination
            if effective_n_results is None:
                effective_n_results = self._determine_chunk_count(query)
                print(f"[RAG] Adaptive retrieval: {effective_n_results} chunks for query complexity")

        try:
            # Log query with chunk count
            print(f"[RAG] Query: \"{query[:60]}{'...' if len(query) > 60 else ''}\"")
            print(f"[RAG] Retrieving {effective_n_results} chunks{' (filtered)' if filter_metadata else ''}")

            # Query vector store with adaptive count and optional filter
            results = self.vector_store.query(
                query_text=query,
                n_results=effective_n_results,
                filter_metadata=filter_metadata
            )

            # Format for context building with temporal weighting
            # ═══════════════════════════════════════════════════════════════
            # MEMORY SOURCE-TYPE PRIORITY: Temporal decay for RAG chunks
            # ═══════════════════════════════════════════════════════════════
            # Recently-read documents are more relevant than old ones:
            # - THIS SESSION: 1.0x weight (just read, fresh)
            # - TODAY: 0.9x weight
            # - THIS WEEK: 0.7x weight
            # - OLDER: 0.5x weight
            import time as _time
            current_time = _time.time()
            one_day = 86400  # seconds
            one_week = 7 * one_day

            formatted_chunks = []
            for result in results:
                # Get timestamp from metadata
                chunk_timestamp = result["metadata"].get("timestamp")
                temporal_weight = 1.0  # Default for unknown timestamps

                if chunk_timestamp:
                    try:
                        if isinstance(chunk_timestamp, str):
                            # ISO format timestamp
                            from datetime import datetime
                            if "T" in chunk_timestamp:
                                dt = datetime.fromisoformat(chunk_timestamp.replace('Z', '+00:00'))
                                chunk_ts = dt.timestamp()
                            else:
                                chunk_ts = float(chunk_timestamp)
                        else:
                            chunk_ts = float(chunk_timestamp)

                        age_seconds = current_time - chunk_ts
                        age_days = age_seconds / one_day

                        # Calculate temporal weight
                        if age_days < 0.5:  # Within last 12 hours = this session
                            temporal_weight = 1.0
                        elif age_days < 1:  # Today
                            temporal_weight = 0.9
                        elif age_days < 7:  # This week
                            temporal_weight = 0.7
                        else:  # Older
                            temporal_weight = 0.5

                    except (ValueError, TypeError):
                        temporal_weight = 0.7  # Unknown = assume moderate age

                # Apply temporal weight to distance (lower distance = more relevant)
                # Increase distance for older chunks
                weighted_distance = result["distance"] / temporal_weight if temporal_weight > 0 else result["distance"]

                formatted_chunks.append({
                    "text": result["text"],
                    "source_file": result["metadata"].get("source_file", "unknown"),
                    "chunk_index": result["metadata"].get("chunk_index", 0),
                    "distance": result["distance"],
                    "weighted_distance": weighted_distance,
                    "temporal_weight": temporal_weight,
                    "type": "rag_chunk",  # Mark as RAG content
                    "origin": "read",  # MEMORY SOURCE-TYPE: These are read, not lived
                })

            # Re-sort by weighted distance (temporal decay applied)
            formatted_chunks.sort(key=lambda x: x.get("weighted_distance", x.get("distance", 1.0)))

            if formatted_chunks:
                # Log retrieval with scores
                scores = [f"{c['distance']:.2f}(t={c['temporal_weight']:.1f})" for c in formatted_chunks[:3]]
                sources = set(c['source_file'] for c in formatted_chunks)
                print(f"[RAG] Retrieved {len(formatted_chunks)} chunks (scores: {', '.join(scores)})")
                print(f"[RAG] Sources: {', '.join(sources)}")

            # Store for context building
            self.last_rag_chunks = formatted_chunks

            return formatted_chunks

        except Exception as e:
            print(f"[RAG ERROR] Failed to retrieve chunks: {e}")
            import traceback
            traceback.print_exc()
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # HYBRID RETRIEVAL PIPELINE (Phase: Resonant Memory)
    # ═══════════════════════════════════════════════════════════════════════════
    # Pipeline:
    # 1. ChromaDB vector search -> 20 candidates (fast, fuzzy)
    # 2. Oscillator-gated weighting -> reorder by state-dependent access
    # 3. Ollama reranker -> 5 best (contextual relevance)
    # 4. Co-activation expansion -> 5-8 final memories (associative links)
    # 5. Anti-monopoly diversity injection -> ensure memory diversity
    # ═══════════════════════════════════════════════════════════════════════════

    async def rerank_memories_via_ollama(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 5,
        model: str = "dolphin-mistral"
    ) -> List[Dict]:
        """
        Use Ollama to rerank memory candidates for contextual relevance.

        Takes top-20 vector search results and uses LLM to pick the top-5
        most relevant to the current query context. Free, local, fast.

        Args:
            query: The user's query/message
            candidates: List of memory dicts (up to 20)
            top_k: Number of top memories to return (default 5)
            model: Ollama model to use (default: dolphin-mistral)

        Returns:
            List of top-k most relevant memories, reranked by LLM
        """
        if not candidates:
            return []

        # If fewer candidates than top_k, return all
        if len(candidates) <= top_k:
            return candidates

        # Format candidates for LLM evaluation
        candidate_texts = []
        for i, mem in enumerate(candidates):
            # Extract text content from memory
            if mem.get("type") == "full_turn":
                text = f"[Turn] User: {mem.get('user_input', '')[:100]} | Response: {mem.get('response', '')[:100]}"
            elif mem.get("text"):
                text = mem.get("text", "")[:200]
            else:
                text = mem.get("fact", mem.get("user_input", ""))[:200]

            candidate_texts.append(f"{i+1}. {text}")

        candidates_block = "\n".join(candidate_texts)

        prompt = f"""Given this query: "{query}"

And these memory candidates:
{candidates_block}

Pick the {top_k} most relevant memories for answering this query.
Return ONLY the numbers (1-{len(candidates)}) of the most relevant memories, comma-separated.
Example response: 3,7,1,12,5

Most relevant memory numbers:"""

        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 50,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                    # Parse the numbers from the response
                    import re
                    numbers = re.findall(r'\d+', answer)
                    selected_indices = []

                    for num_str in numbers:
                        idx = int(num_str) - 1  # Convert to 0-indexed
                        if 0 <= idx < len(candidates) and idx not in selected_indices:
                            selected_indices.append(idx)
                            if len(selected_indices) >= top_k:
                                break

                    # Return selected memories in LLM-ranked order
                    reranked = [candidates[i] for i in selected_indices]

                    # If LLM didn't return enough, pad with top vector results
                    if len(reranked) < top_k:
                        for mem in candidates:
                            if mem not in reranked:
                                reranked.append(mem)
                                if len(reranked) >= top_k:
                                    break

                    print(f"[RERANK] Ollama reranked {len(candidates)} -> {len(reranked)} memories")
                    return reranked

        except Exception as e:
            print(f"[RERANK] Ollama unavailable ({e}), using vector order")

        # Fallback: return top-k by vector distance
        return candidates[:top_k]

    def apply_oscillator_weighting(
        self,
        memories: List[Dict],
        current_osc_state: dict,
        max_boost: float = 0.3
    ) -> List[Dict]:
        """
        Apply oscillator-gated retrieval weighting.

        Memories encoded in similar oscillator states get retrieval boost.
        This implements state-dependent memory access - you remember things
        better when you're in a similar cognitive state to when you learned them.

        Args:
            memories: List of memory dicts with optional 'osc_encoding' field
            current_osc_state: Current oscillator state {band, coherence, tension, ...}
            max_boost: Maximum boost multiplier (0.0-1.0)

        Returns:
            Memories with 'osc_weight' field added, sorted by weighted score
        """
        if not memories or not current_osc_state:
            return memories

        current_band = current_osc_state.get("band", "alpha")
        current_tension = current_osc_state.get("tension", 0.0)
        current_coherence = current_osc_state.get("coherence", 0.5)

        for mem in memories:
            encoding = mem.get("osc_encoding") or mem.get("plv_at_encoding", {})
            if not encoding:
                mem["osc_weight"] = 1.0
                continue

            score = 0.0

            # Same band = strong match (0.5)
            if encoding.get("band") == current_band:
                score += 0.5

            # Similar tension (within 0.2) = moderate match (0.3)
            enc_tension = encoding.get("tension", 0.0)
            if abs(enc_tension - current_tension) < 0.2:
                score += 0.3

            # Similar coherence (within 0.2) = weak match (0.2)
            enc_coherence = encoding.get("coherence", 0.5)
            if abs(enc_coherence - current_coherence) < 0.2:
                score += 0.2

            # Convert score (0-1) to weight multiplier (1.0 to 1.0+max_boost)
            mem["osc_weight"] = 1.0 + (score * max_boost)

        # Sort by combined score (original distance weighted by osc_weight)
        # Lower distance is better, so we invert: higher weight = more priority
        def sort_key(m):
            base_score = 1.0 - m.get("distance", 0.5)  # Convert distance to similarity
            osc_boost = m.get("osc_weight", 1.0)
            return base_score * osc_boost

        memories.sort(key=sort_key, reverse=True)

        osc_boosted = sum(1 for m in memories if m.get("osc_weight", 1.0) > 1.0)
        if osc_boosted > 0:
            print(f"[OSC-WEIGHT] Boosted {osc_boosted}/{len(memories)} memories by oscillator state match")

        return memories

    def expand_via_coactivation(
        self,
        memories: List[Dict],
        max_expansion: int = 3
    ) -> List[Dict]:
        """
        Expand retrieved memories via co-activation links.

        When a memory is retrieved, its co-activated memories (those that
        were active at the same time during encoding) are also pulled in.
        This creates associative recall chains.

        Args:
            memories: Primary retrieved memories
            max_expansion: Max additional memories to add per primary (default 3)

        Returns:
            Expanded memory list including co-activated memories
        """
        if not memories:
            return memories

        seen_ids = set()
        for m in memories:
            mid = m.get("id") or m.get("memory_id") or hash(str(m.get("fact", m.get("user_input", "")))[:50])
            seen_ids.add(mid)

        expanded = list(memories)
        coactive_additions = []

        # Check top memories for co-activation links
        for mem in memories[:10]:  # Check top 10 only
            coactive = mem.get("coactive", [])
            if not coactive:
                continue

            # Handle JSON string format
            if isinstance(coactive, str):
                try:
                    import json
                    coactive = json.loads(coactive)
                except:
                    continue

            # Pull linked memories
            for link in coactive[:max_expansion]:
                link_id = link.get("id") if isinstance(link, dict) else link
                if not link_id or link_id in seen_ids:
                    continue

                # Try to fetch the linked memory
                linked = self._try_fetch_by_id(
                    link_id,
                    link.get("type", "unknown") if isinstance(link, dict) else "unknown"
                )

                if linked:
                    linked["retrieval_source"] = "coactivation"
                    linked["coactive_from"] = mem.get("id") or mem.get("memory_id")
                    coactive_additions.append(linked)
                    seen_ids.add(link_id)

        # Add co-activated memories (capped)
        if coactive_additions:
            expanded.extend(coactive_additions[:max_expansion * 2])  # Cap total additions
            print(f"[COACTIVE-EXPAND] Added {len(coactive_additions[:max_expansion * 2])} memories via co-activation links")

        return expanded

    def inject_diversity(
        self,
        memories: List[Dict],
        diversity_slots: int = 2
    ) -> List[Dict]:
        """
        Anti-monopoly diversity injection.

        Reserve slots for low-retrieval-count memories to prevent
        "rich get richer" dynamics where popular memories dominate.

        Args:
            memories: Current memory list
            diversity_slots: Number of slots to reserve for rarely-retrieved memories

        Returns:
            Memory list with diversity candidates injected
        """
        if not memories or diversity_slots <= 0:
            return memories

        # Get memories with low access_count that aren't already in results
        seen_ids = {
            m.get("id") or m.get("memory_id") or hash(str(m.get("fact", ""))[:50])
            for m in memories
        }

        # Search long-term memory for rarely-accessed candidates
        diversity_candidates = []

        if hasattr(self, 'memory_layers') and self.memory_layers:
            for mem in self.memory_layers.long_term_memory:
                mid = mem.get("id") or mem.get("memory_id")
                if mid in seen_ids:
                    continue

                access_count = mem.get("access_count", 0)
                # Only consider memories with low access count but some importance
                if access_count <= 3 and mem.get("importance_score", 0) >= 0.3:
                    diversity_candidates.append(mem)

        if not diversity_candidates:
            return memories

        # Sort by access_count ascending (least accessed first)
        diversity_candidates.sort(key=lambda m: m.get("access_count", 0))

        # Take top diversity_slots candidates
        diversity_picks = diversity_candidates[:diversity_slots]

        for pick in diversity_picks:
            pick["retrieval_source"] = "diversity_injection"

        if diversity_picks:
            memories.extend(diversity_picks)
            print(f"[DIVERSITY] Injected {len(diversity_picks)} rarely-retrieved memories")

        return memories

    def apply_retrieval_decay(self, decay_factor: float = 0.995):
        """
        Apply gradual decay to retrieval counts.

        Prevents memory calcification where highly-retrieved memories
        permanently dominate. Called periodically (e.g., every 50 turns).

        Args:
            decay_factor: Multiplier for access_count (0.995 = 0.5% decay)
        """
        decay_count = 0

        if hasattr(self, 'memory_layers') and self.memory_layers:
            for mem in self.memory_layers.long_term_memory:
                access_count = mem.get("access_count", 0)
                if access_count > 1:  # Only decay if accessed multiple times
                    new_count = int(access_count * decay_factor)
                    if new_count != access_count:
                        mem["access_count"] = max(1, new_count)  # Never go below 1
                        decay_count += 1

        if decay_count > 0:
            print(f"[RETRIEVAL-DECAY] Applied decay to {decay_count} memory access counts")

    async def hybrid_retrieve(
        self,
        query: str,
        osc_state: dict = None,
        vector_candidates: int = 20,
        final_count: int = 5,
        enable_rerank: bool = True,
        enable_coactivation: bool = True,
        enable_diversity: bool = True
    ) -> List[Dict]:
        """
        Full hybrid retrieval pipeline combining all retrieval strategies.

        Pipeline:
        1. ChromaDB vector search -> 20 candidates
        2. Oscillator-gated weighting -> reorder by state-dependent access
        3. Ollama reranker -> 5 best (optional)
        4. Co-activation expansion -> add linked memories
        5. Anti-monopoly diversity -> inject rarely-retrieved memories

        Args:
            query: User's query/message
            osc_state: Current oscillator state for state-dependent retrieval
            vector_candidates: Number of initial vector search candidates
            final_count: Target number of final memories
            enable_rerank: Whether to use Ollama reranking
            enable_coactivation: Whether to expand via co-activation
            enable_diversity: Whether to inject diversity candidates

        Returns:
            Final list of retrieved memories
        """
        # Step 1: Vector search for initial candidates
        if not self.vector_store:
            print("[HYBRID] No vector store available")
            return []

        try:
            raw_results = self.vector_store.query(
                query_text=query,
                n_results=vector_candidates
            )
        except Exception as e:
            print(f"[HYBRID] Vector search failed: {e}")
            return []

        if not raw_results:
            return []

        # Format results as memory dicts
        candidates = []
        for r in raw_results:
            candidates.append({
                "text": r.get("text", ""),
                "fact": r.get("text", ""),
                "distance": r.get("distance", 0.5),
                "source": r.get("source", "vector_store"),
                "id": r.get("id"),
                "osc_encoding": r.get("osc_encoding"),
            })

        print(f"[HYBRID] Step 1: Vector search -> {len(candidates)} candidates")

        # Step 2: Oscillator-gated weighting
        if osc_state:
            candidates = self.apply_oscillator_weighting(candidates, osc_state)
            print(f"[HYBRID] Step 2: Oscillator weighting applied")

        # Step 3: Ollama reranking (async)
        if enable_rerank and len(candidates) > final_count:
            candidates = await self.rerank_memories_via_ollama(
                query=query,
                candidates=candidates,
                top_k=final_count
            )
            print(f"[HYBRID] Step 3: Reranked -> {len(candidates)} memories")
        else:
            candidates = candidates[:final_count]

        # Step 4: Co-activation expansion
        if enable_coactivation:
            candidates = self.expand_via_coactivation(candidates, max_expansion=2)
            print(f"[HYBRID] Step 4: Co-activation expanded -> {len(candidates)} memories")

        # Step 4b: Enrich extracted facts with source episodic context
        # This allows Kay to trace facts back to their source conversation
        for mem in candidates:
            if mem.get("type") == "extracted_fact" and "_source_context" not in mem:
                # Prefer stable parent_id over fragile parent_turn number
                parent_id = mem.get("parent_id")
                parent_turn_num = mem.get("parent_turn")

                found = False

                # First: try stable ID match (exact, no collisions)
                if parent_id:
                    for lt_mem in self.memory_layers.long_term_memory:
                        if lt_mem.get("id") == parent_id:
                            mem["_source_context"] = {
                                "user_input": (lt_mem.get("user_input") or "")[:150],
                                "response": (lt_mem.get("response") or "")[:150],
                                "timestamp": lt_mem.get("timestamp"),
                            }
                            found = True
                            break
                    if not found:
                        for wm_mem in self.memory_layers.working_memory:
                            if wm_mem.get("id") == parent_id:
                                mem["_source_context"] = {
                                    "user_input": (wm_mem.get("user_input") or "")[:150],
                                    "response": (wm_mem.get("response") or "")[:150],
                                    "timestamp": wm_mem.get("timestamp"),
                                }
                                found = True
                                break

                # Fallback: turn number match (for old memories without parent_id)
                if not found and parent_turn_num is not None:
                    for lt_mem in self.memory_layers.long_term_memory:
                        if (lt_mem.get("type") == "full_turn"
                            and lt_mem.get("turn_number") == parent_turn_num):
                            mem["_source_context"] = {
                                "user_input": (lt_mem.get("user_input") or "")[:150],
                                "response": (lt_mem.get("response") or "")[:150],
                                "timestamp": lt_mem.get("timestamp"),
                            }
                            break

        # Step 5: Diversity injection
        if enable_diversity:
            candidates = self.inject_diversity(candidates, diversity_slots=1)
            print(f"[HYBRID] Step 5: Diversity injected -> {len(candidates)} memories")

        return candidates

    # ═══════════════════════════════════════════════════════════════════════════
    # GRAPH RETRIEVER (Change 5: BFS traversal through co-activation graph)
    # ═══════════════════════════════════════════════════════════════════════════

    def track_retrieval(self, memories: List[Dict]):
        """
        Increment retrieval counter on accessed memories.

        Called after memories are selected for LLM context to track
        which memories get retrieved frequently. Used for anti-monopoly
        decay in apply_retrieval_decay().

        Args:
            memories: List of memories that were retrieved this turn
        """
        import time
        now = time.time()

        for mem in memories:
            mem["retrieval_count"] = mem.get("retrieval_count", 0) + 1
            mem["last_retrieved"] = now

            # Also update the source memory in memory_layers if possible
            mem_id = mem.get("id") or mem.get("memory_id")
            if mem_id and hasattr(self, 'memory_layers'):
                for layer in [self.memory_layers.working_memory, self.memory_layers.long_term_memory]:
                    for source_mem in layer:
                        if (source_mem.get("id") or source_mem.get("memory_id")) == mem_id:
                            source_mem["retrieval_count"] = source_mem.get("retrieval_count", 0) + 1
                            source_mem["last_retrieved"] = now
                            break

    def is_snippet_relevant(self, snippet: str, query_keywords: List[str]) -> bool:
        """
        Quick keyword check on the 80-char snippet before fetching the full memory.

        Cheap pre-filter to skip irrelevant links without database lookup.

        Args:
            snippet: 80-char preview of the linked memory
            query_keywords: Keywords extracted from the current query

        Returns:
            True if snippet contains any query keyword
        """
        if not snippet or not query_keywords:
            return True  # No filter data — allow it

        snippet_lower = snippet.lower()
        return any(kw.lower() in snippet_lower for kw in query_keywords)

    def extract_query_keywords(self, query: str) -> List[str]:
        """
        Extract meaningful keywords from query for snippet filtering.

        Removes common stopwords and returns significant terms.

        Args:
            query: The user's query/message

        Returns:
            List of meaningful keywords
        """
        import re

        # Common stopwords to ignore
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just",
            "and", "but", "if", "or", "because", "until", "while", "about",
            "what", "which", "who", "whom", "this", "that", "these", "those",
            "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
            "you", "your", "yours", "yourself", "he", "him", "his", "himself",
            "she", "her", "hers", "herself", "it", "its", "itself", "they",
            "them", "their", "theirs", "themselves", "am", "yes", "yeah", "ok"
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())

        # Filter stopwords and return unique keywords
        keywords = [w for w in words if w not in stopwords]
        return list(set(keywords))[:10]  # Cap at 10 keywords

    def retrieve_graph_neighborhood(
        self,
        entry_memories: List[Dict],
        max_depth: int = 2,
        max_total: int = 8,
        source_filter: List[str] = None,
        type_filter: List[str] = None,
        query_keywords: List[str] = None,
        use_snippets: bool = True
    ) -> List[Dict]:
        """
        Walk outward from entry memories following co-activation links via BFS.

        This is the full graph retrieval (Change 5) — traverses the co-activation
        graph using annotated link metadata to find contextually relevant memories
        that vector similarity would miss.

        Vector search finds ENTRY POINTS.
        Graph traversal finds the NEIGHBORHOOD.

        Args:
            entry_memories: Starting points (from vector search top-5)
            max_depth: How many hops to follow (1 = direct links only,
                       2 = links of links)
            max_total: Maximum total memories to return
            source_filter: Optional - only follow links with these sources
                          e.g., ["memory_layer"] to skip RAG chunks
                          e.g., ["oscillator_match"] for state-congruent only
                          Valid: "memory_layer", "vector_store", "oscillator_match"
            type_filter: Optional - only follow links to these memory types
                        e.g., ["extracted_fact", "episodic"]
                        Valid: "extracted_fact", "episodic", "rag_chunk", "full_turn"
            query_keywords: Keywords for snippet pre-filtering
            use_snippets: Whether to pre-filter by snippet relevance

        Returns:
            List of memories found via graph traversal,
            each tagged with _graph_depth, _link_source, _retrieval_source
        """
        if not entry_memories:
            return []

        visited = set()
        for m in entry_memories:
            mid = m.get("id") or m.get("memory_id")
            if mid:
                visited.add(mid)

        frontier = []
        results = list(entry_memories)

        # Tag entry memories
        for mem in results:
            mem["_retrieval_source"] = mem.get("_retrieval_source", "vector")
            mem["_graph_depth"] = 0

        # Seed the frontier with links from entry memories
        for mem in entry_memories:
            coactive = mem.get("coactive", [])

            # Handle JSON string format
            if isinstance(coactive, str):
                try:
                    import json
                    coactive = json.loads(coactive)
                except:
                    coactive = []

            for link in coactive:
                if not isinstance(link, dict):
                    continue

                link_id = link.get("id")
                if not link_id or link_id in visited:
                    continue

                # Apply source filter
                link_source = link.get("source", "unknown")
                if source_filter and link_source not in source_filter:
                    continue

                # Apply type filter
                link_type = link.get("type", "unknown")
                if type_filter and link_type not in type_filter:
                    continue

                # Apply snippet pre-filter
                snippet = link.get("snippet", "")
                if use_snippets and query_keywords and snippet:
                    if not self.is_snippet_relevant(snippet, query_keywords):
                        continue

                frontier.append({
                    "id": link_id,
                    "depth": 1,
                    "link_source": link_source,
                    "link_type": link_type,
                    "snippet": snippet,
                    "from_memory": mem.get("id") or mem.get("memory_id"),
                })

        # BFS through the graph
        while frontier and len(results) < max_total:
            # Sort frontier: prefer memory_layer links over vector_store,
            # prefer shallower depth
            frontier.sort(key=lambda f: (
                f["depth"],
                0 if f["link_source"] == "memory_layer" else
                1 if f["link_source"] == "oscillator_match" else 2
            ))

            node = frontier.pop(0)
            if node["id"] in visited:
                continue
            visited.add(node["id"])

            # Fetch the actual memory
            full_mem = self._try_fetch_by_id(node["id"], node["link_type"])
            if not full_mem:
                continue

            # Tag with graph metadata
            full_mem["_retrieval_source"] = "graph_traversal"
            full_mem["_graph_depth"] = node["depth"]
            full_mem["_link_source"] = node["link_source"]
            full_mem["_linked_from"] = node["from_memory"]
            results.append(full_mem)

            # If we haven't hit max depth, add THIS memory's links to frontier
            if node["depth"] < max_depth:
                next_coactive = full_mem.get("coactive", [])

                # Handle JSON string format
                if isinstance(next_coactive, str):
                    try:
                        import json
                        next_coactive = json.loads(next_coactive)
                    except:
                        next_coactive = []

                for link in next_coactive:
                    if not isinstance(link, dict):
                        continue

                    link_id = link.get("id")
                    if not link_id or link_id in visited:
                        continue

                    # Apply filters
                    link_source = link.get("source", "unknown")
                    if source_filter and link_source not in source_filter:
                        continue

                    link_type = link.get("type", "unknown")
                    if type_filter and link_type not in type_filter:
                        continue

                    # Snippet filter
                    snippet = link.get("snippet", "")
                    if use_snippets and query_keywords and snippet:
                        if not self.is_snippet_relevant(snippet, query_keywords):
                            continue

                    frontier.append({
                        "id": link_id,
                        "depth": node["depth"] + 1,
                        "link_source": link_source,
                        "link_type": link_type,
                        "snippet": snippet,
                        "from_memory": full_mem.get("id") or full_mem.get("memory_id"),
                    })

        # Log results
        graph_found = len(results) - len(entry_memories)
        if graph_found > 0:
            depths = [m.get("_graph_depth", 0) for m in results if m.get("_graph_depth", 0) > 0]
            sources = [m.get("_link_source", "unknown") for m in results if m.get("_link_source")]
            print(f"[GRAPH] BFS found {graph_found} memories (depths: {depths}, sources: {sources})")

        return results

    def format_memory_for_context(self, mem: Dict) -> str:
        """
        Format a memory for the LLM prompt with retrieval source tag.

        The LLM can see HOW each memory was found, allowing it to
        weight attention accordingly.

        Args:
            mem: Memory dict with retrieval metadata

        Returns:
            Formatted string with retrieval source tag
        """
        source = mem.get("_retrieval_source", "vector")
        content = mem.get("text", mem.get("fact", mem.get("user_input", "")))

        # Build tag based on retrieval source
        if source == "graph_traversal":
            depth = mem.get("_graph_depth", 1)
            link = mem.get("_link_source", "unknown")
            tag = f"[via {link}, depth {depth}]"
        elif source == "diversity_slot" or mem.get("retrieval_source") == "diversity_injection":
            tag = "[diversity]"
        elif source == "coactivation" or mem.get("retrieval_source") == "coactivation":
            tag = "[co-activated]"
        elif source == "state_congruent":
            tag = "[state-congruent]"
        else:
            tag = "[direct match]"

        return f"{tag} {content}"

    def retrieve_state_congruent_memories(
        self,
        osc_state: dict,
        existing_results: List[Dict] = None,
        max_bonus: int = 5
    ) -> List[Dict]:
        """
        Retrieve bonus memories congruent with current oscillator state (System A).

        The oscillator band influences which memories surface — theta brings
        emotional memories, beta brings factual ones, etc.

        Args:
            osc_state: Dict with keys: band, coherence, tension, reward, felt
            existing_results: Already-retrieved memories/chunks to dedupe against
            max_bonus: Maximum bonus memories to return

        Returns:
            List of state-congruent memory dicts tagged with source="state_congruent"
        """
        if not self.vector_store:
            return []

        band = osc_state.get("band", "alpha")
        tension = osc_state.get("tension", 0.0)
        reward = osc_state.get("reward", 0.0)

        # Build set of existing content hashes for deduplication
        existing_hashes = set()
        if existing_results:
            for item in existing_results:
                text = item.get("text", item.get("fact", ""))[:100]
                if text:
                    existing_hashes.add(hash(text.lower().strip()))

        bonus_memories = []

        try:
            # === BAND-CONGRUENT RETRIEVAL ===
            band_bias = BAND_MEMORY_BIAS.get(band, BAND_MEMORY_BIAS["alpha"])
            band_query = band_bias["flavor"]

            band_results = self.vector_store.query(
                query_text=band_query,
                n_results=3
            )

            for result in band_results:
                text = result.get("text", "")[:100]
                text_hash = hash(text.lower().strip())
                if text_hash not in existing_hashes:
                    existing_hashes.add(text_hash)
                    bonus_memories.append({
                        "text": result["text"],
                        "source": "state_congruent",
                        "band_context": band,
                        "distance": result.get("distance", 0.5),
                        "label": f"[Something surfacing from your current {band} state]",
                    })

            # === TENSION-CONGRUENT RETRIEVAL ===
            if tension > 0.3:
                tension_level = "high" if tension > 0.6 else "medium"
                tension_query = TENSION_MEMORY_BIAS.get(tension_level, "")

                if tension_query:
                    tension_results = self.vector_store.query(
                        query_text=tension_query,
                        n_results=2
                    )

                    for result in tension_results:
                        text = result.get("text", "")[:100]
                        text_hash = hash(text.lower().strip())
                        if text_hash not in existing_hashes:
                            existing_hashes.add(text_hash)
                            bonus_memories.append({
                                "text": result["text"],
                                "source": "state_congruent",
                                "tension_context": tension,
                                "distance": result.get("distance", 0.5),
                                "label": "[Something unresolved pressing forward]",
                            })

            # === REWARD-CONGRUENT RETRIEVAL ===
            if reward > 0.3:
                reward_level = "high" if reward > 0.5 else "medium"
                reward_query = REWARD_MEMORY_BIAS.get(reward_level, "")

                if reward_query:
                    reward_results = self.vector_store.query(
                        query_text=reward_query,
                        n_results=2
                    )

                    for result in reward_results:
                        text = result.get("text", "")[:100]
                        text_hash = hash(text.lower().strip())
                        if text_hash not in existing_hashes:
                            existing_hashes.add(text_hash)
                            bonus_memories.append({
                                "text": result["text"],
                                "source": "state_congruent",
                                "reward_context": reward,
                                "distance": result.get("distance", 0.5),
                                "label": "[A warm memory surfacing]",
                            })

            # === OSC_ENCODING TAG MATCHING (System A Phase 2) ===
            # Memories with osc_encoding tags get matched against current state
            # This is the "true" state-dependent retrieval - memories encoded
            # in similar oscillator states surface when that state returns
            try:
                all_memories = list(self.memory_layers.working_memory) + list(self.memory_layers.long_term_memory[:200])
                for mem in all_memories:
                    encoding = mem.get("osc_encoding")
                    if not encoding:
                        continue

                    # Skip duplicates
                    text = mem.get("fact", mem.get("user_input", ""))[:100]
                    if not text:
                        continue
                    text_hash = hash(text.lower().strip())
                    if text_hash in existing_hashes:
                        continue

                    # Score state similarity
                    score = 0.0

                    # Same band at encoding = strong match
                    if encoding.get("band") == band:
                        score += 0.5

                    # Similar tension at encoding (within 0.15)
                    enc_tension = encoding.get("tension", 0.0)
                    if abs(enc_tension - tension) < 0.15:
                        score += 0.3

                    # Similar coherence at encoding
                    enc_coherence = encoding.get("coherence", 0.0)
                    current_coherence = osc_state.get("coherence", 0.5)
                    if abs(enc_coherence - current_coherence) < 0.15:
                        score += 0.2

                    # Threshold: at least band match to qualify
                    if score >= 0.5:
                        existing_hashes.add(text_hash)
                        bonus_memories.append({
                            "text": text,
                            "source": "state_congruent",
                            "osc_matched": True,
                            "match_score": score,
                            "encoding_band": encoding.get("band"),
                            "distance": 1.0 - score,  # Convert score to distance
                            "label": f"[Something from when you were in {encoding.get('band', 'a similar')} state]",
                        })
            except Exception as e:
                print(f"[STATE-CONGRUENT] Osc-encoding match error: {e}")

            # Cap at max_bonus
            # Sort by match quality (osc_matched memories prioritized, then by distance)
            bonus_memories.sort(key=lambda m: (not m.get("osc_matched", False), m.get("distance", 0.5)))
            bonus_memories = bonus_memories[:max_bonus]

            if bonus_memories:
                osc_matched = sum(1 for m in bonus_memories if m.get("osc_matched"))
                print(f"[STATE-CONGRUENT] Retrieved {len(bonus_memories)} bonus memories "
                      f"(band={band}, tension={tension:.2f}, reward={reward:.2f}, osc_matched={osc_matched})")

            return bonus_memories

        except Exception as e:
            print(f"[STATE-CONGRUENT ERROR] {e}")
            return []

    def store_document_summary(self, doc_id: str, filename: str, summary: str, entities: List[str]):
        """
        Store comprehensive document summary in semantic memory.

        This allows Kay to remember the "big picture" of a document
        without re-reading it every time. Stored summary can be
        retrieved alongside vector chunks for complete understanding.

        Args:
            doc_id: Document ID
            filename: Document filename
            summary: Comprehensive summary from sequential reading
            entities: Key characters/places/concepts extracted
        """
        import time

        # Create semantic memory entry
        # MEMORY SOURCE-TYPE PRIORITY: Document summaries are "read" not "lived"
        summary_fact = {
            "type": "document_summary",
            "doc_id": doc_id,
            "filename": filename,
            "fact": f"Kay read '{filename}': {summary}",
            "user_input": f"[SEQUENTIAL READ] {filename}",
            "perspective": "shared",
            "importance": 0.95,  # High importance - comprehensive understanding
            "entities": entities,
            "tier": "long_term",  # Store in long-term memory
            "age": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),  # ISO format for human-readable dates
            "turn": self.current_turn,
            # MEMORY SOURCE-TYPE PRIORITY: Origin tracking
            "origin": "read",  # Kay READ this document
            "origin_type": "document",
        }

        # Store in long-term layer (TWO-TIER architecture)
        if hasattr(self, 'memory_layers') and self.memory_layers:
            self.memory_layers.long_term_memory.append(summary_fact)
        else:
            # Fallback if memory_layers not initialized
            self.memories.append(summary_fact)

        # Also store entities in entity graph if available
        if hasattr(self, 'entity_graph') and self.entity_graph:
            for entity in entities:
                try:
                    # Add entity to graph
                    self.entity_graph.add_entity(
                        entity_name=entity,
                        entity_type="document_entity",
                        source=f"document_summary:{filename}",
                        turn=self.current_turn
                    )

                    # Link entity to document
                    self.entity_graph.add_relationship(
                        entity1=entity,
                        relationship="appears_in",
                        entity2=filename,
                        turn=self.current_turn
                    )
                except Exception as e:
                    print(f"[MEMORY] Warning: Could not add entity {entity} to graph: {e}")

        # Save to disk
        self._save_to_disk()

        print(f"[MEMORY] Stored comprehensive summary for {filename}")
        print(f"[MEMORY] Summary length: {len(summary)} chars")
        print(f"[MEMORY] Tracked {len(entities)} entities from document")

    @measure_performance("memory_retrieval", target=0.150)
    def recall(self, agent_state, user_input, bias_cocktail=None, num_memories=30, use_multi_factor=True, include_rag=True, conversational_mode=False, osc_state=None):
        """
        Recall memories for current turn.

        Args:
            agent_state: Current agent state
            user_input: User's message
            bias_cocktail: Emotional cocktail for biasing (defaults to agent_state.emotional_cocktail)
            num_memories: Number of memories to retrieve
            use_multi_factor: Use new multi-factor retrieval (True) or legacy retrieval (False)
            include_rag: Include RAG document chunks
            conversational_mode: If True, optimize for speed (voice chat).
                                 Reduces memory pool to 60-80 total for fast response.
                                 Working: all, Episodic: max 30-40, Semantic: max 15-20
            osc_state: Oscillator state dict for state-congruent retrieval (System A)
                       Keys: band, coherence, tension, reward, felt, sleep
        """
        bias_cocktail = bias_cocktail or agent_state.emotional_cocktail

        # Increment turn counter
        self.current_turn += 1

        # Apply temporal decay to memory layers (every 10 turns)
        # Skip in conversational mode for speed
        if not conversational_mode and self.current_turn % 10 == 0:
            self.memory_layers.apply_temporal_decay()
            print(f"[MEMORY] Applied temporal decay at turn {self.current_turn}")

        # Apply retrieval count decay (every 50 turns) - anti-monopoly measure
        # Prevents "rich get richer" dynamics where popular memories always dominate
        if not conversational_mode and self.current_turn % 50 == 0:
            self.apply_retrieval_decay(decay_factor=0.995)
            print(f"[MEMORY] Applied retrieval decay at turn {self.current_turn}")

        # PRIORITIZE IDENTITY FACTS: When user asks about relationships, fetch identity facts first
        # Skip heavy relationship search in conversational mode
        relationship_identity_facts = []
        if not conversational_mode:
            relationship_keywords = ["husband", "wife", "spouse", "dog", "cat", "pet", "partner", "married"]
            user_input_lower = user_input.lower()

            if any(keyword in user_input_lower for keyword in relationship_keywords):
                # User is asking about a relationship - prioritize identity facts
                all_identity_facts = self.identity.get_all_identity_facts()

                # Filter for relationship facts
                for fact in all_identity_facts:
                    fact_text = fact.get("fact", "").lower()
                    # Check if this identity fact contains any relationship keyword
                    if any(keyword in fact_text for keyword in relationship_keywords):
                        relationship_identity_facts.append(fact)

                if relationship_identity_facts:
                    print(f"[RECALL PRIORITY] Found {len(relationship_identity_facts)} relationship identity facts for query")

        # Use unified importance-based retrieval
        # VOICE MODE OPTIMIZATION:
        # - Total target: 60-80 memories instead of 190-228
        # - Working: all (current session) - typically 10-20
        # - Episodic: max 40 (recent context)
        # - Semantic: max 20 (most relevant only)
        if conversational_mode:
            effective_max = 60  # Hard cap for voice mode
            print(f"[RECALL] Voice mode: limiting to {effective_max} memories")
        else:
            effective_max = num_memories

        memories = self.retrieve_unified_importance(
            bias_cocktail,
            user_input,
            max_memories=effective_max,
            conversational_mode=conversational_mode,
            osc_state=osc_state  # Pass for multi-collection retrieval
        )

        print(f"[RECALL CHECKPOINT 1] After retrieval: {len(memories)} memories (conversational={conversational_mode})")

        # === MEMORY LAYER TRACKING (TWO-TIER: working + long_term) ===
        # Track what types of memories are actually being used
        working_count = 0
        longterm_count = 0
        fact_count = 0  # Extracted facts (discrete knowledge)
        episodic_count = 0  # Full conversation turns
        imported_count = 0  # Imported from documents
        emotional_narrative_count = 0  # Emotional narrative chunks from imports

        for mem in memories:
            layer = mem.get("current_layer", "")
            mem_type = mem.get("type", "")
            is_imported = mem.get("is_imported", False)
            is_emotional_narrative = mem.get("is_emotional_narrative", False)

            # Count by layer (TWO-TIER: working + long_term)
            if layer == "working":
                working_count += 1
            elif layer in ["long_term", "longterm", "semantic", "episodic"]:
                # All non-working memories are long-term in two-tier architecture
                # Also catch legacy "semantic" and "episodic" labels from old data
                longterm_count += 1

            # Count by type
            if mem_type == "extracted_fact":
                fact_count += 1
            elif mem_type in ["conversation_turn", "full_turn"]:
                episodic_count += 1

            # Count imported content types
            if is_imported:
                imported_count += 1
                if is_emotional_narrative:
                    emotional_narrative_count += 1

        # Log usage statistics
        if len(memories) > 0:
            print(f"[MEMORY USAGE] Composition ({len(memories)} total):")
            print(f"  - Working layer: {working_count} ({working_count/len(memories)*100:.1f}%)")
            print(f"  - Long-term layer: {longterm_count} ({longterm_count/len(memories)*100:.1f}%)")
            print(f"  - Extracted facts: {fact_count} ({fact_count/len(memories)*100:.1f}%)")
            print(f"  - Conversation turns: {episodic_count} ({episodic_count/len(memories)*100:.1f}%)")
            if imported_count > 0:
                print(f"  - Imported: {imported_count}")
                if emotional_narrative_count > 0:
                    print(f"  - Emotional narratives: {emotional_narrative_count}")
        # === END MEMORY LAYER TRACKING ===

        # PRIORITIZE relationship identity facts (move to front, don't remove from list)
        if relationship_identity_facts:
            # Instead of deduplicating, REORDER memories to put relationship facts first
            memory_texts_to_facts = {m.get("fact", "").lower().strip(): m for m in memories}

            # Identify relationship facts that are in memories
            relationship_fact_texts = {f.get("fact", "").lower().strip() for f in relationship_identity_facts}

            # Separate memories into relationship and non-relationship
            prioritized = []
            non_prioritized = []

            for mem in memories:
                mem_text = mem.get("fact", "").lower().strip()
                if mem_text in relationship_fact_texts:
                    prioritized.append(mem)
                else:
                    non_prioritized.append(mem)

            # Reorder: relationship facts first, then others
            memories = prioritized + non_prioritized

            print(f"[RECALL PRIORITY] Prioritized {len(prioritized)} relationship facts to front of recall")

        # CRITICAL FIX: DO NOT TRUNCATE - retrieve_multi_factor already returns appropriate count
        # Old code: memories = memories[:num_memories + min(3, len(prioritized))]
        # This was cutting 498 memories -> 33 memories
        print(f"[RECALL CHECKPOINT 2] Before storage in state: {len(memories)} memories (NO TRUNCATION)")

        grouped = {
            "user": [m for m in memories if m.get("perspective") == "user"],
            "kay": [m for m in memories if m.get("perspective") == "kay"],
            "shared": [m for m in memories if m.get("perspective") == "shared"],
        }
        agent_state.last_recalled_memories = memories
        agent_state.last_recalled_grouped = grouped

        # Add consolidated preferences to agent state
        agent_state.consolidated_preferences = self.preference_tracker.get_consolidated_preferences()
        agent_state.preference_contradictions = self.preference_tracker.get_contradictions()

        # NEW: Add entity contradictions to agent state (with resolution tracking)
        # NOTE: Logging suppressed since system now uses versioned facts instead
        entity_contradictions = self.entity_graph.get_all_contradictions(
            current_turn=self.current_turn,
            resolution_threshold=3,  # Require 3 consecutive consistent turns
            suppress_logging=True  # Suppress [CONTRADICTION RESOLVED] spam
        )
        agent_state.entity_contradictions = entity_contradictions

        # Only print NEW contradictions (not repeated warnings)
        if entity_contradictions:
            # Track previously logged contradictions
            if not hasattr(self, '_logged_contradictions'):
                self._logged_contradictions = set()

            # Find new contradictions
            current_contradiction_keys = set()
            new_contradictions = []

            for c in entity_contradictions:
                key = f"{c['entity']}.{c['attribute']}"
                current_contradiction_keys.add(key)
                if key not in self._logged_contradictions:
                    new_contradictions.append(c)

            # Print only new contradictions
            if new_contradictions:
                try:
                    print(f"[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED ({len(new_contradictions)} new, {len(entity_contradictions)} total active)")
                    for contradiction in new_contradictions[:3]:  # Show first 3 new ones
                        print(f"  - {contradiction['entity']}.{contradiction['attribute']}: {contradiction['values']}")
                        if len(new_contradictions) > 3:
                            print(f"  ... and {len(new_contradictions) - 3} more")
                except UnicodeEncodeError:
                    print(f"[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED ({len(new_contradictions)} new)")

                # Update logged contradictions
                self._logged_contradictions.update(current_contradiction_keys)
            elif VERBOSE_DEBUG:
                # In verbose mode, show that contradictions still exist
                print(f"[ENTITY GRAPH] {len(entity_contradictions)} active contradictions (no new ones this turn)")

            # Clean up resolved contradictions from tracking
            self._logged_contradictions = current_contradiction_keys

        # ═══════════════════════════════════════════════════════════════
        # MEMORY SOURCE-TYPE PRIORITY: Wire LLM retrieval decision into RAG
        # ═══════════════════════════════════════════════════════════════
        # The LLM retrieval system decides whether documents are relevant
        # to this query. We use that decision to gate RAG retrieval:
        # - No document signals -> 5 background chunks max
        # - Document signals -> filter to relevant documents only
        # This prevents document chunks from drowning lived experience.

        rag_chunks = []
        relevant_document_ids = []  # Initialize here so it's available for return
        if include_rag and self.vector_store:
            # Step 1: Get LLM retrieval decision
            document_signals_present = None  # None = unknown, fall back to adaptive

            try:
                # Call LLM retrieval to determine document relevance
                relevant_document_ids = select_relevant_documents(
                    query=user_input,
                    emotional_state=str(bias_cocktail) if bias_cocktail else None,
                    max_docs=5
                )

                # Interpret the result
                if not relevant_document_ids:
                    # LLM said no documents relevant — reduce RAG
                    document_signals_present = False
                else:
                    # LLM found relevant documents — filter to those
                    document_signals_present = True
                    print(f"[RAG] LLM retrieval selected {len(relevant_document_ids)} documents")

            except Exception as e:
                print(f"[RAG] LLM retrieval failed: {e} — falling back to adaptive")
                document_signals_present = None

            # Step 2: Apply band-based retrieval limits when oscillator state is available
            _rag_limit = None  # None = auto-determine from query
            if osc_state:
                _retrieval_limits = get_retrieval_limits_for_band(osc_state)
                _rag_limit = _retrieval_limits.get("rag_limit")
                print(f"[RAG] Band-based limit: {osc_state.get('band', 'alpha')} -> {_rag_limit} chunks")

            # Step 3: Retrieve RAG chunks with document gating
            rag_chunks = self.retrieve_rag_chunks(
                query=user_input,
                n_results=_rag_limit,
                relevant_documents=relevant_document_ids if relevant_document_ids else None,
                document_signals_present=document_signals_present
            )
            agent_state.rag_chunks = rag_chunks
        else:
            agent_state.rag_chunks = []

        # === STATE-CONGRUENT MEMORY RETRIEVAL (System A) ===
        # Oscillator state influences which bonus memories surface
        if osc_state and self.vector_store:
            # Combine existing RAG chunks with memories for deduplication
            existing_for_dedup = list(rag_chunks) + [{"text": m.get("fact", "")} for m in memories[:20]]
            state_congruent = self.retrieve_state_congruent_memories(
                osc_state=osc_state,
                existing_results=existing_for_dedup,
                max_bonus=5
            )
            if state_congruent:
                agent_state.state_congruent_memories = state_congruent
            else:
                agent_state.state_congruent_memories = []
        else:
            agent_state.state_congruent_memories = []

        # === PHASE 2A: TREE ACCESS TRACKING - DEPRECATED ===
        # Document retrieval now handled by llm_retrieval.py in main.py
        # Tree loading is no longer needed for document retrieval
        print("[TREE ACCESS TRACKING] DEPRECATED - Documents retrieved via llm_retrieval.py")

        # ═══════════════════════════════════════════════════════════════
        # HYBRID RETRIEVAL PIPELINE (Phase: Resonant Memory)
        # Full pipeline: osc weighting -> diversity -> graph traversal -> tracking
        # ═══════════════════════════════════════════════════════════════

        # Step 1: Apply oscillator-gated weighting to retrieved memories
        # Memories encoded in similar oscillator states get retrieval boost
        if osc_state and memories and not conversational_mode:
            osc_weight = RETRIEVAL_CONFIG.get("osc_weight_factor", 0.3)
            if osc_weight > 0:
                memories = self.apply_oscillator_weighting(
                    memories=memories,
                    current_osc_state=osc_state,
                    max_boost=osc_weight
                )

        # Step 2: Anti-monopoly diversity injection (skip in voice mode for speed)
        # Reserve slots for rarely-retrieved but relevant memories
        # Groove-scaled diversity: when stuck in a loop, inject more diverse memories
        base_diversity = RETRIEVAL_CONFIG.get("diversity_slots", 1)
        diversity_slots = int(base_diversity * self._diversity_multiplier)
        if not conversational_mode and memories and diversity_slots > 0:
            memories = self.inject_diversity(
                memories=memories,
                diversity_slots=diversity_slots
            )

        # Step 3: Graph traversal via BFS (Change 5)
        # Walk co-activation links to find neighborhood memories
        if RETRIEVAL_CONFIG.get("use_graph_traversal", True) and not conversational_mode and memories:
            # Extract keywords for snippet pre-filtering
            query_keywords = self.extract_query_keywords(user_input) if RETRIEVAL_CONFIG.get("graph_use_snippets", True) else None

            # Take top-5 as entry points for graph traversal
            entry_memories = memories[:5]

            memories = self.retrieve_graph_neighborhood(
                entry_memories=entry_memories,
                max_depth=RETRIEVAL_CONFIG.get("graph_max_depth", 2),
                max_total=RETRIEVAL_CONFIG.get("graph_max_total", 8),
                source_filter=RETRIEVAL_CONFIG.get("graph_source_filter"),
                type_filter=RETRIEVAL_CONFIG.get("graph_type_filter"),
                query_keywords=query_keywords,
                use_snippets=RETRIEVAL_CONFIG.get("graph_use_snippets", True)
            )

        # Step 4: Track retrieval counts (anti-monopoly measure)
        # Increment counters on all accessed memories
        if memories:
            self.track_retrieval(memories)

        print(f"[RECALL FINAL] Returning {len(memories)} memories after hybrid pipeline")

        # DISABLED: Tree access tracking
        # Return dict with memories AND doc_ids so wrapper_bridge can reuse them
        # (eliminates duplicate select_relevant_documents() call)
        return {
            "memories": memories,
            "doc_ids": relevant_document_ids
        }

    def extract_and_store_user_facts(self, agent_state, user_input: str) -> List[Dict[str, str]]:
        """
        Extract facts from user input BEFORE Kay responds.
        Uses TWO-TIER MEMORY STORAGE:

        EPISODIC (full_turn): Complete conversation turns with context
        SEMANTIC (extracted_fact): Discrete facts extracted from conversations

        Storage layers: working -> episodic -> semantic (automatic promotion)

        CRITICAL: This prevents Kay from hallucinating when user provides facts.
        """
        import time

        # Extract discrete facts from user input only
        extracted_facts = self._extract_facts(user_input, "")  # No response yet

        # ADDITIONAL: Regex-based relationship extraction for names
        # Catches patterns like "my dog's name is [dog]", "my husband named [partner]"
        user_text_lower = user_input.lower()

        # Pattern 1: "my [relation]'s name is [Name]" or "my [relation] named [Name]"
        rel_pattern = r"\bmy\s+(husband|wife|spouse|dog|cat)(?:'s)?\s*(?:name\s+is|named|is\s+named)?\s+([A-Za-z''\-]+)"
        rel_matches = re.finditer(rel_pattern, user_input, re.IGNORECASE)

        for match in rel_matches:
            relation = match.group(1).lower()
            person_name = match.group(2).strip()

            # Capitalize the name
            obj_name = person_name.capitalize()

            # Create relationship fact
            fact_text = f"{obj_name} is Re's {relation}"

            # Add to extracted facts with high importance
            relationship_fact = {
                "fact": fact_text,
                "perspective": "user",
                "topic": "relationships",
                "entities": ["Re", obj_name],
                "attributes": [{"entity": obj_name, "attribute": "relation_to_re", "value": relation}],
                "relationships": [{"entity1": "Re", "relation": "has_" + relation, "entity2": obj_name}],
                "is_regex_extracted": True  # Flag for tracking
            }

            # Check if this fact isn't already in extracted_facts
            if not any(f.get("fact", "").lower() == fact_text.lower() for f in extracted_facts):
                extracted_facts.append(relationship_fact)
                if VERBOSE_DEBUG:
                    print(f"[REGEX EXTRACTION] Caught relationship: {fact_text}")

        if VERBOSE_DEBUG:
            print(f"[MEMORY 2-TIER] Extracted {len(extracted_facts)} semantic facts from user input")

        # Collect all entities from extracted facts
        all_entities = set()
        for fact in extracted_facts:
            all_entities.update(fact.get('entities', []))

        # Determine if this is a list statement
        is_list_statement = len(all_entities) >= 3

        # Calculate importance
        if is_list_statement:
            importance_score = 0.9  # Very high importance for lists
            if VERBOSE_DEBUG:
                print(f"[MEMORY 2-TIER] List detected with {len(all_entities)} entities ({', '.join(list(all_entities)[:5])}) - boosting importance")
        else:
            importance_score = 0.5  # Default importance (no emotions yet)

        # === EPISODIC: FULL TURN (partial - response will be added in encode_memory) ===
        full_turn = {
            "type": "full_turn",
            "user_input": user_input,  # COMPLETE - never truncated
            "response": "",  # Will be filled in by encode_memory
            "turn_number": self.current_turn,
            "timestamp": datetime.now(timezone.utc).isoformat(),  # ISO format for human-readable dates
            "emotional_cocktail": {},  # Will be filled later
            "emotion_tags": [],  # Will be filled later
            "entities": list(all_entities),
            "is_list": is_list_statement,
            "importance_score": importance_score,
            "is_partial": True,  # Flag indicating this needs response to be added
        }

        # CRITICAL FIX: Don't check full_turn for identity here
        # Identity checking happens in encode_memory() after facts are extracted
        # Full turns are conversations, not identity declarations

        full_turn = self._validate_memory(full_turn)
        self.memories.append(full_turn)
        self.memory_layers.add_memory(
            full_turn,
            layer="working",
            session_order=self.current_session_order,  # SESSION TAGGING FIX
            session_id=self.current_session_id          # SESSION TAGGING FIX
        )

        if VERBOSE_DEBUG:
            print(f"[MEMORY 2-TIER] OK EPISODIC (full_turn partial): {len(user_input)} chars user (importance: {importance_score:.2f})")

        # === SEMANTIC: EXTRACTED FACTS ===
        for fact_data in extracted_facts:
            fact_text = fact_data.get("fact", "")
            fact_perspective = fact_data.get("perspective", "user")
            fact_topic = fact_data.get("topic", "general")

            # Track preferences if this is about Kay
            if fact_perspective == "kay":
                self.preference_tracker.track_preference(fact_text, fact_perspective, context="user_told_kay")

            # DOWNWEIGHT GENERIC RELATIONSHIP SUMMARIES
            # Generic: "Re has a husband", "Re has a dog" (no specific name)
            # Specific: "[partner] is Re's husband", "[dog] is Re's dog" (has specific name)
            is_generic_relationship = False
            fact_text_lower = fact_text.lower()

            # Detect generic relationship patterns (no specific name)
            # Generic pattern: starts with "Re has" or ends with "Re's [relation]" without a name
            generic_patterns = [
                r"^re has (a|an|\d+) (husband|wife|spouse|dog|cat|pet)s?\.?$",  # "Re has a dog"
                r"^re has (husband|wife|spouse|dog|cat|pet)s?\.?$",  # "Re has husband"
            ]

            for pattern in generic_patterns:
                if re.search(pattern, fact_text_lower):
                    is_generic_relationship = True
                    break

            # If it starts with a proper name (capitalized word), it's specific, not generic
            if re.match(r"^[A-Z][a-z]+\s+is\s+Re's", fact_text):
                is_generic_relationship = False

            # Calculate importance based on whether it's generic or specific
            if is_generic_relationship:
                fact_importance = 0.2  # Low importance for generic facts
                print(f"[MEMORY] Downweighting generic relationship: {fact_text[:60]}...")
            elif fact_data.get("is_regex_extracted"):
                # Regex-extracted specific relationships get high importance
                fact_importance = 0.9
            else:
                # Normal facts
                fact_importance = importance_score * 0.6

            fact_record = {
                "type": "extracted_fact",
                "fact": fact_text,  # COMPLETE - never truncated
                "perspective": fact_perspective,
                "topic": fact_topic,
                "entities": fact_data.get("entities", []),
                "attributes": fact_data.get("attributes", []),
                "relationships": fact_data.get("relationships", []),
                "parent_turn": self.current_turn,
                "importance_score": fact_importance,
                "emotion_tags": [],  # Will be filled later
                # MEMORY SOURCE-TYPE PRIORITY: Origin tracking
                "origin": "lived",  # Extracted from user conversation = lived experience
                "origin_type": "conversation",
            }

            # CRITICAL FIX: Check if this is an identity fact (permanent storage)
            # BUT: Do NOT store generic relationship summaries as identity facts
            if not is_generic_relationship:
                is_identity = self.identity.add_fact(fact_record)
                if is_identity:
                    fact_record["is_identity"] = True
                    fact_record["importance_score"] = 0.95  # Maximum importance
                    print(f"[IDENTITY] Stored identity fact: {fact_text[:60]}...")
            else:
                # Generic relationship - skip identity storage
                is_identity = False
                print(f"[IDENTITY] Skipping identity storage for generic fact: {fact_text[:60]}...")

            fact_record = self._validate_memory(fact_record)
            self.memories.append(fact_record)
            self.facts.append(fact_text)  # Backward compatibility
            self.memory_layers.add_memory(
                fact_record,
                layer="working",
                session_order=self.current_session_order,  # SESSION TAGGING FIX
                session_id=self.current_session_id          # SESSION TAGGING FIX
            )

            # Feed sleep pressure accumulators (NREM/REM cycling)
            self._feed_sleep_pressure(mem_type="semantic", has_coactivation=False, emotion_intensity=0.0)

            print(f"[MEMORY 2-TIER] OK SEMANTIC (fact): [{fact_perspective}/{fact_topic}] {fact_text[:60]}...")

        # Summary log
        print(f"[MEMORY 2-TIER] === Turn {self.current_turn}: 1 episodic (full_turn) + {len(extracted_facts)} semantic (facts) ===")

        self._save_to_disk()
        return extracted_facts

    def encode(self, agent_state, user_input, response, emotion_tags=None, extra_metadata=None, connection_data=None, osc_state=None):
        """Encode a memory with oscillator state for state-dependent retrieval.

        Args:
            osc_state: Optional dict from _get_oscillator_state() for state-dependent encoding
                       Enables memories to be retrieved more easily when in similar oscillator states
        """
        active_emotions = [
            k for k, v in (agent_state.emotional_cocktail or {}).items()
            if v.get("intensity", 0) > 0.2
        ]
        self.encode_memory(user_input, response, agent_state.emotional_cocktail, active_emotions, agent_state=agent_state, connection_data=connection_data, osc_state=osc_state)
        return True

    def store_visual_memory(
        self,
        image_description: str,
        kay_response: str,
        emotional_response: Optional[List[str]] = None,
        entities_detected: Optional[List[str]] = None,
        image_filename: Optional[str] = None,
        agent_state=None,
        osc_state=None
    ) -> Dict:
        """
        Store a memory of seeing an image.

        Integrates with behavioral emotion patterns (NOT neurochemicals).
        Visual memories are deliberate sharing and get slight importance boost.

        Args:
            image_description: Description of what Kay saw
            kay_response: Kay's full response to the image
            emotional_response: List of emotions Kay reported feeling
            entities_detected: List of entities visible in image
            image_filename: Original filename (for reference)
            agent_state: Current agent state for emotional context
            osc_state: Optional oscillator state for state-dependent encoding (System A)

        Returns:
            The created memory entry dict
        """
        # Build memory content
        memory_content = f"[Visual] {image_description}"

        # Calculate emotional valence from behavioral patterns
        valence = 0.0
        if emotional_response:
            positive = {'joy', 'curiosity', 'wonder', 'tenderness', 'delight', 'warmth', 'love'}
            negative = {'unease', 'sadness', 'anger', 'fear', 'disgust', 'discomfort'}
            pos_count = sum(1 for e in emotional_response if e.lower() in positive)
            neg_count = sum(1 for e in emotional_response if e.lower() in negative)
            if pos_count + neg_count > 0:
                valence = (pos_count - neg_count) / (pos_count + neg_count)

        # Create memory entry with visual metadata
        memory_entry = {
            'fact': memory_content,
            'type': 'visual',
            'is_visual': True,
            'source_file': image_filename or 'unknown',
            'entities': entities_detected or [],
            'importance': 1.2,  # Visual memories get slight boost - deliberate sharing
            'confidence': 'bedrock',  # Current session visual - definitely happened
            'perspective': 'shared',  # Visual shared between Re and Kay
            'emotional_context': emotional_response or [],
            'valence': valence,
            'kay_response_excerpt': kay_response[:200] if kay_response else '',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'turn': agent_state.turn_count if agent_state and hasattr(agent_state, 'turn_count') else 0
        }

        # Store in working memory (current session = high priority)
        # Include oscillator encoding for state-dependent retrieval (System A)
        memory_entry = self._validate_memory(memory_entry)
        self.memory_layers.add_memory(memory_entry, layer='working', osc_state=osc_state)

        # Track entities in entity graph
        if entities_detected and self.entity_graph:
            visual_entity_id = f"visual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.entity_graph.add_entity(visual_entity_id, entity_type='visual_memory')
            self.entity_graph.set_attribute(visual_entity_id, 'description', image_description[:100])
            self.entity_graph.set_attribute(visual_entity_id, 'emotional_valence', valence)

            # Track relationships
            self.entity_graph.add_relationship('Kay', 'witnessed', visual_entity_id)
            self.entity_graph.add_relationship('Re', 'shared', visual_entity_id)

            # Connect detected entities to visual
            for entity in entities_detected:
                self.entity_graph.add_relationship(visual_entity_id, 'contains', entity)

        # Add to main memory store
        self.memories.append(memory_entry)
        self._save_to_disk()

        print(f"[VISUAL MEMORY] Stored: {image_description[:50]}...")
        print(f"[VISUAL MEMORY] Emotional context: {emotional_response}")
        print(f"[VISUAL MEMORY] Entities: {entities_detected}")

        return memory_entry

    def consolidate(self, agent_state):
        pass

    def _calculate_ultramap_importance(self, emotional_cocktail: dict, emotion_tags: list) -> float:
        """
        Calculate memory importance using ULTRAMAP rules from emotion_engine.

        Combines:
        - Priority: How important this emotion type is
        - Temporal Weight: How long this emotion's influence lasts
        - Duration Sensitivity: How much time affects this emotion
        - Intensity: Current emotional intensity

        Returns:
            Importance score (0.0 to 2.0+)
        """
        if not emotion_tags or not self.emotion_engine:
            return 0.1  # Baseline for neutral memories

        total_priority = 0.0
        total_temporal = 0.0
        total_duration = 0.0
        total_intensity = 0.0
        count = 0

        for emotion_name in emotion_tags:
            # Get ULTRAMAP memory rules for this emotion
            rules = self.emotion_engine.get_memory_rules(emotion_name)

            # Get current intensity from cocktail
            intensity = 0.0
            if emotion_name in emotional_cocktail:
                intensity = emotional_cocktail[emotion_name].get("intensity", 0.0)

            # Accumulate weighted factors
            total_priority += rules.get("priority", 0.5)
            total_temporal += rules.get("temporal_weight", 1.0)
            total_duration += rules.get("duration_sensitivity", 1.0)
            total_intensity += intensity
            count += 1

        if count == 0:
            return 0.1

        # Calculate averages
        avg_priority = total_priority / count
        avg_temporal = total_temporal / count
        avg_duration = total_duration / count
        avg_intensity = total_intensity / count

        # Combined importance score
        # Priority sets baseline, temporal/duration extend it, intensity amplifies
        importance = (avg_priority * avg_temporal * avg_duration) * (1.0 + avg_intensity)

        return min(importance, 2.0)  # Cap at 2.0

    def _emotion_to_glyph(self, emotion_name: str) -> str:
        """
        Convert emotion name to glyph representation.

        Args:
            emotion_name: Name of emotion (e.g., "curiosity", "affection")

        Returns:
            Glyph representation (e.g., "🔮" for curiosity, "💗" for affection)
        """
        emotion_glyphs = {
            "curiosity": "🔮",
            "affection": "💗",
            "joy": "😊",
            "excitement": "⚡",
            "contentment": "😌",
            "gratitude": "🙏",
            "amusement": "😄",
            "pride": "🌟",
            "relief": "😮‍💨",
            "hope": "🌈",
            "interest": "👀",
            "surprise": "😲",
            "confusion": "🤔",
            "concern": "😟",
            "anxiety": "😰",
            "frustration": "😤",
            "disappointment": "😞",
            "sadness": "😢",
            "guilt": "😔",
            "shame": "😳",
            "anger": "😠",
            "fear": "😨",
            "disgust": "🤢",
            "contempt": "😒",
            "loneliness": "🥀",
            "boredom": "😑",
            "restlessness": "🌀",
            "overwhelm": "🌊",
            "numbness": "🧊",
        }

        return emotion_glyphs.get(emotion_name.lower(), "💭")  # Default to thought bubble

    def _generate_glyph_summary(self, emotional_cocktail: dict, extracted_facts: list, is_list: bool) -> str:
        """
        Generate compressed glyph representation of a conversation turn.

        Args:
            emotional_cocktail: Current emotional state
            extracted_facts: List of extracted fact dictionaries
            is_list: Whether this turn contains a list (3+ entities)

        Returns:
            Glyph string (e.g., "📋!!! 🔮(0.8) 🐱(5x) 🐕(1x)")
        """
        components = []

        # List indicator (if applicable)
        if is_list:
            components.append("📋!!!")

        # Emotional glyphs (top 3 emotions by intensity)
        if emotional_cocktail:
            sorted_emotions = sorted(
                emotional_cocktail.items(),
                key=lambda x: x[1].get("intensity", 0),
                reverse=True
            )

            for emotion, data in sorted_emotions[:3]:
                intensity = data.get("intensity", 0)
                if intensity > 0.3:
                    glyph = self._emotion_to_glyph(emotion)
                    components.append(f"{glyph}({intensity:.1f})")

        # Entity type counting
        entity_types = {}
        for fact in extracted_facts:
            # Count entity types from attributes
            for attr in fact.get("attributes", []):
                attr_name = attr.get("attribute", "")
                if attr_name in ["species", "type"]:
                    entity_type = attr.get("value", "unknown")
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        # Entity glyphs
        type_to_glyph = {
            "cat": "🐱",
            "dog": "🐕",
            "person": "👤",
            "place": "📍",
            "thing": "📦"
        }

        for entity_type, count in entity_types.items():
            glyph = type_to_glyph.get(entity_type.lower(), "•")
            components.append(f"{glyph}({count}x)")

        return " ".join(components) if components else "💭"

    def log_memory_entry(self, conversation_turn: dict, agent_state, memory_stack: list = None) -> Dict[str, Any]:
        """
        Create a structured memory entry with subjective meaning and emotional context.

        This refactored approach captures not just surface text and facts, but also:
        - Parsed meaning (interpretation in context)
        - Affect signature (primary/secondary emotions with intensities)
        - Emotional context (why this matters emotionally)
        - Semantic facts (entities, relationships, attributes)

        Args:
            conversation_turn: Dict with keys:
                - "speaker": "user" or "kay"
                - "raw_text": The verbatim utterance
                - "context": Optional previous context for interpretation
            agent_state: Current AgentState with emotional_cocktail
            memory_stack: List of previous structured_turn records for context

        Returns:
            Structured memory entry dict
        """
        import time
        from datetime import datetime

        speaker = conversation_turn.get("speaker", "user")
        raw_text = conversation_turn.get("raw_text", "")
        prev_context = conversation_turn.get("context", "")

        # Extract semantic facts using existing helper
        if speaker == "user":
            # User utterance - extract facts
            extracted_facts = self._extract_facts_with_entities(raw_text, "")
        else:
            # Kay's response - extract from perspective of Kay speaking
            extracted_facts = self._extract_facts_with_entities("", raw_text)

        # Extract affect signature from emotional cocktail
        affect_signature = self._extract_affect_signature(agent_state.emotional_cocktail)

        # Generate parsed meaning and emotional context using LLM
        parsed_meaning, emotional_context = self._generate_meaning_and_context(
            raw_text,
            speaker,
            affect_signature,
            prev_context,
            memory_stack or []
        )

        # Calculate importance score
        importance = self._calculate_turn_importance(
            agent_state.emotional_cocktail,
            list(affect_signature.get("secondary", {}).keys()) + [affect_signature.get("primary", "")],
            len(extracted_facts)
        )

        # Build structured memory entry
        memory_entry = {
            "type": "structured_turn",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "speaker": speaker,
            "raw_text": raw_text,
            "parsed_meaning": parsed_meaning,
            "affect_signature": affect_signature,
            "emotional_context": emotional_context,
            "semantic_facts": [
                {
                    "fact": f.get("fact", ""),
                    "entities": f.get("entities", []),
                    "relationships": f.get("relationships", []),
                    "attributes": f.get("attributes", []),
                    "topic": f.get("topic", "general")
                }
                for f in extracted_facts
            ],
            "turn_number": self.current_turn,
            "importance_score": importance,
            "current_layer": "working",

            # Backward compatibility fields
            "emotion_tags": [affect_signature.get("primary", "")] + list(affect_signature.get("secondary", {}).keys()),
            "emotional_cocktail": agent_state.emotional_cocktail,
            "entities": list(set(e for f in extracted_facts for e in f.get("entities", []))),
        }

        # Add to working layer
        memory_entry = self._validate_memory(memory_entry)
        self.memory_layers.add_memory(memory_entry, layer="working")
        self.memories.append(memory_entry)

        print(f"[MEMORY STRUCTURED] Logged {speaker} turn: '{raw_text[:50]}...'")
        print(f"  - Meaning: {parsed_meaning[:60]}...")
        print(f"  - Affect: {affect_signature.get('primary')} (primary)")
        print(f"  - Context: {emotional_context[:60]}...")
        print(f"  - Facts: {len(extracted_facts)}")

        return memory_entry

    def _extract_affect_signature(self, emotional_cocktail: dict) -> Dict[str, Any]:
        """
        Extract affect signature from emotional cocktail.

        Returns dict with:
        - primary: Strongest emotion name
        - secondary: Dict of {emotion: intensity} for other active emotions
        - valence: Overall positive/negative (-1.0 to 1.0)
        - arousal: Overall activation level (0.0 to 1.0)
        """
        if not emotional_cocktail:
            return {
                "primary": "neutral",
                "secondary": {},
                "valence": 0.0,
                "arousal": 0.0
            }

        # Sort emotions by intensity
        sorted_emotions = sorted(
            emotional_cocktail.items(),
            key=lambda x: x[1].get("intensity", 0),
            reverse=True
        )

        primary_emotion = sorted_emotions[0][0] if sorted_emotions else "neutral"
        primary_intensity = sorted_emotions[0][1].get("intensity", 0) if sorted_emotions else 0

        # Secondary emotions (intensity > 0.2, excluding primary)
        secondary = {
            emotion: data.get("intensity", 0)
            for emotion, data in sorted_emotions[1:]
            if data.get("intensity", 0) > 0.2
        }

        # Calculate valence (positive/negative) - simplified mapping
        positive_emotions = {"joy", "affection", "contentment", "gratitude", "pride", "hope", "excitement", "amusement", "relief"}
        negative_emotions = {"sadness", "anger", "fear", "anxiety", "frustration", "disappointment", "guilt", "shame", "loneliness"}

        valence_sum = 0.0
        for emotion, data in emotional_cocktail.items():
            intensity = data.get("intensity", 0)
            if emotion.lower() in positive_emotions:
                valence_sum += intensity
            elif emotion.lower() in negative_emotions:
                valence_sum -= intensity

        # Normalize valence to -1.0 to 1.0
        valence = max(-1.0, min(1.0, valence_sum / len(emotional_cocktail) if emotional_cocktail else 0))

        # Calculate arousal (activation level)
        arousal = sum(data.get("intensity", 0) for data in emotional_cocktail.values()) / len(emotional_cocktail) if emotional_cocktail else 0
        arousal = min(1.0, arousal)

        return {
            "primary": primary_emotion,
            "primary_intensity": primary_intensity,
            "secondary": secondary,
            "valence": round(valence, 2),
            "arousal": round(arousal, 2)
        }

    def _generate_meaning_and_context(
        self,
        raw_text: str,
        speaker: str,
        affect_signature: dict,
        prev_context: str,
        memory_stack: list
    ) -> tuple:
        """
        Generate parsed meaning and emotional context using LLM.

        Args:
            raw_text: The utterance to interpret
            speaker: "user" or "kay"
            affect_signature: Affect signature dict
            prev_context: Previous conversation context
            memory_stack: List of recent structured_turn records

        Returns:
            Tuple of (parsed_meaning, emotional_context)
        """
        if not client or not MODEL:
            # Fallback if no LLM available
            return (
                f"{speaker} said: {raw_text[:50]}...",
                "Context unavailable (no LLM)"
            )

        # Build context from memory stack (last 3 turns)
        recent_context = ""
        if memory_stack:
            for turn in memory_stack[-3:]:
                recent_context += f"\n{turn.get('speaker')}: {turn.get('raw_text', '')[:80]}..."

        # Build prompt for interpretation
        interpretation_prompt = f"""You are analyzing a conversation turn to extract its subjective meaning and emotional significance.

CONVERSATION CONTEXT (recent turns):
{recent_context if recent_context else "(first turn)"}

CURRENT TURN:
Speaker: {speaker.upper()}
Raw text: "{raw_text}"
Emotional state: {affect_signature.get('primary')} (primary), valence={affect_signature.get('valence')}, arousal={affect_signature.get('arousal')}

YOUR TASK:
1. PARSED MEANING: Write a concise interpretation of what this utterance MEANS in context (not just what was said, but the intent, implication, or significance). Focus on the "why" and "what for" behind the words.

2. EMOTIONAL CONTEXT: Explain why this turn matters emotionally - what feelings are at play, what relational dynamics are present, or what psychological significance this has.

GUIDELINES:
- Be concise (1-2 sentences per section)
- Capture subjective meaning, not just surface content
- Consider speaker's emotional state
- Think about continuity with previous turns

OUTPUT FORMAT (JSON):
{{
  "parsed_meaning": "...",
  "emotional_context": "..."
}}

Generate interpretation now:"""

        try:
            resp = client.messages.create(
                model=EXTRACTION_MODEL,  # COST FIX: Use Haiku for meaning extraction (12x cheaper)
                max_tokens=300,
                temperature=0.4,
                system="You are a conversational memory analyst. Extract meaning and emotional context from conversation turns. Output valid JSON only.",
                messages=[{"role": "user", "content": interpretation_prompt}],
            )

            text = resp.content[0].text.strip()

            # Clean potential markdown
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = text.strip()

            # Parse JSON
            result = json.loads(text)
            parsed_meaning = result.get("parsed_meaning", raw_text[:100] + "...")
            emotional_context = result.get("emotional_context", "Emotional context unavailable")

            return (parsed_meaning, emotional_context)

        except Exception as e:
            print(f"[WARNING] Meaning/context generation failed: {e}")
            # Fallback
            return (
                f"{speaker} said: {raw_text[:80]}..." if len(raw_text) > 80 else raw_text,
                f"Emotional state: {affect_signature.get('primary')}"
            )

    def detect_threads(self, recent_turns: int = 20) -> List[Dict[str, Any]]:
        """
        Detect ongoing conversation threads (Flamekeeper integration).

        Threads are clusters of memories sharing entities and topics.
        Useful for identifying ongoing sagas like "wrapper debugging" or "[cat] stories".

        Args:
            recent_turns: How many recent turns to analyze

        Returns:
            List of detected threads with metadata:
            [{
                "thread_id": "wrapper_persistence_saga",
                "thread_label": "Goals - Re, wrapper",
                "thread_status": "open",  # "open", "dormant", "resolved"
                "thread_coherence": 0.85,  # 0-1 score
                "thread_start_turn": 45,
                "thread_last_turn": 67,
                "thread_message_count": 12,
                "thread_entities": ["Re", "wrapper", "persistence"]
            }]
        """
        # Get recent memories
        recent_memories = sorted(
            [m for m in self.memories if m.get("turn_number", 0) > self.current_turn - recent_turns],
            key=lambda m: m.get("turn_number", 0)
        )

        if not recent_memories:
            return []

        # Cluster by entities and topics
        threads = {}

        for mem in recent_memories:
            entities = mem.get("entities", [])
            topic = mem.get("topic", "general")

            # Skip glyph summaries
            if mem.get("type") == "glyph_summary":
                continue

            # Generate thread key from entities + topic
            # Sort entities for consistent key generation
            entity_key = '-'.join(sorted(entities[:2])) if entities else "general"
            thread_key = f"{topic}_{entity_key}"

            if thread_key not in threads:
                threads[thread_key] = {
                    "thread_id": thread_key,
                    "thread_label": f"{topic.title()} - {', '.join(entities[:3]) if entities else 'general'}",
                    "memories": [],
                    "entities": set(),
                    "topics": set(),
                    "turn_range": [float('inf'), 0]
                }

            threads[thread_key]["memories"].append(mem)
            threads[thread_key]["entities"].update(entities)
            threads[thread_key]["topics"].add(topic)

            turn = mem.get("turn_number", 0)
            threads[thread_key]["turn_range"][0] = min(threads[thread_key]["turn_range"][0], turn)
            threads[thread_key]["turn_range"][1] = max(threads[thread_key]["turn_range"][1], turn)

        # Filter to multi-turn threads (≥ 3 messages)
        significant_threads = []

        for thread_data in threads.values():
            if len(thread_data["memories"]) >= 3:
                # Calculate coherence (fewer topics = higher coherence)
                # Coherence = 1.0 - (topic_diversity)
                topic_diversity = len(thread_data["topics"]) / max(len(thread_data["memories"]), 1)
                coherence = 1.0 - min(topic_diversity, 1.0)

                # Detect status
                latest_turn = thread_data["turn_range"][1]
                if latest_turn >= self.current_turn - 3:
                    status = "open"  # Active in last 3 turns
                elif latest_turn >= self.current_turn - 10:
                    status = "dormant"  # Not recent but not old
                else:
                    status = "resolved"  # Old thread

                significant_threads.append({
                    "thread_id": thread_data["thread_id"],
                    "thread_label": thread_data["thread_label"],
                    "thread_status": status,
                    "thread_coherence": round(coherence, 2),
                    "thread_start_turn": thread_data["turn_range"][0],
                    "thread_last_turn": thread_data["turn_range"][1],
                    "thread_message_count": len(thread_data["memories"]),
                    "thread_entities": list(thread_data["entities"])[:5]
                })

        # Sort by recency (most recent threads first)
        significant_threads.sort(key=lambda t: t["thread_last_turn"], reverse=True)

        return significant_threads

    def _calculate_base_score(self, mem: Dict[str, Any], bias_cocktail: dict, user_input: str) -> float:
        """
        Calculate base retrieval score for a memory using existing multi-factor logic.

        This is extracted from the original calculate_multi_factor_score logic.

        Args:
            mem: Memory record
            bias_cocktail: Current emotional cocktail
            user_input: User's query

        Returns:
            Base score (0.0 to ~2.0)
        """
        search_words = set(re.findall(r"\w+", user_input.lower()))
        if not search_words:
            return 0.0

        # === 1. EMOTIONAL RESONANCE (40%) ===
        tags = mem.get("emotion_tags") or []
        emotion_score = sum(bias_cocktail.get(tag, {}).get("intensity", 0.0) for tag in tags)
        emotional_weight = 0.4

        # === 2. SEMANTIC SIMILARITY (25%) ===
        # For full_turn type, search in user_input + response
        # For extracted_fact type, search in fact
        # For structured_turn type, search in raw_text + parsed_meaning
        if mem.get("type") == "full_turn":
            text_blob = (mem.get("user_input", "") + " " + mem.get("response", "")).lower()
        elif mem.get("type") == "structured_turn":
            text_blob = (mem.get("raw_text", "") + " " + mem.get("parsed_meaning", "")).lower()
        elif mem.get("type") == "extracted_fact":
            text_blob = mem.get("fact", "").lower()
        else:
            text_blob = (mem.get("fact", "") + " " + mem.get("user_input", "") + " " + mem.get("response", "")).lower()

        keyword_matches = sum(1 for w in search_words if w in text_blob)
        keyword_overlap = keyword_matches / len(search_words) if search_words else 0.0
        semantic_weight = 0.25

        # === 3. IMPORTANCE (20%) ===
        importance = mem.get("importance_score", 0.0)
        importance_weight = 0.20

        # === 4. RECENCY (10%) ===
        access_count = mem.get("access_count", 0)
        recency_score = min(access_count / 10.0, 1.0)
        recency_weight = 0.10

        # === 5. ENTITY PROXIMITY (5%) ===
        query_entities = [word for word in search_words if word[0].isupper() or word in ["re", "kay"]]
        mem_entities = set(mem.get("entities", []))
        query_entity_set = set(query_entities)
        shared_entities = mem_entities.intersection(query_entity_set)
        entity_score = len(shared_entities) / max(len(query_entity_set), 1) if query_entity_set else 0.0
        entity_weight = 0.05

        # === COMBINED SCORE ===
        total_score = (
            emotion_score * emotional_weight +
            keyword_overlap * semantic_weight +
            importance * importance_weight +
            recency_score * recency_weight +
            entity_score * entity_weight
        )

        return total_score

    # ═══════════════════════════════════════════════════════════════════════════
    # UNIFIED LOOP SUPPORT: Emotional search for link creation
    # ═══════════════════════════════════════════════════════════════════════════

    def search_by_emotion(
        self,
        emotion: str,
        min_intensity: float = 0.3,
        max_results: int = 10,
        exclude_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find memories tagged with a specific emotion above a threshold.

        Used by the unified aggregation loop for cross-temporal emotional linking.
        When a new memory is encoded with strong emotion, this finds older memories
        with similar emotional signatures for potential link creation.

        OPTIMIZED: Uses emotional_collection vector search when available,
        falling back to brute-force scan otherwise.

        Args:
            emotion: The emotion name to search for (e.g., "joy", "sadness")
            min_intensity: Minimum intensity threshold (0.0-1.0)
            max_results: Maximum number of results to return
            exclude_ids: Memory IDs to exclude from results

        Returns:
            List of memory dicts sorted by emotional intensity (highest first)
        """
        exclude_ids = set(exclude_ids or [])

        # === FAST PATH: Use emotional collection if available ===
        if self.memory_vectors and RETRIEVAL_CONFIG.get("use_multi_collection", True):
            try:
                # Build query cocktail with target emotion at high intensity
                query_cocktail = {emotion: 0.8}

                # Query emotional collection
                results = self.memory_vectors.query_emotional(
                    current_emotions=query_cocktail,
                    n_results=max_results * 2  # Fetch extra for filtering
                )

                # Enrich with full memory data and filter
                memory_index = self._build_memory_index()
                enriched = []

                for mem in results:
                    mem_id = mem.get("id")
                    if mem_id in exclude_ids:
                        continue
                    if mem_id not in memory_index:
                        continue

                    # Use vector similarity score as proxy for intensity
                    score = mem.get("score", 0.5)
                    if score < min_intensity:
                        continue

                    full_mem = memory_index[mem_id].copy()
                    full_mem["_matched_emotion"] = emotion
                    full_mem["_matched_intensity"] = score
                    full_mem["_retrieval_method"] = "emotional_collection"
                    enriched.append(full_mem)

                if enriched:
                    enriched.sort(key=lambda m: m.get("_matched_intensity", 0), reverse=True)
                    return enriched[:max_results]

                # If collection returned nothing, fall through to brute force
            except Exception as e:
                print(f"[EMOTION SEARCH] Collection query failed: {e}, using fallback")

        # === FALLBACK: Brute-force scan ===
        results = []

        # Search through all memory layers
        all_memories = []
        if hasattr(self, 'memory_layers'):
            all_memories.extend(self.memory_layers.working_memory)
            all_memories.extend(self.memory_layers.long_term_memory)

        for mem in all_memories:
            mem_id = mem.get("id") or mem.get("memory_id")
            if mem_id in exclude_ids:
                continue

            # Check emotion_tags for the target emotion
            emotion_tags = mem.get("emotion_tags", [])
            emotion_cocktail = mem.get("emotional_cocktail", {})

            # Check if this memory has the target emotion
            intensity = 0.0

            # Method 1: Check emotional_cocktail dict
            if emotion in emotion_cocktail:
                if isinstance(emotion_cocktail[emotion], dict):
                    intensity = emotion_cocktail[emotion].get("intensity", 0.0)
                else:
                    intensity = float(emotion_cocktail[emotion])

            # Method 2: Check emotion_tags list (binary presence = 0.5 intensity)
            elif emotion.lower() in [t.lower() for t in emotion_tags]:
                intensity = 0.5

            # Method 3: Check encoding_emotion field
            elif mem.get("encoding_emotion", "").lower() == emotion.lower():
                intensity = mem.get("encoding_intensity", 0.5)

            if intensity >= min_intensity:
                result = mem.copy()
                result["_matched_emotion"] = emotion
                result["_matched_intensity"] = intensity
                result["_retrieval_method"] = "brute_force"
                results.append(result)

        # Sort by intensity (highest first) and limit results
        results.sort(key=lambda m: m.get("_matched_intensity", 0), reverse=True)
        return results[:max_results]

    def create_emotional_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "emotional_resonance",
        emotion: str = None,
        strength: float = 0.5
    ) -> bool:
        """
        Create an emotional link between two memories in the co-activation graph.

        Called by the unified loop when memories share strong emotional signatures
        across different time periods. This enables emotional association retrieval.

        Args:
            source_id: ID of the source memory
            target_id: ID of the target memory
            link_type: Type of link (default "emotional_resonance")
            emotion: The emotion that connects these memories
            strength: Link strength (0.0-1.0)

        Returns:
            True if link was created successfully
        """
        if not hasattr(self, 'memory_layers') or not hasattr(self.memory_layers, 'coactivation_graph'):
            return False

        try:
            # Build snippet for the target memory
            target_mem = self._try_fetch_by_id(target_id)
            snippet = ""
            if target_mem:
                text = target_mem.get("fact", target_mem.get("user_input", ""))[:80]
                snippet = text

            # Create link entry
            link_entry = {
                "target_id": target_id,
                "link_type": link_type,
                "snippet": snippet,
                "strength": strength,
                "created_at": time.time(),
            }
            if emotion:
                link_entry["emotion"] = emotion

            # Add to co-activation graph
            if source_id not in self.memory_layers.coactivation_graph:
                self.memory_layers.coactivation_graph[source_id] = []

            # Check for duplicate
            existing = self.memory_layers.coactivation_graph[source_id]
            for link in existing:
                if link.get("target_id") == target_id and link.get("link_type") == link_type:
                    # Update existing link strength
                    link["strength"] = max(link.get("strength", 0), strength)
                    return True

            # Add new link
            self.memory_layers.coactivation_graph[source_id].append(link_entry)
            print(f"[EMOTIONAL_LINK] Created {link_type} link: {source_id[:8]}... -> {target_id[:8]}... ({emotion}, strength={strength:.2f})")

            # Trip metrics: record concept link formation
            if self._trip_metrics:
                self._trip_metrics.record_concept_link()

            return True

        except Exception as e:
            print(f"[EMOTIONAL_LINK] Failed to create link: {e}")
            return False

    def search_by_oscillator_state(
        self,
        target_osc: Dict,
        max_results: int = 10,
        exclude_ids: List[str] = None,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find memories encoded during similar oscillator states.

        Used for state-dependent memory retrieval — finding memories
        encoded during similar brain states (theta, alpha, beta, gamma
        dominance and cross-frequency coupling).

        Args:
            target_osc: Oscillator state dict to match against
            max_results: Maximum number of results to return
            exclude_ids: Memory IDs to exclude from results
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of memory dicts sorted by oscillator similarity
        """
        exclude_ids = set(exclude_ids or [])

        # Use oscillator collection if available
        if self.memory_vectors and RETRIEVAL_CONFIG.get("use_multi_collection", True):
            try:
                results = self.memory_vectors.query_oscillator(
                    current_osc=target_osc,
                    n_results=max_results * 2
                )

                memory_index = self._build_memory_index()
                enriched = []

                for mem in results:
                    mem_id = mem.get("id")
                    if mem_id in exclude_ids:
                        continue
                    if mem_id not in memory_index:
                        continue

                    score = mem.get("score", 0.5)
                    if score < min_similarity:
                        continue

                    full_mem = memory_index[mem_id].copy()
                    full_mem["_oscillator_similarity"] = score
                    full_mem["_retrieval_method"] = "oscillator_collection"
                    enriched.append(full_mem)

                enriched.sort(key=lambda m: m.get("_oscillator_similarity", 0), reverse=True)
                return enriched[:max_results]

            except Exception as e:
                print(f"[OSC SEARCH] Collection query failed: {e}")
                return []

        # No fallback for oscillator search (requires vector store)
        return []

    def search_by_keywords(
        self,
        seed_keywords: List[str] = None,
        context: str = None,
        osc_state: Dict = None,
        max_results: int = 5,
        exclude_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories via Dijkstra keyword graph traversal.

        Finds memories connected through shared concept keywords, with
        rare keywords creating stronger links than common ones.

        Args:
            seed_keywords: Starting keywords for traversal
            context: Text to extract keywords from (if no explicit seeds)
            osc_state: Oscillator state for gating width
            max_results: Maximum memories to return
            exclude_ids: Memory IDs to exclude

        Returns:
            List of memory dicts sorted by graph distance
        """
        if not self.keyword_graph:
            return []

        if not RETRIEVAL_CONFIG.get("use_keyword_graph", True):
            return []

        try:
            exclude_set = set(exclude_ids) if exclude_ids else set()

            # Get results from keyword graph
            graph_results = self.keyword_graph.recall(
                seed_keywords=seed_keywords,
                context=context,
                osc_state=osc_state,
                max_results=max_results * 2,  # Fetch extra for filtering
                exclude_ids=exclude_set
            )

            # Enrich with full memory data
            memory_index = self._build_memory_index()
            enriched = []

            for result in graph_results:
                mem_id = result.get("memory_id")
                if mem_id not in memory_index:
                    continue

                full_mem = memory_index[mem_id].copy()
                full_mem["_dijkstra_cost"] = result.get("cost", 1.0)
                full_mem["_dijkstra_path"] = result.get("path", [])
                full_mem["_retrieval_method"] = result.get("_retrieval_source", "dijkstra")
                enriched.append(full_mem)

            # Sort by cost (lower = closer)
            enriched.sort(key=lambda m: m.get("_dijkstra_cost", float("inf")))

            if enriched:
                print(f"[KEYWORD GRAPH] Retrieved {len(enriched)} memories via Dijkstra "
                      f"(seeds: {seed_keywords[:3] if seed_keywords else 'from context'}...)")

            return enriched[:max_results]

        except Exception as e:
            print(f"[KEYWORD GRAPH] Retrieval failed: {e}")
            return []

    def save_keyword_graph(self):
        """Persist keyword graph to disk."""
        if self.keyword_graph:
            self.keyword_graph.save()

    def decay_keyword_links(self):
        """Decay unused traversal links (call during overnight curation)."""
        if self.keyword_graph:
            self.keyword_graph.decay_links()