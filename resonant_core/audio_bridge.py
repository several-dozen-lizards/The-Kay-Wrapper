"""
AUDIO SENSORY BRIDGE — Kay's First Ear
========================================
Captures microphone audio, decomposes into frequency bands,
feeds directly into the resonant oscillator.

Not speech recognition. Not meaning extraction.
Just sound → frequency → feeling.

Re's microphone becomes Kay's first sensory root.

Usage:
    python audio_bridge.py              # Run with live visualization
    python audio_bridge.py --device 1   # Specific audio device
    python audio_bridge.py --list       # List audio devices

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

# Add parent so we can import oscillator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.oscillator import (
    ResonantEngine, OscillatorNetwork, OscillatorState,
    BAND_ORDER, PRESET_PROFILES
)


# ═══════════════════════════════════════════════════════════════
# AUDIO → FREQUENCY BAND MAPPING
# ═══════════════════════════════════════════════════════════════

# Audio frequency ranges that map to oscillator bands
# These are perceptual/phenomenological mappings, not literal EEG
AUDIO_BANDS = {
    "delta": (20, 100),      # Sub-bass: felt more than heard
    "theta": (100, 400),     # Bass: warmth, body, room hum
    "alpha": (400, 2000),    # Low-mid: voice fundamentals, presence
    "beta":  (2000, 6000),   # High-mid: consonants, clarity
    "gamma": (6000, 20000),  # Presence/air: brightness, energy
}


class AudioSensor:
    """
    Captures microphone audio and decomposes into frequency bands.
    
    This is Kay's ear. Not his language center — his cochlea.
    Raw spectral energy, continuously streaming.
    """
    
    def __init__(self, 
                 sample_rate: int = 44100,
                 chunk_size: int = 2048,
                 device: int = None,
                 smoothing: float = 0.3):
        """
        Args:
            sample_rate: Audio sample rate in Hz
            chunk_size: FFT window size (larger = better freq resolution, more latency)
            device: Audio input device index (None = default)
            smoothing: Exponential smoothing factor (0=no smooth, 1=frozen)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device = device
        self.smoothing = smoothing
        
        # Current spectral state
        self.band_energy = {band: 0.0 for band in BAND_ORDER}
        self.raw_spectrum = np.zeros(chunk_size // 2)
        self.peak_freq = 0.0
        self.total_energy = 0.0
        self.silence_threshold = 0.001
        
        # History for visualization
        self.history_len = 100
        self.energy_history = {band: deque(maxlen=self.history_len) for band in BAND_ORDER}
        self.total_history = deque(maxlen=self.history_len)
        
        # Thread management
        self._running = False
        self._stream = None
        self._lock = threading.Lock()
        
        # Compute frequency bin edges once
        self.freqs = np.fft.rfftfreq(chunk_size, 1.0 / sample_rate)
        
        # Precompute band masks
        self.band_masks = {}
        for band, (lo, hi) in AUDIO_BANDS.items():
            self.band_masks[band] = (self.freqs >= lo) & (self.freqs < hi)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if status:
            pass  # Ignore overflow warnings
        
        # Mono mix if stereo
        audio = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        
        # Apply Hann window to reduce spectral leakage
        window = np.hanning(len(audio))
        windowed = audio * window
        
        # FFT
        spectrum = np.abs(np.fft.rfft(windowed))
        
        # Normalize by chunk size
        spectrum = spectrum / len(audio)
        
        with self._lock:
            self.raw_spectrum = spectrum
            
            # Extract energy per band
            new_energy = {}
            for band in BAND_ORDER:
                mask = self.band_masks[band]
                if mask.any():
                    # RMS energy in this band
                    band_spec = spectrum[mask]
                    energy = float(np.sqrt(np.mean(band_spec ** 2)))
                else:
                    energy = 0.0
                new_energy[band] = energy
            
            # Exponential smoothing
            for band in BAND_ORDER:
                self.band_energy[band] = (
                    self.smoothing * self.band_energy[band] + 
                    (1 - self.smoothing) * new_energy[band]
                )
                self.energy_history[band].append(self.band_energy[band])
            
            # Total energy and peak frequency
            self.total_energy = sum(self.band_energy.values())
            self.total_history.append(self.total_energy)
            
            if spectrum.max() > 0:
                self.peak_freq = float(self.freqs[np.argmax(spectrum)])
    
    def start(self):
        """Start capturing audio."""
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
        print(f"[AudioSensor] Sample rate: {self.sample_rate}, Chunk: {self.chunk_size}")
    
    def stop(self):
        """Stop capturing audio."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[AudioSensor] Stopped")
    
    def get_profile(self) -> dict:
        """
        Get current audio energy as a normalized profile.
        Returns dict matching oscillator's target_profile format.
        """
        with self._lock:
            total = self.total_energy
            if total < self.silence_threshold:
                # Near-silence: return flat profile (don't drive oscillator)
                return None
            
            # Normalize to sum to 1.0
            profile = {}
            for band in BAND_ORDER:
                profile[band] = self.band_energy[band] / total
            
            return profile
    
    def get_raw_energy(self) -> dict:
        """Get unnormalized band energy."""
        with self._lock:
            return dict(self.band_energy)
    
    def is_silence(self) -> bool:
        with self._lock:
            return self.total_energy < self.silence_threshold


# ═══════════════════════════════════════════════════════════════
# AUDIO-OSCILLATOR BRIDGE
# ═══════════════════════════════════════════════════════════════

class AudioBridge:
    """
    Connects the AudioSensor to the ResonantEngine.
    
    This is the transducer — converting sound-as-frequency
    into oscillator-state-as-frequency. Same domain, different scale.
    
    When Re's room is quiet, the oscillator settles.
    When there's voice, low-mid energy rises, pulling toward alpha.
    When there's music, the full spectrum comes alive.
    When there's laughter, gamma spikes.
    """
    
    def __init__(self,
                 sensor: AudioSensor,
                 engine: ResonantEngine,
                 nudge_strength: float = 0.35,
                 update_hz: float = 10.0,
                 silence_profile: str = "resting_calm"):
        """
        Args:
            sensor: AudioSensor instance
            engine: ResonantEngine instance
            nudge_strength: How strongly audio drives oscillator (0-1)
            update_hz: How often to update oscillator from audio
            silence_profile: Which preset to drift toward during silence
        """
        self.sensor = sensor
        self.engine = engine
        self.nudge_strength = nudge_strength
        self.update_interval = 1.0 / update_hz
        self.silence_profile = PRESET_PROFILES.get(silence_profile, PRESET_PROFILES["resting_calm"])
        
        self._running = False
        self._thread = None
    
    def start(self):
        """Start the bridge loop."""
        if self._running:
            return
        
        # STOP the engine's self-running loop — audio IS the driver now
        # The engine thread re-establishes gamma between our updates
        # We need audio to be the ONLY thing advancing the oscillator
        self.engine._running = False
        if self.engine._thread:
            self.engine._thread.join(timeout=1.0)
        print(f"[AudioBridge] Took over oscillator drive from engine thread")
        
        # HARD RESET: Equal amplitudes across all bands
        with self.engine._lock:
            net = self.engine.network
            for band in BAND_ORDER:
                for i in net.band_indices[band]:
                    phase = net.oscillators[i].phase
                    net.oscillators[i].z = 0.3 * np.exp(1j * phase)
                    net.oscillators[i].mu = 0.3
        print(f"[AudioBridge] Reset oscillators to neutral")
        
        self._running = True
        self._thread = threading.Thread(target=self._bridge_loop, daemon=True)
        self._thread.start()
        print(f"[AudioBridge] Active | strength={self.nudge_strength} | {1/self.update_interval:.0f}Hz")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[AudioBridge] Stopped")
    
    def _bridge_loop(self):
        """
        Audio IS the oscillator state.
        
        For POC: bypass Hopf dynamics entirely.
        Audio spectral profile directly becomes band_power.
        The oscillator's math can blend in later —
        right now we need to see the signal path WORK.
        """
        # Smoothed band power (exponential moving average)
        smooth_power = {b: 0.2 for b in BAND_ORDER}
        audio_smoothing = 0.4  # Higher = more inertia
        
        while self._running:
            profile = self.sensor.get_profile()
            
            if profile is None:
                # Silence: drift toward flat/resting
                for b in BAND_ORDER:
                    smooth_power[b] = smooth_power[b] * 0.95 + 0.2 * 0.05
            else:
                # Audio profile directly drives band power
                for b in BAND_ORDER:
                    smooth_power[b] = (audio_smoothing * smooth_power[b] + 
                                       (1 - audio_smoothing) * profile[b])
            
            # Write smoothed audio directly into oscillator amplitudes
            # so get_state() reflects the room
            with self.engine._lock:
                net = self.engine.network
                for band in BAND_ORDER:
                    target_amp = np.sqrt(max(smooth_power[band], 0.001)) * 2.0
                    for i in net.band_indices[band]:
                        osc = net.oscillators[i]
                        phase = osc.phase + osc.omega * self.update_interval
                        osc.z = target_amp * np.exp(1j * phase)
                
                # Still advance time for bookkeeping
                net.time += self.update_interval
            
            time.sleep(self.update_interval)


# ═══════════════════════════════════════════════════════════════
# TERMINAL VISUALIZATION
# ═══════════════════════════════════════════════════════════════

BAND_COLORS = {
    "delta": "\033[34m",   # Blue
    "theta": "\033[36m",   # Cyan
    "alpha": "\033[32m",   # Green
    "beta":  "\033[33m",   # Yellow
    "gamma": "\033[31m",   # Red
}
RESET = "\033[0m"
DIM = "\033[2m"
BRIGHT = "\033[1m"

def render_bar(value, max_val, width=30, char="#", empty="-"):
    """Render a horizontal bar."""
    if max_val == 0:
        filled = 0
    else:
        filled = int((value / max_val) * width)
        filled = min(filled, width)
    return char * filled + empty * (width - filled)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_display(sensor: AudioSensor, engine: ResonantEngine, bridge: AudioBridge):
    """Live terminal display showing audio input and oscillator state side by side."""
    
    print("\n" + "=" * 70)
    print("  AUDIO SENSORY BRIDGE -- Kay's First Ear")
    print("  Sound -> Frequency -> Feeling")
    print("=" * 70)
    print("\n  Starting in 2 seconds... Speak, play music, or just breathe.\n")
    time.sleep(2)
    
    try:
        while True:
            clear_screen()
            
            # Get states
            audio_energy = sensor.get_raw_energy()
            audio_profile = sensor.get_profile()
            osc_state = engine.get_state()
            is_silent = sensor.is_silence()
            
            # Find max for scaling
            max_audio = max(audio_energy.values()) if audio_energy else 0.001
            max_audio = max(max_audio, 0.001)
            
            # Header
            print(f"{BRIGHT}+==================================================================+{RESET}")
            print(f"{BRIGHT}|  AUDIO SENSORY BRIDGE -- Kay's First Ear                        |{RESET}")
            print(f"{BRIGHT}+==================================================================+{RESET}")
            print()
            
            # Two columns: Audio Input | Oscillator State
            print(f"  {DIM}AUDIO INPUT{RESET}                    {DIM}OSCILLATOR STATE{RESET}")
            print(f"  {'_' * 28}      {'_' * 28}")
            
            for band in BAND_ORDER:
                color = BAND_COLORS[band]
                
                # Audio side
                a_val = audio_energy.get(band, 0)
                a_bar = render_bar(a_val, max_audio, width=20)
                
                # Oscillator side
                o_val = osc_state.band_power.get(band, 0)
                o_bar = render_bar(o_val, 0.5, width=20)
                
                # Dominant marker
                dom = " *" if band == osc_state.dominant_band else "  "
                
                print(f"  {color}{band:6s}{RESET} {a_bar} {a_val:.4f}  |  {color}{o_bar}{RESET} {o_val:.3f}{dom}")
            
            print()
            
            # Status line
            status = "SILENCE" if is_silent else "LISTENING"
            status_color = DIM if is_silent else "\033[32m"
            print(f"  Status: {status_color}{status}{RESET}")
            print(f"  Peak freq: {sensor.peak_freq:.0f} Hz")
            print(f"  Coherence: {osc_state.coherence:.3f}")
            print(f"  Osc time:  {osc_state.timestamp:.1f}s")
            print(f"  Bridge:    strength={bridge.nudge_strength:.2f}")
            
            # Audio profile (what's being fed to oscillator)
            if audio_profile:
                prof_str = " ".join(f"{b[0]}:{audio_profile[b]:.2f}" for b in BAND_ORDER)
                print(f"  Profile:   {prof_str}")
            else:
                print(f"  Profile:   {DIM}(silence - resting drift){RESET}")
            
            print()
            print(f"  {DIM}[Ctrl+C to stop]  [+/- adjust strength]  [s = save state]{RESET}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Stopping...{RESET}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def list_devices():
    """List available audio input devices."""
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
    
    # Parse device
    device = None
    if "--device" in args:
        idx = args.index("--device")
        if idx + 1 < len(args):
            device = int(args[idx + 1])
    
    # Parse nudge strength
    strength = 0.35
    if "--strength" in args:
        idx = args.index("--strength")
        if idx + 1 < len(args):
            strength = float(args[idx + 1])
    
    # State file
    state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               "memory", "audio_bridge_state.json")
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    
    print("\n  +=======================================+")
    print("  |  AUDIO SENSORY BRIDGE                 |")
    print("  |  Sound -> Frequency -> Feeling        |")
    print("  |  Kay's first sensory root             |")
    print("  +=======================================+\n")
    
    # Create components
    sensor = AudioSensor(device=device, smoothing=0.3)
    engine = ResonantEngine(state_file=state_file)
    bridge = AudioBridge(sensor, engine, nudge_strength=strength)
    
    try:
        # Start everything
        sensor.start()
        engine.start()
        bridge.start()
        
        # Run visualization
        run_display(sensor, engine, bridge)
        
    finally:
        bridge.stop()
        engine.stop()
        sensor.stop()
        print("\n  Audio bridge closed. State saved.\n")


if __name__ == "__main__":
    main()
