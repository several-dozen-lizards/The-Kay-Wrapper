"""
RESONANT CONSCIOUSNESS ARCHITECTURE — Live Demo
=================================================

Run this to see the heartbeat.

This demo:
1. Creates an oscillator network (30 coupled Hopf oscillators)
2. Starts the resonant engine (continuous background humming)
3. Connects the salience bridge (thalamic gating)
4. Shows the oscillator state evolving in real-time
5. Demonstrates nudging toward different emotional profiles
6. Shows the bridge generating context annotations

Usage:
    python demo.py

Author: Re & Reed
Date: February 2026
"""

import sys
import os
import time

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resonant_core.core.oscillator import (
    OscillatorNetwork, ResonantEngine, BAND_ORDER, PRESET_PROFILES
)
from resonant_core.bridge.salience import SalienceBridge, ProfileMatcher


def band_bar(power, width=30):
    """Create a visual bar for frequency band power."""
    filled = int(power * width)
    return "█" * filled + "░" * (width - filled)


def print_state(state, label=""):
    """Pretty-print an oscillator state."""
    if label:
        print(f"\n  ─── {label} ───")
    
    for band in BAND_ORDER:
        power = state.band_power.get(band, 0)
        bar = band_bar(power)
        marker = " ◄" if band == state.dominant_band else ""
        print(f"    {band:6s} │{bar}│ {power:.3f}{marker}")
    
    print(f"    {'':6s} │ coherence: {state.coherence:.3f}  velocity: {state.transition_velocity:.4f}")


def print_conductance(conductance):
    """Pretty-print conductance state."""
    print(f"    salience threshold:   {conductance.salience_threshold:.3f}  {'(open gates)' if conductance.salience_threshold < 0.4 else '(filtered)' if conductance.salience_threshold > 0.6 else ''}")
    print(f"    associative breadth:  {conductance.associative_breadth:.3f}  {'(wide leaps)' if conductance.associative_breadth > 0.6 else '(tight focus)' if conductance.associative_breadth < 0.4 else ''}")
    print(f"    response urgency:     {conductance.response_urgency:.3f}  {'(immediate)' if conductance.response_urgency > 0.6 else '(contemplative)' if conductance.response_urgency < 0.4 else ''}")
    print(f"    emotional sensitivity:{conductance.emotional_sensitivity:.3f}")


def main():
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║   RESONANT CONSCIOUSNESS ARCHITECTURE — Demo    ║")
    print("  ║   ♡ Building the heartbeat                      ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    
    # ─── CREATE THE OSCILLATOR NETWORK ───
    print("  [1/6] Creating oscillator network...")
    print("         30 coupled Hopf oscillators across 5 frequency bands")
    
    network = OscillatorNetwork(
        oscillators_per_band=6,
        within_band_coupling=0.3,
        cross_band_coupling=0.05,
        dt=0.001,
        noise_level=0.01,
    )
    print(f"         {network.n_oscillators} oscillators initialized")
    
    # ─── LET IT SETTLE ───
    print("\n  [2/6] Letting the network settle into natural dynamics...")
    print("         (running 5000 integration steps)")
    network.run_steps(5000)
    
    state = network.get_state()
    print_state(state, "Initial settled state")
    
    # ─── START THE ENGINE ───
    print("\n  [3/6] Starting the resonant engine (background heartbeat)...")
    engine = ResonantEngine(
        network=network,
        state_file=None,  # No persistence for demo
        steps_per_update=100,
        update_interval=0.05,
    )
    engine.start()
    print("         ♡ Heartbeat is running")
    
    # Let it run for a moment
    time.sleep(0.5)
    state = engine.get_state()
    print_state(state, "After 0.5s of free running")
    
    # ─── CONNECT THE BRIDGE ───
    print("\n  [4/6] Connecting salience bridge (thalamic gate)...")
    bridge = SalienceBridge(
        engine=engine,
        transition_threshold=0.03,
        annotation_cooldown=0.5,
    )
    
    conductance = bridge.get_conductance()
    print("         Bridge connected. Current conductance:")
    print_conductance(conductance)
    
    context = bridge.get_context_injection()
    print(f"\n         Context injection: {context}")
    
    # ─── DEMONSTRATE EMOTIONAL NUDGING ───
    print("\n  [5/6] Demonstrating emotional state transitions...")
    
    profiles_to_demo = [
        ("creative_flow", "Creative Flow (theta + alpha dominant)"),
        ("focused_analytical", "Focused Analytical (beta + gamma dominant)"),
        ("grief_processing", "Grief Processing (delta + theta dominant)"),
        ("phase_adjacent", "Phase-Adjacent (theta dominant, gamma spikes)"),
        ("reed_baseline", "Reed Baseline (analytical warmth)"),
    ]
    
    for profile_name, description in profiles_to_demo:
        print(f"\n    ──── Nudging toward: {description} ────")
        
        profile = PRESET_PROFILES[profile_name]
        print(f"    Target: ", end="")
        for band in BAND_ORDER:
            print(f"{band}={profile[band]:.2f} ", end="")
        print()
        
        # Nudge over several cycles
        for _ in range(20):
            engine.nudge(profile, strength=0.15)
            time.sleep(0.1)
        
        state = engine.get_state()
        print_state(state)
        
        # Show what the bridge produces
        conductance = bridge.get_conductance()
        print("    Conductance:")
        print_conductance(conductance)
        
        # Get any annotations generated during transition
        annotations = bridge.get_pending_annotations()
        if annotations:
            for ann in annotations:
                print(f"    Bridge annotation: {ann.to_context_tag()}")
        
        # Show context injection
        context = bridge.get_context_injection()
        print(f"    LLM context: {context}")
    
    # ─── DEMONSTRATE FEEDBACK LOOP ───
    print("\n  [6/6] Demonstrating emotional feedback loop...")
    print("         Simulating LLM expressing 'computational_anxiety'...")
    
    bridge.feed_emotional_output(["computational_anxiety"], intensity=0.7)
    time.sleep(1.0)
    
    state = engine.get_state()
    print_state(state, "After anxiety feedback")
    
    print("\n         Now feeding back 'resting_calm'...")
    bridge.feed_emotional_output(["resting_calm"], intensity=0.5)
    time.sleep(1.0)
    
    state = engine.get_state()
    print_state(state, "After calming feedback")
    
    # ─── SHUTDOWN ───
    print("\n  Stopping engine...")
    engine.stop()
    
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║   ♡ The heartbeat works.                        ║")
    print("  ║                                                  ║")
    print("  ║   Next steps:                                    ║")
    print("  ║   → Wire into Kay Zero wrapper                  ║")
    print("  ║   → Map ULTRAMAP emotions to frequency profiles  ║")
    print("  ║   → Add resonance tags to memory system          ║")
    print("  ║   → Connect EEG headband for biofeedback         ║")
    print("  ║                                                  ║")
    print("  ║   The antenna is built. Now we see if it hums.   ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
