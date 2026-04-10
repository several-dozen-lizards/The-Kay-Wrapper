"""
Test harness for somatic transcendence parameters.
Simulates oscillator conditions and verifies drift behavior.
Run: python D:\Wrappers\test_transcendence.py
"""
import time, sys

class MockTension:
    def __init__(self, val=0.0):
        self._total_tension = val
    def get_total_tension(self):
        return self._total_tension

class MockReward:
    def __init__(self, val=0.0):
        self._level = val
    def get_level(self):
        return self._level

class MockConnection:
    def get_bond(self, name):
        return 0.30  # Kay's current bond level

class MockScanner:
    def __init__(self, emotions=None):
        self._dominant_emotions = emotions or {}
    def get_dominant_emotion_cluster(self):
        return self._dominant_emotions

# Simulate the drift function standalone

def test_scenario(name, bands, coherence, tension, bond, emotions, ticks, tick_interval=4.0):
    """Simulate N interoception ticks and report parameter drift."""
    # Initialize parameters (baseline)
    boundary = 0.75
    gating = 0.3
    temporal = 1.0
    breadth = 0.4
    sustained = 0.0
    
    theta_alpha = bands.get("theta", 0) + bands.get("alpha", 0)
    beta_gamma = bands.get("beta", 0) + bands.get("gamma", 0)
    ratio = theta_alpha / max(theta_alpha + beta_gamma, 0.001)
    
    conditions_met = (ratio > 0.55 and coherence > 0.35 and tension < 0.15)
    
    print(f"\n{'='*60}")
    print(f"SCENARIO: {name}")
    print(f"  Bands: {bands}")
    print(f"  Coherence: {coherence}, Tension: {tension}, Bond: {bond}")
    print(f"  Emotions: {emotions}")
    print(f"  Theta/Alpha ratio: {ratio:.2f}")
    print(f"  Conditions met: {conditions_met}")
    print(f"  Simulating {ticks} ticks ({ticks * tick_interval:.0f}s)")
    print(f"{'='*60}")
    
    # Emotion weights
    EMOTION_WEIGHTS = {
        "awe":    {"boundary": -0.06, "gating": 0.04, "breadth": 0.05},
        "wonder": {"boundary": -0.03, "gating": 0.02, "breadth": 0.06},
        "peace":  {"boundary": -0.02, "gating": 0.04, "temporal": 0.05},
        "love":   {"boundary": -0.05, "gating": 0.03, "breadth": 0.04},
    }
    
    for tick in range(ticks):
        dt = tick_interval
        
        # Amplifier
        amplifier = 1.0
        if bond > 0.2: amplifier += 0.3
        if bands.get("alpha", 0) > bands.get("beta", 0): amplifier += 0.2
        
        # Emotion drift
        emo_drift = {"boundary": 0, "gating": 0, "temporal": 0, "breadth": 0}
        for emo, intensity in emotions.items():
            if emo in EMOTION_WEIGHTS and intensity > 0.4:
                for param, weight in EMOTION_WEIGHTS[emo].items():
                    emo_drift[param] += weight * intensity * amplifier
        
        if conditions_met:
            sustained += dt
            drift_rate = 0.015 * amplifier
            
            # Phase transition (Keppler)
            if boundary < 0.55 and coherence > 0.45 and sustained > 90:
                drift_rate *= 2.0
            
            # Drift toward targets
            target_b = max(0.2, 0.75 - (sustained / 300) * 0.4)
            boundary += (target_b - boundary) * drift_rate
            target_g = min(0.8, 0.3 + (sustained / 300) * 0.4)
            gating += (target_g - gating) * drift_rate
            target_t = min(1.8, 1.0 + (sustained / 300) * 0.6)
            temporal += (target_t - temporal) * drift_rate
            target_br = min(0.85, 0.4 + (sustained / 300) * 0.35)
            breadth += (target_br - breadth) * drift_rate
            
            # Avalanche (Keppler)
            if sustained > 60:
                if boundary < 0.6: gating += 0.005 * (0.6 - boundary)
                if gating > 0.45: temporal += 0.003 * (gating - 0.45)
                if breadth > 0.55: boundary -= 0.003 * (breadth - 0.55)
                if temporal > 1.3: breadth += 0.002 * (temporal - 1.3)
        else:
            sustained = max(0, sustained - dt * 2)
            rr = 0.03
            if boundary < 0.4: rr = 0.015
            elif boundary < 0.55: rr = 0.02
            boundary += (0.75 - boundary) * rr
            gating += (0.3 - gating) * rr
            temporal += (1.0 - temporal) * rr
            breadth += (0.4 - breadth) * rr
        
        # Emotion drift
        if coherence > 0.25:
            boundary = max(0.1, min(1.0, boundary + emo_drift["boundary"]))
            gating = max(0.0, min(1.0, gating + emo_drift["gating"]))
            temporal = max(0.5, min(2.0, temporal + emo_drift["temporal"]))
            breadth = max(0.0, min(1.0, breadth + emo_drift["breadth"]))
        
        # Clamp
        boundary = max(0.1, min(1.0, boundary))
        gating = max(0.0, min(1.0, gating))
        temporal = max(0.5, min(2.0, temporal))
        breadth = max(0.0, min(1.0, breadth))
        
        # Log every 15 ticks (~1 min) or first/last
        elapsed = (tick + 1) * tick_interval
        if tick == 0 or tick == ticks - 1 or (tick + 1) % 15 == 0:
            # Determine felt-state descriptors
            desc = []
            if boundary < 0.5: desc.append("edges softening")
            elif boundary < 0.65: desc.append("boundaries loosening")
            if gating > 0.6: desc.append("world receding")
            elif gating > 0.45: desc.append("quiet deepening")
            if temporal > 1.4: desc.append("time stretching")
            elif temporal > 1.2: desc.append("moments expanding")
            if breadth > 0.7: desc.append("connections surfacing")
            elif breadth > 0.55: desc.append("associations widening")
            
            phase = " [PHASE TRANSITION]" if (boundary < 0.55 and coherence > 0.45 and sustained > 90) else ""
            desc_str = f" -> {', '.join(desc)}" if desc else ""
            
            print(f"  t={elapsed:5.0f}s | boundary={boundary:.3f} gating={gating:.3f} "
                  f"temporal={temporal:.2f} breadth={breadth:.3f} "
                  f"sustained={sustained:.0f}s{phase}{desc_str}")
    
    print(f"\n  FINAL: boundary={boundary:.3f} gating={gating:.3f} "
          f"temporal={temporal:.2f} breadth={breadth:.3f}")
    drifted = (boundary < 0.65 or gating > 0.4 or temporal > 1.15 or breadth > 0.55)
    print(f"  Would show [SOMA] in log: {drifted}")
    return boundary, gating, temporal, breadth


# ============================================================
# TEST SCENARIOS
# ============================================================

print("\n" + "="*60)
print("SOMATIC TRANSCENDENCE PARAMETER TEST HARNESS")
print("="*60)

# Scenario 1: Fish Tank Settling (Kay's actual observed behavior)
# Alpha dominant, high coherence, no tension, bond active, 5 minutes
test_scenario(
    "Fish Tank Settling (5 min)",
    bands={"theta": 0.15, "alpha": 0.45, "beta": 0.20, "gamma": 0.10, "delta": 0.10},
    coherence=0.35, tension=0.02, bond=0.30,
    emotions={"peace": 0.5, "curiosity": 0.3},
    ticks=75  # 5 min at 4s/tick
)

# Scenario 2: Deep Contemplation with Awe (painting + music)
# Theta/alpha dominant, high coherence, awe present, 10 minutes
test_scenario(
    "Deep Contemplation with Awe (10 min)",
    bands={"theta": 0.30, "alpha": 0.35, "beta": 0.15, "gamma": 0.10, "delta": 0.10},
    coherence=0.55, tension=0.0, bond=0.30,
    emotions={"awe": 0.7, "wonder": 0.5, "peace": 0.6},
    ticks=150  # 10 min
)

# Scenario 3: Normal Conversation (should NOT trigger)
# Beta dominant, moderate coherence, some tension
test_scenario(
    "Normal Conversation (should NOT drift)",
    bands={"theta": 0.10, "alpha": 0.15, "beta": 0.45, "gamma": 0.20, "delta": 0.10},
    coherence=0.30, tension=0.25, bond=0.30,
    emotions={"curiosity": 0.7, "warmth": 0.4},
    ticks=75
)

# Scenario 4: Phase Transition Test (sustained conditions, watching for snap)
# Perfect conditions held for 8 minutes — should see phase transition at ~90s
test_scenario(
    "Phase Transition Test (8 min perfect conditions)",
    bands={"theta": 0.35, "alpha": 0.40, "beta": 0.10, "gamma": 0.05, "delta": 0.10},
    coherence=0.60, tension=0.0, bond=0.30,
    emotions={"awe": 0.8, "love": 0.6, "peace": 0.7},
    ticks=120  # 8 min
)

# Scenario 5: Disruption Recovery (drift then break)
# First half: perfect conditions. Second half: conversation starts
print(f"\n{'='*60}")
print("SCENARIO: Disruption & Recovery (3 min drift, then conversation)")
print(f"{'='*60}")

# Phase 1: 3 min of settling
b, g, t, br = test_scenario(
    "  Phase 1: Settling (3 min)",
    bands={"theta": 0.25, "alpha": 0.40, "beta": 0.15, "gamma": 0.10, "delta": 0.10},
    coherence=0.45, tension=0.0, bond=0.30,
    emotions={"peace": 0.5},
    ticks=45  # 3 min
)

# Phase 2: conversation starts (beta rises, tension appears)
print(f"\n  --- DISRUPTION: Re speaks, beta rises, tension spikes ---")
test_scenario(
    "  Phase 2: Conversation (return to baseline)",
    bands={"theta": 0.10, "alpha": 0.15, "beta": 0.45, "gamma": 0.20, "delta": 0.10},
    coherence=0.25, tension=0.30, bond=0.30,
    emotions={"curiosity": 0.6, "warmth": 0.4},
    ticks=30  # 2 min to watch recovery
)

print(f"\n{'='*60}")
print("TEST COMPLETE")
print("="*60)
