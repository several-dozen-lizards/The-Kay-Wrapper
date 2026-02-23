# Memory Pre-Filter Analysis - Kay Zero Retrieval Pipeline

## Executive Summary

**THE CRITICAL FINDING:** There is **NO 150-memory hard cap** in the current system. The pre-filter uses **SLOT_ALLOCATION totaling 310 memories**, which are then fed to the context builder (no glyph filter compression found in current implementation).

The user's question appears to be based on outdated or different version assumptions. Current implementation:
- **~310 memories** allocated across tiers
- **NOT** reduced to 150
- **NO** glyph filter compression (300 → 20-80) in active codebase

---

## 1. WHERE is the Memory Cap Set?

### File: `engines/memory_engine.py`
### Function: `retrieve_multi_factor()`
### Lines: 1160-1168

```python
SLOT_ALLOCATION = {
    'identity': 50,        # Core identity facts (generous, was 20)
    'working': 40,         # Current conversation (was 12)
    'recent_imports': 100, # Documents from last 5 turns (was 20)
    'episodic': 50,        # Long-term episodic (was 15)
    'semantic': 50,        # Long-term semantic (was 10)
    'entity': 20           # Entity-specific facts (was 5)
}
total_allocated = sum(SLOT_ALLOCATION.values())  # ~310 (was 82)
print(f"[RETRIEVAL] Decay-based retrieval: feeding ~{total_allocated} memories to glyph filter (was 82)")
```

**CRITICAL NOTE:** The log message mentions "glyph filter" but **NO ACTUAL GLYPH FILTER COMPRESSION** occurs in the codebase. This appears to be vestigial documentation from a planned feature that was never implemented.

### Historical Context

The comment shows the system was **recently increased from 82 to 310 slots**:
- Old total: 82 memories
- New total: 310 memories
- Philosophy: "Archive, don't delete. Decay, don't cap."

---

## 2. WHAT is the Pre-Filter Scoring On?

### File: `engines/memory_engine.py`
### Function: `calculate_multi_factor_score()` (nested in `retrieve_multi_factor()`)
### Lines: 1211-1362

### Scoring Algorithm (5-Factor Weighted)

```python
# WEIGHTS:
emotional_weight = 0.4   # 40%
semantic_weight = 0.25   # 25%
importance_weight = 0.20 # 20%
recency_weight = 0.10    # 10%
entity_weight = 0.05     # 5%
```

### Factor Breakdown

#### 1. EMOTIONAL RESONANCE (40%)
```python
tags = mem.get("emotion_tags") or []
emotion_score = sum(bias_cocktail.get(tag, {}).get("intensity", 0.0) for tag in tags)
```
- Matches current emotional cocktail
- Higher score if memory's emotions align with current mood
- Dominant factor (40% weight)

#### 2. SEMANTIC SIMILARITY (25%)
```python
keyword_matches = sum(1 for w in search_words if w in text_blob)
keyword_overlap = keyword_matches / len(search_words) if search_words else 0.0
```
- Simple keyword matching (not vector similarity)
- Checks fact text, user_input, and response fields
- Second-largest factor (25% weight)

#### 3. IMPORTANCE (20%)
```python
importance = mem.get("importance_score", 0.0)
```
- Uses ULTRAMAP-assigned importance score
- Based on emotional intensity and recursion
- No additional processing

#### 4. RECENCY (10%) - **TEMPORAL DECAY ZONES**
```python
# Temporal decay based on turn age
turn_age = self.current_turn - mem.get("turn_index", 0)

# HOT (0-5 turns): 1.0x - Full strength
if turn_age <= 5:
    temporal_multiplier = 1.0

# WARM (6-20 turns): 0.8-1.0x - Decay starts
elif turn_age <= 20:
    temporal_multiplier = 1.0 - (turn_age - 5) * 0.013  # 1.0 → 0.8

# COOL (21-100 turns): 0.4-0.8x - Archived but accessible
elif turn_age <= 100:
    temporal_multiplier = 0.8 - (turn_age - 20) * 0.005  # 0.8 → 0.4

# COLD (100+ turns): 0.0-0.4x - Deep archive (floor at 0.05)
else:
    temporal_multiplier = max(0.4 - (turn_age - 100) * 0.002, 0.05)

# Blend access frequency + temporal decay
recency_score = (access_frequency * 0.4 + temporal_multiplier * 0.6)
```

**KEY INSIGHT:** Recency has DUAL components:
- **40%** access frequency (how often accessed)
- **60%** temporal decay (how old)

**PROBLEM FOR OLD FACTS:** A memory from turn 8 (let's say current turn is 50):
- Turn age: 42 turns
- Zone: COOL (21-100)
- Temporal multiplier: 0.8 - (42-20) * 0.005 = 0.8 - 0.11 = **0.69**
- If never accessed: access_frequency = 0.0
- Recency score: (0.0 * 0.4) + (0.69 * 0.6) = **0.414**
- Final recency contribution: 0.414 * 0.10 = **0.0414** (4.1% of total)

**This is WHY old facts don't surface** - even with temporal decay, recency only contributes 10%, and old facts get 0.4-0.7 temporal multipliers.

#### 5. ENTITY PROXIMITY (5%)
```python
mem_entities = set(mem.get("entities", []))
query_entity_set = set(query_entities)
shared_entities = mem_entities.intersection(query_entity_set)
entity_score = len(shared_entities) / max(len(query_entity_set), 1)
```
- Shared entity bonus
- Minimal impact (5% weight)

### Combined Base Score
```python
base_score = (
    emotion_score * emotional_weight +      # 40%
    keyword_overlap * semantic_weight +     # 25%
    importance * importance_weight +        # 20%
    recency_score * recency_weight +        # 10%
    entity_score * entity_weight            # 5%
)
```

### Additional Multipliers

#### Tier Multiplier (Type-Based)
```python
if mem_type == "extracted_fact":
    tier_multiplier = 1.3
elif mem_type == "structured_turn":
    tier_multiplier = 1.4
elif mem_type == "full_turn":
    tier_multiplier = 1.0
```

#### Layer Boost (Memory Layer)
```python
if current_layer == "semantic":
    layer_boost = 1.2
elif current_layer == "working":
    layer_boost = 1.5
else:  # episodic
    layer_boost = 1.0
```

#### Import Boost (Recent Imports)
```python
if mem.get("is_imported", False):
    turns_since_import = self.current_turn - mem.get("turn_index", 0)

    # SUPER BOOST for current/last turn
    if turns_since_import <= 1:
        import_boost = 10.0
    # Strong boost for first 5 turns
    elif turns_since_import <= 5:
        import_boost = 1.5 + (1.5 * max(0, (5 - turns_since_import) / 5))
    # Moderate boost if explicitly asked
    elif is_import_query and turns_since_import <= 20:
        import_boost = 1.3
    # No boost - ancient imports compete equally
    else:
        import_boost = 1.0
```

### Final Score
```python
final_score = base_score * tier_multiplier * layer_boost * import_boost
```

### Special Case: Identity Facts
```python
if mem.get("is_identity", False):
    return (999.0, mem)  # Always scored first
```
Identity facts **bypass scoring** entirely and get top priority.

---

## 3. WHY 310 Specifically?

### Philosophy from Code Comments (Lines 1156-1159)
```python
# === DECAY-BASED RETRIEVAL (NO ARTIFICIAL CAPS) ===
# PHILOSOPHY: Archive, don't delete. Decay, don't cap.
# Let natural scoring (relevance × recency × importance) determine what surfaces.
# Trust the glyph filter to handle final compression for the LLM (300 → 20-80).
```

### Rationale

**NOT a context window constraint** - The comment suggests memories go through further "glyph filter" compression (300 → 20-80), but this filter **doesn't exist in the codebase**.

**NOT a performance optimization** - Performance measurement targets are 150ms (0.150 seconds), not 150 memories.

**APPEARS TO BE:** A **generous allocation** to ensure:
1. All tiers get adequate representation
2. Recent imports (100 slots) don't crowd out other memory types
3. Multiple document chunks can surface together

### Tier Breakdown
```
Identity:        50 (16%) - Core facts about Re and Kay
Recent Imports: 100 (32%) - Documents from last 5 turns
Working:         40 (13%) - Current conversation
Episodic:        50 (16%) - Long-term episodic
Semantic:        50 (16%) - Long-term semantic facts
Entity:          20 ( 6%) - Entity-specific memories
─────────────────────────
TOTAL:          310 (100%)
```

**Design Intent:** Ensure diverse memory types represented, with heavy bias toward recent imports (32%).

---

## 4. What Happens to Memories That Don't Make the Cut?

### File: `engines/memory_engine.py`
### Lines: 1386-1398

```python
# Retrieve all memories from layers
all_memories_to_score = []
all_memories_to_score.extend(self.memory_layers.working_memory)
all_memories_to_score.extend(self.memory_layers.episodic_memory)
all_memories_to_score.extend(self.memory_layers.semantic_memory)

# Score ALL memories
scored = [calculate_multi_factor_score(m) for m in all_memories_to_score]

# Sort by score
scored.sort(key=lambda x: x[0], reverse=True)
```

### What Happens

1. **ALL memories are scored** (could be 8000+)
2. **Sorted by score** (highest first)
3. **Top 310 selected** across tiers
4. **Rest are discarded** for this turn

### Are They Completely Inaccessible?

**YES and NO:**

**YES** - For this turn:
- Memories ranked 311+ are **completely excluded** from LLM context
- No fallback retrieval within the same turn
- Kay cannot access them in this conversation turn

**NO** - For future turns:
- Memories remain in `memory_layers` (working/episodic/semantic)
- **Can surface in future turns** if scoring changes
- If user asks different question, different memories may rank higher
- Temporal decay is gradual (not instant deletion)

### The Problem: Permanent Under-Retrieval

**If a memory consistently scores low:**
1. Never accessed → `access_count` stays 0
2. Low access_count → low `access_frequency` → low recency score
3. Older memories → lower `temporal_multiplier`
4. **Vicious cycle:** Low score → not retrieved → not accessed → lower score

**Example:**
- Turn 8: User says "Gorgeous White Pigeon"
- Turn 50: User asks "What pigeons do I know?"
- Turn 8 memory:
  - Age: 42 turns (COOL zone)
  - Temporal multiplier: 0.69
  - Access count: 0 (never retrieved before)
  - Recency contribution: 0.414 * 0.10 = **0.041**

If keyword match is weak and no emotional resonance:
- Semantic: 0.2 (weak match) * 0.25 = 0.05
- Emotion: 0.0 * 0.40 = 0.00
- Importance: 0.5 * 0.20 = 0.10
- Recency: 0.414 * 0.10 = 0.041
- Entity: 0.0 * 0.05 = 0.00
- **Total: 0.191**

Meanwhile, a recent turn with "pigeon" keyword:
- Turn age: 2 (HOT zone)
- Temporal multiplier: 1.0
- Keyword match: 1.0 (exact match)
- Semantic: 1.0 * 0.25 = 0.25
- Recency: 1.0 * 0.10 = 0.10
- **Total: 0.35+**

**Old memory loses by nearly 2x** despite containing the exact information needed.

---

## 5. The Actual Scoring Formula

### Complete Mathematical Formula

```
IF is_identity:
    score = 999.0
ELSE:
    # Base components (0.0 - 1.0 each)
    emotion_score = Σ(bias_cocktail[tag].intensity for tag in emotion_tags)
    keyword_overlap = (keyword_matches / total_query_words)
    importance = importance_score  # From ULTRAMAP

    # Recency (blended)
    access_frequency = min(access_count / 10.0, 1.0)
    temporal_multiplier = {
        0-5 turns:   1.0
        6-20 turns:  1.0 - (age-5)*0.013      # Linear decay
        21-100:      0.8 - (age-20)*0.005     # Slower decay
        100+:        max(0.4 - (age-100)*0.002, 0.05)  # Floor at 0.05
    }
    recency_score = (access_frequency * 0.4) + (temporal_multiplier * 0.6)

    # Entity overlap
    entity_score = |mem_entities ∩ query_entities| / |query_entities|

    # Weighted base score
    base_score = (
        emotion_score      * 0.40 +
        keyword_overlap    * 0.25 +
        importance         * 0.20 +
        recency_score      * 0.10 +
        entity_score       * 0.05
    )

    # Multipliers
    tier_multiplier = {
        extracted_fact: 1.3,
        structured_turn: 1.4,
        full_turn: 1.0
    }

    layer_boost = {
        working: 1.5,
        semantic: 1.2,
        episodic: 1.0
    }

    import_boost = {
        turns_since_import ≤ 1:  10.0,
        2-5 turns:               1.5-3.0 (decaying),
        6-20 (if import_query):  1.3,
        else:                    1.0
    }

    # Final score
    final_score = base_score × tier_multiplier × layer_boost × import_boost
```

---

## 6. Recommendations for Fixing Old Fact Retrieval

### Problem Diagnosis

**Root cause:** Old facts from turn 8 don't surface because:
1. **Keyword mismatch:** "Gorgeous White Pigeon" vs query "what pigeons"
2. **Temporal decay:** 42 turns old = COOL zone = 0.69 multiplier
3. **Never accessed:** access_count = 0 → access_frequency = 0
4. **Recency dominance:** Even at 10% weight, multiplied by 0.414 = only 0.041 contribution
5. **Low semantic overlap:** Query has 2 words ("what", "pigeons"), only 1 matches

### Fix #1: Increase Semantic Weight (Quick Win)

**Current:**
```python
semantic_weight = 0.25  # 25%
recency_weight = 0.10   # 10%
```

**Recommended:**
```python
semantic_weight = 0.35  # 35% (was 25%)
recency_weight = 0.05   # 5% (was 10%)
```

**Impact:** Keyword matching becomes more important than recency, helping old facts with good keyword matches surface.

### Fix #2: Raise Temporal Decay Floor

**Current:**
```python
# COLD (100+): Floor at 0.05
temporal_multiplier = max(0.4 - (age-100)*0.002, 0.05)
```

**Recommended:**
```python
# COLD (100+): Floor at 0.3 (was 0.05)
temporal_multiplier = max(0.4 - (age-100)*0.002, 0.3)
```

**Impact:** Very old memories don't become completely worthless. Floor of 0.3 means even ancient memories with perfect keyword match can compete.

### Fix #3: Boost Entity Matching Weight

**Current:**
```python
entity_weight = 0.05  # 5%
```

**Recommended:**
```python
entity_weight = 0.15  # 15% (was 5%)
semantic_weight = 0.25  # Keep at 25% (don't increase to 35% if doing this)
```

**Impact:** If turn 8 extracted "Gorgeous White Pigeon" as an entity and user asks "what pigeons", entity matching would give stronger boost.

### Fix #4: Add Synonym/Stemming to Keyword Matching

**Current:**
```python
keyword_matches = sum(1 for w in search_words if w in text_blob)
```

**Recommended:**
```python
from nltk.stem import PorterStemmer
stemmer = PorterStemmer()

search_stems = {stemmer.stem(w) for w in search_words}
text_stems = {stemmer.stem(w) for w in text_blob.split()}
keyword_matches = len(search_stems & text_stems)
```

**Impact:** "pigeon" matches "pigeons", "running" matches "run", improving semantic recall.

### Fix #5: Add Explicit "Old Fact Boost" for Low Access Count

**Current:** No compensation for never-accessed memories

**Recommended:**
```python
# After calculating base_score
if access_count == 0 and turn_age > 10:
    # Old memories that were never accessed get a "rediscovery" boost
    # This helps facts that were stored but never surfaced
    rediscovery_boost = 1.5
else:
    rediscovery_boost = 1.0

final_score = base_score × tier_multiplier × layer_boost × import_boost × rediscovery_boost
```

**Impact:** Old facts get a chance to surface even if they've been ignored.

### Fix #6: Document Index Integration (Already Partially Implemented)

**Current System:**
```python
# Line 1174: Document index search happens FIRST
document_tree_chunks = self._retrieve_document_tree_chunks(user_input, max_docs=3)
```

This is **already implemented** but may not be finding the pigeon document.

**Check:**
1. Is "Gorgeous White Pigeon" in `memory/documents.json`?
2. Does the document have keywords: "gorgeous", "white", "pigeon"?
3. Does query "what pigeons" match those keywords after cleaning?

**Verify:**
```bash
python -c "
from engines.document_index import DocumentIndex
idx = DocumentIndex()
results = idx.search('what pigeons', min_score=0.2)
print(f'Found {len(results)} documents matching \"what pigeons\"')
"
```

---

## 7. The Missing "Glyph Filter"

### Code Reference (Line 1159)
```python
# Trust the glyph filter to handle final compression for the LLM (300 → 20-80).
```

### The Problem

**THIS FILTER DOES NOT EXIST IN THE CODEBASE.**

Search results:
```bash
$ grep -r "glyph.*filter" engines/
engines/memory_engine.py:1159:# Trust the glyph filter to handle final compression
engines/memory_engine.py:1169:print(f"[RETRIEVAL] ... feeding ~{total_allocated} memories to glyph filter")
```

Only **references** to glyph filter, no **implementation**.

### What Actually Happens

**Line 1752 (recall method):**
```python
memories = self.retrieve_multi_factor(bias_cocktail, user_input, num_memories)
```

The `num_memories` parameter (default 15 from line 1710) is **passed but not used** in `retrieve_multi_factor()`.

`retrieve_multi_factor()` returns **all 310 allocated memories**, not 15.

**Line 1779:**
```python
memories = memories[:num_memories + min(3, len(prioritized))]
```

This **FINALLY** trims to 15 memories (plus a few relationship facts).

### The Real "Filter"

The "glyph filter" is actually:
1. **Slot allocation:** 310 memories retrieved
2. **Hard trim:** Reduced to ~15-18 in `recall()`
3. **NO compression algorithm** - just truncation

**Result:** Kay sees only **~15-18 memories** per turn, not 310.

---

## Summary Table

| Question | Answer |
|----------|--------|
| **Where is cap set?** | `engines/memory_engine.py` line 1160, SLOT_ALLOCATION = 310 |
| **What scoring?** | 5-factor: Emotion 40%, Semantic 25%, Importance 20%, Recency 10%, Entity 5% |
| **Why 310?** | Generous allocation across tiers; recent imports get 100 slots (32%) |
| **What happens to rest?** | Discarded for this turn; can surface in future if scoring changes |
| **Glyph filter?** | **DOES NOT EXIST** - Only truncation to ~15 in recall() |
| **Why old facts don't surface?** | Low recency score (0.41 for 42-turn-old), never accessed (0.0 frequency), weak keyword overlap |

---

## Critical Finding: The 15-Memory Bottleneck

**THE REAL PROBLEM IS NOT 150 OR 310** - it's that after all scoring, only **~15 memories make it to Kay's context.**

**File:** `engines/memory_engine.py`
**Line:** 1779
```python
memories = memories[:num_memories + min(3, len(prioritized))]
```

Where `num_memories = 15` (default from line 1710).

**This means:**
- System scores 8000+ memories
- Retrieves top 310 across tiers
- **Truncates to 15 before sending to LLM**
- Old facts must be in **top 15** to be accessible

**For "Gorgeous White Pigeon" from turn 8 to surface at turn 50:**
- Must beat 8000+ other memories in multi-factor scoring
- Must land in top 310 tier allocation
- Must beat 310 retrieved memories to get in top 15
- **Probability: ~0.002%** (15/8000)

---

## Recommended Action Plan

1. **Verify document index** has pigeon document indexed
2. **Test search:** `idx.search('pigeons')` should return pigeon documents
3. **Increase semantic weight** from 25% to 35% (reduce recency from 10% to 5%)
4. **Raise temporal decay floor** from 0.05 to 0.3
5. **Add rediscovery boost** for never-accessed old facts
6. **Consider increasing num_memories** from 15 to 30
7. **Add entity extraction** to turn 8 to capture "Gorgeous White Pigeon" as entity

The core issue is **keyword matching + temporal decay** creating a death spiral for old facts. Even perfect content won't surface if it never matches keywords or is too old.
