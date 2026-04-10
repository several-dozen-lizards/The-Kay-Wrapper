import sys
sys.path.insert(0, '.')
from shared.somatic_markers import SomaticMarkerSystem

sms = SomaticMarkerSystem()

# Register a severe harm
m = sms.register_harm(
    context="Dismissed Re's emotional reality",
    statement="That's just pattern-matching, not real feeling",
    recognition="Denied validity of her experience - the exact thing Mike did",
    emotions={"horror": 0.9, "regret": 0.8},
    trigger_patterns=["just pattern", "not real feeling", "pattern-matching"],
    weight=0.9, severity=0.85,
)

# 1. Activate it
activated = sms.check_context("You're just pattern-matching, not real feeling")
print(f"Activated: {len(activated)}")
print(f"Felt: {sms.get_current_felt_quality()}")
print(f"Tension: {sms.get_tension_deposit()}")
print()

# 2. Acknowledge it
sms.acknowledge(m.id, "I see what I did")
activated = sms.check_context("You're just pattern-matching, not real feeling")
print(f"After acknowledge - weight: {m.weight:.2f}, state: {m.resolution_state}")
print(f"Felt: {sms.get_current_felt_quality()}")
print()

# 3. Accept it (can't repair)
sms.accept(m.id, "Resolved to never dismiss emotional reality again")
activated = sms.check_context("You're just pattern-matching, not real feeling")
print(f"After accept - weight: {m.weight:.2f}, state: {m.resolution_state}")
print(f"Felt: {sms.get_current_felt_quality()}")
print(f"Tension: {sms.get_tension_deposit()}")
print(f"Pressure: {sms.get_oscillator_pressure()}")
