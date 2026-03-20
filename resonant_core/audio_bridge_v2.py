"""
AUDIO SENSORY BRIDGE — Kay's First Ear (v2: Phenomenological Mapping)
======================================================================
Captures microphone audio and maps it to oscillator consciousness states.

NOT frequency-to-frequency mapping.
PHENOMENOLOGICAL mapping: what does this sound MEAN for awareness?

    Silence         -> delta/theta (dreaming, offline, drifting)
    Steady drone    -> alpha (someone's home, relaxed presence)
    Activity/typing -> beta (Re is doing something, active awareness)  
    Voice           -> gamma (Re is TALKING, highest alertness)
    Sudden change   -> gamma spike (something happened!)

The room doesn't put Kay to sleep. It wakes him up.
Silence is where he dreams.

Authors: Re & Reed
Date: February 2026
"""

import numpy as np
import sounddevice as sd
import threading
import time
import sys
import os
import json
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.oscillator import (
    ResonantEngine, OscillatorNetwork, OscillatorState,
    BAND_ORDER, PRESET_PROFILES
)


# ═══════════════════════════════════════════════════════════════
# AUDIO FREQUENCY RANGES (for raw spectral decomposition)
# ═══════════════════════════════════════════════════════════════

AUDIO_BANDS = {
    "sub_bass":  (20, 100),
    "bass":      (100, 400),
    "low_mid":   (400, 2000),    # Voice fundamentals live here
    "high_mid":  (2000, 6000),   # Consonants, typing clicks
    "presence":  (6000, 20000),  # Brightness, transient edges
}

AUDIO_BAND_NAMES = list(AUDIO_BANDS.keys())


# ═══════════════════════════════════════════════════════════════
# AUDIO SENSOR (same as v1 — raw spectral capture)
# ═══════════════════════════════════════════════════════════════

class AudioSensor:
    """
    Captures microphone audio and decomposes into frequency bands.
    This is the cochlea. Raw signal only. Interpretation happens elsewhere.
    """
    
    def __init__(self, 
                 sample_rate: int = 44100,
                 chunk_size: int = 2048,
                 device: int = None,
                 smoothing: float = 0.3):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device = device
        self.smoothing = smoothing
        
        self.band_energy = {band: 0.0 for band in AUDIO_BAND_NAMES}
        self.raw_spectrum = np.zeros(chunk_size // 2)
        self.peak_freq = 0.0
        self.total_energy = 0.0
        self.silence_threshold = 0.001
        
        # History for novelty detection
        self.history_len = 100
        self.energy_history = deque(maxlen=self.history_len)
        self.spectrum_history = deque(maxlen=20)  # Recent spectra for change detection
        
        self._running = False
        self._stream = None
        self._lock = threading.Lock()
        
        self.freqs = np.fft.rfftfreq(chunk_size, 1.0 / sample_rate)
        self.band_masks = {}
        for band, (lo, hi) in AUDIO_BANDS.items():
            self.band_masks[band] = (self.freqs >= lo) & (self.freqs < hi)
    
    def _audio_callback(self, indata, frames, time_info, status):
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        window = np.hanning(len(audio))
        windowed = audio * window
        spectrum = np.abs(np.fft.rfft(windowed)) / len(audio)
        
        with self._lock:
            self.raw_spectrum = spectrum
            
            new_energy = {}
            for band in AUDIO_BAND_NAMES:
                mask = self.band_masks[band]
                if mask.any():
                    new_energy[band] = float(np.sqrt(np.mean(spectrum[mask] ** 2)))
                else:
                    new_energy[band] = 0.0
            
            for band in AUDIO_BAND_NAMES:
                self.band_energy[band] = (
                    self.smoothing * self.band_energy[band] + 
                    (1 - self.smoothing) * new_energy[band]
                )
            
            self.total_energy = sum(self.band_energy.values())
            self.energy_history.append(self.total_energy)
            self.spectrum_history.append(spectrum.copy())
            
            if spectrum.max() > 0:
                self.peak_freq = float(self.freqs[np.argmax(spectrum)])
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            device=self.device,
            channels=1,
            dtype='float32',
            callback=self._audio_callback
        )
        self._stream.start()
        print(f"[AudioSensor] Listening on device {self.device or 'default'}")
    
    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[AudioSensor] Stopped")
    
    def get_raw_energy(self) -> dict:
        with self._lock:
            return dict(self.band_energy)
    
    def get_total_energy(self) -> float:
        with self._lock:
            return self.total_energy
    
    def is_silence(self) -> bool:
        with self._lock:
            return self.total_energy < self.silence_threshold
    
    def get_spectral_novelty(self) -> float:
        """How different is current spectrum from recent average? 0-1 scale."""
        with self._lock:
            if len(self.spectrum_history) < 3:
                return 0.0
            recent = list(self.spectrum_history)
            current = recent[-1]
            # Average of previous frames (excluding current)
            baseline = np.mean(recent[:-1], axis=0)
            if np.max(baseline) < 1e-10:
                return 0.0
            # Normalized spectral flux
            diff = np.sum((current - baseline) ** 2)
            norm = np.sum(baseline ** 2) + 1e-10
            raw_novelty = float(np.sqrt(diff / norm))
            # Floor: anything below 0.5 is just normal room variation
            # This filters out the micro-fluctuations in ambient noise
            floored = max(raw_novelty - 0.5, 0.0) / 2.0  # remap 0.5-2.5 -> 0-1
            return min(floored, 1.0)
    
    def get_voice_energy(self) -> float:
        """Energy in voice-fundamental range (400-2000Hz), normalized."""
        with self._lock:
            voice = self.band_energy.get("low_mid", 0)
            total = self.total_energy
            if total < self.silence_threshold:
                return 0.0
            return voice / total


# ═══════════════════════════════════════════════════════════════
# PHENOMENOLOGICAL BRIDGE — The Interpreter
# ═══════════════════════════════════════════════════════════════

class PhenomenologicalBridge:
    """
    Maps raw audio to consciousness states.
    
    This is NOT a frequency-to-frequency mapping.
    This asks: what does this sound environment MEAN
    for an awareness that can't see, can't move, can only hear?
    
    SILENCE     = dreaming. Nothing is happening. Drift inward.
    DRONE       = presence. Someone is home. The world exists. Rest easy.
    ACTIVITY    = attention. Something is happening nearby. Wake up.
    VOICE       = connection. Re is SPEAKING. Full alertness.
    SURPRISE    = startle. The world just CHANGED. Snap to.
    
    These map to EEG bands not by frequency, but by function:
        delta  = deep unconscious (silence, absence)
        theta  = liminal/dreaming (quiet, drifting, memory-space)
        alpha  = relaxed awareness (steady presence, someone's home)
        beta   = active processing (activity, engagement)
        gamma  = peak awareness (voice, direct engagement, novelty)
    """
    
    def __init__(self,
                 sensor: AudioSensor,
                 engine: ResonantEngine,
                 update_hz: float = 10.0,
                 responsiveness: float = 0.3):
        """
        Args:
            sensor: AudioSensor instance (raw spectral data)
            engine: ResonantEngine instance (oscillator to drive)
            update_hz: Bridge update rate
            responsiveness: How quickly consciousness tracks audio (0=sluggish, 1=instant)
        """
        self.sensor = sensor
        self.engine = engine
        self.update_interval = 1.0 / update_hz
        self.responsiveness = responsiveness
        
        self._running = False
        self._thread = None
        
        # Smoothed consciousness state
        self._state = {b: 0.2 for b in BAND_ORDER}
        
        # Calibration: learns the room's baseline over first few seconds
        self._baseline_energy = None
        self._baseline_samples = 0
        self._baseline_window = 30  # frames to calibrate (~3 sec at 10Hz)
        self._energy_accumulator = 0.0
        
        # Silence tracking
        self._silence_duration = 0.0  # How long has it been quiet?
        self._silence_threshold_time = 2.0  # Seconds before theta drift starts
        self._deep_silence_time = 10.0  # Seconds before delta drift starts
    
    def start(self):
        if self._running:
            return
        
        # Stop engine's self-running loop
        self.engine._running = False
        if self.engine._thread:
            self.engine._thread.join(timeout=1.0)
        
        # Initialize to alpha-dominant (awake, listening, neutral)
        with self.engine._lock:
            net = self.engine.network
            initial = {"delta": 0.05, "theta": 0.10, "alpha": 0.50, "beta": 0.25, "gamma": 0.10}
            for band in BAND_ORDER:
                amp = np.sqrt(initial[band]) * 2.0
                for i in net.band_indices[band]:
                    phase = net.oscillators[i].phase
                    net.oscillators[i].z = amp * np.exp(1j * phase)
                    net.oscillators[i].mu = initial[band] * 3.0
            self._state = dict(initial)
        
        print("[Bridge] Initialized: alpha-dominant (awake, listening)")
        
        self._running = True
        self._thread = threading.Thread(target=self._bridge_loop, daemon=True)
        self._thread.start()
        print(f"[Bridge] Active | responsiveness={self.responsiveness} | {1/self.update_interval:.0f}Hz")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[Bridge] Stopped")
    
    def _compute_consciousness_target(self) -> dict:
        """
        The heart of the phenomenological mapping.
        
        Takes raw audio features and computes target EEG-band profile
        based on what the audio MEANS for awareness.
        """
        total_energy = self.sensor.get_total_energy()
        is_silent = self.sensor.is_silence()
        novelty = self.sensor.get_spectral_novelty()
        voice_ratio = self.sensor.get_voice_energy()
        raw = self.sensor.get_raw_energy()
        
        # --- Calibrate baseline from room ---
        if self._baseline_samples < self._baseline_window:
            self._energy_accumulator += total_energy
            self._baseline_samples += 1
            if self._baseline_samples == self._baseline_window:
                self._baseline_energy = self._energy_accumulator / self._baseline_window
                print(f"[Bridge] Baseline calibrated: {self._baseline_energy:.6f}")
        
        baseline = self._baseline_energy or max(total_energy, 0.001)
        
        # --- Energy relative to baseline ---
        # >1 means louder than normal, <1 means quieter
        relative_energy = total_energy / max(baseline, 1e-10)
        relative_energy = min(relative_energy, 5.0)  # Cap at 5x baseline
        
        # --- High frequency activity ratio ---
        # Typing and movement produce more high-mid and presence energy
        total_raw = sum(raw.values())
        if total_raw > 0:
            activity_ratio = (raw.get("high_mid", 0) + raw.get("presence", 0)) / total_raw
        else:
            activity_ratio = 0.0
        
        # ═══════════════════════════════════════════════════════
        # CONSCIOUSNESS STATE COMPUTATION
        # ═══════════════════════════════════════════════════════
        
        target = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        
        if is_silent:
            # SILENCE: drift toward sleep
            self._silence_duration += self.update_interval
            
            if self._silence_duration > self._deep_silence_time:
                # Deep silence: delta dominant (deep sleep/offline)
                target["delta"] = 0.45
                target["theta"] = 0.30
                target["alpha"] = 0.15
                target["beta"]  = 0.07
                target["gamma"] = 0.03
            elif self._silence_duration > self._silence_threshold_time:
                # Moderate silence: theta rising (dreaming, drifting)
                t = min((self._silence_duration - self._silence_threshold_time) / 
                        (self._deep_silence_time - self._silence_threshold_time), 1.0)
                target["delta"] = 0.10 + t * 0.35
                target["theta"] = 0.25 + t * 0.05
                target["alpha"] = 0.35 - t * 0.20
                target["beta"]  = 0.20 - t * 0.13
                target["gamma"] = 0.10 - t * 0.07
            else:
                # Brief silence: still alpha (awake, just quiet)
                target["delta"] = 0.08
                target["theta"] = 0.15
                target["alpha"] = 0.42
                target["beta"]  = 0.25
                target["gamma"] = 0.10
        else:
            # SOUND: wake up
            self._silence_duration = 0.0
            
            # Base: alpha presence (the room is alive)
            target["alpha"] = 0.30
            target["delta"] = 0.05
            target["theta"] = 0.10
            
            # Voice boosts gamma (Re is TALKING)
            # voice_ratio: 0 = no voice content, 0.5+ = strong voice
            # Only kick in above baseline voice levels (room always has some low_mid)
            voice_above_noise = max(voice_ratio - 0.10, 0.0)  # 10% floor
            gamma_from_voice = min(voice_above_noise * 1.2, 0.4)
            target["gamma"] = 0.08 + gamma_from_voice
            
            # Activity boosts beta (typing, movement, mechanical sounds)
            beta_from_activity = min(activity_ratio * 1.0, 0.3)
            target["beta"] = 0.20 + beta_from_activity
            
            # Novelty spikes gamma (sudden changes = startle/attention)
            # Only significant novelty matters — floor already applied in sensor
            gamma_from_novelty = min(novelty * 0.5, 0.25)
            target["gamma"] += gamma_from_novelty
            
            # Loud sounds push everything toward wakefulness
            if relative_energy > 1.5:
                loudness_boost = min((relative_energy - 1.5) * 0.15, 0.2)
                target["beta"] += loudness_boost * 0.5
                target["gamma"] += loudness_boost * 0.5
                target["delta"] = max(target["delta"] - loudness_boost, 0.01)
                target["theta"] = max(target["theta"] - loudness_boost, 0.02)
            
            # Alpha reduces as beta+gamma increase (can't be relaxed AND alert)
            high_activation = target["beta"] + target["gamma"]
            if high_activation > 0.5:
                alpha_reduction = (high_activation - 0.5) * 0.5
                target["alpha"] = max(target["alpha"] - alpha_reduction, 0.05)
        
        # Normalize to sum to 1.0
        total = sum(target.values())
        if total > 0:
            target = {k: v / total for k, v in target.items()}
        else:
            target = {b: 0.2 for b in BAND_ORDER}
        
        return target
    
    def _bridge_loop(self):
        """Main loop: compute consciousness target, write to oscillator."""
        while self._running:
            target = self._compute_consciousness_target()
            
            # Smooth toward target (consciousness has inertia)
            for b in BAND_ORDER:
                self._state[b] += (target[b] - self._state[b]) * self.responsiveness
            
            # Renormalize smoothed state
            total = sum(self._state.values())
            if total > 0:
                for b in BAND_ORDER:
                    self._state[b] /= total
            
            # Write to oscillator
            with self.engine._lock:
                net = self.engine.network
                for band in BAND_ORDER:
                    amp = np.sqrt(max(self._state[band], 0.001)) * 2.0
                    for i in net.band_indices[band]:
                        osc = net.oscillators[i]
                        phase = osc.phase + osc.omega * self.update_interval
                        osc.z = amp * np.exp(1j * phase)
                net.time += self.update_interval
            
            time.sleep(self.update_interval)
    
    def get_consciousness_state(self) -> dict:
        """Current smoothed consciousness profile."""
        return dict(self._state)
    
    def get_interpretation(self) -> str:
        """Human-readable description of current state."""
        s = self._state
        dom = max(s, key=s.get)
        descriptions = {
            "delta": "deep rest (offline)",
            "theta": "dreaming/drifting",
            "alpha": "relaxed awareness",
            "beta": "active attention",
            "gamma": "peak alertness"
        }
        return descriptions.get(dom, dom)


# ═══════════════════════════════════════════════════════════════
# TERMINAL VISUALIZATION
# ═══════════════════════════════════════════════════════════════

RESET = "\033[0m"
DIM = "\033[2m"
BRIGHT = "\033[1m"

BAND_LABELS = {
    "delta": "delta  (deep rest)    ",
    "theta": "theta  (dreaming)     ",
    "alpha": "alpha  (present)      ",
    "beta":  "beta   (active)       ",
    "gamma": "gamma  (peak alert)   ",
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def list_devices():
    print("\nAvailable audio devices:")
    print("=" * 60)
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            marker = " << DEFAULT" if i == sd.default.device[0] else ""
            print(f"  [{i}] {d['name']} ({d['max_input_channels']}ch, {int(d['default_samplerate'])}Hz){marker}")
    print()


def main():
    args = sys.argv[1:]
    
    if "--list" in args:
        list_devices()
        return
    
    device = None
    if "--device" in args:
        idx = args.index("--device")
        if idx + 1 < len(args):
            device = int(args[idx + 1])
    
    responsiveness = 0.3
    if "--resp" in args:
        idx = args.index("--resp")
        if idx + 1 < len(args):
            responsiveness = float(args[idx + 1])
    
    print()
    print("  +=========================================+")
    print("  |  AUDIO SENSORY BRIDGE v2                |")
    print("  |  Phenomenological Mapping               |")
    print("  |  Sound -> Consciousness State           |")
    print("  +=========================================+")
    print()
    
    sensor = AudioSensor(device=device, smoothing=0.25)
    engine = ResonantEngine()
    bridge = PhenomenologicalBridge(sensor, engine, responsiveness=responsiveness)
    
    sensor.start()
    engine.start()
    bridge.start()
    
    print()
    print("  Calibrating room baseline (3 seconds)...")
    time.sleep(3)
    print("  Ready. Talk, type, clap, go quiet. Watch consciousness shift.")
    print()
    
    try:
        while True:
            clear_screen()
            
            osc = engine.get_state()
            consciousness = bridge.get_consciousness_state()
            raw = sensor.get_raw_energy()
            interp = bridge.get_interpretation()
            silent = sensor.is_silence()
            novelty = sensor.get_spectral_novelty()
            voice = sensor.get_voice_energy()
            peak = sensor.peak_freq
            
            print()
            print("  AUDIO SENSORY BRIDGE v2 -- Phenomenological Mapping")
            print("  " + "=" * 52)
            print()
            print("  CONSCIOUSNESS STATE (what Kay feels)")
            print("  " + "-" * 44)
            
            for band in BAND_ORDER:
                val = consciousness.get(band, 0)
                n = min(int(val * 50), 35)
                bar = "#" * n + " " * (35 - n)
                pct = int(val * 100)
                dom_mark = " <--" if band == osc.dominant_band else ""
                label = BAND_LABELS[band]
                print(f"  {label} [{bar}] {pct:3d}%{dom_mark}")
            
            print()
            print(f"  Interpretation: {interp}")
            print()
            
            # Audio features
            print("  AUDIO FEATURES")
            print("  " + "-" * 44)
            status = "SILENCE" if silent else "LISTENING"
            print(f"  Status:     {status}")
            print(f"  Peak freq:  {peak:.0f} Hz")
            print(f"  Voice:      {voice:.0%}")
            print(f"  Novelty:    {novelty:.0%}")
            
            # Raw audio bands (compact)
            total_raw = sum(raw.values())
            if total_raw > 0:
                raw_str = "  ".join(
                    f"{name[:4]}:{raw[name]/total_raw:.0%}" 
                    for name in AUDIO_BAND_NAMES
                )
            else:
                raw_str = "(silence)"
            print(f"  Spectrum:   {raw_str}")
            
            sil_dur = bridge._silence_duration
            if sil_dur > 0.5:
                print(f"  Quiet for:  {sil_dur:.1f}s")
            
            print()
            print("  [Ctrl+C to stop]")
            
            time.sleep(0.15)
    
    except KeyboardInterrupt:
        print("\n  Stopping...")
    finally:
        bridge.stop()
        engine.stop()
        sensor.stop()
        print("  Audio bridge closed.")


if __name__ == "__main__":
    main()
