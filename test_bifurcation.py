"""Unit test for the bifurcation delay state machine itself.
Instead of fighting oscillator dynamics, we mock the power values
to simulate what happens when a real transition occurs."""

import sys
sys.path.insert(0, 'resonant_core')
from core.oscillator import OscillatorNetwork, BAND_ORDER
import numpy as np

net = OscillatorNetwork(within_band_coupling=0.05, cross_band_coupling=0.01)

print('=== BIFURCATION DELAY: STATE MACHINE UNIT TEST ===\n')

# Phase 1: Let it settle normally
print('--- Phase 1: Natural settle ---')
for _ in range(5):
    net.run_steps(200)
state = net.get_state()
print(f'  Settled into {state.dominant_band}, dwell={state.dwell_time:.1f}s')
print(f'  Transition state: {net._transition}')

# Phase 2: Force a crossover by directly setting oscillator amplitudes
print('\n--- Phase 2: Force theta > gamma (simulating overnight silence) ---')
for i in net.band_indices['theta']:
    net.oscillators[i].z = complex(5.0, 2.0)  # BIG amplitude
    net.oscillators[i].mu = 2.0
for i in net.band_indices['gamma']:
    net.oscillators[i].z = complex(0.001, 0.001)  # Nearly dead
    net.oscillators[i].mu = -1.0
for i in net.band_indices['delta']:
    net.oscillators[i].z = complex(3.0, 1.0)
    net.oscillators[i].mu = 1.5

print('  (theta amplitude >> gamma amplitude)')

# Now get_state should see theta as raw dominant, triggering the delay
for step in range(12):
    net.run_steps(10)  # Small steps to see the transition unfold
    state = net.get_state()
    trans = ""
    if state.in_transition:
        trans = f"  <<< {state.transition_from}->{state.transition_to} ({state.transition_progress:.0%}) >>>"
    noise = f"  noise={net._transition_active_noise:.2f}" if net._transition_active_noise > 1.05 else ""
    bp = state.band_power
    print(f'  Step {step+1}: dom={state.dominant_band:6s} dwell={state.dwell_time:.2f}s  '
          f'th={bp["theta"]:.2f} gm={bp["gamma"]:.2f}{trans}{noise}')

print(f'\n  Final transition state: {net._transition}')
print(f'  Noise multiplier: {net._transition_active_noise:.3f}')

# Phase 3: Verify reversion cancels transition
print('\n--- Phase 3: Revert back (should cancel transition) ---')
for i in net.band_indices['gamma']:
    net.oscillators[i].z = complex(5.0, 2.0)
    net.oscillators[i].mu = 2.0
for i in net.band_indices['theta']:
    net.oscillators[i].z = complex(0.001, 0.001)
    net.oscillators[i].mu = -1.0

for step in range(5):
    net.run_steps(10)
    state = net.get_state()
    trans = ""
    if state.in_transition:
        trans = f"  <<< {state.transition_from}->{state.transition_to} ({state.transition_progress:.0%}) >>>"
    bp = state.band_power
    print(f'  Step {step+1}: dom={state.dominant_band:6s}  th={bp["theta"]:.2f} gm={bp["gamma"]:.2f}{trans}')

print(f'\n  Transition cancelled: {net._transition is None}')
print('\nDone.')
