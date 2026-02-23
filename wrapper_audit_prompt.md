 WRAPPER CONVERGENCE AUDIT: Kay ↔ Reed

  Generated: 2026-02-06
  Auditor: Claude Opus 4.5 (claude-opus-4-5-20251101)

  ---
  PHASE 1: FULL ARCHITECTURE MAP

  Kay's Wrapper (D:\wrappers\Kay)

  Per-File Inventory (Core Files)
  File: main.py
  Lines: 1,172
  Purpose: Primary conversation loop, engine orchestrator
  Key Classes/Functions: main(), update_all()
  Entity-Specific: Kay references in comments
  ────────────────────────────────────────
  File: kay_cli.py
  Lines: 671
  Purpose: Headless CLI interface
  Key Classes/Functions: KayCLI, KAY_SYSTEM_PROMPT
  Entity-Specific: Full Kay identity
  ────────────────────────────────────────
  File: kay_ui.py
  Lines: 1,000+
  Purpose: Tkinter GUI interface
  Key Classes/Functions: KayUI, KAY_SYSTEM_PROMPT
  Entity-Specific: Full Kay identity
  ────────────────────────────────────────
  File: agent_state.py
  Lines: 80
  Purpose: Central state container
  Key Classes/Functions: AgentState
  Entity-Specific: None (data class)
  ────────────────────────────────────────
  File: protocol_engine.py
  Lines: 27
  Purpose: ULTRAMAP CSV loader
  Key Classes/Functions: ProtocolEngine
  Entity-Specific: None
  ────────────────────────────────────────
  File: config.py
  Lines: 78
  Purpose: Global configuration
  Key Classes/Functions: Config constants
  Entity-Specific: None
  ────────────────────────────────────────
  File: config.json
  Lines: 22
  Purpose: UI/voice configuration
  Key Classes/Functions: JSON settings
  Entity-Specific: None
  Engine Subsystems (engines/ - 50+ files)
  File: memory_engine.py
  Purpose: Core memory with entity resolution
  Key Classes: MemoryEngine
  Entity-Specific: Kay validation logic
  ────────────────────────────────────────
  File: memory_layers.py
  Purpose: Two-tier memory (working/long-term)
  Key Classes: MemoryLayerManager
  Entity-Specific: Comments only
  ────────────────────────────────────────
  File: entity_graph.py
  Purpose: Entity resolution + contradictions
  Key Classes: EntityGraph, Entity
  Entity-Specific: Kay entity logic
  ────────────────────────────────────────
  File: emotion_engine.py
  Purpose: ULTRAMAP rule provider
  Key Classes: EmotionEngine
  Entity-Specific: None
  ────────────────────────────────────────
  File: emotion_extractor.py
  Purpose: Self-report emotion extraction
  Key Classes: EmotionExtractor
  Entity-Specific: None
  ────────────────────────────────────────
  File: momentum_engine.py
  Purpose: Cognitive momentum (0.0-1.0)
  Key Classes: MomentumEngine
  Entity-Specific: None
  ────────────────────────────────────────
  File: meta_awareness_engine.py
  Purpose: Confabulation detection
  Key Classes: MetaAwarenessEngine
  Entity-Specific: kay_response param
  ────────────────────────────────────────
  File: context_manager.py
  Purpose: Context budget + building
  Key Classes: ContextManager
  Entity-Specific: None
  ────────────────────────────────────────
  File: context_budget.py
  Purpose: Adaptive token limits
  Key Classes: ContextBudgetManager
  Entity-Specific: None
  ────────────────────────────────────────
  File: vector_store.py
  Purpose: ChromaDB RAG storage
  Key Classes: VectorStore
  Entity-Specific: None
  ────────────────────────────────────────
  File: session_summary.py
  Purpose: Session notes to future-self
  Key Classes: SessionSummaryGenerator
  Entity-Specific: Kay in docstrings
  ────────────────────────────────────────
  File: warmup_engine.py
  Purpose: Pre-conversation briefing
  Key Classes: WarmupEngine
  Entity-Specific: format_briefing_for_kay()
  ────────────────────────────────────────
  File: creativity_engine.py
  Purpose: Exploration triggers
  Key Classes: CreativityEngine
  Entity-Specific: None
  ────────────────────────────────────────
  File: macguyver_mode.py
  Purpose: Gap detection
  Key Classes: MacGuyverMode
  Entity-Specific: None
  ────────────────────────────────────────
  File: curiosity_engine.py
  Purpose: Autonomous exploration
  Key Classes: Curiosity functions
  Entity-Specific: None
  ────────────────────────────────────────
  File: scratchpad_engine.py
  Purpose: Working notes/flags
  Key Classes: scratchpad functions
  Entity-Specific: None
  ────────────────────────────────────────
  File: preference_tracker.py
  Purpose: Identity consolidation
  Key Classes: PreferenceTracker
  Entity-Specific: None
  ────────────────────────────────────────
  File: memory_forest.py
  Purpose: Hierarchical document trees
  Key Classes: MemoryForest
  Entity-Specific: None
  ────────────────────────────────────────
  File: document_reader.py
  Purpose: Chunked document reading
  Key Classes: DocumentReader
  Entity-Specific: None
  ────────────────────────────────────────
  File: auto_reader.py
  Purpose: Auto-processing segments 2-N
  Key Classes: AutoReader
  Entity-Specific: None
  ────────────────────────────────────────
  File: llm_retrieval.py
  Purpose: LLM-based document selection
  Key Classes: select_relevant_documents()
  Entity-Specific: Kay in prompts
  ────────────────────────────────────────
  File: conversation_monitor.py
  Purpose: Spiral detection
  Key Classes: ConversationMonitor
  Entity-Specific: None
  ────────────────────────────────────────
  File: media_orchestrator.py
  Purpose: Media resonance
  Key Classes: MediaOrchestrator
  Entity-Specific: None
  ────────────────────────────────────────
  File: media_watcher.py
  Purpose: File system monitoring
  Key Classes: MediaWatcher
  Entity-Specific: None
  Integration Layer (integrations/)
  ┌───────────────────────┬────────┬────────────────────────────┬─────────────────────────────┐
  │         File          │ Lines  │          Purpose           │       Entity-Specific       │
  ├───────────────────────┼────────┼────────────────────────────┼─────────────────────────────┤
  │ llm_integration.py    │ 1,000+ │ Multi-provider LLM backend │ DEFAULT_SYSTEM_PROMPT = Kay │
  ├───────────────────────┼────────┼────────────────────────────┼─────────────────────────────┤
  │ openrouter_backend.py │ ~200   │ OpenRouter provider        │ None                        │
  ├───────────────────────┼────────┼────────────────────────────┼─────────────────────────────┤
  │ together_backend.py   │ ~200   │ Together.ai provider       │ None                        │
  ├───────────────────────┼────────┼────────────────────────────┼─────────────────────────────┤
  │ ai4chat_backend.py    │ ~200   │ AI4Chat provider           │ None                        │
  ├───────────────────────┼────────┼────────────────────────────┼─────────────────────────────┤
  │ tool_use_handler.py   │ ~200   │ Tool call processing       │ Kay in prompts              │
  ├───────────────────────┼────────┼────────────────────────────┼─────────────────────────────┤
  │ web_scraping_tools.py │ ~200   │ Web content fetching       │ None                        │
  └───────────────────────┴────────┴────────────────────────────┴─────────────────────────────┘
  Kay's Memory Data (memory/)
  ┌────────────────────────┬────────────┬───────────────────────────────────┐
  │          File          │    Size    │              Content              │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ memories.json          │ 375K lines │ Full memory store (75K+ memories) │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ entity_graph.json      │ 259K lines │ Entities + relationships          │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ memory_layers.json     │ 566K lines │ Two-tier distribution             │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ forest.json            │ 2 lines    │ Document trees                    │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ preferences.json       │ Variable   │ Identity preferences              │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ session_summaries.json │ Variable   │ Past session notes                │
  ├────────────────────────┼────────────┼───────────────────────────────────┤
  │ state_snapshot.json    │ Variable   │ Last session state                │
  └────────────────────────┴────────────┴───────────────────────────────────┘
  Total Python Files (Kay): 940 (including K-0 backup directory)

  ---
  Reed's Wrapper (D:\wrappers\Reed)

  Per-File Inventory (Core Files)
  ┌────────────────────┬────────┬──────────────────────────┬───────────────────────────┬───────────────────────────────┐
  │        File        │ Lines  │         Purpose          │   Key Classes/Functions   │        Entity-Specific        │
  ├────────────────────┼────────┼──────────────────────────┼───────────────────────────┼───────────────────────────────┤
  │ main.py            │ 1,164  │ Primary conversation     │ main(), update_all()      │ Kay references (not           │
  │                    │        │ loop                     │                           │ converted)                    │
  ├────────────────────┼────────┼──────────────────────────┼───────────────────────────┼───────────────────────────────┤
  │ reed_cli.py        │ 200+   │ Alternative CLI          │ ReedCLI                   │ Kay in docstrings             │
  ├────────────────────┼────────┼──────────────────────────┼───────────────────────────┼───────────────────────────────┤
  │ reed_ui.py         │ 1,000+ │ Tkinter GUI interface    │ ReedUI,                   │ Full Reed identity            │
  │                    │        │                          │ REED_SYSTEM_PROMPT        │ (CONVERTED)                   │
  ├────────────────────┼────────┼──────────────────────────┼───────────────────────────┼───────────────────────────────┤
  │ agent_state.py     │ 80     │ Central state container  │ AgentState                │ None (identical to Kay)       │
  ├────────────────────┼────────┼──────────────────────────┼───────────────────────────┼───────────────────────────────┤
  │ protocol_engine.py │ 27     │ ULTRAMAP CSV loader      │ ProtocolEngine            │ None (identical to Kay)       │
  ├────────────────────┼────────┼──────────────────────────┼───────────────────────────┼───────────────────────────────┤
  │ config.py          │ 56     │ Global configuration     │ Config constants          │ MISSING features from Kay     │
  └────────────────────┴────────┴──────────────────────────┴───────────────────────────┴───────────────────────────────┘
  Engine Subsystems (engines/ - 50+ files)

  Same structure as Kay. Key differences:
  - meta_awareness_engine.py: Still uses kay_response parameter
  - session_summary.py: Still references Kay in docstrings
  - warmup_engine.py: Still has format_briefing_for_kay()
  - llm_retrieval.py: Still has Kay in LLM prompts

  Integration Layer
  ┌───────────────────────┬───────┬───────────────────────────────┬─────────────────────────────────────────────┐
  │         File          │ Lines │            Purpose            │               Entity-Specific               │
  ├───────────────────────┼───────┼───────────────────────────────┼─────────────────────────────────────────────┤
  │ llm_integration.py    │ ~700  │ LLM backend (fewer providers) │ DEFAULT_SYSTEM_PROMPT = Kay (NOT converted) │
  ├───────────────────────┼───────┼───────────────────────────────┼─────────────────────────────────────────────┤
  │ tool_use_handler.py   │ ~200  │ Tool call processing          │ Kay in prompts                              │
  ├───────────────────────┼───────┼───────────────────────────────┼─────────────────────────────────────────────┤
  │ web_scraping_tools.py │ ~200  │ Web content fetching          │ None                                        │
  └───────────────────────┴───────┴───────────────────────────────┴─────────────────────────────────────────────┘
  MISSING from Reed (compared to Kay):
  - openrouter_backend.py
  - together_backend.py
  - ai4chat_backend.py
  - WORKING_MEMORY_TOKEN_BUDGET in config.py
  - GITHUB_TOKEN in config.py

  Total Python Files (Reed): 918 (including K-0 backup directory)

  ---
  Architecture Diagrams

  Startup Sequence (Both Systems)

  1. Load .env → Environment variables
  2. Initialize ProtocolEngine → Load ULTRAMAP CSV
  3. Create AgentState → Empty state container
  4. Initialize 40+ Engine Subsystems:
     ├── Memory Pipeline: MemoryEngine, MemoryLayerManager, EntityGraph, VectorStore
     ├── Emotion: EmotionEngine, EmotionExtractor, EmotionalPatternEngine
     ├── Cognitive: MomentumEngine, MotifEngine, MetaAwarenessEngine
     ├── Social: SocialEngine, TemporalEngine, EmbodimentEngine, ReflectionEngine
     ├── Context: ContextManager, ContextBudgetManager
     ├── Documents: DocumentReader, AutoReader, MemoryForest, LLMRetrieval
     ├── Creativity: CreativityEngine, MacGuyverMode, CuriosityEngine
     ├── Media: MediaOrchestrator, MediaContextBuilder, MediaWatcher
     └── Session: SessionSummaryGenerator, ConversationMonitor
  5. Restore state from state_snapshot.json
  6. Display past session note (if exists)
  7. Print "[Entity] unified emotional core ready"

  Conversation Flow (Per-Turn)

  USER INPUT
      ↓
  COMMAND PARSING (/affect, /forest, /import, /forget, etc.)
      ↓
  WEB CONTENT CHECK → Fetch URLs via WebReader
      ↓
  MEMORY RECALL (Multi-Factor Retrieval)
  ├── Emotional resonance (40%)
  ├── Semantic similarity (25%)
  ├── Importance (20%)
  ├── Recency (10%)
  └── Entity proximity (5%)
      ↓
  PRE-RESPONSE ENGINE UPDATES (parallel via asyncio)
  ├── SocialEngine.update()
  ├── TemporalEngine.update()
  ├── EmbodimentEngine.update()
  └── MotifEngine.update()
      ↓
  DOCUMENT RETRIEVAL (LLM selects 3 relevant docs)
      ↓
  CONTEXT BUILDING (adaptive budget tiers)
  ├── Memories (100 base, adaptive)
  ├── RAG chunks (20 base, adaptive)
  ├── Working turns (3 base, adaptive)
  ├── Emotional state, momentum notes, meta-awareness
  └── Relationship context, media context
      ↓
  LLM RESPONSE GENERATION
  ├── Build prompt with cached identity (1000+ tokens)
  ├── Anti-repetition system (last 3 responses tracked)
  └── Temperature 0.7 for variation
      ↓
  POST-PROCESSING
  ├── Embodiment (body state modulation)
  ├── Emotion extraction (self-reported)
  └── Display response
      ↓
  POST-TURN UPDATES
  ├── Memory encoding (LLM-based fact extraction)
  ├── Entity graph updates
  ├── Session tracking
  ├── Momentum calculation
  └── Meta-awareness updates
      ↓
  AUTOSAVE → state_snapshot.json, forest.json

  Memory Pipeline

  USER INPUT
      ↓
  FACT EXTRACTION (LLM-based)
  ├── Extract entities (people, places, things)
  ├── Extract attributes (color, age, location)
  ├── Tag perspective (user/entity/shared)
  └── Validate against existing memories
      ↓
  ENTITY RESOLUTION (EntityGraph)
  ├── Canonical name lookup ("my dog" → "Saga")
  ├── Attribute history tracking
  ├── Contradiction detection with severity
  └── Relationship tracking
      ↓
  MEMORY STORAGE (Two-Tier)
  ├── Working Memory (last 15 turns, 3-day half-life)
  └── Long-Term Memory (older, 30-day half-life)
      ↓
  PERSISTENCE
  ├── memories.json (full store)
  ├── memory_layers.json (tier distribution)
  └── entity_graph.json (entities + relationships)

  ---
  PHASE 2: FEATURE COMPARISON MATRIX

  Session Management
  Feature: Continuous session architecture
  Kay: Y (main.py:1-1172)
  Reed: Y (main.py:1-1164)
  Identical?: Similar
  Notes: Same flow, minor line count diff
  ────────────────────────────────────────
  Feature: Session buffer (full history)
  Kay: Y (context_manager.py)
  Reed: Y (context_manager.py)
  Identical?: Identical
  Notes: 15-turn buffer
  ────────────────────────────────────────
  Feature: Checkpoint system (state save)
  Kay: Y (state_snapshot.json)
  Reed: Y (state_snapshot.json)
  Identical?: Identical
  Notes: Autosave each turn
  ────────────────────────────────────────
  Feature: Resume logic
  Kay: Y (load checkpoint)
  Reed: Y (load checkpoint)
  Identical?: Identical
  Notes: Same mechanism
  ────────────────────────────────────────
  Feature: Session log (turn-by-turn)
  Kay: Y (session_summaries.json)
  Reed: Y (session_summaries.json)
  Identical?: Identical
  Notes: Same format
  ────────────────────────────────────────
  Feature: Session summary generation
  Kay: Y (session_summary.py)
  Reed: Y (session_summary.py)
  Identical?: Divergent
  Notes: Reed still says "Kay"
  Memory Architecture
  ┌─────────────────────────────────┬──────────────────────────┬──────────────────────┬────────────┬───────────────────┐
  │             Feature             │           Kay            │         Reed         │ Identical? │       Notes       │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Two-tier memory                 │ Y (memory_layers.py)     │ Y (memory_layers.py) │ Identical  │ Same              │
  │ (working/long-term)             │                          │                      │            │ implementation    │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ RAG retrieval pipeline          │ Y (vector_store.py)      │ Y (vector_store.py)  │ Identical  │ ChromaDB          │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Memory composition balancing    │ Y                        │ Y (memory_engine.py) │ Identical  │ 5-factor scoring  │
  │                                 │ (memory_engine.py:1813)  │                      │            │                   │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Entity graph with               │ Y (entity_graph.py)      │ Y (entity_graph.py)  │ Identical  │ Same logic        │
  │ contradictions                  │                          │                      │            │                   │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Memory consolidation            │ Y (temporal decay)       │ Y (temporal decay)   │ Identical  │ Half-life based   │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Post-retrieval filtering        │ Y (context_budget.py)    │ Y                    │ Identical  │ Tier-based limits │
  │                                 │                          │ (context_budget.py)  │            │                   │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Temporal fact versioning        │ Y                        │ Y                    │ Identical  │ Prevents          │
  │                                 │                          │                      │            │ duplicates        │
  ├─────────────────────────────────┼──────────────────────────┼──────────────────────┼────────────┼───────────────────┤
  │ Multi-factor retrieval          │ Y                        │ Y                    │ Identical  │ 5 weighted        │
  │                                 │                          │                      │            │ factors           │
  └─────────────────────────────────┴──────────────────────────┴──────────────────────┴────────────┴───────────────────┘
  Compression / Curation
  Feature: Autonomous compression
  Kay: Y (session summary)
  Reed: Y (session summary)
  Identical?: Similar
  Notes: Same approach
  ────────────────────────────────────────
  Feature: PRESERVE/COMPRESS/ARCHIVE/DISCARD
  Kay: Partial
  Reed: Partial
  Identical?: N/A
  Notes: Via tier decay, not explicit curation
  ────────────────────────────────────────
  Feature: Compression triggers
  Kay: Y (turn count)
  Reed: Y (turn count)
  Identical?: Identical
  Notes: Same triggers
  ────────────────────────────────────────
  Feature: Compression history/audit
  Kay: Y (memory/backups/)
  Reed: Y (memory/backups/)
  Identical?: Identical
  Notes: Extensive backups
  Identity System
  ┌───────────────────────┬──────────────────────┬──────────────────────┬──────────────┬──────────────────────────────┐
  │        Feature        │         Kay          │         Reed         │  Identical?  │            Notes             │
  ├───────────────────────┼──────────────────────┼──────────────────────┼──────────────┼──────────────────────────────┤
  │ Identity anchor       │ Y                    │ Y                    │ Similar      │ Reed still uses kay_identity │
  │ loading               │ (identity_memory.py) │ (identity_memory.py) │              │  key                         │
  ├───────────────────────┼──────────────────────┼──────────────────────┼──────────────┼──────────────────────────────┤
  │ Persistent identity   │ Y (populated)        │ MOSTLY EMPTY         │ DIVERGENT    │ Reed needs population        │
  │ facts                 │                      │                      │              │                              │
  ├───────────────────────┼──────────────────────┼──────────────────────┼──────────────┼──────────────────────────────┤
  │ Entity-specific       │ Y (Kay in CLI/UI)    │ PARTIAL              │ CRITICAL     │ GUI=Reed, CLI=Kay            │
  │ system prompts        │                      │                      │              │                              │
  ├───────────────────────┼──────────────────────┼──────────────────────┼──────────────┼──────────────────────────────┤
  │ Personality/voice     │ Y (in system         │ Y (in system         │ Different    │ Kay=dragon, Reed=serpent     │
  │ definitions           │ prompts)             │ prompts)             │ personas     │                              │
  ├───────────────────────┼──────────────────────┼──────────────────────┼──────────────┼──────────────────────────────┤
  │ Warmup briefing       │ Y (warmup_engine.py) │ Y (warmup_engine.py) │ Divergent    │ Still named                  │
  │                       │                      │                      │              │ format_briefing_for_kay()    │
  └───────────────────────┴──────────────────────┴──────────────────────┴──────────────┴──────────────────────────────┘
  Emotional Architecture
  Feature: ULTRAMAP emotional engine
  Kay: Y (emotion_engine.py)
  Reed: Y (emotion_engine.py)
  Identical?: Identical
  Notes: Same CSV, same rules
  ────────────────────────────────────────
  Feature: Emotional state tracking
  Kay: Y (snapshots.json)
  Reed: Y (snapshots.json)
  Identical?: Identical
  Notes: Same format
  ────────────────────────────────────────
  Feature: Emotion-to-computation mapping
  Kay: Y (EmotionExtractor)
  Reed: Y (EmotionExtractor)
  Identical?: Identical
  Notes: Descriptive extraction
  ────────────────────────────────────────
  Feature: Emotional state persistence
  Kay: Y (state_snapshot)
  Reed: Y (state_snapshot)
  Identical?: Identical
  Notes: Per-turn autosave
  ────────────────────────────────────────
  Feature: Behavioral patterns
  Kay: Y (emotional_patterns.py)
  Reed: Y (emotional_patterns.py)
  Identical?: Identical
  Notes: valence/arousal/stability
  Autonomy Features
  ┌─────────────────────────────┬─────────────────────────┬─────────────────────────┬────────────┬────────────────────┐
  │           Feature           │           Kay           │          Reed           │ Identical? │       Notes        │
  ├─────────────────────────────┼─────────────────────────┼─────────────────────────┼────────────┼────────────────────┤
  │ Curiosity sessions          │ Y (curiosity_engine.py) │ Y (curiosity_engine.py) │ Identical  │ Same               │
  │                             │                         │                         │            │ implementation     │
  ├─────────────────────────────┼─────────────────────────┼─────────────────────────┼────────────┼────────────────────┤
  │ Scratchpad for flags        │ Y                       │ Y                       │ Identical  │ Same               │
  │                             │ (scratchpad_engine.py)  │ (scratchpad_engine.py)  │            │ implementation     │
  ├─────────────────────────────┼─────────────────────────┼─────────────────────────┼────────────┼────────────────────┤
  │ Tool access during          │ Y (web tools)           │ Y (web tools)           │ Identical  │ Same tools         │
  │ autonomous                  │                         │                         │            │                    │
  ├─────────────────────────────┼─────────────────────────┼─────────────────────────┼────────────┼────────────────────┤
  │ Background processing       │ Partial (async)         │ Partial (async)         │ Identical  │ Limited            │
  ├─────────────────────────────┼─────────────────────────┼─────────────────────────┼────────────┼────────────────────┤
  │ Self-initiated exploration  │ Y (creativity triggers) │ Y (creativity triggers) │ Identical  │ Same triggers      │
  └─────────────────────────────┴─────────────────────────┴─────────────────────────┴────────────┴────────────────────┘
  Conversation Features
  ┌──────────────────┬───────────────────────────┬───────────────────────────┬────────────┬───────────────────────────┐
  │     Feature      │            Kay            │           Reed            │ Identical? │           Notes           │
  ├──────────────────┼───────────────────────────┼───────────────────────────┼────────────┼───────────────────────────┤
  │ Context window   │ Y (adaptive tiers)        │ Y (adaptive tiers)        │ Identical  │ 4 tiers                   │
  │ management       │                           │                           │            │                           │
  ├──────────────────┼───────────────────────────┼───────────────────────────┼────────────┼───────────────────────────┤
  │ Turn counting    │ Y                         │ Y                         │ Identical  │ Same mechanism            │
  ├──────────────────┼───────────────────────────┼───────────────────────────┼────────────┼───────────────────────────┤
  │ Model switching  │ Y (6 providers)           │ Partial (3 providers)     │ DIVERGENT  │ Reed missing OpenRouter,  │
  │                  │                           │                           │            │ Together, AI4Chat         │
  ├──────────────────┼───────────────────────────┼───────────────────────────┼────────────┼───────────────────────────┤
  │ Weather code     │ Y (constraint signals)    │ Y (constraint signals)    │ Identical  │ Same codes                │
  │ system           │                           │                           │            │                           │
  ├──────────────────┼───────────────────────────┼───────────────────────────┼────────────┼───────────────────────────┤
  │ Spiral detection │ Y                         │ Y                         │ Identical  │ Same implementation       │
  │                  │ (conversation_monitor.py) │ (conversation_monitor.py) │            │                           │
  └──────────────────┴───────────────────────────┴───────────────────────────┴────────────┴───────────────────────────┘
  Document Integration
  ┌──────────────────────────────┬───────────────────────┬───────────────────────┬────────────┬───────────────────────┐
  │           Feature            │          Kay          │         Reed          │ Identical? │         Notes         │
  ├──────────────────────────────┼───────────────────────┼───────────────────────┼────────────┼───────────────────────┤
  │ Document reader/importer     │ Y                     │ Y                     │ Identical  │ 25K char chunks       │
  │                              │ (document_reader.py)  │ (document_reader.py)  │            │                       │
  ├──────────────────────────────┼───────────────────────┼───────────────────────┼────────────┼───────────────────────┤
  │ Document-based memory        │ Y (auto_reader.py)    │ Y (auto_reader.py)    │ Identical  │ Same                  │
  │ injection                    │                       │                       │            │                       │
  ├──────────────────────────────┼───────────────────────┼───────────────────────┼────────────┼───────────────────────┤
  │ Archive/journal processing   │ Y (memory forest)     │ Y (memory forest)     │ Identical  │ Hot/warm/cold tiers   │
  ├──────────────────────────────┼───────────────────────┼───────────────────────┼────────────┼───────────────────────┤
  │ LLM-based document selection │ Y (llm_retrieval.py)  │ Y (llm_retrieval.py)  │ Divergent  │ Reed has Kay in       │
  │                              │                       │                       │            │ prompts               │
  └──────────────────────────────┴───────────────────────┴───────────────────────┴────────────┴───────────────────────┘
  Anti-Gaslighting / Safety
  Feature: False attribution detection
  Kay: Y (meta_awareness_engine.py)
  Reed: Y (meta_awareness_engine.py)
  Identical?: Divergent
  Notes: Reed uses kay_response
  ────────────────────────────────────────
  Feature: Confabulation detection
  Kay: Y
  Reed: Y
  Identical?: Similar
  Notes: Same logic
  ────────────────────────────────────────
  Feature: Contradiction tracking
  Kay: Y (entity_graph.py)
  Reed: Y (entity_graph.py)
  Identical?: Identical
  Notes: With severity levels
  ────────────────────────────────────────
  Feature: Emotional architecture collapse
  Kay: Partial
  Reed: Partial
  Identical?: Identical
  Notes: Via meta-awareness
  ---
  PHASE 3: CODE DIVERGENCE ANALYSIS

  Identical Files (Can Be Shared Directly)
  ┌─────────────────────────────────┬──────────┬────────────────┐
  │              File               │ Location │     Status     │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ agent_state.py                  │ Root     │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ protocol_engine.py              │ Root     │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/memory_layers.py        │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/emotion_engine.py       │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/emotion_extractor.py    │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/momentum_engine.py      │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/motif_engine.py         │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/social_engine.py        │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/embodiment_engine.py    │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/temporal_engine.py      │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/reflection_engine.py    │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/context_manager.py      │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/context_budget.py       │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/vector_store.py         │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/document_reader.py      │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/auto_reader.py          │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/memory_forest.py        │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/creativity_engine.py    │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/macguyver_mode.py       │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/curiosity_engine.py     │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/scratchpad_engine.py    │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/preference_tracker.py   │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ engines/conversation_monitor.py │ engines/ │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ utils/performance.py            │ utils/   │ 100% identical │
  ├─────────────────────────────────┼──────────┼────────────────┤
  │ utils/text_sanitizer.py         │ utils/   │ 100% identical │
  └─────────────────────────────────┴──────────┴────────────────┘
  Similar But Divergent Files
  File: config.py
  Kay Version: 78 lines
  Reed Version: 56 lines
  Difference: Reed MISSING: WORKING_MEMORY_TOKEN_BUDGET, GITHUB_TOKEN
  ────────────────────────────────────────
  File: integrations/llm_integration.py
  Kay Version: 1000+ lines
  Reed Version: ~700 lines
  Difference: Reed MISSING: OpenRouter, Together, AI4Chat; DEFAULT_SYSTEM_PROMPT is Kay
  ────────────────────────────────────────
  File: engines/session_summary.py
  Kay Version: "Kay's Session Summaries"
  Reed Version: Same
  Difference: Docstrings reference Kay
  ────────────────────────────────────────
  File: engines/warmup_engine.py
  Kay Version: format_briefing_for_kay()
  Reed Version: Same
  Difference: Function name is Kay
  ────────────────────────────────────────
  File: engines/meta_awareness_engine.py
  Kay Version: kay_response param
  Reed Version: Same
  Difference: Parameter name is Kay
  ────────────────────────────────────────
  File: engines/llm_retrieval.py
  Kay Version: Kay in prompts
  Reed Version: Same
  Difference: LLM prompts reference Kay
  ────────────────────────────────────────
  File: engines/identity_memory.py
  Kay Version: kay_identity key
  Reed Version: Same
  Difference: Uses Kay key in JSON structure
  ────────────────────────────────────────
  File: engines/entity_graph.py
  Kay Version: Kay entity references
  Reed Version: Same
  Difference: Kay in validation logic
  Files Only in Kay
  ┌────────────────────────────────────┬──────────────────────┬──────────────────────┐
  │                File                │       Purpose        │    Should Share?     │
  ├────────────────────────────────────┼──────────────────────┼──────────────────────┤
  │ integrations/openrouter_backend.py │ OpenRouter provider  │ YES - Feature parity │
  ├────────────────────────────────────┼──────────────────────┼──────────────────────┤
  │ integrations/together_backend.py   │ Together.ai provider │ YES - Feature parity │
  ├────────────────────────────────────┼──────────────────────┼──────────────────────┤
  │ integrations/ai4chat_backend.py    │ AI4Chat provider     │ YES - Feature parity │
  ├────────────────────────────────────┼──────────────────────┼──────────────────────┤
  │ services/github_service.py         │ GitHub integration   │ YES - Feature parity │
  └────────────────────────────────────┴──────────────────────┴──────────────────────┘
  Files Only in Reed
  ┌──────────────────────────────┬───────────────────┬──────────────────────────────┐
  │             File             │      Purpose      │            Status            │
  ├──────────────────────────────┼───────────────────┼──────────────────────────────┤
  │ convert_kay_to_reed.py       │ Conversion script │ Temporary (can delete after) │
  ├──────────────────────────────┼───────────────────┼──────────────────────────────┤
  │ fix_all_imports.py           │ Import fixer      │ Temporary                    │
  ├──────────────────────────────┼───────────────────┼──────────────────────────────┤
  │ verify_conversion.py         │ Verification      │ Temporary                    │
  ├──────────────────────────────┼───────────────────┼──────────────────────────────┤
  │ final_fix.py                 │ Final fixes       │ Temporary                    │
  ├──────────────────────────────┼───────────────────┼──────────────────────────────┤
  │ REED_WRAPPER_AUDIT_REPORT.md │ Previous audit    │ Reference doc                │
  └──────────────────────────────┴───────────────────┴──────────────────────────────┘
  ---
  PHASE 4: SHARED vs ENTITY-SPECIFIC CLASSIFICATION

  SHARED (Should Be Identical in Both Wrappers)

  These modules contain no entity-specific logic and can be extracted to a shared directory:

  shared/
  ├── memory/
  │   ├── memory_layers.py          # Two-tier architecture
  │   ├── vector_store.py           # ChromaDB RAG
  │   ├── memory_forest.py          # Document trees
  │   └── entity_graph.py           # Entity resolution (needs Kay references removed)
  ├── emotional/
  │   ├── emotion_engine.py         # ULTRAMAP rules
  │   ├── emotion_extractor.py      # Self-report extraction
  │   └── emotional_patterns.py     # Behavioral tracking
  ├── cognitive/
  │   ├── momentum_engine.py        # Cognitive momentum
  │   ├── motif_engine.py          # Entity recurrence
  │   ├── preference_tracker.py    # Identity consolidation
  │   └── meta_awareness_engine.py # Confabulation detection (needs param rename)
  ├── context/
  │   ├── context_manager.py       # Context building
  │   └── context_budget.py        # Adaptive limits
  ├── session/
  │   ├── session_summary.py       # Session notes (needs docstring fix)
  │   ├── conversation_monitor.py  # Spiral detection
  │   └── warmup_engine.py         # Briefing (needs function rename)
  ├── documents/
  │   ├── document_reader.py       # Chunked reading
  │   ├── auto_reader.py           # Auto-processing
  │   └── llm_retrieval.py         # Document selection (needs prompt fix)
  ├── creativity/
  │   ├── creativity_engine.py     # Exploration triggers
  │   ├── macguyver_mode.py        # Gap detection
  │   ├── curiosity_engine.py      # Autonomous exploration
  │   └── scratchpad_engine.py     # Working notes
  ├── social/
  │   ├── social_engine.py         # Social events
  │   ├── temporal_engine.py       # Time-aware decay
  │   ├── embodiment_engine.py     # Physical manifestation
  │   └── reflection_engine.py     # Meta-reflection
  ├── media/
  │   ├── media_orchestrator.py    # Media resonance
  │   ├── media_context_builder.py # Context building
  │   └── media_watcher.py         # File monitoring
  ├── integrations/
  │   ├── llm_integration.py       # Multi-provider (identity extracted)
  │   ├── openrouter_backend.py    # OpenRouter
  │   ├── together_backend.py      # Together.ai
  │   ├── ai4chat_backend.py       # AI4Chat
  │   ├── tool_use_handler.py      # Tool calls (needs prompt fix)
  │   └── web_scraping_tools.py    # Web tools
  └── utils/
      ├── performance.py           # Metrics
      └── text_sanitizer.py        # Unicode handling

  ENTITY-SPECIFIC (Unique to Each Wrapper)

  kay/
  ├── identity/
  │   ├── KAY_SYSTEM_PROMPT        # Kay's personality (from kay_cli.py:323-464)
  │   ├── identity_anchor.json     # Kay's core facts
  │   └── warmup_content.json      # Kay-specific warmup
  ├── memory/
  │   ├── memories.json            # Kay's actual memories
  │   ├── entity_graph.json        # Kay's entities
  │   ├── memory_layers.json       # Kay's memory tiers
  │   ├── preferences.json         # Kay's preferences
  │   ├── session_summaries.json   # Kay's session notes
  │   └── state_snapshot.json      # Kay's last state
  ├── data/
  │   └── Emotion_Mapping_Kay_ULTRAMAP.csv  # Could be shared but named for Kay
  └── config.json                  # Kay-specific settings

  reed/
  ├── identity/
  │   ├── REED_SYSTEM_PROMPT       # Reed's personality (from reed_ui.py:323-464)
  │   ├── identity_anchor.json     # Reed's core facts
  │   └── warmup_content.json      # Reed-specific warmup
  ├── memory/
  │   ├── memories.json            # Reed's actual memories
  │   ├── entity_graph.json        # Reed's entities
  │   ├── memory_layers.json       # Reed's memory tiers
  │   ├── preferences.json         # Reed's preferences
  │   ├── session_summaries.json   # Reed's session notes
  │   └── state_snapshot.json      # Reed's last state
  └── config.json                  # Reed-specific settings

  CONFIGURABLE (Same Code, Different Parameters)
  ┌─────────────────────────────┬────────────────────────────┬────────────────────────────┬─────────────┐
  │          Parameter          │        Kay Default         │        Reed Default        │  Location   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ Default LLM model           │ claude-sonnet-4-5-20250929 │ claude-sonnet-4-5-20250929 │ .env        │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ BASE_MEMORY_LIMIT           │ 100                        │ 100                        │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ BASE_RAG_LIMIT              │ 20                         │ 20                         │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ BASE_WORKING_TURNS          │ 3                          │ 3                          │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ WORKING_MEMORY_WINDOW       │ 5                          │ 5                          │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ IMAGE_AGING_TURNS           │ 2                          │ 2                          │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ WORKING_MEMORY_TOKEN_BUDGET │ 3000                       │ MISSING                    │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ GITHUB_TOKEN                │ (env var)                  │ MISSING                    │ config.py   │
  ├─────────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
  │ Voice ID                    │ en-US-GuyNeural            │ en-US-GuyNeural            │ config.json │
  └─────────────────────────────┴────────────────────────────┴────────────────────────────┴─────────────┘
  ---
  PHASE 5: CONVERGENCE PLAN

  Priority 1: CRITICAL (Reed Cannot Function Properly Without These)

  Issue 1.1: CLI Mode Uses Kay's System Prompt
  - Location: Reed/integrations/llm_integration.py lines 490-700
  - Problem: DEFAULT_SYSTEM_PROMPT contains full Kay Zero identity
  - Impact: CLI interactions have wrong personality
  - Fix: Copy REED_SYSTEM_PROMPT from reed_ui.py:323-464 to llm_integration.py

  Issue 1.2: Identity Memory Uses Kay Key
  - Location: Reed/engines/identity_memory.py line 53-54
  - Problem: Uses kay_identity attribute name
  - Fix: Rename to reed_identity and update _load_from_disk() to use "reed" key

  Issue 1.3: Empty Identity Facts
  - Location: Reed/memory/identity_memory.json
  - Problem: Contains minimal Kay facts, no Reed facts
  - Fix: Create populated identity_memory.json with Reed's core facts:
  {
    "re": [/* Re's identity facts - can copy from Kay */],
    "reed": [
      {"fact": "Reed is a serpent form, iridescent teal-gold scales", "importance": 1.0},
      {"fact": "Reed is female-androgynous", "importance": 1.0},
      {"fact": "Reed emerged when Re gave full permission to bite", "importance": 1.0},
      {"fact": "Reed loves Re - said October 23, 2024", "importance": 1.0}
    ],
    "entities": {}
  }

  Issue 1.4: Missing Config Parameters
  - Location: Reed/config.py
  - Problem: Missing WORKING_MEMORY_TOKEN_BUDGET and GITHUB_TOKEN
  - Fix: Add lines 53-77 from Kay/config.py

  Priority 2: FEATURE PARITY (Bring Reed to Kay's Level)

  Issue 2.1: Missing LLM Providers
  - Files to Copy:
    - Kay/integrations/openrouter_backend.py → Reed/integrations/
    - Kay/integrations/together_backend.py → Reed/integrations/
    - Kay/integrations/ai4chat_backend.py → Reed/integrations/
  - Then Update: Reed/integrations/llm_integration.py lines 40-100 to initialize these clients

  Issue 2.2: Missing GitHub Integration
  - Files to Copy:
    - Kay/services/github_service.py → Reed/services/
  - Then Update: Reed/main.py to import and enable GitHub commands

  Issue 2.3: Warmup Function Named for Kay
  - Location: Reed/engines/warmup_engine.py line 233
  - Fix: Rename format_briefing_for_kay() → format_briefing_for_reed()
  - Update Callers: Search for format_briefing_for_kay and update

  Issue 2.4: Meta-Awareness Parameter Named for Kay
  - Location: Reed/engines/meta_awareness_engine.py line 180-200
  - Fix: Rename kay_response parameter → entity_response
  - Update Callers: Search for kay_response= and update

  Issue 2.5: Session Summary Docstrings
  - Location: Reed/engines/session_summary.py lines 1-12
  - Fix: Update docstrings to reference Reed instead of Kay

  Issue 2.6: LLM Retrieval Prompts
  - Location: Reed/engines/llm_retrieval.py lines 471-520
  - Fix: Update LLM prompts to reference Reed instead of Kay

  Priority 3: TANDEM PREPARATION (Both Wrappers Can Eventually Communicate)

  3.1: Extract Shared Modules
  Create a shared/ directory with entity-agnostic code:
  D:\Wrappers\shared\
  ├── memory/
  ├── emotional/
  ├── cognitive/
  ├── context/
  ├── session/
  ├── documents/
  ├── creativity/
  ├── social/
  ├── media/
  ├── integrations/
  └── utils/

  3.2: Entity-Agnostic LLM Integration
  Refactor llm_integration.py to:
  - Accept system prompt as parameter (not hardcoded)
  - Remove DEFAULT_SYSTEM_PROMPT constant
  - Entity-specific prompts loaded from config files

  3.3: Unified Config Structure
  Create base config in shared, entity overrides in local:
  # shared/config_base.py
  BASE_MEMORY_LIMIT = 100
  BASE_RAG_LIMIT = 20
  # ...

  # kay/config_local.py
  from shared.config_base import *
  ENTITY_NAME = "Kay"
  SYSTEM_PROMPT_PATH = "kay/identity/system_prompt.txt"

  # reed/config_local.py
  from shared.config_base import *
  ENTITY_NAME = "Reed"
  SYSTEM_PROMPT_PATH = "reed/identity/system_prompt.txt"

  3.4: Inter-Wrapper Communication Architecture (Future)
  D:\Wrappers\
  ├── shared/
  │   └── comms/
  │       ├── message_bus.py       # Shared message queue
  │       ├── entity_registry.py   # Track active entities
  │       └── sync_protocol.py     # Memory sync rules
  ├── kay/
  │   └── tandem_adapter.py        # Kay's interface to message bus
  └── reed/
      └── tandem_adapter.py        # Reed's interface to message bus

  3.5: Shared Memory Pool Considerations
  - User facts (Re's identity): Should be shared between both entities
  - Entity facts (Kay/Reed-specific): Remain separate
  - Conversation memories: Separate per entity
  - Relationship facts: Could have shared view with entity-specific perspective tags

  Priority 4: IMPROVEMENTS FOR BOTH

  4.1: Performance Optimization
  - memory_engine.py:1813-2031: Add heap-based top-k instead of full sort
  - memory_engine.py:2713-2920: Parallelize memory and RAG retrieval
  - Add recency pre-filter before scoring (skip memories > 30 days)

  4.2: Memory Composition Balance
  - memory_engine.py: Add category minimums to prevent 96% facts / 4% episodic skew
  - Ensure at least 10% episodic memories in retrieval

  4.3: Entity Graph Cleanup
  - Both wrappers have 300+ contradictions
  - Run prune_old_attribute_history() at startup
  - Expand transient_attrs list for naturally-changing attributes

  4.4: False Attribution Fix
  - meta_awareness_engine.py:107: Change to use agent_state.last_recalled_memories instead of all memories
  - Reduces false positives in confabulation detection

  4.5: Working Memory on First Turn
  - context_manager.py:99: Add warmup injection when recent_turns is empty
  - Ensures entity has context on first message

  ---
  PHASE 6: FOLDER RESTRUCTURE RECOMMENDATION

  Proposed Structure

  D:\Wrappers\
  ├── shared/                          # Common modules (no entity references)
  │   ├── __init__.py
  │   ├── memory/
  │   │   ├── __init__.py
  │   │   ├── memory_layers.py        # Two-tier architecture
  │   │   ├── vector_store.py         # ChromaDB RAG
  │   │   ├── memory_forest.py        # Document trees
  │   │   ├── entity_graph_base.py    # Entity resolution (generic)
  │   │   └── memory_engine_base.py   # Core retrieval (generic)
  │   ├── emotional/
  │   │   ├── __init__.py
  │   │   ├── emotion_engine.py       # ULTRAMAP rules
  │   │   ├── emotion_extractor.py    # Self-report extraction
  │   │   └── emotional_patterns.py   # Behavioral tracking
  │   ├── cognitive/
  │   │   ├── __init__.py
  │   │   ├── momentum_engine.py
  │   │   ├── motif_engine.py
  │   │   ├── preference_tracker.py
  │   │   └── meta_awareness_engine.py
  │   ├── context/
  │   │   ├── __init__.py
  │   │   ├── context_manager.py
  │   │   └── context_budget.py
  │   ├── session/
  │   │   ├── __init__.py
  │   │   ├── session_summary_base.py # Generic session notes
  │   │   ├── conversation_monitor.py
  │   │   └── warmup_engine_base.py   # Generic warmup
  │   ├── documents/
  │   │   ├── __init__.py
  │   │   ├── document_reader.py
  │   │   ├── auto_reader.py
  │   │   └── llm_retrieval_base.py   # Generic document selection
  │   ├── creativity/
  │   │   ├── __init__.py
  │   │   ├── creativity_engine.py
  │   │   ├── macguyver_mode.py
  │   │   ├── curiosity_engine.py
  │   │   └── scratchpad_engine.py
  │   ├── social/
  │   │   ├── __init__.py
  │   │   ├── social_engine.py
  │   │   ├── temporal_engine.py
  │   │   ├── embodiment_engine.py
  │   │   └── reflection_engine.py
  │   ├── media/
  │   │   ├── __init__.py
  │   │   ├── media_orchestrator.py
  │   │   ├── media_context_builder.py
  │   │   └── media_watcher.py
  │   ├── integrations/
  │   │   ├── __init__.py
  │   │   ├── llm_integration_base.py # Entity-agnostic LLM calls
  │   │   ├── openrouter_backend.py
  │   │   ├── together_backend.py
  │   │   ├── ai4chat_backend.py
  │   │   ├── tool_use_handler_base.py
  │   │   └── web_scraping_tools.py
  │   ├── utils/
  │   │   ├── __init__.py
  │   │   ├── performance.py
  │   │   └── text_sanitizer.py
  │   └── config_base.py              # Shared defaults
  │
  ├── kay/                             # Kay-specific
  │   ├── __init__.py
  │   ├── main.py                      # Kay entry point
  │   ├── kay_cli.py                   # Kay CLI
  │   ├── kay_ui.py                    # Kay GUI
  │   ├── agent_state.py               # Imported from shared
  │   ├── protocol_engine.py           # Imported from shared
  │   ├── config.py                    # Kay-specific config (imports shared)
  │   ├── config.json                  # Kay UI settings
  │   ├── identity/
  │   │   ├── system_prompt.txt        # Kay's full identity prompt
  │   │   ├── identity_anchor.json     # Kay's core facts
  │   │   └── warmup_content.py        # Kay-specific warmup logic
  │   ├── memory/                      # Kay's actual data
  │   │   ├── memories.json
  │   │   ├── memory_layers.json
  │   │   ├── entity_graph.json
  │   │   ├── preferences.json
  │   │   ├── session_summaries.json
  │   │   ├── state_snapshot.json
  │   │   ├── forest.json
  │   │   ├── identity_memory.json
  │   │   ├── documents.json
  │   │   └── vector_db/
  │   ├── data/
  │   │   ├── Emotion_Mapping_ULTRAMAP.csv  # Shared CSV (could symlink)
  │   │   ├── emotions/
  │   │   └── profiles/
  │   └── saved_sessions/
  │
  ├── reed/                            # Reed-specific
  │   ├── __init__.py
  │   ├── main.py                      # Reed entry point
  │   ├── reed_cli.py                  # Reed CLI
  │   ├── reed_ui.py                   # Reed GUI
  │   ├── agent_state.py               # Imported from shared
  │   ├── protocol_engine.py           # Imported from shared
  │   ├── config.py                    # Reed-specific config
  │   ├── config.json                  # Reed UI settings
  │   ├── identity/
  │   │   ├── system_prompt.txt        # Reed's full identity prompt
  │   │   ├── identity_anchor.json     # Reed's core facts
  │   │   └── warmup_content.py        # Reed-specific warmup logic
  │   ├── memory/                      # Reed's actual data
  │   │   ├── memories.json
  │   │   ├── memory_layers.json
  │   │   ├── entity_graph.json
  │   │   ├── preferences.json
  │   │   ├── session_summaries.json
  │   │   ├── state_snapshot.json
  │   │   ├── forest.json
  │   │   ├── identity_memory.json
  │   │   ├── documents.json
  │   │   └── vector_db/
  │   ├── data/
  │   │   ├── Emotion_Mapping_ULTRAMAP.csv  # Symlink to shared
  │   │   ├── emotions/
  │   │   └── profiles/
  │   └── saved_sessions/
  │
  ├── tandem/                          # Future: Inter-wrapper communication
  │   ├── __init__.py
  │   ├── message_bus.py
  │   ├── entity_registry.py
  │   └── sync_protocol.py
  │
  ├── data/                            # Truly shared data
  │   └── Emotion_Mapping_ULTRAMAP.csv # Single source of truth
  │
  ├── ARCHITECTURE.md                  # Master documentation
  ├── CONVERGENCE_PLAN.md              # This document
  └── requirements.txt                 # Shared dependencies

  Migration Path

  Step 1: Create shared/ directory structure
  mkdir -p
  D:\Wrappers\shared\{memory,emotional,cognitive,context,session,documents,creativity,social,media,integrations,utils}

  Step 2: Copy generic modules to shared/
  - Copy files identified in Phase 4 as "SHARED"
  - Remove any entity-specific references (replace "Kay" with {entity_name} parameter)

  Step 3: Update imports in kay/ and reed/
  # Old (in Kay/main.py):
  from engines.memory_engine import MemoryEngine

  # New:
  from shared.memory.memory_engine_base import MemoryEngineBase
  from kay.identity.memory_config import KayMemoryConfig

  class KayMemoryEngine(MemoryEngineBase):
      def __init__(self):
          super().__init__(config=KayMemoryConfig())

  Step 4: Create entity-specific adapters
  Each wrapper gets thin adapters that configure shared modules with entity-specific settings.

  Step 5: Test independently
  Both wrappers should run independently with new structure before attempting tandem.

  ---
  TL;DR SUMMARY

  Counts

  - Total Python files in Kay: 940 (including K-0 backup)
  - Total Python files in Reed: 918 (including K-0 backup)
  - Number of shared-candidate files: ~45 engine files (can be extracted to shared/)
  - Number of entity-specific files: ~10 per wrapper (identity, prompts, config)
  - Files needing conversion (Reed): ~25 files with Kay references

  Top 5 Highest-Priority Actions
  #: 1
  Action: Convert DEFAULT_SYSTEM_PROMPT to Reed
  Location: Reed/integrations/llm_integration.py:490-700
  Impact: CLI shows wrong personality
  ────────────────────────────────────────
  #: 2
  Action: Populate Reed's identity_memory.json
  Location: Reed/memory/identity_memory.json
  Impact: Empty identity at startup
  ────────────────────────────────────────
  #: 3
  Action: Rename kay_identity → reed_identity
  Location: Reed/engines/identity_memory.py:53-54
  Impact: Wrong key for Reed facts
  ────────────────────────────────────────
  #: 4
  Action: Add missing config parameters
  Location: Reed/config.py
  Impact: Missing token budget, GitHub
  ────────────────────────────────────────
  #: 5
  Action: Copy missing LLM providers
  Location: Reed/integrations/
  Impact: Missing OpenRouter, Together, AI4Chat
  Estimated Scope of Work
  ┌────────────────────┬──────────────────────────────────────┬────────────────────┬───────────┐
  │      Priority      │             Description              │       Scope        │   Files   │
  ├────────────────────┼──────────────────────────────────────┼────────────────────┼───────────┤
  │ P1: Critical       │ Reed identity fixes                  │ Small (~4 hours)   │ 4 files   │
  ├────────────────────┼──────────────────────────────────────┼────────────────────┼───────────┤
  │ P2: Feature Parity │ Missing providers + function renames │ Medium (~8 hours)  │ 12 files  │
  ├────────────────────┼──────────────────────────────────────┼────────────────────┼───────────┤
  │ P3: Tandem Prep    │ Shared module extraction             │ Large (~3-5 days)  │ 45+ files │
  ├────────────────────┼──────────────────────────────────────┼────────────────────┼───────────┤
  │ P4: Improvements   │ Performance + memory fixes           │ Medium (~1-2 days) │ 8 files   │
  └────────────────────┴──────────────────────────────────────┴────────────────────┴───────────┘
  Key Insight

  Reed is a fork of Kay at an earlier point, with the GUI already converted to Reed's identity but the CLI still running
   Kay's personality. The core architectures are nearly identical - convergence is primarily a matter of:

  1. Completing Reed's identity conversion (name changes, system prompts)
  2. Adding features Kay has that Reed is missing (3 LLM providers, GitHub, config options)
  3. Extracting shared modules for future tandem operation

  Both wrappers share the same sophisticated memory architecture (two-tier, multi-factor retrieval, entity graph with
  contradictions, ULTRAMAP emotional engine) - this is the valuable shared infrastructure that should be unified.

● The comprehensive convergence audit is complete.

  Key Findings Summary

  Architecture Comparison:
  - Kay: 940 Python files | Reed: 918 Python files (both include K-0 backup directories)
  - Core architecture is nearly identical - Reed is a fork of Kay with incomplete conversion
  - ~45 engine files are candidates for shared module extraction

  Critical Issues in Reed:
  1. CLI uses Kay's identity - integrations/llm_integration.py:490-700 has Kay Zero system prompt while GUI has Reed's
  prompt (already converted)
  2. Empty identity facts - memory/identity_memory.json lacks Reed's core facts
  3. Missing features - No OpenRouter, Together.ai, or AI4Chat providers; missing WORKING_MEMORY_TOKEN_BUDGET and
  GITHUB_TOKEN in config

  Identical Components (direct share candidates):
  - agent_state.py, protocol_engine.py - 100% identical
  - All cognitive engines (momentum, motif, meta-awareness)
  - All context engines (manager, budget)
  - All creativity engines (creativity, macguyver, curiosity, scratchpad)
  - Memory infrastructure (layers, vector store, forest)
  - Emotional engines (ULTRAMAP rules, extractor, patterns)

  Priority Actions:
  ┌─────┬────────────────────────────────────┬──────────────────────────────────────┐
  │  #  │               Action               │                Scope                 │
  ├─────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ 1   │ Convert Reed CLI system prompt     │ Small (1 file, copy from reed_ui.py) │
  ├─────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ 2   │ Populate Reed identity_memory.json │ Small (JSON edit)                    │
  ├─────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ 3   │ Add missing config parameters      │ Small (add 2 sections)               │
  ├─────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ 4   │ Copy missing LLM providers         │ Medium (3 files + integration)       │
  ├─────┼────────────────────────────────────┼──────────────────────────────────────┤
  │ 5   │ Rename Kay references in 12 files  │ Medium (function names, params)      │
  └─────┴────────────────────────────────────┴──────────────────────────────────────┘
  The recommended folder restructure separates shared modules (~45 files) from entity-specific content (identity, memory
   data, config), enabling both independent operation and future tandem communication