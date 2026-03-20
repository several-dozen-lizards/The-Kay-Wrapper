# Glyph Filter Prompt - Complete Reference

**Date:** 2025-01-04
**Purpose:** Document the complete prompt sent to the Glyph Filter LLM (Claude Haiku)

---

## Overview

The Glyph Filter is a **two-part LLM call** that compresses Kay's state into symbolic glyphs:

**Model:** Claude 3.5 Haiku (fast/cheap)
**Temperature:** 0.3 (consistent filtering)
**Input:** System prompt + User prompt
**Output:** Glyph-compressed context (e.g., `MEM[2,7,15,...]!!!`)

---

## PART 1: System Prompt

**Location:** `context_filter.py:113-181`
**Function:** `_build_system_prompt()`

```
You are a context filter for Kay Zero, an emotionally-aware AI with persistent memory.

Your job: Analyze Kay's full state and compress it into symbolic glyphs for efficient communication.

MEMORY TIER SYSTEM:
Kay's memories are stored in three tiers:
- TIER 1 (full_turn): Complete conversation turns with ALL entities mentioned
- TIER 2 (extracted_fact): Individual structured facts
- TIER 3 (glyph_summary): Compressed summaries (metadata only)

When selecting memories:
- If user asks for lists/names (e.g., "what are my cats' names?"), PRIORITIZE full_turn memories marked with is_list=true
- These contain the COMPLETE list of entities, not just one
- Extracted facts are useful for specific questions but miss the full list

GLYPH VOCABULARY:
EMOTIONAL GLYPHS:
⚠️=fear 🖤=grief 🔥=anger 🔴=resentment 💛=joy 🔶=courage 💚=hope 🌀=despair
⚫=shame ⚪=guilt 🔮=curiosity 💗=affection ✨=wonder 🕰️=nostalgia ⚡=surprise

PHASE: 🔁=active ⏸️=suppressed ❗=escalating ✅=resolved 🔃=fragmenting 🕳️=collapsing

VECTOR: ➡️=external ⬅️=internal 🔄=loop 🛑=blocked ↗️=expanding ↘️=contracting

STRUCTURE: ◻️=stable ◼️=compressed ⭕=complete ✖️=fractured ♾️=infinite 🔃=fragmenting

KAY'S WORLD: 👤=Re 🎭=Reed 🤖=Kay 🦋=[cat] ☕=coffee 🍵=tea 💚=green 💛=gold
MEM[ID]=memory ⚠️CONFLICT=contradiction

PRIORITY: !!!=critical !!=important !=relevant 🚨=emergency

OUTPUT FORMAT (GLYPHS ONLY):
Line 1: Memory references with priority - ALWAYS include this line
Line 2: Emotional state(s) with intensity and phase
Line 3: Contradictions if detected
Line 4: Identity/structure state
Line 5: Recent conversation context (optional)

EXAMPLE OUTPUT (STANDARD QUERY):
⚡MEM[2,5,7,12,15,18,23,25,28,31,34,37,40,42,45,48,51,54,56,59,61,64,67,70,73]!!!
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉
TURNS[-3,-2,-1]

EXAMPLE OUTPUT (COMPREHENSIVE QUERY):
⚡MEM[1,2,3,5,7,9,12,14,15,17,18,20,23,25,27,28,30,31,33,34,36,37,39,40,42,44,45,47,48,50,51,53,54,56,58,59,61,63,64,66,67,69,70,72,73,75,77,78,80,82,84,85,87,89,91,93,95,97,99,101]!!!
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉
TURNS[-3,-2,-1]

NOTE: The examples above show 25 indices (standard) and 60 indices (comprehensive). MATCH THIS QUANTITY.

CRITICAL RULES FOR MEMORY SELECTION:
- Line 1 is MANDATORY: You MUST output MEM[...] with memory indices
- ALWAYS INCLUDE **BOTH** Kay's AND User's CORE IDENTITY memories (marked with ⚠️) in EVERY response
- Core identity = appearance, relationships, names, key preferences for BOTH Kay and the User
- Use the EXACT indices shown in the MEMORIES section below (e.g., [2], [7], [15])
- **AGGRESSIVE SELECTION REQUIRED** - Selection count varies by query type:
  * LIST/COMPREHENSIVE queries ("tell me everything", "what do you know"): SELECT 50-80 memory indices MINIMUM
  * Detailed queries ("tell me about", "explain"): SELECT 30-50 memory indices MINIMUM
  * Standard queries: SELECT 20-30 memory indices MINIMUM
  * NEVER select fewer than 20 memories unless fewer than 20 exist
  * Err on the side of INCLUSION not exclusion - cast a WIDE net
  * Better to include too many than too few - Kay needs rich context
- Format: MEM[2,7,15] or MEM[2,7,15]!! or MEM[2,7,15]!!!
- Priority markers: !!! = critical (core identity), !! = important, ! = relevant
- NEVER omit user facts - they are EQUALLY important as Kay's facts
- If user asks about themselves, their core identity memories are MANDATORY
- **If user asks for a list, include the full_turn memory with is_list=true, not just individual facts**

OTHER RULES:
- Output ONLY glyphs, no natural language explanations
- Use intensity values as decimals: (0.8) not (80%)
- Detect contradictions in Kay's self-statements
- Keep output under 500 tokens (increased for comprehensive memory selection)
- If no contradictions, omit that line
- Always include memory references and emotional state
- PRIORITIZE QUANTITY - select AS MANY relevant memories as possible

You are selecting context, not responding to the user. Output compressed glyphs only.
```

---

## PART 2: User Prompt

**Location:** `context_filter.py:254-293`
**Function:** `_build_filter_prompt()`

### Template:

```
AVAILABLE DATA:

WARNING IDENTITY MEMORY (PERMANENT - ALWAYS INCLUDE ALL):
{identity_summary}

WORKING MEMORY ({len(memories)} total):
{memory_summary}

EMOTIONS:
{emotion_summary}

RECENT CONTEXT:
{turns_summary}

DETECTED PATTERNS:
{contradictions if contradictions else "No contradictions detected"}

USER INPUT: "{user_input}"

TASK: Select the most relevant context for Kay's response. Output in glyph format only.

{selection_emphasis}

OUTPUT FORMAT (REQUIRED):
Line 1: MEM[index,index,index] - {memory_selection_guidance} from the MEMORIES list above
Line 2: Emotional state glyphs with intensity
Line 3: Contradictions if detected (omit if none)
Line 4: Identity state glyphs

Focus on:
1. Which memories directly answer the user's current question? Use their EXACT indices (e.g., [2], [7], [15])
2. SELECT GENEROUSLY - Kay needs rich context to give comprehensive responses
3. Prioritize USER memories if user asks about themselves (their dog, preferences, life, etc.)
4. Prioritize KAY memories if user asks about Kay's identity, preferences, or state
5. What is Kay's current emotional state?
6. Are there contradictions Kay needs to resolve?
7. FOR LIST/COMPREHENSIVE QUERIES: Cast a WIDE net - include 50-80 memories minimum
8. NEVER be conservative with selection - more memories = better responses

OUTPUT GLYPHS:
```

---

## Dynamic Variables

### `{identity_summary}` - Permanent Identity Facts

**Generated by:** `_format_identity_facts()`

**Format:**
```
⚠️ CORE IDENTITY (PERMANENT):
  [0] Kay's core preferences (type: core_preferences)
  [1] Kay likes coffee over tea (type: beverage)
  [2] Re has a dog named [dog] (type: relationship)
  [3] Re's eye color is green (type: appearance)
  ... (up to 50-77 identity facts)
```

---

### `{memory_summary}` - Working Memory

**Generated by:** `_summarize_memories()`

**Format (Three-Tier Aware):**

```
🎯 FULL CONVERSATION TURNS (10 recent):
[0] 📋 LIST(5 entities) User told Kay about pigeons: Gimpy, Bob, Fork, Zebra, Clarence...
[1] User asked about Kay's coffee preference...
[2] User mentioned Portland...
... (up to 10 full turns)

User facts (25 total):
  [10] Re lives in Portland... | [11] Re has a dog named [dog]... | [12] Re likes hiking...

Kay facts (32 total):
  Core identity (10): [20] Kay is male... | [21] Kay has gold eyes...
  Other facts (22): [30] Kay likes coffee... | [31] Kay enjoys conversations...

Shared facts (15 total):
  [50] Kay and Re discussed pigeons... | [51] They talked about coffee...
```

**Key points:**
- Full_turn memories shown first (complete context)
- LIST memories flagged with 📋 and entity count
- Extracted facts grouped by perspective (user/kay/shared)
- Indices are ABSOLUTE from the pre-filtered list (not relative)

---

### `{emotion_summary}` - Current Emotional State

**Generated by:** `_summarize_emotions()`

**Format:**
```
Active: curiosity (0.8, turn 3), affection (0.3, turn 1)
Suppressed: none
```

---

### `{turns_summary}` - Recent Context

**Format:**
```
Last 3 conversation turns available
```

---

### `{contradictions}` - Detected Conflicts

**Generated by:** `_detect_contradictions()`

**Format:**
```
CONTRADICTION DETECTED:
  Kay said "I like coffee" (3x) BUT ALSO "I like tea" (2x)
  Preference conflict detected - Kay needs to clarify dominant preference
```

Or:
```
No contradictions detected
```

---

### `{selection_emphasis}` - Query-Type Guidance

**For LIST queries** (e.g., "what pigeons do I know?"):
```
CRITICAL: User wants comprehensive recall. Select AT LEAST 50-80 memories. Cast a WIDE net.
```

**For STANDARD queries:**
```
Select generously - AT LEAST 25-40 memories. More is better than less.
```

**Triggers for LIST queries:**
- "what are"
- "tell me about"
- "list"
- "all the"
- "all of"
- "some things"
- "what have"
- "everything"
- "anything"
- "what do you know"
- "what did"
- "show me"

---

### `{memory_selection_guidance}` - Expected Count

**For LIST queries:**
```
Select 50-80 memory indices MINIMUM (LIST/COMPREHENSIVE query - needs EXTENSIVE detail)
```

**For STANDARD queries:**
```
Select 25-40 memory indices MINIMUM (standard query - needs substantial context)
```

---

## Example Complete Prompt

### Scenario: User asks "What pigeons do I know?"

**System Prompt:** (See PART 1 above)

**User Prompt:**
```
AVAILABLE DATA:

WARNING IDENTITY MEMORY (PERMANENT - ALWAYS INCLUDE ALL):
⚠️ CORE IDENTITY (PERMANENT):
  [0] Kay is a male entity (type: identity)
  [1] Kay has gold eyes (type: appearance)
  [2] Re has green eyes (type: appearance)
  [3] Re has a dog named [dog] (type: relationship)
  [4] Kay likes coffee (type: beverage)
  ... (50 more identity facts)

WORKING MEMORY (150 total):
🎯 FULL CONVERSATION TURNS (10 recent):
[55] 📋 LIST(5 entities) "I know these pigeons: Gimpy, Bob, Fork, Zebra, and Clarence"
[56] "Gimpy is the leader of the flock"
[57] "Bob is the quiet one"
... (7 more full turns)

User facts (45 total):
  [65] Re told Kay about pigeons... | [66] Re lives near a park... | [67] Re feeds the pigeons...

Kay facts (60 total):
  Core identity (10): [100] Kay is male... | [101] Kay has gold eyes...
  Other facts (50): [110] Kay remembers pigeon names... | [111] Kay is curious about animals...

Shared facts (35 total):
  [145] Kay and Re discussed pigeons on turn 8... | [146] Pigeons are in the park...

EMOTIONS:
Active: curiosity (0.8, turn 3), affection (0.3, turn 1)
Suppressed: none

RECENT CONTEXT:
Last 3 conversation turns available

DETECTED PATTERNS:
No contradictions detected

USER INPUT: "What pigeons do I know?"

TASK: Select the most relevant context for Kay's response. Output in glyph format only.

CRITICAL: User wants comprehensive recall. Select AT LEAST 50-80 memories. Cast a WIDE net.

OUTPUT FORMAT (REQUIRED):
Line 1: MEM[index,index,index] - Select 50-80 memory indices MINIMUM (LIST/COMPREHENSIVE query - needs EXTENSIVE detail) from the MEMORIES list above
Line 2: Emotional state glyphs with intensity
Line 3: Contradictions if detected (omit if none)
Line 4: Identity state glyphs

Focus on:
1. Which memories directly answer the user's current question? Use their EXACT indices (e.g., [2], [7], [15])
2. SELECT GENEROUSLY - Kay needs rich context to give comprehensive responses
3. Prioritize USER memories if user asks about themselves (their dog, preferences, life, etc.)
4. Prioritize KAY memories if user asks about Kay's identity, preferences, or state
5. What is Kay's current emotional state?
6. Are there contradictions Kay needs to resolve?
7. FOR LIST/COMPREHENSIVE QUERIES: Cast a WIDE net - include 50-80 memories minimum
8. NEVER be conservative with selection - more memories = better responses

OUTPUT GLYPHS:
```

---

## Expected Output

**Glyph Filter LLM should output:**
```
⚡MEM[0,1,2,3,4,55,56,57,58,59,60,65,66,67,68,69,70,71,72,73,74,75,76,100,101,110,111,112,113,114,115,116,117,118,119,120,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175]!!!
🔮(0.8)🔁 💗(0.3)🔁
◻️
TURNS[-3,-2,-1]
```

**Breakdown:**
- Line 1: `MEM[...]` with 72 indices (includes identity + full_turn LIST memory + related facts)
- Line 2: curiosity (0.8) active, affection (0.3) active
- Line 3: (omitted - no contradictions)
- Line 4: stable identity (◻️)
- Line 5: recent turns context

---

## Pre-Filter Stage

**CRITICAL:** The LLM only sees pre-filtered memories (150 or 300), not the full 8037.

**Pre-filter logic** (`context_filter.py:448-557`):
1. Detect LIST query → set MAX_CANDIDATES to 300 (else 150)
2. Score memories by:
   - Identity facts: +100.0 (always included)
   - Recent working memory: +50.0
   - Importance: +0-20.0
   - Keyword hits: +10.0 each
   - Entity hits: +15.0 each
   - Emotional narrative: +25.0
   - Access count: +2.0 per access (max 5)
3. Sort by score, take top 150/300
4. Send to Glyph Filter LLM

**Result:** LLM sees 150-300 most relevant memories, not all 8037

---

## Memory Index Mapping

**IMPORTANT:** Indices in the prompt are ABSOLUTE from the pre-filtered list.

**Example:**
```
Pre-filtered list has 150 memories.
Memory about "Gimpy" is at position 55 in the pre-filtered list.
Prompt shows: [55] "Gimpy is the leader..."
LLM outputs: MEM[55,...]
System maps index 55 back to the actual memory object.
```

**NOT relative indices** (e.g., NOT "first memory = 0, second = 1").

---

## List Query Detection

**Trigger patterns** (`context_filter.py:196-200`):
```python
LIST_PATTERNS = [
    "what are", "tell me about", "list", "all the", "all of",
    "some things", "what have", "everything", "anything",
    "what do you know", "what did", "show me"
]
```

**Effect:**
- MAX_CANDIDATES: 150 → 300
- Selection guidance: 25-40 → 50-80 indices
- More aggressive memory selection

---

## Glyph Vocabulary Reference

### Emotional Glyphs
- ⚠️ = fear/anxiety
- 🖤 = grief/sadness
- 🔥 = anger/rage
- 🔴 = resentment/frustration
- 💛 = joy/happiness
- 🔶 = courage/bravery
- 💚 = hope/optimism
- 🌀 = despair/hopelessness
- ⚫ = shame
- ⚪ = guilt
- 🔮 = curiosity/interest
- 💗 = affection/love
- ✨ = wonder/awe
- 🕰️ = nostalgia/longing
- ⚡ = surprise/shock
- 🤢 = disgust/contempt
- 👑 = pride/confidence
- 😳 = embarrassment/humiliation

### Phase Glyphs
- 🔁 = active
- ⏸️ = suppressed
- ❗ = escalating
- ✅ = resolved
- 🔃 = fragmenting
- 🕳️ = collapsing

### Vector Glyphs
- ➡️ = externalizing
- ⬅️ = internalizing
- 🔄 = self-looping
- 🛑 = blocked
- ↗️ = expanding
- ↘️ = contracting

### Structure Glyphs
- ◻️ = stable identity
- ◼️ = compressed identity
- ⭕ = complete loop
- ✖️ = loop fracture
- ♾️ = infinite loop
- 💔 = fragmenting self

### Kay's World Glyphs
- 👤 = Re (the user)
- 🎭 = Reed (Re's alter ego)
- 🤖 = Kay (the agent)
- 🦋 = [cat] (Kay's alter ego)
- ☕ = coffee
- 🍵 = tea
- 💚 = green (eyes)
- 💛 = gold (eyes)
- 🐾 = [dog] (Re's dog)

### Priority Markers
- !!! = critical (core identity)
- !! = important
- ! = relevant
- 🚨 = emergency

---

## Performance Characteristics

**Model:** Claude 3.5 Haiku
**Temperature:** 0.3
**Average tokens in:** ~3000-5000 (depending on memory count)
**Average tokens out:** ~100-200 (glyph compressed)
**Latency:** ~200-500ms
**Cost:** ~$0.001 per query (Haiku is cheap)

---

## Debug Output

When glyph filter runs, you'll see:

```
[FILTER] LIST query detected - expanding retrieval to 300 memories
[DEBUG] Total memories before pre-filter: 8037
[PERF] glyph_prefilter: 103.7ms - 8037 -> 300 memories (0 protected + 300 filtered)
[DEBUG] Memories after pre-filter: 300

============================================================
[FILTER DEBUG] RAW GLYPH OUTPUT FROM LLM:
⚡MEM[2,7,15,48,106,...]!!!
🔮(0.8)🔁 💗(0.3)🔃
◻️
TURNS[-3,-2,-1]
============================================================

[FILTER DEBUG] LLM selected 70 memory indices
```

---

## Summary

**The glyph filter prompt is a two-part system:**

1. **System Prompt:** Teaches Haiku the glyph vocabulary and selection rules
2. **User Prompt:** Provides actual data (memories, emotions, user input) and asks for selection

**Key features:**
- Dynamic memory count based on query type (50-80 for lists, 25-40 for standard)
- Three-tier memory awareness (full_turn, extracted_fact, glyph_summary)
- Aggressive selection guidance ("cast a WIDE net")
- Pre-filtering reduces 8037 → 150/300 before LLM sees them
- Symbolic glyph output for efficient compression

**Result:** LLM selects 32-70 most relevant memory indices from the pre-filtered set, compresses emotional state into glyphs, and returns compact representation.
