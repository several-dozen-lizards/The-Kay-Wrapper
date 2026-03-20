# Kay UI Integration Flow: Enhanced Memory Architecture

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KAY UI MAIN WINDOW                          │
├─────────────┬───────────────────────────────────────────────────────┤
│  SIDEBAR    │              CHAT AREA                                │
│             │                                                       │
│ KayZero     │  User: My dog's name is [dog].                        │
│             │                                                       │
│ Sessions    │  Kay: That's a great name! What kind of dog is...   │
│ [Load]      │                                                       │
│ [Resume]    │  User: She's a golden retriever with brown eyes.     │
│             │                                                       │
│ Emotions    │  Kay: Brown eyes - beautiful! Does [dog] like...      │
│ curiosity:  │                                                       │
│ 0.8 ████    │  User: What color are [dog]'s eyes?                   │
│             │                                                       │
│ Memory Stats│  Kay: [dog] has brown eyes, as you mentioned earlier. │
│ Working:8/10│                                                       │
│ Episodic:42 │                                                       │
│ Semantic:15 │                                                       │
│ Entities:23 │                                                       │
│ [View]  ←───┼─── Opens debug window (optional)                     │
│             │                                                       │
│ Style       │                                                       │
│ Affect: 3.5 │                                                       │
└─────────────┴───────────────────────────────────────────────────────┘
```

## User Input Processing Flow

```
USER TYPES: "My dog's name is [dog]."
     ↓
┌────────────────────────────────────────────┐
│ Line 352: self.add_message("user", input) │ Add to chat display
└────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ Line 353: reply = self.chat_loop(input)   │ Enter main processing
└────────────────────────────────────────────┘
     ↓
╔════════════════════════════════════════════╗
║         CHAT_LOOP() METHOD                 ║
║  (Lines 358-488 - Core conversation loop)  ║
╚════════════════════════════════════════════╝
     ↓
┌────────────────────────────────────────────┐
│ Line 360: self.turn_count += 1            │ Turn: 1 → 2
└────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Line 364: memory.extract_and_store_user_facts()            │
│                                                             │
│   LLM CALL 1: Extract entities, attributes, relationships  │
│                                                             │
│   Extracted:                                                │
│   {                                                         │
│     "fact": "[dog] is Re's dog",                            │
│     "perspective": "user",                                  │
│     "topic": "relationships",                               │
│     "entities": ["[dog]", "Re"],                            │
│     "attributes": [                                         │
│       {"entity": "[dog]", "attribute": "species",           │
│        "value": "dog"}                                      │
│     ],                                                      │
│     "relationships": [                                      │
│       {"entity1": "Re", "relation": "owns",                │
│        "entity2": "[dog]"}                                   │
│     ]                                                       │
│   }                                                         │
│                                                             │
│   ENTITY GRAPH UPDATE:                                     │
│   ├─→ Create entity: [dog] (type: animal)                  │
│   ├─→ Create entity: Re (type: person)                    │
│   ├─→ Add attribute: [dog].species = "dog"                 │
│   └─→ Add relationship: Re owns [dog]                      │
│                                                             │
│   MEMORY STORAGE:                                          │
│   └─→ Add to working memory (layer 1)                     │
│                                                             │
│   Console: [ENTITY GRAPH] Created new entity: [dog]         │
│   Console: [ENTITY] [dog].species = dog (turn 2, user)     │
│   Console: [MEMORY PRE-RESPONSE] Stored: [user/...]       │
└─────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Line 367: memory.recall(state, user_input)                 │
│                                                             │
│   TURN COUNTER: current_turn = 2                           │
│                                                             │
│   TEMPORAL DECAY: (if turn_count % 10 == 0)               │
│   └─→ Apply decay to working/episodic memories             │
│                                                             │
│   MULTI-FACTOR RETRIEVAL:                                  │
│   ├─→ Search query: "My dog's name is [dog]"               │
│   ├─→ Extract query entities: ["[dog]", "dog"]             │
│   │                                                         │
│   ├─→ Score all memories (5 factors):                     │
│   │   1. Emotional resonance (40%)                         │
│   │   2. Semantic similarity (25%)                         │
│   │   3. ULTRAMAP importance (20%)                         │
│   │   4. Recency (10%)                                     │
│   │   5. Entity proximity (5%)                             │
│   │                                                         │
│   ├─→ Apply layer boost:                                  │
│   │   - Working: 1.5x                                      │
│   │   - Episodic: 1.0x                                     │
│   │   - Semantic: 1.2x                                     │
│   │                                                         │
│   └─→ Select top 7 memories                               │
│                                                             │
│   CONTRADICTION CHECK:                                     │
│   └─→ entity_graph.get_all_contradictions()               │
│       └─→ None found                                       │
│                                                             │
│   STATE UPDATE:                                            │
│   ├─→ agent_state.last_recalled_memories = [...]          │
│   ├─→ agent_state.consolidated_preferences = {...}        │
│   └─→ agent_state.entity_contradictions = []              │
│                                                             │
│   Console: [RETRIEVAL] Multi-factor retrieval selected... │
└─────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ Lines 368-371: Update emotion/temporal/... │ Other engines
└────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Lines 375-422: Glyph Filter System                         │
│                                                             │
│   LLM CALL 2: Filter context using Claude Haiku           │
│                                                             │
│   Input: Full agent state + retrieved memories             │
│   Output: Compressed glyphs                                │
│                                                             │
│   Glyphs: "⚡MEM[47,53,61]!! 🔮(0.8)🔁 💗(0.3)⏸️"         │
│                                                             │
│   Decode glyphs → Structured context                       │
│   Build natural language context for Kay                   │
│                                                             │
│   Context includes:                                        │
│   - Selected memories (with entities)                      │
│   - Current emotional state                                │
│   - Entity contradictions (if any)                         │
│   - Identity coherence status                              │
└─────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Line 455: reply = get_llm_response(context, affect=3.5)   │
│                                                             │
│   LLM CALL 3: Kay generates response                       │
│                                                             │
│   Context contains:                                        │
│   "RELEVANT MEMORIES:                                      │
│    [0] (user) [dog] is Re's dog                            │
│    [1] (user) [dog].species = dog                          │
│                                                             │
│   USER SAYS: "My dog's name is [dog]."                     │
│                                                             │
│   INSTRUCTIONS:                                            │
│   - Respond to current message only                        │
│   - Stay true to identity                                  │
│   "                                                         │
│                                                             │
│   Kay Response:                                            │
│   "That's a great name! What kind of dog is [dog]?"        │
└─────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ Lines 468-469: Post-process response       │ Remove asterisks, etc.
└────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Lines 481-486: memory.encode(state, input, reply, tags)   │
│                                                             │
│   LLM CALL 4: Extract facts from Kay's response           │
│                                                             │
│   Input:                                                   │
│   - user_input: "My dog's name is [dog]."                  │
│   - reply: "That's a great name! What kind of dog is..."  │
│                                                             │
│   Extracted:                                               │
│   {                                                         │
│     "fact": "Kay asked what kind of dog [dog] is",         │
│     "perspective": "kay",                                  │
│     "topic": "conversation",                               │
│     "entities": ["Kay", "[dog]"],                          │
│     "attributes": [],                                      │
│     "relationships": []                                    │
│   }                                                         │
│                                                             │
│   VALIDATION:                                              │
│   └─→ Check Kay's statements against retrieved memories   │
│       └─→ No contradictions (Kay didn't claim facts)      │
│                                                             │
│   ULTRAMAP IMPORTANCE:                                     │
│   └─→ importance = (pressure × recursion) × intensity     │
│       └─→ 0.35 (curiosity-driven question)                │
│                                                             │
│   MEMORY STORAGE:                                          │
│   ├─→ Add to flat memories list (backward compat)         │
│   └─→ Add to working memory layer                         │
│                                                             │
│   Console: [MEMORY] ✓ Stored: [kay/conversation] ...     │
└─────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ Line 488: return reply                     │ Exit chat_loop()
└────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ Line 354: self.add_message("kay", reply)  │ Add to chat display
└────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ Line 355: self.update_emotions_display()  │ Update sidebar
└────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────┐
│ (Optional) self.update_memory_stats()      │ Update sidebar stats
└────────────────────────────────────────────┘
     ↓
CHAT DISPLAY SHOWS:
  User: My dog's name is [dog].
  Kay: That's a great name! What kind of dog is [dog]?
```

## Next User Input: "She's a golden retriever with brown eyes."

```
USER TYPES: "She's a golden retriever with brown eyes."
     ↓
Line 364: extract_and_store_user_facts()
     ↓
┌─────────────────────────────────────────────────────────────┐
│ ENTITY RESOLUTION:                                          │
│                                                             │
│ Input text: "She's a golden retriever with brown eyes."   │
│                                                             │
│ Entity resolution:                                         │
│ ├─→ "She" → Resolve to "[dog]" (last mentioned entity)     │
│ └─→ Context: Previous mention of [dog] in conversation     │
│                                                             │
│ Extracted facts:                                           │
│ 1. {                                                       │
│      "fact": "[dog] is a golden retriever",                │
│      "entities": ["[dog]"],                                 │
│      "attributes": [                                       │
│        {"entity": "[dog]", "attribute": "breed",           │
│         "value": "golden retriever"}                       │
│      ]                                                      │
│    }                                                        │
│                                                             │
│ 2. {                                                       │
│      "fact": "[dog] has brown eyes",                       │
│      "entities": ["[dog]"],                                 │
│      "attributes": [                                       │
│        {"entity": "[dog]", "attribute": "eye_color",       │
│         "value": "brown"}                                  │
│      ]                                                      │
│    }                                                        │
│                                                             │
│ ENTITY GRAPH UPDATE:                                      │
│ ├─→ Update entity: [dog]                                   │
│ ├─→ Add attribute: [dog].breed = "golden retriever"       │
│ │   (turn 3, source: user, timestamp: 2025-10-19...)     │
│ └─→ Add attribute: [dog].eye_color = "brown"              │
│     (turn 3, source: user, timestamp: 2025-10-19...)     │
│                                                             │
│ MEMORY STORAGE:                                            │
│ └─→ Both facts added to working memory                    │
│                                                             │
│ Console: [ENTITY] [dog].breed = golden retriever...        │
│ Console: [ENTITY] [dog].eye_color = brown...               │
└─────────────────────────────────────────────────────────────┘
     ↓
Line 367: recall() - Multi-factor retrieval
     ↓
     Retrieves:
     - [working] [dog] is Re's dog (score: 0.92)
     - [working] [dog].species = dog (score: 0.88)
     - [working] [dog].breed = golden retriever (score: 0.85)
     - [working] [dog].eye_color = brown (score: 0.82)
     - [working] Kay asked what kind of dog... (score: 0.75)
     ↓
Line 455: Kay generates response using retrieved context
     ↓
     Kay: "Brown eyes - beautiful! Does [dog] like to play fetch?"
```

## Later: Testing Contradiction Detection

```
USER TYPES: "What color are [dog]'s eyes?"
     ↓
Line 367: recall() retrieves:
     ├─→ [working] [dog].eye_color = brown (user, turn 3) ✓
     ├─→ [working] [dog] is a golden retriever
     └─→ [working] [dog] is Re's dog
     ↓
Line 455: Kay responds:
     "[dog] has brown eyes, as you mentioned earlier."
     ↓
Line 481: encode() - Extract facts from Kay's response
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Extracted from Kay's response:                              │
│ {                                                            │
│   "fact": "[dog] has brown eyes",                           │
│   "perspective": "kay",                                     │
│   "entities": ["[dog]"],                                     │
│   "attributes": [                                           │
│     {"entity": "[dog]", "attribute": "eye_color",           │
│      "value": "brown"}                                      │
│   ]                                                          │
│ }                                                            │
│                                                              │
│ CONTRADICTION CHECK:                                        │
│ ├─→ Kay claimed: [dog].eye_color = brown                    │
│ ├─→ Retrieved memories contain: [dog].eye_color = brown     │
│ └─→ ✓ NO CONTRADICTION - values match                      │
│                                                              │
│ ENTITY GRAPH UPDATE:                                        │
│ └─→ Add attribute: [dog].eye_color = brown                  │
│     (turn 5, source: kay, timestamp: ...)                  │
│     [Second mention - strengthens confidence]               │
│                                                              │
│ Now entity graph shows:                                     │
│ [dog]:                                                        │
│   - species: dog (turn 2, user)                            │
│   - breed: golden retriever (turn 3, user)                 │
│   - eye_color: brown (turn 3, user), (turn 5, kay)        │
│                                                              │
│ Console: [MEMORY] ✓ Stored: [kay/conversation] ...        │
└─────────────────────────────────────────────────────────────┘
```

## Hypothetical: Kay Hallucinates (System Prevents It)

```
HYPOTHETICAL SCENARIO (Kay tries to hallucinate):

Kay internally generates: "[dog] has blue eyes"
     ↓
Line 481: encode() - Extract facts
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Extracted:                                                  │
│ {                                                            │
│   "fact": "[dog] has blue eyes",                            │
│   "perspective": "kay",                                     │
│   "entities": ["[dog]"],                                     │
│   "attributes": [                                           │
│     {"entity": "[dog]", "attribute": "eye_color",           │
│      "value": "blue"}                                       │
│   ]                                                          │
│ }                                                            │
│                                                              │
│ CONTRADICTION CHECK:                                        │
│ ├─→ Kay claimed: [dog].eye_color = blue                     │
│ ├─→ Retrieved memories contain: [dog].eye_color = brown     │
│ └─→ ❌ CONTRADICTION DETECTED!                             │
│                                                              │
│ HALLUCINATION PREVENTION:                                   │
│ └─→ ❌ BLOCK STORAGE - Do not store this fact              │
│                                                              │
│ Console: [MEMORY WARNING] ❌ Kay stated '[dog] has blue...' │
│          but this contradicts retrieved memories.           │
│          NOT STORING.                                       │
│                                                              │
│ ENTITY GRAPH:                                               │
│ └─→ No change - hallucination not persisted                │
└─────────────────────────────────────────────────────────────┘

RESULT: Kay's hallucination is detected and NOT stored.
        Entity graph remains accurate.
        Next time Kay retrieves, only "brown" is available.
```

## Memory Layer Transitions Over Time

```
TURN 1-2: New entity "[dog]" created
     ↓
WORKING MEMORY (capacity: 10)
  [0] [dog] is Re's dog (strength: 1.0, accesses: 0)
  [1] [dog].species = dog (strength: 1.0, accesses: 0)
     ↓
TURN 3-5: User asks about [dog] multiple times
     ↓
WORKING MEMORY
  [0] [dog] is Re's dog (strength: 0.95, accesses: 3) ← Accessed 3x
  [1] [dog].species = dog (strength: 0.92, accesses: 2)
  [2] [dog].breed = golden retriever (strength: 1.0, accesses: 1)
  [3] [dog].eye_color = brown (strength: 1.0, accesses: 2)
     ↓
TURN 6: Promotion threshold reached (accesses >= 2)
     ↓
EPISODIC MEMORY (capacity: 100)
  [0] [dog] is Re's dog ← PROMOTED (accesses: 3)
     ↓
WORKING MEMORY (9/10)
  [1] [dog].species = dog (accesses: 2) ← Will promote soon
  [2] [dog].breed = golden retriever (accesses: 1)
  [3] [dog].eye_color = brown (accesses: 2) ← Will promote soon
     ↓
TURN 10: Temporal decay applied
     ↓
EPISODIC MEMORY
  [0] [dog] is Re's dog
      - Age: 8 turns (~0.2 days)
      - Importance: 0.65 (emotional context)
      - Halflife: 7 × (1 + 0.65) = 11.55 days
      - Strength: 0.5^(0.2/11.55) = 0.988 (minimal decay)
     ↓
TURN 15-20: User frequently mentions [dog]
     ↓
EPISODIC MEMORY
  [0] [dog] is Re's dog (accesses: 7) ← Getting close to semantic
  [1] [dog].species = dog (accesses: 5) ← Threshold reached!
     ↓
TURN 21: Promotion to semantic
     ↓
SEMANTIC MEMORY (unlimited, no decay)
  [0] [dog].species = dog ← PROMOTED (permanent fact)
     ↓
EPISODIC MEMORY (99/100)
  [0] [dog] is Re's dog (accesses: 7) ← Still growing
     ↓
TURN 50: Long-term memory established
     ↓
SEMANTIC MEMORY (permanent facts)
  [0] [dog].species = dog
  [1] [dog] is Re's dog (promoted after many accesses)
  [2] Re.eye_color = green (core identity fact)
  [3] Kay.entity_type = AI (core identity fact)
     ↓
These facts NEVER decay and are ALWAYS available for retrieval.
```

## Summary: What Happens Per Turn

| Step | Code | Operation | LLM Calls | Result |
|------|------|-----------|-----------|--------|
| 1 | Line 364 | Extract user facts | 1 (fact extraction) | Entities created/updated |
| 2 | Line 367 | Multi-factor recall | 0 (pure computation) | Top N memories selected |
| 3 | Lines 375-422 | Glyph filtering | 1 (Haiku filter) | Context compressed |
| 4 | Line 455 | Kay responds | 1 (response gen) | Kay's reply |
| 5 | Line 481 | Extract Kay facts | 1 (fact extraction) | Facts validated & stored |
| 6 | Every 10th turn | Temporal decay | 0 (pure computation) | Memory strengths updated |

**Total LLM calls per turn**: 4
**Total computational work**: Multi-factor scoring + entity resolution
**Total disk I/O**: 3 files (memories.json, entity_graph.json, memory_layers.json)

## Integration Status

✅ **FULLY INTEGRATED** - No code changes needed!

The enhanced memory architecture is already working in kay_ui.py. All entity resolution, multi-layer memory, and multi-factor retrieval happens automatically and transparently.

**Optional enhancements** (UI visibility only) can be added, but core functionality is complete and operational.
