# Quick Reference: Memory Wipe and Import Retrieval

## TL;DR - What Was Fixed

1. **Memory Wipe:** Already worked perfectly, no changes needed
2. **Import Retrieval:** Added missing `return memories` statement to `recall()` function

Both issues now verified working with comprehensive test suite.

---

## How to Use

### Wipe Kay's Memory
```bash
python aggressive_wipe.py
```
**Result:** All 8 memory files deleted and recreated empty. Backup saved automatically.

### Test Wipe + Retrieval
```bash
python test_wipe_and_retrieval.py
```
**Expected:** All 5 queries succeed, imported facts retrieved

### Verify Memory is Empty
```bash
python -c "import json; print('Memories:', len(json.load(open('memory/memories.json'))))"
```
**Expected:** `Memories: 0`

---

## The Fix (1 Line)

**File:** `engines/memory_engine.py`
**Line:** 1255

```python
# BEFORE (broken):
def recall(self, agent_state, user_input, ...):
    memories = self.retrieve_multi_factor(...)
    agent_state.last_recalled_memories = memories
    # BUG: No return statement!

# AFTER (fixed):
def recall(self, agent_state, user_input, ...):
    memories = self.retrieve_multi_factor(...)
    agent_state.last_recalled_memories = memories
    return memories  # ← Added this line
```

That's it. One missing `return` statement broke all retrieval.

---

## Why Import Retrieval Appeared Broken

The logs showed:
```
[RETRIEVAL] Import query detected - boosting imported facts
[RETRIEVAL] Boosting imported fact -> MASSIVE boost: 14.8x
Multi-factor retrieval: 5 working memories scored
Retrieved 0 total memories  # ← This was the bug!
```

The system was correctly:
1. Detecting import queries ✓
2. Applying 14.8x boost ✓
3. Scoring facts highly ✓

But `recall()` returned `None` instead of the memories!

---

## What Import Boost Does

When you import a document, each fact gets `is_imported=True`.

Then during retrieval:
- **Base boost:** 3.0x for recently imported facts (decays over 50 turns)
- **Query boost:** Additional 5x if query mentions "imported", "new document", "recently", etc.
- **Total:** Up to 15x multiplier for imported content

Query patterns that trigger the 5x boost:
- "What's in what I just imported?"
- "What do you remember from the new document?"
- "Tell me about the recently imported facts"
- "What did I just tell you?"
- Any query with: "new document", "just imported", "recent import", "from the document", etc.

Even keyword queries work:
- "sky blue" → Retrieves "The sky is blue on clear days"

---

## Test Results

```
======================================================================
FINAL VERDICT
======================================================================
[SUCCESS] All 5 retrieval queries returned imported facts
Memory wipe and retrieval system working correctly!

Successful queries: 5/5
  [OK] 'What's in what I just imported?' -> 5/5 imported
  [OK] 'What do you remember from the new document?' -> 5/5 imported
  [OK] 'Tell me about the recently imported facts' -> 5/5 imported
  [OK] 'What did I just tell you?' -> 5/5 imported
  [OK] 'sky blue' -> 5/5 imported
```

---

## File Changes

Only 2 files modified:

1. **engines/memory_engine.py** (1 line added)
   - Line 1255: `return memories`

2. **utils/performance.py** (2 lines changed)
   - Replaced unicode checkmarks with ASCII for Windows console

Plus 1 new file:
3. **test_wipe_and_retrieval.py** (comprehensive test suite)

---

## Workflow: Clean Slate Testing

```bash
# 1. Wipe memory
python aggressive_wipe.py

# 2. Run test (imports 5 facts and queries them)
python test_wipe_and_retrieval.py

# Expected output:
# [SUCCESS] All 5 retrieval queries returned imported facts
```

Or manually:
```bash
# 1. Wipe
python aggressive_wipe.py

# 2. Start Kay
python main.py

# 3. Import document
> /import sky_facts.txt

# 4. Query
> What's in what I just imported?
```

Kay should now respond with specific facts from the document (e.g., "sky is blue, grass is green") instead of vague confabulation.

---

## Backups

Every wipe creates a timestamped backup:
```
memory/backups/backup_20251028_202823/
├── memories.json
├── entity_graph.json
├── memory_layers.json
├── identity_memory.json
├── preferences.json
├── motifs.json
├── memory_index.json
└── identity_index.json
```

To restore:
```bash
cp memory/backups/backup_YYYYMMDD_HHMMSS/* memory/
```

---

## Troubleshooting

**Q: Wipe says successful but files still have data**
**A:** Did you restart Kay immediately after wiping? Kay auto-loads and may create initial state. Run the test script instead which controls the full flow.

**Q: Import retrieval still not working**
**A:**
1. Check if `engines/memory_engine.py:1255` has `return memories`
2. Run `python test_wipe_and_retrieval.py` to verify
3. Check that imported facts have `is_imported=True` flag

**Q: Unicode errors in output**
**A:** Fixed in `utils/performance.py`. If you still see them, ensure you're using the updated version.

---

## Key Files

- **aggressive_wipe.py** - Memory wipe script (no changes needed)
- **test_wipe_and_retrieval.py** - Comprehensive test suite (NEW)
- **engines/memory_engine.py** - Fixed recall() function (1 line added)
- **utils/performance.py** - Fixed unicode issues (cosmetic)
- **FIX_SUMMARY.md** - Detailed technical report
- **QUICK_REFERENCE.md** - This file

---

## Next Steps

1. Run `python test_wipe_and_retrieval.py` to verify both fixes
2. If test passes → both issues resolved
3. Use `python aggressive_wipe.py` before testing wrapper
4. Import test documents and verify Kay retrieves actual content

Both critical blockers are now **RESOLVED** and **VERIFIED**.
