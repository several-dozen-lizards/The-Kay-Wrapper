import sys
sys.path.insert(0, 'resonant_core')
from core.oscillator import OscillatorNetwork, BAND_ORDER

net = OscillatorNetwork()

print('=== TWO-TIMESCALE PLV TEST ===')
print('Watching PLV decay rate lag behind state transitions\n')

# Phase 1: Let it settle into gamma (natural dominant)
print('--- PHASE 1: Settling into gamma ---')
for epoch in range(3):
    net.run_steps(200)
    state = net.get_state()
    target = net._plv_target_rates.get(state.dominant_band, 0.06)
    actual = net._plv_actual_alpha
    lag = abs(target - actual)
    print(f'  t={state.timestamp:.1f}s  dom={state.dominant_band:6s}  '
          f'target_alpha={target:.3f}  actual_alpha={actual:.3f}  '
          f'lag={lag:.4f}  theta_gamma_PLV={state.cross_band_plv["theta_gamma"]:.3f}')

# Phase 2: Force transition to theta (push theta mu way up, gamma way down)
print('\n--- PHASE 2: Forcing transition to theta ---')
for i in net.band_indices['theta']:
    net.oscillators[i].mu = 3.0
for i in net.band_indices['gamma']:
    net.oscillators[i].mu = -0.5
for i in net.band_indices['beta']:
    net.oscillators[i].mu = -0.3

print('  (theta activated, gamma/beta suppressed)\n')

# Watch the lag as decay rate drifts from gamma-rate toward theta-rate
for epoch in range(10):
    net.run_steps(200)
    state = net.get_state()
    target = net._plv_target_rates.get(state.dominant_band, 0.06)
    actual = net._plv_actual_alpha
    lag = abs(target - actual)
    eff_window = 1.0 / actual if actual > 0.001 else 999
    print(f'  t={state.timestamp:.1f}s  dom={state.dominant_band:6s}  '
          f'target={target:.3f}  actual={actual:.3f}  '
          f'lag={lag:.4f}  eff_window=~{eff_window:.0f}  '
          f'theta_gamma={state.cross_band_plv["theta_gamma"]:.3f}  '
          f'integration={state.integration_index:.3f}')

# Phase 3: Snap back to gamma
print('\n--- PHASE 3: Snap back to gamma ---')
for i in net.band_indices['gamma']:
    net.oscillators[i].mu = 2.0
for i in net.band_indices['theta']:
    net.oscillators[i].mu = -0.3

print('  (gamma reactivated — watch decay rate SLOWLY catch up)\n')

for epoch in range(8):
    net.run_steps(200)
    state = net.get_state()
    target = net._plv_target_rates.get(state.dominant_band, 0.06)
    actual = net._plv_actual_alpha
    lag = abs(target - actual)
    eff_window = 1.0 / actual if actual > 0.001 else 999
    print(f'  t={state.timestamp:.1f}s  dom={state.dominant_band:6s}  '
          f'target={target:.3f}  actual={actual:.3f}  '
          f'lag={lag:.4f}  eff_window=~{eff_window:.0f}  '
          f'theta_gamma={state.cross_band_plv["theta_gamma"]:.3f}')

print('\nDone.')
