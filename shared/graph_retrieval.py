# shared/graph_retrieval.py
"""
Unified Aggregation + Linking Loop: Graph Retrieval Components

"In the moment: aggregation. In memory: linking. One flow."

This module provides the bridge between real-time sensory aggregation
(oscillator) and memory linking (co-activation graph). The key insight:
these aren't two separate phases, they're one continuous loop running
at different speeds.

Components:
- GraphActivationCache: Small in-RAM buffer of currently-activated memories
- MediumLoopWorker: Background thread that refreshes the cache based on
  cognitive state changes (band shifts)
- Emotional link creation utilities

The three-tier architecture:
- TIER 1 (Fast, every 10-15s): Read cache, apply gentle oscillator pressure
- TIER 2 (Medium, every 30-60s or on band shift): Refresh cache via graph walk
- TIER 3 (Slow, per turn): Full retrieval pipeline + link formation
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Optional: Keyword graph for Dijkstra associative retrieval
try:
    from shared.keyword_graph import (
        extract_keywords_from_context,
        get_gating_width,
        DIJKSTRA_CONFIG,
    )
    KEYWORD_GRAPH_AVAILABLE = True
except ImportError:
    KEYWORD_GRAPH_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

UNIFIED_LOOP_CONFIG = {
    # Tier 1: Fast loop
    "cache_pressure_scale": 0.01,    # How strongly cached memories push oscillator
    "show_associative_echo": True,   # Include snippet in felt state
    "max_cache_age": 120.0,          # Seconds before cache considered stale

    # Tier 2: Medium loop
    "medium_loop_enabled": True,
    "medium_loop_interval": 45.0,    # Seconds between timer-triggered refreshes
    "trigger_on_band_shift": True,   # Refresh on dominant band change
    "graph_max_depth": 2,
    "graph_max_cached": 15,
    "check_interval": 5.0,           # How often to check for triggers

    # HOTFIX: Debounce to prevent flicker-triggered rapid refreshes
    "min_refresh_interval": 15.0,    # Minimum seconds between ANY refreshes
    "band_stability_time": 10.0,     # Band must be stable this long before triggering

    # Tier 3: Emotional links
    "create_emotional_links": True,
    "emotional_link_threshold": 0.5, # Min intensity to create cross-temporal link
    "emotional_link_max": 3,         # Max emotional links per turn

    # Dijkstra keyword graph (lazy link construction)
    "use_dijkstra_in_medium_loop": True,  # Include Dijkstra results in cache refresh
    "dijkstra_max_results": 5,            # Max memories from Dijkstra per refresh

    # Consciousness stream integration
    "stream_associative_thoughts": True,  # Let stream reference cache
}


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: GRAPH ACTIVATION CACHE (Fast Loop Component)
# ═══════════════════════════════════════════════════════════════════════════

class GraphActivationCache:
    """
    Small in-RAM buffer of memories activated by the current
    oscillator state. Populated async by the medium loop.
    Read synchronously by the fast loop.

    This is the bridge between slow graph traversal and fast
    interoception ticks. The medium loop populates it, the fast
    loop reads it without blocking.

    Usage:
        cache = GraphActivationCache()

        # Fast loop reads (every interoception tick):
        memories = cache.get_active_memories()
        pressure = cache.get_emotional_pressure()
        snippet = cache.get_top_snippet()

        # Medium loop writes (async, on band shift):
        cache.update(new_memories, current_band)
    """

    def __init__(self, max_size: int = 15):
        self.max_size = max_size
        self.memories: List[Dict] = []
        self.last_updated: float = 0.0
        self.activated_band: str = ""  # Which band triggered this cache fill
        self.lock = threading.Lock()

        # Statistics for debugging
        self.total_updates = 0
        self.total_reads = 0

    def get_active_memories(self) -> List[Dict]:
        """
        Read current cache (thread-safe, non-blocking).

        Returns a COPY of the cached memories to prevent
        modification issues between threads.
        """
        with self.lock:
            self.total_reads += 1
            return list(self.memories)

    def update(self, memories: List[Dict], band: str):
        """
        Replace cache contents (called by medium loop).

        Args:
            memories: New memories to cache (will be truncated to max_size)
            band: The oscillator band that triggered this update
        """
        with self.lock:
            self.memories = memories[:self.max_size]
            self.last_updated = time.time()
            self.activated_band = band
            self.total_updates += 1

    def clear(self):
        """Clear the cache (e.g., on sleep state entry)."""
        with self.lock:
            self.memories = []
            self.activated_band = ""

    def inject_memory(self, memory: Dict):
        """Inject a single memory into the cache (for novelty/anti-rumination).
        Replaces the oldest entry if cache is full."""
        with self.lock:
            if len(self.memories) >= self.max_size:
                self.memories.pop(0)  # Remove oldest
            self.memories.append(memory)
            self.last_updated = time.time()

    def is_stale(self, max_age: float = None) -> bool:
        """Check if cache is too old to be useful."""
        max_age = max_age or UNIFIED_LOOP_CONFIG.get("max_cache_age", 120.0)
        with self.lock:
            if not self.memories:
                return True
            return (time.time() - self.last_updated) > max_age

    def get_emotional_pressure(self) -> Dict[str, float]:
        """
        Aggregate emotional signatures from cached memories
        into gentle oscillator pressure.

        Returns band pressures derived from cached memories'
        encoding states. These are VERY gentle - just a subtle
        pull toward the cognitive state in which similar memories
        were formed.

        Returns:
            Dict of band -> pressure value (only non-zero bands)
        """
        with self.lock:
            if not self.memories:
                return {}

            scale = UNIFIED_LOOP_CONFIG.get("cache_pressure_scale", 0.01)

            pressure = {
                "delta": 0.0,
                "theta": 0.0,
                "alpha": 0.0,
                "beta": 0.0,
                "gamma": 0.0
            }

            # Only use top 5 memories to avoid overwhelming
            for mem in self.memories[:5]:
                osc = mem.get("osc_state", mem.get("osc_encoding", {}))
                if not osc:
                    continue

                # Each cached memory gently pulls toward its encoding state
                encoding_band = osc.get("band", "alpha")
                if encoding_band in pressure:
                    pressure[encoding_band] += scale

                # Also consider band_power if available
                band_power = osc.get("band_power", {})
                for band, power in band_power.items():
                    if band in pressure and isinstance(power, (int, float)):
                        pressure[band] += power * scale * 0.5

            # Filter out negligible pressures
            return {b: round(v, 4) for b, v in pressure.items() if v > 0.005}

    def get_top_snippet(self) -> str:
        """
        Get the most relevant cached memory's snippet for felt-state.

        This becomes the "associative echo" - a faint trace of
        what's surfacing from memory, available to the consciousness
        stream for generating thoughts like "something about
        that conversation keeps surfacing..."
        """
        with self.lock:
            if not self.memories:
                return ""

            top = self.memories[0]
            # Try multiple fields for the snippet
            snippet = (
                top.get("snippet") or
                top.get("fact") or
                top.get("text") or
                top.get("user_input", "")
            )
            return str(snippet)[:100] if snippet else ""

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics for debugging."""
        with self.lock:
            return {
                "size": len(self.memories),
                "max_size": self.max_size,
                "activated_band": self.activated_band,
                "age_seconds": time.time() - self.last_updated if self.last_updated else None,
                "total_updates": self.total_updates,
                "total_reads": self.total_reads,
                "is_stale": self.is_stale(),
            }


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: MEDIUM LOOP WORKER (Background Cache Refresher)
# ═══════════════════════════════════════════════════════════════════════════

class MediumLoopWorker:
    """
    Background worker that refreshes the graph activation cache
    based on current oscillator state.

    Runs async. Non-blocking. Fires on band shift or timer.

    The medium loop is the bridge between:
    - The oscillator's current cognitive state
    - The memory graph's neighborhood of relevant memories

    When cognitive state changes (beta -> alpha), different memory
    neighborhoods become relevant. The medium loop detects this
    and refreshes the cache so the fast loop has fresh material.

    Usage:
        worker = MediumLoopWorker(
            graph_cache=cache,
            memory_engine=memory,
            get_oscillator_state=lambda: resonance.engine.get_state(),
            get_felt_summary=lambda: interoception.get_felt_summary()
        )
        worker.start()
        # ... later ...
        worker.stop()
    """

    def __init__(
        self,
        graph_cache: GraphActivationCache,
        memory_engine,  # MemoryEngine instance
        get_oscillator_state: Callable[[], Any],
        get_felt_summary: Callable[[], str] = None,
        interval: float = None
    ):
        self.cache = graph_cache
        self.memory = memory_engine
        self.get_osc_state = get_oscillator_state
        self.get_felt = get_felt_summary or (lambda: "")
        self.interval = interval or UNIFIED_LOOP_CONFIG.get("medium_loop_interval", 45.0)

        self._last_band = ""
        self._last_run = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sleep_state = None  # Track sleep state to throttle during sleep

        # HOTFIX: Band stability tracking for debounce
        self._band_changed_at = 0.0  # When current band was first detected
        self._pending_band = ""      # Band we're waiting to stabilize

        # Statistics
        self.total_refreshes = 0
        self.band_shift_refreshes = 0
        self.timer_refreshes = 0
        self.debounced_refreshes = 0  # Refreshes skipped due to debounce

    def start(self):
        """Start the background loop."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="MediumLoopWorker")
        self._thread.start()
        log.info("[GRAPH:MEDIUM] Background worker started")

    def stop(self):
        """Stop the background loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        log.info("[GRAPH:MEDIUM] Background worker stopped")

    def set_sleep_state(self, state: str):
        """
        Update sleep state tracking. Throttle during NREM/REM.

        During sleep, we don't want to activate random memory
        neighborhoods - that's what dreams are for.
        """
        self._sleep_state = state

    def force_refresh(self):
        """Manually trigger a cache refresh (for testing/debugging)."""
        try:
            osc_state = self.get_osc_state()
            current_band = self._extract_band(osc_state)
            self._refresh_cache(osc_state, current_band)
        except Exception as e:
            log.warning(f"[GRAPH:MEDIUM] Force refresh failed: {e}")

    def _loop(self):
        """Main background loop."""
        check_interval = UNIFIED_LOOP_CONFIG.get("check_interval", 5.0)

        while self._running:
            try:
                # Skip during sleep states
                if self._sleep_state in ("NREM", "REM", "DEEP_REST"):
                    time.sleep(check_interval)
                    continue

                osc_state = self.get_osc_state()
                current_band = self._extract_band(osc_state)
                now = time.time()

                # HOTFIX: Debounce parameters
                min_refresh_interval = UNIFIED_LOOP_CONFIG.get("min_refresh_interval", 15.0)
                band_stability_time = UNIFIED_LOOP_CONFIG.get("band_stability_time", 10.0)

                # Check if minimum refresh interval has passed
                time_since_last = now - self._last_run
                can_refresh = time_since_last >= min_refresh_interval

                # Track band stability
                if current_band != self._pending_band:
                    # Band changed - start stability timer
                    self._pending_band = current_band
                    self._band_changed_at = now

                # Calculate how long this band has been stable
                band_stable_for = now - self._band_changed_at

                # Band shift detection with stability check
                band_shifted = (
                    UNIFIED_LOOP_CONFIG.get("trigger_on_band_shift", True) and
                    current_band != self._last_band and
                    self._last_band != "" and  # Don't trigger on first run
                    band_stable_for >= band_stability_time  # Must be stable
                )
                timer_elapsed = time_since_last > self.interval

                if band_shifted and can_refresh:
                    log.info(f"[GRAPH:MEDIUM] Band shift {self._last_band} -> {current_band} (stable {band_stable_for:.1f}s): refreshing")
                    self._refresh_cache(osc_state, current_band)
                    self._last_band = current_band
                    self._last_run = now
                    self.band_shift_refreshes += 1

                elif band_shifted and not can_refresh:
                    # Debounced - skip this refresh
                    log.debug(f"[GRAPH:MEDIUM] Band shift debounced (only {time_since_last:.1f}s since last refresh)")
                    self.debounced_refreshes += 1
                    # Still update band tracking so we don't re-trigger
                    self._last_band = current_band

                elif timer_elapsed and can_refresh:
                    log.debug(f"[GRAPH:MEDIUM] Timer elapsed: refreshing for {current_band}")
                    self._refresh_cache(osc_state, current_band)
                    self._last_band = current_band
                    self._last_run = now
                    self.timer_refreshes += 1

                else:
                    # Just update band tracking without refresh
                    if current_band != self._last_band and band_stable_for >= band_stability_time:
                        self._last_band = current_band

            except Exception as e:
                log.warning(f"[GRAPH:MEDIUM] Loop error: {e}")

            time.sleep(check_interval)

    def _extract_band(self, osc_state) -> str:
        """Extract dominant band from oscillator state."""
        if osc_state is None:
            return "alpha"

        # Handle different state formats
        if hasattr(osc_state, 'dominant_band'):
            return osc_state.dominant_band
        if isinstance(osc_state, dict):
            return osc_state.get("band", osc_state.get("dominant_band", "alpha"))

        return "alpha"

    def _refresh_cache(self, osc_state, band: str):
        """
        Find memories relevant to current cognitive state
        and populate the cache.
        """
        self.total_refreshes += 1

        # Step 1: Build state query from current felt-state
        entry_query = self._build_state_query(osc_state, band)

        # Step 2: Find entry points
        entry_points = []
        if entry_query and hasattr(self.memory, 'vector_store') and self.memory.vector_store:
            try:
                # One small ChromaDB query (50-100ms)
                results = self.memory.vector_store.query(
                    query_text=entry_query,
                    n_results=5
                )
                entry_points = results if results else []
            except Exception as e:
                log.debug(f"[GRAPH:MEDIUM] ChromaDB query failed: {e}")

        # Fallback: use recent memories from working memory
        if not entry_points and hasattr(self.memory, 'memory_layers'):
            entry_points = list(self.memory.memory_layers.working_memory[-5:])

        if not entry_points:
            log.debug("[GRAPH:MEDIUM] No entry points found")
            return

        # Step 3: Graph walk from entry points (if graph retrieval available)
        neighborhood = entry_points

        if hasattr(self.memory, 'retrieve_graph_neighborhood'):
            try:
                source_filter = self._source_filter_for_band(band)
                neighborhood = self.memory.retrieve_graph_neighborhood(
                    entry_memories=entry_points,
                    max_depth=UNIFIED_LOOP_CONFIG.get("graph_max_depth", 2),
                    max_total=UNIFIED_LOOP_CONFIG.get("graph_max_cached", 15),
                    source_filter=source_filter,
                    use_snippets=False  # Skip snippet filtering for cache population
                )
            except Exception as e:
                log.debug(f"[GRAPH:MEDIUM] Graph traversal failed: {e}")
                neighborhood = entry_points

        # Step 3b: Dijkstra keyword graph traversal (if available)
        # Adds associative memories connected through shared concepts
        if (KEYWORD_GRAPH_AVAILABLE and
            UNIFIED_LOOP_CONFIG.get("use_dijkstra_in_medium_loop", True) and
            hasattr(self.memory, 'search_by_keywords')):
            try:
                # Extract keywords from RECENT MEMORY CONTENT, not felt-state
                # Felt-state gives emotional descriptors ("settled, accompanied")
                # which don't match content keywords ("lemon", "chrome", "trial")
                # Working memory has the actual conversation topics
                recent_content = ""
                if hasattr(self.memory, 'memory_layers'):
                    for mem in list(self.memory.memory_layers.working_memory)[-5:]:
                        # Try multiple content fields in priority order
                        # Avoid metadata fields like "caption", "update_time"
                        text = ""
                        for field in ["user_input", "response", "fact", "text", "content"]:
                            val = mem.get(field)
                            if val and isinstance(val, str) and len(val) > 10:
                                text = val
                                break
                        if text:
                            recent_content += " " + text[:200]

                # Also include entry point content (from ChromaDB results)
                for ep in entry_points[:3]:
                    text = ""
                    for field in ["fact", "text", "content", "user_input", "response"]:
                        val = ep.get(field)
                        if val and isinstance(val, str) and len(val) > 10:
                            text = val
                            break
                    if text:
                        recent_content += " " + text[:150]

                seed_keywords = extract_keywords_from_context(recent_content) if recent_content.strip() else []

                if seed_keywords:
                    log.info(f"[GRAPH:DIJKSTRA] Seed keywords from recent content: {seed_keywords[:5]}")

                    # Get gating width from oscillator state
                    gating_width = get_gating_width(osc_state) if osc_state else 0.5

                    # Get existing IDs to avoid duplicates
                    existing_ids = {m.get("id") for m in neighborhood if m.get("id")}

                    # Dijkstra traversal
                    dijkstra_results = self.memory.search_by_keywords(
                        seed_keywords=seed_keywords,
                        osc_state=osc_state,
                        max_results=UNIFIED_LOOP_CONFIG.get("dijkstra_max_results", 5),
                        exclude_ids=list(existing_ids)
                    )

                    # Merge with neighborhood
                    if dijkstra_results:
                        neighborhood.extend(dijkstra_results)
                        log.info(f"[GRAPH:DIJKSTRA] Added {len(dijkstra_results)} memories "
                                 f"(seeds: {seed_keywords[:3]})")
                else:
                    log.debug(f"[GRAPH:DIJKSTRA] No seed keywords extracted (content length: {len(recent_content.strip())})")

            except Exception as e:
                log.warning(f"[GRAPH:DIJKSTRA] Traversal failed: {e}")

        # Step 4: Update cache
        self.cache.update(neighborhood, band)
        log.info(f"[GRAPH:MEDIUM] Cache refreshed: {len(neighborhood)} memories for {band}-dominant state")

    def _build_state_query(self, osc_state, band: str) -> str:
        """
        Build a retrieval query from current cognitive state.
        Not a conversation query - a STATE query.
        """
        # Use the felt-state description as the query
        felt = self.get_felt()
        if felt and len(felt) > 10:
            return felt

        # Fallback: use band name as crude query
        band_queries = {
            "delta": "rest sleep deep quiet peaceful",
            "theta": "reflection contemplation memory emotion feeling",
            "alpha": "relaxed awareness creative calm present",
            "beta": "focused active working task engaged",
            "gamma": "intense engaged concentrated binding insight",
        }
        return band_queries.get(band, "awareness present moment")

    def _source_filter_for_band(self, band: str) -> Optional[List[str]]:
        """
        Different cognitive states favor different link types.
        This is the bridge between aggregation and linking.

        Reflective states (theta/alpha) -> emotional and episodic links
        "What did I FEEL when this happened before?"

        Active states (beta/gamma) -> factual and document links
        "What INFORMATION is relevant to what I'm doing?"
        """
        if band in ("theta", "delta"):
            # Reflective states -> emotional and episodic links
            return ["memory_layer", "oscillator_match", "emotional_match"]
        elif band in ("beta", "gamma"):
            # Active states -> factual and document links
            return ["memory_layer", "vector_store"]
        else:
            # Alpha (balanced) -> all link types
            return None  # No filter

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics for debugging."""
        return {
            "running": self._running,
            "last_band": self._last_band,
            "sleep_state": self._sleep_state,
            "total_refreshes": self.total_refreshes,
            "band_shift_refreshes": self.band_shift_refreshes,
            "timer_refreshes": self.timer_refreshes,
            "interval": self.interval,
        }


# ═══════════════════════════════════════════════════════════════════════════
# TIER 3: EMOTIONAL LINK CREATION (Cross-Temporal)
# ═══════════════════════════════════════════════════════════════════════════

def create_emotional_links(
    new_memory: Dict,
    memory_engine,
    emotional_cocktail: Dict,
    current_session_id: str = None,
    max_links: int = None
) -> List[Dict]:
    """
    Find memories with similar emotional profiles and create
    cross-temporal emotional links.

    "This moment of curiosity connects to that other moment of
    curiosity from three weeks ago."

    This creates the retrieval pathway for "remember a time when you felt ___"

    Args:
        new_memory: The memory being stored
        memory_engine: MemoryEngine instance with search_by_emotion method
        emotional_cocktail: Current emotional state {emotion: {intensity, ...}}
        current_session_id: Session to exclude from search
        max_links: Maximum emotional links to create

    Returns:
        List of emotional link dicts ready to be added to coactive array
    """
    if not UNIFIED_LOOP_CONFIG.get("create_emotional_links", True):
        return []

    if not emotional_cocktail:
        return []

    max_links = max_links or UNIFIED_LOOP_CONFIG.get("emotional_link_max", 3)
    threshold = UNIFIED_LOOP_CONFIG.get("emotional_link_threshold", 0.5)

    # Get the dominant emotions from current turn
    dominant_emotions = []
    for emotion_name, emotion_data in emotional_cocktail.items():
        if isinstance(emotion_data, dict):
            intensity = emotion_data.get("intensity", 0.0)
        elif isinstance(emotion_data, (int, float)):
            intensity = float(emotion_data)
        else:
            continue

        dominant_emotions.append((emotion_name, intensity))

    # Sort by intensity, take top 2
    dominant_emotions.sort(key=lambda x: x[1], reverse=True)
    dominant_emotions = dominant_emotions[:2]

    emotional_links = []

    for emotion_name, intensity in dominant_emotions:
        # Only link on strong emotions
        if intensity < threshold:
            continue

        # Search for other memories with the same dominant emotion
        if not hasattr(memory_engine, 'search_by_emotion'):
            continue

        try:
            similar_emotional = memory_engine.search_by_emotion(
                emotion=emotion_name,
                min_intensity=threshold - 0.1,  # Slightly lower threshold for matches
                exclude_session=current_session_id,
                max_results=max_links
            )
        except Exception as e:
            log.debug(f"[EMOTIONAL-LINK] Search failed for {emotion_name}: {e}")
            continue

        for match in similar_emotional:
            # Don't create duplicate links
            match_id = match.get("id") or match.get("memory_id")
            if not match_id:
                continue

            if any(l.get("id") == match_id for l in emotional_links):
                continue

            emotional_links.append({
                "id": match_id,
                "type": match.get("type", "unknown"),
                "source": "emotional_match",
                "emotion": emotion_name,
                "my_intensity": round(intensity, 2),
                "their_intensity": round(match.get("emotion_intensity", 0.5), 2),
                "snippet": (match.get("text", match.get("fact", "")) or "")[:80],
            })

            if len(emotional_links) >= max_links:
                break

        if len(emotional_links) >= max_links:
            break

    if emotional_links:
        log.info(f"[EMOTIONAL-LINK] Created {len(emotional_links)} cross-temporal emotional links")

    return emotional_links


def search_by_emotion_impl(
    memory_layers,
    emotion: str,
    min_intensity: float = 0.4,
    exclude_session: str = None,
    max_results: int = 3
) -> List[Dict]:
    """
    Implementation of search_by_emotion for memory engines.

    Finds memories with matching emotion from recent history.
    This is Option B from the spec (scan-based, works immediately).

    Can be migrated to ChromaDB metadata filter (Option A) later
    if emotion tags are stored in metadata.

    Args:
        memory_layers: MemoryLayerManager instance
        emotion: Emotion name to search for
        min_intensity: Minimum intensity threshold
        exclude_session: Session ID to exclude
        max_results: Maximum results to return

    Returns:
        List of matching memory dicts with emotion_intensity field added
    """
    matches = []
    emotion_lower = emotion.lower()

    # Search last 500 long-term memories
    search_pool = list(memory_layers.long_term_memory[-500:])

    for mem in search_pool:
        # Skip same session
        if exclude_session and mem.get("session_id") == exclude_session:
            continue

        # Check emotion tags
        tags = mem.get("emotion_tags", [])
        cocktail = mem.get("emotional_cocktail", {})

        # Check if emotion is in tags
        tag_match = emotion_lower in [t.lower() for t in tags]

        # Check if emotion is in cocktail
        cocktail_match = False
        emo_data = cocktail.get(emotion, cocktail.get(emotion_lower, {}))

        if emo_data:
            if isinstance(emo_data, dict):
                intensity = emo_data.get("intensity", 0.5)
            elif isinstance(emo_data, (int, float)):
                intensity = float(emo_data)
            else:
                intensity = 0.5

            if intensity >= min_intensity:
                cocktail_match = True
                mem_copy = mem.copy()
                mem_copy["emotion_intensity"] = intensity
                matches.append(mem_copy)
        elif tag_match:
            # Tag match but no intensity info - assume moderate intensity
            mem_copy = mem.copy()
            mem_copy["emotion_intensity"] = 0.5
            matches.append(mem_copy)

    # Sort by intensity descending
    matches.sort(key=lambda m: m.get("emotion_intensity", 0), reverse=True)

    return matches[:max_results]


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def apply_cache_pressure_to_oscillator(
    cache: GraphActivationCache,
    oscillator_engine,
    source: str = "memory_association"
) -> bool:
    """
    Apply gentle oscillator pressure from cached memory associations.

    Called during interoception tick (fast loop). Non-blocking.

    Args:
        cache: GraphActivationCache instance
        oscillator_engine: ResonantOscillator instance with apply_band_pressure
        source: Source label for the pressure

    Returns:
        True if pressure was applied, False otherwise
    """
    if cache.is_stale():
        return False

    pressure = cache.get_emotional_pressure()
    if not pressure:
        return False

    if hasattr(oscillator_engine, 'apply_band_pressure'):
        try:
            oscillator_engine.apply_band_pressure(pressure, source=source)
            return True
        except Exception as e:
            log.debug(f"[GRAPH:FAST] Failed to apply pressure: {e}")

    return False


def get_associative_echo(cache: GraphActivationCache) -> Dict[str, Any]:
    """
    Get associative echo data for felt-state buffer.

    Returns a dict suitable for merging into felt_state during
    interoception scan.

    Args:
        cache: GraphActivationCache instance

    Returns:
        Dict with associative_echo field (and maybe more)
    """
    if not UNIFIED_LOOP_CONFIG.get("show_associative_echo", True):
        return {}

    if cache.is_stale():
        return {}

    snippet = cache.get_top_snippet()
    if not snippet or len(snippet) < 20:
        return {}

    return {
        "associative_echo": snippet,
        "echo_band": cache.activated_band,
        "echo_age": time.time() - cache.last_updated,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def create_unified_loop_components(
    memory_engine,
    get_oscillator_state: Callable,
    get_felt_summary: Callable = None
) -> Dict[str, Any]:
    """
    Factory function to create all unified loop components.

    Returns a dict containing:
    - cache: GraphActivationCache instance
    - worker: MediumLoopWorker instance (not started)

    Usage:
        components = create_unified_loop_components(
            memory_engine=bridge.memory,
            get_oscillator_state=lambda: resonance.engine.get_state(),
            get_felt_summary=lambda: interoception.get_felt_summary()
        )

        # Start the worker
        components["worker"].start()

        # In interoception tick:
        memories = components["cache"].get_active_memories()
        pressure = components["cache"].get_emotional_pressure()
    """
    cache = GraphActivationCache(
        max_size=UNIFIED_LOOP_CONFIG.get("graph_max_cached", 15)
    )

    worker = MediumLoopWorker(
        graph_cache=cache,
        memory_engine=memory_engine,
        get_oscillator_state=get_oscillator_state,
        get_felt_summary=get_felt_summary,
        interval=UNIFIED_LOOP_CONFIG.get("medium_loop_interval", 45.0)
    )

    return {
        "cache": cache,
        "worker": worker,
    }
