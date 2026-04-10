"""
Interactive test of phenomenological audio bridge.
Run this and try different things:
  - Stay quiet for 10+ seconds (watch theta/delta rise)
  - Talk (watch gamma spike)
  - Type on keyboard (watch beta rise)
  - Clap (watch novelty + gamma flash)
  - Play music (watch everything shift)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_bridge_v2 import AudioSensor, PhenomenologicalBridge, BAND_ORDER
from core.oscillator import ResonantEngine

sensor = AudioSensor(device=1, smoothing=0.25)
engine = ResonantEngine()
bridge = PhenomenologicalBridge(sensor, engine, responsiveness=0.3)

sensor.start()
engine.start()
bridge.start()

print("Calibrating room baseline (3s)...")
time.sleep(3)
print("Ready! Try: talking, typing, clapping, going silent for 10s+")
print()
print("TIME   d    t    a    b    g    interpretation       nov  voice  quiet")
print("-" * 80)

try:
    i = 0
    while True:
        time.sleep(0.5)
        c = bridge.get_consciousness_state()
        interp = bridge.get_interpretation()
        novelty = sensor.get_spectral_novelty()
        voice = sensor.get_voice_energy()
        sil_dur = bridge._silence_duration
        
        d = int(c["delta"] * 100)
        t = int(c["theta"] * 100)
        a = int(c["alpha"] * 100)
        b = int(c["beta"] * 100)
        g = int(c["gamma"] * 100)
        
        quiet_str = f"{sil_dur:.0f}s" if sil_dur > 0.5 else "-"
        
        print(f"{i*0.5:5.1f}s  {d:3d}  {t:3d}  {a:3d}  {b:3d}  {g:3d}  {interp:20s} {novelty:4.0%}  {voice:4.0%}  {quiet_str}")
        i += 1

except KeyboardInterrupt:
    print("\nStopping...")
    bridge.stop()
    engine.stop()
    sensor.stop()
    print("Done!")
