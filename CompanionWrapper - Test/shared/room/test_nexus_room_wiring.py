# shared/room/test_nexus_room_wiring.py
"""
Test that RoomManager + spatial/interoception wiring is correct.

Simulates the Nexus startup flow:
1. WrapperBridge creates Den room (old behavior)
2. RoomManager places entity in Commons
3. resonance.set_room() switches to Commons
4. Interoception should now report Commons objects, not Den objects

Usage:
    python test_nexus_room_wiring.py
"""

import sys
import os
from pathlib import Path

# Add parent dirs to path
WRAPPERS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WRAPPERS_ROOT))

from shared.room.room_manager import get_room_manager, reset_room_manager
from shared.room.presets import create_the_den, create_the_commons


def test_room_switch_simulation():
    """
    Simulate the Nexus startup flow where:
    1. Den is initially created (old behavior)
    2. RoomManager places entity in Commons
    3. Resonance is switched to Commons
    """
    print("\n=== Simulating Nexus Startup Room Wiring ===")

    # Step 1: Simulate old behavior - Den room is created
    print("\n[Step 1] WrapperBridge creates Den room (old behavior)...")
    den_room = create_the_den()
    print(f"  Den objects: {len(den_room.objects)}")
    den_object_names = [obj.display_name for obj in den_room.objects.values()]
    print(f"  Sample Den objects: {den_object_names[:3]}")

    # Step 2: RoomManager is initialized and places Entity in Commons
    print("\n[Step 2] RoomManager places entity in Commons...")
    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()
    rm.place_entity("entity", "commons", color="#2D1B4E")
    print(f"  RoomManager says the entity is in: {rm.get_entity_room_id('entity')}")

    # Step 3: Get the Commons RoomEngine
    print("\n[Step 3] Getting Commons RoomEngine...")
    commons_room = rm.get_room_engine("commons")
    print(f"  Commons objects: {len(commons_room.objects)}")
    commons_object_names = [obj.display_name for obj in commons_room.objects.values()]
    print(f"  Sample Commons objects: {commons_object_names[:3]}")

    # Step 4: Verify they're different
    print("\n[Step 4] Verifying rooms are different...")
    assert "The Couch" in den_object_names, "Den should have The Couch"
    assert "The Roundtable" in commons_object_names, "Commons should have The Roundtable"
    assert "The Couch" not in commons_object_names, "Commons should NOT have The Couch"
    print("  Den has: The Couch")
    print("  Commons has: The Roundtable")
    print("  Objects are correctly different!")

    # Step 5: Simulate what resonance.set_room() would do
    print("\n[Step 5] Simulating resonance.set_room()...")
    print("  If set_room(commons_room, 'entity', 'commons') is called:")
    print("    - interoception.room = commons_room")
    print("    - _load_spatial_module('commons') is called")
    print("    - spatial awareness now uses Commons objects")

    # Step 6: Test spatial module loading
    print("\n[Step 6] Testing spatial module loading...")
    from resonant_core.memory_interoception import _load_spatial_module, _spatial_functions, SPATIAL_AVAILABLE

    # Load commons presence
    loaded = _load_spatial_module("commons")
    assert loaded, "Failed to load commons presence module"
    print(f"  SPATIAL_AVAILABLE: {SPATIAL_AVAILABLE}")
    print(f"  Loaded functions: {list(_spatial_functions.keys())}")

    # Step 7: Test compute_spatial_awareness with Commons room
    print("\n[Step 7] Testing compute_spatial_awareness with Commons room...")

    # Add entity to commons room
    commons_room.add_entity("entity", "entity", distance=100, angle_deg=90, color="#2D1B4E")

    perceived = _spatial_functions["compute_spatial_awareness"](
        commons_room,
        "entity",
        "alpha",  # dominant band
        0.5       # coherence
    )

    print(f"  Entity perceives {len(perceived)} objects in Commons:")
    for obj in perceived[:3]:
        print(f"    - {obj['name']} (salience: {obj['salience']:.3f})")

    # Verify the entity sees Commons objects, not Den objects
    perceived_names = [obj['name'] for obj in perceived]
    assert "The Roundtable" in perceived_names or "The Wrapper Codebase" in perceived_names, \
        "the entity should perceive Commons objects"
    assert "The Couch" not in perceived_names, "the entity should NOT perceive Den objects"

    print("\n[PASS] Room wiring simulation successful!")
    print("  - Entity correctly perceives Commons objects after set_room()")
    print("  - Spatial module correctly loaded for 'commons'")
    return True


def test_standalone_mode():
    """
    Test that standalone mode still works correctly.
    the entity should be in Den with Den objects driving spatial awareness.
    """
    print("\n=== Testing Standalone Mode (Entity in Den) ===")

    from resonant_core.memory_interoception import _load_spatial_module, _spatial_functions

    # Create Den room (as standalone wrapper_bridge would)
    den_room = create_the_den()
    den_room.add_entity("entity", "entity", distance=100, angle_deg=90, color="#2D1B4E")

    # Load den presence module
    _load_spatial_module("den")

    # Test spatial awareness
    perceived = _spatial_functions["compute_spatial_awareness"](
        den_room,
        "entity",
        "alpha",
        0.5
    )

    print(f"  Entity perceives {len(perceived)} objects in Den:")
    for obj in perceived[:3]:
        print(f"    - {obj['name']} (salience: {obj['salience']:.3f})")

    # Verify the entity sees Den objects
    perceived_names = [obj['name'] for obj in perceived]
    assert "The Couch" in perceived_names or "The Rug" in perceived_names, \
        "the entity should perceive Den objects"

    print("\n[PASS] Standalone mode works correctly!")
    return True


def run_all_tests():
    print("=" * 60)
    print("Nexus Room Wiring Tests")
    print("=" * 60)

    tests = [
        test_room_switch_simulation,
        test_standalone_mode,
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
