# shared/memory_vectors.py
"""
Multi-Collection Memory Vectors — Oscillator + Emotional Embedding Collections

"The oscillator state IS a vector. The emotional cocktail IS a vector."

Instead of custom BFS graph traversal, store these as SEPARATE EMBEDDING
COLLECTIONS in ChromaDB alongside the existing semantic embeddings. Then use
`$in` filters on co-activation link IDs to constrain queries to the memory's
neighborhood.

Three Embedding Collections:
- semantic: Text embeddings (existing, via sentence-transformers)
- oscillator_state: [delta, theta, alpha, beta, gamma, coherence, plv...]
- emotional: Emotional cocktail vector (fixed vocabulary)

Usage:
    store = MemoryVectorStore(persist_dir)

    # At encoding time:
    store.add_memory(memory_id, text, osc_state, emotional_cocktail)

    # At retrieval time:
    results = store.query_multi_collection(
        query_text="conversation context",
        current_osc=oscillator_state,
        current_emotions=emotional_cocktail,
        linked_ids=coactivation_ids  # $in filter
    )
"""

import os
import logging
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)

# Check for ChromaDB availability
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    log.warning("[MEMORY_VECTORS] ChromaDB not available")

# Check for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDER_AVAILABLE = True
except ImportError:
    EMBEDDER_AVAILABLE = False
    log.warning("[MEMORY_VECTORS] sentence-transformers not available")


# ═══════════════════════════════════════════════════════════════════════════
# EMOTION VOCABULARY — Fixed dimensions for consistent vector embeddings
# ═══════════════════════════════════════════════════════════════════════════

EMOTION_VOCAB = [
    # Primary emotions (ULTRAMAP)
    "curiosity", "warmth", "frustration", "excitement", "confusion",
    "calm", "anxiety", "joy", "sadness", "surprise", "anger",
    "contempt", "fear", "love", "pride", "shame", "guilt",
    "awe", "gratitude", "loneliness",
    # Secondary emotions (from Kay/Reed's emotional landscape)
    "tenderness", "playfulness", "nostalgia", "contentment", "irritation",
    "wonder", "melancholy", "determination", "peace", "longing",
    # Somatic states (body-feel)
    "tension", "relaxation", "alertness", "fatigue", "restlessness",
]  # 35 dimensions

# Map common variations to canonical names
EMOTION_ALIASES = {
    "happy": "joy",
    "sad": "sadness",
    "afraid": "fear",
    "angry": "anger",
    "scared": "fear",
    "worried": "anxiety",
    "nervous": "anxiety",
    "interested": "curiosity",
    "curious": "curiosity",
    "loving": "love",
    "warm": "warmth",
    "peaceful": "peace",
    "content": "contentment",
    "frustrated": "frustration",
    "excited": "excitement",
    "confused": "confusion",
    "grateful": "gratitude",
    "proud": "pride",
    "ashamed": "shame",
    "guilty": "guilt",
    "lonely": "loneliness",
    "tender": "tenderness",
    "playful": "playfulness",
    "nostalgic": "nostalgia",
    "irritated": "irritation",
    "determined": "determination",
    "melancholic": "melancholy",
    "awed": "awe",
    "wondrous": "wonder",
    "tense": "tension",
    "relaxed": "relaxation",
    "alert": "alertness",
    "tired": "fatigue",
    "fatigued": "fatigue",
    "restless": "restlessness",
}


# ═══════════════════════════════════════════════════════════════════════════
# VECTOR BUILDING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def build_oscillator_vector(osc_state: Dict) -> List[float]:
    """
    Convert oscillator state to an 8-dimensional embedding vector.

    Args:
        osc_state: Dict with band power, coherence, plv values
                   From _get_oscillator_state() or osc_encoding

    Returns:
        8-element vector: [delta, theta, alpha, beta, gamma, coherence,
                          theta_gamma_plv, beta_gamma_plv]
    """
    if not osc_state:
        # Neutral default (alpha-dominant, moderate coherence)
        return [0.1, 0.2, 0.4, 0.2, 0.1, 0.5, 0.3, 0.3]

    # Handle both band_power dict and direct band string
    band_power = osc_state.get("band_power", {})
    if not band_power:
        # Convert band string to approximate power distribution
        band = osc_state.get("band", "alpha")
        band_power = _band_to_power_distribution(band)

    # Extract PLV values (cross-frequency coupling)
    plv = osc_state.get("cross_band_plv", {})
    if not plv:
        plv = osc_state.get("plv", {})

    return [
        band_power.get("delta", 0.1),
        band_power.get("theta", 0.2),
        band_power.get("alpha", 0.4),
        band_power.get("beta", 0.2),
        band_power.get("gamma", 0.1),
        osc_state.get("coherence", osc_state.get("global_coherence", 0.5)),
        plv.get("theta_gamma", 0.3),
        plv.get("beta_gamma", 0.3),
    ]


def _band_to_power_distribution(band: str) -> Dict[str, float]:
    """Convert a dominant band string to approximate power distribution."""
    distributions = {
        "delta": {"delta": 0.5, "theta": 0.25, "alpha": 0.15, "beta": 0.07, "gamma": 0.03},
        "theta": {"delta": 0.2, "theta": 0.45, "alpha": 0.2, "beta": 0.1, "gamma": 0.05},
        "alpha": {"delta": 0.1, "theta": 0.2, "alpha": 0.45, "beta": 0.15, "gamma": 0.1},
        "beta": {"delta": 0.05, "theta": 0.1, "alpha": 0.2, "beta": 0.45, "gamma": 0.2},
        "gamma": {"delta": 0.03, "theta": 0.07, "alpha": 0.15, "beta": 0.25, "gamma": 0.5},
    }
    return distributions.get(band, distributions["alpha"])


def build_emotion_vector(emotional_cocktail: Dict) -> List[float]:
    """
    Convert emotional cocktail to a fixed-dimension embedding vector.

    Args:
        emotional_cocktail: Dict of emotion -> intensity (or emotion -> {intensity: x})

    Returns:
        35-element vector (len(EMOTION_VOCAB)) with intensities
    """
    vector = []
    for emotion in EMOTION_VOCAB:
        # Try direct match
        val = emotional_cocktail.get(emotion)

        # Try lowercase
        if val is None:
            val = emotional_cocktail.get(emotion.lower())

        # Try aliases
        if val is None:
            for alias, canonical in EMOTION_ALIASES.items():
                if canonical == emotion and alias in emotional_cocktail:
                    val = emotional_cocktail[alias]
                    break

        # Extract intensity from dict or use direct value
        if isinstance(val, dict):
            intensity = val.get("intensity", 0.0)
        elif isinstance(val, (int, float)):
            intensity = float(val)
        else:
            intensity = 0.0

        vector.append(min(1.0, max(0.0, intensity)))  # Clamp to [0, 1]

    return vector


def normalize_vector(vector: List[float]) -> List[float]:
    """L2 normalize a vector for cosine similarity."""
    import math
    magnitude = math.sqrt(sum(x * x for x in vector))
    if magnitude < 1e-10:
        return vector
    return [x / magnitude for x in vector]


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-COLLECTION MEMORY STORE
# ═══════════════════════════════════════════════════════════════════════════

class MemoryVectorStore:
    """
    Multi-collection ChromaDB store for memory embeddings.

    Three collections:
    - semantic: Text embeddings via sentence-transformers
    - oscillator: Oscillator state vectors (8 dims)
    - emotional: Emotional cocktail vectors (35 dims)

    All three use the same memory IDs, enabling cross-collection queries
    with $in filters on co-activation link IDs.
    """

    def __init__(self, persist_directory: str, entity: str = "kay"):
        """
        Initialize multi-collection vector store.

        Args:
            persist_directory: Path to ChromaDB persistence directory
            entity: Entity name for collection naming (kay, reed, etc.)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not installed. Run: pip install chromadb")

        self.persist_directory = persist_directory
        self.entity = entity
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize sentence-transformers embedder (for semantic collection)
        self.embedder = None
        if EMBEDDER_AVAILABLE:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                log.info(f"[MEMORY_VECTORS] Embedder loaded for {entity}")
            except Exception as e:
                log.warning(f"[MEMORY_VECTORS] Could not load embedder: {e}")

        # Get or create the three collections
        self.semantic_collection = self.client.get_or_create_collection(
            name=f"{entity}_memories_semantic",
            metadata={"hnsw:space": "cosine", "description": "Text embeddings"}
        )

        self.oscillator_collection = self.client.get_or_create_collection(
            name=f"{entity}_memories_oscillator",
            metadata={"hnsw:space": "cosine", "description": "Oscillator state vectors"}
        )

        self.emotional_collection = self.client.get_or_create_collection(
            name=f"{entity}_memories_emotional",
            metadata={"hnsw:space": "cosine", "description": "Emotional cocktail vectors"}
        )

        log.info(f"[MEMORY_VECTORS] Initialized for {entity}: "
                 f"semantic={self.semantic_collection.count()}, "
                 f"oscillator={self.oscillator_collection.count()}, "
                 f"emotional={self.emotional_collection.count()}")

    def add_memory(
        self,
        memory_id: str,
        text: str,
        osc_state: Dict = None,
        emotional_cocktail: Dict = None,
        metadata: Dict = None
    ) -> bool:
        """
        Store a memory in all three collections simultaneously.

        Args:
            memory_id: Unique ID for this memory
            text: Text content for semantic embedding
            osc_state: Oscillator state dict for oscillator embedding
            emotional_cocktail: Emotional cocktail dict for emotional embedding
            metadata: Additional metadata to store

        Returns:
            True if stored successfully
        """
        try:
            base_metadata = metadata or {}
            base_metadata["memory_id"] = memory_id

            # Collection 1: Semantic (text embedding)
            if self.embedder and text:
                embedding = self.embedder.encode(text).tolist()
                self.semantic_collection.upsert(
                    ids=[memory_id],
                    embeddings=[embedding],
                    metadatas=[base_metadata],
                    documents=[text[:1000]]  # Store truncated text as document
                )

            # Collection 2: Oscillator state
            if osc_state:
                osc_vector = normalize_vector(build_oscillator_vector(osc_state))
                self.oscillator_collection.upsert(
                    ids=[memory_id],
                    embeddings=[osc_vector],
                    metadatas=[base_metadata]
                )

            # Collection 3: Emotional
            if emotional_cocktail:
                emo_vector = normalize_vector(build_emotion_vector(emotional_cocktail))
                self.emotional_collection.upsert(
                    ids=[memory_id],
                    embeddings=[emo_vector],
                    metadatas=[base_metadata]
                )

            return True

        except Exception as e:
            log.warning(f"[MEMORY_VECTORS] Failed to add memory {memory_id}: {e}")
            return False

    def query_semantic(
        self,
        query_text: str,
        n_results: int = 10,
        where_filter: Dict = None
    ) -> List[Dict]:
        """
        Query semantic collection by text similarity.

        Args:
            query_text: Text to find similar memories for
            n_results: Number of results to return
            where_filter: Optional ChromaDB where filter (e.g., {"id": {"$in": ids}})

        Returns:
            List of memory dicts with id, text, score, metadata
        """
        if not self.embedder:
            return []

        try:
            query_embedding = self.embedder.encode(query_text).tolist()

            kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
            }
            if where_filter:
                kwargs["where"] = where_filter

            results = self.semantic_collection.query(**kwargs)

            return self._format_results(results, "semantic")

        except Exception as e:
            log.warning(f"[MEMORY_VECTORS] Semantic query failed: {e}")
            return []

    def query_oscillator(
        self,
        current_osc: Dict,
        n_results: int = 5,
        where_filter: Dict = None
    ) -> List[Dict]:
        """
        Query oscillator collection by state similarity.

        Args:
            current_osc: Current oscillator state dict
            n_results: Number of results to return
            where_filter: Optional ChromaDB where filter

        Returns:
            List of memory dicts with id, score, metadata
        """
        try:
            osc_vector = normalize_vector(build_oscillator_vector(current_osc))

            kwargs = {
                "query_embeddings": [osc_vector],
                "n_results": n_results,
            }
            if where_filter:
                kwargs["where"] = where_filter

            results = self.oscillator_collection.query(**kwargs)

            return self._format_results(results, "oscillator")

        except Exception as e:
            log.warning(f"[MEMORY_VECTORS] Oscillator query failed: {e}")
            return []

    def query_emotional(
        self,
        current_emotions: Dict,
        n_results: int = 5,
        where_filter: Dict = None
    ) -> List[Dict]:
        """
        Query emotional collection by feeling similarity.

        Args:
            current_emotions: Current emotional cocktail dict
            n_results: Number of results to return
            where_filter: Optional ChromaDB where filter

        Returns:
            List of memory dicts with id, score, metadata
        """
        try:
            emo_vector = normalize_vector(build_emotion_vector(current_emotions))

            kwargs = {
                "query_embeddings": [emo_vector],
                "n_results": n_results,
            }
            if where_filter:
                kwargs["where"] = where_filter

            results = self.emotional_collection.query(**kwargs)

            return self._format_results(results, "emotional")

        except Exception as e:
            log.warning(f"[MEMORY_VECTORS] Emotional query failed: {e}")
            return []

    def query_multi_collection(
        self,
        query_text: str = None,
        current_osc: Dict = None,
        current_emotions: Dict = None,
        linked_ids: List[str] = None,
        semantic_k: int = 5,
        oscillator_k: int = 3,
        emotional_k: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Query all three collections, optionally filtered to linked IDs.

        This is the main retrieval method. Linked IDs come from co-activation
        links on the semantic entry points, constraining oscillator and
        emotional queries to the memory's neighborhood.

        Args:
            query_text: Text for semantic search (entry points)
            current_osc: Oscillator state for state-dependent retrieval
            current_emotions: Emotional state for feeling-based retrieval
            linked_ids: Co-activation link IDs for $in filtering
            semantic_k: Number of semantic results
            oscillator_k: Number of oscillator results
            emotional_k: Number of emotional results

        Returns:
            Dict with keys: semantic, oscillator, emotional, merged
            Each contains list of memory dicts
        """
        results = {
            "semantic": [],
            "oscillator": [],
            "emotional": [],
            "merged": []
        }

        # Build where filter for linked IDs
        link_filter = None
        if linked_ids:
            link_filter = {"memory_id": {"$in": linked_ids}}

        # Query semantic (entry points, no filter)
        if query_text:
            results["semantic"] = self.query_semantic(
                query_text,
                n_results=semantic_k
            )

        # Query oscillator (filtered to links if provided)
        if current_osc:
            results["oscillator"] = self.query_oscillator(
                current_osc,
                n_results=oscillator_k,
                where_filter=link_filter
            )

        # Query emotional (filtered to links if provided)
        if current_emotions:
            results["emotional"] = self.query_emotional(
                current_emotions,
                n_results=emotional_k,
                where_filter=link_filter
            )

        # Merge and deduplicate
        seen_ids = set()
        for source in ["semantic", "oscillator", "emotional"]:
            for mem in results[source]:
                mem_id = mem.get("id")
                if mem_id and mem_id not in seen_ids:
                    mem["_retrieval_source"] = source
                    results["merged"].append(mem)
                    seen_ids.add(mem_id)

        return results

    def _format_results(self, raw_results: Dict, source: str) -> List[Dict]:
        """Format ChromaDB results into memory dicts."""
        memories = []

        if not raw_results or not raw_results.get("ids"):
            return memories

        ids = raw_results["ids"][0] if raw_results["ids"] else []
        distances = raw_results.get("distances", [[]])[0]
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]

        for i, mem_id in enumerate(ids):
            mem = {
                "id": mem_id,
                "score": 1.0 - distances[i] if i < len(distances) else 0.0,
                "_retrieval_source": source,
            }
            if i < len(documents) and documents[i]:
                mem["text"] = documents[i]
            if i < len(metadatas) and metadatas[i]:
                mem.update(metadatas[i])
            memories.append(mem)

        return memories

    def get_collection_stats(self) -> Dict[str, int]:
        """Get counts for all three collections."""
        return {
            "semantic": self.semantic_collection.count(),
            "oscillator": self.oscillator_collection.count(),
            "emotional": self.emotional_collection.count(),
        }

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from all three collections."""
        try:
            self.semantic_collection.delete(ids=[memory_id])
            self.oscillator_collection.delete(ids=[memory_id])
            self.emotional_collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            log.warning(f"[MEMORY_VECTORS] Failed to delete {memory_id}: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════
# RETRIEVAL CONFIG
# ═══════════════════════════════════════════════════════════════════════════

MULTI_COLLECTION_CONFIG = {
    # Collection queries
    "use_semantic": True,              # Standard text similarity
    "use_oscillator_collection": True, # State-dependent retrieval
    "use_emotional_collection": True,  # Emotion-based retrieval

    # $in filtering
    "filter_by_links": True,           # Constrain osc/emo queries to linked IDs
    "include_unlinked": False,         # Also search outside links (wider net)

    # Results per collection
    "semantic_top_k": 5,
    "oscillator_top_k": 3,
    "emotional_top_k": 3,
    "final_max": 12,
}
