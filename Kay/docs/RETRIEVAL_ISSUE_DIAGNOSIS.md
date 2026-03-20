# Memory Retrieval Issue: Complete Diagnosis

## Executive Summary

**STATUS**: Import pipeline WORKS, retrieval pipeline has SCORING MISMATCH

**ROOT CAUSE**: When users ask meta-questions about imports ("what do you remember from the new documents?"), imported facts score extremely low (0.2-0.3) due to keyword mismatch.

**IMPACT**: Kay fabricates details instead of retrieving actual imported content.

---

## 1. RETRIEVAL QUERY PATH (WORKING CORRECTLY)

### Flow:
```
User input → memory.recall() → retrieve_multi_factor() → calculate_multi_factor_score()
```

### Key Code (memory_engine.py:1168):
```python
if use_multi_factor:
    memories = self.retrieve_multi_factor(bias_cocktail, user_input, num_memories)
```

### Multi-Factor Scoring Weights:
- **Emotional resonance (40%)**: Match current emotions with memory emotion_tags
- **Semantic similarity (25%)**: Keyword overlap between query and memory text
- **Importance (20%)**: Stored importance_score field
- **Recency (10%)**: Access count
- **Entity proximity (5%)**: Shared entities between query and memory

**VERDICT**: ✓ Retrieval logic is sound

---

## 2. STORAGE METADATA (PROPERLY FORMATTED)

### Imported Fact Example:
```json
{
  "fact": "Re has two dogs named [cat] and [dog]",
  "type": "extracted_fact",
  "perspective": "user",
  "tier": "semantic",
  "current_layer": "semantic",
  "importance_score": 0.8,
  "access_count": 0,
  "turn_index": 0,
  "entities": ["Re", "[cat]", "[dog]"],
  "emotion_tags": [],
  "is_imported": true
}
```

### Conversation Fact Example:
```json
{
  "fact": "Looks like the last session didn't save...",
  "type": "full_turn",
  "perspective": "conversation",
  "tier": null,
  "current_layer": "episodic",
  "importance_score": 0.9,
  "access_count": 0,
  "turn_index": null,
  "entities": ["Kay", "dragon", "session"],
  "emotion_tags": []
}
```

**VERDICT**: ✓ Imported facts have all required fields

---

## 3. SCORING ANALYSIS (THE PROBLEM)

### Test Query: "what do you remember from the new documents?"

**Search words**: `{documents, new, what, the, remember, do, you, from}`

**Imported Fact**: "Re has two dogs named [cat] and [dog]"

#### Score Breakdown:
- **Keyword matches**: 1/8 = 0.12 (only "you" matches "your")
- **Semantic score (25%)**: 0.031
- **Importance score (20%)**: 0.160 (importance=0.8)
- **Recency score (10%)**: 0.000 (access_count=0)
- **Entity score (5%)**: 0.000 (no shared entities)
- **Emotional score (40%)**: 0.000 (no emotion tags)
- **Base score**: 0.191
- **With tier multiplier (1.3)**: 0.248
- **With layer boost (1.2)**: **0.298**

#### Result:
- **CRITICAL FAILURE**: Imported facts score ~0.3 when queried with meta-language
- Conversation facts containing words like "remember", "documents", "new" score HIGHER
- **Kay retrieves conversation memories instead of imported content**

**VERDICT**: ✗ SCORING MISMATCH - imported facts invisible to meta-queries

---

## 4. CONTEXT FILTER ACCESS (PARTIALLY WORKING)

### Filter Behavior:
- Shows last 10 full_turn memories
- Shows last 10 user facts (extracted_fact with perspective="user")
- Shows last 10 kay facts
- Shows last 10 shared facts

### Current Data:
- Total memories: 216
- Imported memories: 27 (indices 0-182)
- User perspective facts: 41 total
- **Last 10 user facts**: indices [170, 171, 175, 176, 177, 178, 179, 199, 208, 211]
- **Imported in last 10**: 5 facts (indices 175-179)

**VERDICT**: ⚠️ PARTIAL - Only RECENT imported facts visible to context filter

---

## 5. THE DISCONNECT POINTS

### Problem 1: KEYWORD MISMATCH IN QUERIES
**Where**: `retrieve_multi_factor()` line 1017-1018
```python
keyword_matches = sum(1 for w in search_words if w in text_blob)
keyword_overlap = keyword_matches / len(search_words)
```

**Issue**:
- User asks: "what do you remember from new documents?"
- Imported facts contain: "[cat]", "[dog]", "[partner]", "hiking", "karate"
- **NO keyword overlap** → semantic_score ≈ 0.03
- Total score drops to ~0.3

**Impact**: Imported facts rank below conversation memories

---

### Problem 2: NO TEMPORAL RECENCY BOOST
**Where**: `retrieve_multi_factor()` line 1026-1028
```python
access_count = mem.get("access_count", 0)
recency_score = min(access_count / 10.0, 1.0)
```

**Issue**:
- Imported facts have `access_count=0` (never accessed)
- Imported facts have `turn_index=0` (import timestamp, not current conversation)
- **NO recency boost** for recently imported content

**Impact**: Older conversation facts score equally/higher than fresh imports

---

### Problem 3: NO IMPORT AWARENESS
**Where**: `retrieve_multi_factor()` line 984-1083
**Issue**:
- Scoring algorithm has NO special handling for `is_imported=true`
- No temporary boost for recent imports
- No detection of "just imported this content" context

**Impact**: System treats 2-year-old conversation and 2-minute-old import identically

---

### Problem 4: FILTER WINDOW TOO NARROW
**Where**: `context_filter.py` line 258
```python
recent_user_facts = user_facts[-10:]  # Last 10 user facts
```

**Issue**:
- Only shows last 10 user facts to filter LLM
- If 189 conversation facts exist before 27 imports, most imports invisible

**Impact**: Context filter may not see bulk of imported facts

---

## 6. WHY KAY FABRICATES

1. User asks: "what do you remember from the new documents?"
2. Query extracts: ["what", "remember", "from", "new", "documents"]
3. Imported facts about "[cat]", "[dog]", "hiking" have 0-12% keyword overlap
4. Conversation facts mentioning "remember", "you", "new" score HIGHER
5. Retrieval returns conversation memories (scores 0.5-0.8)
6. Imported facts (scores 0.2-0.3) filtered out
7. Kay builds context from conversation memories only
8. Kay has NO ACCESS to actual imported content
9. **Kay fabricates plausible details** ("Mochi the cat", "blue mugs") based on patterns

---

## 7. PROPOSED FIXES

### Fix 1: IMPORT RECENCY BOOST (CRITICAL)
**Target**: `retrieve_multi_factor()` line 1045
**Change**: Add temporary boost for recently imported facts

```python
# NEW: Import recency boost
import_boost = 1.0
if mem.get("is_imported", False):
    # Boost imported facts for 50 turns after import
    turns_since_import = self.current_turn - mem.get("turn_index", 0)
    if turns_since_import < 50:
        # Decay from 3.0x boost (immediate) to 1.0x (after 50 turns)
        import_boost = 1.0 + (2.0 * max(0, (50 - turns_since_import) / 50))
        print(f"[RETRIEVAL] Boosting imported fact (turns_since={turns_since_import}): {import_boost:.1f}x")

base_score = base_score * import_boost
```

**Effect**:
- Freshly imported facts get 3.0x score multiplier
- Decays linearly to 1.0x over 50 turns
- Query "what do you remember from new documents?" now surfaces imports

---

### Fix 2: IMPORT-AWARE QUERY DETECTION (HIGH PRIORITY)
**Target**: `retrieve_multi_factor()` line 974
**Change**: Detect queries about imports and boost all imported facts

```python
# Detect import-related queries
query_lower = user_input.lower()
is_import_query = any(phrase in query_lower for phrase in [
    "new document", "just imported", "what do you remember from",
    "recent import", "added to memory", "uploaded"
])

if is_import_query:
    print("[RETRIEVAL] Import query detected - boosting all imported facts")
```

Then in scoring:
```python
if is_import_query and mem.get("is_imported", False):
    base_score *= 5.0  # Massive boost for import queries
```

**Effect**: Asking about "new documents" directly boosts imported content

---

### Fix 3: TAG IMPORTED FACTS AT STORAGE (MEDIUM PRIORITY)
**Target**: `import_manager.py` line 407-447
**Change**: Add special tags to make imported facts more discoverable

```python
return {
    "fact": fact.text,
    "user_input": fact.text,
    "response": "",
    "type": "extracted_fact",
    "perspective": fact.perspective,
    "topic": fact.topic,
    "entities": fact.entities,
    "emotion_tags": ["imported_content"],  # NEW: Add import tag
    "importance": fact.importance,
    "tier": fact.tier,
    "turn_index": self.memory_engine.current_turn,
    "is_imported": True,
    "import_timestamp": datetime.now().isoformat(),  # NEW: Track when imported
    # ... rest of fields
}
```

**Effect**: Imported facts tagged with emotion="imported_content" for easier filtering

---

### Fix 4: EXPAND CONTEXT FILTER WINDOW (LOW PRIORITY)
**Target**: `context_filter.py` line 258
**Change**: Show more recent facts if imports are present

```python
# Check if any recent facts are imported
has_recent_imports = any(m.get("is_imported", False) for i, m in user_facts[-20:])

if has_recent_imports:
    recent_user_facts = user_facts[-20:]  # Expand window for imports
else:
    recent_user_facts = user_facts[-10:]  # Normal window
```

**Effect**: Context filter sees more imported facts

---

## 8. RECOMMENDED IMPLEMENTATION ORDER

1. **Fix 1 (Import Recency Boost)** - 5 minutes
   - Simple multiplier based on turn count
   - Immediate impact on retrieval
   - Zero breaking changes

2. **Fix 2 (Import Query Detection)** - 10 minutes
   - Detects user asking about imports
   - Boosts imported facts specifically
   - High user-facing value

3. **Fix 3 (Import Tagging)** - 15 minutes
   - Requires re-import of data
   - Enables better long-term tracking
   - Provides import_timestamp field

4. **Fix 4 (Context Filter)** - 10 minutes
   - Low risk change
   - Improves but not critical
   - Nice-to-have

---

## 9. TEST CASE

### Scenario:
1. Import document containing: "Re experienced PTSD from Kroger incident"
2. User asks: "what do you remember from the new documents?"

### Current Behavior (BROKEN):
- Query: ["what", "remember", "from", "new", "documents"]
- Imported fact "Re experienced PTSD..." scores 0.3
- Conversation facts mentioning "remember" score 0.6+
- Kay retrieves: conversation memories
- Kay response: Fabricates "Mochi the cat", "blue mugs" (hallucination)

### Expected Behavior (FIXED):
- Query: ["what", "remember", "from", "new", "documents"]
- Import query detected → apply 5.0x boost
- Imported fact "Re experienced PTSD..." scores 1.5 (0.3 * 5.0)
- Kay retrieves: imported facts about PTSD, Kroger
- Kay response: "From the documents, I remember you experienced PTSD related to an incident at Kroger..."

---

## 10. VERIFICATION COMMAND

After fixes, run:
```bash
python -c "
from engines.memory_engine import MemoryEngine
from agent_state import AgentState

memory = MemoryEngine()
state = AgentState()
state.memory = memory

# Test import query
memory.recall(state, 'what do you remember from the new documents?')
print(f'Retrieved {len(state.last_recalled_memories)} memories')

# Check if imported facts present
imported_count = sum(1 for m in state.last_recalled_memories if m.get('is_imported', False))
print(f'Imported facts: {imported_count}')

# Should be > 5 imported facts if fix works
assert imported_count >= 5, 'FIX FAILED: No imported facts retrieved!'
print('[SUCCESS] Imported facts now retrievable!')
"
```

---

## CONCLUSION

The import pipeline works perfectly. The retrieval pipeline has a semantic mismatch:
- **Storing**: "[cat] is a gray husky"
- **Querying**: "what do you remember from new documents?"
- **Problem**: Zero keyword overlap = near-zero score

**Solution**: Add temporal awareness to scoring. Recently imported facts need temporary boost regardless of keyword match.

**Minimal fix**: Implement Fix 1 (Import Recency Boost) - 5 lines of code, immediate impact.
