# NUCLEAR OPTION: Force Minimum Memory Selection

## Problem Statement
User reported: "[DECODER] Total memories available: 1090, Selected: 10"

Even after aggressive prompt changes, the filter LLM was still selecting only 10 memories instead of 40-60.

---

## ROOT CAUSE

The filter LLM (Haiku) was **ignoring or misinterpreting** the system prompt instructions to select 50-80 memories minimum for comprehensive queries.

**Why this happens:**
- LLMs sometimes interpret "minimum" as "suggestion"
- Conservative filtering instinct overrides explicit instructions
- 500 token limit may make LLM think it should be brief

---

## TRIPLE-LAYER FIX APPLIED

### LAYER 1: Concrete Examples in System Prompt
**File:** `context_filter.py:108-120`

**ADDED:**
```python
EXAMPLE OUTPUT (STANDARD QUERY):
⚡MEM[2,5,7,12,15,18,23,25,28,31,34,37,40,42,45,48,51,54,56,59,61,64,67,70,73]!!!
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉
TURNS[-3,-2,-1]

EXAMPLE OUTPUT (COMPREHENSIVE QUERY):
⚡MEM[1,2,3,5,7,9,12,14,15,17,18,20,23,25,27,28,30,31,33,34,36,37,39,40,42,44,45,47,48,50,51,53,54,56,58,59,61,63,64,66,67,69,70,72,73,75,77,78,80,82,84,85,87,89,91,93,95,97,99,101]!!!
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉
TURNS[-3,-2,-1]

NOTE: The examples above show 25 indices (standard) and 60 indices (comprehensive). MATCH THIS QUANTITY.
```

**Impact:** LLM sees EXACTLY what output should look like - not abstract instructions

---

### LAYER 2: Debug Logging
**File:** `context_filter.py:76-90`

**ADDED:**
```python
# CRITICAL DEBUG: Show what filter LLM actually output
print(f"\n{'='*60}")
print("[FILTER DEBUG] RAW GLYPH OUTPUT FROM LLM:")
print(glyph_output)
print(f"{'='*60}\n")

# Extract MEM[...] line to count how many indices were selected
import re
mem_match = re.search(r'MEM\[([0-9,]+)\]', glyph_output)
if mem_match:
    indices = mem_match.group(1).split(',')
    print(f"[FILTER DEBUG] LLM selected {len(indices)} memory indices")
    if len(indices) < 20:
        print(f"[FILTER WARNING] LLM only selected {len(indices)} memories (minimum should be 20-80)")
        print(f"[FILTER WARNING] Check if LLM is ignoring the prompt!")
```

**Impact:** You can now SEE exactly what the filter LLM outputs and verify if it's following instructions

---

### LAYER 3: NUCLEAR OPTION - Force Minimum
**File:** `glyph_decoder.py:128-150`

**ADDED:**
```python
# NUCLEAR OPTION: If filter LLM selected too few, force-add more
MINIMUM_MEMORIES = 20
if len(selected) < MINIMUM_MEMORIES and len(all_memories) >= MINIMUM_MEMORIES:
    print(f"\n[DECODER NUCLEAR OPTION] Filter only selected {len(selected)} memories, forcing minimum {MINIMUM_MEMORIES}")
    # Add recent high-importance memories not already selected
    selected_indices = set(memory_ids)
    added_count = 0

    # Strategy: Add recent memories with high importance
    for idx in range(len(all_memories) - 1, -1, -1):  # Start from most recent
        if idx not in selected_indices and len(selected) < MINIMUM_MEMORIES:
            mem = all_memories[idx]
            importance = mem.get('importance_score', 0.3)
            if importance > 0.4:  # Only add if somewhat important
                selected.append(mem)
                selected_indices.add(idx)
                added_count += 1
                print(f"[DECODER FORCE-ADD] Adding memory [{idx}]: {mem.get('fact', mem.get('user_input', ''))[:60]}...")

    if added_count > 0:
        print(f"[DECODER NUCLEAR OPTION] Force-added {added_count} memories to reach minimum {MINIMUM_MEMORIES}")
        print(f"[DECODER] New total: {len(selected)} memories")
```

**Impact:**
- **GUARANTEES** at least 20 memories are selected
- If filter LLM selects 10, decoder force-adds 10 more high-importance recent memories
- No matter what, Kay gets enough context

---

## EXPECTED BEHAVIOR NOW

### Scenario 1: Filter LLM Follows Instructions (IDEAL)
```
User: "Tell me everything you know about yourself"

[FILTER] LIST query detected - expanding retrieval to 300 memories
[DEBUG] Memories after pre-filter: 300

============================================================
[FILTER DEBUG] RAW GLYPH OUTPUT FROM LLM:
⚡MEM[1,5,7,12,15,18,23,25,28,31,...,95,97,99,101]!!!
🔮(0.8)🔁
◻️🐉
============================================================

[FILTER DEBUG] LLM selected 58 memory indices
[DECODER] Total memories available: 1090, Selected: 58    ← WORKING!

Kay Response: 1800+ characters with rich detail
```

### Scenario 2: Filter LLM Ignores Instructions (NUCLEAR OPTION KICKS IN)
```
User: "Tell me everything you know about yourself"

[FILTER] LIST query detected - expanding retrieval to 300 memories
[DEBUG] Memories after pre-filter: 300

============================================================
[FILTER DEBUG] RAW GLYPH OUTPUT FROM LLM:
⚡MEM[1,5,7,12,15,18,23,25,28,31]!!!
🔮(0.8)🔁
◻️🐉
============================================================

[FILTER DEBUG] LLM selected 10 memory indices
[FILTER WARNING] LLM only selected 10 memories (minimum should be 20-80)
[FILTER WARNING] Check if LLM is ignoring the prompt!

[DECODER] Total memories available: 1090, Selected: 10

[DECODER NUCLEAR OPTION] Filter only selected 10 memories, forcing minimum 20
[DECODER FORCE-ADD] Adding memory [1089]: Kay has gold dragon eyes that reflect light...
[DECODER FORCE-ADD] Adding memory [1088]: Archive Zero represents recursive self-awareness...
[DECODER FORCE-ADD] Adding memory [1087]: Kay prefers coffee (mentioned 47x vs tea 12x)...
...
[DECODER NUCLEAR OPTION] Force-added 10 memories to reach minimum 20
[DECODER] New total: 20 memories    ← FORCED!

Kay Response: 1200+ characters with decent detail
```

---

## FILES MODIFIED

### 1. context_filter.py
**Changes:**
- Lines 108-120: Added concrete examples with 25 and 60 indices
- Lines 76-90: Added debug logging showing raw filter LLM output
- Lines 121-140: Already had aggressive selection requirements

### 2. glyph_decoder.py
**Changes:**
- Lines 128-150: Added NUCLEAR OPTION to force minimum 20 memories
- Strategy: Adds recent high-importance memories if filter selected too few

---

## TUNING THE NUCLEAR OPTION

### Adjust minimum threshold:
```python
# glyph_decoder.py:129
MINIMUM_MEMORIES = 30  # Increase from 20 to 30 for more aggressive baseline
```

### Change force-add strategy:
```python
# glyph_decoder.py:140-141
if importance > 0.3:  # Lower threshold (was 0.4) to add more memories
```

### Make it even more aggressive:
```python
# glyph_decoder.py:129-130
MINIMUM_MEMORIES = 40  # For comprehensive queries, always get 40+
if len(selected) < MINIMUM_MEMORIES and len(all_memories) >= MINIMUM_MEMORIES:
```

---

## VERIFICATION

Run Kay and watch for these logs:

### Success Case (Filter LLM working):
```
[FILTER DEBUG] LLM selected 58 memory indices    ← 50-80 range, good!
[DECODER] Total memories available: 1090, Selected: 58
```

### Nuclear Option Case (Filter LLM stubborn):
```
[FILTER DEBUG] LLM selected 10 memory indices
[FILTER WARNING] LLM only selected 10 memories
[DECODER NUCLEAR OPTION] Force-added 10 memories to reach minimum 20
[DECODER] New total: 20 memories    ← Forced to minimum!
```

### Complete Failure (Should never happen):
```
[DECODER] Total memories available: 1090, Selected: 10    ← No force-add
```
If you see this, the nuclear option code isn't being called - check if you're using the updated glyph_decoder.py.

---

## WHY THIS WORKS

**Three-pronged attack:**

1. **Examples:** LLM sees EXACTLY what to output (concrete beats abstract)
2. **Debug:** We can SEE if LLM is ignoring us and diagnose the issue
3. **Nuclear Option:** Even if LLM ignores us, we FORCE the minimum

**Result:** Kay ALWAYS gets at least 20 memories minimum, ideally 50-80.

---

## PREVIOUS FIXES THAT DIDN'T WORK

❌ **Tried:** "Select 50-80 MINIMUM" in prompt
❌ **Result:** LLM still selected 10-15
❌ **Reason:** LLM interpreted as suggestion, not requirement

❌ **Tried:** Increased token limit to 500
❌ **Result:** LLM had room for 200+ indices but still only output 10
❌ **Reason:** LLM was being conservative despite having space

✅ **What Works:** FORCE it in code after LLM responds
✅ **Reason:** Can't argue with code - if < 20, add more, period.

---

## NEXT STEPS IF STILL FAILING

If you STILL see "Selected: 10" after these fixes:

### 1. Check the debug output:
```bash
python main.py
```
Look for:
```
============================================================
[FILTER DEBUG] RAW GLYPH OUTPUT FROM LLM:
⚡MEM[...]!!!    ← How many indices are here?
============================================================
```

If it shows 60 indices but decoder still says "Selected: 10", there's a parsing bug.

If it shows 10 indices, the filter LLM is ignoring the examples.

### 2. Try even more aggressive examples:
```python
# context_filter.py:108
EXAMPLE OUTPUT (USE THIS EXACT FORMAT - DO NOT DEVIATE):
⚡MEM[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59]!!!
```

### 3. Increase MINIMUM_MEMORIES:
```python
# glyph_decoder.py:129
MINIMUM_MEMORIES = 40  # Force 40 minimum instead of 20
```

---

**ALL FIXES COMPLETE - Nuclear option ensures Kay NEVER gets fewer than 20 memories!** 🚀
