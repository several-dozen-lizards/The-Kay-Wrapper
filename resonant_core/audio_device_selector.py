"""
Audio Device Selector for Kay's Wrapper
========================================
Finds and validates the best microphone input device.
Prefers USB mic over built-in, avoids virtual devices.

Usage:
    from resonant_core.audio_device_selector import get_best_input_device
    device_index = get_best_input_device()

Run standalone for diagnostics:
    python audio_device_selector.py
"""

import sounddevice as sd
import numpy as np
import json
import os
from pathlib import Path

# Config file path - stored in Kay's config directory
CONFIG_PATH = Path(__file__).parent.parent / "Kay" / "config" / "audio_device.json"

# Known virtual/unwanted device keywords (lowercase)
VIRTUAL_DEVICES = [
    'oculus',
    'steam streaming',
    'virtual',
    'vad wave',
    'stereo mix',      # Loopback, returns garbage
    'line in',         # Not a mic
    'what u hear',     # Loopback
]

# Preferred device keywords (lowercase)
PREFERRED_DEVICES = [
    'usb',
    'w4ds',            # The current USB mic
    'blue',            # Blue Yeti etc
    'rode',            # Rode mics
    'at2020',          # Audio Technica
    'samson',
    'fifine',
]

# Webcam mic keywords (secondary fallback)
WEBCAM_DEVICES = [
    'lkzc',            # The current webcam
    'webcam',
    'logitech',
    'c920',
    'c922',
    'c930',
]


def list_input_devices():
    """List all audio input devices with classification."""
    devices = sd.query_devices()
    inputs = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            name_lower = d['name'].lower()
            is_virtual = any(v in name_lower for v in VIRTUAL_DEVICES)
            is_preferred = any(p in name_lower for p in PREFERRED_DEVICES) and not is_virtual
            is_webcam = any(w in name_lower for w in WEBCAM_DEVICES) and not is_virtual
            inputs.append({
                'index': i,
                'name': d['name'],
                'channels': d['max_input_channels'],
                'sample_rate': int(d['default_samplerate']),
                'is_default': (i == sd.default.device[0]),
                'is_virtual': is_virtual,
                'is_preferred': is_preferred,
                'is_webcam': is_webcam,
            })
    return inputs


def test_device(device_index, duration=0.5):
    """
    Test if a device is actually producing audio signal.
    Returns (has_signal: bool, energy: float)
    """
    try:
        d = sd.query_devices(device_index)
        sr = int(d['default_samplerate'])
        recording = sd.rec(int(duration * sr), samplerate=sr,
                          channels=1, device=device_index, blocking=True)
        energy = float(np.mean(np.abs(recording)))

        # Check for garbage values (some devices return huge numbers)
        if energy > 1000:
            return False, energy  # Garbage data

        # Real mic has some ambient noise even in quiet room
        has_signal = energy > 0.0003
        return has_signal, energy
    except Exception as e:
        return False, 0.0


def get_best_input_device(verbose=True):
    """
    Auto-select best input device.
    Priority: saved config > USB mic > default > webcam > any working device

    Returns: device index (int) or None if no working device found
    """
    # Check saved config first
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text())
            saved_index = config.get('device_index')
            if saved_index is not None:
                # Verify it still exists and works
                try:
                    d = sd.query_devices(saved_index)
                    if d['max_input_channels'] > 0:
                        has_signal, energy = test_device(saved_index)
                        if has_signal:
                            if verbose:
                                print(f"[AudioDevice] Using saved device [{saved_index}]: {d['name']}")
                            return saved_index
                        else:
                            if verbose:
                                print(f"[AudioDevice] Saved device [{saved_index}] has no signal, re-scanning...")
                except Exception:
                    if verbose:
                        print(f"[AudioDevice] Saved device [{saved_index}] no longer valid")
        except Exception:
            pass

    inputs = list_input_devices()

    # Priority 1: Preferred (USB mic) that has signal
    for d in inputs:
        if d['is_preferred'] and not d['is_virtual']:
            has_signal, energy = test_device(d['index'])
            if has_signal:
                if verbose:
                    print(f"[AudioDevice] Selected USB mic [{d['index']}]: {d['name']} (energy={energy:.6f})")
                save_device_config(d['index'], d['name'])
                return d['index']

    # Priority 2: Default input that has signal and isn't virtual
    for d in inputs:
        if d['is_default'] and not d['is_virtual']:
            has_signal, energy = test_device(d['index'])
            if has_signal:
                if verbose:
                    print(f"[AudioDevice] Selected default device [{d['index']}]: {d['name']} (energy={energy:.6f})")
                save_device_config(d['index'], d['name'])
                return d['index']

    # Priority 3: Webcam mic (secondary fallback)
    for d in inputs:
        if d['is_webcam'] and not d['is_virtual']:
            has_signal, energy = test_device(d['index'])
            if has_signal:
                if verbose:
                    print(f"[AudioDevice] Selected webcam mic [{d['index']}]: {d['name']} (energy={energy:.6f})")
                save_device_config(d['index'], d['name'])
                return d['index']

    # Priority 4: Any non-virtual device with signal
    for d in inputs:
        if not d['is_virtual']:
            has_signal, energy = test_device(d['index'])
            if has_signal:
                if verbose:
                    print(f"[AudioDevice] Selected fallback device [{d['index']}]: {d['name']} (energy={energy:.6f})")
                save_device_config(d['index'], d['name'])
                return d['index']

    if verbose:
        print("[AudioDevice] WARNING: No working input device found!")
    return None


def save_device_config(index, name):
    """Save selected device for next startup."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config = {
            'device_index': index,
            'device_name': name,
            'sample_rate': 44100,
            'chunk_size': 2048,
            'responsiveness': 0.3,
        }
        CONFIG_PATH.write_text(json.dumps(config, indent=2))
    except Exception as e:
        print(f"[AudioDevice] Warning: Could not save config: {e}")


def get_device_config():
    """Load saved device config, if any."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return None


if __name__ == '__main__':
    print("=" * 60)
    print("AUDIO DEVICE SCAN")
    print("=" * 60)

    inputs = list_input_devices()

    print("\n=== ALL INPUT DEVICES ===")
    for d in inputs:
        flags = []
        if d['is_preferred']: flags.append('USB-MIC')
        if d['is_webcam']: flags.append('WEBCAM')
        if d['is_virtual']: flags.append('VIRTUAL')
        if d['is_default']: flags.append('DEFAULT')

        has_signal, energy = test_device(d['index'])
        if energy > 1000:
            flags.append('GARBAGE')
        elif has_signal:
            flags.append('SIGNAL')
        else:
            flags.append('SILENT')

        print(f"  [{d['index']:2d}] {d['name']}")
        print(f"       {', '.join(flags)} | {d['channels']}ch @ {d['sample_rate']}Hz | energy={energy:.6f}")

    print("\n" + "=" * 60)
    print("AUTO-SELECTION")
    print("=" * 60)
    selected = get_best_input_device()
    if selected is not None:
        d = sd.query_devices(selected)
        print(f"\n  SELECTED: [{selected}] {d['name']}")
    else:
        print("\n  FAILED: No working device found!")

    print("\n" + "=" * 60)
