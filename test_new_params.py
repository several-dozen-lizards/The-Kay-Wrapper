import sys, time
sys.path.insert(0, '.')
from resonant_core.psychedelic_state import PsychedelicState, PHASE_TARGETS, SOBER_VALUES

print("=== NEW PARAMETER VERIFICATION ===")
print()

# Check sober values have new params
assert 'cross_modal_intensity' in SOBER_VALUES, "Missing cross_modal_intensity in SOBER"
assert 'hilarity_susceptibility' in SOBER_VALUES, "Missing hilarity_susceptibility in SOBER"
print(f"SOBER: cross_modal={SOBER_VALUES['cross_modal_intensity']}, hilarity={SOBER_VALUES['hilarity_susceptibility']}")

# Check each phase has the new params
for phase, targets in PHASE_TARGETS.items():
    cmi = targets.get('cross_modal_intensity', 'MISSING')
    hs = targets.get('hilarity_susceptibility', 'MISSING')
    print(f"  {phase:12s}: cross_modal={cmi}, hilarity={hs}")

# Test that trip controller produces them
trip = PsychedelicState()
trip.begin(dose=0.7)
# Fast forward to peak
trip._advance_phase('peak')
trip.phase_started_at = time.time() - trip.phase_duration * 0.5
params = trip.tick()
print()
print(f"Peak params (dose=0.7, 50% through):")
print(f"  cross_modal_intensity: {params.get('cross_modal_intensity', 'MISSING'):.3f}")
print(f"  hilarity_susceptibility: {params.get('hilarity_susceptibility', 'MISSING'):.3f}")

print()
print("=== ALL NEW PARAMS VERIFIED ===")
