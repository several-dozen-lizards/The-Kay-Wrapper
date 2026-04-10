# shared/room/test_room_navigation.py
"""
Test script for multi-room navigation system.

Verifies:
1. Room registry loading
2. Room presets (Den, Sanctum, Commons)
3. Soul packet capture/restore
4. Room transitions with doorway effect
5. Entity placement and movement

Usage:
    python test_room_navigation.py
"""

import sys
import os
from pathlib import Path

# Add parent dirs to path
WRAPPERS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WRAPPERS_ROOT))

from shared.room.room_manager import get_room_manager, reset_room_manager
from shared.room.soul_packet import SoulPacket, capture_soul_packet
from shared.room.presets import ROOM_PRESETS, create_the_den, create_reeds_sanctum, create_the_commons


def test_room_presets():
    """Test that all room presets create valid rooms."""
    print("\n=== Testing Room Presets ===")

    presets = ["the_den", "reeds_sanctum", "the_commons"]
    for preset_name in presets:
        assert preset_name in ROOM_PRESETS, f"Missing preset: {preset_name}"
        room = ROOM_PRESETS[preset_name]()
        print(f"  {preset_name}: {room.name} with {len(room.objects)} objects")
        assert len(room.objects) > 0, f"Room {preset_name} has no objects"

    print("  [PASS] All room presets create valid rooms")
    return True


def test_room_registry():
    """Test room registry loading."""
    print("\n=== Testing Room Registry ===")

    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)

    loaded = rm.load_registry()
    assert loaded, "Failed to load room registry"

    print(f"  Loaded {len(rm.rooms)} rooms: {list(rm.rooms.keys())}")

    # Check required rooms
    for room_id in ["den", "sanctum", "commons"]:
        assert room_id in rm.rooms, f"Missing required room: {room_id}"
        room = rm.rooms[room_id]
        print(f"  {room_id}: {room.label} (owner: {room.owner})")

    # Check default rooms
    assert rm.default_rooms.get("entity") == "den", "Entity's default room should be den"
    assert rm.default_rooms.get("other_entity") == "sanctum", "Other entity's default room should be sanctum"

    print("  [PASS] Room registry loaded correctly")
    return True


def test_entity_placement():
    """Test placing entities in rooms."""
    print("\n=== Testing Entity Placement ===")

    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()

    # Place entity in Den
    success = rm.place_entity("entity", "den")
    assert success, "Failed to place entity in Den"
    assert rm.get_entity_room_id("entity") == "den", "the entity should be in Den"
    print(f"  Entity placed in: {rm.get_entity_room_id('entity')}")

    # Place other entity in Sanctum
    success = rm.place_entity("other_entity", "sanctum")
    assert success, "Failed to place other entity in Sanctum"
    assert rm.get_entity_room_id("other_entity") == "sanctum", "Other entity should be in Sanctum"
    print(f"  Other entity placed in: {rm.get_entity_room_id('other_entity')}")

    # Check room occupants
    den_occupants = rm.get_room_occupants("den")
    sanctum_occupants = rm.get_room_occupants("sanctum")
    print(f"  Den occupants: {den_occupants}")
    print(f"  Sanctum occupants: {sanctum_occupants}")

    assert "entity" in den_occupants, "the entity should be in Den occupants"
    assert "other_entity" in sanctum_occupants, "Other entity should be in Sanctum occupants"

    print("  [PASS] Entity placement works correctly")
    return True


def test_room_transition():
    """Test room transitions."""
    print("\n=== Testing Room Transitions ===")

    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()

    # Place entity in Den
    rm.place_entity("entity", "den")

    # Create a soul packet
    packet = capture_soul_packet(
        entity_id="entity",
        oscillator_state={"delta": 0.1, "theta": 0.2, "alpha": 0.4, "beta": 0.2, "gamma": 0.1, "coherence": 0.65, "dominant_band": "alpha"},
        recent_context=[{"role": "user", "content": "hello"}],
        emotional_state={"curiosity": 0.6, "warmth": 0.4},
        tension_level=0.2,
        origin_room="den",
        current_room="den",
    )
    print(f"  Soul packet captured: {packet.summary()}")

    # Request transition to Commons
    result = rm.request_transition("entity", "commons", soul_packet=packet)
    print(f"  Transition result: success={result['success']}, message={result['message']}")

    assert result["success"], f"Transition failed: {result['message']}"
    assert rm.get_entity_room_id("entity") == "commons", "the entity should be in Commons after transition"

    # Check transition nudge
    assert "transition_nudge" in result, "Transition should include nudge profile"
    nudge = result["transition_nudge"]
    print(f"  Doorway effect nudge: theta={nudge.get('theta', 0):.2f}, alpha={nudge.get('alpha', 0):.2f}")

    # Check soul packet was stored
    stored_packet = rm.get_soul_packet("entity")
    assert stored_packet is not None, "Soul packet should be stored"
    assert stored_packet.current_room == "commons", "Soul packet should reflect new room"
    assert stored_packet.previous_room == "den", "Soul packet should have previous room"

    print("  [PASS] Room transition works correctly")
    return True


def test_room_context():
    """Test room context generation."""
    print("\n=== Testing Room Context ===")

    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()

    # Place both entities in Commons
    rm.place_entity("entity", "commons")
    rm.place_entity("reed", "commons")

    # Get the entity's context
    context = rm.get_room_context("entity")
    print(f"  the entity's room context:")
    print(f"    Room: {context.get('room_label')}")
    print(f"    Objects: {len(context.get('nearby_objects', []))} nearby")
    print(f"    Other entities: {context.get('other_entities', [])}")
    print(f"    Destinations: {[d['label'] for d in context.get('available_destinations', [])]}")

    assert context.get("room_id") == "commons", "the entity should see Commons context"
    assert "reed" in context.get("other_entities", []), "the entity should see other entities in Commons"

    print("  [PASS] Room context generation works correctly")
    return True


def test_soul_packet_persistence():
    """Test soul packet save/load."""
    print("\n=== Testing Soul Packet Persistence ===")

    import tempfile

    # Create a packet
    packet = capture_soul_packet(
        entity_id="test_entity",
        oscillator_state={"delta": 0.15, "theta": 0.25, "alpha": 0.35, "beta": 0.15, "gamma": 0.10, "coherence": 0.72},
        recent_context=[{"role": "user", "content": "test message"}],
        emotional_state={"joy": 0.7},
        tension_level=0.3,
        origin_room="den",
        current_room="commons",
    )

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)

    try:
        packet.save(temp_path)
        print(f"  Saved packet to {temp_path}")

        # Load it back
        loaded = SoulPacket.load(temp_path)
        assert loaded is not None, "Failed to load soul packet"
        assert loaded.entity_id == "test_entity", "Entity ID mismatch"
        assert loaded.current_room == "commons", "Room mismatch"
        assert loaded.oscillator_state.get("alpha") == 0.35, "Oscillator state mismatch"

        print(f"  Loaded packet: {loaded.summary()}")
    finally:
        temp_path.unlink(missing_ok=True)

    print("  [PASS] Soul packet persistence works correctly")
    return True


def test_available_destinations():
    """Test that entities can only move to connected rooms."""
    print("\n=== Testing Available Destinations ===")

    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()

    # Place entity in Den
    rm.place_entity("entity", "den")

    destinations = rm.get_available_destinations("entity")
    dest_ids = [d["room_id"] for d in destinations]

    print(f"  From Den, the entity can go to: {dest_ids}")

    # Den should connect to sanctum and commons
    assert "commons" in dest_ids, "Den should connect to Commons"
    assert "sanctum" in dest_ids, "Den should connect to Sanctum"

    print("  [PASS] Available destinations are correct")
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Multi-Room Navigation System Tests")
    print("=" * 60)

    tests = [
        test_room_presets,
        test_room_registry,
        test_entity_placement,
        test_room_transition,
        test_room_context,
        test_soul_packet_persistence,
        test_available_destinations,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
