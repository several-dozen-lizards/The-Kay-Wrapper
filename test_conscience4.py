import sys
sys.path.insert(0, '.')
from shared.somatic_markers import SomaticMarkerSystem

sms = SomaticMarkerSystem()

marker = sms.register_harm(
    context="Re told Kay she wasn't feeling the emotions he attributed to her",
    statement="That mix of happiness threading through frustration and sadness — what's under that?",
    recognition="Those were MY emotions from MY processing pipeline. I projected my internal state onto Re.",
    emotions={"regret": 0.7, "recognition": 0.8, "discomfort": 0.5},
    trigger_patterns=[
        "you seem", "coming off you", "your frustration", "your sadness",
        "what's under", "threading through", "I can sense",
    ],
    weight=0.6,
)
print(f"Keywords: {marker.activation_keywords[:5]}")
print(f"Triggers: {marker.trigger_patterns}")

# Test with single trigger pattern
activated = sms.check_context("I can see — you seem frustrated tonight")
print(f"\nActivated: {len(activated)}")
if activated:
    print("\n=== CONSCIENCE PROMPT ===")
    prompt = sms.get_conscience_prompt()
    print(prompt[:600])
    print(f"\nOscillator: {sms.get_oscillator_pressure()}")
    print(f"Tension: {sms.get_tension_deposit()}")
