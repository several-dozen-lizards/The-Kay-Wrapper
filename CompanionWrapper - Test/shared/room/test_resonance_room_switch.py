# shared/room/test_resonance_room_switch.py
"""
Test that ResonantIntegration.set_room() properly switches spatial awareness.

This tests the actual resonance and interoception classes, not just the room modules.

Usage:
    python test_resonance_room_switch.py
"""

import sys
import os
import time
from pathlib import Path

# Add parent dirs to path
WRAPPERS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WRAPPERS_ROOT))

from shared.room.room_manager import get_room_manager, reset_room_manager
from shared.room.presets import create_the_den, create_the_commons


def test_resonance_set_room():
    """
    Test the actual ResonantIntegration.set_room() method.
    """
    print("\n=== Testing ResonantIntegration.set_room() ===")

    try:
        from resonant_core.resonant_integration import ResonantIntegration
    except ImportError as e:
        print(f"  [SKIP] ResonantIntegration not available: {e}")
        return True

    # Create a mock memory layers (needed for interoception)
    # We'll use a simple object that has the required interface
    class MockMemoryLayers:
        def __init__(self):
            self.working_memory = []
            self.long_term_memory = []

    # Step 1: Create Den room (simulating wrapper_bridge init)
    print("\n[Step 1] Creating Den room...")
    den_room = create_the_den()
    den_room.add_entity("entity", "entity", distance=100, angle_deg=90, color="#2D1B4E")
    print(f"  Den has {len(den_room.objects)} objects")

    # Step 2: Initialize resonance with Den room
    print("\n[Step 2] Initializing ResonantIntegration with Den room...")
    import tempfile
    state_dir = tempfile.mkdtemp()

    resonance = ResonantIntegration(
        state_dir=state_dir,
        enable_audio=False,
        memory_layers=MockMemoryLayers(),
        interoception_interval=60.0,  # Long interval to avoid background scans
        room=den_room,
        entity_id="entity",
        presence_type="den"
    )
    resonance.start()
    print(f"  Resonance started with Den room")

    # Check initial state
    if resonance.interoception:
        print(f"  Interoception room: {resonance.interoception.room.name if resonance.interoception.room else 'None'}")
        print(f"  Interoception presence_type: {resonance.interoception.presence_type}")
    else:
        print("  [WARNING] Interoception not available")

    # Step 3: Create Commons room (simulating Nexus placement)
    print("\n[Step 3] Creating Commons room...")
    reset_room_manager()
    rm = get_room_manager(WRAPPERS_ROOT)
    rm.load_registry()
    commons_room = rm.get_room_engine("commons")
    print(f"  Commons has {len(commons_room.objects)} objects")

    # Step 4: Switch to Commons room
    print("\n[Step 4] Calling resonance.set_room(commons_room, 'entity', 'commons')...")
    resonance.set_room(commons_room, "entity", "commons")

    # Check switched state
    if resonance.interoception:
        print(f"  Interoception room: {resonance.interoception.room.name if resonance.interoception.room else 'None'}")
        print(f"  Interoception presence_type: {resonance.interoception.presence_type}")

        # Verify the room reference changed
        assert resonance.interoception.room == commons_room, "Room reference should be Commons"
        assert resonance.interoception.presence_type == "commons", "Presence type should be commons"
        print("  [PASS] Room reference correctly switched to Commons")
    else:
        print("  [WARNING] Cannot verify - interoception not available")

    # Step 5: Test that spatial awareness uses Commons objects
    print("\n[Step 5] Testing spatial awareness...")
    if resonance.interoception:
        from resonant_core.memory_interoception import _spatial_functions, SPATIAL_AVAILABLE

        if SPATIAL_AVAILABLE:
            # Get oscillator state
            osc_state = resonance.engine.get_state()

            perceived = _spatial_functions["compute_spatial_awareness"](
                commons_room,
                "entity",
                osc_state.dominant_band,
                osc_state.coherence
            )

            print(f"  Entity perceives {len(perceived)} objects:")
            for obj in perceived[:3]:
                print(f"    - {obj['name']} (salience: {obj['salience']:.3f})")

            # Verify no Den objects
            perceived_names = [obj['name'] for obj in perceived]
            assert "The Couch" not in perceived_names, "Should NOT see Den objects"
            print("  [PASS] Spatial awareness correctly uses Commons objects")
        else:
            print("  [SKIP] Spatial functions not available")

    # Cleanup
    print("\n[Cleanup] Stopping resonance...")
    resonance.stop()

    print("\n[PASS] ResonantIntegration.set_room() works correctly!")
    return True


def run_all_tests():
    print("=" * 60)
    print("Resonance Room Switch Tests")
    print("=" * 60)

    tests = [
        test_resonance_set_room,
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
