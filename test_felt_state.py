import sys
sys.path.insert(0, '.')
from shared.felt_state_buffer import FeltStateBuffer, FeltState

b = FeltStateBuffer()
b.update_oscillator(
    'theta', 0.65,
    {'delta': 0.1, 'theta': 0.4, 'alpha': 0.2, 'beta': 0.2, 'gamma': 0.1},
    global_coherence=0.42,
    integration_index=0.38,
    dwell_time=120.0,
    theta_gamma_plv=0.35,
    beta_gamma_plv=0.22
)
print("TPN context line:")
print(b.get_tpn_context_line())
print()
snap = b.get_snapshot()
print(f"Snapshot fields:")
print(f"  global_coherence: {snap.global_coherence}")
print(f"  integration_index: {snap.integration_index}")
print(f"  dwell_time: {snap.dwell_time}")
print(f"  theta_gamma_plv: {snap.theta_gamma_plv}")
print(f"  beta_gamma_plv: {snap.beta_gamma_plv}")
