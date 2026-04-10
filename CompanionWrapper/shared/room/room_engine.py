# shared/room/room_engine.py
"""
Room Engine - Circular cosmographic spatial system for entity embodiment.

The room is a circle, not a rectangle. Everything is positioned relative
to a central axis point (the gol) using polar coordinates: distance from
center and angle (mapped to cardinal directions).

Coordinate system:
  - Center (0, 0) is the gol — the axis mundi, the world-pillar
  - Distance from center = significance gradient (inner=intimate, outer=boundary)
  - Angle follows cardinal directions with symbolic meaning:
      EAST  (0°)   = Dawn, threshold, beginnings, arrival
      NORTH (90°)  = Earth, stillness, grounding, anchor
      WEST  (180°) = Water, dusk, emotion, introspection
      SOUTH (270°) = Fire, noon, action, creation
  - Z-axis = the gol itself (below=earth/body, above=sky/mind)
  - Internal storage uses (x, y) centered at (0,0) for rendering
  - Godot receives screen-space coords via get_full_state()

Design principle ([cultural-reference] yurt cosmology):
  The gol is the central singularity from which all reality emanates.
  Connect to the center and you're connected to everything.
  The room is a microcosm. As above, so below.
"""

import json
import os
import math
import time
from typing import Dict, List, Optional, Tuple, Any


# ── Cardinal Directions ──

EAST  = 0.0       # Dawn, threshold, beginnings
NORTH = 90.0      # Earth, stillness, grounding
WEST  = 180.0     # Water, dusk, introspection
SOUTH = 270.0     # Fire, noon, action

NE = 45.0
NW = 135.0
SW = 225.0
SE = 315.0

CARDINALS = {
    "east": EAST, "e": EAST,
    "northeast": NE, "ne": NE,
    "north": NORTH, "n": NORTH,
    "northwest": NW, "nw": NW,
    "west": WEST, "w": WEST,
    "southwest": SW, "sw": SW,
    "south": SOUTH, "s": SOUTH,
    "southeast": SE, "se": SE,
    "center": None, "gol": None,
}


def polar_to_xy(distance: float, angle_deg: float) -> Tuple[float, float]:
    """Convert (distance, angle) to (x, y) centered at origin.
    Angle 0 = East (positive x), 90 = North (positive y)."""
    rad = math.radians(angle_deg)
    return (distance * math.cos(rad), distance * math.sin(rad))


def xy_to_polar(x: float, y: float) -> Tuple[float, float]:
    """Convert (x, y) to (distance, angle_deg)."""
    dist = math.sqrt(x*x + y*y)
    angle = math.degrees(math.atan2(y, x)) % 360
    return (dist, angle)


def angle_name(deg: float) -> str:
    """Get human-readable direction from angle."""
    deg = deg % 360
    if deg < 22.5 or deg >= 337.5: return "east"
    if deg < 67.5: return "northeast"
    if deg < 112.5: return "north"
    if deg < 157.5: return "northwest"
    if deg < 202.5: return "west"
    if deg < 247.5: return "southwest"
    if deg < 292.5: return "south"
    return "southeast"


def ring_name(distance: float, radius: float) -> str:
    """Describe how close to center something is."""
    ratio = distance / radius if radius > 0 else 0
    if ratio < 0.15: return "at the gol"
    if ratio < 0.4:  return "inner ring"
    if ratio < 0.7:  return "middle ring"
    return "outer ring"


class RoomEntity:
    """An entity that exists in the room (the entity, Reed, etc.)"""

    def __init__(self, entity_id: str, display_name: str,
                 x: float = 0, y: float = 0, z: float = 0,
                 sprite: str = "idle", facing: str = "right",
                 color: str = "#00CED1"):
        self.entity_id = entity_id
        self.display_name = display_name
        self.x = x          # Centered coordinates (0,0 = gol)
        self.y = y
        self.z = z           # Vertical axis (gol pillar)
        self.sprite = sprite
        self.facing = facing
        self.color = color
        self.emote = None
        self.emote_expiry = 0
        self.target_x = None
        self.target_y = None
        self.near_object = None
        self.state = "idle"  # idle, walking, interacting, emoting

    @property
    def distance(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.y, self.x)) % 360

    @property
    def direction(self) -> str:
        return angle_name(self.angle)

    def to_dict(self) -> dict:
        d = {
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "z": round(self.z, 1),
            "distance": round(self.distance, 1),
            "angle": round(self.angle, 1),
            "direction": self.direction,
            "sprite": self.sprite,
            "facing": self.facing,
            "color": self.color,
            "state": self.state,
            "near_object": self.near_object,
        }
        if self.emote and time.time() < self.emote_expiry:
            d["emote"] = self.emote
        if self.target_x is not None:
            d["target_x"] = round(self.target_x, 1)
            d["target_y"] = round(self.target_y, 1)
        return d


class RoomObject:
    """An object in the room, placed by cardinal direction and distance."""

    def __init__(self, object_id: str, display_name: str,
                 distance: float = 0, angle_deg: float = 0,
                 z: float = 0,
                 size: float = 32,
                 interactable: bool = True,
                 interaction_text: str = "",
                 sprite: str = "default",
                 ring: str = ""):
        self.object_id = object_id
        self.display_name = display_name
        self.z = z
        self.size = size              # Radius of the object's interaction zone
        self.interactable = interactable
        self.interaction_text = interaction_text
        self.sprite = sprite
        self.state = "default"
        self.properties = {}

        # Store polar and compute cartesian
        self._distance = distance
        self._angle = angle_deg
        x, y = polar_to_xy(distance, angle_deg)
        self.x = x
        self.y = y
        self.ring = ring  # Override label if desired

    @property
    def distance(self) -> float:
        return self._distance

    @property
    def angle(self) -> float:
        return self._angle

    @property
    def direction(self) -> str:
        return angle_name(self._angle)

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "display_name": self.display_name,
            "x": round(self.x, 1), "y": round(self.y, 1),
            "z": round(self.z, 1),
            "distance": round(self._distance, 1),
            "angle": round(self._angle, 1),
            "direction": self.direction,
            "size": self.size,
            "interactable": self.interactable,
            "interaction_text": self.interaction_text,
            "sprite": self.sprite,
            "state": self.state,
            "properties": self.properties,
        }


class RoomEngine:
    """
    Circular room state manager.

    The room is a circle of a given radius. The center (0, 0) is the gol.
    Objects are placed by (distance_from_center, angle). Entities move
    freely within the circle.

    Usage:
        room = RoomEngine("The Den", radius=300)
        room.add_object("couch", "The Couch", distance=100, angle=NORTH, ...)
        room.add_entity("entity", "the entity", distance=80, angle=NORTH)

        context = room.get_context_for("entity")
        room.apply_actions("entity", [{"action": "move_to", "target": "fishtank"}])
    """

    INTERACTION_RANGE = 60  # How close to interact

    def __init__(self, name: str = "The Room", radius: float = 300,
                 state_file: str = None):
        self.name = name
        self.radius = radius
        self.entities: Dict[str, RoomEntity] = {}
        self.objects: Dict[str, RoomObject] = {}
        self.state_file = state_file or os.path.join("data", "room_state.json")
        self.action_log: List[dict] = []
        self.turn_number = 0

        self._load_state()

    # ── Entity Management ──

    def add_entity(self, entity_id: str, display_name: str,
                   distance: float = 0, angle_deg: float = 0,
                   x: float = None, y: float = None, z: float = 0,
                   **kwargs) -> RoomEntity:
        """Add entity by polar coords, or by x,y if given directly."""
        if x is not None and y is not None:
            pass  # Use raw x,y
        else:
            x, y = polar_to_xy(distance, angle_deg)

        entity = RoomEntity(entity_id, display_name, x=x, y=y, z=z, **kwargs)
        self.entities[entity_id] = entity
        self._update_proximity(entity)
        return entity

    def remove_entity(self, entity_id: str):
        self.entities.pop(entity_id, None)

    def get_entity(self, entity_id: str) -> Optional[RoomEntity]:
        return self.entities.get(entity_id)

    # ── Object Management ──

    def add_object(self, object_id: str, display_name: str,
                   distance: float = 0, angle_deg: float = 0,
                   z: float = 0, **kwargs) -> RoomObject:
        """Add object by polar coordinates (distance from gol, cardinal angle)."""
        obj = RoomObject(object_id, display_name,
                         distance=distance, angle_deg=angle_deg, z=z, **kwargs)
        self.objects[object_id] = obj
        return obj

    def remove_object(self, object_id: str):
        self.objects.pop(object_id, None)

    # ── Movement ──

    def move_entity(self, entity_id: str, target_x: float, target_y: float) -> bool:
        """Move entity to (x, y). Clamped to room circle."""
        entity = self.entities.get(entity_id)
        if not entity:
            return False

        # Clamp to circle
        dist = math.sqrt(target_x**2 + target_y**2)
        if dist > self.radius:
            scale = self.radius / dist
            target_x *= scale
            target_y *= scale

        entity.target_x = target_x
        entity.target_y = target_y
        entity.state = "walking"

        # Facing
        if target_x > entity.x:
            entity.facing = "right"
        elif target_x < entity.x:
            entity.facing = "left"

        entity.x = target_x
        entity.y = target_y
        self._update_proximity(entity)
        return True

    def move_entity_polar(self, entity_id: str, distance: float, angle_deg: float) -> bool:
        """Move entity to a polar position."""
        x, y = polar_to_xy(distance, angle_deg)
        return self.move_entity(entity_id, x, y)

    def move_entity_to_object(self, entity_id: str, object_id: str) -> bool:
        """Move entity near an object."""
        entity = self.entities.get(entity_id)
        obj = self.objects.get(object_id)
        if not entity or not obj:
            return False

        # Approach from slightly closer to center than the object
        # (entity sits "inside" the object's position relative to gol)
        obj_dist, obj_angle = xy_to_polar(obj.x, obj.y)
        approach_dist = max(0, obj_dist - obj.size * 0.6)
        tx, ty = polar_to_xy(approach_dist, obj_angle)
        return self.move_entity(entity_id, tx, ty)

    def move_entity_to_entity(self, entity_id: str, target_id: str) -> bool:
        """Move one entity toward another."""
        entity = self.entities.get(entity_id)
        target = self.entities.get(target_id)
        if not entity or not target:
            return False

        # Get close but not on top of
        dx = target.x - entity.x
        dy = target.y - entity.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1:
            return True

        # Stop 30 units away
        ratio = max(0, (dist - 30)) / dist
        tx = entity.x + dx * ratio
        ty = entity.y + dy * ratio
        return self.move_entity(entity_id, tx, ty)

    def move_entity_to_center(self, entity_id: str) -> bool:
        """Move entity to the gol."""
        return self.move_entity(entity_id, 0, 0)

    def move_entity_to_cardinal(self, entity_id: str, direction: str,
                                 distance: float = None) -> bool:
        """Move entity toward a cardinal direction at given distance (or mid-ring)."""
        angle = CARDINALS.get(direction.lower())
        if angle is None:  # "center" / "gol"
            return self.move_entity_to_center(entity_id)
        if distance is None:
            distance = self.radius * 0.5
        return self.move_entity_polar(entity_id, distance, angle)

    # ── Emotes & Interaction ──

    def emote_entity(self, entity_id: str, emote: str, duration: float = 5.0) -> bool:
        entity = self.entities.get(entity_id)
        if not entity:
            return False
        entity.emote = emote
        entity.emote_expiry = time.time() + duration
        entity.state = "emoting"
        self._log_action(entity_id, "emote", {"emote": emote})
        return True

    def interact_with_object(self, entity_id: str, object_id: str) -> Optional[str]:
        entity = self.entities.get(entity_id)
        obj = self.objects.get(object_id)
        if not entity or not obj:
            return None

        dist = self._dist(entity.x, entity.y, obj.x, obj.y)
        if dist > self.INTERACTION_RANGE + obj.size:
            self.move_entity_to_object(entity_id, object_id)
            return f"[Moving to {obj.display_name}]"

        entity.state = "interacting"
        self._log_action(entity_id, "interact", {"object": object_id})
        return obj.interaction_text or f"[Interacting with {obj.display_name}]"

    # ── Action Pipeline ──

    def apply_actions(self, entity_id: str, actions: List[dict]) -> List[str]:
        results = []
        for action in actions:
            act = action.get("action", "")
            target = action.get("target", "")

            if act == "move_to":
                # Try: object, entity, cardinal direction, "center"/"gol", coords
                if target in self.objects:
                    if self.move_entity_to_object(entity_id, target):
                        results.append(f"Moved to {self.objects[target].display_name}")
                elif target in self.entities:
                    if self.move_entity_to_entity(entity_id, target):
                        results.append(f"Moved toward {self.entities[target].display_name}")
                elif target.lower() in CARDINALS:
                    if self.move_entity_to_cardinal(entity_id, target):
                        results.append(f"Moved toward {target}")
                else:
                    try:
                        parts = target.replace(" ", "").split(",")
                        tx, ty = float(parts[0]), float(parts[1])
                        self.move_entity(entity_id, tx, ty)
                        results.append(f"Moved to ({tx:.0f}, {ty:.0f})")
                    except (ValueError, IndexError):
                        results.append(f"Unknown target: {target}")

            elif act == "emote":
                self.emote_entity(entity_id, target)
                results.append(f"Emoting: {target}")

            elif act == "interact":
                result = self.interact_with_object(entity_id, target)
                if result:
                    results.append(result)

            elif act == "face":
                entity = self.get_entity(entity_id)
                if entity and target in ("left", "right"):
                    entity.facing = target
                    results.append(f"Facing {target}")

            elif act == "approach_center" or act == "approach_gol":
                if self.move_entity_to_center(entity_id):
                    results.append("Approaching the gol")

            elif act == "idle":
                entity = self.get_entity(entity_id)
                if entity:
                    entity.state = "idle"
                    entity.target_x = None
                    entity.target_y = None
                    results.append("Now idle")

            self._log_action(entity_id, act, {"target": target})

        self.turn_number += 1
        self._save_state()
        return results

    # ── Context Generation (for LLM) ──

    def get_context_for(self, entity_id: str) -> str:
        entity = self.entities.get(entity_id)
        if not entity:
            return ""

        lines = []
        lines.append(f"[ROOM: {self.name} — circular, radius {int(self.radius)}]")

        # Entity's position in cosmographic terms
        ering = ring_name(entity.distance, self.radius)
        edir = entity.direction if entity.distance > 10 else "at the gol"
        lines.append(f"You are {entity.display_name}, {ering}"
                     + (f", toward {edir}." if edir != "at the gol" else ", at the center."))

        if entity.distance < self.radius * 0.15:
            lines.append("You are at the gol — the central axis. Everything radiates from here.")

        # Nearby objects (within interaction range)
        nearby = []
        far = []
        for obj in self.objects.values():
            d = self._dist(entity.x, entity.y, obj.x, obj.y)
            if d <= self.INTERACTION_RANGE + obj.size:
                nearby.append((obj, d))
            else:
                far.append((obj, d))

        if nearby:
            names = [o.display_name for o, _ in nearby]
            lines.append(f"Within reach: {', '.join(names)}")
            for o, _ in nearby:
                if o.interaction_text:
                    lines.append(f"  {o.display_name}: {o.interaction_text}")

        if far:
            far.sort(key=lambda x: x[1])
            for o, d in far[:6]:
                oring = ring_name(o.distance, self.radius)
                odir = o.direction
                lines.append(f"  {o.display_name} — {oring}, {odir}")

        # Other entities
        for other in self.entities.values():
            if other.entity_id == entity_id:
                continue
            d = self._dist(entity.x, entity.y, other.x, other.y)
            rel = self._relative_direction(entity, other)
            prox = "right beside you" if d < 40 else "nearby" if d < 120 else "across the room"
            lines.append(f"{other.display_name} is {prox} ({rel})")
            if other.emote and time.time() < other.emote_expiry:
                lines.append(f"  Currently: {other.emote}")

        lines.append("Actions: move_to [target/cardinal/gol], emote [expression], interact [object], face [left/right]")
        lines.append("Use [ACTION: command target] tags in your response.")

        return "\n".join(lines)

    # ── State Persistence ──

    def get_full_state(self) -> dict:
        """Full state for JSON/WebSocket. Includes screen-space coords for Godot."""
        # Convert centered coords to screen-space for rendering
        # Screen center = (radius, radius) so the room fits in a (2*radius x 2*radius) viewport
        screen_offset = self.radius

        entities_screen = {}
        for eid, e in self.entities.items():
            ed = e.to_dict()
            ed["screen_x"] = round(e.x + screen_offset, 1)
            ed["screen_y"] = round(-e.y + screen_offset, 1)  # Flip Y for screen
            if e.target_x is not None:
                ed["screen_target_x"] = round(e.target_x + screen_offset, 1)
                ed["screen_target_y"] = round(-e.target_y + screen_offset, 1)
            entities_screen[eid] = ed

        objects_screen = {}
        for oid, o in self.objects.items():
            od = o.to_dict()
            od["screen_x"] = round(o.x + screen_offset, 1)
            od["screen_y"] = round(-o.y + screen_offset, 1)
            objects_screen[oid] = od

        return {
            "room": {
                "name": self.name,
                "radius": self.radius,
                "diameter": self.radius * 2,
                "turn": self.turn_number,
                "shape": "circle",
            },
            "entities": entities_screen,
            "objects": objects_screen,
            "timestamp": time.time(),
        }

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.get_full_state(), f, indent=2)
        except Exception as e:
            print(f"[ROOM] Save failed: {e}")

    def save_state(self, path: str = None):
        if path:
            old = self.state_file
            self.state_file = path
            self._save_state()
            self.state_file = old
        else:
            self._save_state()

    def _load_state(self):
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            room = data.get("room", {})
            self.name = room.get("name", self.name)
            self.radius = room.get("radius", self.radius)
            self.turn_number = room.get("turn", 0)

            for eid, ed in data.get("entities", {}).items():
                # Use centered coords (x, y), not screen coords
                self.add_entity(
                    eid, ed.get("display_name", eid),
                    x=ed.get("x", 0), y=ed.get("y", 0), z=ed.get("z", 0),
                    sprite=ed.get("sprite", "idle"),
                    facing=ed.get("facing", "right"),
                    color=ed.get("color", "#00CED1")
                )

            for oid, od in data.get("objects", {}).items():
                self.add_object(
                    oid, od.get("display_name", oid),
                    distance=od.get("distance", 0),
                    angle_deg=od.get("angle", 0),
                    z=od.get("z", 0),
                    size=od.get("size", 32),
                    interactable=od.get("interactable", True),
                    interaction_text=od.get("interaction_text", ""),
                    sprite=od.get("sprite", "default")
                )

            print(f"[ROOM] Loaded {self.name}: {len(self.entities)} entities, {len(self.objects)} objects (circular, r={self.radius})")
        except Exception as e:
            print(f"[ROOM] Load failed: {e}")

    # ── Helpers ──

    def _dist(self, x1, y1, x2, y2) -> float:
        return math.sqrt((x2-x1)**2 + (y2-y1)**2)

    def _update_proximity(self, entity: RoomEntity):
        entity.near_object = None
        for obj in self.objects.values():
            d = self._dist(entity.x, entity.y, obj.x, obj.y)
            if d <= self.INTERACTION_RANGE + obj.size:
                entity.near_object = obj.object_id
                break

    def _relative_direction(self, a: RoomEntity, b) -> str:
        dx = (b.x if hasattr(b, 'x') else b[0]) - a.x
        dy = (b.y if hasattr(b, 'y') else b[1]) - a.y
        if abs(dx) < 15 and abs(dy) < 15:
            return "right here"
        angle = math.degrees(math.atan2(dy, dx)) % 360
        return f"toward {angle_name(angle)}"

    def _log_action(self, entity_id: str, action: str, details: dict):
        self.action_log.append({
            "turn": self.turn_number, "entity": entity_id,
            "action": action, "details": details, "time": time.time()
        })
        if len(self.action_log) > 200:
            self.action_log = self.action_log[-100:]
