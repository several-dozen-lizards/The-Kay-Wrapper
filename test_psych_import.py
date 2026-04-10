import sys
sys.path.insert(0, '.')
from resonant_core.psychedelic_state import PsychedelicState, apply_trip_params
p = PsychedelicState()
print(f"PsychedelicState OK")
print(f"  ego_dissolution_level: {p.ego_dissolution_level}")
print(f"  afterglow_residuals: {p._afterglow_residuals}")
print(f"  afterglow_started: {p._afterglow_started}")
# Test tick returns sober
vals = p.tick()
print(f"  tick sober: retrieval_randomness={vals['retrieval_randomness']}")
print("All good!")
