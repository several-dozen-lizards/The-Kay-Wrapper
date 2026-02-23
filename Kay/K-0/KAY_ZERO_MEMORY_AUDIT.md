# KAY ZERO MEMORY AUDIT - COMPREHENSIVE SYSTEM ANALYSIS

**Date:** 2025-11-08
**Status:** COMPLETE
**Scope:** Full memory pipeline from input to retrieval

---

## EXECUTIVE SUMMARY

Kay Zero implements a **sophisticated hybrid memory architecture** combining multiple retrieval strategies, entity resolution, and emotion-tagged storage. The system is **architecturally sound** but suffers from **context continuity bugs** that cause Kay to lose recently-established facts.

**Critical Findings:**
- ✅ Architecture is well-designed with proper separation of concerns
- ⚠️ **BUG #1**: Recent facts don't surface due to keyword overlap threshold
- ⚠️ **BUG #2**: RECENT_TURNS directive parsed but underutilized (PARTIALLY FIXED)
- ⚠️ **BUG #3**: Glyph pre-filter caps memory selection too aggressively
- ⚠️ **BUG #4**: No deduplication between recent turns and selected memories
- ✅ Entity resolution working correctly
- ✅ Multi-layer system functioning as designed
- ⚠️ Temporal decay may be too aggressive for working memory

---

## MEMORY ARCHITECTURE MAP

### 1. STORAGE LAYERS

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY STORAGE TIERS                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TIER 1: FULL TURNS                                         │
│  ├─ Location: memories.json                                 │
│  ├─ Format: {user_input, response, timestamp, turn}         │
│  ├─ Purpose: Complete conversation history                  │
│  └─ Access: Rarely used directly                            │
│                                                             │
│  TIER 2: EXTRACTED FACTS                                    │
│  ├─ Location: memories.json (extracted_facts)               │
│  ├─ Format: {fact, perspective, entities, importance}       │
│  ├─ Purpose: Discrete knowledge units                       │
│  └─ Access: Primary retrieval target                        │
│                                                             │
│  TIER 3: GLYPH SUMMARIES                                    │
│  ├─ Location: memories.json (glyph_summary)                 │
│  ├─ Format: Compressed symbolic representation              │
│  ├─ Purpose: Compact memory representation                  │
│  └─ Access: Used by context filter LLM                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. MEMORY LAYERS (WORKING/EPISODIC/SEMANTIC)

```
┌──────────────────────────────────────────────────────────────┐
│                    MULTI-LAYER SYSTEM                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  WORKING MEMORY (Capacity: 10)                               │
│  ├─ Decay: 0.5 day half-life                                 │
│  ├─ Priority: 1.5x retrieval boost                           │
│  ├─ Promotion: After 2 accesses → Episodic                   │
│  └─ Purpose: Immediate conversational context                │
│                                                              │
│  EPISODIC MEMORY (Capacity: 100)                             │
│  ├─ Decay: 7 day half-life                                   │
│  ├─ Priority: 1.0x baseline                                  │
│  ├─ Promotion: After 5 accesses → Semantic                   │
│  └─ Purpose: Recent experiences                              │
│                                                              │
│  SEMANTIC MEMORY (Capacity: Unlimited)                       │
│  ├─ Decay: None                                              │
│  ├─ Priority: 1.2x retrieval boost                           │
│  ├─ Promotion: Permanent storage                             │
│  └─ Purpose: Long-term knowledge                             │
│                                                              │
│  IDENTITY MEMORY (Special Layer)                             │
│  ├─ Decay: None                                              │
│  ├─ Priority: 1.8x retrieval boost                           │
│  ├─ Promotion: Manually tagged permanent facts               │
│  └─ Purpose: Kay's core identity facts                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3. ENTITY RESOLUTION SYSTEM

```
┌──────────────────────────────────────────────────────────────┐
│                    ENTITY GRAPH                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CANONICAL ENTITIES                                          │
│  ├─ Format: {name, aliases, attributes, relationships}       │
│  ├─ Resolution: "my dog" → "Saga" (canonical)                │
│  ├─ Attributes: [{value, turn, source, timestamp}]           │
│  └─ Contradictions: Auto-detected with severity              │
│                                                              │
│  ATTRIBUTE PROVENANCE                                        │
│  ├─ Every attribute tracked to source turn                   │
│  ├─ Conflicting values flagged (e.g., eyes: green vs blue)   │
│  ├─ Severity: high/moderate/low based on attribute type      │
│  └─ Resolution: LLM decides which value to trust              │
│                                                              │
│  RELATIONSHIPS                                               │
│  ├─ Format: {subject, predicate, object, strength}           │
│  ├─ Examples: "Re owns Saga", "Kay likes coffee"             │
│  ├─ Bidirectional tracking                                   │
│  └─ Strength based on mention frequency                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## INFORMATION FLOW PIPELINE

### ENCODING PATH (User Input → Storage)

```
┌─────────────────────────────────────────────────────────────────┐
│                      MEMORY ENCODING FLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. USER INPUT RECEIVED
   ↓
2. CONVERSATION TURN COMPLETES
   ├─ User input captured
   ├─ Kay's response captured
   ├─ Emotional cocktail snapshot
   ├─ Turn index assigned
   └─ Timestamp recorded
   ↓
3. FACT EXTRACTION (LLM-based)
   ├─ Calls extract_facts_from_turn()
   ├─ Uses Haiku model for speed
   ├─ Prompt: "Extract discrete facts from this conversation"
   ├─ Output: List of {fact, perspective, entities}
   ├─ Perspective detection: "my/I" → user, "your/you" → kay
   └─ Entity extraction: Capitalized words, quoted phrases
   ↓
4. ENTITY PROCESSING
   ├─ EntityGraph.process_entities(facts)
   ├─ Canonical name resolution
   ├─ Attribute updates with provenance
   ├─ Contradiction detection
   └─ Relationship updates
   ↓
5. IMPORTANCE SCORING (ULTRAMAP)
   ├─ Emotional pressure × recursion depth
   ├─ Range: 0.0 to 1.0
   ├─ High importance: Strong emotions during turn
   └─ Used for layer promotion decisions
   ↓
6. LAYER ASSIGNMENT
   ├─ Default: Working memory
   ├─ High importance (>0.7): Start in Episodic
   ├─ Identity-tagged: Identity memory
   └─ Capacity enforcement (evict oldest if full)
   ↓
7. GLYPH COMPRESSION
   ├─ Calls generate_glyph_summary()
   ├─ Uses Haiku model
   ├─ Compresses full turn into symbolic form
   ├─ Format: ⚡MEM[indices]!! 🔮(0.5)📋 ◻️
   └─ Stored alongside full turn and facts
   ↓
8. PERSISTENCE
   ├─ Save to memories.json
   ├─ Save entity graph to entity_graph.json
   ├─ Save memory layers to memory_layers.json
   └─ Append to session history
```

### RETRIEVAL PATH (Query → Context Building)

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEMORY RETRIEVAL FLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. USER QUERY RECEIVED
   ↓
2. CONTEXT FILTER INVOKED
   ├─ Location: context_filter.py
   ├─ Input: Query, emotional cocktail, all memories (glyph form)
   ├─ LLM: Sonnet model
   └─ Task: Select relevant memories + decide recency needs
   ↓
3. GLYPH FILTER OUTPUT
   ├─ Line 1: ⚡MEM[1,5,12,18,23]!!!
   ├─ Line 2: RECENT_TURNS: 3
   ├─ Line 3: 🔮(0.7)🔍 ⚡(0.3)
   ├─ Line 4: (optional contradictions)
   └─ Line 5: (optional identity state)
   ↓
4. GLYPH DECODING
   ├─ Location: glyph_decoder.py
   ├─ Parse MEM[indices] → Extract memory IDs
   ├─ Parse RECENT_TURNS → Extract turn count
   ├─ Parse emotions → Extract emotional state
   └─ Output: {selected_memories, recent_turns_needed, ...}
   ↓
5. MEMORY RETRIEVAL (from MemoryEngine)
   ├─ For each memory ID:
   │   ├─ Retrieve from memories list
   │   ├─ Apply layer boost (working:1.5x, semantic:1.2x)
   │   ├─ Apply temporal decay if episodic/working
   │   └─ Increment access count (for promotion tracking)
   ├─ Check minimum threshold (MINIMUM_MEMORIES = 20)
   └─ Force-add recent high-importance if below minimum
   ↓
6. RECENT TURNS INJECTION
   ├─ Location: kay_ui.py lines 1003-1032
   ├─ If RECENT_TURNS > 0:
   │   ├─ Retrieve last N turns from current_session
   │   ├─ Format as memory objects with type='recent_turn'
   │   └─ PREPEND to selected_memories list
   └─ Purpose: Resolve pronouns and temporal references
   ↓
7. RAG DOCUMENT RETRIEVAL (if applicable)
   ├─ Location: engines/llm_retrieval.py
   ├─ Query document embeddings
   ├─ Retrieve top K chunks (default K=5)
   ├─ Add to decoded context as rag_chunks
   └─ Only if documents imported previously
   ↓
8. CONTEXT BUILDING
   ├─ Location: glyph_decoder.build_context_for_kay()
   ├─ Sections:
   │   ├─ DOCUMENT CONTEXT (RAG chunks if any)
   │   ├─ RECENT CONVERSATION (recent turns if requested)
   │   ├─ RELEVANT MEMORIES (selected facts)
   │   ├─ CURRENT EMOTIONAL STATE
   │   ├─ ACTIVE CONTRADICTIONS (if any)
   │   └─ INSTRUCTIONS
   └─ Output: Natural language context block
   ↓
9. LLM RESPONSE GENERATION
   ├─ Location: integrations/llm_integration.py
   ├─ System prompt + context + user query
   ├─ Anti-repetition measures applied
   ├─ Temperature: 0.7 for variation
   └─ Output: Kay's response
```

---

## DATA STRUCTURES SPECIFICATION

### Memory Object (memories.json)

```python
{
    # TIER 1: Full conversation turn
    "user_input": "Tell me about my dog",
    "response": "Saga is your Czechoslovakian Wolfdog...",
    "timestamp": "2025-11-08T14:23:45",
    "turn_index": 42,

    # TIER 2: Extracted facts
    "extracted_facts": [
        {
            "fact": "Re has a dog named Saga",
            "perspective": "user",
            "entities": ["Re", "Saga"],
            "importance_score": 0.6,
            "turn_extracted": 42
        },
        {
            "fact": "Saga is a Czechoslovakian Wolfdog",
            "perspective": "user",
            "entities": ["Saga"],
            "importance_score": 0.5,
            "turn_extracted": 42
        }
    ],

    # TIER 3: Glyph summary
    "glyph_summary": "⚡MEM[entity:Saga,species:dog]!! 🔮(0.3)📋 ◻️",

    # Metadata
    "emotional_cocktail": [
        {"emotion": "curiosity", "intensity": 0.5, "age": 0}
    ],
    "importance_score": 0.6,
    "layer": "working",  # working/episodic/semantic/identity
    "access_count": 0,
    "last_accessed": "2025-11-08T14:23:45",
    "strength": 1.0  # Temporal decay modifier
}
```

### Entity Graph (entity_graph.json)

```python
{
    "entities": {
        "Saga": {
            "canonical_name": "Saga",
            "aliases": ["my dog", "the wolfdog", "she"],
            "entity_type": "pet",
            "first_mentioned_turn": 42,
            "last_mentioned_turn": 42,
            "mention_count": 1,

            "attributes": {
                "species": [
                    {
                        "value": "Czechoslovakian Wolfdog",
                        "turn": 42,
                        "source": "user stated",
                        "timestamp": "2025-11-08T14:23:45"
                    }
                ],
                "owner": [
                    {
                        "value": "Re",
                        "turn": 42,
                        "source": "user stated",
                        "timestamp": "2025-11-08T14:23:45"
                    }
                ]
            },

            "contradictions": []  # Empty if no conflicts
        }
    },

    "relationships": [
        {
            "subject": "Re",
            "predicate": "owns",
            "object": "Saga",
            "strength": 1.0,
            "first_mentioned_turn": 42,
            "last_mentioned_turn": 42
        }
    ]
}
```

### Memory Layers (memory_layers.json)

```python
{
    "working": [0, 1, 2, 3, 4],  # Indices into memories.json
    "episodic": [5, 6, 7, 8, 9, 10, ...],
    "semantic": [100, 101, 102, ...],
    "identity": [200, 201],

    "layer_capacities": {
        "working": 10,
        "episodic": 100,
        "semantic": null  # Unlimited
    },

    "promotion_thresholds": {
        "working_to_episodic_accesses": 2,
        "episodic_to_semantic_accesses": 5,
        "min_importance_for_promotion": 0.3
    },

    "decay_settings": {
        "working_halflife_days": 0.5,
        "episodic_halflife_days": 7.0,
        "semantic_decay": false
    }
}
```

---

## IDENTIFIED BUGS AND FAILURES

### 🔴 BUG #1: RECENT FACTS DON'T SURFACE (CRITICAL)

**Severity:** HIGH
**Impact:** Kay forgets facts established 1-2 turns ago
**Root Cause:** Keyword overlap threshold too strict

**Location:** `engines/memory_engine.py` lines 61-120

**Problem:**
```python
# In retrieve_biased_memories()
keyword_overlap = self._calculate_keyword_overlap(query, memory_text)
if keyword_overlap < relevance_floor:  # Default: 0.3
    score = 0  # KILLED - even if high importance
```

When user says "Tell me about Saga" (turn 1), then "What else?" (turn 2):
- Query: "What else?"
- Memory: "Saga is your Czechoslovakian Wolfdog"
- Keyword overlap: ~0.0 (no shared words)
- Result: Score = 0, memory excluded despite being from previous turn

**Why It Fails:**
1. Recent facts often don't share keywords with follow-up queries
2. Pronouns ("it", "that") have zero keyword overlap
3. Generic follow-ups ("tell me more", "what else") kill recent context
4. Even with high importance score, relevance_floor gates everything

**Fix Priority:** IMMEDIATE

**Recommended Fix:**
```python
# In retrieve_biased_memories()

# BEFORE (BROKEN):
if keyword_overlap < relevance_floor:
    score = 0

# AFTER (FIXED):
# Don't kill recent memories based on keyword overlap alone
turns_old = current_turn - memory.get('turn_index', 0)
is_recent = turns_old <= 3  # Last 3 turns

if keyword_overlap < relevance_floor and not is_recent:
    score = 0  # Only gate if NOT recent
```

**Alternative Fix (more sophisticated):**
```python
# Add recency boost to scoring
recency_factor = 1.0
if turns_old <= 3:
    recency_factor = 2.0  # Double weight for last 3 turns
elif turns_old <= 10:
    recency_factor = 1.5  # 1.5x weight for last 10 turns

final_score = base_score * keyword_overlap * recency_factor
```

---

### 🟡 BUG #2: RECENT_TURNS DIRECTIVE UNDERUTILIZED (PARTIALLY FIXED)

**Severity:** MEDIUM
**Impact:** Glyph filter decides recency, but not used in all code paths
**Root Cause:** RECENT_TURNS feature recently added, integration incomplete

**Status:** PARTIALLY FIXED (2025-11-06)

**What's Fixed:**
- ✅ Glyph filter outputs RECENT_TURNS directive
- ✅ Glyph decoder parses RECENT_TURNS value
- ✅ kay_ui.py injects recent turns into context (lines 1003-1032)

**What's Still Broken:**
- ❌ Only works in kay_ui.py, not in main.py
- ❌ No deduplication between recent turns and selected memories
- ❌ Recent turns always prepended (should they be interspersed?)

**Location:** `main.py` conversation loop

**Problem:**
```python
# main.py - conversation loop doesn't use RECENT_TURNS
context = await context_manager.build_context(
    recent_turns=conversation_history[-5:],  # HARDCODED 5
    retrieved_memories=filtered_context["selected_memories"],
    # ... but never uses filtered_context["recent_turns_needed"]
)
```

**Fix Priority:** MEDIUM (kay_ui.py works, main.py doesn't)

**Recommended Fix:**
```python
# In main.py, after glyph filtering:
recent_turns_needed = filtered_context.get("recent_turns_needed", 0)
if recent_turns_needed > 0:
    recent_turns = conversation_history[-recent_turns_needed:]
else:
    recent_turns = []  # Filter said no recency needed

context = await context_manager.build_context(
    recent_turns=recent_turns,  # Use LLM's decision
    retrieved_memories=filtered_context["selected_memories"],
    ...
)
```

---

### 🟡 BUG #3: GLYPH PRE-FILTER CAPS TOO AGGRESSIVELY (MEDIUM)

**Severity:** MEDIUM
**Impact:** Context filter LLM only sees first 50 memories, misses relevant ones
**Root Cause:** Pre-filtering caps memory list before glyph encoding

**Location:** `context_filter.py` lines 74-76

**Problem:**
```python
# Only send first 50 memories to glyph filter
memory_glyphs = [
    mem.get('glyph_summary', '[no glyph]')
    for mem in memories[:50]  # HARD CAP at 50
]
```

**Why It Fails:**
1. If relevant memory is at index 75, filter LLM never sees it
2. Memories not pre-sorted by any relevance metric
3. Arbitrary cap of 50 may be too conservative for large memory stores
4. Defeats purpose of having 100+ episodic + unlimited semantic

**Fix Priority:** MEDIUM

**Recommended Fix Option 1 - Increase Cap:**
```python
# Allow more memories through
memory_glyphs = [
    mem.get('glyph_summary', '[no glyph]')
    for mem in memories[:150]  # Increased to 150
]
```

**Recommended Fix Option 2 - Smart Pre-Filter:**
```python
# Pre-sort by layer priority + importance before capping
def priority_score(mem):
    layer_priority = {
        'identity': 4,
        'semantic': 3,
        'working': 2,
        'episodic': 1
    }
    return (
        layer_priority.get(mem.get('layer', 'episodic'), 1) * 10 +
        mem.get('importance_score', 0.3)
    )

sorted_memories = sorted(memories, key=priority_score, reverse=True)
memory_glyphs = [
    mem.get('glyph_summary', '[no glyph]')
    for mem in sorted_memories[:100]  # Top 100 by priority
]
```

---

### 🟡 BUG #4: NO DEDUPLICATION BETWEEN RECENT TURNS AND SELECTED MEMORIES

**Severity:** LOW
**Impact:** Same information may appear twice in context
**Root Cause:** Recent turns injection doesn't check for overlap with selected memories

**Location:** `kay_ui.py` lines 1003-1032

**Problem:**
```python
# Recent turns prepended without checking if same info in selected_memories
filtered_context["selected_memories"] = (
    recent_memories + filtered_context.get("selected_memories", [])
)
# No deduplication → if turn 5 is both "recent" and "selected", appears twice
```

**Why It Fails:**
1. If filter selects memory from turn 42, and RECENT_TURNS=5 includes turn 42, it appears twice
2. Wastes context window tokens
3. May confuse LLM with duplicate info

**Fix Priority:** LOW (doesn't break functionality, just inefficient)

**Recommended Fix:**
```python
# After building recent_memories list:
selected_turn_indices = set(
    mem.get('turn_index') for mem in filtered_context.get("selected_memories", [])
    if mem.get('turn_index') is not None
)

# Only add recent turns not already in selected memories
deduplicated_recent = [
    mem for mem in recent_memories
    if mem.get('original_turn_index') not in selected_turn_indices
]

filtered_context["selected_memories"] = (
    deduplicated_recent + filtered_context.get("selected_memories", [])
)
```

---

### 🟢 BUG #5: TEMPORAL DECAY MAY BE TOO AGGRESSIVE (LOW)

**Severity:** LOW
**Impact:** Working memory facts fade too quickly (0.5 day half-life)
**Root Cause:** Decay parameters not tuned for conversational use

**Location:** `memory_layers.json` decay settings

**Problem:**
```python
"working_halflife_days": 0.5  # Half strength after 12 hours
```

**Why It Might Fail:**
1. If user has conversation on Monday, then Tuesday afternoon, working memory already at 50% strength
2. For daily conversations, this might be too aggressive
3. Multi-day projects would lose context too fast

**Fix Priority:** LOW (tuning parameter, not a bug per se)

**Recommended Fix:**
```python
# Adjust decay settings in MemoryLayerManager.__init__()
self.working_decay_halflife = 1.0  # Changed from 0.5 to 1.0 day
# Now takes 24 hours to reach 50% strength instead of 12
```

**Alternative:** Make decay rate configurable per-user or per-session.

---

## PRIORITIZED FIX RECOMMENDATIONS

### Priority 1: IMMEDIATE (Critical Path Bugs)

**1. Fix Recent Facts Death by Keyword Overlap**
- **File:** `engines/memory_engine.py`
- **Function:** `retrieve_biased_memories()`
- **Lines:** 61-120
- **Fix:**
```python
# Around line 90, replace:
if keyword_overlap < relevance_floor:
    score = 0

# With:
turns_old = current_turn - memory.get('turn_index', 0)
is_recent = turns_old <= 5  # Last 5 turns get exemption

if keyword_overlap < relevance_floor and not is_recent:
    score = 0  # Only kill non-recent low-overlap memories
elif is_recent and keyword_overlap < relevance_floor:
    # Recent but low overlap: reduce score but don't kill
    score *= 0.5
```

**Testing:**
```python
# Test case:
# Turn 1: "Tell me about Saga"
# Turn 2: "What else?"
# Expected: Saga facts from turn 1 should still surface in turn 2
```

---

**2. Integrate RECENT_TURNS in main.py**
- **File:** `main.py`
- **Function:** Main conversation loop
- **Lines:** ~150-200 (context building section)
- **Fix:**
```python
# After glyph filtering:
recent_turns_needed = filtered_context.get("recent_turns_needed", 0)

if recent_turns_needed > 0:
    # Use LLM's decision on how many recent turns
    recent_context = conversation_history[-recent_turns_needed:]
else:
    # LLM said no recency needed
    recent_context = []

# Pass to context manager
context = await context_manager.build_context(
    recent_turns=recent_context,  # Dynamic based on LLM decision
    retrieved_memories=filtered_context["selected_memories"],
    emotional_state=agent_state["emotional_cocktail"],
    ...
)
```

---

### Priority 2: IMPORTANT (Quality of Life)

**3. Smart Glyph Pre-Filter with Priority Sorting**
- **File:** `context_filter.py`
- **Function:** `filter_with_glyph()`
- **Lines:** 74-76
- **Fix:**
```python
# Replace:
memory_glyphs = [
    mem.get('glyph_summary', '[no glyph]')
    for mem in memories[:50]
]

# With:
def memory_priority(mem):
    layer_weights = {
        'identity': 10.0,
        'semantic': 5.0,
        'working': 8.0,  # High priority - current context
        'episodic': 3.0
    }
    layer_weight = layer_weights.get(mem.get('layer', 'episodic'), 1.0)
    importance = mem.get('importance_score', 0.3)
    recency_boost = 1.0

    # Boost very recent memories
    current_turn = len(memories)
    turns_old = current_turn - mem.get('turn_index', 0)
    if turns_old <= 3:
        recency_boost = 2.0
    elif turns_old <= 10:
        recency_boost = 1.5

    return layer_weight * importance * recency_boost

# Sort by priority before capping
sorted_memories = sorted(memories, key=memory_priority, reverse=True)

memory_glyphs = [
    mem.get('glyph_summary', '[no glyph]')
    for mem in sorted_memories[:150]  # Increased cap to 150
]
```

---

**4. Add Deduplication Between Recent Turns and Selected Memories**
- **File:** `kay_ui.py`
- **Function:** Context building after glyph decode
- **Lines:** 1003-1032
- **Fix:**
```python
# After building recent_memories list:

# Extract turn indices from selected memories
selected_turn_indices = set()
for mem in filtered_context.get("selected_memories", []):
    turn_idx = mem.get('turn_index')
    if turn_idx is not None:
        selected_turn_indices.add(turn_idx)

# Filter out recent turns that are already in selected memories
deduplicated_recent = []
for recent_mem in recent_memories:
    # Extract original turn index from recent turn
    # (would need to add this field when creating recent_memory objects)
    original_turn = recent_mem.get('original_turn_index')
    if original_turn not in selected_turn_indices:
        deduplicated_recent.append(recent_mem)

print(f"[DEDUP] Removed {len(recent_memories) - len(deduplicated_recent)} duplicate turns")

# Prepend deduplicated recent turns
filtered_context["selected_memories"] = (
    deduplicated_recent + filtered_context.get("selected_memories", [])
)
```

---

### Priority 3: TUNING (Optional Improvements)

**5. Adjust Working Memory Decay Rate**
- **File:** `engines/memory_layers.py`
- **Function:** `MemoryLayerManager.__init__()`
- **Lines:** Constructor
- **Fix:**
```python
# Change from:
self.working_decay_halflife = 0.5  # 12 hours

# To:
self.working_decay_halflife = 1.5  # 36 hours (more forgiving for daily use)
```

---

**6. Add Configurable Relevance Floor**
- **File:** `engines/memory_engine.py`
- **Function:** `retrieve_biased_memories()`
- **Fix:**
```python
# Make relevance_floor dynamic based on query type
def adaptive_relevance_floor(query, recent_turns_needed):
    """
    Lower threshold when LLM requests recent context (pronouns, etc.)
    Higher threshold for factual queries (no recent context needed)
    """
    if recent_turns_needed >= 5:
        # High recency need = lower keyword threshold
        return 0.1
    elif recent_turns_needed >= 2:
        return 0.2
    else:
        # Factual query = standard threshold
        return 0.3

# Use adaptive floor:
relevance_floor = adaptive_relevance_floor(query, recent_turns_needed)
```

---

## CONSOLIDATION MECHANICS ANALYSIS

### 1. Entity Consolidation

**How it works:**
- EntityGraph tracks canonical entities with aliases
- Contradictions detected when attributes conflict
- LLM asked to resolve: "Which is correct: green eyes or blue eyes?"
- Resolution stored with provenance

**Status:** ✅ Working correctly

**Potential issue:**
- If user intentionally changes attributes ("I dyed my hair"), system might flag as contradiction
- **Fix:** Add temporal context to contradiction detection - changes over time are valid

---

### 2. Preference Consolidation

**How it works:**
- PreferenceTracker maintains weighted preferences per domain
- Frequency (60%) + Recency (40%) with exponential decay
- Conflicting preferences normalized to percentages
- LLM receives consolidated view: "mostly tea 60%, also coffee 40%"

**Status:** ✅ Working correctly

**Potential issue:**
- No mechanism for Kay to actively reject preferences ("I don't actually like coffee")
- **Fix:** Add explicit rejection tracking - if Kay says "I don't like X", set weight to 0

---

### 3. Memory Layer Promotion

**How it works:**
- Working memories promoted to episodic after 2 accesses
- Episodic memories promoted to semantic after 5 accesses
- Minimum importance threshold: 0.3

**Status:** ✅ Working as designed

**Potential issue:**
- Important one-time facts may never get accessed enough to promote
- **Fix:** Add importance-based fast-track: importance > 0.8 = instant semantic

---

## RACE CONDITIONS AND EDGE CASES

### Race Condition 1: Parallel Engine Updates

**Location:** `main.py` main loop

**Problem:**
```python
await asyncio.gather(
    emotion_engine.update(...),
    social_engine.update(...),
    temporal_engine.update(...),
    embodiment_engine.update(...),
    motif_engine.update(...)
)
```

**Risk:** Multiple engines modifying agent_state simultaneously

**Mitigation:** Each engine has isolated state section (no overlap)

**Status:** ✅ Safe (no shared mutable state)

---

### Edge Case 1: First Turn (No History)

**Scenario:** User's first message, no conversation history

**Handling:**
```python
if recent_turns_needed > 0 and self.current_session:
    # Only inject if session exists
```

**Status:** ✅ Handled correctly

---

### Edge Case 2: Query Requests 10 Turns, Only 3 Exist

**Scenario:** RECENT_TURNS: 10 but conversation only has 3 turns

**Handling:**
```python
recent_turns = self.current_session[-recent_turns_needed:]
# Python slicing handles out-of-bounds gracefully
```

**Status:** ✅ Handled correctly (Python list slicing)

---

### Edge Case 3: All Memories Below Relevance Floor

**Scenario:** Query has zero keyword overlap with any memory

**Current Behavior:** Returns empty memory list, Kay responds with no context

**Problem:** Even identity facts get filtered out

**Fix Needed:** Always include identity layer regardless of relevance floor

```python
# In retrieve_biased_memories():
# Always include identity memories
identity_memories = [
    mem for mem in self.memory_layers.get_layer('identity')
]
scored_memories.extend([(mem, 100.0) for mem in identity_memories])
```

---

## TESTING RECOMMENDATIONS

### Test Case 1: Recent Fact Recall

```python
# Turn 1
User: "My eyes are green"
Kay: "Got it, green eyes."

# Turn 2
User: "What color are they?"
Expected: Kay says "Green"
Current Bug: Kay might say "I don't have that information"

# Verification:
# Check logs for:
# - "[DECODER] Retrieved memory [X]: My eyes are green"
# - Keyword overlap score for query "what color are they?"
```

---

### Test Case 2: Pronoun Resolution

```python
# Turn 1
User: "Tell me about Saga"
Kay: "Saga is your Czechoslovakian Wolfdog..."

# Turn 2
User: "Can you describe her?"
Expected: Kay continues talking about Saga
Current: Should work with RECENT_TURNS feature

# Verification:
# Check for: "RECENT_TURNS: 3" or similar in glyph output
# Verify recent turns injected into context
```

---

### Test Case 3: Multi-Turn Reasoning

```python
# Turn 1
User: "I prefer coffee in the morning"

# Turn 2
User: "But tea in the evening"

# Turn 3
User: "What's my beverage preference?"
Expected: Kay says "Coffee mornings, tea evenings"
Current: Should work via preference consolidation

# Verification:
# Check preferences.json for normalized weights
# Check context for consolidated preference injection
```

---

### Test Case 4: Entity Contradiction

```python
# Turn 1
User: "My eyes are green"

# Turn 5
User: "My eyes are blue"

Expected: System flags contradiction, asks for clarification
Current: Should work via entity graph

# Verification:
# Check entity_graph.json for:
# - attributes.eye_color with two entries
# - contradictions array populated
```

---

### Test Case 5: Layer Promotion

```python
# Set up test:
# 1. Create working memory (turn 1)
# 2. Access it twice (turns 2, 3)
# 3. Check if promoted to episodic

# Verification:
# Check memory_layers.json:
# - Memory should move from "working" array to "episodic" array
# - access_count should be >= 2
```

---

## FILES REQUIRING CHANGES

### Immediate Priority:

1. **engines/memory_engine.py**
   - Fix keyword overlap death for recent facts
   - Add recency exemption to relevance floor

2. **main.py**
   - Integrate RECENT_TURNS directive into conversation loop
   - Dynamic recent context based on LLM decision

3. **context_filter.py**
   - Smart pre-filter with priority sorting
   - Increase cap from 50 to 150 memories

### Secondary Priority:

4. **kay_ui.py**
   - Add deduplication between recent turns and selected memories
   - Track original_turn_index in recent_memory objects

5. **engines/memory_layers.py**
   - Adjust working memory decay halflife (0.5 → 1.5 days)
   - Add importance-based fast-track promotion

---

## CONCLUSION

The Kay Zero memory system is **architecturally sound** with sophisticated multi-layer storage, entity resolution, and hybrid retrieval. The core issues are:

1. **Recency vs Relevance Balance**: System over-relies on keyword matching, killing recent facts
2. **Incomplete Integration**: RECENT_TURNS feature exists but not fully integrated
3. **Conservative Filtering**: Pre-filter caps too aggressively, hiding relevant memories

**All bugs are fixable** with targeted code changes to scoring logic and context building.

**Estimated Fix Time:**
- Priority 1 fixes: 2-3 hours
- Priority 2 fixes: 1-2 hours
- Priority 3 tuning: 1 hour

**Risk Level:** LOW - All fixes are scoring/threshold adjustments, no architectural changes needed.

---

**Generated:** 2025-11-08
**Author:** Claude Code Analysis
**Status:** Complete and actionable
