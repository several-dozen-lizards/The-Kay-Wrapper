import sys, os
sys.path.insert(0, 'D:\\Wrappers')
sys.path.insert(0, 'D:\\Wrappers\\Kay')
os.chdir('D:\\Wrappers\\Kay')
from resonant_core.resonant_integration import ResonantIntegration
from engines.memory_layers import MemoryLayerManager
import time

ml = MemoryLayerManager()
print(f"Working: {len(ml.working_memory)}, Long-term: {len(ml.long_term_memory)}")

r = ResonantIntegration(
    state_dir="memory/resonant",
    enable_audio=False,
    memory_layers=ml,
    interoception_interval=2.0,
)
r.start()
time.sleep(7)

ctx = r.get_context_injection()
print(f"Context: {ctx}")

if r.interoception:
    pm = r.interoception.scanner.get_pressure_map()
    ed = pm["emotional_density"]
    rh = pm["recency_heat"]
    ml_val = pm["memory_load"]
    print(f"Pressure: emotional_density={ed:.3f}, recency={rh:.3f}, load={ml_val:.3f}")
    bands = r.interoception.get_band_pressure()
    band_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(bands.items()))
    print(f"Body bands: {band_str}")
    print(f"Cluster: {r.interoception.scanner.get_dominant_emotion_cluster()}")
    print(f"Felt: {r.interoception.get_felt_state()}")

# Simulate turn: curiosity + frustration (tension builds)
r.feed_response_emotions({
    "primary_emotions": ["curiosity", "frustration", "determination"],
    "intensity": 0.7,
    "valence": 0.2
})
time.sleep(3)
ctx2 = r.get_context_injection()
print(f"After tension: {ctx2}")
print(f"Tension: {r.interoception.tension.get_total_tension():.2f}")

# Simulate resolution: joy + contentment (tension releases)
r.feed_response_emotions({
    "primary_emotions": ["joy", "contentment", "peace"],
    "intensity": 0.6,
    "valence": 0.85
})
time.sleep(2)
ctx3 = r.get_context_injection()
print(f"After relief: {ctx3}")
print(f"Tension after: {r.interoception.tension.get_total_tension():.2f}")

r.stop()
print("FULL CHAIN PASSED")
