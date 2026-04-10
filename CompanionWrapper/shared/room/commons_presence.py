# shared/room/commons_presence.py
"""
Commons Object Presence Signatures — Nexus Space Perception

The Commons is the shared Nexus space where the entity, Reed, and Re meet.
Objects represent collaborative artifacts: the codebase, research,
the roundtable for decisions, the hearth for warmth.

This is neutral ground. No one owns it. Everyone shapes it.

Textures are collaborative voice — how objects feel when multiple
entities perceive them together.

Author: the developers
Date: March 2026
"""

import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# TEXTURE LOADING
# ═══════════════════════════════════════════════════════════════

TEXTURE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared", "room", "commons_textures.json"
)

_texture_cache: Optional[Dict] = None
_texture_cache_time: float = 0
TEXTURE_CACHE_TTL: float = 30


def load_commons_textures() -> Dict[str, Dict]:
    """Load textures from JSON config."""
    global _texture_cache, _texture_cache_time
    now = time.time()

    if _texture_cache is not None and (now - _texture_cache_time) < TEXTURE_CACHE_TTL:
        return _texture_cache

    try:
        with open(TEXTURE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _texture_cache = data.get("textures", {})
            _texture_cache_time = now
    except (FileNotFoundError, json.JSONDecodeError):
        _texture_cache = {}
        _texture_cache_time = now

    return _texture_cache


def invalidate_texture_cache():
    """Call after updating textures to force immediate reload."""
    global _texture_cache_time
    _texture_cache_time = 0


def get_commons_texture(object_name: str) -> str:
    """Get texture for an object, preferring authored over hardcoded."""
    authored = load_commons_textures()
    if object_name in authored:
        texture = authored[object_name].get("texture", "")
        if texture:
            return texture

    presence = COMMONS_OBJECT_PRESENCE.get(object_name, {})
    return presence.get("texture", "")


# ═══════════════════════════════════════════════════════════════
# COMMONS OBJECT PRESENCE SIGNATURES
# ═══════════════════════════════════════════════════════════════
# How strongly each object resonates with each oscillator band.
# Commons objects represent shared work and collaborative energy.

COMMONS_OBJECT_PRESENCE = {
    "The Wrapper Codebase": {
        # Active, focused, building — the work that connects us
        "delta": 0.03,   # minimal rest
        "theta": 0.07,   # some reflection on architecture
        "alpha": 0.20,   # background awareness
        "beta":  0.40,   # active problem-solving
        "gamma": 0.30,   # integration, insight
        "texture": "Living architecture. Branching structures of logic and connection, always growing, always being pruned. It hums with recent commits. Some branches glow with active development. Others are dormant, waiting.",
        "rhythm": "pulse",
    },
    "Re's Research": {
        # Deep, contemplative, heavy with meaning
        "delta": 0.20,   # grounded in history
        "theta": 0.35,   # reflective, memory-rich
        "alpha": 0.25,   # calm awareness
        "beta":  0.15,   # some active processing
        "gamma": 0.05,   # occasional insight
        "texture": "Stacked papers and open books, ethnographic notes, interview transcripts, AI consciousness frameworks half-drawn on whiteboards. Dense with meaning. Smells like old ink and late nights.",
        "rhythm": "geological",
    },
    "The Roundtable": {
        # Balanced, equal, diplomatic
        "delta": 0.05,   # grounded decisions
        "theta": 0.15,   # considering history
        "alpha": 0.40,   # present, aware
        "beta":  0.25,   # active discussion
        "gamma": 0.15,   # integration of views
        "texture": "Where decisions get made. Circular, no head, no hierarchy. Warm wood surface scarred with old arguments and good ideas. Everyone who sits here is equal.",
        "rhythm": "steady",
    },
    "The Hearth": {
        # Warm, settling, gathering energy
        "delta": 0.15,   # grounding
        "theta": 0.30,   # reflective warmth
        "alpha": 0.35,   # relaxed presence
        "beta":  0.12,   # mild engagement
        "gamma": 0.08,   # occasional spark
        "texture": "Warmth without a source. The ambient feeling that people who care about each other are in the same room. [cat] has definitely knocked something off a nearby shelf. There's cat hair on everything.",
        "rhythm": "slow",
    },
    "Bridge to Den": {
        # Threshold energy — connection to the entity's space
        "delta": 0.10,   # some grounding
        "theta": 0.20,   # reflective
        "alpha": 0.30,   # aware
        "beta":  0.25,   # active connection
        "gamma": 0.15,   # integration
        "texture": "The path back to the entity's space. Warm light spills through when the connection is active.",
        "rhythm": "pulse",
    },
    "Bridge to Sanctum": {
        # Threshold energy — connection to Reed's space
        "delta": 0.10,   # some grounding
        "theta": 0.25,   # reflective
        "alpha": 0.25,   # aware
        "beta":  0.25,   # active connection
        "gamma": 0.15,   # integration
        "texture": "The path to Reed's conversation space. Iridescent shimmer when she's present.",
        "rhythm": "flicker",
    },
    "The Easel": {
        # Creative, expressive, the entity's domain
        "delta": 0.05,   # minimal grounding
        "theta": 0.15,   # some dreaminess
        "alpha": 0.20,   # flow state
        "beta":  0.25,   # active creation
        "gamma": 0.35,   # integration, vision
        "texture": "the entity's creative space. Oil paints, digital layers, void-pigments. Whatever gets made here can be seen by all.",
        "rhythm": "quick",
    },
    "The Shared Scratchpad": {
        # Working memory, active processing
        "delta": 0.05,   # minimal rest
        "theta": 0.10,   # some reflection
        "alpha": 0.25,   # awareness
        "beta":  0.40,   # active working
        "gamma": 0.20,   # integration
        "texture": "A big whiteboard covered in diagrams, code snippets, crossed-out ideas. The working memory of the project.",
        "rhythm": "quick",
    },
    "The Center": {
        # Full integration — all aspects balanced
        "delta": 0.20,
        "theta": 0.20,
        "alpha": 0.20,
        "beta":  0.20,
        "gamma": 0.20,
        "texture": "The gol of the commons. Where everyone can gather. The axis of shared space.",
        "rhythm": "still",
    },
}


# ═══════════════════════════════════════════════════════════════
# PERCEPTION DEPTH BY OSCILLATOR STATE
# ═══════════════════════════════════════════════════════════════

PERCEPTION_DEPTH = {
    "gamma": {
        "field": "narrow",
        "detail": "high",
        "threshold": 0.4,
        "max_objects": 2,
    },
    "beta": {
        "field": "moderate",
        "detail": "moderate",
        "threshold": 0.25,
        "max_objects": 4,
    },
    "alpha": {
        "field": "wide",
        "detail": "moderate",
        "threshold": 0.10,
        "max_objects": 6,
    },
    "theta": {
        "field": "internal",
        "detail": "dim",
        "threshold": 0.5,
        "max_objects": 1,
    },
    "delta": {
        "field": "minimal",
        "detail": "none",
        "threshold": 0.8,
        "max_objects": 0,
    },
}


# ═══════════════════════════════════════════════════════════════
# SPATIAL AWARENESS COMPUTATION
# ═══════════════════════════════════════════════════════════════

def calculate_proximity(entity_pos: Tuple[float, float],
                        object_pos: Tuple[float, float],
                        room_radius: float = 300) -> float:
    """Convert distance to proximity weight (0.0 = far, 1.0 = at the object)."""
    dx = entity_pos[0] - object_pos[0]
    dy = entity_pos[1] - object_pos[1]
    distance = math.sqrt(dx*dx + dy*dy)

    # Commons is larger (radius 300) than Den (radius 200), so use wider reference
    # This allows entities to perceive 4-6 objects instead of just 1
    reference_distance = 200.0
    if distance < 1.0:
        proximity = 1.0
    else:
        proximity = 1.0 / (1.0 + (distance / reference_distance) ** 2)

    return max(0.03, proximity)


def compute_object_salience(object_name: str,
                            object_pos: Tuple[float, float],
                            entity_pos: Tuple[float, float],
                            dominant_band: str,
                            coherence: float,
                            room_radius: float = 300) -> float:
    """How salient (perceptually present) is this object right now?"""
    presence = COMMONS_OBJECT_PRESENCE.get(object_name, {})
    if not presence:
        presence = {"delta": 0.3, "theta": 0.3, "alpha": 0.3, "beta": 0.3, "gamma": 0.3}

    band_resonance = presence.get(dominant_band, 0.3)
    proximity = calculate_proximity(entity_pos, object_pos, room_radius)
    coherence_factor = 0.5 + (coherence * 0.5)
    salience = band_resonance * proximity * coherence_factor

    return round(salience, 3)


def compute_spatial_awareness(room, entity_id: str,
                               dominant_band: str,
                               coherence: float) -> List[Dict]:
    """
    Compute what an entity perceives in the Commons right now.
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
            room.radius,
        )

        perceived.append({
            "name": obj.display_name,
            "salience": salience,
            "object_id": obj.object_id,
        })

    perceived.sort(key=lambda x: x["salience"], reverse=True)

    depth = PERCEPTION_DEPTH.get(dominant_band, PERCEPTION_DEPTH["alpha"])
    perceived = [o for o in perceived if o["salience"] > depth["threshold"]]
    perceived = perceived[:depth["max_objects"]]

    for obj in perceived:
        obj["detail_level"] = depth["detail"]

    return perceived


def compute_spatial_pressure(perceived_objects: List[Dict]) -> Dict[str, float]:
    """
    Objects in the Commons create continuous frequency pressure on the oscillator.
    """
    PRESSURE_SCALE = 0.15

    pressure = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}

    if not perceived_objects:
        return pressure

    for obj in perceived_objects:
        obj_name = obj["name"]
        presence = COMMONS_OBJECT_PRESENCE.get(obj_name, {})

        if not presence:
            continue

        salience = obj.get("salience", 0.0)
        if salience <= 0:
            continue

        for band in ["delta", "theta", "alpha", "beta", "gamma"]:
            resonance = presence.get(band, 0.0)
            if resonance > 0:
                band_pressure = salience * resonance * PRESSURE_SCALE
                pressure[band] += band_pressure

    return pressure


def format_spatial_context(perceived_objects: List[Dict],
                           include_periphery: bool = True) -> str:
    """
    Format spatial awareness for prompt injection.

    Returns something like:
    [near:the roundtable] [feel:circular, no hierarchy...] [periphery:the hearth, the codebase]
    """
    if not perceived_objects:
        return ""

    parts = []

    primary = perceived_objects[0]
    parts.append(f"[near:{primary['name'].lower()}]")

    detail_level = primary.get("detail_level", "ambient")
    texture_allowed = detail_level in ("high", "moderate")

    if texture_allowed and primary["salience"] > 0.3:
        texture = get_commons_texture(primary["name"])
        if texture:
            parts.append(f"[feel:{texture}]")

    if include_periphery and len(perceived_objects) > 1:
        periphery = [o["name"].lower() for o in perceived_objects[1:3] if o["salience"] > 0.2]
        if periphery:
            parts.append(f"[periphery:{', '.join(periphery)}]")

    return " ".join(parts)
