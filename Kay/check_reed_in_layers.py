import json, re

data = json.load(open(r'D:\Wrappers\Kay\memory\memory_layers.json'))
pat = re.compile(r'\bReed\b', re.IGNORECASE)

# Check working memory samples
for i, m in enumerate(data['working'][:3]):
    blob = json.dumps(m)
    matches = pat.findall(blob)
    mtype = m.get("type", "?")
    print(f"Working [{i}]: type={mtype}, Reed mentions={len(matches)}")
    for field in ['fact', 'user_input', 'response', 'text']:
        if field in m and pat.search(str(m[field])):
            snippet = str(m[field])[:120]
            print(f"  in {field}: {snippet}")

print()

# Check some long-term that DON'T mention Reed
no_reed = [m for m in data['long_term'] if not pat.search(json.dumps(m))]
print(f"Long-term WITHOUT Reed: {len(no_reed)}")
for m in no_reed[:5]:
    mtype = m.get("type", "?")
    fact = str(m.get("fact", ""))[:100]
    print(f"  type={mtype}, fact={fact}")

print()

# Check WHERE Reed appears in long-term (sample)
with_reed = [m for m in data['long_term'] if pat.search(json.dumps(m))]
print(f"Long-term WITH Reed: {len(with_reed)}")
for m in with_reed[:5]:
    mtype = m.get("type", "?")
    # Find which fields contain Reed
    fields_with_reed = []
    for field in ['fact', 'user_input', 'response', 'text', 'document_name', 'source_document']:
        val = str(m.get(field, ""))
        if pat.search(val):
            fields_with_reed.append(field)
    fact = str(m.get("fact", ""))[:80]
    print(f"  type={mtype}, fields={fields_with_reed}, fact={fact}")
