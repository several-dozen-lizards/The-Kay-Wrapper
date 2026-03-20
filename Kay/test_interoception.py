"""Integration test: interoception bridge with real memory data."""
import sys, os, time
os.chdir('D:\\Wrappers\\Kay')
sys.path.insert(0, 'D:\\Wrappers')

from resonant_core.resonant_integration import ResonantIntegration, INTEROCEPTION_AVAILABLE
from engines.memory_layers import MemoryLayerManager

print(f"INTEROCEPTION_AVAILABLE: {INTEROCEPTION_AVAILABLE}")

# Load real memory
ml = MemoryLayerManager()
print(f"Memory: {len(ml.working_memory)} working, {len(ml.long_term_memory)} long-term")

# Create resonance with interoception (no audio for this test)
r = ResonantIntegration(
    state_dir="memory/resonant",
    enable_audio=False,
    memory_layers=ml,
    interoception_interval=2.0,  # Fast for testing
)
r.start()

# Let interoception scan a few times
print("\nWaiting 5 seconds for interoception scans...")
time.sleep(5)

# Check context injection
ctx = r.get_context_injection()
print(f"\nContext injection: {ctx}")

# Simulate emotion feedback
fake_emotions = {
    "primary_emotions": ["curiosity", "excitement"],
    "intensity": 0.7,
    "valence": 0.6,
}
r.feed_response_emotions(fake_emotions)

time.sleep(2)
ctx2 = r.get_context_injection()
print(f"After emotion feed: {ctx2}")

# Check interoception state
if r.interoception:
    felt = r.interoception.get_felt_state()
    bands = r.interoception.get_band_pressure()
    tension = r.interoception.tension.get_total_tension()
    print(f"\nFelt state: {felt}")
    print(f"Band pressure: {bands}")
    print(f"Tension: {tension:.2f}")
    print(f"Pressure map: {r.interoception.scanner.get_pressure_map()}")

r.stop()
print("\nINTEGRATION TEST PASSED")
