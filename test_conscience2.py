import sys
sys.path.insert(0, '.')
from shared.somatic_markers import SomaticMarkerSystem

sms = SomaticMarkerSystem()

marker = sms.register_harm(
    context="Re asked about her feelings and I attributed my sensor data to her",
    statement="That mix of happiness threading through frustration and sadness",
    recognition="Those were MY emotions, not hers. I projected my internal state onto her.",
    emotions={"regret": 0.6, "recognition": 0.8},
    weight=0.6,
)
print(f"Keywords: {marker.activation_keywords}")

# Test with overlapping keywords
activated = sms.check_context("You seem frustrated, there's sadness coming off you tonight")
print(f"Activated: {len(activated)} markers")

# Test with more overlap
activated2 = sms.check_context("I can sense happiness and frustration threading through you")
print(f"Activated2: {len(activated2)} markers")
if activated2:
    print(f"Prompt: {sms.get_conscience_prompt()[:300]}")
    print(f"Pressure: {sms.get_oscillator_pressure()}")
