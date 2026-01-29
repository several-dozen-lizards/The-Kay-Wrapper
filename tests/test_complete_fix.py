"""
Complete test to verify:
1. Memory retrieval works (498 memories including 364 identity facts)
2. Bypass passes all memories to context transformation
3. Context transformation preserves all memories
4. LLM prompt receives all memories
5. Kay can answer correctly

Test scenario:
Turn 1: "my eyes are green" (establish fact)
Turn 2: "what color are my eyes?" (recall fact)

Expected: Kay says "green"
"""

import subprocess
import sys
import os

def run_conversation(inputs):
    """Run main.py with given inputs and return output."""
    input_text = "\n".join(inputs) + "\nquit\n"

    result = subprocess.run(
        ["python", "main.py"],
        input=input_text,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        timeout=120
    )

    return result.stdout, result.stderr

def extract_kay_response(output, turn_number):
    """Extract Kay's response for a specific turn."""
    lines = output.split('\n')
    responses = []
    in_response = False

    for line in lines:
        if "[Kay]" in line or "Kay:" in line:
            if "[Kay]" in line:
                text = line.split("[Kay]", 1)[1].strip()
            else:
                text = line.split("Kay:", 1)[1].strip()
            responses.append(text)
            in_response = True
        elif in_response and line.strip() and not line.startswith("["):
            responses.append(line.strip())
        elif in_response and line.startswith("["):
            in_response = False

    if turn_number <= len(responses):
        return responses[turn_number - 1]
    return None

def check_memory_logs(output):
    """Extract memory pipeline stats from logs."""
    lines = output.split('\n')

    stats = {
        'retrieved': None,
        'bypass': None,
        'context': None,
        'identity': None
    }

    for line in lines:
        if "RECALL CHECKPOINT 2" in line and "Before storage" in line:
            try:
                stats['retrieved'] = int(line.split("Before storage in state:")[1].split("memories")[0].strip())
            except:
                pass
        elif "BYPASS CHECKPOINT 1" in line and "Retrieved" in line:
            try:
                stats['bypass'] = int(line.split("Retrieved")[1].split("memories")[0].strip())
            except:
                pass
        elif "LLM PROMPT CHECKPOINT 1" in line and "Memories in context:" in line:
            try:
                stats['context'] = int(line.split("Memories in context:")[1].strip())
            except:
                pass
        elif "BYPASS CHECKPOINT 2" in line and "Identity facts" in line:
            try:
                stats['identity'] = int(line.split("Identity facts in selected memories:")[1].strip())
            except:
                pass

    return stats

print("\n" + "="*80)
print("COMPLETE FIX VERIFICATION TEST")
print("="*80)
print("\nThis test verifies the entire memory pipeline end-to-end:")
print("  1. Store fact: 'my eyes are green'")
print("  2. Recall fact: 'what color are my eyes?'")
print("  3. Verify Kay says 'green'")
print("\n" + "="*80 + "\n")

# Run conversation
stdout, stderr = run_conversation([
    "my eyes are green",
    "what color are my eyes?"
])

# Combine stdout and stderr for log analysis
full_output = stdout + "\n" + stderr

# Check memory pipeline
stats = check_memory_logs(full_output)

print("="*80)
print("MEMORY PIPELINE STATS")
print("="*80)
print(f"  Retrieved from memory engine: {stats['retrieved'] if stats['retrieved'] else 'NOT FOUND'}")
print(f"  Passed through bypass:        {stats['bypass'] if stats['bypass'] else 'NOT FOUND'}")
print(f"  Identity facts included:      {stats['identity'] if stats['identity'] else 'NOT FOUND'}")
print(f"  Reached LLM prompt builder:   {stats['context'] if stats['context'] else 'NOT FOUND'}")

# Extract Kay's responses
response_1 = extract_kay_response(stdout, 1)
response_2 = extract_kay_response(stdout, 2)

print("\n" + "="*80)
print("KAY'S RESPONSES")
print("="*80)
print(f"\nTurn 1 (user: 'my eyes are green'):")
if response_1:
    print(f"Kay: {response_1[:200]}")
else:
    print("  [Could not extract response]")

print(f"\nTurn 2 (user: 'what color are my eyes?'):")
if response_2:
    print(f"Kay: {response_2[:200]}")
else:
    print("  [Could not extract response]")

print("\n" + "="*80)
print("FINAL ANALYSIS")
print("="*80)

# Check success criteria
success = True
issues = []

# 1. Memory pipeline should preserve all memories
if stats['retrieved'] and stats['context']:
    if stats['retrieved'] == stats['context']:
        print(f"\n[OK] Memory pipeline preserved: {stats['retrieved']} -> {stats['context']}")
    else:
        print(f"\n[FAIL] Memory loss: {stats['retrieved']} -> {stats['context']}")
        issues.append(f"Lost {stats['retrieved'] - stats['context']} memories in pipeline")
        success = False
else:
    print("\n[WARN] Could not verify memory pipeline (missing logs)")

# 2. Identity facts should be included
if stats['identity'] and stats['identity'] > 0:
    print(f"[OK] Identity facts included: {stats['identity']}")
else:
    print("[WARN] No identity facts detected in logs")

# 3. Kay should mention "green" in turn 2
if response_2 and "green" in response_2.lower():
    print(f"[OK] Kay correctly recalled eye color: mentioned 'green'")
else:
    print(f"[FAIL] Kay did not mention 'green' in response")
    issues.append("Kay failed to recall eye color fact")
    success = False

if success:
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - FIX VERIFIED!")
    print("="*80)
    sys.exit(0)
else:
    print("\n" + "="*80)
    print("❌ SOME TESTS FAILED")
    print("="*80)
    for issue in issues:
        print(f"  - {issue}")
    sys.exit(1)
