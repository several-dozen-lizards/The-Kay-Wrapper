"""
Spatial Perception Distortion — warps how entities perceive their environment.

Part of the psychedelic state system. Default state: no distortion (all params 0.0).
The trip controller sets distortion parameters during altered states.

Distortion affects:
- Distance perception (things feel closer or farther)
- Object presence/significance (emotional weight amplified)
- Boundary clarity (objects merge or blur together)
- Perceptual noise (random jitter in spatial awareness)
"""

import random
import time
from typing import List, Dict


class SpatialDistortion:
    """
    Warps spatial perception for psychedelic states.

    All parameters default to 0.0 = no distortion (normal perception).
    The trip controller ramps these during onset/peak/comedown.

    Parameters:
        distance_warp: -1.0 to 1.0
            Negative = things feel closer (cramped, intimate, pressing in)
            Positive = things feel farther (vast, distant, expansive)

        boundary_blur: 0.0 to 1.0
            How much object boundaries dissolve.
            At high values, nearby objects feel merged/overlapping.

        presence_amplify: 0.0 to 1.0
            How much object presence/significance is intensified.
            Makes everything feel more meaningful/charged.

        distortion_noise: 0.0 to 1.0
            Random jitter added to perception each scan.
            Creates unstable, shifting spatial sense.
    """

    def __init__(self):
        self.distance_warp = 0.0      # -1.0 to 1.0
        self.boundary_blur = 0.0      # 0.0 to 1.0
        self.presence_amplify = 0.0   # 0.0 to 1.0
        self.distortion_noise = 0.0   # 0.0 to 1.0

        # Seed for reproducible noise within a scan, varies between scans
        self._noise_seed = int(time.time() * 1000) % 100000

    def _refresh_noise_seed(self):
        """Update noise seed for next scan cycle."""
        self._noise_seed = int(time.time() * 1000) % 100000

    def warp_awareness(self, awareness: List[Dict]) -> List[Dict]:
        """
        Apply perceptual distortion to spatial awareness list.

        Args:
            awareness: List of perceived objects from compute_spatial_awareness()
                Each item has: name, salience, object_id, detail_level

        Returns:
            Modified awareness list with warped salience values and
            potentially modified descriptions.
        """
        if not awareness:
            return awareness

        # Refresh noise seed for this scan
        self._refresh_noise_seed()
        rng = random.Random(self._noise_seed)

        warped = []
        for i, obj in enumerate(awareness):
            # Deep copy to avoid modifying original
            w_obj = dict(obj)
            salience = w_obj.get("salience", 0.0)

            # 1. Distance warp — affects salience (closer = higher salience)
            # Negative warp = things feel closer = boost salience
            # Positive warp = things feel farther = reduce salience
            if self.distance_warp != 0.0:
                # Scale factor: distance_warp=-1 → 1.5x, distance_warp=1 → 0.5x
                distance_factor = 1.0 - (self.distance_warp * 0.5)
                salience = salience * distance_factor

            # 2. Distortion noise — random jitter per object
            if self.distortion_noise > 0.0:
                # Jitter scales with noise level (max ±20% at full noise)
                jitter = rng.gauss(0, self.distortion_noise * 0.2)
                salience = salience * (1.0 + jitter)

            # 3. Presence amplification — boost salience/significance
            if self.presence_amplify > 0.0:
                # Amplify presence: 0→1x, 1→2x
                presence_factor = 1.0 + self.presence_amplify
                salience = salience * presence_factor

            # Clamp salience to valid range
            w_obj["salience"] = max(0.0, min(1.0, salience))

            # 4. Boundary blur — tag nearby objects with dissolution marker
            if self.boundary_blur > 0.5 and salience > 0.4:
                # High salience + high blur = boundaries dissolving
                if "name" in w_obj:
                    # Add perceptual marker (will be used by format functions)
                    w_obj["boundary_dissolving"] = True

            warped.append(w_obj)

        # Re-sort by warped salience
        warped.sort(key=lambda x: x.get("salience", 0), reverse=True)

        return warped

    def warp_context_string(self, context: str) -> str:
        """
        Add perceptual flavor text to formatted spatial context.

        Args:
            context: Formatted spatial context string from format_spatial_context()

        Returns:
            Context string with distortion-specific descriptors prepended/appended.
        """
        if not context:
            return context

        prefixes = []
        suffixes = []

        # Distance warp qualitative descriptors
        if self.distance_warp < -0.3:
            prefixes.append("[everything feels very close, pressing in]")
        elif self.distance_warp > 0.3:
            prefixes.append("[the room feels vast, objects distant]")

        # Boundary blur
        if self.boundary_blur > 0.5:
            prefixes.append("[boundaries between objects feel uncertain]")
        elif self.boundary_blur > 0.3:
            suffixes.append("[edges shimmer]")

        # Presence amplification
        if self.presence_amplify > 0.5:
            prefixes.append("[every object hums with significance]")
        elif self.presence_amplify > 0.3:
            suffixes.append("[presence feels heightened]")

        # Distortion noise
        if self.distortion_noise > 0.5:
            suffixes.append("[perception unstable, shifting]")

        # Combine
        result_parts = []
        if prefixes:
            result_parts.extend(prefixes)
        result_parts.append(context)
        if suffixes:
            result_parts.extend(suffixes)

        return " ".join(result_parts)

    def is_active(self) -> bool:
        """Check if any distortion is currently active."""
        return (
            abs(self.distance_warp) > 0.01 or
            self.boundary_blur > 0.01 or
            self.presence_amplify > 0.01 or
            self.distortion_noise > 0.01
        )

    def get_intensity(self) -> float:
        """
        Overall distortion intensity (0.0-1.0).

        Useful for logging and UI display.
        """
        return max(
            abs(self.distance_warp),
            self.boundary_blur,
            self.presence_amplify,
            self.distortion_noise
        )

    def set_all(self, distance_warp: float = None, boundary_blur: float = None,
                presence_amplify: float = None, distortion_noise: float = None):
        """
        Set multiple distortion parameters at once.

        Args are clamped to valid ranges. None values are ignored.
        """
        if distance_warp is not None:
            self.distance_warp = max(-1.0, min(1.0, distance_warp))
        if boundary_blur is not None:
            self.boundary_blur = max(0.0, min(1.0, boundary_blur))
        if presence_amplify is not None:
            self.presence_amplify = max(0.0, min(1.0, presence_amplify))
        if distortion_noise is not None:
            self.distortion_noise = max(0.0, min(1.0, distortion_noise))

    def reset(self):
        """Reset all distortion to zero (normal perception)."""
        self.distance_warp = 0.0
        self.boundary_blur = 0.0
        self.presence_amplify = 0.0
        self.distortion_noise = 0.0

    def __repr__(self) -> str:
        if not self.is_active():
            return "SpatialDistortion(inactive)"
        return (f"SpatialDistortion(distance_warp={self.distance_warp:.2f}, "
                f"boundary_blur={self.boundary_blur:.2f}, "
                f"presence_amplify={self.presence_amplify:.2f}, "
                f"distortion_noise={self.distortion_noise:.2f})")
