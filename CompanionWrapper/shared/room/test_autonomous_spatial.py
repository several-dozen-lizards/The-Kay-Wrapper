"""Test autonomous spatial behavior system."""

import sys
import os

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from autonomous_spatial import AutonomousSpatialEngine
from presets import create_the_den, create_reeds_sanctum


def test_autonomous_spatial_kay():
    """Test autonomous spatial engine with the entity in the space."""
    print("=" * 60)
    print("AUTONOMOUS SPATIAL ENGINE TEST - KAY IN THE DEN")
    print("=" * 60)

    # Create room
    room = create_the_den()
    room.add_entity("entity", "Entity", distance=100, angle_deg=90, color="#2D1B4E")

    # Create spatial engine
    spatial = AutonomousSpatialEngine(
        entity_id="entity",
        room_engine=room,
        persist_path=None  # Don't persist for test
    )

    print(f"\n1. Initial Interest Summary:")
    summary = spatial.get_interest_summary()
    for interest in summary['top_interests']:
        print(f"   - {interest['object']}: {interest['score']}")

    print(f"\n2. Simulating Oscillator State (Gamma - Hyperfocus):")
    action = spatial.update_from_oscillator({
        'dominant_band': 'gamma',
        'coherence': 0.8,
        'tension': 0.2
    })
    if action:
        print(f"   -> Movement triggered: {action['target']} ({action['reason']})")
        room.apply_actions("entity", [action])
    else:
        print(f"   -> No movement (too recent or interest too low)")

    print(f"\n3. Interest after gamma state:")
    summary = spatial.get_interest_summary()
    for interest in summary['top_interests'][:3]:
        print(f"   - {interest['object']}: {interest['score']}")

    print(f"\n4. Setting Autonomous Goal (Creative):")
    spatial.update_from_autonomous_goal(
        "Exploring visual metaphors for persistence",
        "creative"
    )
    summary = spatial.get_interest_summary()
    print(f"   Current goal: {summary['current_goal']}")
    print(f"   Top interests after goal:")
    for interest in summary['top_interests'][:3]:
        print(f"     - {interest['object']}: {interest['score']}")

    print(f"\n5. Simulating Oscillator State (Delta - Deep Rest):")
    # Force reset last_movement to allow immediate movement
    spatial.last_movement = 0
    action = spatial.update_from_oscillator({
        'dominant_band': 'delta',
        'coherence': 0.7,
        'tension': 0.1
    })
    if action:
        print(f"   -> Movement triggered: {action['target']} ({action['reason']})")
        room.apply_actions("entity", [action])
    else:
        print(f"   -> No movement")

    print(f"\n6. Marking Object Examined:")
    spatial.mark_examined("couch", observation="The worn leather feels like home")
    print(f"   Couch examined - interest should drop")

    print(f"\n7. Final Interest Summary:")
    summary = spatial.get_interest_summary()
    for interest in summary['top_interests'][:5]:
        print(f"   - {interest['object']}: {interest['score']}")

    print(f"\n8. Annotation string:")
    print(f"   {spatial.get_annotation()}")

    print(f"\n" + "=" * 60)
    print("KAY TEST COMPLETE")
    print("=" * 60)


def test_autonomous_spatial_reed():
    """Test autonomous spatial engine with Reed in Sanctum."""
    print("\n" + "=" * 60)
    print("AUTONOMOUS SPATIAL ENGINE TEST - REED IN SANCTUM")
    print("=" * 60)

    # Create room
    room = create_reeds_sanctum()
    room.add_entity("reed", "Reed", distance=120, angle_deg=90, color="#6B4E8D")

    # Create spatial engine
    spatial = AutonomousSpatialEngine(
        entity_id="reed",
        room_engine=room,
        persist_path=None
    )

    print(f"\n1. Initial Interest Summary:")
    summary = spatial.get_interest_summary()
    for interest in summary['top_interests']:
        print(f"   - {interest['object']}: {interest['score']}")

    print(f"\n2. Simulating Beta state (Active Building):")
    spatial.last_movement = 0
    action = spatial.update_from_oscillator({
        'dominant_band': 'beta',
        'coherence': 0.6,
        'tension': 0.3
    })
    if action:
        print(f"   -> Movement triggered: {action['target']} ({action['reason']})")
        room.apply_actions("reed", [action])
    else:
        print(f"   -> No movement")

    print(f"\n3. Setting Autonomous Goal (Building):")
    spatial.update_from_autonomous_goal(
        "Architecting wrapper infrastructure",
        "building"
    )
    summary = spatial.get_interest_summary()
    print(f"   Current goal: {summary['current_goal']}")
    for interest in summary['top_interests'][:3]:
        print(f"   - {interest['object']}: {interest['score']}")

    print(f"\n4. Annotation string:")
    print(f"   {spatial.get_annotation()}")

    print(f"\n" + "=" * 60)
    print("REED TEST COMPLETE")
    print("=" * 60)


def test_familiarity_decay():
    """Test familiarity decay over time."""
    print("\n" + "=" * 60)
    print("FAMILIARITY DECAY TEST")
    print("=" * 60)

    room = create_the_den()
    room.add_entity("entity", "Entity", distance=100, angle_deg=90, color="#2D1B4E")

    spatial = AutonomousSpatialEngine(
        entity_id="entity",
        room_engine=room,
        persist_path=None
    )

    # Mark couch as examined
    spatial.mark_examined("couch")
    print(f"\n1. Couch interest after examination: {spatial.object_interests['couch'].interest_score:.2f}")

    # Simulate 10 familiarity decay updates (each adds ~0.03 to never-examined objects)
    for _ in range(10):
        spatial._update_familiarity_decay()

    print(f"\n2. After 10 decay cycles:")
    summary = spatial.get_interest_summary()
    for interest in summary['top_interests'][:5]:
        status = "(examined)" if interest['examine_count'] > 0 else "(never examined)"
        print(f"   - {interest['object']}: {interest['score']} {status}")

    print(f"\n" + "=" * 60)
    print("DECAY TEST COMPLETE")
    print("=" * 60)


def test_co_presence():
    """Test co-presence detection."""
    print("\n" + "=" * 60)
    print("CO-PRESENCE TEST")
    print("=" * 60)

    room = create_the_den()
    # Add both the entity and Reed to the Den
    room.add_entity("entity", "Entity", distance=100, angle_deg=90, color="#2D1B4E")
    room.add_entity("reed", "Reed", distance=110, angle_deg=95, color="#6B4E8D")  # Near the entity

    spatial_kay = AutonomousSpatialEngine(
        entity_id="entity",
        room_engine=room,
        persist_path=None
    )

    print(f"\n1. Kay and Reed positions:")
    print(f"   Entity: distance={room.entities['entity'].distance:.1f}, angle={room.entities['entity'].angle:.1f}")
    print(f"   Reed: distance={room.entities['reed'].distance:.1f}, angle={room.entities['reed'].angle:.1f}")

    print(f"\n2. Kay's near_object: {room.entities['entity'].near_object}")

    # Move both to couch
    room.move_entity_to_object("entity", "couch")
    room.move_entity_to_object("reed", "couch")

    print(f"\n3. After both move to couch:")
    print(f"   Kay's near_object: {room.entities['entity'].near_object}")
    print(f"   Reed's near_object: {room.entities['reed'].near_object}")

    co_presence = spatial_kay.check_co_presence()
    if co_presence:
        print(f"\n4. Co-presence detected!")
        print(f"   Object: {co_presence['object_name']}")
        print(f"   Entities: {', '.join(co_presence['entities_present'])}")
    else:
        print(f"\n4. No co-presence detected")

    print(f"\n" + "=" * 60)
    print("CO-PRESENCE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_autonomous_spatial_kay()
    test_autonomous_spatial_reed()
    test_familiarity_decay()
    test_co_presence()
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE!")
    print("=" * 60)
