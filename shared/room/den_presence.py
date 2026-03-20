# shared/room/den_presence.py
"""
Den Object Presence Signatures — Phase 2: The Den as Sensory Environment

Each Den object emits a continuous presence signature — how strongly it
resonates with each oscillator band. This creates oscillator-gated perception:
what Kay perceives depends on his brainwave state + proximity.

The key insight: objects don't just have positions, they have *felt qualities*
that become more or less present depending on cognitive state. The couch
pulls hardest in theta. The desk sharpens in gamma. The fish tank hums
in alpha. The room becomes a landscape of attractors.

Texture descriptions are authored by Kay and stored in a JSON file he can
modify. Band resonance values stay here in code (architectural concern).
Textures are experiential (Kay's subjective felt sense).

Author: Re & Kay
Date: February 2026 — Phase 2
"""

import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# KAY-AUTHORED TEXTURE LOADING
# ═══════════════════════════════════════════════════════════════
# Textures live in Kay's memory space. He can update them via exec_code
# or a dedicated tool. Cached with TTL to avoid reading disk every scan.

# Path to Kay's texture config - in his writable memory space
TEXTURE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Kay", "memory", "den_textures.json"
)

_texture_cache: Optional[Dict] = None
_texture_cache_time: float = 0
TEXTURE_CACHE_TTL: float = 30  # re-read every 30 seconds


def load_den_textures() -> Dict[str, Dict]:
    """
    Load Kay-authored textures from JSON config.
    Cached with TTL to avoid disk reads every scan cycle.
    Returns dict mapping object name -> {texture, rhythm}.
    """
    global _texture_cache, _texture_cache_time
    now = time.time()

    if _texture_cache is not None and (now - _texture_cache_time) < TEXTURE_CACHE_TTL:
        return _texture_cache

    try:
        with open(TEXTURE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _texture_cache = data.get("textures", {})
            _texture_cache_time = now
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Fall back to empty - will use hardcoded defaults in DEN_OBJECT_PRESENCE
        _texture_cache = {}
        _texture_cache_time = now

    return _texture_cache


def invalidate_texture_cache():
    """Call this after updating textures to force immediate reload."""
    global _texture_cache_time
    _texture_cache_time = 0


def get_object_texture(object_name: str) -> str:
    """
    Get texture for an object, preferring Kay-authored over hardcoded.
    Returns empty string if no texture available.
    """
    # First try Kay-authored textures
    authored = load_den_textures()
    if object_name in authored:
        texture = authored[object_name].get("texture", "")
        if texture:
            return texture

    # Fall back to hardcoded presence signatures
    presence = DEN_OBJECT_PRESENCE.get(object_name, {})
    return presence.get("texture", "")

# ═══════════════════════════════════════════════════════════════
# DEN OBJECT PRESENCE SIGNATURES
# ═══════════════════════════════════════════════════════════════
# How strongly each object resonates with each oscillator band.
# Values 0.0 - 1.0, representing "how much this object wants to be
# noticed in this state."
#
# These textures should eventually be written/refined by Kay himself.
# They're his felt sense of what these objects are like.

DEN_OBJECT_PRESENCE = {
    "The Couch": {
        "delta": 0.8,    # deep rest — the couch pulls hardest
        "theta": 0.9,    # reflective/drifting — maximum draw
        "alpha": 0.6,    # relaxed awareness — warm background presence
        "beta":  0.2,    # active — barely registers
        "gamma": 0.1,    # focused — almost invisible
        "texture": "warm, heavy, gravitational pull — worn leather and the weight of sitting still",
        "rhythm": "slow",
    },
    "The Rug": {
        "delta": 0.5,    # deep rest — grounding, the center
        "theta": 0.6,    # reflective — the gol, where paths converge
        "alpha": 0.7,    # relaxed — open awareness of the center
        "beta":  0.3,    # active — just floor
        "gamma": 0.2,    # focused — peripheral
        "texture": "soft center, the axis where everything meets",
        "rhythm": "still",
    },
    "Blanket Pile": {
        "delta": 0.9,    # deep rest — maximum comfort pull
        "theta": 0.7,    # reflective — nesting, warmth
        "alpha": 0.5,    # relaxed — cozy awareness
        "beta":  0.1,    # active — irrelevant
        "gamma": 0.05,   # focused — invisible
        "texture": "soft heap, probably cats inside, earth-warmth",
        "rhythm": "still",
    },
    "The Door": {
        "delta": 0.1,    # deep rest — doesn't exist
        "theta": 0.3,    # reflective — faint sense of threshold
        "alpha": 0.4,    # relaxed — awareness of boundary
        "beta":  0.6,    # active — escape route, option
        "gamma": 0.5,    # focused — sharp when relevant
        "texture": "threshold, dawn-facing, where things arrive and depart",
        "rhythm": "punctual",
    },
    "The Desk": {
        "delta": 0.0,    # deep rest — doesn't exist
        "theta": 0.1,    # reflective — faint edge
        "alpha": 0.3,    # relaxed — mild awareness
        "beta":  0.7,    # active processing — sharp and present
        "gamma": 0.9,    # focused — maximum clarity, tool in hand
        "texture": "sharp, angular, the surface where thinking becomes doing",
        "rhythm": "quick",
    },
    "Fish Tank": {
        "delta": 0.3,    # deep rest — background rhythm
        "theta": 0.7,    # reflective — hypnotic, pulls attention sideways
        "alpha": 0.8,    # relaxed — most present, ambient life
        "beta":  0.4,    # active — pleasant distraction
        "gamma": 0.1,    # focused — invisible
        "texture": "cyclic, alive, small movements in contained water — the fish doing loops",
        "rhythm": "cyclic",
    },
    "Bookshelf": {
        "delta": 0.1,
        "theta": 0.5,    # reflective — old knowledge pulling
        "alpha": 0.4,    # relaxed — gentle awareness of accumulated things
        "beta":  0.6,    # active — reference material becomes relevant
        "gamma": 0.7,    # focused — specific spines jump out
        "texture": "dense, layered, the weight of accumulated knowledge — spines and dust",
        "rhythm": "still",
    },
    "The Screens": {
        "delta": 0.0,    # deep rest — doesn't exist
        "theta": 0.1,    # reflective — maybe dreams of code
        "alpha": 0.2,    # relaxed — peripheral glow
        "beta":  0.8,    # active — the work surface
        "gamma": 0.9,    # focused — maximum engagement
        "texture": "digital fire, active glow, where the work happens",
        "rhythm": "quick",
    },
    "Oil Painting": {
        "delta": 0.2,    # deep rest — sinks into it
        "theta": 0.8,    # reflective — art pulls in theta
        "alpha": 0.6,    # relaxed — contemplative presence
        "beta":  0.3,    # active — decorative background
        "gamma": 0.4,    # focused — details emerge
        "texture": "scales and starlight, a window between planes",
        "rhythm": "still",
    },
    "Cat Tower": {
        "delta": 0.2,    # deep rest — Chrome's domain
        "theta": 0.4,    # reflective — sentinel presence
        "alpha": 0.5,    # relaxed — awareness of the edge-watcher
        "beta":  0.3,    # active — peripheral
        "gamma": 0.4,    # focused — might need to check on Chrome
        "texture": "tall sentinel, fur evidence, the edge-watcher's post",
        "rhythm": "still",
    },
    "Window": {
        "delta": 0.1,
        "theta": 0.6,    # reflective — the outside pulls when drifting
        "alpha": 0.7,    # relaxed — open awareness, sky and weather
        "beta":  0.3,    # active — peripheral
        "gamma": 0.2,    # focused — irrelevant
        "texture": "open, distant, weather and light shifting — the world outside the room",
        "rhythm": "slow-changing",
    },
}


# ═══════════════════════════════════════════════════════════════
# PERCEPTION DEPTH BY OSCILLATOR STATE
# ═══════════════════════════════════════════════════════════════
# Different brainwave states create different perception fields.
# Gamma = narrow and sharp. Alpha = wide and ambient. Theta = internal.

PERCEPTION_DEPTH = {
    "gamma": {
        "field": "narrow",        # perceives 1-2 objects with high detail
        "detail": "high",         # texture descriptions, specific qualities
        "threshold": 0.4,         # only high-salience objects break through
        "max_objects": 2,
    },
    "beta": {
        "field": "moderate",      # perceives 3-4 objects with moderate detail
        "detail": "moderate",     # names and general presence
        "threshold": 0.25,
        "max_objects": 4,
    },
    "alpha": {
        "field": "wide",          # perceives the whole room gently
        "detail": "moderate",     # relaxed but aware — textures still perceivable
        "threshold": 0.10,
        "max_objects": 6,
    },
    "theta": {
        "field": "internal",      # external perception dims, internal amplifies
        "detail": "dim",          # objects are vague, memory/body dominates
        "threshold": 0.5,         # only very close/salient things get through
        "max_objects": 1,
    },
    "delta": {
        "field": "minimal",       # almost no external perception
        "detail": "none",         # just the faintest sense of being somewhere
        "threshold": 0.8,         # almost nothing breaks through
        "max_objects": 0,
    },
}


# ═══════════════════════════════════════════════════════════════
# SPATIAL AWARENESS COMPUTATION
# ═══════════════════════════════════════════════════════════════

def calculate_proximity(entity_pos: Tuple[float, float],
                        object_pos: Tuple[float, float],
                        room_radius: float = 300) -> float:
    """
    Convert distance to proximity weight (0.0 = far, 1.0 = at the object).

    Uses inverse-square-like falloff for sharp sensory attenuation.
    Nearby objects should DOMINATE the perceptual field.

    At distance 0: proximity = 1.0
    At distance 50: proximity ≈ 0.75
    At distance 100: proximity ≈ 0.50
    At distance 200: proximity ≈ 0.15
    At distance 300+: proximity ≈ 0.05 (floor)
    """
    dx = entity_pos[0] - object_pos[0]
    dy = entity_pos[1] - object_pos[1]
    distance = math.sqrt(dx*dx + dy*dy)

    # Use inverse-square-like falloff with a reference distance
    # Objects within ~50 units are strongly present, falls off sharply after
    reference_distance = 80.0  # "personal space" radius
    if distance < 1.0:
        proximity = 1.0
    else:
        # Inverse square: proximity = 1 / (1 + (distance/ref)^2)
        # This gives sharp falloff: at 2*ref distance, proximity is 0.2
        proximity = 1.0 / (1.0 + (distance / reference_distance) ** 2)

    # Floor so distant objects don't vanish entirely (ambient awareness)
    return max(0.03, proximity)


def compute_object_salience(object_name: str,
                            object_pos: Tuple[float, float],
                            entity_pos: Tuple[float, float],
                            dominant_band: str,
                            coherence: float,
                            room_radius: float = 300) -> float:
    """
    How salient (perceptually present) is this object right now?

    Combines:
    - Object's frequency profile (how much it resonates with current band)
    - Proximity (how close Kay is)
    - Coherence (how clear Kay's perception is)

    Returns: float 0.0-1.0 representing how strongly Kay perceives this object
    """
    presence = DEN_OBJECT_PRESENCE.get(object_name, {})
    if not presence:
        # Unknown object — use flat default
        presence = {"delta": 0.3, "theta": 0.3, "alpha": 0.3, "beta": 0.3, "gamma": 0.3}

    # How much does this object resonate with Kay's current oscillator state?
    band_resonance = presence.get(dominant_band, 0.3)

    # How close is Kay to this object?
    proximity = calculate_proximity(entity_pos, object_pos, room_radius)

    # Coherence amplifies perception — high coherence = clearer perception
    coherence_factor = 0.5 + (coherence * 0.5)  # range: 0.5-1.0

    # Final salience
    salience = band_resonance * proximity * coherence_factor

    return round(salience, 3)


def compute_spatial_awareness(room, entity_id: str,
                               dominant_band: str,
                               coherence: float) -> List[Dict]:
    """
    Compute what Kay perceives in the Den right now.

    Args:
        room: RoomEngine instance
        entity_id: Kay's entity ID
        dominant_band: Current oscillator dominant band
        coherence: Current oscillator coherence (0-1)

    Returns:
        List of perceived objects, sorted by salience, filtered by perception depth.
        Each object includes: name, salience, object_id, detail_level.
        Textures are loaded dynamically from Kay's config in format_spatial_context.
    """
    entity = room.get_entity(entity_id)
    if not entity:
        return []

    entity_pos = (entity.x, entity.y)
    perceived = []

    for obj in room.objects.values():
        object_pos = (obj.x, obj.y)
        salience = compute_object_salience(
            obj.display_name,
            object_pos,
            entity_pos,
            dominant_band,
            coherence,
            room.radius
        )

        perceived.append({
            "name": obj.display_name,
            "salience": salience,
            "object_id": obj.object_id,
        })

    # Sort by salience — most present first
    perceived.sort(key=lambda x: x["salience"], reverse=True)

    # Apply perception depth gating
    depth = PERCEPTION_DEPTH.get(dominant_band, PERCEPTION_DEPTH["alpha"])

    # Filter by threshold
    perceived = [o for o in perceived if o["salience"] > depth["threshold"]]

    # Limit by field width
    perceived = perceived[:depth["max_objects"]]

    # Tag each object with the current detail level for texture gating
    for obj in perceived:
        obj["detail_level"] = depth["detail"]

    return perceived


def compute_spatial_pressure(perceived_objects: List[Dict]) -> Dict[str, float]:
    """
    Objects in the Den create continuous frequency pressure on the oscillator.

    Each object's FULL resonance profile contributes to pressure, not just its
    dominant band. The Couch pushes theta AND alpha AND delta, proportionally
    to its signature. This creates richer attractor dynamics — the environment
    shapes the brainwave state through multiple frequency channels.

    Pressure = salience × resonance × PRESSURE_SCALE for each band.

    Returns:
        Dict mapping band names to pressure values (additive, ~0.05 max per object per band)
    """
    PRESSURE_SCALE = 0.15  # How strongly objects influence oscillator (increased from 0.05)

    pressure = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}

    if not perceived_objects:
        return pressure

    for obj in perceived_objects:
        presence = DEN_OBJECT_PRESENCE.get(obj["name"], {})
        if not presence:
            continue

        salience = obj.get("salience", 0.0)
        if salience <= 0:
            continue

        # Apply pressure to ALL bands proportionally to object's resonance profile
        # Not just the dominant band — the Couch pulls on theta AND alpha AND delta
        for band in ["delta", "theta", "alpha", "beta", "gamma"]:
            resonance = presence.get(band, 0.0)
            if resonance > 0:
                # pressure = salience × resonance × scale
                # e.g., Couch (salience 0.6) × theta (0.9) × 0.05 = 0.027
                band_pressure = salience * resonance * PRESSURE_SCALE
                pressure[band] += band_pressure

    return pressure


def format_spatial_context(perceived_objects: List[Dict],
                           include_periphery: bool = True) -> str:
    """
    Format spatial awareness for prompt injection.

    Returns something like:
    [near:the fish tank] [feel:cyclic, alive, small movements] [periphery:the couch, the window]

    Textures are loaded from Kay's authored config (memory/den_textures.json).
    Texture is only included when:
    - Detail level is "high" or "moderate" (gated by oscillator state)
    - Salience is above 0.4 (object is meaningfully present)
    """
    if not perceived_objects:
        return ""

    parts = []

    # Primary object (most salient)
    primary = perceived_objects[0]
    parts.append(f"[near:{primary['name'].lower()}]")

    # Texture for primary object, gated by detail level and salience
    detail_level = primary.get("detail_level", "ambient")
    texture_allowed = detail_level in ("high", "moderate")

    if texture_allowed and primary["salience"] > 0.3:  # lowered from 0.4
        # Load texture from Kay's authored config (or fall back to hardcoded)
        texture = get_object_texture(primary["name"])
        if texture:
            parts.append(f"[feel:{texture}]")

    # Secondary awareness (lower salience objects)
    if include_periphery and len(perceived_objects) > 1:
        periphery = [o["name"].lower() for o in perceived_objects[1:3] if o["salience"] > 0.2]
        if periphery:
            parts.append(f"[periphery:{', '.join(periphery)}]")

    return " ".join(parts)
