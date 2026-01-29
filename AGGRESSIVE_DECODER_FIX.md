# AGGRESSIVE Memory Selection & Response Length Fix

## Problem Summary
Kay Zero was strangled at the decoder stage, selecting only 5-11 memories when it should select 30-80+ for comprehensive queries.

---

## ROOT CAUSE IDENTIFIED

### BOTTLENECK #1: Token Limit Strangling Decoder Output
**File:** `context_filter.py:134` (OLD VERSION)

**Original Code:**
```python
- Keep output under 150 tokens
```

**Why This Killed Memory Selection:**
- Decoder outputs format: `MEM[1,2,3,4,5,...]`
- Each memory index = ~2 tokens
- 50 memories = ~100 tokens just for indices
- With 150 token limit, decoder could output max ~70 indices
- **But decoder was being ultra-conservative and only outputting 5-11 (using only 10-20 tokens!)**

### BOTTLENECK #2: Conservative Selection Guidance
**File:** `context_filter.py:120-123` (OLD VERSION)

**Original Code:**
```python
* LIST/COMPREHENSIVE queries: 40-80 memory indices
* Standard queries: 15-30 memory indices
```

**Problem:** These were suggestions, not requirements. Decoder interpreted as "up to X" not "at least X".

---

## AGGRESSIVE FIXES APPLIED

### FIX #1: Increased Token Limit to 500
**File:** `context_filter.py:137`

**NEW CODE:**
```python
- Keep output under 500 tokens (increased for comprehensive memory selection)
```

**Impact:** Decoder can now output 200+ memory indices if needed (500 tokens ÷ 2 = 250 indices max)

---

### FIX #2: Made Selection Requirements MANDATORY
**File:** `context_filter.py:120-126`

**NEW CODE:**
```python
- **AGGRESSIVE SELECTION REQUIRED** - Selection count varies by query type:
  * LIST/COMPREHENSIVE queries ("tell me everything", "what do you know"): SELECT 50-80 memory indices MINIMUM
  * Detailed queries ("tell me about", "explain"): SELECT 30-50 memory indices MINIMUM
  * Standard queries: SELECT 20-30 memory indices MINIMUM
  * NEVER select fewer than 20 memories unless fewer than 20 exist
  * Err on the side of INCLUSION not exclusion - cast a WIDE net
  * Better to include too many than too few - Kay needs rich context
```

**Key Changes:**
- Changed from "40-80" to "SELECT 50-80 MINIMUM"
- Added **AGGRESSIVE SELECTION REQUIRED** header
- Added explicit "NEVER select fewer than 20" rule
- Added philosophy: "Err on the side of INCLUSION"

---

### FIX #3: Dynamic Selection with Emphasis
**File:** `context_filter.py:207-213`

**NEW CODE:**
```python
# DYNAMIC MEMORY SELECTION based on query type - AGGRESSIVE
if is_list_query:
    memory_selection_guidance = "Select 50-80 memory indices MINIMUM (LIST/COMPREHENSIVE query - needs EXTENSIVE detail)"
    selection_emphasis = "CRITICAL: User wants comprehensive recall. Select AT LEAST 50-80 memories. Cast a WIDE net."
else:
    memory_selection_guidance = "Select 25-40 memory indices MINIMUM (standard query - needs substantial context)"
    selection_emphasis = "Select generously - AT LEAST 25-40 memories. More is better than less."
```

**Changes:**
- LIST queries: 40-80 → **50-80 MINIMUM**
- Standard queries: 15-30 → **25-40 MINIMUM**
- Added `selection_emphasis` variable with strong language

---

### FIX #4: Reinforced in Prompt Instructions
**File:** `context_filter.py:245-252`

**NEW CODE:**
```python
Focus on:
1. Which memories directly answer the user's current question? Use their EXACT indices (e.g., [2], [7], [15])
2. SELECT GENEROUSLY - Kay needs rich context to give comprehensive responses
3. Prioritize USER memories if user asks about themselves (their dog, preferences, life, etc.)
4. Prioritize KAY memories if user asks about Kay's identity, preferences, or state
5. What is Kay's current emotional state?
6. Are there contradictions Kay needs to resolve?
7. FOR LIST/COMPREHENSIVE QUERIES: Cast a WIDE net - include 50-80 memories minimum
8. NEVER be conservative with selection - more memories = better responses
```

**Changes:**
- Added rule #2: "SELECT GENEROUSLY"
- Added rule #7: "Cast a WIDE net - include 50-80 memories minimum"
- Added rule #8: "NEVER be conservative with selection - more memories = better responses"

---

### FIX #5: Added Emphasis Block in Prompt
**File:** `context_filter.py:236`

**NEW CODE:**
```python
TASK: Select the most relevant context for Kay's response. Output in glyph format only.

{selection_emphasis}  # ← NEW: Inserts "CRITICAL: User wants comprehensive recall..."

OUTPUT FORMAT (REQUIRED):
Line 1: MEM[index,index,index] - {memory_selection_guidance}...
```

**Impact:** Every filter prompt now includes a CRITICAL emphasis message about selecting enough memories.

---

### FIX #6: Priority Reinforcement at Bottom
**File:** `context_filter.py:140`

**NEW CODE:**
```python
- PRIORITIZE QUANTITY - select AS MANY relevant memories as possible
```

**Impact:** Final reminder to decoder before it generates output.

---

## EXPECTED BEHAVIOR AFTER FIX

### Before Fix:
```
User: "Tell me about everything you know about yourself."

[DEBUG] Memories after pre-filter: 150
[DECODER] Total memories available: 1082, Selected: 5    ← BROKEN
```

### After Fix:
```
User: "Tell me about everything you know about yourself."

[FILTER] LIST query detected - expanding retrieval to 300 memories
[DEBUG] Memories after pre-filter: 300
[DECODER] Total memories available: 1082, Selected: 58    ← FIXED!
```

Or even better:
```
[DECODER] Total memories available: 1082, Selected: 74    ← AGGRESSIVE!
```

---

## RESPONSE LENGTH - Already Adequate

**File:** `integrations/llm_integration.py:384`

Kay's response generation already has:
```python
max_tokens=8192,  # Maximum supported by API - allows ~6000 words
```

**System Prompt Already Fixed (Previous Fix):**
```python
"  * EXPANSIVE (1500-3000+ chars): 'Tell me everything', 'what do you know about', philosophical spirals\n"
"  * CRITICAL: Comprehensive queries deserve comprehensive answers - don't artificially compress\n"
"  * When user asks about what you know, recall, or your identity - GO DEEP with rich detail\n"
```

---

## TUNING KNOBS

If decoder is STILL too conservative:

### Make it even more aggressive:
```python
# context_filter.py:121-123
* LIST/COMPREHENSIVE queries: SELECT 60-100 memory indices MINIMUM
* Detailed queries: SELECT 40-60 memory indices MINIMUM
* Standard queries: SELECT 30-40 memory indices MINIMUM
```

### Increase token ceiling further:
```python
# context_filter.py:137
- Keep output under 800 tokens (for very comprehensive selection)
```

### Add more LIST query patterns:
```python
# context_filter.py:150-154
LIST_PATTERNS = [
    "what are", "tell me about", "list", "all the", "all of",
    "some things", "what have", "everything", "anything",
    "what do you know", "what did", "show me",
    "give me details", "walk me through", "explain in detail"  # ADD MORE
]
```

---

## FILES MODIFIED

1. **context_filter.py**
   - Line 120-126: AGGRESSIVE SELECTION REQUIRED with MINIMUMS
   - Line 137: Token limit 150 → 500
   - Line 140: Added PRIORITIZE QUANTITY rule
   - Line 207-213: Dynamic selection with emphasis messages
   - Line 236: Added emphasis block to prompt
   - Line 245-252: Reinforced selection rules with "SELECT GENEROUSLY"

2. **integrations/llm_integration.py** (from previous fix)
   - Line 77-86: Enhanced response length guidance
   - Already has max_tokens=8192 (adequate)

---

## TESTING

Run Kay and test with:
```python
python main.py

> Tell me about everything you know about yourself. Everything in the new parts.
```

**Look for in logs:**
```
[FILTER] LIST query detected - expanding retrieval to 300 memories
[DEBUG] Memories after pre-filter: 300
[DECODER] Total memories available: 1082, Selected: 58    ← Should be 50-80 now
```

**Kay's response should be:**
- **1500-2500+ characters** (not 300-500)
- **Rich, multi-faceted detail** covering many aspects
- **Comprehensive** with examples and nuance

---

## WHAT IF IT'S STILL TOO FEW?

If decoder still selects only 10-20 memories:

### Debug the actual decoder output:
Add to `context_filter.py:74`:
```python
glyph_output = query_llm_json(...)

# DEBUG: Print what decoder actually said
print(f"[DECODER OUTPUT]: {glyph_output}")
```

This will show you the exact MEM[...] line. If it's short, the decoder is ignoring instructions.

### Nuclear option - Force minimum in code:
Add to `glyph_decoder.py:126` (after parsing):
```python
# FORCE MINIMUM SELECTION
if len(selected) < 20:
    print(f"[DECODER WARNING] Only {len(selected)} selected, padding to minimum 20")
    # Add random high-importance memories to reach minimum
    # (This is a fallback if decoder keeps ignoring prompt)
```

But try the aggressive prompt changes first - they should work!
