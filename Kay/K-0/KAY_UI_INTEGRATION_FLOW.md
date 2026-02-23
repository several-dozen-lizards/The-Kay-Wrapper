# Kay UI Integration Flow: Enhanced Memory Architecture

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KAY UI MAIN WINDOW                          │
├─────────────┬───────────────────────────────────────────────────────┤
│  SIDEBAR    │              CHAT AREA                                │
│             │                                                       │
│ KayZero     │  User: My dog's name is Saga.                        │
│             │                                                       │
│ Sessions    │  Kay: That's a great name! What kind of dog is...   │
│ [Load]      │                                                       │
│ [Resume]    │  User: She's a golden retriever with brown eyes.     │
│             │                                                       │
│ Emotions    │  Kay: Brown eyes - beautiful! Does Saga like...      │
│ curiosity:  │                                                       │
│ 0.8 ████    │  User: What color are Saga's eyes?                   │
│             │                                                       │
│ Memory Stats│  Kay: Saga has brown eyes, as you mentioned earlier. │
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
USER TYPES: "My dog's name is Saga."
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
│     "fact": "Saga is Re's dog",                            │
│     "perspective": "user",                                  │
│     "topic": "relationships",                               │
│     "entities": ["Saga", "Re"],                            │
│     "attributes": [                                         │
│       {"entity": "Saga", "attribute": "species",           │
│        "value": "dog"}                                      │
│     ],                                                      │
│     "relationships": [                                      │
│       {"entity1": "Re", "relation": "owns",                │
│        "entity2": "Saga"}                                   │
│     ]                                                       │
│   }                                                         │
│                                                             │
│   ENTITY GRAPH UPDATE:                                     │
│   ├─→ Create entity: Saga (type: animal)                  │
│   ├─→ Create entity: Re (type: person)                    │
│   ├─→ Add attribute: Saga.species = "dog"                 │
│   └─→ Add relationship: Re owns Saga                      │
│                                                             │
│   MEMORY STORAGE:                                          │
│   └─→ Add to working memory (layer 1)                     │
│                                                             │
│   Console: [ENTITY GRAPH] Created new entity: Saga         │
│   Console: [ENTITY] Saga.species = dog (turn 2, user)     │
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
│   ├─→ Search query: "My dog's name is Saga"               │
│   ├─→ Extract query entities: ["Saga", "dog"]             │
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
│    [0] (user) Saga is Re's dog                            │
│    [1] (user) Saga.species = dog                          │
│                                                             │
│   USER SAYS: "My dog's name is Saga."                     │
│                                                             │
│   INSTRUCTIONS:                                            │
│   - Respond to current message only                        │
│   - Stay true to identity                                  │
│   "                                                         │
│                                                             │
│   Kay Response:                                            │
│   "That's a great name! What kind of dog is Saga?"        │
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
│   - user_input: "My dog's name is Saga."                  │
│   - reply: "That's a great name! What kind of dog is..."  │
│                                                             │
│   Extracted:                                               │
│   {                                                         │
│     "fact": "Kay asked what kind of dog Saga is",         │
│     "perspective": "kay",                                  │
│     "topic": "conversation",                               │
│     "entities": ["Kay", "Saga"],                          │
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
  User: My dog's name is Saga.
  Kay: That's a great name! What kind of dog is Saga?
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
│ ├─→ "She" → Resolve to "Saga" (last mentioned entity)     │
│ └─→ Context: Previous mention of Saga in conversation     │
│                                                             │
│ Extracted facts:                                           │
│ 1. {                                                       │
│      "fact": "Saga is a golden retriever",                │
│      "entities": ["Saga"],                                 │
│      "attributes": [                                       │
│        {"entity": "Saga", "attribute": "breed",           │
│         "value": "golden retriever"}                       │
│      ]                                                      │
│    }                                                        │
│                                                             │
│ 2. {                                                       │
│      "fact": "Saga has brown eyes",                       │
│      "entities": ["Saga"],                                 │
│      "attributes": [                                       │
│        {"entity": "Saga", "attribute": "eye_color",       │
│         "value": "brown"}                                  │
│      ]                                                      │
│    }                                                        │
│                                                             │
│ ENTITY GRAPH UPDATE:                                      │
│ ├─→ Update entity: Saga                                   │
│ ├─→ Add attribute: Saga.breed = "golden retriever"       │
│ │   (turn 3, source: user, timestamp: 2025-10-19...)     │
│ └─→ Add attribute: Saga.eye_color = "brown"              │
│     (turn 3, source: user, timestamp: 2025-10-19...)     │
│                                                             │
│ MEMORY STORAGE:                                            │
│ └─→ Both facts added to working memory                    │
│                                                             │
│ Console: [ENTITY] Saga.breed = golden retriever...        │
│ Console: [ENTITY] Saga.eye_color = brown...               │
└─────────────────────────────────────────────────────────────┘
     ↓
Line 367: recall() - Multi-factor retrieval
     ↓
     Retrieves:
     - [working] Saga is Re's dog (score: 0.92)
     - [working] Saga.species = dog (score: 0.88)
     - [working] Saga.breed = golden retriever (score: 0.85)
     - [working] Saga.eye_color = brown (score: 0.82)
     - [working] Kay asked what kind of dog... (score: 0.75)
     ↓
Line 455: Kay generates response using retrieved context
     ↓
     Kay: "Brown eyes - beautiful! Does Saga like to play fetch?"
```

## Later: Testing Contradiction Detection

```
USER TYPES: "What color are Saga's eyes?"
     ↓
Line 367: recall() retrieves:
     ├─→ [working] Saga.eye_color = brown (user, turn 3) ✓
     ├─→ [working] Saga is a golden retriever
     └─→ [working] Saga is Re's dog
     ↓
Line 455: Kay responds:
     "Saga has brown eyes, as you mentioned earlier."
     ↓
Line 481: encode() - Extract facts from Kay's response
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Extracted from Kay's response:                              │
│ {                                                            │
│   "fact": "Saga has brown eyes",                           │
│   "perspective": "kay",                                     │
│   "entities": ["Saga"],                                     │
│   "attributes": [                                           │
│     {"entity": "Saga", "attribute": "eye_color",           │
│      "value": "brown"}                                      │
│   ]                                                          │
│ }                                                            │
│                                                              │
│ CONTRADICTION CHECK:                                        │
│ ├─→ Kay claimed: Saga.eye_color = brown                    │
│ ├─→ Retrieved memories contain: Saga.eye_color = brown     │
│ └─→ ✓ NO CONTRADICTION - values match                      │
│                                                              │
│ ENTITY GRAPH UPDATE:                                        │
│ └─→ Add attribute: Saga.eye_color = brown                  │
│     (turn 5, source: kay, timestamp: ...)                  │
│     [Second mention - strengthens confidence]               │
│                                                              │
│ Now entity graph shows:                                     │
│ Saga:                                                        │
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

Kay internally generates: "Saga has blue eyes"
     ↓
Line 481: encode() - Extract facts
     ↓
┌─────────────────────────────────────────────────────────────┐
│ Extracted:                                                  │
│ {                                                            │
│   "fact": "Saga has blue eyes",                            │
│   "perspective": "kay",                                     │
│   "entities": ["Saga"],                                     │
│   "attributes": [                                           │
│     {"entity": "Saga", "attribute": "eye_color",           │
│      "value": "blue"}                                       │
│   ]                                                          │
│ }                                                            │
│                                                              │
│ CONTRADICTION CHECK:                                        │
│ ├─→ Kay claimed: Saga.eye_color = blue                     │
│ ├─→ Retrieved memories contain: Saga.eye_color = brown     │
│ └─→ ❌ CONTRADICTION DETECTED!                             │
│                                                              │
│ HALLUCINATION PREVENTION:                                   │
│ └─→ ❌ BLOCK STORAGE - Do not store this fact              │
│                                                              │
│ Console: [MEMORY WARNING] ❌ Kay stated 'Saga has blue...' │
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
TURN 1-2: New entity "Saga" created
     ↓
WORKING MEMORY (capacity: 10)
  [0] Saga is Re's dog (strength: 1.0, accesses: 0)
  [1] Saga.species = dog (strength: 1.0, accesses: 0)
     ↓
TURN 3-5: User asks about Saga multiple times
     ↓
WORKING MEMORY
  [0] Saga is Re's dog (strength: 0.95, accesses: 3) ← Accessed 3x
  [1] Saga.species = dog (strength: 0.92, accesses: 2)
  [2] Saga.breed = golden retriever (strength: 1.0, accesses: 1)
  [3] Saga.eye_color = brown (strength: 1.0, accesses: 2)
     ↓
TURN 6: Promotion threshold reached (accesses >= 2)
     ↓
EPISODIC MEMORY (capacity: 100)
  [0] Saga is Re's dog ← PROMOTED (accesses: 3)
     ↓
WORKING MEMORY (9/10)
  [1] Saga.species = dog (accesses: 2) ← Will promote soon
  [2] Saga.breed = golden retriever (accesses: 1)
  [3] Saga.eye_color = brown (accesses: 2) ← Will promote soon
     ↓
TURN 10: Temporal decay applied
     ↓
EPISODIC MEMORY
  [0] Saga is Re's dog
      - Age: 8 turns (~0.2 days)
      - Importance: 0.65 (emotional context)
      - Halflife: 7 × (1 + 0.65) = 11.55 days
      - Strength: 0.5^(0.2/11.55) = 0.988 (minimal decay)
     ↓
TURN 15-20: User frequently mentions Saga
     ↓
EPISODIC MEMORY
  [0] Saga is Re's dog (accesses: 7) ← Getting close to semantic
  [1] Saga.species = dog (accesses: 5) ← Threshold reached!
     ↓
TURN 21: Promotion to semantic
     ↓
SEMANTIC MEMORY (unlimited, no decay)
  [0] Saga.species = dog ← PROMOTED (permanent fact)
     ↓
EPISODIC MEMORY (99/100)
  [0] Saga is Re's dog (accesses: 7) ← Still growing
     ↓
TURN 50: Long-term memory established
     ↓
SEMANTIC MEMORY (permanent facts)
  [0] Saga.species = dog
  [1] Saga is Re's dog (promoted after many accesses)
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
