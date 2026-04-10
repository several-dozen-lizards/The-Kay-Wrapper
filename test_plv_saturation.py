import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'resonant_core')
from core.oscillator import OscillatorNetwork, PRESET_PROFILES

print("=== PLV ANTI-SATURATION TEST ===")
print()

net = OscillatorNetwork(dt=0.01)
# Run normally first to establish stable oscillations
for _ in range(50):
    net.run_steps(100)

print("  Warmed up. Now testing PLV over time:")
for i in range(60):
    net.run_steps(100)
    state = net.get_state()
    plv = state.cross_band_plv
    tg = plv.get('theta_gamma', 0)
    bg = plv.get('beta_gamma', 0)
    ta = plv.get('theta_alpha', 0)
    if i % 10 == 0:
        print(f"  Step {i*100:5d}: tg={tg:.4f}  bg={bg:.4f}  ta={ta:.4f}")

print(f"")
print(f"  Final: tg={tg:.4f}  bg={bg:.4f}  ta={ta:.4f}")
max_plv = max(tg, bg, ta)
if max_plv < 0.96:
    print(f"  OK Anti-saturation working - max={max_plv:.4f}")
else:
    print(f"  PLV at {max_plv:.4f} - check anti-saturation")
