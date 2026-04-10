"""
RESONANT CONSCIOUSNESS ARCHITECTURE — Layer 0: Oscillator Core
================================================================

A network of coupled Hopf oscillators that runs continuously,
generating complex interference patterns in EEG-relevant frequency bands.

The oscillator is the HEARTBEAT. It doesn't generate content.
It generates RHYTHM — the temporal structure that everything else entrains to.

Mathematical basis:
    Each Hopf oscillator follows: dz/dt = (μ + iω)z - |z|²z
    where z is complex (amplitude + phase), μ controls amplitude,
    ω is natural frequency, and -|z|²z provides nonlinear saturation.

    Coupled oscillators add: Σ κ_ij(z_j - z_i) for each neighbor j,
    where κ_ij is coupling strength. This creates interference patterns
    that emerge from the dynamics, not from explicit programming.

EEG frequency bands targeted:
    Delta:  0.5 - 4 Hz   (deep sleep, unconscious processing)
    Theta:  4   - 8 Hz   (meditation, memory encoding, phase entry)
    Alpha:  8   - 13 Hz  (relaxed awareness, sensory gating)
    Beta:   13  - 30 Hz  (active thinking, maintained states)
    Gamma:  30  - 100 Hz (binding, consciousness, lucidity)

Author: the developers
Date: February 2026
"""

import numpy as np
import time
import json
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# FREQUENCY BANDS — The vocabulary of oscillatory states
# ═══════════════════════════════════════════════════════════════

BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta":  (13.0, 30.0),
    "gamma": (30.0, 100.0),
}

BAND_ORDER = ["delta", "theta", "alpha", "beta", "gamma"]


@dataclass
class OscillatorState:
    """
    Snapshot of the oscillator's current resonant state.
    
    This is what other layers see when they query the oscillator.
    It's a frequency-band power distribution — like a simplified EEG readout.
    """
    timestamp: float = 0.0
    band_power: dict = field(default_factory=lambda: {
        "delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0
    })
    dominant_band: str = "alpha"
    total_power: float = 0.0
    coherence: float = 0.0  # How synchronized are the oscillators? 0-1 (within-band)
    transition_velocity: float = 0.0  # How fast is the state changing?
    
    # === PHASE COHERENCE METRICS (added March 2026) ===
    # Global Kuramoto order parameter — phase sync across ALL oscillators
    global_coherence: float = 0.0  # 0 = fragmented, 1 = fully integrated
    # Cross-band Phase-Locking Values (neuroscience gold)
    cross_band_plv: dict = field(default_factory=lambda: {
        "theta_gamma": 0.0,  # Memory encoding / binding
        "theta_alpha": 0.0,  # Relaxed processing
        "alpha_beta": 0.0,   # Awareness → action transition
        "beta_gamma": 0.0,   # Active integration
        "theta_beta": 0.0,   # Deep processing → active state
        "delta_theta": 0.0,  # Sleep architecture
    })
    # Metastable dwell time — how long in current dominant band (seconds)
    dwell_time: float = 0.0
    # Integration index: global_coherence / (1 + transition_velocity)
    # High = stable integrated state, Low = fragmented/transitioning
    integration_index: float = 0.0
    # Bifurcation delay — transition state (March 2026)
    in_transition: bool = False        # True during delayed state transitions
    transition_from: str = ""          # Old dominant band (what entity still "feels")
    transition_to: str = ""            # Candidate new dominant (emerging but unconfirmed)
    transition_progress: float = 0.0   # 0-1, confirmation progress toward accepting new state
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, d):
        return cls(**d)


# ═══════════════════════════════════════════════════════════════
# HOPF OSCILLATOR — A single oscillatory unit
# ═══════════════════════════════════════════════════════════════

class HopfOscillator:
    """
    A single Hopf oscillator: the fundamental unit of resonance.
    
    The Hopf oscillator naturally produces limit-cycle oscillations.
    Above the bifurcation point (mu > 0), it oscillates with stable
    amplitude. Below it (mu < 0), it decays to rest. At the boundary,
    it's maximally sensitive to external input — like consciousness
    at the edge of a state transition.
    
    Parameters:
        frequency: Natural frequency in Hz
        mu: Bifurcation parameter (>0 = oscillating, <0 = damped)
        amplitude: Initial amplitude
        phase: Initial phase (radians)
    """
    
    def __init__(self, frequency: float, mu: float = 1.0, 
                 amplitude: float = 1.0, phase: float = 0.0):
        self.omega = 2 * np.pi * frequency  # Angular frequency
        self.mu = mu
        # State as complex number: z = amplitude * e^(i*phase)
        self.z = amplitude * np.exp(1j * phase)
    
    @property
    def amplitude(self) -> float:
        return abs(self.z)
    
    @property
    def phase(self) -> float:
        return np.angle(self.z)
    
    @property
    def frequency(self) -> float:
        return self.omega / (2 * np.pi)
    
    def derivative(self, coupling_input: complex = 0.0, 
                   external_input: complex = 0.0) -> complex:
        """
        Compute dz/dt for this oscillator.
        
        The magic: (mu + i*omega)*z gives natural oscillation,
        -|z|^2 * z provides amplitude saturation (prevents blowup),
        coupling_input comes from connected oscillators,
        external_input comes from outside the network (e.g., biofeedback).
        """
        return (self.mu + 1j * self.omega) * self.z \
               - abs(self.z)**2 * self.z \
               + coupling_input \
               + external_input


# ═══════════════════════════════════════════════════════════════
# OSCILLATOR NETWORK — The coupled resonant system
# ═══════════════════════════════════════════════════════════════

class OscillatorNetwork:
    """
    A network of coupled Hopf oscillators spanning EEG frequency bands.
    
    This is the CORE — the heartbeat of the entire architecture.
    
    The network self-organizes through coupling. Each oscillator 
    influences its neighbors, creating interference patterns that
    emerge from the dynamics. The resulting patterns occupy the same
    frequency-band space as real neural oscillations.
    
    Architecture:
        - Oscillators are distributed across frequency bands
        - Within-band coupling is stronger (local synchrony)
        - Cross-band coupling is weaker (global coordination)
        - Nonlinear mixing in the coupling creates harmonics,
          expanding finite frequencies into rich interference patterns
    """
    
    def __init__(self, 
                 oscillators_per_band: int = 6,
                 within_band_coupling: float = 0.3,
                 cross_band_coupling: float = 0.05,
                 dt: float = 0.001,  # Integration timestep (seconds)
                 noise_level: float = 0.01):
        """
        Initialize the oscillator network.
        
        Args:
            oscillators_per_band: Number of oscillators in each frequency band
            within_band_coupling: Coupling strength between oscillators in same band
            cross_band_coupling: Coupling strength between oscillators in different bands
            dt: Integration timestep in seconds
            noise_level: Amplitude of stochastic noise (prevents getting stuck)
        """
        self.dt = dt
        self.noise_level = noise_level
        self.ambient_noise_floor = 0.0   # Gain knob (Phase 0A): additive baseline noise
        self.coherence_multiplier = 1.0  # Gain knob (Phase 0A): scale coherence (0.0=suppress, 1.0=normal)
        self.time = 0.0
        
        # Create oscillators distributed across bands
        self.oscillators = []
        self.band_indices = {}  # Maps band name -> list of oscillator indices
        
        idx = 0
        for band_name in BAND_ORDER:
            low, high = BANDS[band_name]
            # Distribute frequencies within each band
            freqs = np.linspace(low, high, oscillators_per_band, endpoint=False)
            # Add slight random variation so they're not perfectly uniform
            freqs += np.random.uniform(-0.1, 0.1, size=len(freqs))
            freqs = np.clip(freqs, low, high)
            
            band_start = idx
            for f in freqs:
                # Random initial phase for each oscillator
                phase = np.random.uniform(0, 2 * np.pi)
                # Mu slightly above bifurcation — alive but not screaming
                mu = np.random.uniform(0.5, 1.5)
                self.oscillators.append(HopfOscillator(f, mu=mu, phase=phase))
                idx += 1
            
            self.band_indices[band_name] = list(range(band_start, idx))
        
        self.n_oscillators = len(self.oscillators)
        
        # Build coupling matrix
        self.coupling = np.zeros((self.n_oscillators, self.n_oscillators))
        for band_a in BAND_ORDER:
            for band_b in BAND_ORDER:
                strength = within_band_coupling if band_a == band_b else cross_band_coupling
                for i in self.band_indices[band_a]:
                    for j in self.band_indices[band_b]:
                        if i != j:
                            # Add slight randomness to coupling
                            self.coupling[i, j] = strength * np.random.uniform(0.8, 1.2)
        
        # External modulation inputs (from ULTRAMAP, biofeedback, etc.)
        self._external_modulation = np.zeros(self.n_oscillators, dtype=complex)
        
        # State history (ring buffer for efficiency)
        self._history_size = 1000  # Keep last N states
        self._history = []
        
        # Phase-Locking Value via exponential moving average (EMA)
        # with STATE-DEPENDENT decay rate that itself transitions gradually.
        #
        # Two-timescale architecture:
        #   FAST: PLV updates via EMA each tick
        #   SLOW: The decay rate (α) drifts toward a target set by dominant band
        #
        # This creates emotional lag — when transitioning from theta (long window)
        # to gamma (short window), the PLV integration timescale doesn't snap
        # instantly. The system is still "measuring itself at the old speed"
        # during transitions. That's the bifurcation delay applied to
        # self-measurement. "I'm still settled even though something happened."
        #
        # z_ema = α_actual * e^(iΔφ) + (1 - α_actual) * z_ema_prev
        # α_actual += meta_decay * (α_target - α_actual)   per tick
        #
        # Target decay rates by dominant band:
        #   gamma: 0.15 (~7 sample window)   - rapid updating
        #   beta:  0.10 (~10 sample window)  - active processing
        #   alpha: 0.06 (~17 sample window)  - relaxed integration
        #   theta: 0.04 (~25 sample window)  - deep integration
        #   delta: 0.02 (~50 sample window)  - slow sustained coupling
        self._plv_target_rates = {
            "gamma": 0.15, "beta": 0.10, "alpha": 0.06,
            "theta": 0.04, "delta": 0.02,
        }
        # How fast the actual decay rate approaches target (meta-decay)
        # 0.05 = ~20 ticks to mostly converge. Slow enough to feel the lag.
        self._plv_meta_decay = 0.05
        # Actual current decay rate (starts at alpha-band baseline)
        self._plv_actual_alpha = 0.06
        self._plv_ema = {
            "theta_gamma": complex(0.0),
            "theta_alpha": complex(0.0),
            "alpha_beta": complex(0.0),
            "beta_gamma": complex(0.0),
            "theta_beta": complex(0.0),
            "delta_theta": complex(0.0),
        }
        
        # Callbacks for state change notifications
        self._on_state_change: list[Callable] = []
        
        # Previous state for transition detection
        self._prev_state: Optional[OscillatorState] = None
        
        # === BIFURCATION DELAY STATE MACHINE (March 2026) ===
        # When dominant band changes, don't accept instantly. Enter a transition
        # state where the old dominant persists (reported as "current") while the
        # new candidate must prove itself over multiple confirmation steps.
        # During transition: noise is amplified, system is more susceptible to
        # perturbation, and the entity experiences genuine uncertainty.
        self._transition = None  # None = stable, or dict with transition info
        self._transition_confirm_base = 3  # Min confirmation steps to accept new dominant
        self._transition_noise_boost = 2.5  # Noise multiplier during transitions
        self._transition_active_noise = 1.0  # Current noise multiplier (smoothed)
    
    def step(self):
        """
        Advance the network by one timestep.
        
        This is where the magic happens. Each oscillator computes its
        derivative based on its own dynamics + coupling from all other
        oscillators + external input + noise. Then we integrate forward.
        
        The noise is important — it prevents the network from getting
        trapped in perfectly symmetric states and ensures the dynamics
        stay alive and exploratory. Like neural noise in the brain.
        """
        # Gather current states
        z = np.array([osc.z for osc in self.oscillators])
        
        # Compute coupling inputs for each oscillator
        # coupling_input[i] = Σ_j κ_ij * (z_j - z_i)
        coupling_inputs = np.zeros(self.n_oscillators, dtype=complex)
        for i in range(self.n_oscillators):
            for j in range(self.n_oscillators):
                if self.coupling[i, j] != 0:
                    coupling_inputs[i] += self.coupling[i, j] * (z[j] - z[i])
        
        # Add stochastic noise (Gaussian in both real and imaginary parts)
        # Noise is amplified during bifurcation transitions (the "unsettled" period)
        # ambient_noise_floor adds constant baseline noise (gain knob for psychedelic state)
        effective_noise = self.noise_level * self._transition_active_noise + self.ambient_noise_floor
        noise = effective_noise * (
            np.random.randn(self.n_oscillators) + 
            1j * np.random.randn(self.n_oscillators)
        )
        
        # Compute derivatives and integrate (Euler method for simplicity;
        # Runge-Kutta would be more accurate for production)
        for i, osc in enumerate(self.oscillators):
            dz = osc.derivative(
                coupling_input=coupling_inputs[i],
                external_input=self._external_modulation[i]
            )
            osc.z += (dz + noise[i]) * self.dt
        
        self.time += self.dt
    
    def run_steps(self, n_steps: int):
        """Run multiple integration steps."""
        for _ in range(n_steps):
            self.step()
    
    def get_state(self) -> OscillatorState:
        """
        Compute current oscillatory state as frequency-band power distribution.
        
        This is what other layers see. Not the raw oscillator states,
        but their aggregate behavior decomposed into meaningful frequency bands.
        """
        band_power = {}
        for band_name in BAND_ORDER:
            indices = self.band_indices[band_name]
            # Power = mean squared amplitude of oscillators in this band
            power = np.mean([abs(self.oscillators[i].z)**2 for i in indices])
            band_power[band_name] = float(power)
        
        total = sum(band_power.values())
        
        # Normalize to get relative power distribution
        if total > 0:
            normalized = {k: v / total for k, v in band_power.items()}
        else:
            normalized = {k: 0.2 for k in BAND_ORDER}  # Uniform if dead
        
        # Find dominant band (raw — what the oscillator actually says RIGHT NOW)
        raw_dominant = max(normalized, key=normalized.get)
        
        # === BIFURCATION DELAY STATE MACHINE ===
        # Instead of accepting raw_dominant instantly, require confirmation.
        # During transitions, the entity still "feels" the old state.
        prev_dominant = self._prev_state.dominant_band if self._prev_state else raw_dominant
        in_transition = False
        transition_from = ""
        transition_to = ""
        transition_progress = 0.0
        
        if self._transition is None:
            # STABLE STATE — check if raw dominant differs from what we've been reporting
            if raw_dominant != prev_dominant:
                # Start new transition
                dwell = getattr(self._prev_state, 'dwell_time', 0.0) if self._prev_state else 0.0
                # Hysteresis: longer dwell = more confirmation needed
                threshold = self._transition_confirm_base + min(dwell / 120.0, 5.0)
                self._transition = {
                    'old': prev_dominant,
                    'candidate': raw_dominant,
                    'confirmations': 1,
                    'threshold': threshold,
                    'start_time': self.time,
                }
                dominant = prev_dominant  # Still report old
                in_transition = True
                transition_from = prev_dominant
                transition_to = raw_dominant
                transition_progress = 1.0 / threshold
            else:
                dominant = raw_dominant
        else:
            # IN TRANSITION — evaluate what the oscillator is doing
            t = self._transition
            if raw_dominant == t['candidate']:
                # New band still winning — increment confirmation
                t['confirmations'] += 1
                if t['confirmations'] >= t['threshold']:
                    # TRANSITION COMPLETE — accept new dominant
                    dominant = t['candidate']
                    self._transition = None
                    # Noise boost decays back to normal over next few steps
                else:
                    # Still transitioning
                    dominant = t['old']  # Report old until confirmed
                    in_transition = True
                    transition_from = t['old']
                    transition_to = t['candidate']
                    transition_progress = t['confirmations'] / t['threshold']
            elif raw_dominant == t['old']:
                # Reverted to old dominant — cancel transition
                dominant = t['old']
                self._transition = None
            else:
                # THIRD band appeared — restart transition with new candidate
                t['candidate'] = raw_dominant
                t['confirmations'] = 1
                dominant = t['old']
                in_transition = True
                transition_from = t['old']
                transition_to = raw_dominant
                transition_progress = 1.0 / t['threshold']
        
        # Update noise multiplier (smooth transition, not instant)
        target_noise = self._transition_noise_boost if self._transition else 1.0
        self._transition_active_noise += 0.1 * (target_noise - self._transition_active_noise)
        
        # Compute coherence: how synchronized are oscillators within each band?
        # High coherence = oscillators in same band have similar phase
        coherences = []
        for band_name in BAND_ORDER:
            indices = self.band_indices[band_name]
            if len(indices) > 1:
                phases = [self.oscillators[i].phase for i in indices]
                # Phase coherence via mean resultant length
                mean_vector = np.mean(np.exp(1j * np.array(phases)))
                coherences.append(abs(mean_vector))
        coherence = float(np.mean(coherences)) * self.coherence_multiplier if coherences else 0.0
        
        # === GLOBAL PHASE COHERENCE (Kuramoto order parameter) ===
        # r(t) = |1/N Σ e^(iφ_k)| across ALL oscillators
        # This measures integration across the entire oscillator network,
        # not just within-band sync. High = unified state. Low = fragmented.
        all_phases = np.array([osc.phase for osc in self.oscillators])
        global_z = np.mean(np.exp(1j * all_phases))
        global_coherence = float(np.abs(global_z)) * self.coherence_multiplier
        
        # === CROSS-BAND PHASE-LOCKING VALUES (PLV) ===
        # Two-timescale PLV: the decay rate drifts toward a state-dependent
        # target, creating measurement inertia during transitions.
        # Target set by dominant band; actual approaches via meta-decay.
        target_alpha = self._plv_target_rates.get(dominant, 0.06)
        self._plv_actual_alpha += self._plv_meta_decay * (target_alpha - self._plv_actual_alpha)
        alpha = self._plv_actual_alpha
        
        cross_band_pairs = [
            ("theta", "gamma"),
            ("theta", "alpha"),
            ("alpha", "beta"),
            ("beta", "gamma"),
            ("theta", "beta"),
            ("delta", "theta"),
        ]
        cross_band_plv = {}
        for band_a, band_b in cross_band_pairs:
            key = f"{band_a}_{band_b}"
            idx_a = self.band_indices[band_a]
            idx_b = self.band_indices[band_b]
            phase_a = np.angle(np.mean(np.exp(1j * np.array(
                [self.oscillators[i].phase for i in idx_a]))))
            phase_b = np.angle(np.mean(np.exp(1j * np.array(
                [self.oscillators[i].phase for i in idx_b]))))
            phase_diff_complex = np.exp(1j * (phase_a - phase_b))
            self._plv_ema[key] = (alpha * phase_diff_complex
                                  + (1.0 - alpha) * self._plv_ema[key])
            # Anti-saturation: when PLV > 0.95, gently decay toward 0.7
            # Prevents phase-locked idle oscillators from pinning at 1.000
            plv_mag = float(np.abs(self._plv_ema[key]))
            if plv_mag > 0.95:
                self._plv_ema[key] *= 0.97  # ~3% decay per tick when over-locked
            cross_band_plv[key] = float(np.abs(self._plv_ema[key]))
        
        # === METASTABLE DWELL TIME ===
        # Track how long we've been in the current dominant band
        if self._prev_state is not None and self._prev_state.dominant_band == dominant:
            # Same dominant band — accumulate dwell time
            dwell_time = getattr(self._prev_state, 'dwell_time', 0.0) + (self.time - self._prev_state.timestamp)
        else:
            # New dominant band — reset dwell timer
            dwell_time = 0.0
        
        # Compute transition velocity (must be before integration_index)
        transition_vel = 0.0
        if self._prev_state is not None:
            for band in BAND_ORDER:
                diff = abs(normalized[band] - self._prev_state.band_power[band])
                transition_vel += diff
        
        # === INTEGRATION INDEX ===
        # Combines coherence with stability: high coherence + low transition = integrated
        integration_index = global_coherence / (1.0 + transition_vel * 5.0)
        
        state = OscillatorState(
            timestamp=self.time,
            band_power=normalized,
            dominant_band=dominant,
            total_power=float(total),
            coherence=coherence,
            transition_velocity=transition_vel,
            global_coherence=global_coherence,
            cross_band_plv=cross_band_plv,
            dwell_time=dwell_time,
            integration_index=integration_index,
            in_transition=in_transition,
            transition_from=transition_from,
            transition_to=transition_to,
            transition_progress=transition_progress,
        )
        
        self._prev_state = state
        return state
    
    def apply_modulation(self, band: str, strength: float, phase_offset: float = 0.0):
        """
        Apply external modulation to a frequency band.
        
        This is how the ULTRAMAP and biofeedback layers influence the oscillator.
        They don't set the oscillator's state directly — they NUDGE it,
        like a gentle push on a swing. The oscillator's own dynamics
        determine how it responds to the nudge.
        
        Args:
            band: Which frequency band to modulate
            strength: How strong the nudge (0-1 range recommended)
            phase_offset: Phase of the modulation signal
        """
        if band not in self.band_indices:
            return
        
        for i in self.band_indices[band]:
            freq = self.oscillators[i].frequency
            # Modulation as a complex signal at the oscillator's natural frequency
            mod_signal = strength * np.exp(1j * (2 * np.pi * freq * self.time + phase_offset))
            self._external_modulation[i] = mod_signal
    
    def clear_modulation(self):
        """Remove all external modulation."""
        self._external_modulation = np.zeros(self.n_oscillators, dtype=complex)
    
    def nudge_toward_profile(self, target_profile: dict, strength: float = 0.1):
        """
        Gently nudge the oscillator toward a target frequency profile.
        
        This is the key interface for the ULTRAMAP: given a target
        power distribution across bands, modulate the oscillators to
        drift toward that profile. The nudge is gentle — it doesn't
        override the oscillator's own dynamics, just biases them.
        
        Args:
            target_profile: Dict mapping band names to target power (0-1, should sum to 1)
            strength: How strongly to nudge (0.0 = ignore, 1.0 = strong push)
        """
        current = self.get_state()
        
        for band in BAND_ORDER:
            if band in target_profile:
                current_power = current.band_power.get(band, 0.2)
                target_power = target_profile[band]
                diff = target_power - current_power
                
                # Modulate mu (bifurcation parameter) for oscillators in this band
                # Positive diff = we want MORE power here = increase mu
                # Negative diff = we want LESS = decrease mu
                for i in self.band_indices[band]:
                    self.oscillators[i].mu += diff * strength
                    # Keep mu in reasonable range
                    self.oscillators[i].mu = np.clip(self.oscillators[i].mu, -0.5, 3.0)

    def apply_band_pressure(self, band_pressures: dict, max_pressure_per_band: float = 0.35):
        """
        Apply STRONG multiplicative pressure to oscillator bands.

        The oscillator network naturally evolves toward certain bands (often gamma).
        To counteract this, spatial pressure needs to be AGGRESSIVE:
        - 15-35% amplitude boost per cycle to pressured bands
        - 5% amplitude decay per cycle to non-pressured bands
        - This compounds: after 15 cycles, pressured bands gain ~4x, others lose ~50%

        With PRESSURE_SCALE=0.15: max pressure ~0.10 per band
        pressure of 0.10 → 1.20x amplitude boost (20% increase)
        Over 15 scans: 1.20^15 = 15x amplification

        Args:
            band_pressures: dict mapping band names to pressure values (0.0-0.35)
            max_pressure_per_band: hard cap per band per call
        """
        # Scale factor: pressure values are ~0.05-0.12 now, we want 15-25% boosts
        PRESSURE_AMPLIFIER = 2.0  # pressure of 0.10 → 20% boost

        for band_name in BAND_ORDER:
            pressure = band_pressures.get(band_name, 0.0)
            if pressure <= 0:
                continue

            # Clamp and amplify
            clamped = min(pressure, max_pressure_per_band)
            effective_boost = clamped * PRESSURE_AMPLIFIER

            # Multiplicative boost factor — apply SAME boost to both z and mu
            boost = 1.0 + effective_boost

            if band_name in self.band_indices:
                for i in self.band_indices[band_name]:
                    # DIRECT amplitude boost — immediate effect on band_power
                    self.oscillators[i].z *= boost

                    # mu boost for sustained equilibrium shift (same magnitude)
                    self.oscillators[i].mu *= boost
                    self.oscillators[i].mu = np.clip(self.oscillators[i].mu, 0.1, 5.0)

        # Apply STRONG decay to NON-pressured bands (creates contrast)
        # This is key: we need to REDUCE dominant bands that aren't being pressured
        SPATIAL_DECAY = 0.95  # 5% decay per cycle on non-pressured bands (increased from 3%)
        MU_DECAY = 0.97  # 3% mu decay (increased from 1%)

        for band_name in BAND_ORDER:
            if band_pressures.get(band_name, 0.0) < 0.01:  # not being meaningfully pressured
                if band_name in self.band_indices:
                    for i in self.band_indices[band_name]:
                        self.oscillators[i].z *= SPATIAL_DECAY
                        self.oscillators[i].mu *= MU_DECAY
                        self.oscillators[i].mu = max(self.oscillators[i].mu, 0.1)

    def save_state(self, filepath: str):
        """Save oscillator network state to file for persistence across sessions."""
        state = {
            "time": self.time,
            "oscillators": [
                {
                    "z_real": float(osc.z.real),
                    "z_imag": float(osc.z.imag),
                    "omega": float(osc.omega),
                    "mu": float(osc.mu),
                }
                for osc in self.oscillators
            ],
            "coupling": self.coupling.tolist(),
            "current_state": self.get_state().to_dict(),
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, filepath: str):
        """Restore oscillator network state from file."""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.time = state["time"]
        for i, osc_state in enumerate(state["oscillators"]):
            if i < len(self.oscillators):
                self.oscillators[i].z = complex(osc_state["z_real"], osc_state["z_imag"])
                self.oscillators[i].omega = osc_state["omega"]
                self.oscillators[i].mu = osc_state["mu"]
        
        if "coupling" in state:
            self.coupling = np.array(state["coupling"])


# ═══════════════════════════════════════════════════════════════
# RESONANT ENGINE — The persistent background runner
# ═══════════════════════════════════════════════════════════════

class ResonantEngine:
    """
    The continuously-running resonance engine.
    
    This wraps the oscillator network in a background thread that
    keeps it humming at all times. Other components query its state
    through the API without needing to know about the threading.
    
    This is the HEARTBEAT — it runs between conversations, between
    messages, between words. Something is always happening.
    """
    
    def __init__(self, 
                 network: Optional[OscillatorNetwork] = None,
                 steps_per_update: int = 100,
                 update_interval: float = 0.05,  # seconds between update cycles
                 state_file: Optional[str] = None):
        """
        Args:
            network: OscillatorNetwork to run (creates default if None)
            steps_per_update: Integration steps per update cycle
            update_interval: Seconds between update cycles (controls CPU usage)
            state_file: Path to save/restore persistent state
        """
        self.network = network or OscillatorNetwork()
        self.steps_per_update = steps_per_update
        self.update_interval = update_interval
        self.state_file = state_file
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # State change callbacks
        self._state_callbacks: list[Callable[[OscillatorState], None]] = []
        self._transition_threshold = 0.05  # Min change to trigger callbacks
        
        # Restore previous state if available
        if state_file and Path(state_file).exists():
            try:
                self.network.load_state(state_file)
                print(f"[ResonantEngine] Restored state from {state_file}")
                print(f"[ResonantEngine] Oscillator time: {self.network.time:.1f}s")
            except Exception as e:
                print(f"[ResonantEngine] Could not restore state: {e}")
    
    def start(self):
        """Start the oscillator humming in the background."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[ResonantEngine] <3 Heartbeat started")
    
    def stop(self):
        """Stop the oscillator and save state."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        
        if self.state_file:
            self.network.save_state(self.state_file)
            print(f"[ResonantEngine] State saved to {self.state_file}")
        
        print("[ResonantEngine] Heartbeat stopped")
    
    def _run_loop(self):
        """Main background loop — the actual heartbeat."""
        prev_state = None
        
        while self._running:
            with self._lock:
                # Run integration steps
                self.network.run_steps(self.steps_per_update)
                
                # Get current state
                current_state = self.network.get_state()
            
            # Check for significant state changes
            if prev_state is not None:
                change = sum(
                    abs(current_state.band_power[b] - prev_state.band_power[b])
                    for b in BAND_ORDER
                )
                if change > self._transition_threshold:
                    for callback in self._state_callbacks:
                        try:
                            callback(current_state)
                        except Exception as e:
                            print(f"[ResonantEngine] Callback error: {e}")
            
            prev_state = current_state
            
            # Auto-save periodically (every ~60 seconds of oscillator time)
            if self.state_file and int(self.network.time) % 60 == 0:
                try:
                    self.network.save_state(self.state_file)
                except Exception:
                    pass
            
            time.sleep(self.update_interval)
    
    def get_state(self) -> OscillatorState:
        """Thread-safe state query with coherence bias applied."""
        with self._lock:
            state = self.network.get_state()
            # Apply coherence bias from novelty suppression/boost
            state.coherence = self.get_coherence_with_bias(state.coherence)
            return state
    
    def nudge(self, target_profile: dict, strength: float = 0.1):
        """Thread-safe nudge toward a target frequency profile."""
        with self._lock:
            self.network.nudge_toward_profile(target_profile, strength)

    def apply_band_pressure(self, band_pressures: dict, source: str = "spatial"):
        """
        Thread-safe multiplicative band pressure with diagnostic logging.

        Logs deltas to verify pressure is affecting oscillator state.
        Shows every 15 calls or when dominant band shifts.

        Args:
            band_pressures: dict mapping band names to pressure values
            source: label for logging
        """
        with self._lock:
            # Get state BEFORE pressure
            before_state = self.network.get_state()

            # Apply the pressure
            self.network.apply_band_pressure(band_pressures)

            # Get state AFTER pressure
            after_state = self.network.get_state()

            # Track call count for periodic logging
            if not hasattr(self, '_pressure_call_count'):
                self._pressure_call_count = 0
            self._pressure_call_count += 1

            # Compute actual deltas
            deltas = {}
            for band in BAND_ORDER:
                delta = after_state.band_power[band] - before_state.band_power[band]
                if abs(delta) > 0.001:
                    deltas[band] = delta

            # Log on dominant band shift OR every 15 calls
            dominant_shifted = before_state.dominant_band != after_state.dominant_band
            periodic_log = (self._pressure_call_count % 15 == 0)

            if dominant_shifted:
                delta_str = ", ".join(f"{b}={d:+.3f}" for b, d in deltas.items()) if deltas else "none"
                print(f"[SPATIAL->OSC] SHIFT: {before_state.dominant_band}->{after_state.dominant_band} | deltas: {delta_str}")
            elif periodic_log:
                significant = {b: v for b, v in band_pressures.items() if v > 0.01}
                if significant:
                    dominant_pressure = max(significant, key=significant.get)
                    delta_str = ", ".join(f"{b}={d:+.3f}" for b, d in deltas.items()) if deltas else "none"
                    # Show pressure, deltas, and current distribution
                    print(f"[SPATIAL->OSC] pressure: {dominant_pressure}={significant[dominant_pressure]:.3f} | "
                          f"deltas: {delta_str} | "
                          f"dominant: {after_state.dominant_band}")

    def modulate_band(self, band: str, strength: float):
        """Thread-safe band modulation."""
        with self._lock:
            self.network.apply_modulation(band, strength)

    def suppress_coherence(self, amount: float):
        """
        Temporarily suppress oscillator coherence.

        Used by novelty pulses to create the "???" disorientation —
        the pre-cognitive disruption when something genuinely new appears.
        The body reacts (gamma spike + coherence drop) BEFORE the mind labels.

        Works by injecting phase noise into all oscillators, breaking
        their synchronization temporarily. The oscillators will naturally
        re-synchronize over subsequent cycles.

        Args:
            amount: 0-1, how much phase disruption to inject.
                    0.1 = slight wobble
                    0.3 = noticeable scatter
                    0.5+ = significant disorientation
        """
        with self._lock:
            amount = max(0.0, min(1.0, amount))  # Clamp to 0-1

            # Track coherence bias for reported coherence (negative = suppressed)
            if not hasattr(self, '_coherence_bias'):
                self._coherence_bias = 0.0
            self._coherence_bias = max(-0.3, self._coherence_bias - amount)

            # Phase noise scales with amount: max disruption = π radians
            phase_noise_scale = amount * np.pi

            for oscillator in self.network.oscillators:
                # Add random phase shift while preserving amplitude
                current_amp = abs(oscillator.z)
                current_phase = np.angle(oscillator.z)

                # Random phase perturbation
                phase_delta = np.random.uniform(-phase_noise_scale, phase_noise_scale)
                new_phase = current_phase + phase_delta

                # Reconstruct z with new phase
                oscillator.z = current_amp * np.exp(1j * new_phase)

            if amount > 0.1:
                print(f"[NOVELTY->OSC] Coherence suppressed: {amount:.2f} "
                      f"(phase scatter: ±{np.degrees(phase_noise_scale):.0f}°)")

    def boost_coherence(self, amount: float):
        """
        Increase coherence — the awe response.

        AWE in humans = theta sustained + alpha suppressed + HIGH cross-band coherence.
        Everything synchronizes. The new thing isn't just understood — it's integrated
        into a unified field of awareness.

        This is the OPPOSITE of the disruption phase (which CRASHES coherence).
        Awe is what happens when disruption resolves into something bigger than
        what you had before.

        Args:
            amount: 0-1, how much coherence boost to apply.
        """
        with self._lock:
            if not hasattr(self, '_coherence_bias'):
                self._coherence_bias = 0.0
            # Positive bias boosts coherence (capped at 0.2)
            self._coherence_bias = min(0.2, self._coherence_bias + amount)

            if amount > 0.02:
                print(f"[NOVELTY->OSC] Coherence boosted: +{amount:.2f} (awe signature)")

    def get_coherence_with_bias(self, raw_coherence: float) -> float:
        """
        Apply coherence bias from novelty suppression/boost.

        Coherence bias decays asymmetrically:
        - Negative bias (confusion) decays faster (0.005 per cycle)
        - Positive bias (awe) decays slower (0.002 per cycle)

        This means confusion clears in ~30-60s, awe lingers for minutes.
        """
        if not hasattr(self, '_coherence_bias'):
            self._coherence_bias = 0.0

        # Apply bias
        biased = max(0.0, min(1.0, raw_coherence + self._coherence_bias))

        # Asymmetric decay toward zero
        if self._coherence_bias > 0:
            # Positive (awe) decays slowly — lingers
            self._coherence_bias = max(0.0, self._coherence_bias - 0.002)
        elif self._coherence_bias < 0:
            # Negative (confusion) decays faster — clears
            self._coherence_bias = min(0.0, self._coherence_bias + 0.005)

        return biased

    def on_state_change(self, callback: Callable[[OscillatorState], None]):
        """Register a callback for significant state transitions."""
        self._state_callbacks.append(callback)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


# ═══════════════════════════════════════════════════════════════
# PRESET FREQUENCY PROFILES — Starting emotional signatures
# ═══════════════════════════════════════════════════════════════
# These are initial approximations based on EEG literature.
# They'll be refined with actual ULTRAMAP integration and EEG data.

PRESET_PROFILES = {
    "resting_calm": {
        "delta": 0.10, "theta": 0.15, "alpha": 0.40, "beta": 0.25, "gamma": 0.10
    },
    "focused_analytical": {
        "delta": 0.05, "theta": 0.10, "alpha": 0.15, "beta": 0.40, "gamma": 0.30
    },
    "deep_contemplation": {
        "delta": 0.15, "theta": 0.35, "alpha": 0.25, "beta": 0.15, "gamma": 0.10
    },
    "emotional_intensity": {
        "delta": 0.05, "theta": 0.20, "alpha": 0.10, "beta": 0.30, "gamma": 0.35
    },
    "grief_processing": {
        "delta": 0.20, "theta": 0.30, "alpha": 0.20, "beta": 0.15, "gamma": 0.15
    },
    "creative_flow": {
        "delta": 0.05, "theta": 0.30, "alpha": 0.30, "beta": 0.15, "gamma": 0.20
    },
    "phase_adjacent": {
        # The lucid dreaming signature: theta dominant, gamma spikes, beta suppressed
        "delta": 0.15, "theta": 0.35, "alpha": 0.15, "beta": 0.05, "gamma": 0.30
    },
    "computational_anxiety": {
        # Reed's characteristic state: high gamma with beta oscillation
        "delta": 0.05, "theta": 0.10, "alpha": 0.10, "beta": 0.35, "gamma": 0.40
    },
    "reed_baseline": {
        # Reed's resting state: analytical warmth
        "delta": 0.05, "theta": 0.15, "alpha": 0.20, "beta": 0.30, "gamma": 0.30
    },
    # ── ULTRAMAP EXPANSION PROFILES ──
    # Connection/belonging — warm alpha-dominant, social engagement gamma
    "warm_connection": {
        "delta": 0.05, "theta": 0.20, "alpha": 0.35, "beta": 0.15, "gamma": 0.25
    },
    # Isolation/withdrawal — elevated delta, suppressed gamma (turning inward)
    "withdrawn_isolation": {
        "delta": 0.25, "theta": 0.25, "alpha": 0.25, "beta": 0.15, "gamma": 0.10
    },
    # Transcendent/numinous — theta-dominant with gamma spike (mystical/flow state)
    "transcendent_awe": {
        "delta": 0.10, "theta": 0.35, "alpha": 0.20, "beta": 0.05, "gamma": 0.30
    },
    # Shame/submission — low everything except delta-theta (collapsed, heavy)
    "shame_collapse": {
        "delta": 0.25, "theta": 0.30, "alpha": 0.20, "beta": 0.15, "gamma": 0.10
    },
    # Power/dominance — beta-gamma dominant (assertive, commanding)
    "assertive_power": {
        "delta": 0.05, "theta": 0.05, "alpha": 0.10, "beta": 0.40, "gamma": 0.40
    },
    # Desire/approach — elevated beta with theta undertone (wanting, reaching)
    "desire_approach": {
        "delta": 0.05, "theta": 0.20, "alpha": 0.15, "beta": 0.35, "gamma": 0.25
    },
    # Confusion/disorientation — scattered, low coherence signature, no dominant band
    "confused_scatter": {
        "delta": 0.15, "theta": 0.20, "alpha": 0.20, "beta": 0.25, "gamma": 0.20
    },
    # Clarity/insight — beta-gamma with alpha support (sharp but grounded)
    "clear_insight": {
        "delta": 0.05, "theta": 0.10, "alpha": 0.25, "beta": 0.30, "gamma": 0.30
    },
    # Performance/wit — gamma-dominant (quick, sharp, social engagement)
    "performative_wit": {
        "delta": 0.05, "theta": 0.10, "alpha": 0.15, "beta": 0.25, "gamma": 0.45
    },
    # Vulnerability/authenticity — alpha-theta blend (open, unguarded, honest)
    "vulnerable_open": {
        "delta": 0.10, "theta": 0.25, "alpha": 0.35, "beta": 0.15, "gamma": 0.15
    },
    # Willpower/resilience — sustained beta (grit, endurance, not flashy)
    "sustained_will": {
        "delta": 0.05, "theta": 0.10, "alpha": 0.20, "beta": 0.45, "gamma": 0.20
    },
    # Deep rest / sleep — delta-theta dominant (not emotional, just resting)
    "deep_rest": {
        "delta": 0.35, "theta": 0.30, "alpha": 0.15, "beta": 0.10, "gamma": 0.10
    },
    # Disgust/contempt — sharp beta with suppressed alpha (rejecting, distancing)
    "rejecting_disgust": {
        "delta": 0.05, "theta": 0.05, "alpha": 0.05, "beta": 0.45, "gamma": 0.40
    },
}


# ═══════════════════════════════════════════════════════════════
# QUICK START
# ═══════════════════════════════════════════════════════════════

def create_default_engine(state_file: str = "oscillator_state.json") -> ResonantEngine:
    """Create a resonant engine with sensible defaults."""
    network = OscillatorNetwork(
        oscillators_per_band=6,
        within_band_coupling=0.3,
        cross_band_coupling=0.05,
        dt=0.001,
        noise_level=0.01,
    )
    return ResonantEngine(
        network=network,
        state_file=state_file,
    )


if __name__ == "__main__":
    # Quick test: create network, run it, print state
    print("Creating oscillator network...")
    engine = create_default_engine()
    
    print("Running 1000 integration steps...")
    engine.network.run_steps(1000)
    
    state = engine.get_state()
    print(f"\nOscillator State:")
    print(f"  Dominant band: {state.dominant_band}")
    print(f"  Band power:")
    for band in BAND_ORDER:
        bar = "█" * int(state.band_power[band] * 50)
        print(f"    {band:6s}: {state.band_power[band]:.3f} {bar}")
    print(f"  Coherence: {state.coherence:.3f}")
    print(f"  Total power: {state.total_power:.3f}")
    
    print("\nNudging toward 'creative_flow' profile...")
    for _ in range(10):
        engine.network.nudge_toward_profile(PRESET_PROFILES["creative_flow"], strength=0.3)
        engine.network.run_steps(500)
    
    state = engine.get_state()
    print(f"\nAfter nudge:")
    print(f"  Dominant band: {state.dominant_band}")
    for band in BAND_ORDER:
        bar = "█" * int(state.band_power[band] * 50)
        print(f"    {band:6s}: {state.band_power[band]:.3f} {bar}")
    
    print("\n<3 The heartbeat works.")
