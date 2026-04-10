"""
AUDIO BRIDGE - Live Visualization
===================================
Run this and make sounds. Watch the oscillator follow.

Usage:
    python audio_live.py              # Default mic
    python audio_live.py --device 1   # Specific device
"""
import sys, os, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_bridge import AudioSensor, AudioBridge, BAND_ORDER
from core.oscillator import ResonantEngine

def main():
    device = None
    if "--device" in sys.argv:
        idx = sys.argv.index("--device")
        device = int(sys.argv[idx + 1])

    sensor = AudioSensor(device=device, smoothing=0.2)
    engine = ResonantEngine()
    bridge = AudioBridge(sensor, engine, nudge_strength=0.5)

    sensor.start()
    engine.start()
    bridge.start()

    print()
    print("  +=========================================+")
    print("  |  AUDIO SENSORY BRIDGE - The First Ear |")
    print("  |  Sound -> Frequency -> Feeling          |")
    print("  |                                         |")
    print("  |  Talk, hum, clap, play music.           |")
    print("  |  Watch the oscillator follow the room.  |")
    print("  |  Ctrl+C to stop.                        |")
    print("  +=========================================+")
    print()

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")

            osc = engine.get_state()
            energy = sensor.get_raw_energy()
            profile = sensor.get_profile()
            silent = sensor.is_silence()
            peak = sensor.peak_freq

            print()
            print("  AUDIO SENSORY BRIDGE -- The First Ear")
            print("  " + "=" * 50)
            print()
            
            # Audio input column
            a_total = sum(energy.values())
            print("  ROOM (audio in)          OSCILLATOR (the entity feels)")
            print("  " + "-" * 22 + "     " + "-" * 22)

            for band in BAND_ORDER:
                # Audio bar
                if a_total > 0:
                    a_pct = energy[band] / a_total
                else:
                    a_pct = 0
                a_n = min(int(a_pct * 40), 18)
                a_bar = "=" * a_n + " " * (18 - a_n)

                # Oscillator bar
                o_pct = osc.band_power.get(band, 0)
                o_n = min(int(o_pct * 30), 18)
                o_bar = "#" * o_n + " " * (18 - o_n)

                dom_mark = " <--" if band == osc.dominant_band else ""

                print(f"  {band:6s} [{a_bar}]  [{o_bar}]{dom_mark}")

            print()
            
            # Status
            status = "SILENCE" if silent else "LISTENING"
            print(f"  Status:    {status}")
            print(f"  Peak freq: {peak:.0f} Hz")
            print(f"  Coherence: {osc.coherence:.3f}")
            print(f"  Dominant:  {osc.dominant_band}")
            
            if profile:
                prof = " ".join(f"{b[0].upper()}:{profile[b]:.0%}" for b in BAND_ORDER)
                print(f"  Audio:     {prof}")
            
            print()
            print("  [Ctrl+C to stop]")

            time.sleep(0.15)

    except KeyboardInterrupt:
        print("\n  Stopping...")
        bridge.stop()
        engine.stop()
        sensor.stop()
        print("  Audio bridge closed.")


if __name__ == "__main__":
    main()
