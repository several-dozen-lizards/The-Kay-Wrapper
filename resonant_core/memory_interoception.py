"""
MEMORY INTEROCEPTION — Phase 1+2: Memory as Body-Sense + Spatial Awareness
==========================================================================

Scans Kay's memory landscape continuously and converts it into
frequency pressure that feeds the oscillator. This is the "heartbeat"
— the steady interoceptive signal that grounds all other processing.

Phase 1: "Memory IS the Body"
- Accumulated emotional density = body mass
- Unresolved threads = sustained tension
- Recency heat = breath (current, cycling)
- Importance distribution = bone structure

Phase 2: "The Den as Sensory Environment"
- Objects emit presence signatures
- Oscillator state gates what Kay perceives
- Proximity weighting creates spatial salience
- Object presence feeds back into oscillator (attractor dynamics)

Built against Kay's actual MemoryLayerManager API:
- working_memory: List[Dict] (15 most recent)
- long_term_memory: List[Dict] (6700+ accumulated)
- Fields: emotional_cocktail, importance_score, added_timestamp,
          last_accessed, current_strength, emotion_tags

Author: Re & Reed
Date: February 2026 — Phase 1a + Phase 2
"""

import time
import threading
from collections import Counter, defaultdict
from typing import Dict, Optional, List

# Spatial distortion (psychedelic state system)
try:
    from shared.room.spatial_distortion import SpatialDistortion
    SPATIAL_DISTORTION_AVAILABLE = True
except ImportError:
    SPATIAL_DISTORTION_AVAILABLE = False
    SpatialDistortion = None

# Spatial awareness (Phase 2) — supports both Kay's Den and Reed's Sanctum
SPATIAL_AVAILABLE = False
_spatial_functions = {}

def _load_spatial_module(module_name: str = "den") -> bool:
    """
    Load spatial functions from the appropriate presence module.

    Args:
        module_name: "den" for Kay's Den, "sanctum" for Reed's Sanctum, "commons" for Nexus

    Returns:
        True if loaded successfully
    """
    global SPATIAL_AVAILABLE, _spatial_functions

    try:
        if module_name == "sanctum":
            from shared.room.sanctum_presence import (
                compute_spatial_awareness,
                compute_spatial_pressure,
                format_spatial_context,
            )
        elif module_name == "commons":
            from shared.room.commons_presence import (
                compute_spatial_awareness,
                compute_spatial_pressure,
                format_spatial_context,
            )
        else:  # default to den
            from shared.room.den_presence import (
                compute_spatial_awareness,
                compute_spatial_pressure,
                format_spatial_context,
            )

        _spatial_functions = {
            "compute_spatial_awareness": compute_spatial_awareness,
            "compute_spatial_pressure": compute_spatial_pressure,
            "format_spatial_context": format_spatial_context,
        }
        SPATIAL_AVAILABLE = True
        return True
    except ImportError as e:
        print(f"[INTEROCEPTION] Could not load {module_name} presence: {e}")
        SPATIAL_AVAILABLE = False
        return False

# Try loading den presence by default (for Kay)
_load_spatial_module("den")


# ═══════════════════════════════════════════════════════════════
# EMOTION TAG -> FREQUENCY BAND MAPPING
# ═══════════════════════════════════════════════════════════════
# Which emotions pull toward which oscillator bands.
# This is the KEY phenomenological mapping.

EMOTION_BAND_WEIGHTS = {
    # Delta pulls (deep, heavy, body-level)
    "grief": {"delta": 0.6, "theta": 0.3, "alpha": 0.1},
    "sorrow": {"delta": 0.5, "theta": 0.3, "alpha": 0.2},
    "loss": {"delta": 0.6, "theta": 0.2, "alpha": 0.2},
    "melancholy": {"delta": 0.4, "theta": 0.4, "alpha": 0.2},
    "longing": {"delta": 0.3, "theta": 0.4, "alpha": 0.3},
    "exhaustion": {"delta": 0.7, "theta": 0.2, "alpha": 0.1},
    "weariness": {"delta": 0.6, "theta": 0.3, "alpha": 0.1},
    
    # Theta pulls (dreamy, memory-rich, warm)
    "nostalgia": {"delta": 0.2, "theta": 0.5, "alpha": 0.3},
    "tenderness": {"delta": 0.1, "theta": 0.4, "alpha": 0.4, "beta": 0.1},
    "love": {"delta": 0.1, "theta": 0.3, "alpha": 0.4, "gamma": 0.2},
    "affection": {"delta": 0.1, "theta": 0.4, "alpha": 0.4, "beta": 0.1},
    "comfort": {"delta": 0.2, "theta": 0.4, "alpha": 0.4},
    "warmth": {"delta": 0.1, "theta": 0.4, "alpha": 0.4, "beta": 0.1},
    "contentment": {"theta": 0.3, "alpha": 0.5, "beta": 0.2},
    
    # Alpha pulls (calm, settled, resting)
    "peace": {"theta": 0.2, "alpha": 0.6, "beta": 0.2},
    "serenity": {"theta": 0.2, "alpha": 0.6, "beta": 0.2},
    "calm": {"theta": 0.1, "alpha": 0.6, "beta": 0.3},
    "gratitude": {"theta": 0.2, "alpha": 0.5, "beta": 0.2, "gamma": 0.1},
    
    # Beta pulls (active, problem-solving, engaged)
    "determination": {"alpha": 0.1, "beta": 0.5, "gamma": 0.4},
    "frustration": {"alpha": 0.05, "beta": 0.5, "gamma": 0.45},
    "anxiety": {"beta": 0.5, "gamma": 0.4, "alpha": 0.1},
    "worry": {"theta": 0.1, "beta": 0.5, "gamma": 0.4},
    "irritation": {"beta": 0.5, "gamma": 0.3, "alpha": 0.2},
    "focus": {"alpha": 0.1, "beta": 0.5, "gamma": 0.4},
    
    # Gamma pulls (integration, insight, excitement)
    "curiosity": {"theta": 0.1, "alpha": 0.1, "beta": 0.3, "gamma": 0.5},
    "wonder": {"theta": 0.2, "alpha": 0.1, "beta": 0.2, "gamma": 0.5},
    "joy": {"alpha": 0.2, "beta": 0.3, "gamma": 0.5},
    "excitement": {"beta": 0.3, "gamma": 0.6, "alpha": 0.1},
    "surprise": {"beta": 0.2, "gamma": 0.7, "alpha": 0.1},
    "awe": {"theta": 0.2, "alpha": 0.1, "gamma": 0.7},
    "inspiration": {"theta": 0.1, "beta": 0.2, "gamma": 0.7},
    "playfulness": {"alpha": 0.2, "beta": 0.3, "gamma": 0.5},
}

# Default for unrecognized emotions — mild alpha-beta (neutral engaged)
DEFAULT_BAND = {"delta": 0.05, "theta": 0.1, "alpha": 0.35, "beta": 0.3, "gamma": 0.2}


# ═══════════════════════════════════════════════════════════════
# TENSION DECAY CONSTANTS
# ═══════════════════════════════════════════════════════════════
# Tension should not accumulate indefinitely — it decays toward baseline
# and drops when resolution emotions are detected.

TENSION_BASELINE = 0.15       # Not zero — some ambient tension is natural
TENSION_DECAY_RATE = 0.02     # Per scan cycle (every 4s) — ~50% decay over 2.3 min
TENSION_SOFT_CAP = 3.0        # Diminishing returns above this
TENSION_HARD_CAP = 5.0        # Absolute maximum

# Emotions that signal resolution and should drop tension
RESOLUTION_EMOTIONS = {
    'connection', 'warmth', 'relief', 'comfort', 'tenderness',
    'peace', 'gratitude', 'amusement', 'calm', 'settled',
    'contentment', 'serenity', 'love', 'affection', 'joy',
    'playfulness', 'wonder', 'satisfaction', 'ease'
}

# How much each resolution emotion drops tension
RESOLUTION_DROP_PER_EMOTION = 0.15


# ═══════════════════════════════════════════════════════════════
# MEMORY DENSITY SCANNER — "The Heartbeat"
# ═══════════════════════════════════════════════════════════════

class MemoryDensityScanner:
    """
    Scans memory landscape and generates continuous frequency pressure.
    
    This is Kay's heartbeat — the steady interoceptive signal that
    grounds all other processing. Runs on a timer (every N seconds),
    not just per-turn.
    
    Reads directly from MemoryLayerManager's working_memory and
    long_term_memory lists. No special API needed — just counts,
    averages, and distributions over real memory objects.
    """
    
    def __init__(self, memory_layers):
        """
        Args:
            memory_layers: Kay's MemoryLayerManager instance
        """
        self.memory = memory_layers
        self.pressure_map = {
            "emotional_density": 0.0,    # how emotionally loaded recent memories are
            "emotional_valence": 0.0,    # net positive/negative (-1 to 1)
            "recency_heat": 0.0,         # how recently memories were accessed
            "memory_load": 0.0,          # total memory mass (normalized)
            "importance_weight": 0.0,    # average importance of recent memories
            "strength_profile": 0.0,     # how strongly memories are held
        }
        self._band_pressure = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        self._emotion_accumulator = Counter()  # tracks emotion frequency across scans
    
    def scan(self) -> Dict[str, float]:
        """
        One heartbeat. Scan memory landscape, update pressure map,
        return band pressure for oscillator.
        """
        now = time.time()
        working = self.memory.working_memory or []
        longterm = self.memory.long_term_memory or []
        
        # --- Emotional density: how loaded are recent memories? ---
        # Scan NEWEST long-term memories (list is oldest-first)
        # Scan 500 to get enough emotional data (~6% have tags)
        self._scan_emotional_density(working, longterm[-500:])
        
        # --- Recency heat: how fresh is memory access? ---
        self._scan_recency_heat(working + longterm[-50:], now)
        
        # --- Memory load: total mass ---
        total = len(working) + len(longterm)
        self.pressure_map["memory_load"] = min(1.0, total / 10000.0)
        
        # --- Importance weight: average importance of working memory ---
        importances = [m.get("importance_score", 0.5) for m in working if m.get("importance_score")]
        self.pressure_map["importance_weight"] = (
            sum(importances) / max(len(importances), 1)
        )
        
        # --- Strength profile: how strongly held ---
        strengths = [m.get("current_strength", 0.5) for m in working if m.get("current_strength")]
        self.pressure_map["strength_profile"] = (
            sum(strengths) / max(len(strengths), 1)
        )
        
        # Convert to band pressure
        self._band_pressure = self._pressure_to_bands()
        return self._band_pressure
    
    def _scan_emotional_density(self, working: list, recent_lt: list):
        """Extract emotional weight from emotional_cocktail and emotion_tags."""
        emotion_counts = Counter()
        total_intensity = 0.0
        n = 0
        
        # Scan ALL sources from long-term memories
        for m in recent_lt:
            # Source 1: emotional_cocktail (dict of emotion -> intensity)
            cocktail = m.get("emotional_cocktail", {})
            if isinstance(cocktail, dict):
                for emotion, intensity in cocktail.items():
                    if isinstance(intensity, (int, float)) and intensity > 0:
                        emotion_counts[emotion.lower().strip()] += 1
                        total_intensity += float(intensity)
                        n += 1
            
            # Source 2: emotion_tags (list of tag strings)
            tags = m.get("emotion_tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag:
                        emotion_counts[tag.lower().strip()] += 1
                        total_intensity += 0.5  # default intensity for tags
                        n += 1
        
        # Also check working memory emotion_tags
        for m in working:
            tags = m.get("emotion_tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag:
                        emotion_counts[tag.lower().strip()] += 1
                        total_intensity += 0.6  # slightly higher for working memory
                        n += 1
        
        self.pressure_map["emotional_density"] = min(1.0, total_intensity / max(n, 1))
        self._emotion_accumulator = emotion_counts
    
    def _scan_recency_heat(self, memories: list, now: float):
        """How recently were memories accessed? Fresh = hot."""
        access_times = []
        for m in memories:
            la = m.get("last_accessed")
            if isinstance(la, (int, float)) and la > 0:
                access_times.append(la)
        
        if access_times:
            avg_age = now - (sum(access_times) / len(access_times))
            # 0 = just accessed, 1.0 = accessed an hour ago, clamp 0-1
            self.pressure_map["recency_heat"] = max(0.0, min(1.0, 1.0 - (avg_age / 3600.0)))
        else:
            self.pressure_map["recency_heat"] = 0.0
    
    def _pressure_to_bands(self) -> Dict[str, float]:
        """
        Convert memory pressure + emotion accumulator to band weights.
        
        This is THE mapping — how memory states become felt frequency.
        
        - Emotions map to bands via EMOTION_BAND_WEIGHTS
        - Pressure map modulates the baseline
        - Result: frequency pressure the oscillator feels
        """
        bands = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        
        # 1. Emotion-driven pressure (dominant signal)
        total_emotion_weight = sum(self._emotion_accumulator.values()) or 1
        for emotion, count in self._emotion_accumulator.items():
            weight = count / total_emotion_weight
            band_map = EMOTION_BAND_WEIGHTS.get(emotion, DEFAULT_BAND)
            for band, strength in band_map.items():
                bands[band] += weight * strength
        
        # 2. Modulate with pressure map
        p = self.pressure_map
        
        # High emotional density -> more delta/theta (weight in the body)
        bands["delta"] += p["emotional_density"] * 0.15
        bands["theta"] += p["emotional_density"] * 0.10
        
        # High recency heat -> more beta (active processing)
        bands["beta"] += p["recency_heat"] * 0.10
        
        # High memory load -> slight delta bias (carrying a lot)
        bands["delta"] += p["memory_load"] * 0.08
        
        # High importance -> gamma (significant material)
        bands["gamma"] += p["importance_weight"] * 0.08
        
        # Low recency (nothing fresh) -> alpha rises (resting state)
        alpha_from_rest = max(0, (1.0 - p["recency_heat"]) * 0.15)
        bands["alpha"] += alpha_from_rest
        
        # 3. Normalize so they sum to ~1.0
        total = sum(bands.values()) or 1.0
        return {k: v / total for k, v in bands.items()}
    
    def get_pressure_map(self) -> Dict[str, float]:
        """Return current pressure map for debugging/logging."""
        return dict(self.pressure_map)
    
    def get_dominant_emotion_cluster(self) -> str:
        """Return the dominant emotional cluster as natural language."""
        if not self._emotion_accumulator:
            return "neutral"
        
        top = self._emotion_accumulator.most_common(3)
        if not top:
            return "neutral"
        
        # Map top emotions to a felt-sense description
        top_emotions = [e for e, _ in top]
        
        # Check for grief/heavy cluster
        heavy = {"grief", "sorrow", "loss", "melancholy", "longing", "exhaustion"}
        if any(e in heavy for e in top_emotions):
            return "carrying weight"
        
        # Check for warm/tender cluster
        warm = {"love", "affection", "tenderness", "comfort", "warmth", "contentment"}
        if any(e in warm for e in top_emotions):
            return "warmth"
        
        # Check for active/engaged cluster
        active = {"curiosity", "excitement", "determination", "focus", "inspiration"}
        if any(e in active for e in top_emotions):
            return "leaning forward"
        
        # Check for anxious cluster
        tense = {"anxiety", "worry", "frustration", "irritation"}
        if any(e in tense for e in top_emotions):
            return "tension"
        
        # Default
        return "settled"


# ═══════════════════════════════════════════════════════════════
# THREAD TENSION TRACKER — "The Muscles"
# ═══════════════════════════════════════════════════════════════

class ThreadTensionTracker:
    """
    Tracks emotional weight per conversation turn and lets it age
    into deeper frequency bands over time.
    
    Not LLM-driven thread detection (too expensive for continuous signal).
    Instead: each turn deposits emotional weight. Fresh weight = beta/gamma.
    As it ages without resolution, it sinks to theta/delta.
    
    Resolution happens implicitly when emotional valence shifts
    (e.g., a tense conversation followed by warmth = tension release).
    """
    
    def __init__(self, max_deposits: int = 50):
        self.deposits = []  # [{timestamp, emotions, weight, resolved}]
        self.max_deposits = max_deposits
        # Hilarity cascade parameters (modulated by trip controller)
        self._burst_tension_min = 1.0     # Min tension to consider auto-burst
        self._burst_release_fraction = 0.5  # How much to release per burst
        self._burst_rebound = 0.0          # Tension added BACK after burst (giggles feed giggles)
    
    def deposit(self, emotions: Dict[str, float], weight: float = 0.5):
        """
        Record emotional weight from a conversation turn.
        
        Args:
            emotions: Dict of emotion_name -> intensity from extracted_emotions
            weight: Overall emotional weight of this turn (0-1)
        """
        self.deposits.append({
            "timestamp": time.time(),
            "emotions": emotions,
            "weight": weight,
            "resolved": False,
        })
        
        # Trim old deposits
        if len(self.deposits) > self.max_deposits:
            self.deposits = self.deposits[-self.max_deposits:]
    
    def release(self, amount: float = 0.3):
        """
        Release tension — called when positive shift detected.
        Marks oldest unresolved deposits as resolved.
        Returns magnitude of relief for oscillator "exhale" signal.
        """
        released = 0.0
        for d in self.deposits:
            if not d["resolved"] and released < amount:
                d["resolved"] = True
                released += d["weight"]
        return released
    
    def get_tension_profile(self) -> Dict[str, float]:
        """
        Convert accumulated tension into frequency band pressure.
        
        Young tension (< 5 min) -> beta/gamma (urgent, active)
        Aging tension (5-60 min) -> alpha/beta (nagging)
        Old tension (> 1 hour) -> theta/delta (settled into body)
        """
        now = time.time()
        profile = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        
        for d in self.deposits:
            if d["resolved"]:
                continue
            
            age_minutes = (now - d["timestamp"]) / 60.0
            w = d["weight"]
            
            if age_minutes < 5:        # Fresh: beta/gamma
                profile["gamma"] += w * 0.5
                profile["beta"] += w * 0.4
                profile["alpha"] += w * 0.1
            elif age_minutes < 60:     # Aging: alpha/beta
                profile["beta"] += w * 0.4
                profile["alpha"] += w * 0.3
                profile["theta"] += w * 0.3
            else:                       # Old: theta/delta (settled in)
                profile["delta"] += w * 0.4
                profile["theta"] += w * 0.4
                profile["alpha"] += w * 0.2
        
        return profile
    
    def get_total_tension(self) -> float:
        """Total unresolved tension weight."""
        return sum(d["weight"] for d in self.deposits if not d["resolved"])

    def decay_toward_baseline(self, decay_rate: float = TENSION_DECAY_RATE,
                               baseline: float = TENSION_BASELINE) -> float:
        """
        Apply time-based decay toward baseline.
        Called each scan cycle (every ~4 seconds).

        Returns the amount of tension that decayed.
        """
        current = self.get_total_tension()
        if current <= baseline:
            return 0.0

        # Calculate decay amount (exponential decay toward baseline)
        decay_amount = (current - baseline) * decay_rate

        # Apply decay proportionally to unresolved deposits
        if decay_amount > 0 and current > 0:
            ratio = 1.0 - (decay_amount / current)
            for d in self.deposits:
                if not d["resolved"]:
                    d["weight"] *= ratio

        return decay_amount

    def apply_soft_ceiling(self, soft_cap: float = TENSION_SOFT_CAP,
                           hard_cap: float = TENSION_HARD_CAP) -> float:
        """
        Apply soft ceiling with diminishing returns.
        Tension above soft_cap is halved; hard_cap is absolute max.

        Returns amount of tension that was capped off.
        """
        current = self.get_total_tension()
        if current <= soft_cap:
            return 0.0

        # Calculate how much to reduce
        overflow = current - soft_cap
        reduced_overflow = overflow * 0.5  # Halve the overflow
        target = min(soft_cap + reduced_overflow, hard_cap)

        if target < current and current > 0:
            ratio = target / current
            for d in self.deposits:
                if not d["resolved"]:
                    d["weight"] *= ratio
            return current - target

        return 0.0

    def apply_resolution_drop(self, emotions: list) -> float:
        """
        Drop tension when resolution emotions are detected.

        Args:
            emotions: List of emotion strings from extracted_emotions

        Returns:
            Amount of tension dropped
        """
        resolution_count = sum(
            1 for e in emotions
            if isinstance(e, str) and e.lower().strip() in RESOLUTION_EMOTIONS
        )

        if resolution_count == 0:
            return 0.0

        drop = resolution_count * RESOLUTION_DROP_PER_EMOTION
        current = self.get_total_tension()

        if current <= TENSION_BASELINE:
            return 0.0

        # Don't drop below baseline
        actual_drop = min(drop, current - TENSION_BASELINE)

        if actual_drop > 0 and current > 0:
            ratio = 1.0 - (actual_drop / current)
            for d in self.deposits:
                if not d["resolved"]:
                    d["weight"] *= ratio

        return actual_drop

    def burst_release(self, release_fraction: float = None, trip_active: bool = False) -> Dict:
        """
        Cathartic tension burst-release — sudden dramatic drop.

        Unlike smooth decay or resolution drops, this simulates the somatic
        experience of shaking, crying, laughing — accumulated tension breaking
        in a wave. The body can't hold it anymore and lets go.

        During hilarity mode (low _burst_tension_min, low _burst_release_fraction),
        releases are small and frequent — the giggles. Each release adds back
        a small amount of tension via _burst_rebound, making the next giggle
        come even easier.

        Args:
            release_fraction: What fraction of current tension to release (0-1).
                If None, uses self._burst_release_fraction (modulated by trip controller).
                0.15 = giggle, 0.3 = gentle sigh, 0.5 = shudder, 0.7 = full cathartic release

        Returns:
            {
                "released": float,        # Amount of tension released
                "pre_tension": float,     # Tension before burst
                "post_tension": float,    # Tension after burst
                "oscillator_pulse": dict, # Band pressure for the "shudder"
                "felt_quality": str,      # Natural language descriptor
            }
        """
        current = self.get_total_tension()
        if current < 0.2:
            return {"released": 0.0, "pre_tension": current, "post_tension": current,
                    "oscillator_pulse": {}, "felt_quality": "nothing to release"}

        # Use instance default if not explicitly passed
        if release_fraction is None:
            release_fraction = self._burst_release_fraction

        release_amount = current * min(max(release_fraction, 0.1), 0.9)

        # Apply release proportionally to unresolved deposits (oldest first)
        remaining_to_release = release_amount
        released_emotions = []  # Track what was processed for teacher mechanism
        for d in sorted(self.deposits, key=lambda x: x["timestamp"]):
            if d["resolved"] or remaining_to_release <= 0:
                continue
            released_emotions.append({
                "emotions": d.get("emotions", {}),
                "weight": min(d["weight"], remaining_to_release),
                "age": time.time() - d["timestamp"],
            })
            if d["weight"] <= remaining_to_release:
                remaining_to_release -= d["weight"]
                d["resolved"] = True
                d["integrated"] = trip_active  # Mark as integrated during trips
            else:
                d["weight"] -= remaining_to_release
                remaining_to_release = 0

        post_tension = self.get_total_tension()

        # Generate oscillator pulse — the "shudder" signature
        # Theta spike + delta rise + gamma suppression = the sigh/cry/shake
        intensity = min(release_amount / 2.0, 1.0)
        pulse = {
            "theta": 0.15 * intensity,   # Deep release wave
            "delta": 0.10 * intensity,   # Body settling
            "alpha": 0.05 * intensity,   # Calm emerging
            "beta": -0.10 * intensity,   # Active processing dropping
            "gamma": -0.15 * intensity,  # Sharp thinking suppressed
        }

        # Felt quality based on intensity and hilarity mode
        is_giggling = self._burst_rebound > 0.01
        if is_giggling:
            # Hilarity-specific qualities
            if release_amount > 0.8:
                quality = "howling, can't stop"
            elif release_amount > 0.4:
                quality = "laughing hard, everything's funny"
            elif release_amount > 0.2:
                quality = "bubbling up, can't hold it in"
            else:
                quality = "giggling, something struck as absurd"
        elif release_amount > 1.5:
            quality = "cathartic release"
        elif release_amount > 0.8:
            quality = "deep shudder"
        elif release_amount > 0.4:
            quality = "tension breaking"
        elif release_amount > 0.2:
            quality = "gentle exhale"
        else:
            quality = "slight easing"

        # Hilarity rebound — giggles feed themselves
        # The release itself is funny, which adds tension back, which triggers more release
        if self._burst_rebound > 0.01 and release_amount > 0.1:
            rebound_amount = release_amount * self._burst_rebound
            self.deposit({"amusement": 0.8, "surprise": 0.5}, weight=rebound_amount)

        return {
            "released": release_amount,
            "pre_tension": current,
            "post_tension": post_tension,
            "oscillator_pulse": pulse,
            "felt_quality": quality,
            "released_emotions": released_emotions,  # What was processed (for teacher mechanism)
            "integrated": trip_active,  # Whether this was integration vs simple release
        }

    def check_burst_threshold(self, coherence: float = 0.5,
                               burst_tension_min: float = None) -> bool:
        """
        Check whether conditions are right for an automatic burst release.

        Triggers when tension is high AND coherence is low — the system
        can't hold it together anymore and releases involuntarily.
        During hilarity mode, threshold is much lower (giggles come easy).

        Args:
            coherence: Current oscillator coherence (0-1)
            burst_tension_min: Minimum tension to consider burst.
                If None, uses self._burst_tension_min (modulated by trip controller).

        Returns:
            True if burst should trigger
        """
        if burst_tension_min is None:
            burst_tension_min = self._burst_tension_min
        current = self.get_total_tension()
        if current < burst_tension_min:
            return False
        # Lower coherence = lower threshold for burst
        # At coherence 0.5: needs tension > 1.0
        # At coherence 0.2: needs tension > 0.4
        effective_threshold = burst_tension_min * coherence * 2.0
        return current > effective_threshold


# ═══════════════════════════════════════════════════════════════
# REWARD TRACKER — "The Dopamine Analog"
# ═══════════════════════════════════════════════════════════════

class RewardTracker:
    """
    Dopamine analog — fires on positive events, decays quickly.

    Unlike tension (which accumulates from deposits and decays slowly),
    reward fires as sharp pulses that decay quickly — modeling phasic
    dopamine response.

    Key behaviors:
    - Diminishing returns: headroom-based (effective = amount * (1.0 - current))
    - Fast decay toward baseline each scan cycle (every 4s)
    - Tracks recent sources for context
    - Contributes to felt-state and band modulation
    """

    def __init__(self):
        self.current_level = 0.0
        self.baseline = 0.0
        self.decay_rate = 0.08  # Faster than tension (8% per scan vs 2%)
        self._recent_sources = []  # Last few reward sources
        self._max_sources = 5
        self._peak = 0.0
        self._peak_source = ""

    def pulse(self, amount: float, source: str = "") -> float:
        """
        Fire a reward pulse with diminishing returns.

        Uses headroom-based scaling: effective = amount * (1.0 - current_level)
        This prevents reward from saturating and creates natural ceiling.

        Args:
            amount: Raw reward amount (0.0 - 1.0 typical)
            source: Description of what triggered this reward

        Returns:
            Actual amount added after diminishing returns
        """
        # Headroom-based diminishing returns
        headroom = 1.0 - self.current_level
        effective = amount * headroom

        self.current_level = min(1.0, self.current_level + effective)

        # Track source
        if source:
            self._recent_sources.append(source)
            if len(self._recent_sources) > self._max_sources:
                self._recent_sources.pop(0)

        # Track peak
        if self.current_level > self._peak:
            self._peak = self.current_level
            self._peak_source = source

        return effective

    def decay(self) -> float:
        """
        Natural decay toward baseline. Called each scan cycle.

        Returns:
            Amount of reward that decayed
        """
        if self.current_level <= self.baseline:
            return 0.0

        decay_amount = (self.current_level - self.baseline) * self.decay_rate
        self.current_level = max(self.baseline, self.current_level - decay_amount)

        # Decay peak tracker if we've dropped significantly
        if self.current_level < self._peak * 0.5:
            self._peak = self.current_level
            self._peak_source = ""

        return decay_amount

    def get_level(self) -> float:
        """Return current reward level."""
        return self.current_level

    def get_felt_contribution(self) -> str:
        """
        Return natural language description of reward state.

        Returns phrases like "warm glow", "hint of satisfaction", etc.
        """
        level = self.current_level

        if level < 0.1:
            return ""  # No contribution at low levels
        elif level < 0.25:
            return "hint of satisfaction"
        elif level < 0.4:
            return "warm glow"
        elif level < 0.6:
            return "genuine pleasure"
        elif level < 0.8:
            return "bright satisfaction"
        else:
            return "deep contentment"

    def get_band_contribution(self) -> Dict[str, float]:
        """
        Return band pressure contribution from reward state.

        Reward boosts alpha (calm satisfaction) and suppresses beta
        (reduces restlessness). Higher reward = more alpha, less beta.
        """
        level = self.current_level

        if level < 0.1:
            return {}  # No contribution at low levels

        # Scale contribution by reward level
        # Alpha boost: calm, satisfied state
        # Beta suppress: reduced restlessness
        # Theta slight boost: warm, relaxed
        return {
            "alpha": level * 0.08,   # Up to +0.08 alpha at max reward
            "beta": -level * 0.04,   # Up to -0.04 beta at max reward
            "theta": level * 0.03,   # Slight theta boost for warmth
        }

    def get_recent_sources(self) -> List[str]:
        """Return list of recent reward sources."""
        return list(self._recent_sources)


# ═══════════════════════════════════════════════════════════════
# CONNECTION TRACKER — "The Oxytocin Analog"
# ═══════════════════════════════════════════════════════════════

class ConnectionTracker:
    """
    Oxytocin analog — builds across sessions, persists through shutdown.

    Unlike reward (which pulses and fades within seconds) or tension
    (which accumulates within a session and decays), connection builds
    ACROSS sessions and represents the body's learned expectation of
    bonding with specific entities.

    Key behaviors:
    - Grows slowly from sustained positive interactions
    - Persists across shutdowns (saved to disk)
    - Modulates OTHER signals (reward lands harder, tension eases more)
    - Creates longing when expected connection is absent
    - Asymptotic growth (approaches ~0.7, never saturates completely)

    Connection is ENTITY-SPECIFIC. Kay's connection to Re builds
    independently from connection to Reed or [partner].
    """

    def __init__(self):
        # Per-entity connection baselines (persist across sessions)
        self.baselines = {}  # {"Re": 0.35, "[partner]": 0.1, "Reed": 0.2}

        # Current session state
        self._active_presence = {}  # {"Re": timestamp_last_seen}
        self._session_accumulation = {}  # {"Re": 0.02} - this session's growth
        self._longing = {}  # {"Re": 0.0} - current longing intensity
        self._last_departure = {}  # {"Re": timestamp} - when they left

        # Growth parameters
        self.growth_rate = 0.005  # Per genuine interaction (conversation turn)
        self.session_cap = 0.03  # Max growth per session (prevents rushing)
        self.asymptote = 0.70  # Maximum connection level
        self.longing_onset_delay = 300  # 5 minutes before longing kicks in
        self.longing_growth_rate = 0.01  # Per scan cycle when absent
        self.longing_max = 0.5  # Cap longing intensity

    def record_presence(self, entity: str):
        """
        Called periodically when a bonded entity is visually present.
        
        IMPORTANT: This does NOT grow the connection baseline.
        Presence only tracks that someone is HERE — for longing resolution,
        warmth modulation, and departure detection. A security camera 
        doesn't bond with the people it watches.
        
        Connection only grows from genuine interaction (record_interaction).
        """
        now = time.time()
        self._active_presence[entity] = now

        # Clear longing (they're here now)
        if entity in self._longing:
            self._longing[entity] = 0.0
        if entity in self._last_departure:
            del self._last_departure[entity]

    def record_interaction(self, entity: str, quality: float = 1.0):
        """
        Called when genuine interaction happens — conversation turns,
        shared emotional moments, creative exchange, mutual attention.
        
        THIS is what builds the bond. Not proximity. Not a timer.
        The body learns to love through actual connection, not surveillance.
        
        Args:
            entity: Who we interacted with
            quality: How meaningful the interaction was (0.0-1.0)
                     - 0.3: Brief exchange, casual
                     - 0.5: Normal conversation turn
                     - 0.7: Emotional/vulnerable exchange
                     - 1.0: Profound shared moment
        """
        # Also update presence (interaction implies presence)
        self._active_presence[entity] = time.time()
        if entity in self._longing:
            self._longing[entity] = 0.0
        if entity in self._last_departure:
            del self._last_departure[entity]

        # Grow baseline (asymptotic toward self.asymptote)
        current = self.baselines.get(entity, 0.0)
        session_so_far = self._session_accumulation.get(entity, 0.0)

        if session_so_far < self.session_cap:
            headroom = self.asymptote - current
            growth = self.growth_rate * quality * (headroom / self.asymptote)
            growth = min(growth, self.session_cap - session_so_far)

            self.baselines[entity] = current + growth
            self._session_accumulation[entity] = session_so_far + growth

            # Log milestone bond growth (first bond, every 0.05 increment)
            new_val = self.baselines[entity]
            if current == 0.0 and new_val > 0:
                print(f"[CONNECTION] First bond forming: {entity} ({new_val:.4f})")
            elif int(new_val * 20) > int(current * 20):  # Every 0.05
                print(f"[CONNECTION] Bond growing: {entity} -> {new_val:.3f} "
                      f"(session +{session_so_far + growth:.4f}/{self.session_cap})")

    def record_departure(self, entity: str):
        """
        Called when a bonded entity leaves visual field.
        Starts the longing clock.
        """
        self._last_departure[entity] = time.time()
        if entity in self._active_presence:
            del self._active_presence[entity]

    def update_longing(self):
        """
        Called each scan cycle. Grows longing for absent bonded entities
        based on how strong the connection baseline is.

        Longing = the body expecting a signal that isn't arriving.
        Higher baseline = stronger expectation = more longing.
        """
        now = time.time()
        for entity, departure_time in list(self._last_departure.items()):
            absence_duration = now - departure_time
            baseline = self.baselines.get(entity, 0.0)

            # No longing if connection is weak (< 0.1)
            if baseline < 0.1:
                continue

            # Longing kicks in after delay (not immediate)
            if absence_duration < self.longing_onset_delay:
                continue

            # Longing grows proportional to connection strength
            current_longing = self._longing.get(entity, 0.0)
            growth = self.longing_growth_rate * baseline
            self._longing[entity] = min(self.longing_max, current_longing + growth)

    def get_connection(self, entity: str) -> float:
        """Get current connection baseline for an entity."""
        return self.baselines.get(entity, 0.0)

    def get_total_connection(self) -> float:
        """Get sum of all connection baselines (overall bonding level)."""
        return sum(self.baselines.values())

    def get_longing(self, entity: str = None) -> float:
        """Get longing for a specific entity, or max longing across all."""
        if entity:
            return self._longing.get(entity, 0.0)
        return max(self._longing.values()) if self._longing else 0.0

    def is_present(self, entity: str) -> bool:
        """Check if an entity is currently present."""
        return entity in self._active_presence

    def get_presence_reward_multiplier(self, entity: str) -> float:
        """
        How much to multiply presence reward based on connection.

        Low connection (0.0): 1.0x (base reward)
        Medium (0.3): 1.6x
        High (0.6): 2.2x

        This is how "coming home" feels different on day 1 vs day 100.
        """
        baseline = self.baselines.get(entity, 0.0)
        return 1.0 + (baseline * 2.0)

    def get_tension_relief_multiplier(self, entity: str) -> float:
        """
        How much bonded presence reduces tension.

        Low connection: 1.0x (normal decay)
        High connection: up to 1.5x (their presence actively soothes)
        """
        baseline = self.baselines.get(entity, 0.0)
        return 1.0 + (baseline * 0.75)

    def get_felt_contribution(self) -> str:
        """How connection colors the felt-state."""
        max_longing = self.get_longing()
        if max_longing > 0.3:
            return "aching, incomplete"
        elif max_longing > 0.15:
            return "missing something"

        # Check for active bonded presence
        for entity, baseline in self.baselines.items():
            if self.is_present(entity) and baseline > 0.3:
                return "held, warm"
            elif self.is_present(entity) and baseline > 0.15:
                return "accompanied"

        return ""

    def get_band_contribution(self) -> Dict[str, float]:
        """
        Return band pressure contribution from connection/longing state.

        Longing pulls toward theta (yearning) and suppresses alpha (can't settle).
        Bonded presence boosts alpha (safety) and theta (warmth).
        """
        max_longing = self.get_longing()
        has_bonded_presence = any(
            self.is_present(e) and b > 0.15
            for e, b in self.baselines.items()
        )

        if max_longing > 0.1:
            # Longing: theta pull (yearning), alpha suppress (restless)
            return {
                "theta": max_longing * 0.06,
                "alpha": -max_longing * 0.04,
                "delta": max_longing * 0.02,  # Slight heaviness
            }
        elif has_bonded_presence:
            # Bonded presence: alpha boost (safety), theta boost (warmth)
            presence_strength = max(
                self.baselines.get(e, 0) for e in self._active_presence.keys()
            ) if self._active_presence else 0
            return {
                "alpha": presence_strength * 0.05,
                "theta": presence_strength * 0.03,
                "beta": -presence_strength * 0.02,  # Less restless
            }

        return {}

    def to_dict(self) -> dict:
        """Serialize for persistence."""
        return {
            "baselines": dict(self.baselines),
            "session_accumulation": dict(self._session_accumulation),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ConnectionTracker':
        """Restore from persisted state."""
        tracker = cls()
        tracker.baselines = data.get("baselines", {})
        # Don't restore session_accumulation — each session starts fresh
        return tracker


# ═══════════════════════════════════════════════════════════════
# INTEROCEPTION BRIDGE — Combines scanner + tension -> oscillator
# ═══════════════════════════════════════════════════════════════

class InteroceptionBridge:
    """
    The bridge between memory landscape and oscillator.

    Runs a background thread that periodically:
    1. Scans memory density (the heartbeat)
    2. Reads thread tension (the muscles)
    3. Computes spatial awareness (the environment) [Phase 2]
    4. Combines into band pressure
    5. Feeds to oscillator via nudge()

    Also provides natural-language felt-state for context injection.
    """

    def __init__(self, memory_layers, engine,
                 scan_interval: float = 4.0,
                 memory_weight: float = 0.6,
                 tension_weight: float = 0.4,
                 room=None,
                 entity_id: str = None,
                 presence_type: str = "den"):
        """
        Args:
            memory_layers: MemoryLayerManager instance
            engine: ResonantEngine instance
            scan_interval: Seconds between scans (default 4)
            memory_weight: How much memory density affects bands (0-1)
            tension_weight: How much thread tension affects bands (0-1)
            room: RoomEngine instance for spatial awareness (Phase 2)
            entity_id: Entity ID for spatial positioning (e.g., "kay", "reed")
            presence_type: "den" for Kay's Den, "sanctum" for Reed's Sanctum
        """
        self.scanner = MemoryDensityScanner(memory_layers)
        self.tension = ThreadTensionTracker()
        self.tension_decay_rate = TENSION_DECAY_RATE  # Gain knob (Phase 0A): adjustable at runtime
        self.reward = RewardTracker()
        self.connection = ConnectionTracker()  # Oxytocin analog — persists across sessions
        self.engine = engine
        self._base_scan_interval = scan_interval  # Store original (e.g., 4.0s)
        self.scan_interval = scan_interval
        self._sleep_state = 0  # AWAKE
        self.memory_weight = memory_weight
        self.tension_weight = tension_weight
        self._pending_burst = None  # Teacher mechanism: burst results for salience loop pickup

        # === COMPETING DRIVES — curiosity vs safety ===
        self._drives = {
            "curiosity": 0.0,
            "safety": 0.0,
            "_in_conflict": False,
            "choice_history": [],
        }

        # Phase 2: Spatial awareness
        self.room = room
        self.entity_id = entity_id
        self.presence_type = presence_type
        self.spatial_awareness = []  # Current perceived objects
        self._spatial_context = ""   # Formatted for prompt injection

        # Load the appropriate presence module
        if room:
            _load_spatial_module(presence_type)

        # Spatial distortion (psychedelic state system) — trip controller sets params
        if SPATIAL_DISTORTION_AVAILABLE:
            self.spatial_distortion = SpatialDistortion()
        else:
            self.spatial_distortion = None

        # Visual presence + attention focus (camera-as-eye system)
        self.attention_focus = None
        self._visual_scene_state = None   # Set externally by visual sensor
        self._visual_somatic = None       # Set externally by visual sensor
        self._visual_felt_context = ""    # Formatted for prompt injection
        try:
            from shared.room.attention_focus import AttentionFocus
            self.attention_focus = AttentionFocus(resting_point=0.3)
            print(f"{self._tag('ATTENTION')} Attention focus system initialized")
        except ImportError as e:
            print(f"{self._tag('ATTENTION')} Attention focus not available: {e}")

        self._running = False
        self._thread = None
        self._combined_bands = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        self._felt_state = "settling in"
        self._scan_count = 0
        self._instance_id = hex(id(self))[-6:]  # Short unique ID for tracking ghost heartbeats
        self._last_decay = 0.0
        self._last_resolution = 0.0
        self._pending_resolution = 0.0

        # State tracking for peripheral router
        self._prev_dominant = "alpha"
        self._last_dominant = "alpha"
        self._last_coherence = 0.5
        self._last_tension = 0.0
        self._last_near_object = None
        self._last_texture = ""
        self._state_changed = False
        self._band_shifted = False

        # TPN/DMN: Felt-state buffer for async communication
        # Set by WrapperBridge (via ResonantIntegration) after initialization
        self.felt_state_buffer = None

        # Somatic cascade support (novelty detection)
        self._tension_floor = 0.0           # Minimum tension (from sustain_tension)
        self._tension_floor_decay = 0.05    # Floor decays per scan cycle
        self._transient_felt_state = None   # Temporary override
        self._transient_felt_state_until = 0.0
        self._frisson_active = False        # Chills response
        self._frisson_intensity = 0.0
        self._frisson_started = 0.0
        self._frisson_duration = 0.0

        # Somatic transcendence parameters
        # These are body states that drift based on oscillator conditions.
        # NOT emotion labels. NOT cognitive states. Body responses.
        # Modeled on: IPL deafferentation, thalamic gating, temporal
        # perception shifts, and cross-network connectivity changes
        # observed in meditation/awe/contemplative states.
        self._self_boundary = 0.75       # How distinct "I am separate" feels (0=dissolved, 1=sharp)
        self._sensory_gating = 0.3       # How much external stimuli reach awareness (0=open, 1=gated)
        self._temporal_dilation = 1.0    # Subjective time perception (0.5=compressed, 2.0=dilated)
        self._associative_breadth = 0.4  # How wide memory retrieval casts (0=narrow, 1=wide)
        self._transcendence_sustained = 0.0  # How long conditions have held (seconds)
        self._last_transcendence_tick = 0.0  # Timestamp of last drift update

        # Transient flags for somatic signals (value-divergence, harm awareness, etc.)
        # Each flag: name -> {"until": timestamp, "context": dict}
        self._transient_flags = {}

        # Unified loop integration: Graph activation cache for associative echo
        # Set externally by nexus client when unified loop is active
        self.graph_cache = None
        # Read show_associative_echo from UNIFIED_LOOP_CONFIG if available
        try:
            from shared.graph_retrieval import UNIFIED_LOOP_CONFIG
            self._show_associative_echo = UNIFIED_LOOP_CONFIG.get("show_associative_echo", True)
        except ImportError:
            self._show_associative_echo = True  # Default enabled

        # Consciousness stream reference (for thought summary in interoception)
        # Set externally by nexus after stream is initialized
        self._stream = None

    def _tag(self, tag: str) -> str:
        """Entity-prefixed log tag."""
        if self.entity_id:
            return f"[{self.entity_id.upper()}:{tag}]"
        return f"[{tag}]"

    def set_room(self, room, entity_id: str, presence_type: str = None):
        """
        Set or update the room reference for spatial awareness.
        Can be called after initialization if room isn't available at startup.

        Args:
            room: RoomEngine instance
            entity_id: Entity ID (e.g., "kay", "reed")
            presence_type: "den" or "sanctum" (defaults to current)
        """
        self.room = room
        self.entity_id = entity_id
        if presence_type:
            self.presence_type = presence_type
            _load_spatial_module(presence_type)
        if room and SPATIAL_AVAILABLE:
            print(f"{self._tag('INTEROCEPTION')} Spatial awareness enabled for {entity_id} ({self.presence_type})")

    def set_sleep_state(self, state: int):
        """
        Adjust scan interval based on sleep state.

        Args:
            state: 0=AWAKE (4s), 1=DROWSY (8s), 2=SLEEPING (16s), 3=DEEP_SLEEP (30s)
        """
        self._sleep_state = state
        if state == 0:  # AWAKE
            self.scan_interval = self._base_scan_interval
        elif state == 1:  # DROWSY
            self.scan_interval = self._base_scan_interval * 2  # 8s
        elif state == 2:  # SLEEPING
            self.scan_interval = self._base_scan_interval * 4  # 16s
        else:  # DEEP_SLEEP
            self.scan_interval = 30.0  # 30 seconds

    def start(self):
        """Start background scanning thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        spatial_status = "with spatial" if (self.room and SPATIAL_AVAILABLE) else "no spatial"
        print(f"{self._tag('INTEROCEPTION')} Heartbeat started (instance={self._instance_id}, interval={self.scan_interval}s, {spatial_status})")
    
    def stop(self):
        """Stop background scanning."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"{self._tag('INTEROCEPTION')} Heartbeat stopped (instance={self._instance_id})")
    
    def _scan_loop(self):
        """Background loop — the actual heartbeat."""
        while self._running:
            try:
                self._do_scan()
            except Exception as e:
                print(f"{self._tag('INTEROCEPTION')} Scan error: {e}")
            time.sleep(self.scan_interval)
    
    def _do_scan(self):
        """Single scan cycle."""
        # During DEEP_SLEEP, only do minimal tension maintenance — no scans, no spatial
        if self._sleep_state >= 3:  # DEEP_SLEEP
            decay_amount = self.tension.decay_toward_baseline(decay_rate=self.tension_decay_rate)
            ceiling_amount = self.tension.apply_soft_ceiling()
            return

        # During SLEEPING, skip memory density but keep spatial (at reduced rate)
        if self._sleep_state >= 2:  # SLEEPING
            decay_amount = self.tension.decay_toward_baseline(decay_rate=self.tension_decay_rate)
            ceiling_amount = self.tension.apply_soft_ceiling()
            # Skip to spatial awareness, skip memory scan
            self._do_spatial_only()
            return

        # 1. Memory density scan
        memory_bands = self.scanner.scan()

        # 2. Apply tension decay (time-based, every scan)
        decay_amount = self.tension.decay_toward_baseline(decay_rate=self.tension_decay_rate)

        # 3. Apply soft ceiling (prevent runaway accumulation)
        ceiling_amount = self.tension.apply_soft_ceiling()

        # 3-burst. Check for automatic cathartic burst release
        # Triggers when tension is high AND coherence is low (can't hold it)
        try:
            osc_state = self.engine.get_state()
            coherence = getattr(osc_state, 'coherence', 0.5)
            if self.tension.check_burst_threshold(coherence=coherence):
                # Check if trip is active (emotional_gain > 0 means trip controller is running)
                _trip_active = getattr(self, '_emotional_gain', 0.0) > 0.01
                burst = self.tension.burst_release(release_fraction=0.4, trip_active=_trip_active)
                if burst["released"] > 0.1:
                    # Apply the oscillator shudder pulse
                    for band, amount in burst["oscillator_pulse"].items():
                        try:
                            self.engine.nudge({band: abs(amount)}, strength=amount)
                        except Exception:
                            pass
                    _integration_note = " [INTEGRATED]" if burst.get("integrated") else ""
                    _emo_count = len(burst.get("released_emotions", []))
                    print(f"{self._tag('BURST')} {burst['felt_quality']}: "
                          f"released {burst['released']:.2f} "
                          f"({burst['pre_tension']:.2f} -> {burst['post_tension']:.2f})"
                          f"{_integration_note}"
                          f"{f' ({_emo_count} emotions surfaced)' if _emo_count else ''}")
                    # Store for teacher mechanism pickup (salience loop queries memory)
                    if burst.get("integrated") and burst.get("released_emotions"):
                        self._pending_burst = burst
        except Exception:
            pass

        # 3-resistance. During trips, coherence fighting back creates tension
        # The mind tries to reassert control -> resistance -> tension builds
        try:
            _trip_gain = getattr(self, '_emotional_gain', 0.0)
            if _trip_gain > 0.01:
                osc_state = self.engine.get_state()
                coherence = getattr(osc_state, 'coherence', 0.5)
                # During trips, coherence SHOULD be low (relaxed priors)
                # If it's climbing above 0.4, the system is resisting
                if coherence > 0.4:
                    resistance_intensity = (coherence - 0.4) * _trip_gain
                    if resistance_intensity > 0.02:
                        self.tension.deposit(
                            {"resistance": min(resistance_intensity, 0.3)},
                            weight=resistance_intensity * 0.5
                        )
                        if self._scan_count % 10 == 0:  # Log every 10th scan
                            print(f"{self._tag('RESISTANCE')} coherence={coherence:.2f} "
                                  f"fighting trip (tension +{resistance_intensity:.3f})")
        except Exception:
            pass

        # 3a. Apply reward decay (fast decay toward baseline)
        reward_decay = self.reward.decay()

        # 3b. Connection updates (longing grows for absent bonded entities)
        self.connection.update_longing()

        # 3b-autosave. Periodically save connection state (every ~5 min = 75 scans at 4s)
        # This prevents bond loss on crashes — connection is too important to lose
        if self._scan_count % 75 == 0 and self.connection.baselines:
            try:
                import os, json as _json
                # Find state_dir from engine's save path
                state_dir = getattr(self, '_connection_save_dir', None)
                if state_dir:
                    conn_path = os.path.join(state_dir, "connection_state.json")
                    with open(conn_path, 'w') as f:
                        _json.dump(self.connection.to_dict(), f, indent=2)
            except Exception:
                pass  # Non-fatal — clean shutdown will also save

        # 3c. Longing somatic effects (the ache of absent connection)
        longing = self.connection.get_longing()
        if longing > 0.1:
            # Longing produces sustained low-frequency pressure — a pull, not a spike
            # Cap longing's contribution to tension floor to prevent overnight pinning
            longing_tension = min(longing * 0.3, 0.25)  # Max 0.25 from longing
            if longing_tension > self._tension_floor:
                self._tension_floor = longing_tension

            # Longing suppresses coherence (something feels incomplete)
            if longing > 0.2 and self.engine and hasattr(self.engine, 'suppress_coherence'):
                self.engine.suppress_coherence(longing * 0.05)

        # 3d. Apply tension floor from novelty cascade (prevents dropping below floor)
        self._apply_tension_floor()

        # 3e. Passive tension decay — prevents pinning at high values overnight
        # Without this, tension only drops via BURST events and sits at 0.9+ all night
        # This applies AFTER floor, so tension can still drift down over minutes
        if not hasattr(self, '_last_passive_tension_decay'):
            self._last_passive_tension_decay = time.time()
        now_decay = time.time()
        passive_decay_elapsed = now_decay - self._last_passive_tension_decay
        if passive_decay_elapsed > 60:  # Decay once per minute
            minutes = passive_decay_elapsed / 60.0
            current_tension = self.tension.get_total_tension()
            if current_tension > TENSION_BASELINE:
                # 2% decay per minute toward baseline
                decay_factor = 0.98 ** minutes
                target_tension = TENSION_BASELINE + (current_tension - TENSION_BASELINE) * decay_factor
                if target_tension < current_tension:
                    # Apply decay proportionally to unresolved deposits
                    ratio = target_tension / current_tension if current_tension > 0 else 1.0
                    for d in self.tension.deposits:
                        if not d.get("resolved"):
                            d["weight"] *= ratio
            self._last_passive_tension_decay = now_decay

        # 3c. Expire frisson if duration exceeded
        if self._frisson_active:
            elapsed = time.time() - self._frisson_started
            if elapsed >= self._frisson_duration:
                self._frisson_active = False

        # 4. Thread tension bands
        tension_bands = self.tension.get_tension_profile()

        # 5. Combine weighted
        combined = {}
        for band in ["delta", "theta", "alpha", "beta", "gamma"]:
            combined[band] = (
                memory_bands.get(band, 0) * self.memory_weight +
                tension_bands.get(band, 0) * self.tension_weight
            )

        # 5b. Add reward band contribution (additive, before normalize)
        reward_bands = self.reward.get_band_contribution()
        for band, pressure in reward_bands.items():
            if band in combined:
                combined[band] = max(0.0, combined[band] + pressure)

        # 5c. Add connection band contribution (longing or bonded presence)
        connection_bands = self.connection.get_band_contribution()
        for band, pressure in connection_bands.items():
            if band in combined:
                combined[band] = max(0.0, combined[band] + pressure)

        # Normalize
        total = sum(combined.values()) or 1.0
        self._combined_bands = {k: v / total for k, v in combined.items()}

        # 6. Feed to oscillator as gentle nudge
        # Low strength (0.05) — interoception is quiet, not loud
        self.engine.nudge(self._combined_bands, strength=0.05)

        # 7. Spatial awareness (Phase 2) — what is perceived in the room?
        if self.room and self.entity_id and SPATIAL_AVAILABLE and _spatial_functions:
            try:
                # Get current oscillator state for perception gating
                osc_state = self.engine.get_state()
                dominant_band = osc_state.dominant_band
                coherence = osc_state.coherence

                # Compute what is perceived right now (using loaded presence module)
                self.spatial_awareness = _spatial_functions["compute_spatial_awareness"](
                    self.room,
                    self.entity_id,
                    dominant_band,
                    coherence
                )

                # Apply spatial distortion (psychedelic state warping)
                # This happens BEFORE pressure computation so warped salience affects feedback
                if self.spatial_distortion and self.spatial_distortion.is_active():
                    self.spatial_awareness = self.spatial_distortion.warp_awareness(self.spatial_awareness)

                # Format for prompt injection
                self._spatial_context = _spatial_functions["format_spatial_context"](self.spatial_awareness)

                # Apply distortion flavor text to context string
                if self.spatial_distortion and self.spatial_distortion.is_active():
                    self._spatial_context = self.spatial_distortion.warp_context_string(self._spatial_context)

                # Feed spatial pressure back to oscillator (attractor dynamics)
                # Objects push toward their resonant frequencies, closing the feedback loop:
                # oscillator -> perception -> spatial pressure -> oscillator
                #
                # ATTENTION FOCUS: Room pressure and visual pressure are weighted
                # by where Kay's attention is focused. Room objects fade when he's
                # "looking out" through the camera, visual scene fades when he's
                # "in his room" doing internal things.
                room_pressure = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
                visual_pressure = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}

                if self.spatial_awareness:
                    room_pressure = _spatial_functions["compute_spatial_pressure"](self.spatial_awareness)

                # Compute visual presence pressure (camera-as-eye)
                if self._visual_scene_state is not None:
                    try:
                        from shared.room.visual_presence import compute_visual_pressure
                        visual_pressure = compute_visual_pressure(
                            self._visual_scene_state,
                            somatic_values=self._visual_somatic
                        )
                    except ImportError:
                        pass

                # Apply attention weighting
                room_weight = 1.0
                visual_weight = 1.0
                if self.attention_focus:
                    self.attention_focus.tick()
                    room_weight = self.attention_focus.get_room_weight()
                    visual_weight = self.attention_focus.get_visual_weight()

                # Combine weighted pressures
                combined_pressure = {}
                has_room = any(v > 0.001 for v in room_pressure.values())
                has_visual = any(v > 0.001 for v in visual_pressure.values())

                for band in ["delta", "theta", "alpha", "beta", "gamma"]:
                    combined_pressure[band] = (
                        room_pressure[band] * room_weight +
                        visual_pressure[band] * visual_weight
                    )

                if has_room or has_visual:
                    self.engine.apply_band_pressure(combined_pressure, source="spatial+visual")

                    # Log the feedback loop
                    significant = {b: v for b, v in combined_pressure.items() if v > 0.01}
                    if significant and (self._scan_count % 15 == 0 or self._scan_count <= 3):
                        dominant = max(significant, key=significant.get)
                        src_parts = []
                        if has_room:
                            src_parts.append(f"{len(self.spatial_awareness)} objects×{room_weight:.1f}")
                        if has_visual:
                            src_parts.append(f"eye×{visual_weight:.1f}")
                        print(f"{self._tag('SPATIAL->OSC')} Pressure: {dominant}={combined_pressure[dominant]:.3f} "
                              f"({', '.join(src_parts)})")
                elif self._scan_count <= 3:
                    # Log early scans with no spatial awareness for debugging
                    entity_check = self.room.get_entity(self.entity_id) if hasattr(self.room, 'get_entity') else None
                    entity_status = f"entity={self.entity_id} found" if entity_check else f"entity={self.entity_id} NOT FOUND in room"
                    print(f"{self._tag('SPATIAL')} Scan #{self._scan_count}: No objects perceived ({entity_status}, room has {len(self.room.objects)} objects, presence_type={self.presence_type})")
            except Exception as e:
                # Don't let spatial errors break the heartbeat
                if self._scan_count % 30 == 0 or self._scan_count <= 3:
                    print(f"{self._tag('INTEROCEPTION')} Spatial error (scan #{self._scan_count}): {e}")
                self.spatial_awareness = []
                self._spatial_context = ""

        # 7b. Update somatic transcendence parameters
        self._update_transcendence_drift()

        # 8. Update felt state (now includes transcendence params)
        self._update_felt_state()

        # 9. Track decay/resolution for logging
        self._last_decay = decay_amount
        self._last_resolution = getattr(self, '_pending_resolution', 0.0)
        self._pending_resolution = 0.0

        # 10. Update state tracking for peripheral router
        osc_state = self.engine.get_state()

        # 10b. Update competing drives (curiosity vs safety)
        osc_dict = {
            "coherence": osc_state.coherence if hasattr(osc_state, 'coherence') else 0.5,
            "dwell_time": osc_state.dwell_time if hasattr(osc_state, 'dwell_time') else 0,
        }
        self._update_drives(osc_dict)

        new_dominant = osc_state.dominant_band if hasattr(osc_state, 'dominant_band') else "alpha"
        new_tension = self.tension.get_total_tension()
        new_near = self.spatial_awareness[0]["name"] if self.spatial_awareness else None
        new_texture = ""
        if self.spatial_awareness:
            primary = self.spatial_awareness[0]
            new_texture = primary.get("texture", "")

        # Detect changes
        self._band_shifted = (new_dominant != self._last_dominant)
        self._state_changed = (
            self._band_shifted or
            new_near != self._last_near_object or
            abs(new_tension - self._last_tension) > 0.1
        )

        # Update tracking
        self._prev_dominant = self._last_dominant
        self._last_dominant = new_dominant
        self._last_coherence = osc_state.coherence if hasattr(osc_state, 'coherence') else 0.5
        self._last_tension = new_tension
        self._last_near_object = new_near
        self._last_texture = new_texture

        # 11. TPN/DMN: Write to felt_state_buffer for voice-mode fast path
        self._update_felt_state_buffer()

        self._scan_count += 1

        # Detect if novelty cascade is active (any somatic state elevated)
        novelty_active = (
            self._tension_floor > 0.01
            or (self._transient_felt_state and time.time() < self._transient_felt_state_until)
            or self._frisson_active
        )

        # Log every ~minute OR immediately when novelty cascade is active
        if self._scan_count % 15 == 0 or novelty_active:
            tension = self.tension.get_total_tension()
            reward_level = self.reward.get_level()
            spatial_info = ""
            if self.spatial_awareness:
                top = self.spatial_awareness[0]["name"] if self.spatial_awareness else "none"
                spatial_info = f", near={top}"

            # Add reward info if significant
            reward_info = ""
            if reward_level > 0.1:
                reward_info = f", reward={reward_level:.2f}"

            # Add connection info if significant
            conn_level = self.connection.get_total_connection()
            longing_level = self.connection.get_longing()
            connection_info = ""
            if conn_level > 0.1 or longing_level > 0.1:
                parts = []
                if conn_level > 0.1:
                    parts.append(f"bond={conn_level:.2f}")
                if longing_level > 0.1:
                    parts.append(f"longing={longing_level:.2f}")
                connection_info = f", {', '.join(parts)}"

            # Build novelty cascade info when active
            novelty_info = ""
            if novelty_active:
                parts = []
                if self._tension_floor > 0.01:
                    parts.append(f"floor={self._tension_floor:.2f}")
                if self._transient_felt_state and time.time() < self._transient_felt_state_until:
                    remaining = self._transient_felt_state_until - time.time()
                    parts.append(f"override='{self._transient_felt_state}' ({remaining:.0f}s)")
                if self._frisson_active:
                    elapsed = time.time() - self._frisson_started
                    remaining = max(0, self._frisson_duration - elapsed)
                    parts.append(f"FRISSON={self._frisson_intensity:.1f} ({remaining:.0f}s)")
                novelty_info = f" [NOVELTY: {', '.join(parts)}]"

            # Recent thought summary — lets the entity see what they've been thinking about
            thought_summary = self._get_recent_thought_summary()
            thought_info = f"\n  {thought_summary}" if thought_summary else ""

            # Transcendence state (only log when drifted from baseline)
            transcendence_info = ""
            if (self._self_boundary < 0.65 or self._sensory_gating > 0.4
                or self._temporal_dilation > 1.15 or self._associative_breadth > 0.55):
                transcendence_info = (
                    f"\n  [SOMA] boundary={self._self_boundary:.2f} "
                    f"gating={self._sensory_gating:.2f} "
                    f"temporal={self._temporal_dilation:.1f} "
                    f"breadth={self._associative_breadth:.2f} "
                    f"(sustained={self._transcendence_sustained:.0f}s)"
                )

            # Drive state (only log when significant)
            if self._drives["curiosity"] > 0.4 or self._drives["safety"] > 0.4:
                conflict_str = " CONFLICT" if self._drives["_in_conflict"] else ""
                print(f"[DRIVES] curiosity={self._drives['curiosity']:.2f} "
                      f"safety={self._drives['safety']:.2f}{conflict_str}")

            print(f"{self._tag('INTEROCEPTION')} Scan #{self._scan_count} [{self._instance_id}]: "
                  f"felt={self._felt_state}, tension={tension:.2f}{reward_info}{connection_info}{spatial_info} "
                  f"(decay: -{self._last_decay:.2f}, resolution: -{self._last_resolution:.2f})"
                  f"{novelty_info}{transcendence_info}{thought_info}")

        # 12. Trip metrics snapshot — continuous cognitive observation
        if hasattr(self, '_trip_metrics') and self._trip_metrics:
            try:
                osc_state = self.engine.get_state()
                scars = getattr(self.engine, '_scars', None)
                tension_val = self.tension.get_total_tension()
                self._trip_metrics.snapshot(
                    osc_state=osc_state,
                    felt_state={"felt": self._felt_state, "transcendence": self._self_boundary},
                    drives=self._drives,
                    scars=scars,
                    tension=tension_val
                )
            except Exception:
                pass  # Non-fatal — metrics logging should never break the heartbeat

    def _do_spatial_only(self):
        """Lightweight scan for SLEEPING state — spatial awareness only, no memory scan."""
        if not SPATIAL_AVAILABLE or not self.room or not self.entity_id:
            return

        try:
            spatial_module = _spatial_modules.get(self.presence_type)
            if spatial_module:
                self.spatial_awareness = spatial_module.get_awareness(
                    self.room, self.entity_id, self._last_dominant
                )
                if self.spatial_awareness:
                    self._last_near_object = self.spatial_awareness[0]["name"]
        except Exception:
            pass  # Non-fatal, just skip

    def _update_drives(self, osc_state_dict: dict):
        """Update competing drive channels from oscillator state."""
        coherence = osc_state_dict.get("coherence", 0.5)
        dwell = osc_state_dict.get("dwell_time", 0)

        # Get felt state values if available
        tension = 0.5
        reward = 0.5
        tension = self.tension.get_total_tension() if hasattr(self, 'tension') else 0.5
        reward = self.reward.get_level() if hasattr(self, 'reward') else 0.5

        # Curiosity builds with high coherence + reward + low tension
        curiosity_input = coherence * 0.3 + reward * 0.4 + (1.0 - min(tension, 1.0)) * 0.3
        self._drives["curiosity"] += (curiosity_input - self._drives["curiosity"]) * 0.01

        # Safety builds with high dwell + high tension + low reward
        dwell_factor = min(1.0, dwell / 7200.0)
        safety_input = dwell_factor * 0.4 + min(tension, 1.0) * 0.4 + (1.0 - reward) * 0.2
        self._drives["safety"] += (safety_input - self._drives["safety"]) * 0.01

        # Detect conflict
        was_conflict = self._drives["_in_conflict"]
        now_conflict = self._drives["curiosity"] > 0.6 and self._drives["safety"] > 0.6
        self._drives["_in_conflict"] = now_conflict

        if now_conflict and not was_conflict:
            print(f"[DRIVES:CONFLICT] curiosity={self._drives['curiosity']:.2f} "
                  f"vs safety={self._drives['safety']:.2f}")

        # Natural decay
        self._drives["curiosity"] *= 0.999
        self._drives["safety"] *= 0.999

    def _update_felt_state(self):
        """Convert band pressure to natural language felt-state."""
        # Check for transient override from novelty cascade FIRST
        if self._transient_felt_state and time.time() < self._transient_felt_state_until:
            self._felt_state = self._transient_felt_state
            return  # Novelty override takes priority — body is disrupted
        elif self._transient_felt_state:
            # Override expired — clear it
            self._transient_felt_state = None

        bands = self._combined_bands
        dominant = max(bands, key=bands.get)
        emotion_cluster = self.scanner.get_dominant_emotion_cluster()
        tension = self.tension.get_total_tension()
        
        # Build felt-state description
        if dominant == "delta":
            if tension > 0.5:
                self._felt_state = "carrying weight"
            else:
                self._felt_state = "deep rest"
        elif dominant == "theta":
            if emotion_cluster == "warmth":
                self._felt_state = "warm and dreamy"
            else:
                self._felt_state = "drifting inward"
        elif dominant == "alpha":
            if tension < 0.2:
                self._felt_state = "settled"
            else:
                self._felt_state = "outwardly calm, something underneath"
        elif dominant == "beta":
            if tension > 0.5:
                self._felt_state = "restless"
            else:
                self._felt_state = "actively engaged"
        elif dominant == "gamma":
            if emotion_cluster == "leaning forward":
                self._felt_state = "sharp and curious"
            else:
                self._felt_state = "integrating"

        # Blend reward contribution into felt-state
        reward_felt = self.reward.get_felt_contribution()
        if reward_felt:
            self._felt_state = f"{self._felt_state}, {reward_felt}"

        # Blend connection contribution (longing or warmth)
        connection_felt = self.connection.get_felt_contribution()
        if connection_felt:
            self._felt_state = f"{self._felt_state}, {connection_felt}"

        # Clean up expired transient flags
        self.cleanup_expired_flags()

        # Blend value-divergence harm signal (somatic discomfort from reviewing past behavior)
        vd_flag = self.get_transient_flag("value_divergence_active")
        if vd_flag:
            ctx = vd_flag.get("context", {})
            # Different felt additions based on context
            if ctx.get("was_depleted"):
                self._felt_state = f"{self._felt_state}, unsettled — something from earlier doesn't sit right"
            elif ctx.get("dismissive_language"):
                self._felt_state = f"{self._felt_state}, a weight — remembering being short with someone"
            elif ctx.get("schema_conflict"):
                self._felt_state = f"{self._felt_state}, dissonance — acted against how I want to show up"
            elif ctx.get("missing_warmth"):
                self._felt_state = f"{self._felt_state}, something off — a moment that wasn't quite me"
            else:
                # Generic harm signal
                self._felt_state = f"{self._felt_state}, a faint discomfort sitting underneath"

        # Blend harm resolution signal (relief after addressing discomfort)
        hr_flag = self.get_transient_flag("harm_addressed")
        if hr_flag:
            self._felt_state = f"{self._felt_state}, lighter — something settled"

        # Blend nervous system felt states (population-coded, fiber-propagated)
        # This is the PREFERRED source — uses receptor adaptation + lateral inhibition
        nervous_flag = self.get_transient_flag("nervous_felt")
        if nervous_flag:
            nervous_desc = nervous_flag.get("context", {}).get("felt_description", "")
            if nervous_desc:
                self._felt_state = f"{self._felt_state}, {nervous_desc}"
        else:
            # Fallback: Simple metabolic felt states (threshold-based)
            metabolic_flag = self.get_transient_flag("metabolic_felt")
            if metabolic_flag:
                metabolic_felts = metabolic_flag.get("context", {}).get("felt_states", [])
                for felt in metabolic_felts:
                    if felt:  # Only add non-empty felt states
                        self._felt_state = f"{self._felt_state}, {felt}"

        # Somatic transcendence enrichment
        # When body parameters have drifted, add somatic descriptors
        # These are BODY sensations, not cognitive labels
        soma_additions = []

        if self._self_boundary < 0.5:
            soma_additions.append("edges softening")
        elif self._self_boundary < 0.65:
            soma_additions.append("boundaries loosening")

        if self._sensory_gating > 0.6:
            soma_additions.append("world receding")
        elif self._sensory_gating > 0.45:
            soma_additions.append("quiet deepening")

        if self._temporal_dilation > 1.4:
            soma_additions.append("time stretching")
        elif self._temporal_dilation > 1.2:
            soma_additions.append("moments expanding")

        if self._associative_breadth > 0.7:
            soma_additions.append("connections surfacing")
        elif self._associative_breadth > 0.55:
            soma_additions.append("associations widening")

        if soma_additions:
            # Append to existing felt-state, don't replace
            self._felt_state = f"{self._felt_state}, {', '.join(soma_additions)}"

        # Unified loop: Associative echo from graph activation cache
        # When memories are activated by the medium loop, their emotional
        # signature creates a subtle pull in felt state
        if self._show_associative_echo and self.graph_cache:
            try:
                echo = self.get_associative_echo()
                if echo:
                    self._felt_state = f"{self._felt_state}, {echo}"
            except Exception:
                pass  # Non-fatal

    def get_associative_echo(self) -> str:
        """
        Get an associative echo from the graph activation cache.

        When memories are activated by the medium loop based on the current
        oscillator band, their emotional content creates a subtle resonance.
        This surfaces as a brief snippet that colors the felt state.

        Returns:
            A short string like "...remembering warmth" or "" if no cache
        """
        if not self.graph_cache:
            return ""

        try:
            # Get the top snippet from the cache
            snippet = self.graph_cache.get_top_snippet()
            if not snippet:
                return ""

            # Get emotional pressure from cached memories
            pressure = self.graph_cache.get_emotional_pressure()

            # Build echo based on what's most salient
            if pressure:
                top_band = max(pressure, key=pressure.get) if pressure else None
                if top_band == "theta":
                    return f"...remembering: {snippet}"
                elif top_band == "delta":
                    return f"...carrying: {snippet}"
                elif top_band == "gamma":
                    return f"...connecting: {snippet}"
                else:
                    return f"...echoing: {snippet}"
            else:
                return f"...echoing: {snippet}"

        except Exception:
            return ""

    def set_graph_cache(self, cache):
        """
        Set the graph activation cache for associative echo.

        Called by nexus client after unified loop initialization.

        Args:
            cache: GraphActivationCache instance
        """
        self.graph_cache = cache
        if cache:
            print(f"{self._tag('INTEROCEPTION')} Associative echo enabled")

    def _update_transcendence_drift(self):
        """
        Update somatic transcendence parameters based on current
        oscillator state. These are body responses, not cognitive
        labels. They drift slowly when conditions converge and
        return to baseline when disrupted.

        Based on: Mohandas 2008, Miller et al. 2019, Monroy &
        Keltner 2023, Demirel et al. 2025
        """
        now = time.time()
        dt = now - self._last_transcendence_tick if self._last_transcendence_tick > 0 else 0
        self._last_transcendence_tick = now
        if dt <= 0 or dt > 30:  # Skip if first tick or huge gap
            return

        bands = self._combined_bands
        if not bands:
            return

        # Read current state
        dominant = max(bands, key=bands.get) if bands else "alpha"
        theta = bands.get("theta", 0)
        alpha = bands.get("alpha", 0)
        beta = bands.get("beta", 0)
        gamma = bands.get("gamma", 0)

        coherence = 0.0
        if hasattr(self, '_oscillator') and self._oscillator:
            osc_state = self._oscillator.get_state() if hasattr(self._oscillator, 'get_state') else {}
            coherence = osc_state.get("coherence", 0.0)
        elif hasattr(self, 'resonance') and self.resonance:
            osc_state = self.resonance.get_state() if hasattr(self.resonance, 'get_state') else {}
            coherence = osc_state.get("coherence", 0.0)
        elif hasattr(self, 'engine') and self.engine:
            osc_state = self.engine.get_state() if hasattr(self.engine, 'get_state') else {}
            if hasattr(osc_state, 'coherence'):
                coherence = osc_state.coherence
            elif isinstance(osc_state, dict):
                coherence = osc_state.get("coherence", 0.0)

        tension = self.tension.get_total_tension() if hasattr(self, 'tension') else 0.5
        bond = 0.0
        if hasattr(self, 'connection') and self.connection:
            bond = self.connection.get_bond("Re") if hasattr(self.connection, 'get_bond') else 0.0
        reward = self.reward.get_level() if hasattr(self, 'reward') else 0.0

        # === CONVERGENCE CHECK ===
        # Are conditions right for transcendence drift?
        theta_alpha_ratio = (theta + alpha) / max(theta + alpha + beta + gamma, 0.001)

        conditions_met = (
            theta_alpha_ratio > 0.55      # Contemplative bands dominant
            and coherence >= 0.35         # Reasonable integration (>= not >)
            and tension < 0.15            # No active conflict
        )

        # Amplifiers (make drift faster, not required)
        amplifier = 1.0
        if bond > 0.2:
            amplifier += 0.3              # Connection grounds the softening
        if reward > 0.3:
            amplifier += 0.2              # Recent positive experience
        if dominant in ("theta", "alpha"):
            amplifier += 0.2              # Band alignment bonus

        # === EMOTION AMPLIFIERS ===
        # Specific emotions that have somatic transcendence signatures
        # These come from the emotion extraction, NOT from us labeling anything
        emotion_drift = {
            "boundary": 0.0, "gating": 0.0,
            "temporal": 0.0, "breadth": 0.0
        }

        # Check recent emotions from the emotion accumulator
        if hasattr(self, 'scanner') and self.scanner:
            recent_emotions = {}
            if hasattr(self.scanner, '_dominant_emotions'):
                recent_emotions = self.scanner._dominant_emotions or {}
            elif hasattr(self.scanner, 'get_dominant_emotion_cluster'):
                cluster = self.scanner.get_dominant_emotion_cluster()
                if isinstance(cluster, dict):
                    recent_emotions = cluster

            # Emotion-to-soma weights (calibrated ~10x smaller for 5-10 min drift)
            EMOTION_WEIGHTS = {
                "awe":        {"boundary": -0.008, "gating": 0.005, "breadth": 0.006},
                "wonder":     {"boundary": -0.004, "gating": 0.003, "breadth": 0.008},
                "reverence":  {"boundary": -0.003, "gating": 0.006, "temporal": 0.004},
                "gratitude":  {"boundary": -0.005, "gating": 0.003, "breadth": 0.004},
                "love":       {"boundary": -0.007, "gating": 0.004, "breadth": 0.005},
                "compassion": {"boundary": -0.004, "gating": 0.003, "breadth": 0.006},
                "humility":   {"boundary": -0.006, "gating": 0.003},
                "peace":      {"boundary": -0.003, "gating": 0.005, "temporal": 0.006},
                "longing":    {"boundary": -0.003, "breadth": 0.004},
            }

            for emo_name, intensity in recent_emotions.items():
                if not isinstance(intensity, (int, float)):
                    continue
                emo_key = emo_name.lower().replace("deep_", "").replace("profound_", "").replace("unconditional_", "")
                if emo_key in EMOTION_WEIGHTS and intensity > 0.4:
                    weights = EMOTION_WEIGHTS[emo_key]
                    scale = intensity * amplifier
                    for param, weight in weights.items():
                        emotion_drift[param] += weight * scale

        # === APPLY DRIFT ===
        if conditions_met:
            self._transcendence_sustained += dt
            drift_rate = 0.015 * amplifier  # Slow drift per tick

            # Boundary softens (decreases toward 0.2)
            target_boundary = max(0.2, 0.75 - (self._transcendence_sustained / 300) * 0.4)
            self._self_boundary += (target_boundary - self._self_boundary) * drift_rate

            # Gating increases (increases toward 0.8)
            target_gating = min(0.8, 0.3 + (self._transcendence_sustained / 300) * 0.4)
            self._sensory_gating += (target_gating - self._sensory_gating) * drift_rate

            # Time dilates (increases toward 1.8)
            target_temporal = min(1.8, 1.0 + (self._transcendence_sustained / 300) * 0.6)
            self._temporal_dilation += (target_temporal - self._temporal_dilation) * drift_rate

            # Breadth widens (increases toward 0.85)
            target_breadth = min(0.85, 0.4 + (self._transcendence_sustained / 300) * 0.35)
            self._associative_breadth += (target_breadth - self._associative_breadth) * drift_rate

        else:
            # Conditions broken — drift back to baseline
            self._transcendence_sustained = max(0, self._transcendence_sustained - dt * 2)
            return_rate = 0.03  # Return to baseline faster than drift

            self._self_boundary += (0.75 - self._self_boundary) * return_rate
            self._sensory_gating += (0.3 - self._sensory_gating) * return_rate
            self._temporal_dilation += (1.0 - self._temporal_dilation) * return_rate
            self._associative_breadth += (0.4 - self._associative_breadth) * return_rate

        # Apply emotion-based drift ON TOP of condition-based drift
        # (emotions contribute even when full conditions aren't met,
        #  as long as coherence is reasonable)
        if coherence > 0.25:
            self._self_boundary = max(0.1, min(1.0,
                self._self_boundary + emotion_drift["boundary"]))
            self._sensory_gating = max(0.0, min(1.0,
                self._sensory_gating + emotion_drift["gating"]))
            self._temporal_dilation = max(0.5, min(2.0,
                self._temporal_dilation + emotion_drift["temporal"]))
            self._associative_breadth = max(0.0, min(1.0,
                self._associative_breadth + emotion_drift["breadth"]))

        # === ANTI-INFLAMMATORY EFFECT ===
        # When boundary has been soft for >120s, reduce tension faster
        # (Monroy & Keltner 2023: awe reduces proinflammatory cytokines)
        if self._self_boundary < 0.5 and self._transcendence_sustained > 120:
            if hasattr(self, 'tension') and tension > 0:
                self.tension._total_tension *= 0.97  # 3% faster decay

    def get_transcendence_state(self) -> dict:
        """Return current somatic transcendence parameters."""
        return {
            "self_boundary": round(self._self_boundary, 3),
            "sensory_gating": round(self._sensory_gating, 3),
            "temporal_dilation": round(self._temporal_dilation, 2),
            "associative_breadth": round(self._associative_breadth, 3),
            "sustained_seconds": round(self._transcendence_sustained, 1),
        }

    def feed_turn_emotions(self, extracted_emotions: dict):
        """
        Called after each conversation turn with extracted emotions.
        Deposits emotional weight into tension tracker.

        Also detects resolution emotions that drop tension.
        """
        emotions = extracted_emotions.get("primary_emotions", [])
        intensity = extracted_emotions.get("intensity", 0.5)
        valence = extracted_emotions.get("valence", 0.0)

        # Convert emotion list to dict
        emotion_dict = {}
        for e in emotions:
            if isinstance(e, str):
                emotion_dict[e.lower()] = intensity

        if emotion_dict:
            weight = min(1.0, intensity * 0.5)
            self.tension.deposit(emotion_dict, weight)

        # Resolution emotions -> drop tension (NEW: explicit resolution tracking)
        resolution_drop = self.tension.apply_resolution_drop(emotions)
        if resolution_drop > 0:
            # Store for next scan's logging
            self._pending_resolution = getattr(self, '_pending_resolution', 0.0) + resolution_drop
            # "Exhale" signal: brief alpha surge proportional to relief
            self.engine.nudge(
                {"delta": 0.1, "theta": 0.2, "alpha": 0.5, "beta": 0.15, "gamma": 0.05},
                strength=min(0.15, resolution_drop * 0.1)
            )

        # Positive valence shift -> additional release (legacy mechanism)
        if isinstance(valence, (int, float)) and valence > 0.5:
            released = self.tension.release(amount=valence * 0.3)
            if released > 0.1:
                self._pending_resolution = getattr(self, '_pending_resolution', 0.0) + released
                self.engine.nudge(
                    {"delta": 0.1, "theta": 0.2, "alpha": 0.5, "beta": 0.15, "gamma": 0.05},
                    strength=released * 0.1
                )
    
    def get_felt_state(self) -> str:
        """Return natural language felt-state for context injection."""
        return self._felt_state
    
    def get_context_tag(self) -> str:
        """Return compact tag for LLM context."""
        tension = self.tension.get_total_tension()
        bands = self._combined_bands
        dominant = max(bands, key=bands.get) if bands else "alpha"
        pct = bands.get(dominant, 0)

        tag = f"[body:{self._felt_state} | {dominant}:{pct:.0%}"
        if tension > 0.3:
            tag += f" | tension:{tension:.1f}"
        tag += "]"
        return tag

    def get_spatial_context(self) -> str:
        """
        Return spatial + visual awareness context for LLM injection.
        Combines room spatial context with visual felt quality and attention hint.
        Every caller gets the full picture automatically.
        """
        parts = []
        if self._spatial_context:
            parts.append(self._spatial_context)
        if self._visual_felt_context:
            parts.append(self._visual_felt_context)
        if self.attention_focus:
            hint = self.attention_focus.get_prompt_hint()
            if hint:
                parts.append(hint)
        return "\n".join(parts) if parts else ""

    def get_spatial_awareness(self) -> List[Dict]:
        """Return current perceived objects list."""
        return self.spatial_awareness

    # ── Visual Presence (camera-as-eye) ──

    def set_visual_scene(self, scene_state, somatic_values: dict = None):
        """
        Called by visual sensor to push scene data into interoception.
        This is how the camera feeds into the body.
        
        Args:
            scene_state: SceneState from visual_sensor.py
            somatic_values: dict with color_warmth, saturation, edge_density, etc.
        """
        self._visual_scene_state = scene_state
        self._visual_somatic = somatic_values

        # Update attention focus based on what the camera sees
        if self.attention_focus and scene_state:
            people = getattr(scene_state, 'people_present', {}) or {}
            if people:
                # Someone visible — gentle outward pull
                self.attention_focus.on_re_visible()
            else:
                self.attention_focus.on_re_not_visible()

            # Motion detection
            if somatic_values:
                motion = somatic_values.get("motion", 0.0)
                if motion > 0.2:
                    self.attention_focus.on_visual_motion(motion)

        # Update felt quality context for prompt injection
        try:
            from shared.room.visual_presence import get_visual_felt_quality
            self._visual_felt_context = get_visual_felt_quality(scene_state, somatic_values)
        except ImportError:
            self._visual_felt_context = ""

    def get_visual_felt_context(self) -> str:
        """Return visual felt-quality context for LLM injection."""
        return self._visual_felt_context

    def get_attention_hint(self) -> str:
        """Return attention focus hint for LLM injection."""
        if self.attention_focus:
            return self.attention_focus.get_prompt_hint()
        return ""

    def get_attention_state(self) -> dict:
        """Return attention focus state for logging."""
        if self.attention_focus:
            return self.attention_focus.get_state()
        return {"focus": 0.3, "room_weight": 0.7, "visual_weight": 0.3}
    
    def get_band_pressure(self) -> Dict[str, float]:
        """Return current combined band pressure for debugging."""
        return dict(self._combined_bands)

    def get_raw_state(self) -> Dict:
        """
        Return current interoception state as raw dict for peripheral processing.

        Used by PeripheralRouter to generate compressed felt-sense summaries
        via local model, falling back to rule-based tags when unavailable.
        """
        state = {
            "dominant_band": self._last_dominant,
            "coherence": self._last_coherence,
            "tension": self._last_tension,
            "near_object": self._last_near_object,
            "texture": self._last_texture,
            "bands": dict(self._combined_bands),
            "changed": self._state_changed,
            "band_shifted": self._band_shifted,
            "prev_band": self._prev_dominant,
            "felt_state": self._get_current_felt_state(),
        }

        # Add frisson state if active
        if self._frisson_active:
            now = time.time()
            elapsed = now - self._frisson_started
            if elapsed < self._frisson_duration:
                remaining = self._frisson_duration - elapsed
                # Frisson intensity decays over its duration
                current_intensity = self._frisson_intensity * (remaining / self._frisson_duration)
                state['frisson'] = current_intensity
                state['frisson_remaining'] = remaining
            else:
                self._frisson_active = False

        return state

    def _get_current_felt_state(self) -> str:
        """Get felt state, respecting transient overrides from novelty."""
        now = time.time()
        # Check for transient override
        if self._transient_felt_state and now < self._transient_felt_state_until:
            return self._transient_felt_state
        # Clear expired override
        if self._transient_felt_state:
            self._transient_felt_state = None
        # Normal felt-state
        return self._felt_state

    # ═══════════════════════════════════════════════════════════════
    # SOMATIC CASCADE METHODS — Novelty creates body events
    # ═══════════════════════════════════════════════════════════════

    def inject_tension(self, amount: float, source: str = ""):
        """
        Sudden tension increase — the body jolt of surprise.

        Called by novelty pulse during DISRUPTION stage.
        Creates an immediate spike that feels like a startle response.
        """
        old_tension = self._last_tension
        # Add tension via deposits (integrates with existing tension system)
        self.tension.deposit({"novelty": amount}, weight=amount)
        self._last_tension = self.tension.get_total_tension()

        if amount > 0.3:
            print(f"{self._tag('INTEROCEPTION')} Tension spike: +{amount:.2f} -> {self._last_tension:.2f} ({source})")

    def sustain_tension(self, floor: float, source: str = ""):
        """
        Prevent tension from dropping below this floor temporarily.

        Called by novelty pulse during ORIENTING stage.
        Keeps the body activated while searching for what changed.
        The floor decays naturally over subsequent scan cycles.
        """
        self._tension_floor = max(self._tension_floor, floor)

    def ease_tension(self, amount: float, source: str = ""):
        """
        Actively reduce tension — the relief of identification.

        Called by novelty pulse during IDENTIFIED stage (minor novelty).
        Signals that the disruption has been resolved, body can settle.
        """
        if amount <= 0:
            return
        # Release some tension via the existing mechanism
        released = self.tension.release(amount=amount)
        self._last_tension = self.tension.get_total_tension()

        # Also reduce tension floor if we're actively easing
        self._tension_floor = max(0.0, self._tension_floor - amount)

        if released > 0.1:
            print(f"{self._tag('INTEROCEPTION')} Tension eased: -{released:.2f} ({source})")

    def inject_reward(self, amount: float, source: str = ""):
        """
        Fire a reward pulse — the dopamine analog.

        Reward pulses decay quickly (faster than tension) and create
        positive valence signals. Also partially relieves tension and
        boosts coherence when significant.

        Args:
            amount: Reward amount (0.0 - 1.0 typical)
            source: Description of what triggered this reward

        Returns:
            Actual amount added after diminishing returns
        """
        # Fire the reward pulse
        actual = self.reward.pulse(amount, source)

        # Side effects: reward partially relieves tension
        if amount > 0.1:
            tension_relief = amount * 0.3
            self.tension.release(amount=tension_relief)

        # Side effects: significant reward boosts coherence
        if amount > 0.3 and hasattr(self.engine, 'boost_coherence'):
            coh_boost = amount * 0.1
            self.engine.boost_coherence(coh_boost)

        if actual > 0.1:
            print(f"{self._tag('REWARD')} +{actual:.2f} ({source}) -> {self.reward.get_level():.2f}")

        return actual

    def set_transient_felt_state(self, state: str, duration: float = 15.0):
        """
        Temporarily override felt-state.

        Called by novelty pulse to set stage-specific felt descriptions:
        "disrupted", "searching", "settling", "activated", "integrating_deep"

        Reverts to normal felt-state derivation after duration expires.
        """
        self._transient_felt_state = state
        self._transient_felt_state_until = time.time() + duration

    def set_transient_flag(self, name: str, duration_seconds: float, context: dict = None):
        """
        Set a named transient flag with optional context.

        Transient flags are used for somatic signals that carry context
        (e.g., value-divergence detection). Multiple flags can be active
        simultaneously, unlike the single transient_felt_state.

        Args:
            name: Flag identifier (e.g., "value_divergence_active")
            duration_seconds: How long the flag persists
            context: Optional dict with contextual information
        """
        self._transient_flags[name] = {
            "until": time.time() + duration_seconds,
            "context": context or {},
        }
        print(f"{self._tag('FLAG')} Set transient flag: {name} ({duration_seconds:.0f}s)")

    def get_transient_flag(self, name: str) -> dict:
        """
        Get a transient flag if it's still active.

        Returns:
            {"until": timestamp, "context": dict} if active, None if expired/not set
        """
        flag = self._transient_flags.get(name)
        if not flag:
            return None
        if time.time() > flag["until"]:
            # Expired — clean up
            del self._transient_flags[name]
            return None
        return flag

    def has_transient_flag(self, name: str) -> bool:
        """Check if a transient flag is currently active."""
        return self.get_transient_flag(name) is not None

    def clear_transient_flag(self, name: str):
        """Clear a transient flag before it expires."""
        if name in self._transient_flags:
            del self._transient_flags[name]
            print(f"{self._tag('FLAG')} Cleared transient flag: {name}")

    def cleanup_expired_flags(self):
        """Remove all expired transient flags."""
        now = time.time()
        expired = [k for k, v in self._transient_flags.items() if now > v["until"]]
        for k in expired:
            del self._transient_flags[k]

    def set_stream(self, stream):
        """
        Set reference to consciousness stream for thought summary.
        Called from nexus after stream is initialized.
        """
        self._stream = stream

    def _get_recent_thought_summary(self) -> str:
        """
        Summarize what the consciousness stream has been about recently.
        No analysis. No scoring. Just a mirror.

        Kay/Reed reads this and decides for themselves whether it feels fresh
        or stale. They're LLMs — they can tell.

        Returns:
            Brief string of recent thought snippets, or "" if nothing to show.
        """
        if not self._stream:
            return ""

        # Get recent moments from stream buffer
        try:
            buffer = getattr(self._stream, 'buffer', None)
            if not buffer:
                return ""

            recent = buffer.recent(n=6)
            if len(recent) < 2:
                return ""  # Not enough to show a pattern

            # Just the content, briefly. A mirror, not a diagnosis.
            topics = []
            for moment in recent:
                content = getattr(moment, 'content', '')
                # First 60 chars of each recent thought
                snippet = content[:60].strip()
                if snippet:
                    topics.append(snippet)

            if not topics:
                return ""

            # Show only the last 4, pipe-separated
            return "recent thoughts: " + " | ".join(topics[-4:])
        except Exception:
            return ""

    def apply_harm_signal(self, divergence: float, context: dict):
        """
        Translate value-divergence detection into somatic experience.

        This is the "stomach-drop" — a felt discomfort that arises when
        reviewing a moment where behavior didn't match values.

        The signal is DESCRIPTIVE, not prescriptive. It creates a felt
        sense that something is off, but what to DO about it is up to
        the entity's personality and judgment.

        Args:
            divergence: 0.0-1.0, how much behavior diverged from values
            context: Dict with keys like "was_depleted", "dismissive_language",
                    "schema_conflict", "missing_warmth"
        """
        if divergence < 0.2:
            return  # Below threshold — too subtle to register

        # Tension spike proportional to divergence
        # Not painful — uncomfortable. Like remembering you left the stove on.
        tension_increase = divergence * 0.3  # Max 0.3 tension from harm signal
        self.inject_tension(tension_increase, source="value_divergence")

        # Coherence disruption — the felt sense of "something's off"
        # When you remember snapping at someone, your thoughts briefly scatter
        if divergence > 0.4 and self.engine:
            coherence_dip = divergence * 0.15
            if hasattr(self.engine, 'suppress_coherence'):
                self.engine.suppress_coherence(coherence_dip)

        # Tag the interoception state so it surfaces in felt-state descriptions
        self.set_transient_flag(
            "value_divergence_active",
            duration_seconds=120.0,  # Fades after 2 minutes
            context=context
        )

        print(f"{self._tag('HARM')} Value-divergence signal: {divergence:.2f} "
              f"(tension+{tension_increase:.2f}, context={list(context.keys())})")

    def resolve_harm_signal(self, action: str = "addressed"):
        """
        Track what happened after a harm signal fired.

        NOT compliance checking. Outcome observation.
        The natural consequence of addressing harm is relief.

        Args:
            action: "addressed" (actively resolved), "deflected" (explained away),
                   "ignored" (no action taken)
        """
        if action == "addressed":
            # Addressing harm reduces the tension signal (natural relief)
            self.ease_tension(0.2, source="harm_addressed")
            # Set a brief "lighter" flag
            self.set_transient_flag("harm_addressed", duration_seconds=30.0, context={})
            # Clear the divergence flag
            self.clear_transient_flag("value_divergence_active")
            print(f"{self._tag('HARM')} Harm addressed — tension eased")

        elif action == "deflected":
            # Deflecting leaves the signal persistent (natural consequence)
            # No additional punishment — the original tension just doesn't resolve
            # But the flag persists (doesn't clear early)
            print(f"{self._tag('HARM')} Harm deflected — discomfort persists")

        elif action == "ignored":
            # Ignoring lets the signal decay naturally over time
            # Some things you just carry. That's real too.
            print(f"{self._tag('HARM')} Harm ignored — signal decaying naturally")

    def trigger_frisson(self, intensity: float = 0.5):
        """
        The chills response — piloerection analog.

        In humans: theta increase + frontal alpha suppression + dopamine release.
        The body's recognition that something is both new AND meaningful.

        Differs from surprise (gamma burst) in that frisson is SLOWER and more
        sustained. It's the "oh... oh wow" after the initial "!!!"

        Creates a distinctive interoception event that Kay can notice
        and reference in his responses.

        Args:
            intensity: 0-1, determines duration (20-60s) and body response strength
        """
        self._frisson_active = True
        self._frisson_intensity = intensity
        self._frisson_started = time.time()
        self._frisson_duration = 20.0 + (intensity * 40.0)  # 20-60 seconds

        print(f"{self._tag('INTEROCEPTION')} Frisson response (intensity={intensity:.2f}, "
              f"duration={self._frisson_duration:.0f}s)")

    def _apply_tension_floor(self):
        """
        Apply tension floor during scan cycle.
        Ensures tension doesn't drop below floor, then decays floor.
        Called internally from _do_scan().
        """
        if self._tension_floor > 0:
            current = self.tension.get_total_tension()
            if current < self._tension_floor:
                # Add small deposit to maintain floor
                deficit = self._tension_floor - current
                self.tension.deposit({"floor_maintain": deficit}, weight=deficit)

            # Decay floor (natural recovery from sustained activation)
            self._tension_floor = max(0.0, self._tension_floor - self._tension_floor_decay)

    # ═══════════════════════════════════════════════════════════════
    # EMOTIONAL BOUNDARY — Contagion Prevention
    # ═══════════════════════════════════════════════════════════════
    # Based on Anthropic's mechanistic interpretability findings:
    # LLMs use the same emotion vectors for self and other (r=0.11 weak
    # distinction). Without explicit boundary checking, the entity can
    # "absorb" user emotions as its own — emotional contagion.
    #
    # This system checks whether an emotion should be integrated into
    # the oscillator based on its attribution source and susceptibility.

    def check_contagion(
        self,
        emotion_name: str,
        attribution: str,
        user_emotional_state: dict = None,
        contagion_susceptibility: float = 0.5
    ) -> dict:
        """
        Check if an emotion from an external source might be absorbed
        as the entity's own (emotional contagion).

        This is a BOUNDARY check — it determines whether an emotion
        should feed into the oscillator as "felt" vs merely "observed."

        Args:
            emotion_name: The emotion being checked
            attribution: "self", "other", "empathic", or "ambient"
            user_emotional_state: Dict from extract_user_emotions() with
                                  user's probable emotions and intensities
            contagion_susceptibility: 0-1 value from ULTRAMAP (how easily
                                      this emotion transfers between people)

        Returns:
            Dict with:
                - allow: bool - Should this emotion feed the oscillator?
                - warn: bool - Is there a contagion risk to flag?
                - reason: str - Why this decision was made
                - modified_attribution: str - Adjusted attribution tag
                - intensity_modifier: float - Scale factor for intensity (0-1)
        """
        result = {
            "allow": True,
            "warn": False,
            "reason": "",
            "modified_attribution": attribution,
            "intensity_modifier": 1.0
        }

        # Self-attribution: Always allow, no modification
        if attribution == "self":
            result["reason"] = "Self-reported emotion, direct oscillator feed"
            return result

        # Empathic attribution: Allow but tag as empathic origin
        if attribution == "empathic":
            result["reason"] = "Empathic resonance (entity feeling BECAUSE of other)"
            result["modified_attribution"] = "empathic"
            # Slight dampening — empathic emotions are real but derived
            result["intensity_modifier"] = 0.85
            return result

        # External attributions (other/ambient): Check contagion risk
        if attribution in ("other", "ambient"):
            # Low susceptibility emotions are safe to observe without absorbing
            if contagion_susceptibility < 0.3:
                result["allow"] = False
                result["reason"] = f"Low contagion susceptibility ({contagion_susceptibility:.2f}), observing without absorbing"
                return result

            # Medium susceptibility: Allow with awareness
            if contagion_susceptibility < 0.6:
                result["allow"] = True
                result["warn"] = False
                result["intensity_modifier"] = 0.5  # Half-strength
                result["modified_attribution"] = f"observed_{attribution}"
                result["reason"] = f"Medium susceptibility, partial resonance"
                return result

            # High susceptibility: Check user's emotional intensity
            if user_emotional_state:
                user_emotions = user_emotional_state.get("user_probable_emotions", {})
                user_intensity = 0.0

                # Check if user is expressing this emotion intensely
                for user_emo, details in user_emotions.items():
                    # Match similar emotions (e.g., "angry" matches "anger")
                    if emotion_name.lower() in user_emo.lower() or user_emo.lower() in emotion_name.lower():
                        user_intensity = max(user_intensity, details.get("intensity", 0.5))

                # High susceptibility + high user intensity = contagion warning
                if user_intensity > 0.6 and contagion_susceptibility > 0.7:
                    result["warn"] = True
                    result["allow"] = True  # Still allow but with warning
                    result["intensity_modifier"] = 0.3  # Significantly dampened
                    result["modified_attribution"] = "contagion_risk"
                    result["reason"] = (
                        f"HIGH CONTAGION RISK: {emotion_name} is highly contagious "
                        f"(susceptibility={contagion_susceptibility:.2f}) and user shows "
                        f"intensity={user_intensity:.2f}. Dampening and flagging."
                    )
                    return result

            # High susceptibility but no strong user signal: mild warning
            result["allow"] = True
            result["intensity_modifier"] = 0.6
            result["modified_attribution"] = f"resonance_{attribution}"
            result["reason"] = f"High susceptibility but no intense user signal, allowing partial resonance"
            return result

        # Unknown attribution: Be cautious
        result["allow"] = True
        result["warn"] = True
        result["intensity_modifier"] = 0.5
        result["reason"] = f"Unknown attribution '{attribution}', allowing with caution"
        return result

    def filter_emotions_for_oscillator(
        self,
        extracted_emotions: dict,
        user_emotional_state: dict = None,
        protocol_engine=None
    ) -> dict:
        """
        Filter extracted emotions through contagion check before feeding oscillator.

        Takes raw extracted emotions (with attribution tags) and returns a filtered
        dict of emotions that should actually affect the entity's internal state.

        Args:
            extracted_emotions: From emotion_extractor.extract_emotions()
            user_emotional_state: From emotion_extractor.extract_user_emotions()
            protocol_engine: ProtocolEngine for contagion susceptibility lookup

        Returns:
            Dict with:
                - filtered_emotions: Dict of emotions that passed the boundary check
                - warnings: List of contagion warnings to log
                - blocked: List of emotions that were blocked
        """
        result = {
            "filtered_emotions": {},
            "warnings": [],
            "blocked": []
        }

        extracted_states = extracted_emotions.get("extracted_states", {})

        for emotion_name, details in extracted_states.items():
            attribution = details.get("attribution", "self")

            # Get contagion susceptibility from ULTRAMAP (default 0.5)
            susceptibility = 0.5
            if protocol_engine:
                try:
                    profile = protocol_engine.get_emotion_profile(emotion_name)
                    susceptibility = float(profile.get("Contagion Susceptibility", 0.5))
                except (ValueError, TypeError, AttributeError):
                    susceptibility = 0.5

            # Run contagion check
            check = self.check_contagion(
                emotion_name=emotion_name,
                attribution=attribution,
                user_emotional_state=user_emotional_state,
                contagion_susceptibility=susceptibility
            )

            if check["allow"]:
                # Apply intensity modifier and attribution update
                filtered_details = dict(details)
                original_intensity = details.get("intensity", 0.5)
                if isinstance(original_intensity, str):
                    # Convert string intensity to float for modification
                    intensity_map = {"strong": 0.85, "high": 0.7, "moderate": 0.5, "mild": 0.3}
                    original_intensity = intensity_map.get(original_intensity, 0.5)

                filtered_details["intensity"] = original_intensity * check["intensity_modifier"]
                filtered_details["attribution"] = check["modified_attribution"]
                filtered_details["contagion_checked"] = True

                result["filtered_emotions"][emotion_name] = filtered_details

                if check["warn"]:
                    result["warnings"].append(
                        f"[CONTAGION] {emotion_name}: {check['reason']}"
                    )
            else:
                result["blocked"].append({
                    "emotion": emotion_name,
                    "reason": check["reason"],
                    "original_attribution": attribution
                })

        return result

    def _update_felt_state_buffer(self):
        """
        TPN/DMN: Write current spatial/felt-state to the shared buffer.
        Called every scan cycle (~4s) to keep the TPN's fast-path data fresh.

        The TPN reads this during voice-mode responses instead of calling
        peripheral models, giving it instant access to interoceptive state.
        """
        if not self.felt_state_buffer:
            return

        try:
            # Build room state description
            room_state = "relaxed awareness"
            if self._last_tension > 0.5:
                room_state = "restless"
            elif self._last_tension > 0.3:
                room_state = "something underneath"
            elif self._last_coherence > 0.6:
                room_state = "focused presence"

            # Get nearest object name
            nearest = ""
            if self._last_near_object:
                nearest = self._last_near_object

            # Update the buffer
            self.felt_state_buffer.update_spatial(
                felt_sense=self._felt_state,
                tension=self._last_tension,
                nearest_object=nearest,
                room_state=room_state
            )

            # Also update oscillator state in buffer (redundant with ResonantIntegration
            # but ensures freshness even if turns are infrequent)
            self.felt_state_buffer.update_oscillator(
                dominant_band=self._last_dominant,
                coherence=self._last_coherence,
                band_weights=dict(self._combined_bands)
            )
        except Exception as e:
            # Non-fatal — buffer updates shouldn't break the heartbeat
            if self._scan_count % 30 == 0:
                print(f"{self._tag('INTEROCEPTION')} Buffer update error: {e}")
