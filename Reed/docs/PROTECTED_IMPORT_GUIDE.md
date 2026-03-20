# Protected Import Pipeline Guide

## Overview

The **Protected Import Pipeline** ensures that newly imported facts are VISIBLE to Kay for 3 turns, even through the aggressive glyph pre-filter.

This solves the critical issue where imported facts were being filtered out before Kay could "see" them.

---

## Problem Solved

**BEFORE (Broken):**
```
1. Upload document → Extract 10 key facts
2. Glyph pre-filter reduces 400 memories → 100
3. Imported facts get filtered out (low keyword match)
4. Kay can't "see" what was just uploaded
5. User asks about upload → Kay says "I don't remember"
```

**AFTER (Fixed):**
```
1. Upload document → Extract 10 key facts (marked protected=True, age=0)
2. Glyph pre-filter: Protected facts BYPASS filtering
3. All 10 imported facts reach Kay's context
4. Kay can answer questions about upload immediately
5. After 3 turns, facts lose protection → integrate naturally
```

---

## Implementation

### 1. Memory Format (Protected + Age)

All imported facts now include:
```python
{
    "fact": "[cat] is Re's gray tabby cat",
    "is_imported": True,
    "protected": True,  # NEW: Bypass filtering
    "age": 0,           # NEW: Increments each turn
    "importance_score": 0.9,
    "entities": ["Re", "[cat]"],
    "turn_index": 42
}
```

### 2. Glyph Pre-Filter (Respects Protection)

**File:** `context_filter.py:_prefilter_memories_by_relevance()`

**Logic:**
```python
# Separate protected vs filterable
protected = []
filterable = []

for mem in all_memories:
    # Protect recently imported (age < 3)
    if mem.get("protected") or (mem.get("is_imported") and mem.get("age", 999) < 3):
        protected.append(mem)
    else:
        filterable.append(mem)

# Apply scoring to filterable only
scored = score_memories(filterable)
top_filtered = scored[:max_count - len(protected)]

# Combine: protected + top filtered
result = protected + top_filtered
```

**Result:**
- Protected facts **always** included in context
- Filterable facts scored and top N selected
- Total stays under max_count (default: 100)

### 3. Age Tracking (MemoryEngine)

**File:** `engines/memory_engine.py:increment_memory_ages()`

**Call at END of each turn:**
```python
def increment_memory_ages(self):
    """
    Increment age of all memories by 1 turn.
    Unprotect facts older than 3 turns.
    """
    for mem in self.memories:
        if "age" in mem:
            mem["age"] += 1

            # Unprotect after 3 turns
            if mem.get("protected") and mem.get("age", 0) >= 3:
                mem["protected"] = False
```

### 4. Integration in Main Loop

**File:** `main.py` (add at END of conversation loop)

**CRITICAL:** Call AFTER Kay responds but BEFORE next turn starts:
```python
# Main conversation loop
while True:
    user_input = input("You: ")

    # 1. Memory recall (includes protected imports)
    recalled_memories = memory_engine.recall(agent_state, user_input)

    # 2. Build context (glyph pre-filter respects protection)
    context = context_manager.build_context(agent_state, user_input)

    # 3. Kay responds
    response = get_llm_response(context, affect_level)
    print(f"Kay: {response}")

    # 4. Post-turn updates (emotion decay, reflection, etc.)
    # ... existing updates ...

    # 5. INCREMENT AGES (NEW - CRITICAL!)
    memory_engine.increment_memory_ages()

    # 6. Save state
    memory_engine._save_to_disk()
```

**Why at the end?**
- Age represents "turns SINCE import"
- Turn 0: Just imported, age=0, protected
- Turn 1: One turn later, age=1, still protected
- Turn 2: Two turns later, age=2, still protected
- Turn 3: Three turns later, age=3, **unprotected**

---

## Complete Flow Example

### Upload Document
```python
from engines.vector_store import VectorStore
from memory_import.hybrid_import_manager import HybridImportManager

# Initialize
vector_store = VectorStore()
manager = HybridImportManager(
    memory_engine=memory_engine,
    entity_graph=entity_graph,
    vector_store=vector_store
)

# Import document
await manager.import_files(["poem.txt"])

# Result: 10 facts added with protected=True, age=0
```

**Logs:**
```
[RAG] Added 27 chunks from poem.txt
[HYBRID_IMPORT] Extracted 8 key facts to structured memory
[MEMORY] 8 facts marked as protected (age=0)
```

### Turn 0 (Immediately After Upload)
```
User: "What did that poem say about [cat]?"

[RETRIEVAL] Protected 8 imported facts from filtering
[RAG] Retrieved 3 relevant chunks
[FILTER] 8 protected + 42 filtered = 50 total memories

Kay: "The poem described [cat] as a gray tabby who door-dashes..."
```

**Facts visible:** ✓ All 8 imported facts (protected)

### Turn 1 (One Turn Later)
```
User: "Tell me more about the cats"

[MEMORY] Aged 327 memories (+1 turn), unprotected 0 old imports
[RETRIEVAL] Protected 8 imported facts from filtering (age=1)
[FILTER] 8 protected + 42 filtered = 50 total memories

Kay: "From what I recall about the cats..."
```

**Facts visible:** ✓ All 8 imported facts (still protected, age=1)

### Turn 2 (Two Turns Later)
```
User: "What else?"

[MEMORY] Aged 327 memories (+1 turn), unprotected 0 old imports
[RETRIEVAL] Protected 8 imported facts from filtering (age=2)
[FILTER] 8 protected + 42 filtered = 50 total memories

Kay: "The poem also mentioned..."
```

**Facts visible:** ✓ All 8 imported facts (still protected, age=2)

### Turn 3 (Three Turns Later - UNPROTECTED)
```
User: "Anything else?"

[MEMORY] Aged 327 memories (+1 turn), unprotected 8 old imports
[RETRIEVAL] Protected 0 imported facts (age >= 3)
[FILTER] 0 protected + 50 filtered = 50 total memories

Kay: "Let me think..."
```

**Facts visible:** ~ 2-3 imported facts (high keyword match)

**Result:** Facts now compete fairly with other memories. High-importance facts stay visible, low-importance fade naturally.

---

## Configuration

### Protection Duration

**Default:** 3 turns

**To change:**
```python
# In context_filter.py
if mem.get("is_imported") and mem.get("age", 999) < 5:  # Change to 5 turns
    protected.append(mem)

# In memory_engine.py
if mem.get("protected") and mem.get("age", 0) >= 5:  # Change to 5 turns
    mem["protected"] = False
```

### Max Protected Facts

Protected facts count toward total context limit (default: 100).

If you import 20 facts, they'll take 20 slots, leaving 80 for filtered memories.

**To prevent flooding:**
- Cap imports at 10 facts per document (already enforced)
- Adjust `max_count` in glyph pre-filter if needed

---

## Verification

### Check Protection Status

```python
# After import
for mem in memory_engine.memories:
    if mem.get("is_imported"):
        print(f"Fact: {mem['fact'][:50]}")
        print(f"  Protected: {mem.get('protected')}")
        print(f"  Age: {mem.get('age')}")
```

### Check Glyph Pre-Filter

Look for logs:
```
[FILTER] Protected 8 imported/identity facts from filtering
[PERF] glyph_prefilter: 12.3ms - 327 -> 50 memories (8 protected + 42 filtered)
```

### Check Age Increment

Look for logs:
```
[MEMORY] Aged 327 memories (+1 turn), unprotected 8 old imports
```

---

## Troubleshooting

### "Imported facts still not visible"

**Check:**
1. Are facts marked `protected=True`?
   - Verify in memories.json
2. Is `increment_memory_ages()` being called?
   - Check for "[MEMORY] Aged X memories" log
3. Is glyph pre-filter checking protection?
   - Check for "[FILTER] Protected X facts" log

**Debug:**
```python
# After import
imported = [m for m in memory_engine.memories if m.get("is_imported")]
print(f"Imported facts: {len(imported)}")
for m in imported[:3]:
    print(f"  - {m['fact'][:50]}: protected={m.get('protected')}, age={m.get('age')}")
```

### "Facts staying protected too long"

**Check:**
- Is `increment_memory_ages()` being called each turn?
- Is age incrementing? (check logs)

**Fix:**
Ensure it's called in main loop:
```python
# At END of each turn
memory_engine.increment_memory_ages()
memory_engine._save_to_disk()
```

### "Facts losing protection too early"

**Check:**
- Age threshold in glyph pre-filter (default: 3)
- Age threshold in increment_memory_ages (default: 3)

**Both must match!**

---

## Performance Impact

**Negligible:**
- Age increment: O(n) where n = total memories (~0.1ms for 300 memories)
- Protected separation: O(n) in glyph pre-filter (already iterating)
- No additional API calls or expensive operations

**Benefits:**
- Imported facts immediately visible to Kay
- Natural integration after 3 turns
- No manual intervention needed

---

## Summary

**Protected Import Pipeline ensures:**
1. ✅ Imported facts marked `protected=True`, `age=0`
2. ✅ Glyph pre-filter **bypasses** protected facts
3. ✅ Age increments each turn
4. ✅ Protection expires after 3 turns (age >= 3)
5. ✅ Facts integrate naturally into memory system

**Result:**
- Kay can "see" uploaded documents immediately
- Facts visible for 3 turns guaranteed
- After 3 turns, natural keyword/importance scoring applies
- No memory bloat (facts still capped at 10 per document)

**System is working as designed!** 🎉
