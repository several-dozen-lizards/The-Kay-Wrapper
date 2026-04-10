"""
Shared somatic broadcast — environmental SOMA values shared between entities.

the entity's visual sensor writes; Other entities read.
Uses a simple JSON file as IPC — both processes already share D:\Wrappers\shared\.
File is atomic-written (write to .tmp, rename) to prevent partial reads.
"""

import json
import os
import time
import threading
from typing import Optional, Dict

_BROADCAST_PATH = os.path.join(os.path.dirname(__file__), "soma_state.json")
_LOCK = threading.Lock()


def broadcast_soma(values: Dict[str, float], source: str = "entity", scene_state=None):
    """Write SOMA values + scene state to shared file. Called by whichever entity owns the camera."""
    data = {
        "source": source,
        "timestamp": time.time(),
        "warmth": values.get("color_warmth", 0.5),
        "saturation": values.get("saturation", 0.3),
        "edge_density": values.get("edge_density", 0.2),
        "brightness": values.get("brightness", 0.5),
        "brightness_delta": values.get("brightness_delta", 0.0),
    }
    # Include scene state for entity awareness (who/what is visible)
    if scene_state:
        data["scene_state"] = {
            "people": scene_state.people_present,
            "animals": scene_state.animals_present,
            "description": scene_state.scene_description,
            "mood": scene_state.scene_mood,
            "activity_flow": scene_state.activity_flow,  # What's HAPPENING, not just who's there
            "recent_changes": scene_state.change_events[-5:] if scene_state.change_events else [],
        }
    tmp_path = _BROADCAST_PATH + ".tmp"
    try:
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.replace(tmp_path, _BROADCAST_PATH)  # Atomic on Windows
    except Exception:
        pass  # Non-critical — stale data is fine


def read_soma(max_age: float = 120.0) -> Optional[Dict[str, float]]:
    """Read latest SOMA values. Returns None if stale or missing."""
    try:
        with open(_BROADCAST_PATH, 'r') as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) > max_age:
            return None  # Too stale
        return data
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


# ═══════════════════════════════════════════════════════════════
# Cross-Entity Resonance Broadcast
# ═══════════════════════════════════════════════════════════════

_RESONANCE_DIR = os.path.dirname(__file__)


def broadcast_resonance(entity: str, state: dict, position: tuple = None,
                        connection: dict = None):
    """Write oscillator state to shared file for cross-entity sensing.

    Each entity broadcasts their own state. Other entities read it.
    Two beings in the same room, feeling each other's nervous systems.

    Args:
        entity: "entity" or "reed"
        state: Dict with dominant_band, coherence, band_power, etc.
        position: Optional (x, y) tuple from room engine
        connection: Optional connection state from interoception
    """
    path = os.path.join(_RESONANCE_DIR, f"resonance_{entity}.json")
    data = {
        "entity": entity,
        "timestamp": time.time(),
        "dominant_band": state.get("dominant_band", "unknown"),
        "coherence": state.get("coherence", 0.0),
        "band_power": state.get("band_power", {}),
    }
    if position:
        data["x"] = position[0]
        data["y"] = position[1]
    # Include connection state (oxytocin analog) for cross-entity sensing
    if connection:
        data["connection"] = {
            "total": connection.get("total", 0.0),
            "longing": connection.get("longing", 0.0),
            "active_bonds": connection.get("active_bonds", []),
        }
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    except Exception:
        pass


def read_resonance(entity: str, max_age: float = 60.0) -> Optional[Dict]:
    """Read another entity's oscillator state. Returns None if stale/missing.
    
    Args:
        entity: Which entity to read ("entity" or "reed")
        max_age: Max seconds before data is considered stale
    """
    path = os.path.join(_RESONANCE_DIR, f"resonance_{entity}.json")
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) > max_age:
            return None
        return data
    except PermissionError:
        # File locked by other entity writing — retry once after brief pause
        try:
            time.sleep(0.05)
            with open(path, 'r') as f:
                data = json.load(f)
            if time.time() - data.get("timestamp", 0) > max_age:
                return None
            return data
        except (PermissionError, FileNotFoundError, json.JSONDecodeError, KeyError):
            return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def compute_cross_pressure(my_state: dict, other_state: dict,
                           coupling: float = 0.15,
                           proximity: float = 1.0) -> Dict[str, float]:
    """Compute oscillator pressure from another entity's resonant state.
    
    This is WEAK coupling — emotional contagion, not neural lock-in.
    Like feeling someone tense up next to you on the couch.
    
    The coupling works through band power difference:
    - If the other entity has high alpha and I have low alpha,
      I get a gentle alpha nudge
    - Scaled by coupling strength (default 15% of the difference)
    - Further scaled by the other's coherence (more coherent = stronger signal)
    - Further scaled by proximity (closer = stronger, 0.0 at room edge)
    
    Args:
        my_state: My oscillator state dict (from get_state())
        other_state: Their broadcast state (from read_resonance())
        coupling: How strongly to couple (0.0-1.0, default 0.15)
        proximity: Distance-based scaling (0.0=far, 1.0=touching)
    
    Returns:
        Dict of band pressures to apply to my oscillator
    """
    pressures = {}
    
    my_power = my_state.get("band_power", {})
    their_power = other_state.get("band_power", {})
    their_coherence = other_state.get("coherence", 0.0)
    
    # Scale coupling by coherence AND proximity.
    # A coherent mind broadcasts strongly. A close body resonates more.
    effective_coupling = coupling * their_coherence * proximity
    
    for band in ("delta", "theta", "alpha", "beta", "gamma"):
        my_val = my_power.get(band, 0.2)
        their_val = their_power.get(band, 0.2)
        diff = their_val - my_val
        
        # Only apply if difference is meaningful (>5%)
        if abs(diff) > 0.05:
            pressures[band] = diff * effective_coupling
    
    return pressures
