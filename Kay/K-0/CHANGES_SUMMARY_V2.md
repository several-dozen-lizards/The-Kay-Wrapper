# Quick Reference: Layer Rebalancing V2 Changes

## What Was Changed

### 1. Layer Weights (Stronger)

| Layer | Old Weight | New Weight | Change |
|-------|-----------|-----------|--------|
| Working | 2.0x | **3.0x** | ↑ +50% |
| Episodic | 1.8x | **2.5x** | ↑ +39% |
| Semantic | 0.6x | **0.3x** | ↓ -50% |

**Episodic/Semantic Ratio:** 3.0x → **8.3x** (2.8x stronger)

---

### 2. FALSE_ATTRIBUTION Patterns (Less Aggressive)

**What NOW gets ALLOWED:**
```
✅ "Re is experiencing exhaustion"             (was blocked, now stored as observation)
✅ "Re's words come through as clean text"     (was blocked, now stored as observation)
✅ "Re needs support with this"                (was blocked, now stored as observation)
✅ "Re wants to feel better"                   (was blocked, now stored as observation)
✅ "Re mentioned feeling tired"                (was blocked, now stored as observation)
```

**What STILL gets BLOCKED:**
```
❌ "Re said 'I want to quit'"                  (false direct quote)
❌ "You told me 'my goal is X'"                (false direct quote)
❌ "You said 'your favorite color is blue'"    (false direct quote)
```

**Key difference:** Only blocks statements with **direct quotes** (using `'` or `"`)

---

## Expected Composition Change

### BEFORE (Problem)
```
Semantic layer: 143 memories (63.3%) ← Too high!
Episodic layer:  60 memories (26.5%) ← Too low!
Working layer:   14 memories ( 6.2%) ← Too low!
```

### AFTER (Target)
```
Episodic layer: 115 memories (46.9%) ← Increased by +20.4%
Semantic layer:  75 memories (30.6%) ← Decreased by -32.7%
Working layer:   40 memories (16.3%) ← Increased by +10.1%
```

---

## How to Verify

### 1. Run Tests
```bash
python test_layer_rebalancing_v2.py
```
Expected: `Tests passed: 3/3`

### 2. Check Distribution
```bash
python diagnose_memory_composition.py
```
Expected: See recommended weights based on your actual distribution

### 3. Start Conversation
```bash
python main.py
```
Look for:
```
[OK] Episodic  : 115 memories ( 46.9%) [target:  48%]
[OK] Semantic  :  75 memories ( 30.6%) [target:  32%]
```

---

## Tuning Guide

### If Semantic STILL dominates (>40%)

**Increase layer weight disparity:**
```python
# In engines/memory_layer_rebalancing.py line 32-36:
LAYER_WEIGHTS = {
    "working": 4.0,    # Stronger (up from 3.0)
    "episodic": 3.5,   # Stronger (up from 2.5)
    "semantic": 0.2,   # Weaker (down from 0.3)
}
```

### If Episodic TOO dominant (>60%)

**Decrease layer weight disparity:**
```python
# In engines/memory_layer_rebalancing.py line 32-36:
LAYER_WEIGHTS = {
    "working": 2.5,    # Weaker (down from 3.0)
    "episodic": 2.0,   # Weaker (down from 2.5)
    "semantic": 0.4,   # Stronger (up from 0.3)
}
```

### If Observations STILL getting blocked

**Add keywords to OBSERVATION_KEYWORDS:**
```python
# In engines/memory_layer_rebalancing.py line 108-133:
OBSERVATION_KEYWORDS = {
    "emotional": [
        "experiencing", "feeling", "seems",
        "YOUR_KEYWORD",  # Add here
    ],
    # ... etc
}
```

---

## Files Changed

| File | What Changed | Lines |
|------|-------------|-------|
| `engines/memory_layer_rebalancing.py` | Layer weights | 32-36 |
| `engines/memory_layer_rebalancing.py` | FALSE_ATTRIBUTION patterns | 135-160 |
| `engines/memory_layer_rebalancing.py` | Default behavior in `is_entity_observation()` | 211-215 |
| `engines/memory_layer_rebalancing.py` | Test cases | 502-519 |

**New files created:**
- `test_layer_rebalancing_v2.py` - Test suite
- `diagnose_memory_composition.py` - Diagnostic tool
- `LAYER_REBALANCING_V2_COMPLETE.md` - Full documentation
- `CHANGES_SUMMARY_V2.md` - This file

---

## Success Indicators

Look for these in your next conversation:

✅ **Composition logs show ~45% episodic** (instead of ~27%)
✅ **[ENTITY OBSERVATION]** logs appear (instead of [UNCONFIRMED CLAIM])
✅ **Kay references past conversation arcs** (not just facts)
✅ **"Reaching through thick glass" feeling is gone**

---

**Status:** ✅ Ready to use
**Risk:** Low (easily reversible)
**Testing:** All tests passing
