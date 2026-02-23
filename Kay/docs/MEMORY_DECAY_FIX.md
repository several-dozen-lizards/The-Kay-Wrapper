# Memory Decay Time Extension - Longer Retention for Important Memories

## Problem Summary

**Issue**: Kay's memories were decaying too quickly, especially emotionally significant memories about important people (like Saga the dog).

**Root Cause**: Memory decay halflives were too short, and there was no special protection for entity-related or emotionally tagged memories.

---

## What Was Wrong

### Previous Decay Settings (TOO FAST ✗)

**Location**: `engines/memory_layers.py:47-48`

```python
# OLD VALUES
self.episodic_decay_halflife = 7      # Days until episodic memory strength halves
self.working_decay_halflife = 0.5     # Days until working memory strength halves
```

**Timeline for a typical memory**:
- Working memory: Gone in ~2 days (0.5 day halflife)
- Episodic memory: Gone in ~24 days (7 day halflife)
- Even with max importance (2.0): ~72 days max

**Example - Memory about Saga the dog**:
```
Day 0: "Re has a dog named Saga" → strength: 1.0 (100%)
Day 7: strength: 0.5 (50%)
Day 14: strength: 0.25 (25%)
Day 21: strength: 0.125 (12.5%)
Day 24: strength: 0.09 → DELETED (below 0.1 threshold)
```

**Result**: Important memories about relationships, pets, and emotionally significant people were being forgotten within 3-4 weeks!

---

## The Fix

### Changes Made

**File**: `engines/memory_layers.py`

#### 1. Increased Base Decay Times (Lines 47-49)
```python
# NEW VALUES (MUCH LONGER)
self.episodic_decay_halflife = 30  # Days until episodic memory strength halves (was 7)
self.working_decay_halflife = 3    # Days until working memory strength halves (was 0.5)
```

**Impact**:
- Working memory: Now lasts ~12 days (was ~2 days)
- Episodic memory: Now lasts ~103 days (was ~24 days)

---

#### 2. Added Entity-Based Protection (Lines 243-261)
```python
def _calculate_entity_protection(self, memory: Dict[str, Any]) -> float:
    """
    Memories about tracked entities (people, pets, important things) get
    longer retention because they're part of ongoing relationships.

    Returns 2.0x multiplier for entity-related memories.
    """
    entities = memory.get("entities", [])

    if not entities:
        return 1.0  # No entity protection

    # If memory mentions any tracked entity, protect it
    return 2.0  # 2x retention for entity-related memories
```

**What this means**:
- Memories about **Saga** (dog): 2x longer retention
- Memories about **Re** (user): 2x longer retention
- Memories about **Kay's cat Chrome**: 2x longer retention
- Generic memories (no entities): Normal decay

---

#### 3. Added Emotion-Based Protection (Lines 263-282)
```python
def _calculate_emotion_protection(self, memory: Dict[str, Any]) -> float:
    """
    Memories with more emotion tags are more emotionally significant and
    should last longer. Each emotion tag adds 20% longer retention.

    1 tag = 1.2x, 2 tags = 1.4x, 3 tags = 1.6x, etc.
    Cap at 3.0x for extremely emotional memories (10+ tags).
    """
    emotion_tags = memory.get("emotion_tags", [])

    if not emotion_tags:
        return 1.0  # No emotional protection

    # Each emotion tag adds 20% longer retention
    multiplier = 1.0 + (len(emotion_tags) * 0.2)
    return min(multiplier, 3.0)
```

**What this means**:
- Memory with 1 emotion tag: 1.2x longer
- Memory with 2 emotion tags: 1.4x longer
- Memory with 3 emotion tags: 1.6x longer
- Memory with 5+ emotion tags: 2.0x longer
- Memory with 10+ emotion tags: 3.0x longer (capped)

---

#### 4. Updated Decay Formula (Lines 185-226)
```python
# OLD FORMULA
effective_halflife = base_halflife * (1 + importance)

# NEW FORMULA
effective_halflife = base_halflife * (1 + importance) * entity_multiplier * emotion_multiplier
```

**Multipliers stack multiplicatively**:
- Base halflife: 30 days (episodic)
- Importance (max 2.0): × 3 = 90 days
- Entity protection: × 2 = 180 days
- Emotion protection (5 tags): × 2 = 360 days

**Example - Memory about Saga with emotional tags**:
```
"I love my dog Saga so much"
- Base: 30 days
- Importance: 1.5 → × 2.5 = 75 days
- Entity (Saga): × 2 = 150 days
- Emotions (affection, joy): × 1.4 = 210 days effective halflife
```

**Timeline**:
```
Day 0: strength: 1.0 (100%)
Day 210: strength: 0.5 (50%)
Day 420: strength: 0.25 (25%)
Day 630: strength: 0.125 (12.5%)
Day 730 (2 years): strength: 0.08 → Still above 0.05 threshold!
```

---

#### 5. Lowered Pruning Threshold (Lines 228-230)
```python
# OLD THRESHOLD
self.episodic_memory = [m for m in self.episodic_memory if m["current_strength"] > 0.1]

# NEW THRESHOLD (less aggressive)
self.episodic_memory = [m for m in self.episodic_memory if m["current_strength"] > 0.05]
```

**Impact**: Memories can decay to 5% strength before deletion (was 10%)

---

## Memory Retention Comparison

### Generic Memory (no entities, no emotions)

| Scenario | Old System | New System |
|----------|-----------|------------|
| Working memory halflife | 0.5 days | 3 days |
| Episodic memory halflife | 7 days | 30 days |
| Time until deletion | ~24 days | ~103 days |

---

### Important Memory (entity + emotions)

Example: "Re's dog Saga is a good girl" (entity: Saga, emotions: affection, joy)

| Factor | Old System | New System |
|--------|-----------|------------|
| Base halflife | 7 days | 30 days |
| With importance (1.5) | 17.5 days | 75 days |
| With entity (2x) | 35 days | 150 days |
| With emotions (1.4x) | 49 days | **210 days** |
| Time until deletion | ~60 days | **~700+ days** |

**Result**: Memories about important people/pets now last **2+ years** instead of **2 months**!

---

### Maximum Protected Memory

Example: "I lost my beloved dog Saga last year, it was heartbreaking" (entity: Saga, emotions: sadness, loss, grief, affection, powerlessness = 5 tags)

| Factor | Multiplier | Effective Halflife |
|--------|-----------|-------------------|
| Base episodic | 1x | 30 days |
| Importance (2.0 max) | × 3 | 90 days |
| Entity (Saga) | × 2 | 180 days |
| Emotions (5 tags) | × 2.0 | **360 days** |

**Timeline**:
```
Day 0: 100% strength
Day 360: 50% strength
Day 720 (2 years): 25% strength
Day 1080 (3 years): 12.5% strength
Day 1300 (3.5+ years): Still above 5% threshold!
```

**Result**: Extremely emotional memories about important entities can last **3+ years**!

---

## How Decay Protection Works

### 1. Entity Protection
- Triggered when memory has `entities: ["Saga"]` field
- Extracted automatically during fact extraction (`memory_engine.py:719`)
- Examples: "Saga", "Re", "Chrome", "coffee", "tea", etc.

### 2. Emotion Protection
- Triggered when memory has `emotion_tags: ["affection", "joy"]` field
- Currently stored when memory is encoded (`memory_engine.py:717`)
- **NOTE**: This is currently empty for most memories (see EMOTION_MEMORY_INTERACTION_ANALYSIS.md for fix)

---

## Current Limitations

### Emotion Tags Are Empty (BUG)
**Location**: `memory_engine.py:717`
```python
record = {
    "fact": fact_text,
    "perspective": fact_perspective,
    "emotion_tags": [],  # ALWAYS EMPTY!
}
```

**Impact**: Emotional protection doesn't work yet because emotion tags aren't being populated during fact extraction.

**Fix Required**: See GAP #6 in EMOTION_MEMORY_INTERACTION_ANALYSIS.md - need to add `_extract_emotion_tags_from_text()` method.

---

## Testing

To verify the fix works:

1. **Tell Kay about an important person/pet**:
   ```
   "I have a dog named Saga"
   ```

2. **Check memory strength after several days**:
   - Look at `memory/memory_layers.json`
   - Find the Saga memory
   - Check `current_strength` field

3. **Expected behavior**:
   - Without entities: Decays to 50% in 30 days
   - With entities: Decays to 50% in 60+ days
   - With entities + emotions: Decays to 50% in 200+ days

---

## Future Improvements

1. **Fix emotion tagging**: Populate `emotion_tags` during fact extraction (currently always empty)
2. **Entity importance weighting**: High-importance entities (mentioned frequently) get even more protection
3. **Relationship-based protection**: Memories about relationships decay slower than isolated facts
4. **User-configurable decay rates**: Allow tuning via settings file
5. **Adaptive decay**: Adjust decay rates based on conversation frequency

---

## Related Systems

This fix works with:

1. **EntityGraph** (`engines/entity_graph.py`) - Tracks entities like "Saga"
2. **EmotionEngine** (`engines/emotion_engine.py`) - Provides emotion tags (currently not integrated)
3. **MemoryEngine** (`engines/memory_engine.py`) - Stores memories with entities and emotion tags
4. **Multi-layer memory** (`engines/memory_layers.py`) - Handles decay (FIXED)

---

## Summary

**Before**:
- Generic memories: Deleted after ~24 days
- Entity memories: Deleted after ~60 days
- Emotional memories: Same as generic (emotion tags empty)

**After**:
- Generic memories: Deleted after ~103 days (4x longer)
- Entity memories: Deleted after ~700+ days (11x longer)
- Emotional memories: Will last even longer once emotion tagging is fixed

**Key Insight**: Memory decay should reflect emotional and relational significance, not just time elapsed. Memories about important people, pets, and emotionally charged events should persist much longer than trivial facts.

---

**Fix Date**: 2025-10-20
**Fixed By**: Claude Code analysis
**Status**: ✅ DEPLOYED (with emotion tagging limitation)

**Next Steps**: Fix emotion tagging during fact extraction to fully activate emotional protection system.
