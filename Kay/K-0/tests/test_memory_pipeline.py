"""
Test to verify all retrieved memories (especially identity facts) make it to the LLM prompt.

Expected flow:
1. [RECALL CHECKPOINT 1] After retrieval: ~498 memories
2. [RECALL CHECKPOINT 2] Before storage: ~498 memories (NO TRUNCATION)
3. [BYPASS CHECKPOINT 1] Retrieved directly: ~498 memories
4. [BYPASS CHECKPOINT 2] Identity facts: ~364
5. [BYPASS CHECKPOINT 3] Memories in filtered_context: ~498
6. [LLM PROMPT CHECKPOINT 1] Memories in context: ~498
7. [LLM PROMPT CHECKPOINT 2] Identity facts in context: ~364
8. [LLM PROMPT CHECKPOINT 3] Split by perspective
9. [LLM PROMPT CHECKPOINT 4-6 - FINAL] Prompt analysis (bullet points)

If any checkpoint shows < 498 memories, that's where the bug is.
"""

import sys
import os

# Suppress normal output to focus on checkpoints
os.environ['PYTHONUNBUFFERED'] = '1'

print("\n" + "="*80)
print("MEMORY PIPELINE TEST")
print("="*80)
print("\nThis test will trace memory count through the entire pipeline:")
print("  Retrieval -> State Storage -> Bypass -> Context Building -> LLM Prompt")
print("\nLook for CHECKPOINT logs to verify all ~498 memories reach the LLM.\n")
print("="*80 + "\n")

# Simulate a simple conversation turn
user_input = "Tell me about Re's eyes"

print(f"USER INPUT: {user_input}\n")
print("Starting Kay...\n")

# Run main.py with the test input
import subprocess
result = subprocess.run(
    ["python", "main.py"],
    input=f"{user_input}\nquit\n",
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore'
)

print("\n" + "="*80)
print("CHECKPOINT SUMMARY")
print("="*80 + "\n")

# Extract checkpoint logs
lines = result.stdout.split('\n') + result.stderr.split('\n')

checkpoints = [
    "RECALL CHECKPOINT",
    "BYPASS CHECKPOINT",
    "LLM PROMPT CHECKPOINT"
]

for checkpoint_name in checkpoints:
    print(f"\n--- {checkpoint_name} ---")
    found = False
    for line in lines:
        if checkpoint_name in line:
            print(line)
            found = True
    if not found:
        print(f"  [WARNING] No {checkpoint_name} logs found!")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

# Check for the critical counts
recall_1 = None
recall_2 = None
bypass_1 = None
bypass_2 = None
bypass_3 = None
prompt_1 = None
prompt_2 = None
prompt_6 = None

for line in lines:
    if "RECALL CHECKPOINT 1" in line and "After retrieval:" in line:
        try:
            recall_1 = int(line.split("After retrieval:")[1].split("memories")[0].strip())
        except:
            pass
    elif "RECALL CHECKPOINT 2" in line and "Before storage" in line:
        try:
            recall_2 = int(line.split("Before storage in state:")[1].split("memories")[0].strip())
        except:
            pass
    elif "BYPASS CHECKPOINT 1" in line and "Retrieved" in line:
        try:
            bypass_1 = int(line.split("Retrieved")[1].split("memories")[0].strip())
        except:
            pass
    elif "BYPASS CHECKPOINT 2" in line and "Identity facts" in line:
        try:
            bypass_2 = int(line.split("Identity facts in selected memories:")[1].strip())
        except:
            pass
    elif "BYPASS CHECKPOINT 3" in line and "Memories in filtered_context:" in line:
        try:
            bypass_3 = int(line.split("Memories in filtered_context:")[1].strip())
        except:
            pass
    elif "LLM PROMPT CHECKPOINT 1" in line and "Memories in context:" in line:
        try:
            prompt_1 = int(line.split("Memories in context:")[1].strip())
        except:
            pass
    elif "LLM PROMPT CHECKPOINT 2" in line and "Identity facts in context:" in line:
        try:
            prompt_2 = int(line.split("Identity facts in context:")[1].strip())
        except:
            pass
    elif "LLM PROMPT CHECKPOINT 6" in line and "Bullet points in prompt:" in line:
        try:
            prompt_6 = int(line.split("Bullet points in prompt:")[1].strip())
        except:
            pass

print(f"\nMemory count at each stage:")
print(f"  1. After retrieval (recall):         {recall_1 if recall_1 else 'NOT FOUND'}")
print(f"  2. Before state storage (recall):    {recall_2 if recall_2 else 'NOT FOUND'}")
print(f"  3. Retrieved from state (bypass):    {bypass_1 if bypass_1 else 'NOT FOUND'}")
print(f"  4. Identity facts (bypass):          {bypass_2 if bypass_2 else 'NOT FOUND'}")
print(f"  5. In filtered_context (bypass):     {bypass_3 if bypass_3 else 'NOT FOUND'}")
print(f"  6. In context dict (prompt):         {prompt_1 if prompt_1 else 'NOT FOUND'}")
print(f"  7. Identity facts (prompt):          {prompt_2 if prompt_2 else 'NOT FOUND'}")
print(f"  8. Bullet points in final prompt:    {prompt_6 if prompt_6 else 'NOT FOUND'}")

# Determine if bug is fixed
if all([recall_1, recall_2, bypass_1, bypass_3, prompt_1]):
    if recall_1 == recall_2 == bypass_1 == bypass_3 == prompt_1:
        print("\n[SUCCESS] All memories preserved throughout pipeline!")
        print(f"   {recall_1} memories retrieved -> {prompt_1} memories in final prompt")

        if prompt_2 and prompt_2 > 0:
            print(f"   {prompt_2} identity facts included")

        if prompt_6:
            print(f"   {prompt_6} bullet points rendered in prompt text")

        sys.exit(0)
    else:
        print("\n[FAILURE] Memories lost somewhere in pipeline:")
        if recall_1 != recall_2:
            print(f"   Lost between retrieval and state storage: {recall_1} -> {recall_2}")
        if recall_2 != bypass_1:
            print(f"   Lost between state storage and bypass: {recall_2} -> {bypass_1}")
        if bypass_1 != bypass_3:
            print(f"   Lost between bypass and filtered_context: {bypass_1} -> {bypass_3}")
        if bypass_3 != prompt_1:
            print(f"   Lost between filtered_context and prompt build: {bypass_3} -> {prompt_1}")
        sys.exit(1)
else:
    print("\n[WARNING] Could not extract all checkpoint data from logs")
    print("   Check if main.py ran successfully")
    sys.exit(1)
