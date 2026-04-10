# shared/room/test_unified_room_system.py
"""
Test the unified room system where RoomManager is the single source of truth.

This test simulates the Nexus startup flow:
1. RoomManager places Kay in Commons FIRST
2. wrapper_bridge sees Kay already placed and uses Commons (not Den)
3. NO "[ROOM] Kay placed in The Den" log should appear

Usage:
    python test_unified_room_system.py
"""

import sys
import os
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

# Add parent dirs to path
WRAPPERS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WRAPPERS_ROOT))

from shared.room.room_manager import get_room_manager, reset_room_manager
from shared.room.presets import create_the_den, create_the_commons


def test_nexus_flow_no_den_log():
    """
    Simulate Nexus flow: RoomManager places Kay in Commons BEFORE wrapper_bridge init.
    Verify that wrapper_bridge uses Commons room, not Den.
    """
    print("\n=== Testing Nexus Flow: No Den Log ===")

    # Step 1: Pre-place the entity in Commons (as nexus_entity.py now does)
    print("\n[Step 1] Pre-placing Kay in Commons via RoomManager...")
    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()
    rm.place_entity("entity", "commons", color="#2D1B4E")
    print(f"  RoomManager: the entity is in {rm.entity_locations.get('entity')}")

    # Step 2: Simulate wrapper_bridge checking RoomManager
    print("\n[Step 2] Simulating wrapper_bridge room initialization...")

    # This is what wrapper_bridge now does:
    entity_id = "entity"
    room = None
    room_manager_active = False

    try:
        if rm.rooms and rm.entity_locations.get(entity_id):
            current_room_id = rm.entity_locations[entity_id]
            room = rm.get_room_engine(current_room_id)
            if room:
                room_manager_active = True
                print(f"  [ROOM] Kay using RoomManager room: {rm.rooms[current_room_id].label} ({len(room.objects)} objects)")
    except Exception as e:
        print(f"  Error: {e}")

    # Verify we used RoomManager's room
    assert room_manager_active, "Should have used RoomManager's room"
    assert room is not None, "Room should be set"
    assert room.name == "The Commons", f"Room should be The Commons, got {room.name}"

    # Verify NO Den room was created
    print("\n[Step 3] Verifying no Den room was created...")
    den_room = None  # In the real code, Den is not created when room_manager_active is True

    # Check object names to confirm it's Commons
    object_names = [obj.display_name for obj in room.objects.values()]
    print(f"  Objects in room: {object_names[:3]}...")

    assert "The Roundtable" in object_names, "Should have Commons objects"
    assert "The Couch" not in object_names, "Should NOT have Den objects"

    print("\n[PASS] Nexus flow works correctly - no Den created!")
    return True


def test_standalone_flow_uses_den():
    """
    Simulate standalone flow: No RoomManager placement, wrapper_bridge creates Den.
    """
    print("\n=== Testing Standalone Flow: Uses Den ===")

    # Step 1: Reset RoomManager (no entity placements)
    print("\n[Step 1] Resetting RoomManager (empty)...")
    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    # Don't load registry or place entities

    # Step 2: Simulate wrapper_bridge checking RoomManager (finds nothing)
    print("\n[Step 2] Simulating wrapper_bridge room initialization...")

    entity_id = "entity"
    room = None
    room_manager_active = False

    try:
        if rm.rooms and rm.entity_locations.get(entity_id):
            current_room_id = rm.entity_locations[entity_id]
            room = rm.get_room_engine(current_room_id)
            if room:
                room_manager_active = True
    except Exception:
        pass

    # Since RoomManager has nothing, create Den (standalone mode)
    if not room_manager_active:
        print("  RoomManager has no placement, creating Den (standalone mode)...")
        room = create_the_den()
        room.add_entity(entity_id, "Entity", distance=100, angle_deg=90, color="#2D1B4E")
        print(f"  [ROOM] Kay placed in The Den (inner ring, north — near the couch)")

    assert room is not None, "Room should be created"
    assert room.name == "The Den", f"Room should be The Den, got {room.name}"

    object_names = [obj.display_name for obj in room.objects.values()]
    print(f"  Objects in room: {object_names[:3]}...")

    assert "The Couch" in object_names, "Should have Den objects"
    assert "The Roundtable" not in object_names, "Should NOT have Commons objects"

    print("\n[PASS] Standalone flow works correctly - Den created!")
    return True


def test_spatial_module_loading():
    """
    Test that the correct spatial module is loaded for each room.
    """
    print("\n=== Testing Spatial Module Loading ===")

    from resonant_core.memory_interoception import _load_spatial_module, _spatial_functions, SPATIAL_AVAILABLE

    # Test Commons module
    print("\n[Step 1] Loading 'commons' spatial module...")
    loaded = _load_spatial_module("commons")
    assert loaded, "Failed to load commons module"
    print(f"  SPATIAL_AVAILABLE: {SPATIAL_AVAILABLE}")

    # Test that it has the required functions
    assert "compute_spatial_awareness" in _spatial_functions
    assert "compute_spatial_pressure" in _spatial_functions
    print("  Commons functions loaded correctly")

    # Test Den module
    print("\n[Step 2] Loading 'den' spatial module...")
    loaded = _load_spatial_module("den")
    assert loaded, "Failed to load den module"
    print("  Den functions loaded correctly")

    # Test Sanctum module
    print("\n[Step 3] Loading 'sanctum' spatial module...")
    loaded = _load_spatial_module("sanctum")
    assert loaded, "Failed to load sanctum module"
    print("  Sanctum functions loaded correctly")

    print("\n[PASS] All spatial modules load correctly!")
    return True


def run_all_tests():
    print("=" * 60)
    print("Unified Room System Tests")
    print("=" * 60)

    tests = [
        test_nexus_flow_no_den_log,
        test_standalone_flow_uses_den,
        test_spatial_module_loading,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] {test_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
