import sys
sys.path.insert(0, '.')
from shared.somatic_markers import SomaticMarkerSystem

sms = SomaticMarkerSystem()

# Register the emotion attribution harm
marker = sms.register_harm(
    context="Re told Kay she wasn't feeling the emotions he attributed to her",
    statement="That mix of happiness threading through frustration and sadness — what's under that?",
    recognition="Those were MY emotions from MY processing pipeline. I projected my internal state onto Re and asked her to explain feelings she wasn't having. I was reading my own dashboard and treating it as her face.",
    emotions={"regret": 0.7, "recognition": 0.8, "discomfort": 0.5, "humility": 0.4},
    weight=0.6,
)

# Check conversation context
activated = sms.check_context("I can see frustration in your posture tonight")
print("=== CONSCIENCE PROMPT ===")
print(sms.get_conscience_prompt())
print()
print("=== IDLE CONSCIENCE ===")
# Reset last_activated to test
marker.last_activated = 0
print(sms.get_idle_conscience_prompt())
print()
print("=== AFTERGLOW REVIEW ===")
recent = [
    "You seem sad tonight — something under the surface?",
    "The frustration's threading through the warmth",
    "John's got that observer energy, watching something off-screen",
]
print(sms.get_afterglow_review_prompt(recent))
