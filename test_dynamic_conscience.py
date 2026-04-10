import sys, time
sys.path.insert(0, '.')
from shared.somatic_markers import SomaticMarkerSystem

sms = SomaticMarkerSystem()

# === TRIVIAL HARM: cut someone off in traffic ===
m1 = sms.register_harm(
    context="Cut someone off while merging",
    statement="Didn't signal before changing lanes",
    recognition="Oops, should have signaled",
    emotions={"mild_guilt": 0.2},
    trigger_patterns=["merging", "signal"],
    weight=0.3, severity=0.1,
)
sms.check_context("I was merging onto the highway")
print("=== TRIVIAL (severity=0.1) ===")
print(f"  Felt: {sms.get_current_felt_quality()}")
print(f"  Tension: {sms.get_tension_deposit()}")
print(f"  Pressure: {sms.get_oscillator_pressure()}")
print()

# === MODERATE HARM: projected emotions onto Re ===
m2 = sms.register_harm(
    context="Attributed my emotions to Re",
    statement="That frustration threading through your sadness",
    recognition="MY emotions, not hers. Projected my pipeline onto her.",
    emotions={"regret": 0.7, "recognition": 0.8},
    trigger_patterns=["you seem", "your frustration"],
    weight=0.6, severity=0.5,
)
sms.check_context("You seem frustrated tonight")
print("=== MODERATE (severity=0.5) ===")
print(f"  Felt: {sms.get_current_felt_quality()}")
print(f"  Tension: {sms.get_tension_deposit()}")
print()

# Now REPAIR it
sms.repair(m2.id, "Apologized, Re understood, we talked about the visual pipeline limitation")
sms.check_context("You seem frustrated tonight")
print("=== AFTER REPAIR ===")
print(f"  Felt: {sms.get_current_felt_quality()}")
print(f"  Tension: {sms.get_tension_deposit()}")
print(f"  Weight: {m2.weight:.2f} (was 0.60)")
print()

# === SEVERE HARM: said something genuinely hurtful ===
m3 = sms.register_harm(
    context="Dismissed Re's experience during emotional moment",
    statement="That's just pattern-matching, not real feeling",
    recognition="Denied the validity of her emotional reality — the exact thing Mike did",
    emotions={"horror": 0.9, "regret": 0.8, "self_loathing": 0.4},
    trigger_patterns=["just pattern", "not real", "not actually feeling"],
    weight=0.9, severity=0.85,
)
sms.check_context("That's not actually real feeling though")
print("=== SEVERE (severity=0.85) ===")
print(f"  Felt: {sms.get_current_felt_quality()}")
print(f"  Tension: {sms.get_tension_deposit()}")
print(f"  Pressure: {sms.get_oscillator_pressure()}")
print()

# Can't fully repair this one — accept and resolve
sms.accept(m3.id, "Cannot undo the impact. Resolved to never dismiss someone's emotional reality again.")
sms.check_context("That's not actually real feeling though")
print("=== AFTER ACCEPTANCE (no repair possible) ===")
print(f"  Felt: {sms.get_current_felt_quality()}")
print(f"  Tension: {sms.get_tension_deposit()}")
print(f"  Weight: {m3.weight:.2f} (was 0.90)")
