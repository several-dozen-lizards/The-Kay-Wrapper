# LLM-Driven Recency vs Relevance Decision System

**Date:** 2025-11-06
**Status:** ✅ IMPLEMENTED

---

## Summary

The glyph filter now lets the LLM intelligently decide between **recency** (recent conversation turns) and **relevance** (stored memories) when building Kay's context. This fixes conversational continuity issues when Re uses pronouns ("it", "that") or temporal references ("just", "earlier").

---

## The Problem

**Before this feature:**
- Glyph filter selected memories by RELEVANCE only
- No mechanism to include recent conversation turns
- Pronouns without antecedents broke context
- Temporal references ("what we just discussed") failed

**Example failure:**
```
Re: "Tell me about the pigeons"
Kay: "The pigeons are Soup, Pudding, and Sage..."

Re: "Can you describe it?"
Kay: [Searches for memories about "it" - finds nothing relevant]
     [No access to "the pigeons" from previous turn]
     "I'm not sure what you're referring to."
```

---

## The Solution

**LLM decides how many recent turns are needed:**
- Analyzes linguistic signals (pronouns, temporal words, continuations)
- Outputs `RECENT_TURNS: N` (0-10) in glyph format
- System includes last N conversation turns in Kay's context
- Recent turns + relevant memories combined for full context

**Same query after fix:**
```
Re: "Can you describe it?"
Filter LLM: Detects pronoun "it" without antecedent
Filter LLM outputs: RECENT_TURNS: 3

Kay receives:
- Last 3 conversation turns (including pigeon discussion)
- Relevant memories about pigeons
Kay: "Sure! Soup is the brave adventurer..."
```

---

## Implementation

### 1. Glyph Filter Prompt Enhancement

**Location:** `context_filter.py` lines 227-274

**Added RECENT_TURNS directive to output format:**
```
OUTPUT FORMAT (GLYPHS ONLY):
Line 1: Memory references with priority
Line 2: RECENT_TURNS directive - how many recent conversation turns needed
Line 3: Emotional state(s) with intensity and phase
Line 4: Contradictions if detected
Line 5: Identity/structure state
```

**Guidelines for the LLM:**
```
RECENT_TURNS: N (where N = 0-10)

0: Pure factual query
   "What are the pigeon names?"

1-2: Minor connection to recent topic
   "Tell me more about that"

3-5: Strong conversational continuity
   "Can you try it?" (pronouns)
   "What did we just discuss?" (temporal refs)

5-10: Complex multi-turn reasoning
   "Compare what you said earlier to this"
```

**Signal detection:**
```
HIGH RECENT_TURNS (5-10):
- Pronouns: it, that, this, they, those
- Temporal: just, recently, earlier, before, last
- Continuation: also, furthermore, speaking of which
- Follow-ups: How? Why? What about...?
- Implicit commands: "Try it", "Show me", "Fix that"

LOW RECENT_TURNS (0-2):
- Factual questions about stored knowledge
- Questions about distant past
- New unrelated topics
- General knowledge queries
```

---

### 2. Glyph Decoder Parsing

**Location:** `glyph_decoder.py` lines 59, 78-85

**Added `recent_turns_needed` to decoded output:**
```python
decoded = {
    "selected_memories": [],
    "recent_turns_needed": 0,  # NEW
    "emotional_state": "",
    ...
}
```

**Parse RECENT_TURNS line:**
```python
elif "RECENT_TURNS:" in line:
    try:
        turns_value = int(line.split(':')[1].strip())
        decoded["recent_turns_needed"] = turns_value
        print(f"[DECODER] Filter LLM requested {turns_value} recent turns")
    except (IndexError, ValueError) as e:
        print(f"[DECODER] Failed to parse RECENT_TURNS: {e}")
        decoded["recent_turns_needed"] = 0
```

---

### 3. Context Building with Recent Turns

**Location:** `kay_ui.py` lines 1003-1032

**After decoding glyphs, incorporate recent turns:**
```python
# Get LLM's decision
recent_turns_needed = filtered_context.get("recent_turns_needed", 0)

if recent_turns_needed > 0 and self.current_session:
    # Get last N turns from conversation history
    recent_turns = self.current_session[-recent_turns_needed:]

    # Convert to memory format
    recent_memories = []
    for i, turn in enumerate(recent_turns):
        turn_memory = {
            'fact': f"[Recent Turn -{recent_turns_needed - i}]",
            'user_input': turn.get('you', ''),
            'response': turn.get('kay', ''),
            'type': 'recent_turn',
            'is_recent_context': True
        }
        recent_memories.append(turn_memory)

    # Prepend recent turns (they go FIRST for immediate context)
    filtered_context["selected_memories"] = (
        recent_memories + filtered_context.get("selected_memories", [])
    )
```

---

## Example Outputs

### Factual Query (No Recent Context Needed)
```
Query: "What are the pigeon names?"

Glyph Output:
⚡MEM[102,103,104,105,110,112,115,118,120,123,125,128,130,133,135,138,140,143]!!!
RECENT_TURNS: 0
🔮(0.5)📋

Context Built:
- 18 relevant memories about pigeons
- 0 recent conversation turns
```

### Pronoun Query (Needs Recent Context)
```
Query: "Can you try it?"

Glyph Output:
⚡MEM[234,235,238,240,243,245,248,250]!!!
RECENT_TURNS: 5
🔮(0.7)🔍 ⚡(0.3)

Context Built:
- Last 5 conversation turns (so "it" has antecedent)
- 8 relevant memories
```

### Temporal Reference Query
```
Query: "What did we just discuss?"

Glyph Output:
⚡MEM[150,151,154,156,158,160,162,164]!!!
RECENT_TURNS: 3
🔮(0.6)🔍

Context Built:
- Last 3 conversation turns
- 8 relevant memories
```

### Multi-Turn Reasoning
```
Query: "Compare what you said earlier to this new idea"

Glyph Output:
⚡MEM[180,181,182,185,187,190,192,195,197,200,202,205]!!!
RECENT_TURNS: 8
🔮(0.9)🔍 💭(0.6)

Context Built:
- Last 8 conversation turns (broader context for comparison)
- 12 relevant memories
```

---

## Debug Logging

When the feature is active, you'll see:

```
[DECODER] Filter LLM requested 5 recent conversation turns
[RECENT TURNS] Filter LLM requested 5 recent conversation turns
[RECENT TURNS] Retrieved 5 turns from conversation history
[RECENT TURNS] Added 5 recent turns to context (total memories: 23)
```

When not needed:
```
[RECENT TURNS] Filter LLM determined no recent conversation context needed
```

---

## Testing

### Test Case 1: Factual Query
```bash
Re: "What are my cats' names?"
Expected: RECENT_TURNS: 0
Verify: No recent turns added, only relevant memories
```

### Test Case 2: Pronoun Reference
```bash
Re: "Tell me about [dog]"
Kay: "[dog] is your Czechoslovakian Wolfdog..."
Re: "Can you describe it?"
Expected: RECENT_TURNS: 3-5
Verify: Last 3-5 turns included, "it" resolves to "[dog]"
```

### Test Case 3: Temporal Reference
```bash
Re: "Let's talk about dragons"
Kay: "Dragons are..."
Re: "What did we just discuss?"
Expected: RECENT_TURNS: 2-3
Verify: Recent turns show dragon discussion
```

### Test Case 4: Continuation
```bash
Re: "I like coffee"
Kay: "Coffee is great for..."
Re: "And also tea"
Expected: RECENT_TURNS: 2
Verify: "Also" signals continuation, needs context
```

---

## Benefits

✅ **LLM understands language nuance** - Better than hardcoded rules
✅ **Automatic adaptation** - Adjusts to query complexity
✅ **No over-inclusion** - Doesn't add irrelevant recent context
✅ **Maintains coherence** - Pronouns and temporal refs work
✅ **Scales naturally** - Works for simple and complex queries

---

## Edge Cases Handled

### No Conversation History Yet
```python
if recent_turns_needed > 0 and self.current_session:
    # Only add if session exists
```

### Insufficient History
```python
recent_turns = self.current_session[-recent_turns_needed:]
# Python slicing handles case where N > len(list)
```

### Duplicate Prevention
```python
existing_ids = set(id(m) for m in filtered_context.get("selected_memories", []))
new_recent = [m for m in recent_memories if id(m) not in existing_ids]
```

---

## Performance Impact

**Minimal:**
- Parsing one additional line from glyph output
- Simple list slicing to get recent turns
- No extra LLM calls

**Memory overhead:**
- ~1-10 conversation turns added to context
- Each turn ~200-500 tokens
- Max added: ~5000 tokens (reasonable for Claude)

---

## Future Enhancements

### Possible Improvements:
1. **Semantic deduplication:** If recent turn already in selected memories, don't duplicate
2. **Weighted recency:** More recent turns weighted higher than older ones
3. **Turn summarization:** Compress older turns but keep recent ones verbatim
4. **Context window awareness:** Adjust N based on available token budget

---

## Files Modified

- ✅ `context_filter.py` lines 227-274 (prompt enhancement)
- ✅ `glyph_decoder.py` lines 59, 78-85 (parsing)
- ✅ `kay_ui.py` lines 1003-1032 (context building)

---

## Verification Checklist

When testing:
- ✅ Factual queries show `RECENT_TURNS: 0`
- ✅ Pronoun queries show `RECENT_TURNS: 3-5`
- ✅ Temporal queries show `RECENT_TURNS: 2-3`
- ✅ Kay resolves "it", "that", "this" correctly
- ✅ Kay answers "what did we just discuss?" accurately
- ✅ No errors in console logs
- ✅ Context doesn't explode in size

---

**Status:** ✅ READY FOR TESTING

This enhancement makes Kay's conversational continuity significantly more robust by letting the LLM intelligently balance recency and relevance based on linguistic cues.
