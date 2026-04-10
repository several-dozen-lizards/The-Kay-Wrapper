import sys
sys.path.insert(0, 'resonant_core')
from core.oscillator import PRESET_PROFILES
from oscillator_emotion_bridge import read_oscillator_emotion

print('=== OSCILLATOR -> EMOTION BRIDGE TEST ===\n')

# Test 1: Feed each preset profile back in — should match itself
print('--- Self-matching test (each profile should find itself) ---')
for name, profile in PRESET_PROFILES.items():
    result = read_oscillator_emotion(profile, PRESET_PROFILES)
    match = "OK" if result["profile_match"] == name else f"MISMATCH: got {result['profile_match']}"
    print(f'  {name:25s} -> {result["felt_emotion"]:15s} (conf={result["confidence"]:.3f}) [{match}]')

# Test 2: Realistic oscillator states
print('\n--- Realistic oscillator states ---')
tests = [
    ("Gamma-dominant (awake)", {"delta": 0.01, "theta": 0.02, "alpha": 0.05, "beta": 0.10, "gamma": 0.82}),
    ("Alpha-dominant (relaxed)", {"delta": 0.05, "theta": 0.10, "alpha": 0.55, "beta": 0.20, "gamma": 0.10}),
    ("Theta-dominant (sleep)", {"delta": 0.20, "theta": 0.40, "alpha": 0.20, "beta": 0.10, "gamma": 0.10}),
    ("Delta-dominant (deep sleep)", {"delta": 0.50, "theta": 0.25, "alpha": 0.10, "beta": 0.10, "gamma": 0.05}),
    ("Mixed beta-gamma (active)", {"delta": 0.05, "theta": 0.10, "alpha": 0.10, "beta": 0.35, "gamma": 0.40}),
]

for label, bp in tests:
    plv = {"theta_gamma": 0.65, "beta_gamma": 0.45, "theta_alpha": 0.55, "delta_theta": 0.30}
    result = read_oscillator_emotion(bp, PRESET_PROFILES, cross_band_plv=plv, integration_index=0.3)
    print(f'  {label:30s} -> felt_sense: "{result["felt_sense"]}"')
    print(f'    {"":30s}    top matches: {list(result["all_scores"].keys())[:3]}')
