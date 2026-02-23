# Memory Debug Tracking Guide

## Overview

The Memory Debug Tracker helps diagnose where specific memories (like pigeon names "Gimpy", "Bob", "Fork", etc.) get filtered out during Kay's multi-stage memory retrieval pipeline.

**Problem it solves:** When Re asks "What pigeons do I know?", Kay should retrieve all the pigeon names from memory. If some names are missing, we need to know WHERE they disappeared in the filtering pipeline.

---

## How It Works

The tracker follows specific keywords through 4 stages:

```
Stage 0: Full Dataset (8037 memories)
    ↓
Stage 1: SLOT_ALLOCATION (~310 memories)
    ↓
Stage 2: PRE-FILTER (150 or 300 memories)
    ↓
Stage 3: GLYPH FILTER (32-70 memories)
    ↓
Kay's LLM Context
```

At each stage, it checks:
- Which memories containing the target keywords survived?
- What were their scores/ranks?
- If they died, at which stage?

---

## Enabling Debug Tracking

### Method 1: Environment Variable (Recommended)

**Windows (PowerShell):**
```powershell
$env:DEBUG_MEMORY_TRACKING="1"
python main.py
```

**Windows (CMD):**
```cmd
set DEBUG_MEMORY_TRACKING=1
python main.py
```

**Linux/Mac:**
```bash
export DEBUG_MEMORY_TRACKING=1
python main.py
```

### Method 2: .env File

Add to your `.env` file:
```
DEBUG_MEMORY_TRACKING=1
```

Then run normally:
```bash
python main.py
```

---

## Disabling Debug Tracking

**Windows (PowerShell):**
```powershell
$env:DEBUG_MEMORY_TRACKING="0"
```

**Windows (CMD):**
```cmd
set DEBUG_MEMORY_TRACKING=0
```

**Linux/Mac:**
```bash
export DEBUG_MEMORY_TRACKING=0
```

Or remove the environment variable entirely.

---

## Example Output

When enabled, you'll see detailed tracking output like this:

```
================================================================================
[PIGEON DEBUG] === MEMORY TRACKING: "What pigeons do I know?" ===
[PIGEON DEBUG] Stage 0: Total memories = 8037
[PIGEON DEBUG] Tracking keywords: Gimpy, Bob, Fork, Zebra, Clarence, pigeon
[PIGEON DEBUG]   - Gimpy: FOUND in 2 memories
[PIGEON DEBUG]       #1: turn 8 - "Re told Kay about a pigeon named Gimpy"
[PIGEON DEBUG]       #2: turn 12 - "Gimpy is the leader of the flock"
[PIGEON DEBUG]   - Bob: FOUND in 1 memory
[PIGEON DEBUG]       #1: turn 8 - "Bob is another pigeon Re mentioned"
[PIGEON DEBUG]   - Fork: FOUND in 1 memory
[PIGEON DEBUG]   - Zebra: FOUND in 1 memory
[PIGEON DEBUG]   - Clarence: FOUND in 1 memory
[PIGEON DEBUG]   - pigeon: FOUND in 15 memories
[PIGEON DEBUG]

[PIGEON DEBUG] Stage 1: After SLOT_ALLOCATION = 310 memories
[PIGEON DEBUG]   - Gimpy: SURVIVED (2/2 instances, best score: 0.623, best rank: 89/8037)
[PIGEON DEBUG]   - Bob: CUT (didn't make top 310)
[PIGEON DEBUG]   - Fork: SURVIVED (1/1 instances, best score: 0.518, best rank: 245/8037)
[PIGEON DEBUG]   - Zebra: CUT (didn't make top 310)
[PIGEON DEBUG]   - Clarence: SURVIVED (1/1 instances, best score: 0.587, best rank: 156/8037)
[PIGEON DEBUG]   - pigeon: SURVIVED (8/15 instances, best score: 0.723, best rank: 45/8037)
[PIGEON DEBUG]

[PIGEON DEBUG] Stage 2: After PRE-FILTER = 150 memories
[PIGEON DEBUG]   - Gimpy: CUT (keyword score too low, didn't make top 150)
[PIGEON DEBUG]   - Fork: CUT (keyword score too low, didn't make top 150)
[PIGEON DEBUG]   - Clarence: SURVIVED (1/1 instances, keyword score: 67.00, rank: 78/150)
[PIGEON DEBUG]   - pigeon: SURVIVED (3/8 instances, keyword score: 85.00, rank: 23/150)
[PIGEON DEBUG]

[PIGEON DEBUG] Stage 3: After GLYPH FILTER = 70 memories
[PIGEON DEBUG]   - Clarence: CUT (LLM did not select it from 150 options)
[PIGEON DEBUG]   - pigeon: SURVIVED (1/3 instances - LLM selected it!)
[PIGEON DEBUG]

[PIGEON DEBUG] ================================================================================
[PIGEON DEBUG] FINAL SUMMARY: "What pigeons do I know?"
[PIGEON DEBUG] ================================================================================
[PIGEON DEBUG] Pipeline flow:
[PIGEON DEBUG]   Stage 0 (Full dataset):     8037 memories
[PIGEON DEBUG]   Stage 1 (SLOT_ALLOCATION):  310 memories
[PIGEON DEBUG]   Stage 2 (PRE-FILTER):       150 memories
[PIGEON DEBUG]   Stage 3 (GLYPH FILTER):     70 memories
[PIGEON DEBUG]

[PIGEON DEBUG] Keyword survival:
[PIGEON DEBUG]   Gimpy           - S0: 2 → S1: 2 → S2: 0 → S3: 0  [✗ DIED AT: Stage 2 (PRE-FILTER keyword scoring)]
[PIGEON DEBUG]   Bob             - S0: 1 → S1: 0 → S2: 0 → S3: 0  [✗ DIED AT: Stage 1 (SLOT_ALLOCATION)]
[PIGEON DEBUG]   Fork            - S0: 1 → S1: 1 → S2: 0 → S3: 0  [✗ DIED AT: Stage 2 (PRE-FILTER keyword scoring)]
[PIGEON DEBUG]   Zebra           - S0: 1 → S1: 0 → S2: 0 → S3: 0  [✗ DIED AT: Stage 1 (SLOT_ALLOCATION)]
[PIGEON DEBUG]   Clarence        - S0: 1 → S1: 1 → S2: 1 → S3: 0  [✗ DIED AT: Stage 3 (GLYPH FILTER - LLM did not select)]
[PIGEON DEBUG]   pigeon          - S0:15 → S1: 8 → S2: 3 → S3: 1  [✓ SURVIVED TO KAY'S CONTEXT]
[PIGEON DEBUG]

[PIGEON DEBUG] RESULT: 1/6 keywords made it to Kay's context
[PIGEON DEBUG] BOTTLENECK: Stage 2 (PRE-FILTER keyword scoring) (killed 2 keywords)
[PIGEON DEBUG] ================================================================================
```

---

## Understanding the Output

### Stage Breakdown

**Stage 0: Full Dataset**
- Shows how many memories contain each keyword
- Lists example memories with turn numbers and snippets

**Stage 1: SLOT_ALLOCATION**
- Shows which keywords survived the first cut (~310 memories)
- Shows multi-factor scores (emotion, semantic, importance, recency, entity)
- Shows rank out of total memories

**Stage 2: PRE-FILTER**
- Shows which keywords survived fast keyword matching (150 or 300 memories)
- Shows keyword matching scores (based on importance, recency, entity hits)
- This is often the bottleneck for specific names

**Stage 3: GLYPH FILTER**
- Shows which keywords the LLM selected (32-70 memories)
- This is intelligent semantic selection by Claude Haiku

### Death Analysis

The tracker identifies the **bottleneck** - which stage killed the most keywords:

- **Stage 1 (SLOT_ALLOCATION)**: Multi-factor score too low
- **Stage 2 (PRE-FILTER)**: Keyword matching score too low
- **Stage 3 (GLYPH FILTER)**: LLM didn't select it

---

## Customizing Tracked Keywords

By default, the tracker looks for pigeon names:
- "Gimpy"
- "Bob"
- "Fork"
- "Zebra"
- "Clarence"
- "pigeon" (generic)

### To Track Different Keywords

Edit `engines/memory_engine.py` line ~1159:

**Current:**
```python
tracker = get_tracker(["Gimpy", "Bob", "Fork", "Zebra", "Clarence", "pigeon"])
```

**Custom Example (tracking cat names):**
```python
tracker = get_tracker(["Whiskers", "Mittens", "Shadow", "cat"])
```

**Custom Example (tracking user info):**
```python
tracker = get_tracker(["dog", "Saga", "coffee", "Portland"])
```

---

## Performance Impact

**When DISABLED** (`DEBUG_MEMORY_TRACKING=0`):
- Zero performance impact
- All tracking code is skipped via early returns

**When ENABLED** (`DEBUG_MEMORY_TRACKING=1`):
- Minor impact: ~50-100ms per query
- Searches through memories 4 times (once per stage)
- Only recommended for debugging specific issues

**Recommendation:** Keep disabled during normal use. Enable only when diagnosing memory retrieval issues.

---

## Common Bottlenecks and Fixes

### Bottleneck: Stage 1 (SLOT_ALLOCATION)

**Symptom:** Keywords die at Stage 1 (multi-factor scoring too low)

**Causes:**
- Low semantic similarity (keyword doesn't match query words)
- Low emotional resonance (no emotional tags match current state)
- Low importance score (ULTRAMAP importance < 0.3)
- Old memory with high temporal decay

**Fixes:**
- Increase `semantic_weight` in `memory_engine.py:1247` (currently 0.35)
- Reduce `recency_weight` in `memory_engine.py:1275` (currently 0.05)
- Raise temporal decay floor in `memory_engine.py:1272` (currently 0.3)
- Increase SLOT_ALLOCATION limits in `memory_engine.py:1165`

### Bottleneck: Stage 2 (PRE-FILTER)

**Symptom:** Keywords survive Stage 1 but die at Stage 2 (keyword scoring)

**Causes:**
- Low keyword overlap with user query
- Low entity matching
- Low importance score
- Not flagged as identity/narrative/emotional

**Fixes:**
- Increase `MAX_CANDIDATES` in `context_filter.py:194` (currently 150)
- Boost keyword matching weight in `context_filter.py:529` (currently +10.0 per hit)
- Boost entity matching weight in `context_filter.py:535` (currently +15.0 per hit)
- Mark memories as `is_emotional_narrative` for +25.0 boost

### Bottleneck: Stage 3 (GLYPH FILTER)

**Symptom:** Keywords survive Stage 2 but LLM doesn't select them

**Causes:**
- LLM prompt asks for too few memories (25-40 standard, 50-80 for lists)
- LLM doesn't understand context relevance
- Memory preview is unclear in the summary

**Fixes:**
- Increase LLM selection guidance in `context_filter.py:232-236`
- Improve memory summary format in `context_filter.py:281-359`
- Add list detection keywords in `context_filter.py:180-184`

---

## Troubleshooting

### "No output appears when I enable tracking"

**Check:**
1. Is `DEBUG_MEMORY_TRACKING` actually set to "1" (string, not integer)?
   ```powershell
   echo $env:DEBUG_MEMORY_TRACKING
   ```
2. Did you restart the Python process after setting the environment variable?
3. Is the query actually triggering memory retrieval?

### "Tracker shows S0: 0 for all keywords"

**This means:** Keywords are not in the dataset at all.

**Check:**
1. Are memories actually stored? Check `memory/memories.json` or `memory/memory_layers.json`
2. Are keywords spelled correctly (case-sensitive)?
3. Try more generic keywords (e.g., "pigeon" instead of "Gimpy")

### "Tracker shows same values at all stages"

**This means:** Filtering isn't actually running (test mode).

**Check:**
1. Is Kay running in production mode?
2. Is the context_filter being called?
3. Check for errors earlier in the pipeline

---

## Files Modified

**New file:**
- `engines/memory_debug_tracker.py` - Core tracking logic

**Modified files:**
- `engines/memory_engine.py` - Stage 0 and Stage 1 tracking
- `context_filter.py` - Stage 2 and Stage 3 tracking

**No files removed or deprecated.**

---

## Future Enhancements

Potential improvements to this tracking system:

1. **Web UI Dashboard:** Visualize filtering pipeline with graphs
2. **Automatic Recommendations:** Suggest fixes based on bottleneck analysis
3. **Historical Tracking:** Log tracking data to file for analysis
4. **Multi-Query Analysis:** Compare tracking across different query types
5. **Score Breakdown:** Show component scores (emotion, semantic, importance, etc.)

---

## Related Documentation

- **RUNTIME_MEMORY_FLOW_ANALYSIS.md** - Complete pipeline documentation
- **RETRIEVAL_FIXES_IMPLEMENTED.md** - Recent memory retrieval improvements
- **MEMORY_PREFILTER_ANALYSIS.md** - Pre-filter scoring analysis

---

## Support

If you find a memory retrieval bug:

1. **Enable tracking:**
   ```bash
   export DEBUG_MEMORY_TRACKING=1
   ```

2. **Reproduce the issue** (e.g., ask "What pigeons do I know?")

3. **Copy the full debug output** from the console

4. **Identify the bottleneck** (Stage 1, 2, or 3)

5. **Check "Common Bottlenecks" section** for fixes

6. **If unclear, share the debug output** for analysis

---

**Status:** ✅ **IMPLEMENTED AND READY TO USE**

Enable tracking anytime to diagnose memory retrieval issues in real-time.
