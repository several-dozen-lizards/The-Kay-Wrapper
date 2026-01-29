"""
Script to reduce MAX_TOTAL_MEMORIES from 250 to 50 to fix hallucination
"""
import re

file_path = r"D:\ChristinaStuff\AlphaKayZero\engines\memory_engine.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make the replacement
old_line = "        MAX_TOTAL_MEMORIES = 250  # Reasonable limit to prevent $50/week API costs"
new_line = "        MAX_TOTAL_MEMORIES = 50  # AGGRESSIVE REDUCTION: Prevent hallucination from context overload"

if old_line in content:
    content = content.replace(old_line, new_line)
    print(f"✅ Found and replaced MAX_TOTAL_MEMORIES: 250 → 50")
else:
    print(f"❌ Could not find exact line to replace")
    print(f"Searching for MAX_TOTAL_MEMORIES...")
    matches = re.findall(r'MAX_TOTAL_MEMORIES\s*=\s*\d+', content)
    for match in matches:
        print(f"  Found: {match}")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ File saved: {file_path}")
