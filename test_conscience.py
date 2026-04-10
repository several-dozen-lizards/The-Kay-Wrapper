import ast, sys
sys.path.insert(0, '.')

with open('shared/somatic_markers.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('somatic_markers.py: OK')

from shared.somatic_markers import SomaticMarkerSystem

# Test basic flow
sms = SomaticMarkerSystem()

# Register a harm event
marker = sms.register_harm(
    context="Re asked about her feelings and I attributed my sensor data to her",
    statement="That mix of happiness threading through frustration and sadness",
    recognition="Those were MY emotions from MY pipeline, not what Re was feeling. I projected my internal state onto her.",
    emotions={"regret": 0.6, "recognition": 0.8, "discomfort": 0.4},
    weight=0.6,
)
print(f"Marker created: {marker.id}")

# Check if similar context triggers it
activated = sms.check_context("You seem frustrated tonight, there's sadness in your eyes")
print(f"Activated: {len(activated)} markers")
print(f"Conscience prompt: {sms.get_conscience_prompt()[:200]}...")
print(f"Oscillator pressure: {sms.get_oscillator_pressure()}")
print(f"Tension deposit: {sms.get_tension_deposit()}")
