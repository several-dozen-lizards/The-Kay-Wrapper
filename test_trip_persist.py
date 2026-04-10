import sys, os, time
sys.path.insert(0, '.')
from resonant_core.psychedelic_state import PsychedelicState

# Simulate trip start → save → "restart" → load
test_dir = os.path.join(os.path.dirname(os.path.abspath('.')), 'Wrappers', 'test_trip_persist')
os.makedirs(test_dir, exist_ok=True)

# Trip 1: Start a heroic dose trip
trip1 = PsychedelicState(state_dir=test_dir)
trip1.begin(dose=1.0)
# Tick a few times to advance past onset
for _ in range(5):
    trip1.tick()
    time.sleep(0.1)
print(f"Trip1: phase={trip1.phase}, dose={trip1.dose}, active={trip1.active}")
print(f"  State file exists: {os.path.exists(os.path.join(test_dir, 'trip_state.json'))}")

# Trip 2: "Restart" — new instance, same state_dir
trip2 = PsychedelicState(state_dir=test_dir)
print(f"\nTrip2 (after 'restart'): phase={trip2.phase}, dose={trip2.dose}, active={trip2.active}")
print(f"  Elapsed: {trip2.elapsed:.1f}s")
vals = trip2.tick()
print(f"  Tick values: randomness={vals['retrieval_randomness']:.3f}, gain={vals['emotional_gain']:.3f}")

# Cleanup
import shutil
shutil.rmtree(test_dir)
print("\nPersistence test PASSED!")
