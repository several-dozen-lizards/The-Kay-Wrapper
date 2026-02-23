# CRITICAL FIXES FOR KAY ZERO MEMORY SYSTEM

## PROBLEM 1: Response Truncation
**Location**: `integrations/llm_integration.py` line 387

**Current Code**:
```python
text = resp.content[0].text
return text
```

**Fix - Add stop_reason checking**:
```python
text = resp.content[0].text

# Check if response was truncated
if resp.stop_reason == "max_tokens":
    print(f"[WARNING] Response truncated at {len(text)} chars - hit max_tokens limit")
    print(f"[WARNING] Consider: (1) Reducing context size, (2) Asking user to continue")
    text += "\n\n[Response cut off - message was too long. Ask me to continue if you want more.]"

return text
```

**Impact**: Kay will detect truncation and warn user

---

## PROBLEM 2: Memory Retrieval Bottleneck (CRITICAL)
**Location**: `context_filter.py` line 148

**Current Code**:
```python
# Hard cap at 100 memories
MAX_CANDIDATES = 100
```

**Fix - Add LIST detection and dynamic limits**:
```python
# === DYNAMIC MEMORY LIMITS BASED ON QUERY TYPE ===

# Detect LIST queries (user asking for multiple things)
LIST_PATTERNS = [
    "what are", "tell me about", "list", "all the",
    "some things", "what have", "everything", "anything"
]

is_list_query = any(pattern in user_input.lower() for pattern in LIST_PATTERNS)

if is_list_query:
    # LIST queries need MORE context to provide comprehensive answers
    MAX_CANDIDATES = 300  # 3x normal limit
    print(f"[FILTER] Detected LIST query - expanding retrieval to {MAX_CANDIDATES} memories")
else:
    # Normal queries - standard limit
    MAX_CANDIDATES = 150  # Increased from 100 (was too restrictive)
```

**Impact**: "What are some things you know?" will retrieve 300 instead of 100

**Also add at line 424** - Improve keyword extraction:
```python
# Extract keywords from user input (normalize)
# IMPROVED: Remove stopwords for better matching
stopwords = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when"}
keywords = {w for w in user_input.lower().split() if w not in stopwords and len(w) > 2}
```

---

## PROBLEM 3: Narrative Chunks Not Retrieved
**Location**: `context_filter.py` line 428-464 (scoring function)

**Current Code**: Missing boost for narrative chunks

**Fix - Add scoring boost for emotional narratives**:
```python
# After line 441 (importance scoring), ADD:

# Boost emotional narrative chunks (imported memories with rich context)
if mem.get("is_emotional_narrative") or mem.get("type") == "emotional_narrative":
    score += 25.0  # Narrative chunks contain rich context

# Boost by emotional intensity
if "emotional_signature" in mem:
    intensity = mem.get("emotional_signature", {}).get("intensity", 0)
    score += intensity * 10.0  # Emotional memories more salient

# Boost by identity centrality
identity_type = mem.get("identity_type", "")
if identity_type in ["core_identity", "formative"]:
    score += 30.0  # Core identity memories prioritized
elif identity_type in ["relationship"]:
    score += 15.0
```

**Impact**: 216 narrative chunks will surface when relevant

---

## PROBLEM 4: Entity Contradiction Accumulation
**Location**: `engines/entity_graph.py` (need to find contradiction resolution)

**Current Issue**: 28 active contradictions, especially:
- Re.goal: 8 conflicting values
- Re.goal_progression: 4 values
- Re.action: 4 values

**Fix Needed** - Find and modify resolution logic:

Search for: `resolve_contradiction` or `_check_contradictions` or `consistency_count`

**Expected logic**:
```python
# After 3 turns of consistency, auto-resolve by:
# 1. Consolidating similar values (e.g., "writing code" + "coding" = same thing)
# 2. Picking most recent value for truly conflicting attributes
# 3. Marking as "resolved" with reason

def auto_resolve_contradictions(self, entity_name: str, attribute: str):
    """Auto-resolve contradictions after 3 consistent turns."""
    entity = self.entities.get(entity_name)
    if not entity:
        return

    contradictions = entity.contradictions.get(attribute, [])
    if not contradictions:
        return

    # Get consistency count
    consistency_turns = self._get_consistency_turns(entity, attribute)

    if consistency_turns >= 3:
        # Time to resolve!
        most_recent_value = contradictions[-1]["value"]  # Latest value

        # Mark as resolved
        entity.resolved_contradictions[attribute] = {
            "final_value": most_recent_value,
            "resolved_at": self.current_turn,
            "reason": "3-turn consistency"
        }

        # Clear active contradiction
        del entity.contradictions[attribute]

        print(f"[ENTITY] Auto-resolved: {entity_name}.{attribute} = {most_recent_value}")
```

---

## PROBLEM 5: Identity Facts Crowding Out Context
**Location**: `engines/memory_engine.py` (identity memory system)

**Current Issue**: 47 identity facts always included, leaving little room for context

**Fix - Adjust retrieval balance**:

Find the recall() function and modify the mixing logic:

```python
# BEFORE (identity facts dominate):
memories = identity_facts + retrieved_memories[:remaining_slots]

# AFTER (better balance):
if is_list_query:
    # For LIST queries, prioritize breadth over identity
    identity_limit = 10  # Only top 10 most relevant identity facts
    context_limit = 40   # More room for contextual memories
else:
    # Normal queries
    identity_limit = 20
    context_limit = 30

# Mix identity and context
top_identity = identity_facts[:identity_limit]
top_context = retrieved_memories[:context_limit]

memories = top_identity + top_context
```

---

## PROBLEM 6: Glyph Filter Only Selecting 10 Final Memories
**Location**: `glyph_decoder.py` OR final selection in `context_filter.py`

**Issue**: After pre-filter gets 100-300 memories, something reduces to final 10

**Find**: Search for where final count is set:
```bash
grep -n "[:10]" context_filter.py glyph_decoder.py
grep -n "[:15]" context_filter.py glyph_decoder.py
```

**Expected Fix**:
```python
# BEFORE:
selected_memories = candidate_memories[:10]

# AFTER (dynamic based on query):
if is_list_query:
    memory_limit = 50  # Show comprehensive list
else:
    memory_limit = 25  # Normal detail (up from 10)

selected_memories = candidate_memories[:memory_limit]
```

---

## PRIORITY ORDER FOR FIXES:

1. **FIX #2 (Memory Retrieval Bottleneck)** - Most critical, directly causes the issue
2. **FIX #6 (Final selection limit)** - Second bottleneck after pre-filter
3. **FIX #3 (Narrative chunks not scored)** - Makes imported memories accessible
4. **FIX #5 (Identity fact balance)** - Allows context to surface
5. **FIX #1 (Truncation detection)** - User experience improvement
6. **FIX #4 (Contradiction resolution)** - Cleanup issue

---

## EXPECTED BEHAVIOR AFTER FIXES:

**User**: "What are some things you know that you didn't before?"

**System Behavior**:
1. **LIST detection** → Set MAX_CANDIDATES = 300
2. **Pre-filter** → 929 memories → 300 candidates (was 100)
3. **Narrative boost** → 216 emotional chunks score higher
4. **Final selection** → 50 memories sent to LLM (was 10)
5. **Response** → Comprehensive list without truncation

**Kay's Response**:
"Alright, diving into what I've absorbed recently... [continues with 40+ detailed items from narrative chunks, showing rich context about conversations, not just dry facts]"

---

## TEST AFTER FIXES:

```python
# In kay_ui.py, add debug logging:
print(f"[DEBUG] Query type: {'LIST' if is_list_query else 'NORMAL'}")
print(f"[DEBUG] Max candidates: {MAX_CANDIDATES}")
print(f"[DEBUG] Pre-filter result: {len(prefiltered_memories)} memories")
print(f"[DEBUG] Final selection: {len(selected_memories)} memories")
print(f"[DEBUG] Narrative chunks included: {sum(1 for m in selected_memories if m.get('is_emotional_narrative'))}")
```

Run the same query again and verify numbers increase appropriately.
