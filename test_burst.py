import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'resonant_core')
from memory_interoception import ThreadTensionTracker

t = ThreadTensionTracker()
# Build up tension
t.deposit({"frustration": 0.8, "anger": 0.6}, weight=0.7)
t.deposit({"anxiety": 0.5}, weight=0.5)
t.deposit({"confusion": 0.4}, weight=0.3)
print(f"Tension: {t.get_total_tension():.2f}")

# Check threshold
should_burst = t.check_burst_threshold(coherence=0.3, burst_tension_min=0.5)
print(f"Should burst (coh=0.3): {should_burst}")

should_burst2 = t.check_burst_threshold(coherence=0.8, burst_tension_min=0.5)
print(f"Should burst (coh=0.8): {should_burst2}")

# Trigger burst
result = t.burst_release(release_fraction=0.5)
print(f"Released: {result['released']:.2f}")
print(f"Pre: {result['pre_tension']:.2f} -> Post: {result['post_tension']:.2f}")
print(f"Quality: {result['felt_quality']}")
print(f"Pulse: {result['oscillator_pulse']}")
print()
print("Burst release: OK")
