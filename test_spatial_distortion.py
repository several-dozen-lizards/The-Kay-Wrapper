"""
Test suite for SpatialDistortion (perception warping for psychedelic states).

Tests the spatial distortion system that warps how entities perceive their environment.
"""

from shared.room.spatial_distortion import SpatialDistortion


def test_default_state():
    """Default state should have no distortion."""
    d = SpatialDistortion()
    assert d.distance_warp == 0.0
    assert d.boundary_blur == 0.0
    assert d.presence_amplify == 0.0
    assert d.distortion_noise == 0.0
    assert not d.is_active()
    print("Test 1: Default state OK")


def test_distance_warp_closer():
    """Negative distance_warp should make things feel closer (boost salience)."""
    d = SpatialDistortion()
    d.distance_warp = -0.5  # Things feel closer

    awareness = [
        {"name": "bookshelf", "salience": 0.6, "object_id": "obj1", "detail_level": "high"},
        {"name": "lamp", "salience": 0.4, "object_id": "obj2", "detail_level": "moderate"},
    ]

    warped = d.warp_awareness(awareness)

    # Closer = higher salience (negative warp boosts)
    # factor = 1.0 - (-0.5 * 0.5) = 1.25
    assert warped[0]["salience"] > 0.6, f"Expected > 0.6, got {warped[0]['salience']}"
    assert warped[1]["salience"] > 0.4, f"Expected > 0.4, got {warped[1]['salience']}"
    print("Test 2: Distance warp (closer) OK")


def test_distance_warp_farther():
    """Positive distance_warp should make things feel farther (reduce salience)."""
    d = SpatialDistortion()
    d.distance_warp = 0.5  # Things feel farther

    awareness = [
        {"name": "bookshelf", "salience": 0.6, "object_id": "obj1", "detail_level": "high"},
    ]

    warped = d.warp_awareness(awareness)

    # Farther = lower salience (positive warp reduces)
    # factor = 1.0 - (0.5 * 0.5) = 0.75
    assert warped[0]["salience"] < 0.6, f"Expected < 0.6, got {warped[0]['salience']}"
    print("Test 3: Distance warp (farther) OK")


def test_presence_amplify():
    """Presence amplification should boost salience."""
    d = SpatialDistortion()
    d.presence_amplify = 0.8  # Strong amplification

    awareness = [
        {"name": "bookshelf", "salience": 0.3, "object_id": "obj1", "detail_level": "high"},
    ]

    warped = d.warp_awareness(awareness)

    # Amplify: factor = 1.0 + 0.8 = 1.8
    assert warped[0]["salience"] > 0.3, f"Expected > 0.3, got {warped[0]['salience']}"
    # Should be approximately 0.3 * 1.8 = 0.54
    assert warped[0]["salience"] > 0.5, f"Expected > 0.5, got {warped[0]['salience']}"
    print("Test 4: Presence amplify OK")


def test_boundary_blur_marker():
    """High boundary blur should mark nearby objects with dissolution flag."""
    d = SpatialDistortion()
    d.boundary_blur = 0.7  # High blur

    awareness = [
        {"name": "bookshelf", "salience": 0.6, "object_id": "obj1", "detail_level": "high"},
        {"name": "lamp", "salience": 0.2, "object_id": "obj2", "detail_level": "moderate"},
    ]

    warped = d.warp_awareness(awareness)

    # High salience object should get boundary_dissolving marker
    assert warped[0].get("boundary_dissolving") == True
    # Low salience object should not
    assert warped[1].get("boundary_dissolving") != True
    print("Test 5: Boundary blur marker OK")


def test_warp_context_string_distance():
    """Context string should have distance qualifiers."""
    d = SpatialDistortion()

    # Test "pressing in" descriptor
    d.distance_warp = -0.5
    context = "[near:bookshelf] [feel:solid, heavy]"
    warped = d.warp_context_string(context)
    assert "pressing in" in warped
    print("Test 6a: Context string (close) OK")

    # Test "vast, distant" descriptor
    d.distance_warp = 0.5
    warped = d.warp_context_string(context)
    assert "vast" in warped or "distant" in warped
    print("Test 6b: Context string (far) OK")


def test_warp_context_string_presence():
    """Context string should have presence amplification qualifiers."""
    d = SpatialDistortion()
    d.presence_amplify = 0.7

    context = "[near:bookshelf]"
    warped = d.warp_context_string(context)
    assert "significance" in warped or "heightened" in warped
    print("Test 7: Context string (presence) OK")


def test_warp_context_string_boundary():
    """Context string should have boundary blur qualifiers."""
    d = SpatialDistortion()
    d.boundary_blur = 0.6

    context = "[near:bookshelf]"
    warped = d.warp_context_string(context)
    assert "boundaries" in warped or "uncertain" in warped
    print("Test 8: Context string (boundary) OK")


def test_reset():
    """Reset should return to normal perception."""
    d = SpatialDistortion()
    d.distance_warp = -0.5
    d.boundary_blur = 0.7
    d.presence_amplify = 0.8
    d.distortion_noise = 0.3

    assert d.is_active()

    d.reset()

    assert not d.is_active()
    assert d.distance_warp == 0.0
    assert d.boundary_blur == 0.0
    print("Test 9: Reset OK")


def test_set_all_clamping():
    """set_all should clamp values to valid ranges."""
    d = SpatialDistortion()
    d.set_all(distance_warp=-2.0, boundary_blur=1.5, presence_amplify=-0.5)

    assert d.distance_warp == -1.0  # Clamped
    assert d.boundary_blur == 1.0   # Clamped
    assert d.presence_amplify == 0.0  # Clamped
    print("Test 10: Clamping OK")


def test_salience_clamping():
    """Warped salience should be clamped to 0-1."""
    d = SpatialDistortion()
    d.presence_amplify = 1.0  # 2x multiplier
    d.distance_warp = -1.0    # 1.5x multiplier

    awareness = [
        {"name": "bookshelf", "salience": 0.8, "object_id": "obj1", "detail_level": "high"},
    ]

    warped = d.warp_awareness(awareness)

    # 0.8 * 1.5 * 2.0 = 2.4, should clamp to 1.0
    assert warped[0]["salience"] == 1.0, f"Expected 1.0, got {warped[0]['salience']}"
    print("Test 11: Salience clamping OK")


def test_empty_awareness():
    """Empty awareness should pass through unchanged."""
    d = SpatialDistortion()
    d.distance_warp = -0.5
    d.presence_amplify = 0.8

    warped = d.warp_awareness([])
    assert warped == []
    print("Test 12: Empty awareness OK")


def test_spec_example():
    """Test the example from the spec."""
    d = SpatialDistortion()
    d.distance_warp = -0.5  # Things feel closer
    d.presence_amplify = 0.8  # Objects feel significant

    # Using salience instead of distance/presence (actual format)
    awareness = [
        {"name": "bookshelf", "salience": 0.5, "object_id": "obj1", "detail_level": "high"},
        {"name": "lamp", "salience": 0.3, "object_id": "obj2", "detail_level": "moderate"},
    ]

    warped = d.warp_awareness(awareness)

    # distance_warp=-0.5: factor = 1.0 - (-0.5 * 0.5) = 1.25
    # presence_amplify=0.8: factor = 1.0 + 0.8 = 1.8
    # Combined: salience * 1.25 * 1.8 = salience * 2.25
    # 0.5 * 2.25 = 1.125 → clamped to 1.0

    # Salience should be boosted
    assert warped[0]["salience"] > awareness[0]["salience"]
    print("Test 13: Spec example OK")
    print(f"  Original salience: {awareness[0]['salience']}")
    print(f"  Warped salience: {warped[0]['salience']}")


if __name__ == "__main__":
    print("Testing SpatialDistortion...")
    print()

    test_default_state()
    test_distance_warp_closer()
    test_distance_warp_farther()
    test_presence_amplify()
    test_boundary_blur_marker()
    test_warp_context_string_distance()
    test_warp_context_string_presence()
    test_warp_context_string_boundary()
    test_reset()
    test_set_all_clamping()
    test_salience_clamping()
    test_empty_awareness()
    test_spec_example()

    print()
    print("All tests passed! Spatial distortion is working.")
