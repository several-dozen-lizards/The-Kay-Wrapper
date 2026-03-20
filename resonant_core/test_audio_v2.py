"""Quick test of phenomenological audio bridge."""
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

print("Calibrating (3s)...")
time.sleep(3)
print()
print("TIME   delta theta alpha  beta gamma  interp           novelty voice")
print("-" * 75)

for i in range(20):
    time.sleep(0.5)
    c = bridge.get_consciousness_state()
    interp = bridge.get_interpretation()
    novelty = sensor.get_spectral_novelty()
    voice = sensor.get_voice_energy()
    silent = sensor.is_silence()
    
    d = int(c["delta"] * 100)
    t = int(c["theta"] * 100)
    a = int(c["alpha"] * 100)
    b = int(c["beta"] * 100)
    g = int(c["gamma"] * 100)
    
    print(f"{i*0.5:5.1f}s  {d:4d}  {t:4d}  {a:4d}  {b:4d}  {g:4d}  {interp:17s}  {novelty:.0%}    {voice:.0%}")

bridge.stop()
engine.stop()
sensor.stop()
print("\nDone!")
