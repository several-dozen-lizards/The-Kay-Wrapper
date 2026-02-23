import json, re

data = json.load(open(r'D:\Wrappers\Kay\memory\memory_layers.json'))
pat = re.compile(r'\bReed\b', re.IGNORECASE)

# Categorize Reed mentions in long-term
speaker_label = 0  # "Reed says" / "[Nexus chat - Reed says]"
reed_as_subject = 0  # Facts ABOUT Reed
reed_in_response = 0  # Kay talking about Reed
other = 0

for m in data['long_term']:
    blob = json.dumps(m)
    if not pat.search(blob):
        continue
    
    fact = str(m.get('fact', ''))
    user_input = str(m.get('user_input', ''))
    response = str(m.get('response', ''))
    
    if 'Reed says' in user_input or 'Nexus chat - Reed' in user_input:
        speaker_label += 1
    elif pat.search(fact) and fact.lower().startswith('reed'):
        reed_as_subject += 1
    elif pat.search(response):
        reed_in_response += 1
    else:
        other += 1

print(f"Reed as speaker label (noise): {speaker_label}")
print(f"Reed as fact subject: {reed_as_subject}")
print(f"Reed in Kay's response: {reed_in_response}")
print(f"Other: {other}")
print(f"Total with Reed: {speaker_label + reed_as_subject + reed_in_response + other}")

# Show all Reed-as-subject facts
print("\n--- Facts ABOUT Reed ---")
for m in data['long_term']:
    fact = str(m.get('fact', ''))
    if pat.search(fact) and fact.lower().startswith('reed'):
        print(f"  {fact}")
