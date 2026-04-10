import re

content = open(r'D:\Wrappers\nexus\nexus_kay.py', encoding='utf-8').read()
lines = content.split('\n')

# Find each anthropic_client.messages.create call and its context
for i, line in enumerate(lines, 1):
    if 'anthropic_client.messages.create' in line:
        # Look backwards for context (function name, activity type)
        context = ""
        for j in range(max(0, i-20), i):
            l = lines[j-1].strip()
            if 'def ' in l or 'ACTIVITY' in l or '# ---' in l or 'async def' in l:
                context = l[:80]
        print(f"Line {i}: max_tokens={lines[i].strip()[:30] if i < len(lines) else '?'}")
        print(f"  Context: {context}")
        print()

# Also check nexus_reed.py
print("=" * 50)
print("REED:")
reed_content = open(r'D:\Wrappers\nexus\nexus_reed.py', encoding='utf-8').read()
reed_lines = reed_content.split('\n')
for i, line in enumerate(reed_lines, 1):
    if 'anthropic_client' in line or 'api.anthropic' in line:
        context = ""
        for j in range(max(0, i-15), i):
            l = reed_lines[j-1].strip()
            if 'def ' in l or 'ACTIVITY' in l or '# ---' in l:
                context = l[:80]
        print(f"Line {i}: {line.strip()[:60]}")
        print(f"  Context: {context}")
        print()

# Also check wrapper_bridge.py for Anthropic calls
print("=" * 50)
print("WRAPPER BRIDGE:")
bridge = open(r'D:\Wrappers\Kay\wrapper_bridge.py', encoding='utf-8').read()
bridge_lines = bridge.split('\n')
anthropic_count = 0
for i, line in enumerate(bridge_lines, 1):
    if 'anthropic' in line.lower() and ('client' in line.lower() or 'model' in line.lower()):
        anthropic_count += 1
print(f"  Anthropic references: {anthropic_count}")

# Check llm_retrieval for model usage
import glob
for f in glob.glob(r'D:\Wrappers\Kay\*retrieval*'):
    print(f"\n  Found: {f}")
    c = open(f, encoding='utf-8').read()
    for i, line in enumerate(c.split('\n'), 1):
        if 'model' in line.lower() and ('sonnet' in line.lower() or 'claude' in line.lower() or 'anthropic' in line.lower()):
            print(f"    Line {i}: {line.strip()[:100]}")
