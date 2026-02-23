# Relevance-Weighted Memory Boost - Implementation Plan

## PROBLEM IDENTIFIED ✅

### Current Broken Behavior (Confirmed)

**File**: `engines/emotion_engine.py` lines 208-220

**Code**:
```python
# --- 3. reinforce via memory ---
memory_count = len(agent_state.last_recalled_memories or [])
reinforced_emotions = []
for mem in agent_state.last_recalled_memories or []:  # ❌ ALL memories
    for tag in mem.get("emotion_tags", []):
        if tag in cocktail:
            old_intensity = cocktail[tag]["intensity"]
            cocktail[tag]["intensity"] = min(1.0,
                cocktail[tag]["intensity"] + 0.05)  # ❌ Equal boost
```

**Problems**:
1. ❌ ALL ~310 retrieved memories boost emotions equally
2. ❌ "Re has green eyes" (relevance 0.05) boosts curiosity same as "I wonder how..." (relevance 0.95)
3. ❌ Decay (-0.05) gets canceled by indiscriminate boost (+0.05 × 310 memories)
4. ❌ Result: Emotions frozen at high intensity, no decay

---

## SOLUTION ARCHITECTURE

### A. Add Relevance Scores to Memories

**File**: `engines/memory_engine.py`

**Location**: Line 1489-1516 in `add_unique_memories()` helper function

**Current Code** (line 1504):
```python
retrieved.append(mem)  # ❌ Score is lost!
```

**Fixed Code**:
```python
# Store relevance score in memory for emotion weighting
mem['relevance_score'] = score  # ✅ Preserve score
retrieved.append(mem)
```

**Why This Location**:
- Line 1420: Scores calculated: `scored = [calculate_multi_factor_score(m) for m in ...]`
- Line 1444-1472: Scored tuples `(score, mem)` categorized into candidate lists
- Line 1493: `add_unique_memories(candidates, ...)` receives `(score, mem)` tuples
- Line 1504: **This is where score is discarded** - we'll preserve it here

---

### B. Implement Relevance-Weighted Boost

**File**: `engines/emotion_engine.py`

**Location**: Lines 208-220

**BEFORE (Current Broken Code)**:
```python
# --- 3. reinforce via memory ---
memory_count = len(agent_state.last_recalled_memories or [])
reinforced_emotions = []
for mem in agent_state.last_recalled_memories or []:
    for tag in mem.get("emotion_tags", []):
        if tag in cocktail:
            old_intensity = cocktail[tag]["intensity"]
            cocktail[tag]["intensity"] = min(1.0,
                cocktail[tag]["intensity"] + 0.05)
            if tag not in reinforced_emotions:
                reinforced_emotions.append(tag)
                print(f"[EMOTION ENGINE] Memory boost: {tag} from {old_intensity:.2f} to {cocktail[tag]['intensity']:.2f}")

print(f"[EMOTION ENGINE] Processed {memory_count} memories, reinforced {len(reinforced_emotions)} emotions")
```

**AFTER (Relevance-Weighted Code)**:
```python
# --- 3. reinforce via memory (RELEVANCE-WEIGHTED) ---
all_memories = agent_state.last_recalled_memories or []

# STEP 1: Sort by relevance and take top N most relevant
relevant_memories = sorted(
    all_memories,
    key=lambda m: m.get('relevance_score', 0),
    reverse=True
)[:150]  # Top 150 memories only (was: all 310)

print(f"[EMOTION ENGINE] Memory reinforcement: using top {len(relevant_memories)}/{len(all_memories)} most relevant memories")

# STEP 2: Boost emotions weighted by relevance
reinforced_emotions = {}  # Track {emotion: total_boost}
relevance_threshold = 0.15  # Only boost from relevant memories (15% minimum)
memories_used = 0

for mem in relevant_memories:
    relevance = mem.get('relevance_score', 0)

    # Skip very low relevance memories
    if relevance < relevance_threshold:
        continue

    memories_used += 1

    # Calculate boost amount scaled by relevance
    # Base boost = 0.05, but scaled by how relevant this memory is
    # Example: relevance=0.9 → boost=0.045, relevance=0.2 → boost=0.010
    boost_amount = 0.05 * relevance

    for tag in mem.get("emotion_tags", []):
        if tag in cocktail:
            old_intensity = cocktail[tag]["intensity"]
            cocktail[tag]["intensity"] = min(1.0,
                cocktail[tag]["intensity"] + boost_amount)

            # Track total boost for logging
            if tag not in reinforced_emotions:
                reinforced_emotions[tag] = boost_amount
            else:
                reinforced_emotions[tag] += boost_amount

# STEP 3: Enhanced logging
if reinforced_emotions:
    print(f"[EMOTION ENGINE] Reinforced {len(reinforced_emotions)} emotions from {memories_used} relevant memories:")
    for emotion, total_boost in sorted(reinforced_emotions.items(),
                                       key=lambda x: x[1], reverse=True):
        final_intensity = cocktail[emotion]["intensity"]
        print(f"[EMOTION ENGINE]   - {emotion}: +{total_boost:.3f} boost → intensity={final_intensity:.2f}")
else:
    print(f"[EMOTION ENGINE] No emotions reinforced (no relevant memories above threshold)")

print(f"[EMOTION ENGINE] Used {memories_used}/{len(all_memories)} memories (relevance ≥ {relevance_threshold:.2f})")
```

---

### C. Add Relevance Score Logging

**File**: `engines/memory_engine.py`

**Location**: After line 1430 (after sorting scored memories)

**Add**:
```python
# Sort by score
scored.sort(key=lambda x: x[0], reverse=True)

# === RELEVANCE SCORE LOGGING ===
if scored:
    print(f"\n[MEMORY RETRIEVAL] Top 10 most relevant memories:")
    for i, (score, mem) in enumerate(scored[:10]):
        mem_type = mem.get('type', 'unknown')

        # Extract preview based on memory type
        if mem_type == 'full_turn' or mem_type == 'structured_turn':
            preview = mem.get('user_input', '')[:60]
        elif mem_type == 'extracted_fact':
            preview = mem.get('fact', '')[:60]
        else:
            preview = str(mem.get('text', ''))[:60]

        emotions = mem.get('emotion_tags', [])
        layer = mem.get('current_layer', 'unknown')

        print(f"[MEMORY RETRIEVAL]   #{i+1}: score={score:.3f}, layer={layer}, "
              f"emotions={emotions}, preview='{preview}...'")
    print()
```

---

## EXPECTED BEHAVIOR CHANGE

### BEFORE Fix (Current Broken Behavior):

```
[EMOTION ENGINE] Processed 310 memories, reinforced 8 emotions
[EMOTION ENGINE] Memory boost: curiosity from 0.95 to 1.00

Turn 1: curiosity intensity=1.00, age=2
Turn 2: curiosity intensity=1.00, age=4  ❌ No decay (boost canceled it)
Turn 3: curiosity intensity=1.00, age=6  ❌ Still frozen
```

**Problem**: 310 memories × 0.05 boost = massive reinforcement canceling decay

---

### AFTER Fix (Relevance-Weighted):

```
[MEMORY RETRIEVAL] Top 10 most relevant memories:
[MEMORY RETRIEVAL]   #1: score=0.892, emotions=['curiosity'], preview='I wonder how the memory system works internally...'
[MEMORY RETRIEVAL]   #2: score=0.745, emotions=['curiosity'], preview='How does the wrapper handle exceptions?...'
[MEMORY RETRIEVAL]   #3: score=0.623, emotions=['affection'], preview='I miss Sammie so much today...'
...

[EMOTION ENGINE] Memory reinforcement: using top 150/310 most relevant memories
[EMOTION ENGINE] Reinforced 3 emotions from 45 relevant memories:
[EMOTION ENGINE]   - curiosity: +0.180 boost → intensity=0.93
[EMOTION ENGINE]   - affection: +0.085 boost → intensity=0.52
[EMOTION ENGINE]   - concern: +0.042 boost → intensity=0.38
[EMOTION ENGINE] Used 45/310 memories (relevance ≥ 0.15)

Turn 1: curiosity intensity=0.95, age=2
Turn 2: curiosity intensity=0.93, age=4  ✅ Decaying! (boost < decay for once)
Turn 3: curiosity intensity=0.91, age=6  ✅ Continues decaying
```

**Fix Applied**:
- Only 45 memories (not 310) contributed to boost
- Boost weighted by relevance (0.180 total, not 15.5 from 310 × 0.05)
- Decay now visible because boost is proportional to actual relevance

---

## IMPLEMENTATION STEPS

### Step 1: Store Relevance Scores ✅

**File**: `engines/memory_engine.py` line 1504

```python
# Before adding memory to retrieved, store its score
mem['relevance_score'] = score  # ADD THIS LINE
retrieved.append(mem)
```

**Verification**: Print first memory's score after retrieval:
```python
if retrieved:
    print(f"[DEBUG] Sample relevance_score: {retrieved[0].get('relevance_score', 'MISSING')}")
```

Expected output: `[DEBUG] Sample relevance_score: 0.892`

---

### Step 2: Implement Relevance-Weighted Boost ✅

**File**: `engines/emotion_engine.py` lines 208-220

Replace entire memory reinforcement section with relevance-weighted version (see code above).

**Verification**: Send message "I wonder how this works"
- Should see: `Used 30-50/310 memories` (not all 310)
- Should see: Individual boost amounts per emotion
- Should see: Total boost < 1.0 (not massive)

---

### Step 3: Add Relevance Logging ✅

**File**: `engines/memory_engine.py` after line 1430

Add logging showing top 10 most relevant memories (see code above).

**Verification**: Check terminal for `[MEMORY RETRIEVAL] Top 10 most relevant memories:`

---

### Step 4: Test Decay Works ✅

**Test Sequence**:
```
Turn 1: "I'm curious about something"  → curiosity=0.70
Turn 2: "Okay, I see"                   → curiosity should decay to ~0.66
Turn 3: "Okay, I see"                   → curiosity should decay to ~0.62
Turn 4: "Okay, I see"                   → curiosity should decay to ~0.59
```

**Expected Logs**:
```
Turn 2:
[EMOTION ENGINE] Aged curiosity: 0.700 -> 0.665 (age 1, decay=0.050)
[EMOTION ENGINE] Used 8/310 memories (relevance ≥ 0.15)
[EMOTION ENGINE] Final: curiosity=0.665  ✅ DECAY VISIBLE

Turn 3:
[EMOTION ENGINE] Aged curiosity: 0.665 -> 0.615 (age 2, decay=0.050)
[EMOTION ENGINE] Final: curiosity=0.615  ✅ CONTINUES DECAYING
```

---

## TUNING PARAMETERS

### If Boost Too Strong:

```python
# Reduce base boost
boost_amount = 0.03 * relevance  # Was: 0.05

# Increase relevance threshold
relevance_threshold = 0.25  # Was: 0.15

# Reduce top N memories
relevant_memories = sorted(...)[:100]  # Was: 150
```

### If Boost Too Weak:

```python
# Increase base boost
boost_amount = 0.07 * relevance  # Was: 0.05

# Decrease relevance threshold
relevance_threshold = 0.10  # Was: 0.15

# Increase top N memories
relevant_memories = sorted(...)[:200]  # Was: 150
```

### Alternative Scaling Formulas:

```python
# Quadratic (emphasizes high relevance more):
boost_amount = 0.05 * (relevance ** 2)

# Threshold-based (only boost above 0.3):
boost_amount = 0.05 * max(0, relevance - 0.3)

# Exponential (strong for very relevant, weak for moderately relevant):
boost_amount = 0.05 * (relevance ** 1.5)
```

---

## TESTING CHECKLIST

### Test 1: Relevance Scores Exist ✅
- [ ] Start Kay, send message
- [ ] Check logs for `[DEBUG] Sample relevance_score: 0.XXX`
- [ ] If "MISSING", fix not applied to memory_engine.py

### Test 2: Relevance-Weighted Boost Working ✅
- [ ] Check logs for `Used XX/310 memories (relevance ≥ 0.15)`
- [ ] Verify XX is much less than 310 (should be 30-80)
- [ ] Check individual boost amounts are < 0.1

### Test 3: Decay Now Works ✅
- [ ] Send emotional message (trigger curiosity)
- [ ] Send 3 neutral messages ("Okay, I see")
- [ ] Verify curiosity intensity DECREASES each turn
- [ ] If frozen at same value, boost still too strong

### Test 4: High Relevance Boosts More ✅
- [ ] Send "I wonder how the memory system works"
- [ ] Check top 10 most relevant memories
- [ ] Verify memories about memory system have high scores (>0.7)
- [ ] Verify unrelated memories have low scores (<0.2)

### Test 5: Low Relevance Ignored ✅
- [ ] Send message about specific topic (e.g., "Tell me about Sammie")
- [ ] Check logs for memories used
- [ ] Verify unrelated memories (relevance <0.15) not used
- [ ] Verify only Sammie-related memories contributed boost

---

## SUCCESS CRITERIA

You'll know the fix worked when you see:

✅ **Relevance Scores Present**:
```
[DEBUG] Sample relevance_score: 0.892
```

✅ **Selective Memory Usage**:
```
[EMOTION ENGINE] Used 42/310 memories (relevance ≥ 0.15)
```

✅ **Weighted Boost Amounts**:
```
[EMOTION ENGINE]   - curiosity: +0.185 boost → intensity=0.93
[EMOTION ENGINE]   - concern: +0.047 boost → intensity=0.38
```

✅ **Decay Actually Works**:
```
Turn 1: curiosity=0.95
Turn 2: curiosity=0.93  ✅ Decreased
Turn 3: curiosity=0.91  ✅ Continues decreasing
```

✅ **Top Memories Are Relevant**:
```
[MEMORY RETRIEVAL]   #1: score=0.892, preview='I wonder how the memory system works...'
[MEMORY RETRIEVAL]   #2: score=0.745, preview='How does the wrapper handle...'
```

---

## ROLLBACK INSTRUCTIONS

If the fix causes problems:

### Rollback Step 1 (Memory Engine):
**File**: `engines/memory_engine.py` line 1504

Remove:
```python
mem['relevance_score'] = score  # DELETE THIS
```

### Rollback Step 2 (Emotion Engine):
**File**: `engines/emotion_engine.py` lines 208-220

Restore original code:
```python
# --- 3. reinforce via memory ---
memory_count = len(agent_state.last_recalled_memories or [])
reinforced_emotions = []
for mem in agent_state.last_recalled_memories or []:
    for tag in mem.get("emotion_tags", []):
        if tag in cocktail:
            old_intensity = cocktail[tag]["intensity"]
            cocktail[tag]["intensity"] = min(1.0, cocktail[tag]["intensity"] + 0.05)
            if tag not in reinforced_emotions:
                reinforced_emotions.append(tag)

print(f"[EMOTION ENGINE] Processed {memory_count} memories, reinforced {len(reinforced_emotions)} emotions")
```

---

## FILES TO MODIFY

1. ✅ `engines/memory_engine.py` - Line 1504 (store relevance_score)
2. ✅ `engines/memory_engine.py` - After line 1430 (add top-10 logging)
3. ✅ `engines/emotion_engine.py` - Lines 208-220 (relevance-weighted boost)

---

## ESTIMATED IMPACT

**Current Behavior**:
- 310 memories × 0.05 = 15.5 total boost potential
- Decay = -0.05 per turn
- Net effect: Boost overwhelms decay, emotions frozen

**After Fix**:
- 40 memories × 0.05 × (avg relevance 0.4) = 0.8 total boost
- Decay = -0.05 per turn
- Net effect: Emotions decay when not actively reinforced ✓

**Cost Reduction**: None (pure logic change, no API calls)

**Performance Impact**: Minimal (sorting 310 items is negligible)

---

## READY FOR REVIEW

This implementation plan:
- ✅ Identifies exact problem location (emotion_engine.py lines 208-220)
- ✅ Confirms relevance_score does NOT exist (needs to be added)
- ✅ Provides exact code changes for both files
- ✅ Includes comprehensive logging for verification
- ✅ Provides tuning parameters for adjustment
- ✅ Includes testing checklist
- ✅ Provides rollback instructions

**Next Step**: Review this plan and approve implementation.
