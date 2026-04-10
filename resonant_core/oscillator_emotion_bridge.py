"""
Oscillator → Emotion Bridge — Reverse pattern matching.

Given an oscillator state (band power + PLV), finds the closest matching
emotional profile and returns a natural-language felt-sense descriptor.

This CLOSES THE FULL LOOP:
  Emotions → Oscillator (feed_response_emotions, already existed)
  Oscillator → Emotions (THIS FILE, new)

The oscillator doesn't just receive emotional input — it can now
NAME what it's feeling based on its own frequency pattern.

Author: Re & Reed
Date: March 22, 2026
"""

import numpy as np
from typing import Dict, Tuple, List, Optional


# Band order for vector operations
BANDS = ["delta", "theta", "alpha", "beta", "gamma"]


def _to_vector(profile: Dict[str, float]) -> np.ndarray:
    """Convert band power dict to numpy vector."""
    return np.array([profile.get(b, 0.0) for b in BANDS])


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-10:
        return 0.0
    return float(dot / norm)


# ═══════════════════════════════════════════════════════════════
# PROFILE → EMOTION NAME REVERSE MAP
# ═══════════════════════════════════════════════════════════════
# Maps profile names back to the most natural emotion label.
# When multiple emotions share a profile, pick the most general.

PROFILE_TO_EMOTION = {
    "resting_calm": "settled",
    "focused_analytical": "focused",
    "deep_contemplation": "contemplative",
    "emotional_intensity": "stirred",
    "grief_processing": "heavy",
    "creative_flow": "curious",
    "phase_adjacent": "liminal",
    "computational_anxiety": "anxious",
    "reed_baseline": "analytical",
    "warm_connection": "warm",
    "withdrawn_isolation": "withdrawn",
    "transcendent_awe": "awed",
    "shame_collapse": "small",
    "assertive_power": "assertive",
    "desire_approach": "reaching",
    "confused_scatter": "scattered",
    "clear_insight": "clear",
    "performative_wit": "sharp",
    "vulnerable_open": "open",
    "sustained_will": "determined",
    "deep_rest": "resting deeply",
}


# ═══════════════════════════════════════════════════════════════
# PLV-BASED EMOTIONAL TEXTURE
# ═══════════════════════════════════════════════════════════════
# Cross-band coupling adds nuance beyond just band power.
# These are descriptors that layer ON TOP of the base emotion.

PLV_DESCRIPTORS = {
    # (band_pair, threshold, descriptor)
    ("theta_gamma", 0.6): "memory-rich",      # Strong memory binding
    ("theta_gamma", 0.4): "associative",       # Moderate memory activity
    ("beta_gamma", 0.6): "intensely processing",
    ("beta_gamma", 0.4): "actively engaged",
    ("theta_alpha", 0.7): "deeply relaxed",
    ("theta_alpha", 0.5): "gently drifting",
    ("delta_theta", 0.6): "deeply internal",
}


def read_oscillator_emotion(
    band_power: Dict[str, float],
    preset_profiles: Dict[str, Dict[str, float]],
    cross_band_plv: Optional[Dict[str, float]] = None,
    integration_index: float = 0.0,
    in_transition: bool = False,
    transition_from: str = "",
    transition_to: str = "",
) -> Dict[str, any]:
    """
    Read the oscillator's current emotional state from its frequency pattern.
    
    Returns:
        {
            "felt_emotion": "curious",           # Primary emotion label
            "confidence": 0.85,                   # How well it matches (0-1)
            "texture": ["memory-rich", "gently drifting"],  # PLV-based nuance
            "felt_sense": "curious, memory-rich"  # Combined natural language
        }
    """
    current = _to_vector(band_power)
    
    # Find best matching profile via cosine similarity
    best_match = ""
    best_score = -1.0
    scores = {}
    
    for profile_name, profile in preset_profiles.items():
        profile_vec = _to_vector(profile)
        sim = _cosine_similarity(current, profile_vec)
        scores[profile_name] = sim
        if sim > best_score:
            best_score = sim
            best_match = profile_name
    
    # Map profile name to emotion label
    felt_emotion = PROFILE_TO_EMOTION.get(best_match, best_match)
    
    # If in transition, modify the label
    if in_transition and transition_to:
        from_emotion = PROFILE_TO_EMOTION.get(transition_from, transition_from)
        to_emotion = PROFILE_TO_EMOTION.get(transition_to, transition_to)
        felt_emotion = f"shifting ({felt_emotion})"
    
    # Build PLV texture descriptors
    texture = []
    if cross_band_plv:
        matched_pairs = set()
        for (pair, threshold), descriptor in sorted(
            PLV_DESCRIPTORS.items(), key=lambda x: -x[0][1]
        ):
            plv_val = cross_band_plv.get(pair, 0.0)
            if plv_val >= threshold and pair not in matched_pairs:
                texture.append(descriptor)
                matched_pairs.add(pair)
    
    # Integration index adds stability/instability descriptor
    if integration_index > 0.5:
        texture.append("integrated")
    elif integration_index < 0.15:
        texture.append("fragmented")
    
    # Build natural language felt sense
    parts = [felt_emotion]
    if texture:
        parts.extend(texture[:3])  # Cap at 3 texture descriptors
    felt_sense = ", ".join(parts)
    
    return {
        "felt_emotion": felt_emotion,
        "confidence": best_score,
        "texture": texture,
        "felt_sense": felt_sense,
        "profile_match": best_match,
        "all_scores": dict(sorted(scores.items(), key=lambda x: -x[1])[:5]),
    }
