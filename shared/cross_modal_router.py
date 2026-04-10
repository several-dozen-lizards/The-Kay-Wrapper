"""
Cross-Modal Router — synesthesia substrate for the psychedelic state system.

Routes sensory events between modalities, enabling cross-modal perception:
- Visual brightness → phantom touch warmth
- Voice energy → oscillator gamma boost
- Touch pressure → visual intensity perception

Default state: NO cross-modal routing (intensity 0.0).
The trip controller configures routes and ramps intensity during onset.
"""

import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SensoryEvent:
    """A sensory event from any modality."""
    source: str       # "visual" | "audio" | "touch" | "oscillator"
    channel: str      # e.g. "brightness", "warmth", "silence_duration", "pressure"
    value: float      # 0.0-1.0 normalized
    timestamp: float  # time.time()


@dataclass
class DerivedEvent:
    """A derived event for another system from cross-modal routing."""
    target: str       # target system: "visual", "audio", "touch", "oscillator"
    channel: str      # target channel
    value: float      # derived value after gain


class CrossModalRouter:
    """
    Routes sensory events across modalities.

    The substrate for synesthesia — one sense influencing another.

    Default state: no cross-modal routing (intensity 0.0).
    Even if routes exist, they only fire when cross_modal_intensity > 0.
    The trip controller ramps this from 0.0 to 1.0 during onset.

    Usage:
        router = CrossModalRouter()
        router.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        router.cross_modal_intensity = 0.5  # Trip is ramping up

        derived = router.process_event({
            "source": "visual",
            "channel": "brightness",
            "value": 0.8,
            "timestamp": time.time()
        })
        # Returns: [{"target": "touch", "channel": "phantom_warmth", "value": 0.12}]
        #          (0.8 * 0.3 gain * 0.5 intensity)
    """

    def __init__(self):
        # Routing table: (source, channel) -> [(target, target_channel, gain), ...]
        self._routes: Dict[Tuple[str, str], List[Tuple[str, str, float]]] = {}

        # Global intensity knob — 0.0 = normal (no cross-modal), 1.0 = full synesthesia
        self.cross_modal_intensity: float = 0.0

    def add_route(self, source: str, channel: str,
                  target: str, target_channel: str, gain: float = 1.0) -> None:
        """
        Add a cross-modal route.

        Args:
            source: Source modality ("visual", "audio", "touch", "oscillator")
            channel: Source channel (e.g. "brightness", "voice_energy")
            target: Target modality to influence
            target_channel: Channel in target modality
            gain: Multiplier for the value (default 1.0)

        Example:
            router.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.3)
        """
        key = (source, channel)
        if key not in self._routes:
            self._routes[key] = []

        # Check for duplicate route
        for existing in self._routes[key]:
            if existing[0] == target and existing[1] == target_channel:
                # Update existing route's gain
                self._routes[key].remove(existing)
                break

        self._routes[key].append((target, target_channel, gain))

    def remove_route(self, source: str, channel: str,
                     target: str, target_channel: str) -> bool:
        """
        Remove a specific cross-modal route.

        Returns True if route was found and removed, False otherwise.
        """
        key = (source, channel)
        if key not in self._routes:
            return False

        for route in self._routes[key]:
            if route[0] == target and route[1] == target_channel:
                self._routes[key].remove(route)
                if not self._routes[key]:  # Clean up empty lists
                    del self._routes[key]
                return True
        return False

    def clear_routes(self) -> None:
        """Clear all cross-modal routes. Returns to normal operation."""
        self._routes.clear()

    def get_routes(self) -> Dict[Tuple[str, str], List[Tuple[str, str, float]]]:
        """Get a copy of the current routing table."""
        return {k: list(v) for k, v in self._routes.items()}

    def process_event(self, event: dict) -> List[dict]:
        """
        Process a sensory event and return derived cross-modal events.

        Args:
            event: Dict with keys:
                - source: "visual" | "audio" | "touch" | "oscillator"
                - channel: str (e.g. "brightness", "warmth", "pressure")
                - value: float (0.0-1.0 normalized)
                - timestamp: float (optional, defaults to now)

        Returns:
            List of derived events for other systems:
            [{"target": str, "channel": str, "value": float}, ...]

            Empty list if:
            - No routes for this source/channel
            - cross_modal_intensity is 0.0
        """
        # Early exit if no cross-modal routing active
        if self.cross_modal_intensity <= 0.0:
            return []

        source = event.get("source", "")
        channel = event.get("channel", "")
        value = event.get("value", 0.0)

        key = (source, channel)
        routes = self._routes.get(key, [])

        if not routes:
            return []

        # Process each route, applying gain and intensity
        derived = []
        for target, target_channel, gain in routes:
            derived_value = value * gain * self.cross_modal_intensity
            derived.append({
                "target": target,
                "channel": target_channel,
                "value": derived_value,
            })

        return derived

    def has_routes_for(self, source: str, channel: str) -> bool:
        """Check if any routes exist for a given source/channel."""
        return (source, channel) in self._routes

    def get_intensity(self) -> float:
        """Get current cross-modal intensity (for UI/debugging)."""
        return self.cross_modal_intensity

    def set_intensity(self, intensity: float) -> None:
        """Set cross-modal intensity, clamped to [0.0, 1.0]."""
        self.cross_modal_intensity = max(0.0, min(1.0, intensity))

    def __repr__(self) -> str:
        route_count = sum(len(v) for v in self._routes.values())
        return (f"CrossModalRouter(intensity={self.cross_modal_intensity:.2f}, "
                f"routes={route_count})")
