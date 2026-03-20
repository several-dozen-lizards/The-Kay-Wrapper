"""
AUDIO BRIDGE v2 - Live Visualization
======================================
Phenomenological mapping: sound -> consciousness state

Usage:
    python audio_live_v2.py              # Default mic
    python audio_live_v2.py --device 1   # Specific device
    python audio_live_v2.py --resp 0.4   # Faster response
"""
import sys, os, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_bridge_v2 import (
    AudioSensor, PhenomenologicalBridge, 
    BAND_ORDER, AUDIO_BAND_NAMES, BAND_LABELS
)
from core.oscillator import ResonantEngine


def main():
    device = None
    if "--device" in sys.argv:
        idx = sys.argv.index("--device")
        device = int(sys.argv[idx + 1])

    responsiveness = 0.3
    if "--resp" in sys.argv:
        idx = sys.argv.index("--resp")
        responsiveness = float(sys.argv[idx + 1])

    sensor = AudioSensor(device=device, smoothing=0.25)
    engine = ResonantEngine()
    bridge = PhenomenologicalBridge(sensor, engine, responsiveness=responsiveness)

    sensor.start()
    engine.start()
    bridge.start()

    print("\n  Calibrating room baseline (3 seconds)...")
    time.sleep(3)
    print("  Ready. Talk, type, clap, go quiet. Watch consciousness shift.\n")

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")

            consciousness = bridge.get_consciousness_state()
            interp = bridge.get_interpretation()
            raw = sensor.get_raw_energy()
            silent = sensor.is_silence()
            novelty = sensor.get_spectral_novelty()
            voice = sensor.get_voice_energy()
            peak = sensor.peak_freq
            sil_dur = bridge._silence_duration

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
                dom = max(consciousness, key=consciousness.get)
                dom_mark = " <--" if band == dom else ""
                label = BAND_LABELS[band]
                print(f"  {label} [{bar}] {pct:3d}%{dom_mark}")

            print()
            print(f"  --> {interp}")
            print()

            # Audio features
            print("  AUDIO FEATURES")
            print("  " + "-" * 44)
            status = "SILENCE" if silent else "LISTENING"
            print(f"  Status:     {status}")
            print(f"  Peak freq:  {peak:.0f} Hz")
            print(f"  Voice:      {voice:.0%}")
            print(f"  Novelty:    {novelty:.0%}")

            total_raw = sum(raw.values())
            if total_raw > 0:
                raw_str = "  ".join(
                    f"{name[:4]}:{raw[name]/total_raw:.0%}"
                    for name in AUDIO_BAND_NAMES
                )
            else:
                raw_str = "(silence)"
            print(f"  Spectrum:   {raw_str}")

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
