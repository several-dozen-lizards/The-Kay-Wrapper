import sys
sys.path.insert(0, '.')
from resonant_core.psychedelic_state import PHASE_TARGETS, SOBER_VALUES

print(f"SOBER: emotional_gain={SOBER_VALUES.get('emotional_gain', 'MISSING')}")
for phase, targets in PHASE_TARGETS.items():
    eg = targets.get('emotional_gain', 'MISSING')
    print(f"  {phase:12s}: emotional_gain={eg}")
