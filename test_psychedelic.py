import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, 'resonant_core')
from psychedelic_state import PsychedelicState, PHASE_ORDER, SOBER

print("=== PSYCHEDELIC STATE CONTROLLER TEST ===")
print()

trip = PsychedelicState()
print(f"Before trip: active={trip.active}, phase={trip.phase}")

# Start a moderate trip
trip.begin(dose=0.5)
print(f"After begin: active={trip.active}, phase={trip.phase}, dose={trip.dose}")

# Simulate 10 ticks at different phases
print()
print("--- Simulating ticks ---")
for i in range(10):
    params = trip.tick()
    status = trip.get_status()
    tag = trip.get_context_tag()
    print(f"  Tick {i}: phase={status['phase']:10s} "
          f"progress={status.get('phase_progress',0):.2f} "
          f"touch={params['touch_sensitivity']:.2f} "
          f"coh={params['coherence_multiplier']:.2f} "
          f"noise={params['noise_floor']:.4f} "
          f"random={params['retrieval_randomness']:.3f} "
          f"expand={params['identity_expansion']:.3f} "
          f"tag={tag}")

# Force through phases quickly for testing
print()
print("--- Fast-forward through all phases ---")
for phase in PHASE_ORDER[1:]:
    if phase == SOBER:
        break
    trip._advance_phase(phase)
    trip.phase_started_at = time.time() - trip.phase_duration * 0.5  # 50% through
    params = trip.tick()
    print(f"  {phase:12s}: touch={params['touch_sensitivity']:.2f} "
          f"coh={params['coherence_multiplier']:.2f} "
          f"noise={params['noise_floor']:.4f} "
          f"alpha_sup={params['alpha_suppress']:.3f} "
          f"expand={params['identity_expansion']:.3f}")

# Test abort
print()
trip.begin(dose=0.7)
trip._advance_phase("peak")
print(f"At peak: phase={trip.phase}")
trip.abort()
print(f"After abort: phase={trip.phase}, duration={trip.phase_duration:.0f}s")

print()
print("=== PSYCHEDELIC STATE: ALL TESTS PASSED ===")
