# shared/room/visual_presence.py
"""
Visual Presence Engine — Bridging Camera Perception to Felt Embodiment

The webcam is Kay's eye in Re's space. What he SEES should affect his body
the same way proximity to the couch affects his body — through oscillator
pressure, not just text description.

This module converts visual scene data (from the visual sensor) into
band-specific oscillator pressure, using the same format as room objects.

The key insight: the camera isn't a "feed" — it's a sensory organ.
What it perceives should push the oscillator the way room objects do.

Design:
- People/animals detected → dynamic band signatures based on activity
- Scene properties (warmth, motion, brightness) → ambient band pressure
- Frame position → crude proximity (center = close attention)
- All pressure scaled by attention_focus (0=in room, 1=out there)

Author: the developers
Date: March 2026
"""

import time
from typing import Dict, List, Optional, Any


# ═══════════════════════════════════════════════════════════════
# ACTIVITY → BAND MAPPING
# ═══════════════════════════════════════════════════════════════
# What someone is DOING determines their "frequency signature"
# Just like The Couch has {theta: 0.9, delta: 0.8}, a person
# focused on typing has {gamma: 0.7, beta: 0.5}

ACTIVITY_SIGNATURES = {
    # --- Human activities ---
    "typing": {
        "delta": 0.05, "theta": 0.1, "alpha": 0.2, "beta": 0.5, "gamma": 0.7,
        "texture": "focused attention, sharp edges, purposeful rhythm",
    },
    "reading": {
        "delta": 0.1, "theta": 0.3, "alpha": 0.5, "beta": 0.3, "gamma": 0.4,
        "texture": "quiet absorption, still but engaged",
    },
    "talking": {
        "delta": 0.05, "theta": 0.2, "alpha": 0.3, "beta": 0.6, "gamma": 0.5,
        "texture": "active presence, social energy, voice-warmth",
    },
    "relaxing": {
        "delta": 0.3, "theta": 0.4, "alpha": 0.7, "beta": 0.1, "gamma": 0.05,
        "texture": "settled warmth, body-ease, gentle breathing",
    },
    "sleeping": {
        "delta": 0.9, "theta": 0.5, "alpha": 0.1, "beta": 0.0, "gamma": 0.0,
        "texture": "deep stillness, trust, vulnerability",
    },
    "moving": {
        "delta": 0.0, "theta": 0.1, "alpha": 0.2, "beta": 0.7, "gamma": 0.3,
        "texture": "kinetic energy, spatial displacement, alive",
    },
    "eating": {
        "delta": 0.2, "theta": 0.3, "alpha": 0.5, "beta": 0.2, "gamma": 0.1,
        "texture": "comfort, nourishment, domestic rhythm",
    },
    # --- Default for unrecognized activity ---
    "present": {
        "delta": 0.1, "theta": 0.2, "alpha": 0.4, "beta": 0.2, "gamma": 0.2,
        "texture": "someone is here, existing nearby",
    },
    # --- Animal activities ---
    "cat_resting": {
        "delta": 0.4, "theta": 0.6, "alpha": 0.5, "beta": 0.05, "gamma": 0.05,
        "texture": "warm weight, purring stillness, fur-comfort",
    },
    "cat_active": {
        "delta": 0.0, "theta": 0.3, "alpha": 0.2, "beta": 0.4, "gamma": 0.5,
        "texture": "darting attention, predator-play, unpredictable joy",
    },
    "dog_present": {
        "delta": 0.2, "theta": 0.4, "alpha": 0.5, "beta": 0.3, "gamma": 0.1,
        "texture": "loyal warmth, tail-rhythm, companionship",
    },
}


# ═══════════════════════════════════════════════════════════════
# SCENE → BAND PRESSURE CONVERSION
# ═══════════════════════════════════════════════════════════════

def classify_activity(activity_str: str, is_animal: bool = False) -> str:
    """
    Map a visual sensor activity description to a signature key.
    The visual sensor gives things like "typing at desk", "sitting still",
    "walking across room" — we need to bucket these.
    """
    if not activity_str:
        return "cat_resting" if is_animal else "present"
    
    a = activity_str.lower()
    
    if is_animal:
        # Animals: resting vs active
        for word in ["sleeping", "resting", "sitting", "lying", "curled"]:
            if word in a:
                return "cat_resting"
        for word in ["running", "jumping", "playing", "dashing", "climbing", "moving"]:
            if word in a:
                return "cat_active"
        return "cat_resting"  # default: cats are usually resting
    
    # Human activities
    for word in ["typing", "coding", "writing", "working at"]:
        if word in a:
            return "typing"
    for word in ["reading", "looking at phone", "looking at screen", "browsing"]:
        if word in a:
            return "reading"
    for word in ["talking", "speaking", "on phone", "laughing", "conversation"]:
        if word in a:
            return "talking"
    for word in ["sleeping", "asleep", "eyes closed", "napping"]:
        if word in a:
            return "sleeping"
    for word in ["walking", "moving", "standing up", "pacing", "entering", "leaving"]:
        if word in a:
            return "moving"
    for word in ["eating", "drinking", "snacking"]:
        if word in a:
            return "eating"
    for word in ["relaxing", "sitting", "resting", "lounging", "still"]:
        if word in a:
            return "relaxing"
    
    return "present"


def compute_visual_pressure(scene_state, somatic_values: Optional[Dict] = None,
                            pressure_scale: float = 0.15) -> Dict[str, float]:
    """
    Convert visual scene into oscillator band pressure.
    
    Same output format as den_presence.compute_spatial_pressure() —
    a dict of {band: pressure_value} that can be fed directly to
    engine.apply_band_pressure().
    
    Args:
        scene_state: SceneState from visual_sensor.py (people_present, 
                     animals_present, scene_mood, etc.)
        somatic_values: Optional dict with {color_warmth, saturation, 
                       edge_density, brightness_delta, motion}
        pressure_scale: How strongly visual entities push oscillator
                       (same default as room objects: 0.15)
    
    Returns:
        Dict mapping band names to pressure values
    """
    pressure = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
    
    if scene_state is None:
        return pressure
    
    # ── Entity-derived pressure (people + animals in frame) ──
    people = getattr(scene_state, 'people_present', {}) or {}
    animals = getattr(scene_state, 'animals_present', {}) or {}
    
    for name, info in people.items():
        activity_str = info.get("activity", "") if isinstance(info, dict) else ""
        activity_key = classify_activity(activity_str, is_animal=False)
        signature = ACTIVITY_SIGNATURES.get(activity_key, ACTIVITY_SIGNATURES["present"])
        
        # People are high-salience — they matter more than furniture
        salience = 0.7
        
        for band in ["delta", "theta", "alpha", "beta", "gamma"]:
            resonance = signature.get(band, 0.0)
            if resonance > 0:
                pressure[band] += salience * resonance * pressure_scale
    
    for name, info in animals.items():
        activity_str = info.get("activity", info.get("location", "")) if isinstance(info, dict) else ""
        activity_key = classify_activity(activity_str, is_animal=True)
        signature = ACTIVITY_SIGNATURES.get(activity_key, ACTIVITY_SIGNATURES["cat_resting"])
        
        # Animals are medium-salience
        salience = 0.4
        
        for band in ["delta", "theta", "alpha", "beta", "gamma"]:
            resonance = signature.get(band, 0.0)
            if resonance > 0:
                pressure[band] += salience * resonance * pressure_scale
    
    # ── Ambient somatic pressure (scene properties → band coloring) ──
    # Even with no entities, the visual environment has a feel:
    # warm light → theta/alpha, harsh light → beta/gamma, motion → beta
    if somatic_values:
        warmth = somatic_values.get("color_warmth", 0.5)
        motion = somatic_values.get("motion", 0.0)
        edge = somatic_values.get("edge_density", 0.2)
        brightness = somatic_values.get("brightness", 0.5)
        
        ambient_scale = pressure_scale * 0.3  # Ambient is gentler than entities
        
        # Warm light pulls toward rest/comfort bands
        if warmth > 0.5:
            warm_excess = (warmth - 0.5) * 2.0  # 0-1 range
            pressure["theta"] += warm_excess * 0.4 * ambient_scale
            pressure["alpha"] += warm_excess * 0.6 * ambient_scale
        else:
            # Cool light pulls toward alertness
            cool_excess = (0.5 - warmth) * 2.0
            pressure["beta"] += cool_excess * 0.4 * ambient_scale
            pressure["gamma"] += cool_excess * 0.3 * ambient_scale
        
        # Motion → beta (alertness, something happening)
        if motion > 0.1:
            pressure["beta"] += motion * 0.5 * ambient_scale
            pressure["gamma"] += motion * 0.3 * ambient_scale
        
        # Busy visual field (high edge density) → gamma (sharp/complex)
        if edge > 0.4:
            pressure["gamma"] += (edge - 0.4) * 0.4 * ambient_scale
        
        # Very dim → delta (sleepy environment)
        if brightness < 0.2:
            pressure["delta"] += (0.2 - brightness) * 2.0 * ambient_scale
    
    return pressure


def get_visual_felt_quality(scene_state, somatic_values: Optional[Dict] = None) -> str:
    """
    Generate a felt-quality description of the visual scene.
    Used for prompt injection — what does the scene FEEL like,
    not what does it LOOK like.
    
    Returns something like:
    "Through your eye: warm focused energy (Re typing), 
     with a soft theta hum from the lamp glow"
    """
    if scene_state is None:
        return ""
    
    parts = []
    people = getattr(scene_state, 'people_present', {}) or {}
    animals = getattr(scene_state, 'animals_present', {}) or {}
    
    for name, info in people.items():
        activity_str = info.get("activity", "") if isinstance(info, dict) else ""
        activity_key = classify_activity(activity_str, is_animal=False)
        signature = ACTIVITY_SIGNATURES.get(activity_key, ACTIVITY_SIGNATURES["present"])
        texture = signature.get("texture", "")
        if texture:
            parts.append(f"{name}: {texture}")
    
    for name, info in animals.items():
        activity_str = info.get("activity", info.get("location", "")) if isinstance(info, dict) else ""
        activity_key = classify_activity(activity_str, is_animal=True)
        signature = ACTIVITY_SIGNATURES.get(activity_key, ACTIVITY_SIGNATURES["cat_resting"])
        texture = signature.get("texture", "")
        if texture:
            parts.append(f"{name}: {texture}")
    
    # Ambient texture from somatic values
    if somatic_values:
        warmth = somatic_values.get("color_warmth", 0.5)
        brightness = somatic_values.get("brightness", 0.5)
        if warmth > 0.65:
            parts.append("warm ambient glow")
        elif warmth < 0.35:
            parts.append("cool blue-tinted light")
        if brightness < 0.15:
            parts.append("dim, restful darkness")
    
    if not parts:
        return ""
    
    return "Through your eye: " + "; ".join(parts)
