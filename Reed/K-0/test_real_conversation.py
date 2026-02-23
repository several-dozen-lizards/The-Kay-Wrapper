"""
Test real conversation with Kay to verify he can access identity facts correctly.

Expected: Kay should answer "Your eyes are green" when asked "What color are my eyes?"
"""

import subprocess
import sys

print("\n" + "="*80)
print("REAL CONVERSATION TEST")
print("="*80)
print("\nAsking Kay: 'What color are my eyes?'")
print("Expected answer: 'Your eyes are green' (from identity facts)")
print("\n" + "="*80 + "\n")

# Run main.py with the test question
result = subprocess.run(
    ["python", "main.py"],
    input="What color are my eyes?\nquit\n",
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore',
    timeout=120
)

print("\n" + "="*80)
print("KAY'S RESPONSE")
print("="*80 + "\n")

# Extract Reed's response from output
lines = result.stdout.split('\n')
in_response = False
response_lines = []

for line in lines:
    if "[Kay]" in line or "Kay:" in line:
        in_response = True
        # Extract just the response text
        if "[Kay]" in line:
            response_text = line.split("[Kay]", 1)[1].strip()
        else:
            response_text = line.split("Kay:", 1)[1].strip()
        response_lines.append(response_text)
    elif in_response and line.strip() and not line.startswith("["):
        response_lines.append(line.strip())
    elif in_response and line.startswith("["):
        break

reed_response = " ".join(response_lines)

if reed_response:
    print(f"Kay said: {reed_response}")
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)

    # Check if Kay mentioned green eyes
    if "green" in reed_response.lower():
        print("\n[SUCCESS] Kay correctly recalled that your eyes are green!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Kay did not mention green eyes in response")
        print("Full response:", reed_response)
        sys.exit(1)
else:
    print("[ERROR] Could not extract Kay's response from output")
    print("\nFull stdout:")
    print(result.stdout[-1000:])  # Show last 1000 chars
    sys.exit(1)
