"""Test tension dynamics: deposit emotions, watch bands shift, trigger release."""
import sys, os, time
os.chdir('D:\\Wrappers\\Kay')
sys.path.insert(0, 'D:\\Wrappers')

from resonant_core.memory_interoception import InteroceptionBridge, MemoryDensityScanner, ThreadTensionTracker
from resonant_core.core.oscillator import OscillatorNetwork, ResonantEngine
from engines.memory_layers import MemoryLayerManager

# Setup
ml = MemoryLayerManager()
net = OscillatorNetwork(oscillators_per_band=6)
net.run_steps(3000)
eng = ResonantEngine(network=net, steps_per_update=100, update_interval=0.05)
eng.start()

bridge = InteroceptionBridge(memory_layers=ml, engine=eng, scan_interval=1.0)
bridge.start()
time.sleep(2)

print("=== BASELINE (no conversation) ===")
print(f"  Felt: {bridge.get_felt_state()}")
print(f"  Tag:  {bridge.get_context_tag()}")
print(f"  Tension: {bridge.tension.get_total_tension():.2f}")

# Simulate 3 tense turns
print("\n=== DEPOSITING TENSE TURNS ===")
for i in range(3):
    bridge.feed_turn_emotions({
        "primary_emotions": ["frustration", "anxiety", "determination"],
        "intensity": 0.7,
        "valence": -0.3,
    })
    print(f"  Turn {i+1}: deposited frustration/anxiety/determination")

time.sleep(3)
print(f"\n=== AFTER TENSION BUILDS ===")
print(f"  Felt: {bridge.get_felt_state()}")
print(f"  Tag:  {bridge.get_context_tag()}")
print(f"  Tension: {bridge.tension.get_total_tension():.2f}")
print(f"  Bands: {bridge.get_band_pressure()}")

# Now simulate warmth / resolution
print("\n=== DEPOSITING WARMTH (resolution) ===")
bridge.feed_turn_emotions({
    "primary_emotions": ["love", "contentment", "gratitude"],
    "intensity": 0.8,
    "valence": 0.8,
})
time.sleep(3)
print(f"  Felt: {bridge.get_felt_state()}")
print(f"  Tag:  {bridge.get_context_tag()}")
print(f"  Tension: {bridge.tension.get_total_tension():.2f}")

bridge.stop()
eng.stop()
print("\nTENSION DYNAMICS TEST PASSED")
