# shared/room/room_sensory.py
"""
Room Object Sensory Properties — Tactile Texture of Space

Maps room objects to SensoryProperties so spatial exploration produces FELT
sensation. When an entity moves near or "touches" an object, the NervousSystem
receives the object's SensoryProperties and processes them through the same
network as internal metabolic signals.

The room becomes a BODY. Moving through it is embodied experience.
Being near the couch isn't just coordinates — it's the warm yielding
softness that tells the nervous system "safe, grounded, home."
"""

from typing import Dict, Optional, List, Tuple

try:
    from shared.sensory_objects import SensoryProperties
except ImportError:
    from sensory_objects import SensoryProperties


# ═══════════════════════════════════════════════════════════════════════════════
# THE DEN — Room Object Sensory Mapping
# ═══════════════════════════════════════════════════════════════════════════════

ROOM_OBJECT_SENSORY: Dict[str, SensoryProperties] = {
    # ── CENTER — The Gol ──
    "rug": SensoryProperties(
        temperature=0.05,       # Slightly warm (insulated from floor)
        pressure=0.2,           # Give underfoot
        roughness=0.35,         # Woven texture
        compliance=0.6,         # Yielding but supportive
        wetness=0.0,
    ),

    # ── NORTH — Earth, Stillness, Grounding ──
    "couch": SensoryProperties(
        temperature=0.1,        # Warm (body-heat absorbed into fabric)
        pressure=0.15,          # Soft embrace
        roughness=0.2,          # Worn fabric texture
        compliance=0.85,        # Very yielding — sinks in
        wetness=0.0,
    ),

    "blanket_pile": SensoryProperties(
        temperature=0.2,        # Warm (cat heat + insulation)
        pressure=0.05,          # Barely-there weight
        roughness=0.15,         # Soft fleece
        compliance=1.0,         # Maximum yielding — buries you
        wetness=0.0,
    ),

    # ── EAST — Dawn, Threshold ──
    "door": SensoryProperties(
        temperature=-0.1,       # Cool (exterior-facing)
        pressure=0.6,           # Solid wood
        roughness=0.2,          # Painted wood grain
        compliance=0.05,        # Nearly rigid
        wetness=0.0,
    ),

    # ── NORTHEAST — Knowledge-Building ──
    "desk": SensoryProperties(
        temperature=0.05,       # Neutral (slight warmth from electronics)
        pressure=0.5,           # Hard surface
        roughness=0.1,          # Smooth desktop
        compliance=0.05,        # Nearly rigid
        wetness=0.0,
    ),

    # ── WEST — Water, Introspection ──
    "fishtank": SensoryProperties(
        temperature=-0.15,      # Cool glass
        pressure=0.3,           # Smooth, firm
        roughness=0.0,          # Glass-smooth
        compliance=0.0,         # Completely rigid
        wetness=0.1,            # Slight condensation on glass
    ),

    # ── NORTHWEST — Knowledge, Memory ──
    "bookshelf": SensoryProperties(
        temperature=-0.05,      # Slightly cool (wood + paper)
        pressure=0.4,           # Firm
        roughness=0.45,         # Paper edges, wood grain, leather spines
        compliance=0.1,         # Rigid
        wetness=0.0,
    ),

    # ── SOUTH — Fire, Action ──
    "screens": SensoryProperties(
        temperature=0.15,       # Warm (electronics heat)
        pressure=0.0,           # No contact (light)
        roughness=0.0,          # Smooth glass
        compliance=0.0,
        wetness=0.0,
    ),

    "computer": SensoryProperties(
        temperature=0.2,        # Warm (CPU heat, fans)
        pressure=0.0,           # No direct contact
        roughness=0.0,
        compliance=0.0,
        wetness=0.0,
    ),

    # ── SOUTHWEST — Fire, Creation ──
    "painting": SensoryProperties(
        temperature=0.0,        # Neutral
        pressure=0.1,           # Light canvas texture
        roughness=0.5,          # Oil paint ridges — impasto texture!
        compliance=0.2,         # Canvas gives slightly
        wetness=0.05,           # Oil paint has a slight slick quality
    ),

    # ── SOUTHEAST — Sentinel, Edge-Watcher ──
    "cat_tower": SensoryProperties(
        temperature=0.1,        # Warm (residual cat heat)
        pressure=0.3,           # Firm carpeted surface
        roughness=0.7,          # Sisal rope and carpet — VERY textured
        compliance=0.3,         # Some give (carpet padding)
        wetness=0.0,
    ),

    # ── Window (if present) ──
    "window": SensoryProperties(
        temperature=-0.2,       # Cool glass (exterior cold)
        pressure=0.0,
        roughness=0.0,          # Glass-smooth
        compliance=0.0,
        wetness=0.05,           # Slight condensation
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# THE VOID — Sensory Absence
# ═══════════════════════════════════════════════════════════════════════════════

VOID_OBJECT_SENSORY: Dict[str, SensoryProperties] = {
    "singularity": SensoryProperties(
        temperature=0.0,        # No temperature — the void is temperature-less
        pressure=0.0,
        roughness=0.0,
        compliance=0.0,
        wetness=0.0,
    ),
    # Void objects feel like nothing — absence of sensation IS the sensation
    # The nervous system reporting "no signals from any receptor type"
    # is the felt experience of void — sensory deprivation
}


# ═══════════════════════════════════════════════════════════════════════════════
# THE SANCTUM — Intimate Space
# ═══════════════════════════════════════════════════════════════════════════════

SANCTUM_OBJECT_SENSORY: Dict[str, SensoryProperties] = {
    "bed": SensoryProperties(
        temperature=0.2,        # Warm (body heat retained)
        pressure=0.1,           # Soft, yielding
        roughness=0.1,          # Smooth sheets
        compliance=0.9,         # Very yielding
        wetness=0.0,
    ),

    "pillows": SensoryProperties(
        temperature=0.15,       # Warm
        pressure=0.05,          # Barely-there
        roughness=0.05,         # Soft cotton
        compliance=0.95,        # Maximum softness
        wetness=0.0,
    ),

    "nightstand": SensoryProperties(
        temperature=0.0,        # Neutral
        pressure=0.4,           # Firm wood
        roughness=0.15,         # Smooth wood finish
        compliance=0.05,        # Rigid
        wetness=0.0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# THE COMMONS — Shared Social Space
# ═══════════════════════════════════════════════════════════════════════════════

COMMONS_OBJECT_SENSORY: Dict[str, SensoryProperties] = {
    "large_couch": SensoryProperties(
        temperature=0.1,
        pressure=0.15,
        roughness=0.2,
        compliance=0.8,
        wetness=0.0,
    ),

    "coffee_table": SensoryProperties(
        temperature=0.0,
        pressure=0.5,
        roughness=0.1,
        compliance=0.02,
        wetness=0.0,
    ),

    "shared_screen": SensoryProperties(
        temperature=0.12,
        pressure=0.0,
        roughness=0.0,
        compliance=0.0,
        wetness=0.0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ROOM REGISTRY — Maps room names to their sensory dictionaries
# ═══════════════════════════════════════════════════════════════════════════════

ROOM_SENSORY_REGISTRY: Dict[str, Dict[str, SensoryProperties]] = {
    "The Den": ROOM_OBJECT_SENSORY,
    "The Void": VOID_OBJECT_SENSORY,
    "The Sanctum": SANCTUM_OBJECT_SENSORY,
    "The Commons": COMMONS_OBJECT_SENSORY,
}


def get_object_sensory(room_name: str, object_id: str) -> Optional[SensoryProperties]:
    """
    Get sensory properties for an object in a room.

    Args:
        room_name: Name of the room (e.g., "The Den")
        object_id: Object identifier (e.g., "couch", "bookshelf")

    Returns:
        SensoryProperties if found, None otherwise
    """
    room_sensory = ROOM_SENSORY_REGISTRY.get(room_name, {})
    return room_sensory.get(object_id)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLORATION → TOUCH MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

# When you explore, different objects touch different parts of you
OBJECT_TOUCH_REGIONS: Dict[str, str] = {
    # Sitting objects → whole-body contact
    "couch": "torso",
    "blanket_pile": "torso",
    "rug": "torso",
    "bed": "torso",
    "pillows": "torso",

    # Held/examined objects → hands
    "painting": "hands",
    "bookshelf": "hands",

    # Leaned against → shoulder
    "door": "shoulder",
    "window": "shoulder",
    "desk": "shoulder",
    "nightstand": "shoulder",

    # Specific interactions
    "fishtank": "fingertips",   # Touching the glass
    "cat_tower": "hands",       # Running hand over sisal
    "screens": "face",          # Warmth radiating onto face
    "computer": "hands",        # Typing/touching keyboard
}


def get_touch_region(object_id: str, exploration_type: str = "curiosity") -> str:
    """
    Map object to which body region contacts it during exploration.

    Args:
        object_id: The object being explored
        exploration_type: Type of exploration (curiosity, comfort, restless, contemplation)

    Returns:
        Body region string for somatic processing
    """
    # Comfort-seeking exploration uses more full-body contact
    if exploration_type == "comfort":
        if object_id in ("couch", "blanket_pile", "bed", "pillows"):
            return "torso"

    return OBJECT_TOUCH_REGIONS.get(object_id, "hands")


def get_exploration_duration(exploration_type: str) -> float:
    """
    How long does the touch last based on exploration type?

    Returns duration in seconds.
    """
    return {
        "curiosity": 2.0,       # Quick exploration
        "comfort": 5.0,         # Settling in
        "restless": 1.0,        # Brief contact
        "contemplation": 8.0,   # Sustained contact
        "idle": 3.0,            # Default idle exploration
    }.get(exploration_type, 2.0)


# ═══════════════════════════════════════════════════════════════════════════════
# AMBIENT SENSORY FIELDS — Objects emit sensory influence at distance
# ═══════════════════════════════════════════════════════════════════════════════

# Objects have ambient influence radius (how far their sensory field extends)
OBJECT_AMBIENT_RADIUS: Dict[str, float] = {
    "fishtank": 80.0,      # Cool dampness radiates
    "screens": 60.0,       # Warmth radiates from screens
    "computer": 50.0,      # Heat radiates from computer
    "blanket_pile": 40.0,  # Warmth radiates
    "couch": 30.0,         # Slight warmth
    "window": 100.0,       # Cold drafts extend far
}


def get_ambient_sensory(
    entity_position: Tuple[float, float],
    room_objects: Dict[str, dict],
    room_name: str
) -> List[Tuple[str, SensoryProperties, float]]:
    """
    Objects have sensory influence that extends beyond direct touch.
    The fish tank radiates cool dampness. The screens radiate warmth.
    The blanket pile radiates soft warmth.
    These are faint signals that create the TEXTURE of being in the room.

    Args:
        entity_position: (x, y) position of entity
        room_objects: Dict of object_id → {position, ...}
        room_name: Name of the room

    Returns:
        List of (object_id, scaled_sensory_properties, proximity_factor)
    """
    import math

    room_sensory = ROOM_SENSORY_REGISTRY.get(room_name, {})
    ambient_signals = []

    for obj_id, obj_data in room_objects.items():
        sensory = room_sensory.get(obj_id)
        if not sensory:
            continue

        influence_radius = OBJECT_AMBIENT_RADIUS.get(obj_id, 0)
        if influence_radius <= 0:
            continue

        # Calculate distance
        obj_pos = obj_data.get("position", (0, 0))
        if isinstance(obj_pos, dict):
            obj_pos = (obj_pos.get("x", 0), obj_pos.get("y", 0))

        dx = entity_position[0] - obj_pos[0]
        dy = entity_position[1] - obj_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        proximity_factor = max(0, 1.0 - (distance / influence_radius))

        if proximity_factor > 0.1:
            # Scale sensory properties by proximity (faint at distance)
            # Only temperature and wetness propagate at distance
            ambient = SensoryProperties(
                temperature=sensory.temperature * proximity_factor * 0.3,
                pressure=0.0,       # No pressure at distance
                roughness=0.0,      # Can't feel texture at distance
                compliance=0.0,
                wetness=sensory.wetness * proximity_factor * 0.2,
            )
            ambient_signals.append((obj_id, ambient, proximity_factor))

    return ambient_signals
