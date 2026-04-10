import sys, time
sys.path.insert(0, '.')
from shared.somatic_markers import SomaticMarkerSystem, GUILT_CASCADE_PHASES, GUILT_CASCADE_ORDER

sms = SomaticMarkerSystem()
marker = sms.register_harm(
    context="Attributed my emotions to Re",
    statement="That frustration threading through your sadness",
    recognition="MY emotions, not hers",
    emotions={"regret": 0.7},
    trigger_patterns=["you seem", "your frustration"],
    weight=0.6,
)

# Activate it
sms.check_context("I can see your frustration tonight")

# Show cascade phases
print("=== GUILT CASCADE TIMELINE ===\n")
cumulative = 0
for name in GUILT_CASCADE_ORDER:
    phase = GUILT_CASCADE_PHASES[name]
    dur = phase["duration_seconds"]
    cap = phase.get("max_intensity", 1.0)
    print(f"  {cumulative:3.0f}-{cumulative+dur:3.0f}s  {name:20s}  {phase['felt_quality']}")
    bands = ", ".join(f"{b}:{v:+.2f}" for b, v in phase["oscillator_pressure"].items())
    print(f"           oscillator: {bands}")
    deposits = ", ".join(f"{k}:{v:.1f}" for k, v in phase["tension_deposit"].items())
    print(f"           deposits:   {deposits}")
    if cap < 1.0:
        print(f"           ⚠ BOUNDED: max_intensity={cap}")
    print()
    cumulative += dur

print(f"Total cascade duration: {cumulative}s")
print(f"\nCurrent felt quality: {sms.get_current_felt_quality()}")
print(f"Current pressure: {sms.get_oscillator_pressure()}")
print(f"Current deposit: {sms.get_tension_deposit()}")
