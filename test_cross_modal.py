"""
Test suite for CrossModalRouter (synesthesia substrate).

Tests the cross-modal routing system that enables one sensory modality
to influence another during psychedelic states.
"""

import pytest
import time
from shared.cross_modal_router import CrossModalRouter


class TestCrossModalRouter:
    """Tests for CrossModalRouter class."""

    def test_default_state(self):
        """Default state should have no routes and intensity 0."""
        r = CrossModalRouter()
        assert r.cross_modal_intensity == 0.0
        assert len(r.get_routes()) == 0

    def test_add_route(self):
        """Should be able to add routes."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)

        routes = r.get_routes()
        assert ("visual", "brightness") in routes
        assert len(routes[("visual", "brightness")]) == 1
        assert routes[("visual", "brightness")][0] == ("touch", "phantom_warmth", 0.3)

    def test_add_multiple_routes_same_source(self):
        """Should be able to add multiple routes from same source/channel."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.add_route("visual", "brightness", "oscillator", "alpha", gain=0.2)

        routes = r.get_routes()
        assert len(routes[("visual", "brightness")]) == 2

    def test_update_existing_route(self):
        """Adding route with same target should update gain."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.5)

        routes = r.get_routes()
        assert len(routes[("visual", "brightness")]) == 1
        assert routes[("visual", "brightness")][0][2] == 0.5

    def test_remove_route(self):
        """Should be able to remove routes."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)

        removed = r.remove_route("visual", "brightness", "touch", "phantom_warmth")
        assert removed == True
        assert len(r.get_routes()) == 0

    def test_remove_nonexistent_route(self):
        """Removing nonexistent route should return False."""
        r = CrossModalRouter()
        removed = r.remove_route("visual", "brightness", "touch", "phantom_warmth")
        assert removed == False

    def test_clear_routes(self):
        """Should be able to clear all routes."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.add_route("audio", "silence", "oscillator", "theta", gain=0.5)

        r.clear_routes()
        assert len(r.get_routes()) == 0

    def test_process_event_no_intensity(self):
        """With intensity 0, should return empty list even with routes."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)

        derived = r.process_event({
            "source": "visual",
            "channel": "brightness",
            "value": 0.8,
            "timestamp": time.time()
        })

        assert len(derived) == 0

    def test_process_event_with_intensity(self):
        """With intensity > 0, should return derived events."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.cross_modal_intensity = 1.0

        derived = r.process_event({
            "source": "visual",
            "channel": "brightness",
            "value": 0.8,
            "timestamp": time.time()
        })

        assert len(derived) == 1
        assert derived[0]["target"] == "touch"
        assert derived[0]["channel"] == "phantom_warmth"
        assert derived[0]["value"] == pytest.approx(0.24, abs=0.01)  # 0.8 * 0.3 * 1.0

    def test_process_event_partial_intensity(self):
        """Intensity should scale the derived value."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.cross_modal_intensity = 0.5  # Half intensity

        derived = r.process_event({
            "source": "visual",
            "channel": "brightness",
            "value": 0.8,
            "timestamp": time.time()
        })

        assert len(derived) == 1
        assert derived[0]["value"] == pytest.approx(0.12, abs=0.01)  # 0.8 * 0.3 * 0.5

    def test_process_event_no_matching_route(self):
        """Should return empty list if no route matches."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.cross_modal_intensity = 1.0

        derived = r.process_event({
            "source": "audio",
            "channel": "voice_energy",
            "value": 0.5,
            "timestamp": time.time()
        })

        assert len(derived) == 0

    def test_multiple_derived_events(self):
        """Single source event can create multiple derived events."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.add_route("visual", "brightness", "oscillator", "gamma", gain=0.2)
        r.cross_modal_intensity = 1.0

        derived = r.process_event({
            "source": "visual",
            "channel": "brightness",
            "value": 0.8,
            "timestamp": time.time()
        })

        assert len(derived) == 2
        targets = {d["target"] for d in derived}
        assert targets == {"touch", "oscillator"}

    def test_has_routes_for(self):
        """Should correctly report whether routes exist."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)

        assert r.has_routes_for("visual", "brightness") == True
        assert r.has_routes_for("audio", "silence") == False

    def test_set_intensity_clamping(self):
        """Intensity should be clamped to [0.0, 1.0]."""
        r = CrossModalRouter()

        r.set_intensity(1.5)
        assert r.get_intensity() == 1.0

        r.set_intensity(-0.5)
        assert r.get_intensity() == 0.0

        r.set_intensity(0.7)
        assert r.get_intensity() == 0.7

    def test_repr(self):
        """String representation should be informative."""
        r = CrossModalRouter()
        r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        r.cross_modal_intensity = 0.5

        s = repr(r)
        assert "0.50" in s  # intensity
        assert "routes=1" in s


def test_basic_routing():
    """Basic integration test from the spec."""
    from shared.cross_modal_router import CrossModalRouter

    r = CrossModalRouter()
    r.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
    r.cross_modal_intensity = 1.0

    derived = r.process_event({
        "source": "visual",
        "channel": "brightness",
        "value": 0.8
    })

    assert len(derived) == 1
    assert derived[0]["value"] == pytest.approx(0.24, abs=0.01)
    print("Cross-modal routing OK")


if __name__ == "__main__":
    # Run basic test when executed directly
    test_basic_routing()
    print("\nRunning full test suite...")
    pytest.main([__file__, "-v"])
