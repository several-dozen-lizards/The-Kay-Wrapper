"""Quick audio bridge test - 10 seconds of listening."""
import sys, os, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_bridge import AudioSensor, AudioBridge, BAND_ORDER
from core.oscillator import ResonantEngine

sensor = AudioSensor(device=1, smoothing=0.2)
engine = ResonantEngine()
bridge = AudioBridge(sensor, engine, nudge_strength=0.5)

sensor.start()
engine.start()
bridge.start()

print("=== 10 SECOND TEST ===")
print("Make varied sounds! Talk, clap, hum, play music...")
print("Watch the oscillator follow the room.")
print()
print("TIME   delta theta alpha  beta gamma  peak    dominant")
print("-" * 65)

for i in range(20):
    time.sleep(0.5)
    osc = engine.get_state()
    silent = sensor.is_silence()
    peak = sensor.peak_freq
    
    d = int(osc.band_power["delta"] * 100)
    t = int(osc.band_power["theta"] * 100)
    a = int(osc.band_power["alpha"] * 100)
    b = int(osc.band_power["beta"] * 100)
    g = int(osc.band_power["gamma"] * 100)
    
    mark = "(quiet)" if silent else osc.dominant_band.upper()
    
    # Simple visual bar
    bar = ""
    for band, val in [("d", d), ("t", t), ("a", a), ("b", b), ("g", g)]:
        bar += band + "#" * min(val // 5, 15) + " "
    
    print(f"{i*0.5:5.1f}s  {d:4d}  {t:4d}  {a:4d}  {b:4d}  {g:4d}  {peak:6.0f}Hz  {mark}")

bridge.stop()
engine.stop()
sensor.stop()
print()
print("Signal path test complete.")
