import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'resonant_core')
from shared.felt_state_buffer import FeltStateBuffer

b = FeltStateBuffer()
b.update_oscillator(
    'gamma', 0.45,
    {'delta': 0.01, 'theta': 0.05, 'alpha': 0.08, 'beta': 0.12, 'gamma': 0.74},
    global_coherence=0.25,
    integration_index=0.22,
    dwell_time=300.0,
    theta_gamma_plv=0.55,
    beta_gamma_plv=0.40,
    oscillator_emotion="sharp, associative, actively engaged"
)
print("TPN context line:")
print(b.get_tpn_context_line())
print()
print(f"oscillator_emotion: {b.get_snapshot().oscillator_emotion}")
