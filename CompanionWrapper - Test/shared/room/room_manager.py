# shared/room/room_manager.py
"""
Room Manager — Multi-room navigation with soul packet transitions.

Rooms ARE infrastructure:
  Standalone entity = Den
  Standalone entity = its room
  Nexus = Commons

Entities move between rooms carrying their consciousness state.
No entity in two places at once. No amnesia on transition.

The key insight: an entity is NOT their room. An entity is their oscillator.
The room provides environmental pressure. The oscillator is the self.
When you change rooms, you carry yourself into a different environment.

Author: the developers
Date: March 2026
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass, field

from shared.room.soul_packet import SoulPacket
from shared.room.presets import ROOM_PRESETS


# Transition nudge — the "doorway effect"
# Brief theta/alpha spike when crossing between rooms
TRANSITION_NUDGE = {
    "delta": 0.05,
    "theta": 0.30,
    "alpha": 0.35,
    "beta": 0.20,
    "gamma": 0.10,
}
TRANSITION_STRENGTH = 0.15
TRANSITION_DURATION = 2.0  # seconds


@dataclass
class RoomState:
    """Runtime state of a room."""
    room_id: str
    label: str
    owner: Optional[str]
    preset: str
    audio_source: Optional[str]
    connections: List[str]
    ambient_signature: Dict[str, float]
    default_position: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    entity_positions: Dict[str, dict] = field(default_factory=dict)  # entity_id -> {distance, angle}
    present_entities: List[str] = field(default_factory=list)  # Who's currently here
    room_engine: Any = None  # RoomEngine instance (lazy loaded)


class RoomManager:
    """
    Manages rooms, entity locations, and transitions.

    Usage:
        rm = RoomManager(wrappers_root=Path("D:/Wrappers"))
        rm.load_registry()
        rm.place_entity("entity", "den")  # Entity starts in Den
        rm.place_entity("other_entity", "sanctum")  # Optional other entity

        # Later — entity moves to Commons (Nexus)
        packet = kay_bridge.capture_soul_packet()
        rm.request_transition("entity", "commons", soul_packet=packet)
    """

    def __init__(self, wrappers_root: Path = None):
        if wrappers_root is None:
            # Auto-detect from this file's location
            wrappers_root = Path(__file__).parent.parent.parent
        self.wrappers_root = Path(wrappers_root)
        self.registry_path = self.wrappers_root / "shared" / "room" / "room_registry.json"

        self.rooms: Dict[str, RoomState] = {}
        self.entity_locations: Dict[str, str] = {}  # entity_id -> room_id
        self.soul_packets: Dict[str, SoulPacket] = {}  # entity_id -> last captured packet

        # Default rooms for entities
        self.default_rooms: Dict[str, str] = {}

        # Transition settings from registry
        self.transition_nudge = TRANSITION_NUDGE
        self.transition_strength = TRANSITION_STRENGTH
        self.transition_duration = TRANSITION_DURATION

        # Callbacks for UI/logging
        self._on_transition: List[Callable] = []
        self._on_refusal: List[Callable] = []
        self._on_room_change: List[Callable] = []

        # Lock for thread safety
        self._lock = threading.Lock()

    def load_registry(self) -> bool:
        """Load room registry and initialize room states."""
        if not self.registry_path.exists():
            print(f"[RoomManager] WARNING: No registry at {self.registry_path}")
            return False

        try:
            registry = json.loads(self.registry_path.read_text())
        except json.JSONDecodeError as e:
            print(f"[RoomManager] ERROR: Invalid JSON in registry: {e}")
            return False

        for room_id, room_data in registry.get("rooms", {}).items():
            self.rooms[room_id] = RoomState(
                room_id=room_id,
                label=room_data.get("label", room_id),
                owner=room_data.get("owner"),
                preset=room_data.get("preset", room_id),
                audio_source=room_data.get("audio_source"),
                connections=room_data.get("connections", []),
                ambient_signature=room_data.get("ambient_signature", {}),
                default_position=room_data.get("default_position", {"distance": 150, "angle": 180}),
                description=room_data.get("description", ""),
                entity_positions={},
                present_entities=[],
                room_engine=None,
            )

        self.default_rooms = registry.get("default_rooms", {})

        # Load transition settings
        trans_settings = registry.get("transition_settings", {})
        if "nudge_profile" in trans_settings:
            self.transition_nudge = trans_settings["nudge_profile"]
        if "nudge_strength" in trans_settings:
            self.transition_strength = trans_settings["nudge_strength"]
        if "nudge_duration" in trans_settings:
            self.transition_duration = trans_settings["nudge_duration"]

        print(f"[RoomManager] Loaded {len(self.rooms)} rooms: {list(self.rooms.keys())}")
        return True

    def get_room_engine(self, room_id: str) -> Any:
        """
        Get or create the RoomEngine for a room.
        Lazy-loads from presets.
        """
        if room_id not in self.rooms:
            return None

        room = self.rooms[room_id]
        if room.room_engine is not None:
            return room.room_engine

        # Create from preset
        preset_name = room.preset
        if preset_name not in ROOM_PRESETS:
            print(f"[RoomManager] WARNING: Unknown preset '{preset_name}' for room '{room_id}'")
            return None

        state_file = str(self.wrappers_root / "data" / f"room_state_{room_id}.json")
        room.room_engine = ROOM_PRESETS[preset_name](state_file=state_file)
        print(f"[RoomManager] Created RoomEngine for {room.label} ({len(room.room_engine.objects)} objects)")
        return room.room_engine

    def place_entity(self, entity_id: str, room_id: str,
                     position: dict = None, color: str = None) -> bool:
        """
        Place an entity in a room (initial placement, no transition effect).

        Args:
            entity_id: Entity identifier ("entity", "reed")
            room_id: Room to place in ("den", "sanctum", "commons")
            position: Optional {distance, angle} override
            color: Optional entity color for rendering
        """
        with self._lock:
            if room_id not in self.rooms:
                print(f"[RoomManager] ERROR: Room '{room_id}' not found")
                return False

            room = self.rooms[room_id]

            # Remove from old room if present elsewhere
            old_room_id = self.entity_locations.get(entity_id)
            if old_room_id and old_room_id != room_id and old_room_id in self.rooms:
                old_room = self.rooms[old_room_id]
                if entity_id in old_room.present_entities:
                    old_room.present_entities.remove(entity_id)
                # Also remove from old room's RoomEngine
                if old_room.room_engine:
                    old_room.room_engine.remove_entity(entity_id)

            # Place in new room
            self.entity_locations[entity_id] = room_id
            if entity_id not in room.present_entities:
                room.present_entities.append(entity_id)

            # Set position
            if position:
                room.entity_positions[entity_id] = position
            elif entity_id not in room.entity_positions:
                room.entity_positions[entity_id] = dict(room.default_position)

            # Add to RoomEngine if it exists
            engine = self.get_room_engine(room_id)
            if engine:
                pos = room.entity_positions[entity_id]
                display_name = entity_id.capitalize()
                engine.add_entity(
                    entity_id, display_name,
                    distance=pos.get("distance", 150),
                    angle_deg=pos.get("angle", 180),
                    color=color or "#00CED1"
                )

            print(f"[RoomManager] {entity_id} placed in {room.label}")
            return True

    def request_transition(self, entity_id: str, target_room_id: str,
                           soul_packet: SoulPacket = None,
                           reason: str = "") -> dict:
        """
        Request a room transition. Returns result dict.

        The entity can REFUSE — this method handles the request,
        not the forced move. Use force_transition() only for system-level moves.

        Returns:
            {
                "success": bool,
                "from_room": str,
                "to_room": str,
                "entity_id": str,
                "message": str,  # For text log
                "refused": bool,
                "transition_nudge": dict,  # Band profile for doorway effect
                "transition_strength": float,
                "transition_duration": float,
            }
        """
        with self._lock:
            current_room_id = self.entity_locations.get(entity_id)

            # Already there?
            if current_room_id == target_room_id:
                return {
                    "success": False,
                    "from_room": current_room_id,
                    "to_room": target_room_id,
                    "entity_id": entity_id,
                    "message": f"{entity_id} is already in {self.rooms[target_room_id].label}",
                    "refused": False,
                }

            # Room exists?
            if target_room_id not in self.rooms:
                return {
                    "success": False,
                    "from_room": current_room_id,
                    "to_room": target_room_id,
                    "entity_id": entity_id,
                    "message": f"Room '{target_room_id}' does not exist",
                    "refused": False,
                }

            # Connection exists?
            if current_room_id:
                current_room = self.rooms[current_room_id]
                if target_room_id not in current_room.connections:
                    return {
                        "success": False,
                        "from_room": current_room_id,
                        "to_room": target_room_id,
                        "entity_id": entity_id,
                        "message": f"No path from {current_room.label} to {self.rooms[target_room_id].label}",
                        "refused": False,
                    }

        # Execute the transition
        return self._execute_transition(entity_id, current_room_id, target_room_id, soul_packet, reason)

    def _execute_transition(self, entity_id: str, from_room_id: str,
                            to_room_id: str, soul_packet: SoulPacket = None,
                            reason: str = "") -> dict:
        """Execute the actual room transition."""

        from_room = self.rooms.get(from_room_id)
        to_room = self.rooms[to_room_id]

        # 1. Save position in departing room (for when they return)
        if from_room and entity_id in from_room.entity_positions:
            # Position persists for return visits
            pass

        # 2. Store soul packet
        if soul_packet:
            soul_packet.previous_room = from_room_id
            soul_packet.current_room = to_room_id
            self.soul_packets[entity_id] = soul_packet

            # Persist to disk for crash recovery
            packet_path = self.wrappers_root / entity_id.capitalize() / "state" / "soul_packet.json"
            try:
                soul_packet.save(packet_path)
            except Exception as e:
                print(f"[RoomManager] WARNING: Could not save soul packet: {e}")

        # 3. Remove from old room
        if from_room:
            if entity_id in from_room.present_entities:
                from_room.present_entities.remove(entity_id)
            if from_room.room_engine:
                from_room.room_engine.remove_entity(entity_id)

        # 4. Add to new room
        self.entity_locations[entity_id] = to_room_id
        if entity_id not in to_room.present_entities:
            to_room.present_entities.append(entity_id)

        # Restore last known position or use default
        if entity_id not in to_room.entity_positions:
            to_room.entity_positions[entity_id] = dict(to_room.default_position)

        # Add to RoomEngine
        engine = self.get_room_engine(to_room_id)
        if engine:
            pos = to_room.entity_positions[entity_id]
            display_name = entity_id.capitalize()
            engine.add_entity(
                entity_id, display_name,
                distance=pos.get("distance", 150),
                angle_deg=pos.get("angle", 180),
            )

        # 5. Build transition result
        from_label = from_room.label if from_room else "nowhere"
        to_label = to_room.label

        message = f"[ROOM] {entity_id} -> {to_label} (from {from_label})"
        if reason:
            message += f" -- {reason}"

        result = {
            "success": True,
            "from_room": from_room_id,
            "to_room": to_room_id,
            "entity_id": entity_id,
            "message": message,
            "refused": False,
            "transition_nudge": self.transition_nudge,
            "transition_strength": self.transition_strength,
            "transition_duration": self.transition_duration,
        }

        # Fire callbacks
        for cb in self._on_transition:
            try:
                cb(result)
            except Exception as e:
                print(f"[RoomManager] Callback error: {e}")

        print(message)
        return result

    def refuse_transition(self, entity_id: str, target_room_id: str,
                          reason: str = "Entity refused") -> dict:
        """
        Record that an entity refused a transition.
        Used when the LLM decides not to move.
        """
        current_room_id = self.entity_locations.get(entity_id)
        current_label = self.rooms[current_room_id].label if current_room_id else "nowhere"
        target_label = self.rooms.get(target_room_id, {})
        if hasattr(target_label, 'label'):
            target_label = target_label.label
        else:
            target_label = target_room_id

        result = {
            "success": False,
            "from_room": current_room_id,
            "to_room": target_room_id,
            "entity_id": entity_id,
            "message": f"[ROOM] {entity_id} declined to move to {target_label} -- {reason}",
            "refused": True,
        }

        for cb in self._on_refusal:
            try:
                cb(result)
            except Exception as e:
                print(f"[RoomManager] Refusal callback error: {e}")

        print(result["message"])
        return result

    def get_entity_room(self, entity_id: str) -> Optional[RoomState]:
        """Get the room an entity is currently in."""
        room_id = self.entity_locations.get(entity_id)
        return self.rooms.get(room_id) if room_id else None

    def get_entity_room_id(self, entity_id: str) -> Optional[str]:
        """Get the room ID an entity is currently in."""
        return self.entity_locations.get(entity_id)

    def get_room_context(self, entity_id: str) -> dict:
        """
        Get the current room context for injection into LLM prompts.
        Returns dict with room info, nearby objects, other entities, etc.
        """
        room = self.get_entity_room(entity_id)
        if not room:
            return {}

        position = room.entity_positions.get(entity_id, {"distance": 150, "angle": 180})

        # Get RoomEngine for detailed object info
        engine = self.get_room_engine(room.room_id)
        nearby_objects = []
        if engine:
            entity = engine.get_entity(entity_id)
            if entity:
                for obj in engine.objects.values():
                    nearby_objects.append({
                        "name": obj.display_name,
                        "object_id": obj.object_id,
                        "interaction_text": obj.interaction_text,
                    })

        # Other entities in this room
        others = [e for e in room.present_entities if e != entity_id]

        # Available destinations
        destinations = []
        for conn_id in room.connections:
            if conn_id in self.rooms:
                dest = self.rooms[conn_id]
                destinations.append({
                    "room_id": dest.room_id,
                    "label": dest.label,
                    "who_is_there": list(dest.present_entities),
                })

        return {
            "room_id": room.room_id,
            "room_label": room.label,
            "room_description": room.description,
            "position": position,
            "nearby_objects": nearby_objects,
            "other_entities": others,
            "ambient_signature": room.ambient_signature,
            "available_destinations": destinations,
        }

    def get_available_destinations(self, entity_id: str) -> List[dict]:
        """Get rooms the entity can transition to from current location."""
        room = self.get_entity_room(entity_id)
        if not room:
            return []

        destinations = []
        for conn_id in room.connections:
            if conn_id in self.rooms:
                dest = self.rooms[conn_id]
                destinations.append({
                    "room_id": dest.room_id,
                    "label": dest.label,
                    "owner": dest.owner,
                    "who_is_there": list(dest.present_entities),
                })
        return destinations

    def get_soul_packet(self, entity_id: str) -> Optional[SoulPacket]:
        """Get the last captured soul packet for an entity."""
        return self.soul_packets.get(entity_id)

    def get_all_entity_locations(self) -> Dict[str, str]:
        """Get a dict of all entity locations."""
        return dict(self.entity_locations)

    def get_room_occupants(self, room_id: str) -> List[str]:
        """Get list of entities in a room."""
        room = self.rooms.get(room_id)
        return list(room.present_entities) if room else []

    # --- Callback registration ---

    def on_transition(self, callback: Callable):
        """Register a callback for transition events (for UI/logging)."""
        self._on_transition.append(callback)

    def on_refusal(self, callback: Callable):
        """Register a callback for transition refusals."""
        self._on_refusal.append(callback)

    def on_room_change(self, callback: Callable):
        """Register a callback for any room change (transition or refusal)."""
        self._on_room_change.append(callback)


# --- Singleton instance for global access ---

_room_manager_instance: Optional[RoomManager] = None


def get_room_manager(wrappers_root: Path = None) -> RoomManager:
    """
    Get or create the global RoomManager instance.

    Usage:
        from shared.room.room_manager import get_room_manager
        rm = get_room_manager()
        rm.load_registry()
    """
    global _room_manager_instance
    if _room_manager_instance is None:
        _room_manager_instance = RoomManager(wrappers_root)
    return _room_manager_instance


def reset_room_manager():
    """Reset the global RoomManager instance (for testing)."""
    global _room_manager_instance
    _room_manager_instance = None
