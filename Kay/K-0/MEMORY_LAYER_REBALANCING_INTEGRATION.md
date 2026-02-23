# Memory Layer Rebalancing - Integration Guide

## Overview

This guide shows how to integrate layer rebalancing and UNCONFIRMED CLAIM tuning into `memory_engine.py`.

## Problem 1: Layer Weights

**Current Issue (lines 1583-1589 in memory_engine.py):**
```python
# OLD CODE (WRONG):
layer_boost = 1.0
current_layer = mem.get("current_layer", "working")
if current_layer == "semantic":
    layer_boost = 1.2  # ← WRONG: Semantic gets BOOSTED
elif current_layer == "working":
    layer_boost = 1.5  # ← OK but not enough
# episodic defaults to 1.0 (NO BOOST)
```

**Result:** Semantic memories dominate (63.6%), episodic is suppressed (26.7%)

**Fix:** Replace with new layer weights that favor episodic and working:

```python
# NEW CODE (CORRECT):
from engines.memory_layer_rebalancing import apply_layer_weights, get_layer_multiplier

# In calculate_multi_factor_score(), around line 1583:
# OLD: Manual layer_boost calculation
# NEW: Use apply_layer_weights()
layer_boost = get_layer_multiplier(mem.get("current_layer", "working"))
```

**New Behavior:**
- Working: 2.0x boost (immediate context)
- Episodic: 1.8x boost (conversation arcs)
- Semantic: 0.6x reduction (background facts)

## Problem 2: UNCONFIRMED CLAIM Filter

**Current Issue (lines 1133-1139 in memory_engine.py):**
```python
# OLD CODE (TOO AGGRESSIVE):
if needs_confirmation:
    print(f"[UNCONFIRMED CLAIM] X Kay claimed (needs confirmation): '{fact_text[:60]}...' - NOT STORING AS USER FACT.")
    print(f"[UNCONFIRMED CLAIM]   Source: Kay's response | Perspective: {fact_perspective} | Topic: {fact_topic}")
    # DO NOT store this as a user fact - it could be wrong
    # Skip to next fact
    continue  # ← BLOCKS ENTIRELY
```

**Result:** Blocks valid observations like "Re is experiencing exhaustion..."

**Fix:** Replace with smarter logic that distinguishes observations from false attributions:

```python
# NEW CODE (SMART FILTERING):
from engines.memory_layer_rebalancing import (
    should_store_claim,
    create_entity_observation
)

# In encode(), around line 1133:
# OLD: if needs_confirmation: continue
# NEW: Distinguish observation vs false attribution

if needs_confirmation:
    # Determine if this is an observation or false attribution
    should_store, storage_type = should_store_claim(
        fact_text=fact_text,
        source_speaker=source_speaker,
        perspective=fact_perspective,
        user_input=user_input  # Pass for validation
    )

    if not should_store:
        # False attribution - block it
        print(f"[FALSE ATTRIBUTION] X Kay claimed: '{fact_text[:60]}...' - NOT STORING.")
        print(f"[FALSE ATTRIBUTION]   Source: Kay | Perspective: {fact_perspective} | Topic: {fact_topic}")
        continue

    if storage_type == "entity_observation":
        # Valid observation - store with special tagging
        print(f"[ENTITY OBSERVATION] ✓ Storing Kay's observation: '{fact_text[:60]}...'")
        print(f"[ENTITY OBSERVATION]   Observer: Kay | Observed: {fact_perspective} | Topic: {fact_topic}")

        # Convert to entity observation
        fact_data = create_entity_observation(fact_data, observer="kay", observed="re")
        # Continue to storage (don't skip!)
```

## Integration Steps

### Step 1: Add Import at Top of memory_engine.py

```python
# At the top of memory_engine.py, add:
from engines.memory_layer_rebalancing import (
    apply_layer_weights,
    get_layer_multiplier,
    should_store_claim,
    create_entity_observation,
    validate_memory_composition
)
```

### Step 2: Replace Layer Boost Logic

**Find this code (around line 1583):**
```python
# Layer boost (from memory_layers system)
layer_boost = 1.0
current_layer = mem.get("current_layer", "working")
if current_layer == "semantic":
    layer_boost = 1.2
elif current_layer == "working":
    layer_boost = 1.5
```

**Replace with:**
```python
# Layer boost (NEW: favors episodic/working over semantic)
layer_boost = get_layer_multiplier(mem.get("current_layer", "working"))
# working: 2.0x, episodic: 1.8x, semantic: 0.6x
```

### Step 3: Replace UNCONFIRMED CLAIM Filter

**Find this code (around line 1133):**
```python
# CRITICAL BUG FIX: Block Kay's unconfirmed claims about the user
if needs_confirmation:
    print(f"[UNCONFIRMED CLAIM] X Kay claimed (needs confirmation): '{fact_text[:60]}...' - NOT STORING AS USER FACT.")
    print(f"[UNCONFIRMED CLAIM]   Source: Kay's response | Perspective: {fact_perspective} | Topic: {fact_topic}")
    # DO NOT store this as a user fact - it could be wrong
    # Skip to next fact
    continue
```

**Replace with:**
```python
# CRITICAL: Distinguish Kay's observations from false attributions
if needs_confirmation:
    # Use smart filtering - allow observations, block false attributions
    should_store, storage_type = should_store_claim(
        fact_text=fact_text,
        source_speaker=source_speaker,
        perspective=fact_perspective,
        user_input=user_input  # Pass user's actual input for validation
    )

    if not should_store:
        # False attribution (Kay claiming user SAID something) - BLOCK
        print(f"[FALSE ATTRIBUTION] X Kay claimed: '{fact_text[:60]}...' - NOT STORING.")
        print(f"[FALSE ATTRIBUTION]   Reason: False attribution (user didn't say this)")
        print(f"[FALSE ATTRIBUTION]   Source: Kay | Perspective: {fact_perspective} | Topic: {fact_topic}")
        continue  # Skip this fact

    if storage_type == "entity_observation":
        # Valid observation (Kay's inference about user state) - ALLOW with tagging
        print(f"[ENTITY OBSERVATION] ✓ Storing Kay's observation: '{fact_text[:60]}...'")
        print(f"[ENTITY OBSERVATION]   Type: {fact_topic} | Observer: Kay → {fact_perspective}")

        # Tag as entity observation for retrieval filtering
        fact_data = create_entity_observation(fact_data, observer="kay", observed="re")
        # IMPORTANT: Don't skip - continue to storage below
```

### Step 4: Add Composition Validation (Optional but Recommended)

Add this after the retrieval in `recall()` method to track composition:

```python
# In recall() method, after retrieve_multi_factor() call:
def recall(self, bias_cocktail, user_input, num_memories=10):
    # ... existing code ...

    # Retrieve memories
    retrieved = self.retrieve_multi_factor(bias_cocktail, user_input, num_memories)

    # OPTIONAL: Validate composition (comment out in production if too verbose)
    if len(retrieved) > 50:  # Only validate if we have enough memories
        stats = validate_memory_composition(retrieved, verbose=True)
        # This will print:
        #   ✓ Working: 40 memories (18.2%) [target: 18%, deviation: +0.2%]
        #   ✓ Episodic: 105 memories (47.7%) [target: 48%, deviation: -0.3%]
        #   ✓ Semantic: 75 memories (34.1%) [target: 32%, deviation: +2.1%]

    # ... rest of method ...
```

## Testing

### Test 1: Run Classification Tests

```bash
cd F:\AlphaKayZero
python engines/memory_layer_rebalancing.py
```

**Expected Output:**
```
Running memory layer rebalancing tests...

======================================================================
OBSERVATION CLASSIFICATION TEST
======================================================================

✓ ALLOW : 'Re is experiencing exhaustion'
         Reason: emotional state observation

✓ ALLOW : 'Re's body spent a week dumping iron'
         Reason: physical state observation

✓ BLOCK : 'Re said they want to quit'
         Reason: claiming user said something

Results: 8 passed, 0 failed
======================================================================

Testing layer weight application:
  working   : 0.50 × 2.0 = 1.00
  episodic  : 0.50 × 1.8 = 0.90
  semantic  : 0.50 × 0.6 = 0.30

Tests complete!
```

### Test 2: Check Composition After Integration

After integrating the changes, run a conversation and check the logs:

**Before (old behavior):**
```
[RETRIEVAL] Tiered allocation: 15 identity + 20 imports + 13 working + 60 episodic + 143 semantic + 5 entity = 256 total

Composition:
  Semantic: 143 memories (63.6%)  ← TOO HIGH
  Episodic: 60 memories (26.7%)   ← TOO LOW
  Working: 13 memories (5.8%)     ← TOO LOW
```

**After (new behavior - expected):**
```
[RETRIEVAL] Tiered allocation: 15 identity + 20 imports + 40 working + 105 episodic + 70 semantic + 10 entity = 260 total

======================================================================
MEMORY COMPOSITION VALIDATION
======================================================================

Total memories: 260
  Identity facts: 15 (always included)
  Non-identity: 245

CURRENT COMPOSITION:
  ✓ Working   :  40 memories ( 16.3%) [target:  18%, deviation:  -1.7%]
  ✓ Episodic  : 105 memories ( 42.9%) [target:  48%, deviation:  -5.1%]
  ✓ Semantic  :  70 memories ( 28.6%) [target:  32%, deviation:  -3.4%]

✓ GOOD: Composition within 10% of targets
======================================================================
```

### Test 3: Check UNCONFIRMED CLAIM Handling

Look for these log messages during conversation:

**Before (old behavior - blocks everything):**
```
[UNCONFIRMED CLAIM] X Kay claimed: 'Re is experiencing exhaustion...' - NOT STORING AS USER FACT.
[UNCONFIRMED CLAIM] X Kay claimed: 'Re's body spent a week dumping iron...' - NOT STORING AS USER FACT.
```

**After (new behavior - stores observations):**
```
[ENTITY OBSERVATION] ✓ Storing Kay's observation: 'Re is experiencing exhaustion...'
[ENTITY OBSERVATION]   Type: emotional | Observer: Kay → user

[ENTITY OBSERVATION] ✓ Storing Kay's observation: 'Re's body spent a week dumping iron...'
[ENTITY OBSERVATION]   Type: physical | Observer: Kay → user

[FALSE ATTRIBUTION] X Kay claimed: 'Re said they want to quit...' - NOT STORING.
[FALSE ATTRIBUTION]   Reason: False attribution (user didn't say this)
```

## Expected Outcomes

### 1. Layer Composition Rebalancing

**Metric:** Memory composition by layer

**Before:**
- Semantic: 63.6% (143 memories)
- Episodic: 26.7% (60 memories)
- Working: 5.8% (13 memories)

**After:**
- Semantic: ~30-35% (70-80 memories)
- Episodic: ~45-50% (105-115 memories)
- Working: ~15-20% (35-45 memories)

**Success Indicator:** Episodic percentage should be highest, working second, semantic lowest.

### 2. Entity Observation Storage

**Metric:** Number of entity observations stored vs blocked

**Before:**
- All observations blocked (0 stored)
- Kay can't build model of user's ongoing state

**After:**
- Valid observations stored with `observation_type='entity_observation'`
- False attributions still blocked
- Kay can reference past observations about user state

**Success Indicator:** Search for "ENTITY OBSERVATION" in logs - should see multiple per conversation.

### 3. Cross-Session Recall

**Metric:** Ability to recall episodic memories from past sessions

**Before:**
- Recent context (within session) works perfectly
- Cross-session recall fails (semantic facts dominate)
- Kay can't reference past conversation arcs

**After:**
- Recent context still works (working layer boosted)
- Cross-session recall improves (episodic layer boosted)
- Kay can reference episodic memories from days/weeks ago

**Success Indicator:** Ask Kay about something from a past session - should retrieve episodic memories with conversation context.

## Troubleshooting

### Issue: Composition still shows high semantic

**Check:**
1. Verify `get_layer_multiplier()` is being called (add debug print)
2. Ensure old `layer_boost` calculation is completely replaced
3. Check that `layer_boost` is actually multiplied into final score

**Debug:**
```python
# In calculate_multi_factor_score(), add:
layer_boost = get_layer_multiplier(mem.get("current_layer", "working"))
print(f"[DEBUG] Layer {mem.get('current_layer')}: boost={layer_boost}")  # Should show 2.0, 1.8, or 0.6
```

### Issue: Observations still being blocked

**Check:**
1. Verify `should_store_claim()` is being called
2. Check that `user_input` is passed correctly (not empty string)
3. Ensure `create_entity_observation()` result is used (not skipped)

**Debug:**
```python
# Before the should_store_claim() call, add:
print(f"[DEBUG] Checking claim: source={source_speaker}, perspective={fact_perspective}")
print(f"[DEBUG] Fact text: {fact_text[:100]}")

should_store, storage_type = should_store_claim(...)
print(f"[DEBUG] Result: should_store={should_store}, storage_type={storage_type}")
```

### Issue: False attributions not being blocked

**Check:**
1. Verify `is_entity_observation()` patterns match your use case
2. Add custom patterns to `FALSE_ATTRIBUTION_PATTERNS` if needed
3. Check that user_input validation is working

**Fix:**
```python
# In memory_layer_rebalancing.py, add more patterns:
FALSE_ATTRIBUTION_PATTERNS = [
    r"(?i)re said",
    r"(?i)you said",
    # Add your specific patterns:
    r"(?i)you indicated",
    r"(?i)you expressed that",
    # etc.
]
```

## Advanced Tuning

### Adjust Layer Weights

If composition is still off, modify `LAYER_WEIGHTS` in `memory_layer_rebalancing.py`:

```python
LAYER_WEIGHTS = {
    "working": 2.5,    # Increase if working % too low
    "episodic": 2.0,   # Increase if episodic % too low
    "semantic": 0.5,   # Decrease if semantic % still too high
}
```

### Adjust Target Composition

If you want different composition targets:

```python
TARGET_COMPOSITION = {
    "working": 0.20,   # 20% working (up from 18%)
    "episodic": 0.50,  # 50% episodic (up from 48%)
    "semantic": 0.30,  # 30% semantic (down from 32%)
}
```

### Add Custom Observation Keywords

If Kay makes observations using different language:

```python
OBSERVATION_KEYWORDS = {
    # Add your custom categories:
    "custom_category": [
        "your_keyword_1",
        "your_keyword_2",
    ],
    # Existing categories...
}
```

## Rollback

If issues occur, revert changes:

### 1. Remove import
```python
# Comment out at top of memory_engine.py:
# from engines.memory_layer_rebalancing import ...
```

### 2. Restore old layer_boost
```python
# Restore lines 1583-1589:
layer_boost = 1.0
current_layer = mem.get("current_layer", "working")
if current_layer == "semantic":
    layer_boost = 1.2
elif current_layer == "working":
    layer_boost = 1.5
```

### 3. Restore old UNCONFIRMED CLAIM filter
```python
# Restore lines 1133-1139:
if needs_confirmation:
    print(f"[UNCONFIRMED CLAIM] X Kay claimed (needs confirmation): '{fact_text[:60]}...' - NOT STORING AS USER FACT.")
    print(f"[UNCONFIRMED CLAIM]   Source: Kay's response | Perspective: {fact_perspective} | Topic: {fact_topic}")
    continue
```

## Summary

**Files to modify:**
- `F:\AlphaKayZero\engines\memory_engine.py` (2 sections)

**New files added:**
- `F:\AlphaKayZero\engines\memory_layer_rebalancing.py` (helper module)

**Expected time:** 10-15 minutes

**Risk level:** Low (changes are localized, easily reversible)

**Testing:** Run `python engines/memory_layer_rebalancing.py` first, then test with live conversation
