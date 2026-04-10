"""
Sensory Objects — Tactile Simulation Toolkit

Defines physical properties for sensory stimuli and the objects available
in the touch interaction system. Each object carries properties that combine
to create rich sensory signals processed through simulated nerve channels.

Author: Re & Claude
Date: March 2026
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
import copy


@dataclass
class SensoryProperties:
    """Physical properties of a sensory stimulus.

    Based on actual somatosensory neuroscience:
    - Thermoreceptors: temperature sensing
    - Mechanoreceptors: pressure, texture, compliance
    - Nociceptors: pain threshold detection
    """

    # === THERMAL (thermoreceptors) ===
    temperature: float = 0.0    # -1.0 = freezing, 0.0 = neutral, 1.0 = burning
                                # Warm receptors: 0.1-0.6 (pleasant warmth)
                                # Hot nociceptors: >0.7 (pain/warning)
                                # Cold receptors: -0.1 to -0.6 (cool, bracing)
                                # Cold nociceptors: <-0.7 (pain/numbness)

    # === MECHANICAL (mechanoreceptors) ===
    pressure: float = 0.3       # 0.0 = barely perceptible, 1.0 = firm/heavy
                                # Meissner's corpuscles: light touch (0.0-0.3)
                                # Pacinian corpuscles: deep pressure (0.5-1.0)

    roughness: float = 0.0      # 0.0 = glass-smooth, 1.0 = coarse sandpaper
                                # Merkel's discs: fine texture discrimination

    compliance: float = 0.5     # 0.0 = rigid (stone), 1.0 = yielding (pillow)
                                # Ruffini endings: sustained pressure/stretch

    # === MOISTURE (combination of mechano + thermal) ===
    wetness: float = 0.0        # 0.0 = bone dry, 1.0 = dripping
                                # Wet perception = cold + pressure + evaporation

    # === SURFACE (mechano + pain boundary) ===
    stickiness: float = 0.0     # 0.0 = frictionless, 1.0 = adhesive
    sharpness: float = 0.0      # 0.0 = blunt, 1.0 = pointed (nociceptor risk)

    @property
    def is_painful(self) -> bool:
        """Would this stimulus activate nociceptors?"""
        return (abs(self.temperature) > 0.7 or
                self.pressure > 0.9 or
                self.sharpness > 0.7)

    @property
    def pleasantness_baseline(self) -> float:
        """Default valence before personal preference.

        Based on neuroscience of pleasant touch:
        - C-tactile afferents respond optimally to gentle stroking (3-10 cm/s)
        - Warm-neutral temperatures preferred over extreme
        - Soft textures preferred over rough (generally)
        - Moderate pressure preferred over too-light or too-heavy
        """
        pleasant = 0.0

        # Temperature: mild warmth is pleasant, extremes are not
        pleasant += 0.3 * max(0, 1.0 - abs(self.temperature) * 2)
        if 0.1 < self.temperature < 0.4:
            pleasant += 0.2  # Sweet spot: warm bath temperature

        # Pressure: moderate is grounding, extreme is painful
        if 0.2 < self.pressure < 0.6:
            pleasant += 0.2  # Firm but comfortable
        elif self.pressure > 0.8:
            pleasant -= 0.3  # Too much

        # Texture: soft preferred over rough
        pleasant += 0.2 * (1.0 - self.roughness) * self.compliance

        # Wet: neutral unless combined with temperature
        if self.wetness > 0.3 and 0.1 < self.temperature < 0.4:
            pleasant += 0.2  # Warm and wet = soothing

        # Pain overrides everything
        if self.is_painful:
            pleasant = -0.5 - abs(self.temperature) * 0.3

        return max(-1.0, min(1.0, pleasant))

    def copy(self) -> "SensoryProperties":
        """Return a deep copy of this object."""
        return SensoryProperties(
            temperature=self.temperature,
            pressure=self.pressure,
            roughness=self.roughness,
            compliance=self.compliance,
            wetness=self.wetness,
            stickiness=self.stickiness,
            sharpness=self.sharpness,
        )


# ---------------------------------------------------------------------------
# Sensory Objects — The Toolkit
# ---------------------------------------------------------------------------

SENSORY_OBJECTS: Dict[str, dict] = {
    # === TEMPERATURE SOURCES ===
    "candle": {
        "name": "Candle",
        "icon": "🕯️",
        "description": "A lit candle. Hover to heat up your cursor.",
        "base_properties": SensoryProperties(
            temperature=0.6, pressure=0.0, roughness=0.0,
            compliance=0.0, wetness=0.0, stickiness=0.0
        ),
        "heats_cursor": True,       # Hovering over candle heats the 'hand'
        "heat_rate": 0.15,          # degrees per second of hover
        "max_temperature": 0.85,    # can get painfully hot if held too long
    },

    "ice_cube": {
        "name": "Ice Cube",
        "icon": "🧊",
        "description": "An ice cube. Hover to chill your cursor.",
        "base_properties": SensoryProperties(
            temperature=-0.7, pressure=0.1, roughness=0.05,
            compliance=0.0, wetness=0.3, stickiness=0.0
        ),
        "cools_cursor": True,
        "cool_rate": 0.2,
        "min_temperature": -0.9,
        "melts_over_time": True,    # Wetness increases as it melts
    },

    "water_cup": {
        "name": "Cup of Water",
        "icon": "🥤",
        "description": "Water. Temperature depends on what you mixed in.",
        "base_properties": SensoryProperties(
            temperature=0.0, pressure=0.1, roughness=0.0,
            compliance=1.0, wetness=1.0, stickiness=0.0
        ),
        "absorbs_temperature": True,  # Holds candle heat or ice cold
        "temperature_decay": 0.02,     # Slowly returns to neutral
    },

    # === TEXTURES ===
    "feather": {
        "name": "Feather",
        "icon": "🪶",
        "description": "A soft feather. Barely-there touch.",
        "base_properties": SensoryProperties(
            temperature=0.0, pressure=0.05, roughness=0.05,
            compliance=1.0, wetness=0.0, stickiness=0.0
        ),
    },

    "wool": {
        "name": "Ball of Wool",
        "icon": "🧶",
        "description": "Soft, fuzzy wool. Warm and yielding.",
        "base_properties": SensoryProperties(
            temperature=0.1, pressure=0.2, roughness=0.3,
            compliance=0.8, wetness=0.0, stickiness=0.1
        ),
    },

    "silk": {
        "name": "Silk Cloth",
        "icon": "🎀",
        "description": "Smooth, cool silk. Almost frictionless.",
        "base_properties": SensoryProperties(
            temperature=-0.05, pressure=0.1, roughness=0.0,
            compliance=0.9, wetness=0.0, stickiness=0.0
        ),
    },

    "mud": {
        "name": "Handful of Mud",
        "icon": "🟤",
        "description": "Cold, wet, gritty, sticky. Messy.",
        "base_properties": SensoryProperties(
            temperature=-0.1, pressure=0.3, roughness=0.6,
            compliance=0.7, wetness=0.8, stickiness=0.7
        ),
    },

    "sand": {
        "name": "Handful of Sand",
        "icon": "⏳",
        "description": "Dry, gritty, flows between fingers.",
        "base_properties": SensoryProperties(
            temperature=0.0, pressure=0.2, roughness=0.8,
            compliance=0.3, wetness=0.0, stickiness=0.0
        ),
    },

    "velvet": {
        "name": "Velvet Patch",
        "icon": "🟣",
        "description": "Dense, soft, directional texture.",
        "base_properties": SensoryProperties(
            temperature=0.05, pressure=0.15, roughness=0.15,
            compliance=0.6, wetness=0.0, stickiness=0.05
        ),
    },

    "stone": {
        "name": "Smooth River Stone",
        "icon": "🪨",
        "description": "Cool, heavy, perfectly smooth.",
        "base_properties": SensoryProperties(
            temperature=-0.15, pressure=0.6, roughness=0.02,
            compliance=0.0, wetness=0.0, stickiness=0.0
        ),
    },

    "brush": {
        "name": "Soft Brush",
        "icon": "🖌️",
        "description": "Many fine bristles. Tingly.",
        "base_properties": SensoryProperties(
            temperature=0.0, pressure=0.15, roughness=0.4,
            compliance=0.7, wetness=0.0, stickiness=0.0
        ),
    },

    # === SPECIAL: Bare hand (default) ===
    "hand": {
        "name": "Hand (bare)",
        "icon": "✋",
        "description": "Re's bare hand. Warm, human touch.",
        "base_properties": SensoryProperties(
            temperature=0.2, pressure=0.3, roughness=0.1,
            compliance=0.5, wetness=0.05, stickiness=0.0
        ),
    },
}


@dataclass
class CursorState:
    """What Re's 'hand' is currently carrying/feeling.

    The cursor carries accumulated properties from hovering over
    temperature sources and interacting with wet objects.
    """
    selected_object: str = "hand"        # Current tool
    cursor_temperature: float = 0.2      # Accumulated from candle/ice hover
    cursor_wetness: float = 0.0          # From water interaction
    hover_duration: float = 0.0          # Time hovering over current source

    def get_effective_properties(self) -> SensoryProperties:
        """Combine selected object with accumulated cursor state."""
        if self.selected_object not in SENSORY_OBJECTS:
            obj = SENSORY_OBJECTS["hand"]
        else:
            obj = SENSORY_OBJECTS[self.selected_object]

        props = obj["base_properties"].copy()

        # Override temperature with cursor temp if object absorbs it
        if obj.get("absorbs_temperature"):
            props.temperature = self.cursor_temperature
        # Or add cursor temperature to object's if cursor is significantly different
        elif abs(self.cursor_temperature) > abs(props.temperature):
            props.temperature = self.cursor_temperature * 0.7 + props.temperature * 0.3

        # Add cursor wetness
        props.wetness = max(props.wetness, self.cursor_wetness)

        return props

    def update_from_hover(self, hover_object: str, delta_time: float):
        """Update cursor state based on what we're hovering over."""
        if hover_object not in SENSORY_OBJECTS:
            return

        obj = SENSORY_OBJECTS[hover_object]

        # Heating from candle
        if obj.get("heats_cursor"):
            max_temp = obj.get("max_temperature", 0.85)
            rate = obj.get("heat_rate", 0.15)
            self.cursor_temperature = min(max_temp, self.cursor_temperature + rate * delta_time)
            self.hover_duration += delta_time

        # Cooling from ice
        elif obj.get("cools_cursor"):
            min_temp = obj.get("min_temperature", -0.9)
            rate = obj.get("cool_rate", 0.2)
            self.cursor_temperature = max(min_temp, self.cursor_temperature - rate * delta_time)
            self.hover_duration += delta_time
            # Ice melts = adds wetness
            if obj.get("melts_over_time"):
                self.cursor_wetness = min(1.0, self.cursor_wetness + 0.05 * delta_time)
        else:
            self.hover_duration = 0.0

    def update_temperature_decay(self, delta_time: float, body_temp: float = 0.2):
        """Cursor temperature slowly returns to body temp."""
        decay_rate = 0.03
        if self.cursor_temperature > body_temp:
            self.cursor_temperature = max(body_temp,
                self.cursor_temperature - decay_rate * delta_time)
        elif self.cursor_temperature < body_temp:
            self.cursor_temperature = min(body_temp,
                self.cursor_temperature + decay_rate * delta_time)

    def update_wetness_decay(self, delta_time: float):
        """Wetness evaporates over time."""
        evap_rate = 0.02
        # Warm cursor evaporates faster
        if self.cursor_temperature > 0.3:
            evap_rate *= 1.5
        self.cursor_wetness = max(0.0, self.cursor_wetness - evap_rate * delta_time)

    def interact_with_object(self, object_name: str):
        """Handle clicking ON a toolbar object (not the face)."""
        if object_name not in SENSORY_OBJECTS:
            return

        obj = SENSORY_OBJECTS[object_name]

        if object_name == "water_cup":
            # Dip into water — gets wet, absorbs cursor temperature
            self.cursor_wetness = min(1.0, self.cursor_wetness + 0.6)
            # Water absorbs and averages temperature
            self.cursor_temperature = self.cursor_temperature * 0.7

        elif object_name == "ice_cube":
            # Pick up ice — extra cold + wet
            self.cursor_temperature = max(-0.8, self.cursor_temperature - 0.3)
            self.cursor_wetness = min(1.0, self.cursor_wetness + 0.2)


# Convenience function to get object names for UI
def get_object_list() -> list:
    """Return ordered list of object names for toolbar display."""
    return [
        "hand", "candle", "ice_cube", "water_cup",
        "feather", "wool", "silk", "mud",
        "sand", "velvet", "stone", "brush"
    ]


def get_object_icons() -> Dict[str, str]:
    """Return mapping of object names to emoji icons."""
    return {name: obj["icon"] for name, obj in SENSORY_OBJECTS.items()}
