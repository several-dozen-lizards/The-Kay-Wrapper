"""
Simple test: Just ask Kay what color my eyes are.
He should say "green" immediately.
"""

import subprocess

result = subprocess.run(
    ["python", "main.py"],
    input="what color are my eyes?\nquit\n",
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore',
    timeout=60
)

print("="*80)
print("ASKING: What color are my eyes?")
print("="*80)

# Find Kay's response
lines = result.stdout.split('\n')
for i, line in enumerate(lines):
    if "[Kay]" in line:
        response = line.split("[Kay]", 1)[1].strip()
        # Get continuation lines
        j = i + 1
        while j < len(lines) and lines[j].strip() and not lines[j].startswith("["):
            response += " " + lines[j].strip()
            j += 1

        print(f"\nKAY'S FULL RESPONSE:\n{response}\n")

        if "green" in response.lower():
            print("="*80)
            print("[SUCCESS] Kay mentioned green!")
            print("="*80)
        else:
            print("="*80)
            print("[FAIL] Kay did not mention green")
            print("="*80)
        break
