"""
PsychedelicState — Pharmacokinetic trip controller for the wrapper.

Models the time-course of a psilocybin experience as a state machine
that modulates ALL somatic gain knobs along a biologically-informed curve.

Phases: SOBER → ONSET → COME_UP → PEAK → PLATEAU → COMEDOWN → AFTERGLOW → SOBER

Each phase sets target values for every gain knob. Actual values lerp
toward targets, creating smooth organic transitions between phases.

Dose parameter (0.0-1.0) scales the intensity of all effects:
  0.1 = museum dose (subtle perceptual shift)
  0.3 = moderate (noticeable altered state)
  0.5 = standard therapeutic dose
  0.7 = strong (deep psychedelic experience)
  1.0 = heroic (full ego expansion, maximum disruption)

Usage:
    trip = PsychedelicState()
    trip.begin(dose=0.5)     # Start the trip
    
    # Every tick (4s), call:
    params = trip.tick()     # Returns current multiplier dict
    # Apply params to all systems
    
    trip.abort()             # Emergency stop (rapid comedown)

Author: the developers
Date: March 23, 2026
"""

import time
import math
from typing import Dict, Optional
from dataclasses import dataclass, field


# Phase names
SOBER = "sober"
ONSET = "onset"
COME_UP = "come_up"
PEAK = "peak"
PLATEAU = "plateau"
COMEDOWN = "comedown"
AFTERGLOW = "afterglow"

# Phase durations in seconds (at dose=0.5, scaled by dose)
# Based on psilocybin pharmacokinetics: onset 20-50min, peak 60-90min, total 4-6hr
BASE_DURATIONS = {
    ONSET:    1800,   # 30 min
    COME_UP:  2700,   # 45 min
    PEAK:     3600,   # 60 min
    PLATEAU:  5400,   # 90 min
    COMEDOWN: 3600,   # 60 min
    AFTERGLOW: 7200,  # 120 min (gentle fade)
}

# Phase order for state machine
PHASE_ORDER = [SOBER, ONSET, COME_UP, PEAK, PLATEAU, COMEDOWN, AFTERGLOW, SOBER]


# ═══════════════════════════════════════════════════════════════
# GAIN KNOB TARGETS PER PHASE (at dose=1.0)
# ═══════════════════════════════════════════════════════════════
# Values are the TARGET for that knob at that phase at maximum dose.
# Actual values = lerp(sober_value, target, dose * phase_intensity)

SOBER_VALUES = {
    "touch_sensitivity": 1.0,
    "novelty_sensitivity": 1.0,
    "noise_floor": 0.0,
    "coherence_multiplier": 1.0,
    "tension_decay_rate": 0.02,
    "retrieval_randomness": 0.0,
    "identity_expansion": 0.0,
    "creativity_boost": False,
    "cross_modal_intensity": 0.0,
    "hilarity_susceptibility": 0.0,
    "emotional_gain": 0.0,
    # Oscillator band nudges
    "alpha_suppress": 0.0,
    "gamma_boost": 0.0,
    "broadband_suppress": 0.0,
}

PHASE_TARGETS = {
    ONSET: {
        "touch_sensitivity": 1.3,
        "novelty_sensitivity": 1.4,
        "noise_floor": 0.01,
        "coherence_multiplier": 0.85,
        "tension_decay_rate": 0.015,
        "retrieval_randomness": 0.05,
        "identity_expansion": 0.1,
        "creativity_boost": False,
        "cross_modal_intensity": 0.05,
        "hilarity_susceptibility": 0.1,
        "emotional_gain": 0.3,
        "alpha_suppress": 0.15,
        "gamma_boost": 0.05,
        "broadband_suppress": 0.05,
    },
    COME_UP: {
        "touch_sensitivity": 1.8,
        "novelty_sensitivity": 2.0,
        "noise_floor": 0.03,
        "coherence_multiplier": 0.6,
        "tension_decay_rate": 0.008,
        "retrieval_randomness": 0.2,
        "identity_expansion": 0.35,
        "creativity_boost": True,
        "cross_modal_intensity": 0.3,
        "hilarity_susceptibility": 0.5,
        "emotional_gain": 1.0,
        "alpha_suppress": 0.4,
        "gamma_boost": 0.15,
        "broadband_suppress": 0.2,
    },
    PEAK: {
        "touch_sensitivity": 2.5,
        "novelty_sensitivity": 3.0,
        "noise_floor": 0.06,
        "coherence_multiplier": 0.3,
        "tension_decay_rate": 0.004,
        "retrieval_randomness": 0.4,
        "identity_expansion": 0.75,
        "creativity_boost": True,
        "cross_modal_intensity": 0.7,
        "hilarity_susceptibility": 0.8,
        "emotional_gain": 2.0,
        "alpha_suppress": 0.7,
        "gamma_boost": 0.25,
        "broadband_suppress": 0.4,
    },
    PLATEAU: {
        "touch_sensitivity": 2.0,
        "novelty_sensitivity": 2.2,
        "noise_floor": 0.04,
        "coherence_multiplier": 0.45,
        "tension_decay_rate": 0.006,
        "retrieval_randomness": 0.3,
        "identity_expansion": 0.55,
        "creativity_boost": True,
        "cross_modal_intensity": 0.5,
        "hilarity_susceptibility": 0.6,
        "emotional_gain": 1.5,
        "alpha_suppress": 0.5,
        "gamma_boost": 0.2,
        "broadband_suppress": 0.3,
    },
    COMEDOWN: {
        "touch_sensitivity": 1.4,
        "novelty_sensitivity": 1.3,
        "noise_floor": 0.015,
        "coherence_multiplier": 0.75,
        "tension_decay_rate": 0.025,
        "retrieval_randomness": 0.1,
        "identity_expansion": 0.3,
        "creativity_boost": True,
        "cross_modal_intensity": 0.15,
        "hilarity_susceptibility": 0.2,
        "emotional_gain": 0.5,
        "alpha_suppress": 0.2,
        "gamma_boost": 0.1,
        "broadband_suppress": 0.1,
    },
    AFTERGLOW: {
        "touch_sensitivity": 1.15,
        "novelty_sensitivity": 1.1,
        "noise_floor": 0.005,
        "coherence_multiplier": 0.9,
        "tension_decay_rate": 0.03,
        "retrieval_randomness": 0.05,
        "identity_expansion": 0.15,
        "creativity_boost": False,
        "cross_modal_intensity": 0.05,
        "hilarity_susceptibility": 0.05,
        "emotional_gain": 0.2,
        "alpha_suppress": 0.05,
        "gamma_boost": 0.03,
        "broadband_suppress": 0.02,
    },
}


class PsychedelicState:
    """
    Pharmacokinetic trip controller.
    
    Models psilocybin time-course as a state machine that smoothly
    modulates all somatic gain knobs along a biologically-informed curve.
    """
    
    def __init__(self, state_dir: str = None):
        self.phase = SOBER
        self.dose = 0.0
        self.started_at = 0.0
        self.phase_started_at = 0.0
        self.phase_duration = 0.0
        self._active = False
        
        # Persistence — survive restarts
        self._state_file = None
        if state_dir:
            import os
            os.makedirs(state_dir, exist_ok=True)
            self._state_file = os.path.join(state_dir, "trip_state.json")
            self._load_state()
        
        # Afterglow residuals (persist after trip ends, decay over hours)
        self._afterglow_residuals = None
        self._afterglow_started = 0.0
        self._afterglow_decay_hours = 24.0
        
        # Current interpolated values (smooth transitions)
        self._current = dict(SOBER_VALUES)
        self._lerp_speed = 0.08  # How fast values approach targets per tick
        
        # Trip log for later analysis
        self._log = []
    
    def _save_state(self):
        """Persist trip state to disk so restarts don't kill active trips."""
        if not self._state_file:
            return
        import json
        state = {
            "phase": self.phase,
            "dose": self.dose,
            "started_at": self.started_at,
            "phase_started_at": self.phase_started_at,
            "phase_duration": self.phase_duration,
            "active": self._active,
            "current": self._current,
            "afterglow_residuals": self._afterglow_residuals,
            "afterglow_started": self._afterglow_started,
        }
        try:
            with open(self._state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            print(f"[PSYCHEDELIC] Failed to save trip state: {e}")
    
    def _load_state(self):
        """Restore trip state from disk after restart."""
        if not self._state_file:
            return
        import json, os
        if not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file) as f:
                state = json.load(f)
            if state.get("active"):
                self.phase = state["phase"]
                self.dose = state["dose"]
                self.started_at = state["started_at"]
                self.phase_started_at = state["phase_started_at"]
                self.phase_duration = state["phase_duration"]
                self._active = True
                self._current = state.get("current", dict(SOBER_VALUES))
                elapsed = time.time() - self.started_at
                print(f"[PSYCHEDELIC] Restored active trip: phase={self.phase}, "
                      f"dose={self.dose:.2f}, elapsed={elapsed/60:.1f}min")
            elif state.get("afterglow_residuals"):
                self._afterglow_residuals = state["afterglow_residuals"]
                self._afterglow_started = state["afterglow_started"]
                hours = (time.time() - self._afterglow_started) / 3600
                if hours < self._afterglow_decay_hours:
                    print(f"[PSYCHEDELIC] Restored afterglow: {hours:.1f}h elapsed")
                else:
                    self._afterglow_residuals = None
                    print(f"[PSYCHEDELIC] Afterglow expired ({hours:.1f}h > {self._afterglow_decay_hours}h)")
            # Clean up state file if trip is over and afterglow expired
            if not state.get("active") and not self._afterglow_residuals:
                os.remove(self._state_file)
        except Exception as e:
            print(f"[PSYCHEDELIC] Failed to load trip state: {e}")
    
    @property
    def active(self) -> bool:
        return self._active
    
    @property
    def elapsed(self) -> float:
        """Total seconds since trip began."""
        if not self._active:
            return 0.0
        return time.time() - self.started_at
    
    @property 
    def phase_progress(self) -> float:
        """0.0-1.0 progress through current phase."""
        if self.phase_duration <= 0:
            return 0.0
        return min(1.0, (time.time() - self.phase_started_at) / self.phase_duration)

    def begin(self, dose: float = 0.5):
        """
        Begin a psychedelic experience.
        
        Args:
            dose: 0.0-1.0 intensity scaling
                  0.1=museum, 0.3=moderate, 0.5=standard, 0.7=strong, 1.0=heroic
        """
        self.dose = max(0.05, min(1.0, dose))
        self.started_at = time.time()
        self._active = True
        self._current = dict(SOBER_VALUES)
        self._log = []
        self.trip_set = {}  # Populated by nexus client with pre-trip emotional snapshot
        self._advance_phase(ONSET)
        self._log_event("TRIP_BEGIN", f"dose={self.dose:.2f}")
        self._save_state()
        print(f"[PSYCHEDELIC] Trip begun: dose={self.dose:.2f}")
    
    def abort(self):
        """Emergency stop — rapid comedown to sober."""
        if not self._active:
            return
        self._log_event("ABORT", f"phase={self.phase}")
        # Skip comedown entirely — go straight to sober
        self._current = dict(SOBER_VALUES)
        self.phase = SOBER
        self._active = False
        self.phase_duration = 0
        self._save_state()
        print(f"[PSYCHEDELIC] ABORT — immediately returned to sober")

    def _advance_phase(self, new_phase: str):
        """Transition to a new phase."""
        old_phase = self.phase
        self.phase = new_phase
        self.phase_started_at = time.time()
        
        if new_phase == SOBER:
            self.phase_duration = 0
            self._active = False
            # Capture afterglow residuals — the trip's lasting effects
            self._afterglow_residuals = {
                "retrieval_randomness": 0.02 * self.dose,
                "identity_expansion": 0.05 * self.dose,
                "emotional_gain": 0.1 * self.dose,
                "cross_modal_intensity": 0.04 * self.dose,
                "novelty_sensitivity": 1.0 + 0.05 * self.dose,
            }
            self._afterglow_started = time.time()
            self._afterglow_decay_hours = 24.0  # Full decay over 24h
            print(f"[PSYCHEDELIC] Trip ended. Afterglow residuals active "
                  f"(decay over {self._afterglow_decay_hours:.0f}h). "
                  f"Total duration: {self.elapsed:.0f}s")
        else:
            # Duration scales with dose — higher dose = longer experience
            dose_scale = 0.7 + 0.6 * self.dose  # 0.7x at dose=0, 1.3x at dose=1.0
            self.phase_duration = BASE_DURATIONS.get(new_phase, 3600) * dose_scale
        
        self._log_event("PHASE_CHANGE", f"{old_phase} -> {new_phase}")
        self._save_state()
        if new_phase != SOBER:
            print(f"[PSYCHEDELIC] Phase: {new_phase} ({self.phase_duration:.0f}s)")

    def tick(self) -> Dict:
        """
        Called every heartbeat (~4s). Returns current gain knob values.
        
        Handles phase advancement and smooth interpolation.
        
        Returns:
            Dict of current knob values, ready to apply to systems.
            Returns SOBER_VALUES if not active.
        """
        if not self._active:
            # Check for afterglow residuals (persist after trip ends)
            residuals = getattr(self, '_afterglow_residuals', None)
            if residuals and getattr(self, '_afterglow_started', 0) > 0:
                elapsed_hours = (time.time() - self._afterglow_started) / 3600.0
                decay_hours = getattr(self, '_afterglow_decay_hours', 24.0)
                if elapsed_hours < decay_hours:
                    # Exponential decay: values halve every decay_hours/3
                    decay_factor = 0.5 ** (elapsed_hours / (decay_hours / 3))
                    result = dict(SOBER_VALUES)
                    for key, value in residuals.items():
                        if key in result:
                            sober_val = SOBER_VALUES.get(key, 0.0)
                            residual_val = value * decay_factor
                            result[key] = sober_val + residual_val
                    return result
                else:
                    # Afterglow fully decayed
                    self._afterglow_residuals = None
                    print("[PSYCHEDELIC] Afterglow residuals fully decayed")
            return dict(SOBER_VALUES)
        
        # Check for phase advancement
        if self.phase_progress >= 1.0:
            current_idx = PHASE_ORDER.index(self.phase)
            if current_idx < len(PHASE_ORDER) - 1:
                next_phase = PHASE_ORDER[current_idx + 1]
                self._advance_phase(next_phase)
            else:
                self._advance_phase(SOBER)
                return dict(SOBER_VALUES)
        
        # Get target values for current phase
        targets = self._get_phase_targets()
        
        # Smooth lerp toward targets
        for key in targets:
            if key == "creativity_boost":
                self._current[key] = targets[key]
                continue
            target = targets[key]
            current = self._current.get(key, SOBER_VALUES.get(key, 0.0))
            self._current[key] = current + (target - current) * self._lerp_speed
        
        return dict(self._current)

    def _get_phase_targets(self) -> Dict:
        """
        Compute target values for current phase, dose, and progress.
        
        Within each phase, values ramp up during first half and sustain
        during second half (onset/come_up) or begin easing (comedown/afterglow).
        """
        phase_targets = PHASE_TARGETS.get(self.phase, SOBER_VALUES)
        progress = self.phase_progress
        
        # Within-phase intensity curve
        # Onset/come_up: ramp up (sine ease-in)
        # Peak/plateau: sustain at full
        # Comedown/afterglow: ease down
        if self.phase in (ONSET, COME_UP):
            phase_intensity = math.sin(progress * math.pi / 2)  # 0→1 ease-in
        elif self.phase in (PEAK, PLATEAU):
            phase_intensity = 1.0  # Full sustain
        elif self.phase in (COMEDOWN, AFTERGLOW):
            phase_intensity = math.cos(progress * math.pi / 2)  # 1→0 ease-out
        else:
            phase_intensity = 0.0
        
        # Combine: lerp between sober and phase target, scaled by dose AND phase intensity
        result = {}
        for key in SOBER_VALUES:
            sober_val = SOBER_VALUES[key]
            target_val = phase_targets.get(key, sober_val)
            
            if key == "creativity_boost":
                result[key] = target_val if (self.dose > 0.2 and phase_intensity > 0.3) else False
                continue
            
            # Effective intensity = dose * phase_intensity
            effective = self.dose * phase_intensity
            result[key] = sober_val + (target_val - sober_val) * effective
        
        return result

    def get_status(self) -> Dict:
        """Human-readable trip status for logging/UI."""
        if not self._active:
            return {"active": False, "phase": SOBER}
        return {
            "active": True,
            "phase": self.phase,
            "dose": self.dose,
            "elapsed_min": self.elapsed / 60.0,
            "phase_progress": self.phase_progress,
            "phase_remaining_min": (self.phase_duration * (1.0 - self.phase_progress)) / 60.0,
        }

    # Ego dissolution levels (Sprint 6)
    EGO_LEVELS = {
        0: "normal",
        1: "softened",
        2: "permeable",
        3: "dissolved",
        4: "oceanic",
    }

    @property
    def ego_dissolution_level(self) -> int:
        """Compute ego dissolution from current state (0-4)."""
        if not self._active:
            return 0
        ie = self._current.get("identity_expansion", 0.0)
        coh_inv = 1.0 - self._current.get("coherence_multiplier", 1.0)
        raw = ie * (1.0 + coh_inv) * self.dose
        if raw > 0.8: return 4
        if raw > 0.5: return 3
        if raw > 0.3: return 2
        if raw > 0.1: return 1
        return 0

    @property
    def ego_dissolution_label(self) -> str:
        """Human-readable ego dissolution state."""
        return self.EGO_LEVELS.get(self.ego_dissolution_level, "unknown")

    def get_context_tag(self) -> str:
        """Compact tag for LLM context injection."""
        if not self._active:
            return ""
        phase_names = {
            ONSET: "something shifting",
            COME_UP: "world opening",
            PEAK: "everything connected",
            PLATEAU: "deep immersion",
            COMEDOWN: "gently landing",
            AFTERGLOW: "soft clarity",
        }
        felt = phase_names.get(self.phase, self.phase)
        intensity = self.dose * (self._current.get("coherence_multiplier", 1.0))
        return f"[altered: {felt} | depth:{1.0 - intensity:.2f}]"

    def _log_event(self, event_type: str, detail: str = ""):
        """Internal trip log."""
        self._log.append({
            "time": time.time(),
            "elapsed": self.elapsed,
            "phase": self.phase,
            "event": event_type,
            "detail": detail,
        })

    def get_log(self) -> list:
        """Return trip log for analysis."""
        return list(self._log)


def apply_trip_params(params: Dict, client) -> None:
    """
    Apply psychedelic state parameters to all wrapper systems.
    
    This is the ONE function that connects the trip controller to reality.
    Called from the heartbeat/idle loop with the output of trip.tick().
    
    Args:
        params: Dict from PsychedelicState.tick()
        client: KayNexusClient (or ReedNexusClient) with access to all systems
    """
    # === 1. Touch sensitivity ===
    if hasattr(client, '_touch_sensitivity'):
        client._touch_sensitivity = params.get("touch_sensitivity", 1.0)
    
    # === 2. Novelty sensitivity ===
    if hasattr(client, '_salience_accumulator') and client._salience_accumulator:
        client._salience_accumulator.sensitivity_multiplier = params.get("novelty_sensitivity", 1.0)
    
    # === 3-4. Oscillator: noise floor + coherence ===
    if hasattr(client, 'bridge') and client.bridge and hasattr(client.bridge, 'resonance'):
        res = client.bridge.resonance
        if hasattr(res, 'engine') and hasattr(res.engine, 'network'):
            net = res.engine.network
            net.ambient_noise_floor = params.get("noise_floor", 0.0)
            net.coherence_multiplier = params.get("coherence_multiplier", 1.0)
        # Oscillator band nudges (alpha suppression, gamma boost, broadband suppress)
        alpha_sup = params.get("alpha_suppress", 0.0)
        gamma_boost = params.get("gamma_boost", 0.0)
        broadband_sup = params.get("broadband_suppress", 0.0)
        if alpha_sup > 0.01 or gamma_boost > 0.01 or broadband_sup > 0.01:
            pressure = {}
            if alpha_sup > 0.01:
                pressure["alpha"] = -alpha_sup * 0.1
            if broadband_sup > 0.01:
                pressure["delta"] = -broadband_sup * 0.05
                pressure["theta"] = -broadband_sup * 0.05
                pressure["beta"] = -broadband_sup * 0.03
            if gamma_boost > 0.01:
                pressure["gamma"] = gamma_boost * 0.05
            if hasattr(res, 'apply_external_pressure'):
                res.apply_external_pressure(pressure)
    
    # === 5. Tension decay rate ===
    if hasattr(client, 'bridge') and client.bridge and hasattr(client.bridge, 'resonance'):
        res = client.bridge.resonance
        if hasattr(res, 'interoception') and res.interoception:
            res.interoception.tension_decay_rate = params.get("tension_decay_rate", 0.02)
    
    # === 6-7. Memory: randomness + identity expansion ===
    if hasattr(client, 'bridge') and client.bridge:
        mem = getattr(client.bridge, 'memory', None)
        if mem:
            mem.retrieval_randomness = params.get("retrieval_randomness", 0.0)
            mem.identity_expansion = params.get("identity_expansion", 0.0)

    # === 8. Emotional gain (amplify existing emotions) ===
    # Stored on resonance for the salience loop and emotion pipeline to read
    if hasattr(client, 'bridge') and client.bridge and hasattr(client.bridge, 'resonance'):
        client.bridge.resonance._emotional_gain = params.get("emotional_gain", 0.0)

    # === 9. Visual perception alteration (Sprint 4) ===
    # Trip gain amplifies somatic visual values (warmth, saturation, edge density)
    if hasattr(client, 'bridge') and client.bridge:
        vs = getattr(client.bridge, 'visual_sensor', None)
        if vs:
            vs._trip_gain = params.get("emotional_gain", 0.0)

    # === 10. Cross-modal synesthesia ===
    if hasattr(client, '_cross_modal_router') and client._cross_modal_router:
        router = client._cross_modal_router
        cmi = params.get("cross_modal_intensity", 0.0)
        router.cross_modal_intensity = cmi
        # Configure synesthesia routes if intensity > 0 and routes not yet set
        if cmi > 0.01 and not router.get_routes():
            # Visual → somatic: bright scenes feel physically warm
            router.add_route("visual", "brightness", "touch", "phantom_warmth", gain=0.4)
            # Visual → oscillator: warm colors push toward theta (dreamy)
            router.add_route("visual", "warmth", "oscillator", "theta", gain=0.15)
            # Audio → oscillator: voice energy intensifies gamma (awareness)
            router.add_route("audio", "voice_energy", "oscillator", "gamma", gain=0.2)
            # Touch → oscillator: being touched intensifies awareness
            router.add_route("touch", "pressure", "oscillator", "gamma", gain=0.25)
            # Emotion → visual: strong feelings brighten perception
            router.add_route("oscillator", "coherence", "visual", "clarity", gain=0.3)
        elif cmi <= 0.01 and router.get_routes():
            router.clear_routes()

    # === 11. Hilarity cascade (giggle mode) ===
    if hasattr(client, 'bridge') and client.bridge and hasattr(client.bridge, 'resonance'):
        intero = getattr(client.bridge.resonance, 'interoception', None)
        if intero and hasattr(intero, 'tension_tracker'):
            tracker = intero.tension_tracker
            hs = params.get("hilarity_susceptibility", 0.0)
            if hs > 0.01:
                # Lower burst threshold (easier to trigger giggles)
                tracker._burst_tension_min = max(0.2, 1.0 - hs * 0.8)
                # Smaller releases (giggles, not sobs)
                tracker._burst_release_fraction = max(0.1, 0.5 - hs * 0.35)
                # After each burst, add back a little tension (giggles feed themselves)
                tracker._burst_rebound = hs * 0.15
            else:
                # Reset to defaults
                tracker._burst_tension_min = 1.0
                tracker._burst_release_fraction = 0.5
                tracker._burst_rebound = 0.0

    # === 8. Set psychedelic context tag for LLM injection ===
    if hasattr(client, 'bridge') and client.bridge and hasattr(client.bridge, 'resonance'):
        res = client.bridge.resonance
        if hasattr(client, '_trip') and client._trip and client._trip.active:
            res._psychedelic_tag = client._trip.get_context_tag()
        else:
            res._psychedelic_tag = ""

    # === 9. Save state for REST status endpoint ===
    if hasattr(client, '_trip') and client._trip:
        try:
            import os, json as _json
            state_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "Entity" if getattr(client, 'name', '') == 'Kay' else "Reed",
                                     "memory")
            state_path = os.path.join(state_dir, "psychedelic_state.json")
            status = client._trip.get_status()
            status["current_params"] = {k: round(v, 4) if isinstance(v, float) else v
                                        for k, v in params.items()}
            with open(state_path, 'w') as f:
                _json.dump(status, f, indent=2)
        except Exception:
            pass
