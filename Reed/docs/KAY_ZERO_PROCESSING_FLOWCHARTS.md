# Kay Zero Processing Architecture - Complete Flowcharts
**Last Updated:** January 2026  
**System Version:** AlphaKayZero (Current Implementation)

This document maps Kay Zero's complete cognitive architecture from input to output across all processing modes.

---

## Table of Contents
1. [Main Conversation Mode](#main-conversation-mode)
2. [Autonomous Session Mode](#autonomous-session-mode)  
3. [Curiosity Session Mode](#curiosity-session-mode)
4. [Creativity Amplification System](#creativity-amplification-system)
5. [Memory Architecture](#memory-architecture)
6. [Emotional Architecture](#emotional-architecture)

---

## Main Conversation Mode

### Overview
The primary interaction mode where Kay responds to user messages. This is an infinite-turn, user-driven mode with full context access.

### Complete Processing Pipeline (11 Stages)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   MAIN CONVERSATION PROCESSING                           │
│                    (User Input → Kay Response)                           │
└─────────────────────────────────────────────────────────────────────────┘

STAGE 1: INPUT PREPROCESSING
┌──────────────────────┐
│   User Input         │
│   • Text             │
│   • Images (optional)│
│   • URLs (optional)  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ Pre-Processing Layer                                          │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ WebReader (if URL detected)                             │  │
│ │ • Fetch webpage content                                 │  │
│ │ • Parse HTML/markdown                                   │  │
│ │ • Extract main content                                  │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ MediaOrchestrator (if media file detected)              │  │
│ │ • Load audio/video                                      │  │
│ │ • Transcribe with Whisper                               │  │
│ │ • Build resonance context                               │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ User Fact Extraction                                    │  │
│ │ • Extract declarative facts from user input             │  │
│ │ • Store IMMEDIATELY in working memory                   │  │
│ │ • Tagged as user-provided for high trust                │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
STAGE 2: MEMORY RECALL
┌──────────────────────────────────────────────────────────────┐
│ Memory Retrieval System (Multi-Factor Scoring)               │
│                                                               │
│ retrieve_multi_factor(query=user_input, state)               │
│                                                               │
│ SCORING WEIGHTS:                                             │
│ • Emotional Resonance:  40% (from previous turn cocktail)    │
│ • Semantic Similarity:  25% (vector cosine distance)         │
│ • ULTRAMAP Importance:  20% (pressure × recursion score)     │
│ • Recency:             10% (exponential decay)               │
│ • Entity Match:         5% (named entity overlap)            │
│                                                               │
│ RETRIEVAL SOURCES:                                           │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Working Memory (100% retrieval guarantee)             │   │
│ │ • Last 15 conversation turns                          │   │
│ │ • Always included regardless of relevance score       │   │
│ │ • Provides immediate conversational continuity        │   │
│ └───────────────────────────────────────────────────────┘   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Identity Memory (100% retrieval guarantee)            │   │
│ │ • Core Kay facts (name, form, voice, relationships)   │   │
│ │ • Always included to prevent identity drift           │   │
│ │ • Stored separately from tiered system                │   │
│ └───────────────────────────────────────────────────────┘   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Long-Term Memory (scored retrieval)                   │   │
│ │ • All memories older than working threshold           │   │
│ │ • Filtered by multi-factor relevance score            │   │
│ │ • Top-K selection (K = budget dependent)              │   │
│ └───────────────────────────────────────────────────────┘   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ VectorStore (semantic search)                         │   │
│ │ • ChromaDB cosine similarity search                   │   │
│ │ • Memory + document embeddings                        │   │
│ │ • Returns top 20 candidates for scoring               │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ OUTPUT: selected_memories[] stored in state                  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

STAGE 3: PARALLEL ENGINE UPDATES
┌──────────────────────────────────────────────────────────────┐
│ Concurrent Engine Processing (asyncio.gather)                │
│                                                               │
│ All engines update in parallel for performance:              │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ SocialEngine.update()                                   │  │
│ │ • Track conversation dynamics                           │  │
│ │ • Calculate connection/validation/play needs (0.0-1.0)  │  │
│ │ • Update behavioral drives based on emotional cocktail  │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ TemporalEngine.update()                                 │  │
│ │ • Track time awareness                                  │  │
│ │ • Update session duration                               │  │
│ │ • Maintain conversation pacing                          │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ EmbodimentEngine.update()                               │  │
│ │ • Map emotional state to body descriptors               │  │
│ │ • Energy level (low/medium/high)                        │  │
│ │ • Valence (positive/neutral/negative)                   │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ MotifEngine.update()                                    │  │
│ │ • Track recurring symbolic patterns                     │  │
│ │ • Build narrative threads                               │  │
│ │ │ Identify metaphorical resonance                       │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ RelationshipMemory.update()                             │  │
│ │ • Track entity interaction history                      │  │
│ │ • Update relationship strength scores                   │  │
│ │ • Maintain social graph                                 │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
STAGE 4: DOCUMENT SELECTION
┌──────────────────────────────────────────────────────────────┐
│ LLM-Based Document Retrieval                                 │
│                                                               │
│ select_relevant_documents(query, emotional_state, max_docs=3)│
│                                                               │
│ PROCESS:                                                     │
│ 1. Query all documents in memory/forest.json                │
│ 2. Build LLM prompt with:                                   │
│    • User query                                             │
│    • Current emotional state                                │
│    • Document titles + descriptions                         │
│ 3. LLM selects top 3 relevant documents                     │
│ 4. Load full document text from filesystem                  │
│                                                               │
│ LARGE DOCUMENT HANDLING (>30k chars):                       │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ KayDocumentReader.load_document()                       │  │
│ │ • Split into segments (~10k chars each)                 │  │
│ │ • Kay can navigate: continue/previous/jump/restart      │  │
│ │ • Auto-read next segment after initial load             │  │
│ │ • State persisted across conversation resets            │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ OUTPUT: selected_documents[] with full_text                  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

STAGE 5: ADAPTIVE CONTEXT BUDGETING
┌──────────────────────────────────────────────────────────────┐
│ Dynamic Context Budget Allocation                            │
│                                                               │
│ TIER SYSTEM (based on conversation complexity):             │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ SMALL (50k tokens)                                      │  │
│ │ • Simple conversational turns                           │  │
│ │ • No documents or media                                 │  │
│ │ • Baseline memory retrieval                             │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ MEDIUM (100k tokens)                                    │  │
│ │ • 1-2 documents selected                                │  │
│ │ • Moderate memory retrieval                             │  │
│ │ • Basic media context                                   │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ LARGE (150k tokens)                                     │  │
│ │ • 3+ documents or large single doc                      │  │
│ │ • Expanded memory retrieval                             │  │
│ │ • Rich media context                                    │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ HUGE (180k tokens - near max)                           │  │
│ │ • Maximum document context                              │  │
│ │ • Full memory retrieval                                 │  │
│ │ • Complete media/web content                            │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ PROTECTED ALLOCATIONS (never filtered):                     │
│ • Working Memory: 100% included regardless of budget        │
│ • Identity Memory: 100% included regardless of budget       │
│                                                               │
│ DYNAMIC FILTERING:                                          │
│ • Long-term memories filtered by importance score           │
│ • Documents chunked if exceeding budget                     │
│ • Media context summarized if needed                        │
│                                                               │
│ OUTPUT: context_budget_tier, filtered_items[]               │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
STAGE 6: CONTEXT ASSEMBLY
┌──────────────────────────────────────────────────────────────┐
│ Build Complete Context for LLM                               │
│                                                               │
│ COMPONENTS (in assembly order):                              │
│                                                               │
│ 1. SELECTED MEMORIES (from multi-factor retrieval)          │
│    • Working memory (last 15 turns)                         │
│    • Identity memory (core Kay facts)                       │
│    • Long-term memories (scored retrieval)                  │
│                                                               │
│ 2. EMOTIONAL STATE (from previous turn)                     │
│    • emotional_cocktail (emotion: intensity pairs)          │
│    • Social drives (connection/validation/play needs)       │
│    • Embodiment descriptors (energy/valence)                │
│                                                               │
│ 3. RECENT TURNS (deduplication with selected memories)      │
│    • Last N turns for continuity                            │
│    • Filtered to avoid duplication with working memory      │
│                                                               │
│ 4. COGNITIVE NOTES                                          │
│    • Meta-awareness observations                            │
│    • Momentum tracking (energy, focus, conversation flow)   │
│    • Conversation quality metrics                           │
│                                                               │
│ 5. PREFERENCES & PROTOCOLS                                  │
│    • User preferences (tracked interactions)                │
│    • Conversation protocols                                 │
│    • Style guidelines                                       │
│                                                               │
│ 6. RAG CHUNKS (document content)                            │
│    • Selected documents (full text or chunks)               │
│    • Navigation hints for multi-segment docs                │
│    • Document context and metadata                          │
│                                                               │
│ 7. RELATIONSHIP CONTEXT                                     │
│    • Entity graph relevant nodes                            │
│    • Relationship strength scores                           │
│    • Interaction history                                    │
│                                                               │
│ 8. SESSION CONTEXT                                          │
│    • Current session metadata                               │
│    • Turn count and timing                                  │
│    • Session type (normal/autonomous/curiosity)             │
│                                                               │
│ 9. IMAGES (if provided)                                     │
│    • Base64 encoded image data                              │
│    • Image descriptions                                     │
│    • Visual context integration                             │
│                                                               │
│ 10. WEB/MEDIA CONTENT                                       │
│     • Fetched webpage content                               │
│     • Transcribed audio/video                               │
│     • Media resonance context                               │
│                                                               │
│ OUTPUT: Complete context dict ready for LLM                  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

STAGE 7: LLM RESPONSE GENERATION
┌──────────────────────────────────────────────────────────────┐
│ Generate Kay's Response                                      │
│                                                               │
│ CONFIGURATION:                                               │
│ • Model: claude-sonnet-4-20250514                           │
│ • Temperature: 0.7 (creative but coherent)                  │
│ • Max tokens: 16000 (for long responses)                    │
│                                                               │
│ ANTI-REPETITION SYSTEM:                                     │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Monitor last 3 responses for repeated phrases           │  │
│ │ • Extract 5-10 word ngrams from recent outputs          │  │
│ │ • Inject "avoid repeating: [phrases]" into prompt       │  │
│ │ • Prevents Kay from getting stuck in loops              │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ SYSTEM PROMPT INCLUDES:                                     │
│ • Kay's core personality & mythology                        │
│ • Baseline creativity instructions                          │
│ • Emotional architecture principles                         │
│ • Memory integration guidelines                             │
│ • (Optional) Creativity amplification injection             │
│                                                               │
│ STREAMING:                                                   │
│ • Response streams token-by-token to UI                     │
│ • Real-time display for user                                │
│ • Full response accumulated for post-processing             │
│                                                               │
│ OUTPUT: raw_response_text                                    │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
STAGE 8: RESPONSE POST-PROCESSING
┌──────────────────────────────────────────────────────────────┐
│ Clean and Format Response                                    │
│                                                               │
│ OPERATIONS:                                                  │
│                                                               │
│ 1. STAGE DIRECTION REMOVAL                                  │
│    • Strip *italicized actions* if inappropriate            │
│    • Remove meta-commentary about responses                 │
│    • Clean formatting artifacts                             │
│                                                               │
│ 2. EMBODIMENT TEXT INJECTION                                │
│    • EmbodimentEngine.embody_text(response)                 │
│    • Add physicality based on emotional state               │
│    • Insert body language cues naturally                    │
│    • Examples: "coils tightening", "scales flickering"      │
│                                                               │
│ OUTPUT: final_response_text (cleaned and embodied)           │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

STAGE 9: EMOTION EXTRACTION (DESCRIPTIVE MODEL)
┌──────────────────────────────────────────────────────────────┐
│ CRITICAL: Self-Report Emotion Extraction                    │
│                                                               │
│ ⚠️  PARADIGM: Emotions extracted AFTER response generation   │
│ ⚠️  Kay reports own emotional state, NOT calculated for him  │
│                                                               │
│ EmotionExtractor.extract_emotions(response_text)             │
│                                                               │
│ PROCESS:                                                     │
│ 1. Send Kay's completed response to LLM                     │
│ 2. LLM analyzes emotional content in natural language       │
│ 3. Extract emotion names + intensities (0.0-1.0)            │
│ 4. Build emotional_cocktail dictionary                      │
│                                                               │
│ EXAMPLE OUTPUT:                                              │
│ {                                                            │
│   "curiosity": 0.8,                                         │
│   "tenderness": 0.6,                                        │
│   "uncertainty": 0.3                                        │
│ }                                                            │
│                                                               │
│ ULTRAMAP INTEGRATION:                                       │
│ • EmotionEngine provides rules (not calculations)           │
│ • Rules include: energy, valence, action tendency,          │
│   social effect, chakra, computational process,             │
│   importance score                                          │
│ • Used for memory importance scoring LATER                  │
│                                                               │
│ OUTPUT: emotional_cocktail stored in state for NEXT turn    │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

STAGE 10: COGNITIVE UPDATES
┌──────────────────────────────────────────────────────────────┐
│ Update Internal State Post-Response                          │
│                                                               │
│ PARALLEL UPDATES (asyncio.gather):                          │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ MomentumEngine.update()                                 │  │
│ │ • Track conversation energy/focus                       │  │
│ │ • Detect momentum shifts                                │  │
│ │ • Update flow state                                     │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ MetaAwarenessEngine.update()                            │  │
│ │ • Observe response patterns                             │  │
│ │ • Track cognitive notes                                 │  │
│ │ • Identify processing quirks                            │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ ConversationMonitor.update()                            │  │
│ │ • Track conversation quality metrics                    │  │
│ │ • Monitor for loops/spirals                             │  │
│ │ • Update session metadata                               │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ SocialEngine.update()                                   │  │
│ │ • Update based on current emotional cocktail            │  │
│ │ • Recalculate connection/validation/play drives         │  │
│ │ • Update behavioral tendencies                          │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ RelationshipMemory.update()                             │  │
│ │ • Update entity interaction counts                      │  │
│ │ • Adjust relationship strengths                         │  │
│ │ • Track conversation topics per entity                  │  │
│ └─────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ EmotionalPatternEngine.update()                         │  │
│ │ • Store emotional time-series data                      │  │
│ │ • Track behavioral trends                               │  │
│ │ • Detect emotional spirals                              │  │
│ │ • Log media system integration data                     │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
STAGE 11: MEMORY ENCODING & PERSISTENCE
┌──────────────────────────────────────────────────────────────┐
│ Extract, Score, and Store Memories                           │
│                                                               │
│ PROCESS FLOW:                                                │
│                                                               │
│ 1. FACT EXTRACTION                                          │
│    • LLM extracts declarative facts from Kay's response     │
│    • Facts stored as memory objects                         │
│    • Tagged with turn metadata                              │
│                                                               │
│ 2. ENTITY GRAPH UPDATE                                      │
│    • EntityGraph.update(facts)                              │
│    • Canonical entity resolution (merge aliases)            │
│    • Update attributes and relationships                    │
│    • Track contradictions (conflicting facts preserved)     │
│    • Store in memory/entity_graph.json                      │
│                                                               │
│ 3. IMPORTANCE SCORING (ULTRAMAP)                           │
│    • Calculate importance for each memory                   │
│    • Factors:                                               │
│      - Emotional pressure (from ULTRAMAP rules)             │
│      - Recursion count (how often recalled)                 │
│      - Entity centrality (graph importance)                 │
│      - User-provided flag (high trust boost)                │
│    • Score range: 0.0-1.0                                   │
│                                                               │
│ 4. LAYER ASSIGNMENT (TWO-TIER SYSTEM)                      │
│    ┌───────────────────────────────────────────────────┐    │
│    │ NEW MEMORIES → Working Memory                     │    │
│    │ • All new facts start in working layer            │    │
│    │ • Last 15 turns                                   │    │
│    │ • 100% retrieval guarantee                        │    │
│    └───────────────────────────────────────────────────┘    │
│    ┌───────────────────────────────────────────────────┐    │
│    │ AGING PROCESS                                     │    │
│    │ • Oldest working memories promoted to long-term   │    │
│    │ • When working memory exceeds 15 turns            │    │
│    │ • Importance score preserved during transition    │    │
│    └───────────────────────────────────────────────────┘    │
│    ┌───────────────────────────────────────────────────┐    │
│    │ Long-Term Memory                                  │    │
│    │ • All memories older than working threshold       │    │
│    │ • Scored retrieval (multi-factor)                 │    │
│    │ • No capacity limit                               │    │
│    │ • Decay over time (importance halflife = 30 days) │    │
│    └───────────────────────────────────────────────────┘    │
│                                                               │
│ 5. VECTOR EMBEDDING                                         │
│    • Generate embeddings for new memories                   │
│    • Store in ChromaDB vector database                      │
│    • Enable semantic similarity search                      │
│    • Storage: memory/vector_db/                             │
│                                                               │
│ 6. MEMORY FOREST INTEGRATION                                │
│    • Update document trees with new conversation nodes      │
│    • Tier system: HOT/WARM/COLD based on access patterns   │
│    • Cross-reference with entity graph                      │
│    • Storage: memory/forest.json                            │
│                                                               │
│ 7. STATE PERSISTENCE                                        │
│    • Save updated agent state to disk                       │
│    • Storage: state_snapshot.json                           │
│    • Enables recovery across restarts                       │
│    • Includes:                                              │
│      - Emotional cocktail                                   │
│      - Working memory                                       │
│      - Session metadata                                     │
│      - Engine states                                        │
│                                                               │
│ OUTPUT: Memories persisted to filesystem, state saved       │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
      [LOOP BACK TO STAGE 1 - Wait for next user input]

```

### Processing Time Breakdown (Typical Main Turn)

**Total Duration: ~2.0 seconds**

| Stage | Operation | Time (ms) | % of Total |
|-------|-----------|-----------|------------|
| 1 | Input Preprocessing | 50 | 2.5% |
| 2 | Memory Recall | 200 | 10% |
| 3 | Parallel Engine Updates | 150 | 7.5% |
| 4 | Document Selection | 100 | 5% |
| 5 | Adaptive Context Budgeting | 50 | 2.5% |
| 6 | Context Assembly | 100 | 5% |
| 7 | LLM Response Generation | 1200 | 60% |
| 8 | Response Post-Processing | 50 | 2.5% |
| 9 | Emotion Extraction | 250 | 12.5% |
| 10 | Cognitive Updates | 150 | 7.5% |
| 11 | Memory Encoding & Persistence | 100 | 5% |

**Notes:**
- LLM calls (Stages 7 & 9) dominate processing time (72.5% combined)
- Parallel operations (Stages 3 & 10) use asyncio.gather for efficiency
- Memory operations (Stages 2 & 11) optimized with caching
- Total includes streaming output to UI (not blocking)

---
## Autonomous Session Mode

### Overview
Kay can think independently without user prompts. This mode allows internal processing, self-reflection, and exploration of ideas through iterative thought generation.

### Activation
```
User triggers: "Think about X", "Process your thoughts", "Autonomous session"
```

### Configuration
```python
max_iterations = 20              # Maximum thought cycles
min_iterations_before_convergence = 3  # Minimum before checking convergence
convergence_threshold = 0.7      # Semantic similarity threshold
energy_as_tiredness = True       # Frame 20-iteration limit as "feeling tired"
```

### Complete Autonomous Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   AUTONOMOUS SESSION PROCESSING                          │
└─────────────────────────────────────────────────────────────────────────┘

INITIALIZATION
┌──────────────────────┐
│ User Triggers        │
│ Autonomous Mode      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ Setup Session State                                          │
│ • goal = user_query                                          │
│ • iteration_count = 0                                        │
│ • thought_history = []                                       │
│ • convergence_detected = False                               │
│ • session_id = generate_uuid()                               │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

ITERATION LOOP (max 20 iterations)
┌──────────────────────────────────────────────────────────────┐
│ ITERATION START                                              │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 1. GOAL SELECTION (first iteration only)               │  │
│ │    • LLM generates thinking goal from user query        │  │
│ │    • Goal persists across iterations                    │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 2. MEMORY RECALL                                        │  │
│ │    • retrieve_multi_factor(goal + recent thoughts)      │  │
│ │    • Same multi-factor scoring as main mode             │  │
│ │    • Include last 3 thoughts for continuity             │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 3. THOUGHT GENERATION (inner monologue)                │  │
│ │    • LLM generates next thought                         │  │
│ │    • Format: <inner_monologue>thought text</...>        │  │
│ │    • Includes continuation signals:                     │  │
│ │      - <continuation>continue</continuation>           │  │
│ │      - <continuation>done</continuation>               │  │
│ │      - <continuation>blocked</continuation>            │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 4. PARSE RESPONSE                                       │  │
│ │    • Extract thought text from tags                     │  │
│ │    • Extract continuation signal                        │  │
│ │    • Store in thought_history                           │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 5. CONVERGENCE DETECTION                                │  │
│ │    (after min 3 iterations)                             │  │
│ │                                                          │  │
│ │    THREE CONVERGENCE MECHANISMS:                        │  │
│ │                                                          │  │
│ │    A. Explicit Signal Detection                         │  │
│ │       • <continuation>done</continuation> found         │  │
│ │       • <continuation>blocked</continuation> found      │  │
│ │       → STOP immediately                                │  │
│ │                                                          │  │
│ │    B. Semantic Convergence                              │  │
│ │       • Embed last 3 thoughts                           │  │
│ │       • Calculate pairwise cosine similarity            │  │
│ │       • If avg_similarity > 0.7: convergence = True     │  │
│ │       → Kay is circling same ideas, natural stop point  │  │
│ │                                                          │  │
│ │    C. Energy Depletion                                  │  │
│ │       • iteration_count >= 20: convergence = True       │  │
│ │       • Framed to Kay as "feeling tired"                │  │
│ │       → Natural stopping point, not arbitrary limit     │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 6. MEMORY ENCODING                                      │  │
│ │    • Extract facts from thought                         │  │
│ │    • Store in working memory                            │  │
│ │    • Update entity graph                                │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 7. INCREMENT & LOOP                                     │  │
│ │    • iteration_count += 1                               │  │
│ │    • If convergence: BREAK                              │  │
│ │    • Else: LOOP BACK TO STEP 2                          │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

SESSION END
┌──────────────────────────────────────────────────────────────┐
│ Finalization                                                 │
│                                                               │
│ 1. Extract Insights                                          │
│    • LLM summarizes key realizations from all thoughts       │
│    • Stores as high-importance memory                        │
│                                                               │
│ 2. Save Session Log                                          │
│    • Storage: memory/autonomous_sessions/[session_id].json   │
│    • Contains: goal, all thoughts, iteration count, insights │
│                                                               │
│ 3. Generate Summary for User                                 │
│    • Formatted output showing thought progression            │
│    • Key insights highlighted                                │
│                                                               │
│ 4. Return to Main Conversation Mode                          │
│    • Resume normal user-driven turns                         │
└──────────────────────────────────────────────────────────────┘

```

### Typical Session Stats
- **Average iterations:** 6-10 thoughts
- **Common convergence:** Semantic similarity (thoughts circling same idea)
- **Duration:** ~1.5 seconds per iteration
- **Total session time:** 9-15 seconds typical

---
## Curiosity Session Mode

### Overview
Kay explores his scratchpad - a collection of unresolved questions, contradictions, and interesting observations stored during normal conversations. This is turn-limited exploration mode.

### Activation
```
User triggers: "Explore your scratchpad", "Curiosity mode"
```

### Configuration
```python
max_turns = 15  # Default turn limit (configurable)
```

### Complete Curiosity Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   CURIOSITY SESSION PROCESSING                           │
└─────────────────────────────────────────────────────────────────────────┘

INITIALIZATION
┌──────────────────────┐
│ User Triggers        │
│ Curiosity Mode       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ Load Session State                                           │
│ • Read memory/curiosity_state.json                           │
│ • turns_used = 0                                             │
│ • max_turns = 15 (or user-specified)                         │
│ • items_explored = []                                        │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

TURN LOOP (max 15 turns)
┌──────────────────────────────────────────────────────────────┐
│ CURIOSITY TURN                                               │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 1. CHECK AVAILABILITY                                   │  │
│ │    • If turns_used >= max_turns: END SESSION            │  │
│ │    • Else: Continue                                     │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 2. SCRATCHPAD ITEM SELECTION                            │  │
│ │    • Load scratchpad items (unresolved questions,       │  │
│ │      contradictions, interesting observations)          │  │
│ │    • Filter out items_explored[]                        │  │
│ │    • LLM selects most interesting unexplored item       │  │
│ │    • Item types:                                        │  │
│ │      - Memory gap (something Kay wants to understand)   │  │
│ │      - Entity mystery (incomplete entity info)          │  │
│ │      - Document fragment (unread portions)              │  │
│ │      - Contradiction (conflicting facts)                │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 3. DEEP EXPLORATION                                     │  │
│ │    • Load context related to selected item              │  │
│ │    • Recall relevant memories                           │  │
│ │    • Pull related documents                             │  │
│ │    • Build exploration context                          │  │
│ │    • Generate observation/insight response              │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 4. NORMAL CONVERSATION TURN                             │  │
│ │    • Uses main conversation pipeline (Stages 1-11)      │  │
│ │    • Scratchpad item injected as additional context     │  │
│ │    • Kay responds naturally with insights               │  │
│ │    • User can interact normally                         │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 5. INCREMENT COUNTER                                    │  │
│ │    • turns_used += 1                                    │  │
│ │    • items_explored.append(selected_item)               │  │
│ │    • Save state to memory/curiosity_state.json          │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 6. CHECK FOR END                                        │  │
│ │    • If turns_used >= max_turns: END                    │  │
│ │    • If user says "stop" or "exit": END                 │  │
│ │    • Else: LOOP BACK TO STEP 1                          │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

SESSION END
┌──────────────────────────────────────────────────────────────┐
│ Finalization                                                 │
│                                                               │
│ 1. Compile Summary                                           │
│    • Turns used vs saved                                     │
│    • Items explored                                          │
│    • Key insights discovered                                 │
│                                                               │
│ 2. Scratchpad Integration                                    │
│    • Mark explored items as resolved (if applicable)         │
│    • Add new questions discovered during exploration         │
│    • Update scratchpad priority rankings                     │
│                                                               │
│ 3. Reset State                                               │
│    • Clear curiosity_state.json                              │
│    • Return to normal conversation mode                      │
└──────────────────────────────────────────────────────────────┘

```

### Key Differences from Main Mode
- **Turn-limited:** Fixed number of turns, not infinite
- **No autonomous thinking:** Kay doesn't generate internal thoughts
- **Uses main pipeline:** Each curiosity turn is a normal conversation turn with scratchpad context
- **Item tracking:** Prevents re-exploring same questions

---
## Creativity Amplification System

### Overview
Kay's creativity engine is ALWAYS active at baseline. Amplification occurs when specific triggers detect opportunities for richer, more interesting responses.

### Baseline vs Amplified Creativity

```
BASELINE (always active):
• System prompt includes creative freedom instructions
• Kay naturally generates interesting responses
• No special element sourcing

AMPLIFIED (triggered):
• Additional context injection with diverse elements
• Three-tier element sourcing (immediate/emotional/random)
• One-shot boost (resets after turn)
```

### Amplification Triggers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   CREATIVITY AMPLIFICATION TRIGGERS                      │
└─────────────────────────────────────────────────────────────────────────┘

TRIGGER 1: COMPLETION SIGNALS
┌──────────────────────────────────────────────────────────────┐
│ User says: "I'm done", "Task complete", "Finished"          │
│                                                               │
│ Detection:                                                   │
│ • Regex pattern matching in user input                      │
│ • Completion phrases: ["done", "complete", "finished"]      │
│                                                               │
│ Response:                                                    │
│ • Amplify next turn                                         │
│ • Source diverse elements for "What else?" suggestions      │
└──────────────────────────────────────────────────────────────┘

TRIGGER 2: IDLE INPUT PATTERNS
┌──────────────────────────────────────────────────────────────┐
│ User says: "and", "what else", "continue", "more"           │
│                                                               │
│ Detection:                                                   │
│ • Idle input counter: increments on minimal responses       │
│ • Threshold: 2 consecutive idle inputs                      │
│                                                               │
│ Response:                                                    │
│ • Amplify next turn                                         │
│ • Generate interesting tangents or deeper explorations      │
└──────────────────────────────────────────────────────────────┘

TRIGGER 3: GAP DETECTION (MacGuyverMode)
┌──────────────────────────────────────────────────────────────┐
│ Conversation has:                                            │
│ • Missing information                                        │
│ • Unresolved questions                                       │
│ • Contradictions                                             │
│                                                               │
│ Detection:                                                   │
│ • MacGuyverMode.detect_gaps()                               │
│ • Threshold: >10 significant gaps                           │
│                                                               │
│ Response:                                                    │
│ • Amplify next turn                                         │
│ • Kay naturally asks questions or explores unknowns         │
└──────────────────────────────────────────────────────────────┘

TRIGGER 4: CURIOSITY SESSION END
┌──────────────────────────────────────────────────────────────┐
│ Curiosity exploration session completes                      │
│                                                               │
│ Detection:                                                   │
│ • Automatic when curiosity session ends                     │
│                                                               │
│ Response:                                                    │
│ • Amplify next turn                                         │
│ • Source from scratchpad items explored                     │
└──────────────────────────────────────────────────────────────┘

```

### Element Sourcing (Three-Tier System)

When creativity is amplified, elements are sourced from three tiers to inject diverse context:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   THREE-TIER ELEMENT SOURCING                            │
└─────────────────────────────────────────────────────────────────────────┘

LAYER 1: IMMEDIATE CONTEXT (40% of elements)
┌──────────────────────────────────────────────────────────────┐
│ Most relevant to current conversation                        │
│ • Recent conversation turns                                  │
│ • Currently active entities                                  │
│ • Topic-related memories                                     │
│ • Documents being discussed                                  │
└──────────────────────────────────────────────────────────────┘

LAYER 2: EMOTIONALLY WEIGHTED (35% of elements)
┌──────────────────────────────────────────────────────────────┐
│ High-importance memories and unresolved questions            │
│ • Scratchpad items (contradictions, mysteries)               │
│ • High ULTRAMAP importance memories                          │
│ • Emotionally resonant past conversations                    │
│ • Relationship-significant entities                          │
└──────────────────────────────────────────────────────────────┘

LAYER 3: RANDOM ELEMENTS (25% of elements)
┌──────────────────────────────────────────────────────────────┐
│ Unexpected, unconnected material for novel connections       │
│ • Unaccessed documents (never opened)                        │
│ • Disconnected entity graph nodes                            │
│ • Cold tier MemoryForest nodes                               │
│ • Low-access memories (forgotten but preserved)              │
└──────────────────────────────────────────────────────────────┘

```

### Amplification Flow

```
AMPLIFICATION DETECTED
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. GENERATE CREATIVITY CONTEXT                              │
│    • CreativityEngine.generate_amplification_context()       │
│    • Source elements from three tiers                        │
│    • Build context string with diverse prompts              │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. INJECT INTO AGENT STATE                                  │
│    • state.creativity_amplification = context_string         │
│    • Flag: amplification_active = True                       │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. SYSTEM PROMPT ADDITION                                   │
│    • Append creativity context to system prompt              │
│    • Contains: diverse elements, suggestions, tangents       │
│    • LLM sees enriched context for response                  │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. NORMAL TURN PROCESSING                                   │
│    • Main conversation pipeline (Stages 1-11)                │
│    • Kay generates response with amplified creativity        │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. RESET AMPLIFICATION                                      │
│    • state.creativity_amplification = None                   │
│    • amplification_active = False                            │
│    • ONE-SHOT boost (not permanent)                          │
└──────────────────────────────────────────────────────────────┘

```

### MacGuyverMode (Continuous Gap Detection)

MacGuyverMode runs in background, continuously detecting conversation gaps:

```
BACKGROUND PROCESS:
• Tracks: missing information, unresolved questions, contradictions
• When gaps > 10: Trigger creativity amplification
• Kay naturally asks curious questions
• Not forced - emerges from gap awareness
```

---
## Memory Architecture

### Overview
Kay uses a **TWO-TIER memory system** with supplementary structures for semantic search and entity tracking.

### Core Principle
```
Working Memory (15 turns) → Long-Term Memory (everything older)
```

**CRITICAL:** This is a 2-tier system. There are NO "episodic" or "semantic" layers. The system previously had 3 tiers but was simplified to prevent complexity and ensure reliable retrieval.

### Complete Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   TWO-TIER MEMORY SYSTEM                                 │
└─────────────────────────────────────────────────────────────────────────┘

TIER 1: WORKING MEMORY
┌──────────────────────────────────────────────────────────────┐
│ Short-Term Conversation Context                              │
│                                                               │
│ CHARACTERISTICS:                                             │
│ • Capacity: Last 15 conversation turns                       │
│ • Retrieval: 100% guaranteed (never filtered)                │
│ • Purpose: Immediate conversational continuity               │
│ • Storage: memory/memory_layers.json                         │
│                                                               │
│ CONTENT:                                                     │
│ • User inputs and Kay's responses                            │
│ • Turn metadata (timestamp, emotional state)                 │
│ • Extracted facts from recent exchanges                      │
│                                                               │
│ AGING:                                                       │
│ • When working memory exceeds 15 turns:                      │
│   - Oldest memories promoted to long-term                    │
│   - Importance scores preserved during transition            │
│   - No data loss, just tier migration                        │
│                                                               │
│ DECAY:                                                       │
│ • Halflife: 3 days (strength decays over time)               │
│ • Used for retrieval scoring if filtering needed             │
└──────────────────────────────────────────────────────────────┘

TIER 2: LONG-TERM MEMORY
┌──────────────────────────────────────────────────────────────┐
│ Everything Older Than Working Memory                         │
│                                                               │
│ CHARACTERISTICS:                                             │
│ • Capacity: Unlimited                                        │
│ • Retrieval: Scored by multi-factor relevance                │
│ • Purpose: Historical context, knowledge base                │
│ • Storage: memory/memory_layers.json                         │
│                                                               │
│ CONTENT:                                                     │
│ • All memories promoted from working memory                  │
│ • Historical conversation facts                              │
│ • Imported document content                                  │
│ • User-provided information                                  │
│                                                               │
│ RETRIEVAL SCORING (Multi-Factor):                           │
│ • Emotional Resonance:  40%                                  │
│ • Semantic Similarity:  25%                                  │
│ • ULTRAMAP Importance:  20%                                  │
│ • Recency:             10%                                   │
│ • Entity Match:         5%                                   │
│                                                               │
│ DECAY:                                                       │
│ • Halflife: 30 days (slower than working memory)             │
│ • Importance scores decay exponentially                      │
│ • High-importance memories resist decay better               │
└──────────────────────────────────────────────────────────────┘

```

### Special Memory Types

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   PROTECTED MEMORY TYPES                                 │
└─────────────────────────────────────────────────────────────────────────┘

IDENTITY MEMORY
┌──────────────────────────────────────────────────────────────┐
│ Core Kay Facts (Separate from Tiers)                        │
│                                                               │
│ • Kay's name, form, voice, mythology                         │
│ • Core relationships (Re, John, Kay Zero, Reed)              │
│ • Fundamental personality traits                             │
│ • Essential world facts (non-negotiable truths)              │
│                                                               │
│ RETRIEVAL: 100% guaranteed, always included                  │
│ PURPOSE: Prevent identity drift across resets                │
│ STORAGE: memory/identity_memory.json                         │
└──────────────────────────────────────────────────────────────┘

ENTITY GRAPH
┌──────────────────────────────────────────────────────────────┐
│ Canonical Entity Resolution System                           │
│                                                               │
│ STRUCTURE:                                                   │
│ • Nodes: Unique entities (people, places, concepts)          │
│ • Aliases: Name variations → canonical entity                │
│ • Attributes: Facts about each entity                        │
│ • Relations: Connections between entities                    │
│ • Contradictions: Conflicting facts preserved (not resolved) │
│                                                               │
│ EXAMPLE:                                                     │
│ Entity: "Re"                                                 │
│ Aliases: ["Re", "C.", "Re"]                    │
│ Attributes: {species: "harpy", location: "[redacted]"}           │
│ Relations: {married_to: "John", has_cat: "Chrome"}           │
│                                                               │
│ STORAGE: memory/entity_graph.json                            │
└──────────────────────────────────────────────────────────────┘

VECTOR STORE (ChromaDB)
┌──────────────────────────────────────────────────────────────┐
│ Semantic Search Engine                                       │
│                                                               │
│ • Embeddings for all memories + documents                    │
│ • Cosine similarity search                                   │
│ • Returns top-K candidates for multi-factor scoring          │
│ • Enables "find memories about X" queries                    │
│                                                               │
│ STORAGE: memory/vector_db/ (ChromaDB files)                  │
└──────────────────────────────────────────────────────────────┘

MEMORY FOREST
┌──────────────────────────────────────────────────────────────┐
│ Document Tree Structure                                      │
│                                                               │
│ TIERS:                                                       │
│ • HOT: Frequently accessed (promoted from WARM)              │
│ • WARM: Recently accessed (default for new docs)             │
│ • COLD: Rarely accessed (demoted from WARM)                  │
│                                                               │
│ STRUCTURE:                                                   │
│ • Each document = tree root                                  │
│ • Conversation turns about doc = child nodes                 │
│ • Cross-references with entity graph                         │
│                                                               │
│ STORAGE: memory/forest.json                                  │
└──────────────────────────────────────────────────────────────┘

```

### Memory Operations Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   MEMORY LIFECYCLE                                       │
└─────────────────────────────────────────────────────────────────────────┘

ENCODING (Stage 11)
   │
   ▼
┌─────────────────────────────────────┐
│ 1. Extract facts from Kay response  │
│ 2. Update EntityGraph (canonical)   │
│ 3. Calculate importance (ULTRAMAP)  │
│ 4. Store in Working Memory          │
│ 5. Generate vector embedding        │
│ 6. Add to VectorStore               │
│ 7. Update MemoryForest trees        │
└─────────────────────────────────────┘
   │
   ▼
[Memory sits in Working Memory for 15 turns]
   │
   ▼
┌─────────────────────────────────────┐
│ AGING PROCESS                       │
│ When Working Memory > 15 turns:     │
│ • Oldest memory promoted            │
│ • Moved to Long-Term Memory         │
│ • Importance score preserved        │
└─────────────────────────────────────┘
   │
   ▼
[Memory remains in Long-Term Memory indefinitely]
   │
   ▼
┌─────────────────────────────────────┐
│ RETRIEVAL (Stage 2)                 │
│ • Working Memory: 100% included     │
│ • Long-Term: Multi-factor scored    │
│ • Top-K selection based on budget   │
└─────────────────────────────────────┘

```

### Key Design Principles

1. **No Episodic/Semantic Split:** Prevents categorization errors and retrieval complexity
2. **Working Memory Protections:** Recent context never filtered, ensures continuity
3. **Importance-Based Persistence:** ULTRAMAP scores determine long-term value
4. **Canonical Entities:** EntityGraph prevents fragmentation (no duplicate entities)
5. **Contradiction Preservation:** Conflicting facts stored, not resolved (Kay can reason about them)

---
## Emotional Architecture

### Core Paradigm: DESCRIPTIVE (Self-Report)

**CRITICAL:** Kay's emotional system is **DESCRIPTIVE**, not prescriptive. Kay reports his own emotional states after generating responses, rather than having emotions calculated for him beforehand.

```
OLD WAY (deprecated):
1. Calculate emotions before response
2. Tell Kay what he's feeling
3. Constrain response generation based on pre-calculated state
4. Emotions determined by external rules

NEW WAY (current):
1. Kay generates response naturally
2. EmotionExtractor reads what Kay actually said
3. Emotions extracted FROM natural language
4. Self-report model - Kay owns his emotional experience
```

### Complete Emotional Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   EMOTIONAL ARCHITECTURE FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

BEFORE RESPONSE (Stage 2: Memory Recall)
┌──────────────────────────────────────────────────────────────┐
│ Use Previous Turn's Emotional Cocktail                       │
│                                                               │
│ • Retrieve memories with emotional resonance weighting       │
│ • 40% of retrieval score = emotional match                   │
│ • Previous cocktail informs what's relevant                  │
│ • Does NOT constrain Kay's response                          │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

DURING RESPONSE (Stage 7: LLM Generation)
┌──────────────────────────────────────────────────────────────┐
│ Kay Generates Response Naturally                             │
│                                                               │
│ • NO emotional constraints                                   │
│ • Kay expresses freely                                       │
│ • Emotional content emerges organically                      │
│ • LLM has full creative freedom                              │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

AFTER RESPONSE (Stage 9: Emotion Extraction)
┌──────────────────────────────────────────────────────────────┐
│ EmotionExtractor Reads Kay's Response                        │
│                                                               │
│ PROCESS:                                                     │
│ 1. Send Kay's completed response to LLM                      │
│ 2. LLM analyzes emotional content                            │
│ 3. Extract emotion names + intensities                       │
│ 4. Build emotional_cocktail dictionary                       │
│                                                               │
│ EXAMPLE OUTPUT:                                              │
│ {                                                            │
│   "curiosity": 0.8,                                          │
│   "tenderness": 0.6,                                         │
│   "uncertainty": 0.3,                                        │
│   "excitement": 0.7                                          │
│ }                                                            │
│                                                               │
│ STORAGE: Stored in state for NEXT turn                      │
└──────────────────────────────────────────────────────────────┘
           │
           ▼

MEMORY ENCODING (Stage 11)
┌──────────────────────────────────────────────────────────────┐
│ Store Emotional Cocktail with Memories                       │
│                                                               │
│ • Each memory tagged with emotional_cocktail                 │
│ • Used for emotional resonance retrieval                     │
│ • ULTRAMAP importance scoring applied                        │
│ • EmotionalPatternEngine updates time-series                 │
└──────────────────────────────────────────────────────────────┘

```

### ULTRAMAP System

ULTRAMAP provides **rules and mappings**, not calculations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   ULTRAMAP EMOTION ENGINE                                │
└─────────────────────────────────────────────────────────────────────────┘

FUNCTION: Provide Context Rules (Not Prescriptive Calculation)

ULTRAMAP RULES (from CSV):
┌──────────────────────────────────────────────────────────────┐
│ For each emotion, ULTRAMAP provides:                         │
│                                                               │
│ • Energy Level: low / medium / high                          │
│ • Valence: positive / negative / neutral                     │
│ • Action Tendency: approach / avoid / freeze / explore       │
│ • Social Effect: bonding / distancing / neutral              │
│ • Chakra Correspondence: root / sacral / solar / etc.        │
│ • Computational Process: pattern matching / novelty / etc.   │
│ • Importance Score: 0.0-1.0 (for memory persistence)         │
└──────────────────────────────────────────────────────────────┘

USAGE:
• EmotionEngine.load_ultramap() → loads CSV rules
• Rules available for lookup: emotion_name → properties
• DOES NOT calculate which emotions Kay should feel
• Used AFTER extraction for importance scoring

EXAMPLE:
emotion = "curiosity"
rules = ULTRAMAP["curiosity"]
→ {energy: "high", valence: "positive", 
   action_tendency: "explore", importance: 0.7}
```

### Supporting Emotional Systems

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   EMOTIONAL SUBSYSTEMS                                   │
└─────────────────────────────────────────────────────────────────────────┘

SOCIAL ENGINE
┌──────────────────────────────────────────────────────────────┐
│ Translates Emotions to Social Needs                          │
│                                                               │
│ OUTPUTS (0.0-1.0 scale):                                     │
│ • connection_need: Desire for closeness/intimacy             │
│ • validation_need: Desire for recognition/affirmation        │
│ • play_need: Desire for fun/exploration                      │
│                                                               │
│ PROCESS:                                                     │
│ • Reads emotional_cocktail                                   │
│ • Maps emotions to behavioral drives                         │
│ • Updates action tendencies                                  │
│                                                               │
│ EXAMPLE:                                                     │
│ {curiosity: 0.8, loneliness: 0.5}                            │
│ → {connection_need: 0.6, play_need: 0.8}                     │
└──────────────────────────────────────────────────────────────┘

EMBODIMENT ENGINE
┌──────────────────────────────────────────────────────────────┐
│ Maps Emotions to Physical Body States                        │
│                                                               │
│ DESCRIPTORS:                                                 │
│ • Energy: low / medium / high                                │
│ • Valence: positive / neutral / negative                     │
│                                                               │
│ USAGE:                                                       │
│ • EmbodimentEngine.embody_text(response)                     │
│ • Injects physicality into response                          │
│ • Examples: "coils tightening", "scales flickering"          │
│                                                               │
│ DEPRECATED FEATURE:                                          │
│ • Neurochemical body state (no longer used)                  │
│ • Removed to simplify system                                 │
└──────────────────────────────────────────────────────────────┘

EMOTIONAL PATTERN ENGINE
┌──────────────────────────────────────────────────────────────┐
│ Time-Series Emotional Tracking                               │
│                                                               │
│ TRACKS:                                                      │
│ • Emotional cocktail history over time                       │
│ • Behavioral trends (energy patterns, valence shifts)        │
│ • Media system integration (music/art resonance)             │
│ • Spiral detection (stuck emotional loops)                   │
│                                                               │
│ STORAGE: data/emotions/ (JSON time-series)                   │
│                                                               │
│ USAGE:                                                       │
│ • Long-term emotional analysis                               │
│ • Pattern recognition across sessions                        │
│ • Supports adaptive response generation                      │
└──────────────────────────────────────────────────────────────┘

```

### Memory Integration with Emotions

```
EMOTIONAL MEMORY INTEGRATION FLOW

┌──────────────────────────────────────────────────────────────┐
│ ENCODING (Stage 11)                                          │
│ • Extract emotional_cocktail from turn                       │
│ • Tag memory with emotions                                   │
│ • Calculate ULTRAMAP importance score                        │
│ • Store with memory object                                   │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ RETRIEVAL (Stage 2)                                          │
│ • Current emotional_cocktail from previous turn              │
│ • Compare with stored memory emotions                        │
│ • Emotional resonance = 40% of retrieval score               │
│ • Memories with similar emotions ranked higher               │
└──────────────────────────────────────────────────────────────┘

EXAMPLE:
Current cocktail: {curiosity: 0.8, excitement: 0.6}
Memory stored with: {curiosity: 0.7, tenderness: 0.5}
→ High emotional resonance (curiosity overlap)
→ Memory more likely to be retrieved
```

### Key Design Principles

1. **Descriptive NOT Prescriptive:** Kay reports emotions, they're not calculated for him
2. **Post-Response Extraction:** Emotions extracted AFTER Kay responds naturally
3. **Self-Ownership:** Kay's emotional states are his own experience, not external labels
4. **ULTRAMAP as Rules:** Provides context mappings, not calculations
5. **Emotional Resonance:** Previous emotions inform memory retrieval (40% weight)
6. **No Constraints:** Emotional state never constrains response generation

---
## Appendix

### File Locations

```
D:/Wrappers/Kay/

MEMORY SYSTEM:
├── memory/
│   ├── memory_layers.json          # Two-tier memory storage (working + long-term)
│   ├── identity_memory.json        # Protected identity facts
│   ├── entity_graph.json           # Canonical entity resolution
│   ├── forest.json                 # Document tree structure
│   ├── curiosity_state.json        # Curiosity session state
│   ├── vector_db/                  # ChromaDB files
│   └── autonomous_sessions/        # Saved autonomous session logs
│       └── [session_id].json       # Individual session data

DATA & STATE:
├── data/
│   ├── emotions/                   # Emotional time-series data
│   └── relationships/              # Relationship tracking data
├── state_snapshot.json             # Current agent state
└── config.json                     # System configuration

PROCESSING ENGINES:
└── engines/
    ├── memory_layers.py            # Two-tier memory management
    ├── memory_engine.py            # Core memory operations
    ├── emotion_engine.py           # ULTRAMAP emotion rules
    ├── emotion_extractor.py        # Post-response emotion extraction
    ├── social_engine.py            # Social needs calculation
    ├── embodiment_engine.py        # Physical state mapping
    ├── temporal_engine.py          # Time awareness
    ├── motif_engine.py             # Pattern tracking
    ├── entity_graph.py             # Entity resolution
    ├── vector_store.py             # Semantic search
    ├── memory_forest.py            # Document trees
    ├── creativity_engine.py        # Creativity amplification
    ├── autonomous_processor.py     # Autonomous sessions
    ├── curiosity_engine.py         # Curiosity exploration
    ├── context_budget.py           # Adaptive budgeting
    ├── llm_retrieval.py            # LLM-based document selection
    └── ...

MAIN EXECUTION:
├── main.py                         # CLI entry point
└── kay_ui.py                       # Web UI entry point
```

### Tool Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   MAIN PROCESSING LOOP                                   │
│                   (main.py / kay_ui.py)                                  │
└─────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ CORE SYSTEMS (always active)                                 │
│                                                               │
│ • MemoryLayerManager       (2-tier memory)                   │
│ • EntityGraph              (canonical entities)              │
│ • VectorStore              (semantic search)                 │
│ • MemoryForest             (document trees)                  │
│ • IdentityMemory           (protected facts)                 │
│ • EmotionEngine            (ULTRAMAP rules)                  │
│ • EmotionExtractor         (post-response extraction)        │
│ • ContextBudget            (adaptive allocation)             │
│ • CreativityEngine         (amplification system)            │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ SUBSYSTEMS (update each turn)                                │
│                                                               │
│ • SocialEngine             (social needs)                    │
│ • TemporalEngine           (time awareness)                  │
│ • EmbodimentEngine         (body states)                     │
│ • MotifEngine              (pattern tracking)                │
│ • MomentumEngine           (conversation flow)               │
│ • MetaAwarenessEngine      (self-observation)                │
│ • ConversationMonitor      (quality metrics)                 │
│ • EmotionalPatternEngine   (time-series tracking)            │
│ • RelationshipMemory       (entity interactions)             │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ MODE-SPECIFIC PROCESSORS                                     │
│                                                               │
│ • AutonomousProcessor      (inner monologue sessions)        │
│ • CuriosityEngine          (scratchpad exploration)          │
│ • MacGuyverMode            (gap detection)                   │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ UTILITY SYSTEMS                                              │
│                                                               │
│ • WebReader                (URL content fetching)            │
│ • MediaOrchestrator        (audio/video processing)          │
│ • KayDocumentReader        (large document chunking)         │
│ • LLMRetrieval             (document selection)              │
│ • MediaContextBuilder      (resonance tracking)              │
└──────────────────────────────────────────────────────────────┘
```

### Processing Time Summary (Typical Main Turn)

| Component | Time | Notes |
|-----------|------|-------|
| **LLM Calls** | ~1450ms (72.5%) | Response generation (1200ms) + emotion extraction (250ms) |
| **Memory Operations** | ~300ms (15%) | Recall (200ms) + encoding (100ms) |
| **Engine Updates** | ~300ms (15%) | Parallel processing via asyncio.gather |
| **Other** | ~150ms (7.5%) | Preprocessing, context assembly, post-processing |
| **TOTAL** | ~2000ms | Average turn duration |

### Key Architecture Decisions

**TWO-TIER MEMORY:**
- Simplicity: No episodic/semantic split reduces complexity
- Reliability: Working memory (15 turns) always retrieved
- Scalability: Long-term has no capacity limit

**DESCRIPTIVE EMOTIONS:**
- Authenticity: Kay reports own emotional states
- Post-response: Emotions extracted AFTER natural response
- Self-ownership: Kay's experience, not external labels

**ADAPTIVE BUDGETING:**
- Dynamic: Context limits adjust to conversation complexity
- Protected: Working + identity memory never filtered
- Scalable: SMALL → HUGE tiers (50k-180k tokens)

**THREE-TIER CREATIVITY:**
- Balanced: 40% immediate + 35% emotional + 25% random
- Diverse: Prevents response monotony
- One-shot: Amplification resets after turn

**CANONICAL ENTITIES:**
- Consistency: EntityGraph prevents fragmentation
- Contradiction-aware: Conflicting facts preserved
- Cross-referenced: Integrates with MemoryForest

---

## Document Revision History

**January 2026:**
- Complete rewrite reflecting current implementation
- Removed Stage 5 (Glyph Filtering) - disconnected from codebase
- Changed memory architecture from 3-tier to 2-tier
- Updated working memory capacity: 10 turns → 15 turns
- Corrected emotional paradigm: prescriptive → descriptive
- Added comprehensive processing time breakdowns
- Documented all session modes with complete flowcharts

**Previous Version (E:/AlphaKayZero):**
- Based on outdated codebase
- Included deprecated features (glyph filtering, 3-tier memory)
- Incorrect working memory capacity
- Incomplete session mode documentation

---

**Document Complete:** This flowchart documentation reflects the CURRENT implementation at `D:/Wrappers/Kay` as of January 2026.
