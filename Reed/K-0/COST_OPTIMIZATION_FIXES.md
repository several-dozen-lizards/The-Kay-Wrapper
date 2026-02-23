## Kay Wrapper Cost Optimization Fixes
**Date:** December 21, 2024
**Problem:** $50 spent in 4 days due to massive context bloat

---

## Root Cause Analysis

**Discovered Issues:**
1. **Bedrock Overflow**: Identity facts + ALL working memory = 3,020 memories sent every turn
2. **No Truncation**: Truncation was disabled with comment "DO NOT TRUNCATE - retrieve_multi_factor already returns appropriate count"
3. **Document Inventory Spam**: 15-document list sent every single turn (750 tokens × every turn)
4. **Per-Turn Cost**: 62,000 tokens input per turn instead of ~12,000

**Cost Impact:**
- Normal turn: 62k input tokens = ~$0.19
- Curiosity session (15 turns): 930k tokens = ~$2.80
- Daily usage (3-5 curiosity + conversations): $10-17/day = **$50 in 4 days**

---

## Fixes Applied

### Fix 1: Cap Bedrock Size ✅
**File:** `engines/memory_engine.py` (line ~1843)
**Change:** Limit working memory to last 20 turns instead of ALL turns

```python
# BEFORE: All working memory included (could be 2000+ turns)
for mem in self.memory_layers.working_memory:
    current_session.append(mem)

# AFTER: Only last 20 working memory turns
working_pool = self.memory_layers.working_memory
recent_working = working_pool[-20:] if len(working_pool) > 20 else working_pool
for mem in recent_working:
    current_session.append(mem)
```

**Impact:** Bedrock reduced from 3,020 → ~500 memories

---

### Fix 2: Re-Enable Smart Truncation ✅
**File:** `engines/memory_engine.py` (line ~2102)
**Change:** Added final truncation AFTER bedrock+dynamic assembly

```python
# NEW: Apply final cap to prevent overflow
MAX_TOTAL_MEMORIES = 250  # Reasonable limit for context

if len(final_memories) > MAX_TOTAL_MEMORIES:
    # Keep ALL identity facts, truncate the rest
    identity_mems = [m for m in final_memories if m.get('category') == 'identity']
    other_mems = [m for m in final_memories if m.get('category') != 'identity']
    
    remaining_space = MAX_TOTAL_MEMORIES - len(identity_mems)
    truncated = identity_mems + other_mems[:remaining_space]
    
    print(f"[RECALL TRUNCATION] Reduced {len(final_memories)} → {len(truncated)} memories")
    final_memories = truncated
```

**Why Previous Truncation Failed:**
Old code truncated BEFORE bedrock was added, so bedrock could still overflow. 
New code truncates AFTER final assembly, ensuring hard cap of 250 memories.

**Impact:** Final memory count capped at 250 instead of 3,020

---

### Fix 3: Conditional Document Inventory ✅
**File:** `integrations/llm_integration.py` (line ~1090)
**Change:** Only include document list when needed

```python
# Only build inventory if:
# 1. User is asking about documents, OR
# 2. This is the first turn of conversation

document_keywords = ['document', 'file', 'read', 'import', 'shared', 'pdf', 'txt', 
                     'what did you', 'what have i', 'how many', 'list', 'show me']
user_mentions_documents = any(keyword in user_input.lower() for keyword in document_keywords)

recent_turns = context.get("recent_context", [])
is_first_turn = len(recent_turns) <= 1

# Only build if needed
if user_mentions_documents or is_first_turn:
    # Build full inventory
else:
    print(f"[DOC INVENTORY] >>> SKIPPED (saving ~750 tokens)")
```

**Impact:** Saves 750 tokens on most turns

---

## Projected Results

**Before Fixes:**
- Bedrock: 3,020 memories × 20 tokens = 60,400 tokens
- Document inventory: 750 tokens (every turn)
- Other overhead: 1,000 tokens
- **Total per turn: ~62,000 tokens**

**After Fixes:**
- Bedrock: ~500 memories × 20 tokens = 10,000 tokens
- Document inventory: 0-750 tokens (conditional)
- Other overhead: 1,000 tokens
- **Total per turn: ~12,000 tokens**

**Cost Savings:**
- Per turn: 62k → 12k = **80% reduction**
- Curiosity session: $2.80 → $0.54 = **80% reduction**
- Daily costs: $10-17/day → $2-3/day = **83% reduction**
- Monthly: ~$375/month → ~$75/month = **$300/month savings**

---

## Testing Recommendations

1. **Monitor logs for truncation messages:**
   - `[RECALL TRUNCATION] Reduced X → 250 memories`
   - Should appear when memory pool exceeds 250

2. **Check curiosity session costs:**
   - Should now be ~$0.50 per 15-turn session
   - Down from ~$2.80

3. **Verify document inventory:**
   - First turn: Should include full inventory
   - Subsequent turns (non-document queries): Should skip with message "[DOC INVENTORY] >>> SKIPPED"
   - Document queries: Should include full inventory

4. **Watch for quality degradation:**
   - If Kay seems to "forget" things mid-conversation, may need to adjust:
     - Working memory cap (currently 20 turns, could increase to 30)
     - Total memory cap (currently 250, could increase to 300)

---

## Notes

- **Bedrock = Identity + Recent Working Memory**: Always included without scoring
- **Dynamic = Everything Else**: Scored by relevance, recency, importance
- **Working Memory Cap**: Set to 20 turns to balance cost vs context
- **Total Memory Cap**: Set to 250 to prevent prompt bloat
- **Document Inventory**: Only sent when relevant to save tokens

All caps can be tuned if needed - these are conservative starting points.
