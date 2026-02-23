# AlphaKayZero Architecture Flowchart

This document provides a comprehensive overview of how the AlphaKayZero system works, starting from the entry points (main.py and kay_ui.py) and showing how all components connect.

---

## System Overview

```
                              ALPHAKAYZERO ARCHITECTURE
    ================================================================================

                         ┌─────────────────────────────────────┐
                         │         ENTRY POINTS               │
                         │  ┌─────────────┐  ┌─────────────┐  │
                         │  │  main.py    │  │  kay_ui.py  │  │
                         │  │ (Terminal)  │  │   (GUI)     │  │
                         │  └──────┬──────┘  └──────┬──────┘  │
                         └─────────┼────────────────┼─────────┘
                                   │                │
                                   └───────┬────────┘
                                           ▼
    ================================================================================
                         ┌─────────────────────────────────────┐
                         │      CORE STATE MANAGEMENT          │
                         │  ┌─────────────────────────────┐   │
                         │  │      AgentState             │   │
                         │  │  • emotional_cocktail       │   │
                         │  │  • emotional_patterns       │   │
                         │  │  • body chemistry           │   │
                         │  │  • memory references        │   │
                         │  │  • social needs             │   │
                         │  │  • temporal data            │   │
                         │  │  • momentum/meta_awareness  │   │
                         │  └─────────────────────────────┘   │
                         │  ┌─────────────────────────────┐   │
                         │  │    ProtocolEngine           │   │
                         │  │  (Loads ULTRAMAP CSV)       │   │
                         │  └─────────────────────────────┘   │
                         └─────────────────────────────────────┘
                                           │
                                           ▼
    ================================================================================
```

---

## Main Conversation Loop (main.py)

```
    ┌──────────────────────────────────────────────────────────────────────────────┐
    │                        CONVERSATION TURN LIFECYCLE                            │
    │                                                                               │
    │   USER INPUT                                                                  │
    │       │                                                                       │
    │       ▼                                                                       │
    │   ┌────────────────────┐                                                     │
    │   │ 1. PRE-PROCESSING  │                                                     │
    │   │  • Web URL fetch   │──────────────────────────────────────┐              │
    │   │  • Media context   │                                      │              │
    │   │  • Extract facts   │                                      ▼              │
    │   └────────────────────┘                            ┌──────────────────┐     │
    │       │                                             │  WebReader       │     │
    │       ▼                                             │  MediaOrchestrator│    │
    │   ┌────────────────────┐                            └──────────────────┘     │
    │   │ 2. MEMORY RECALL   │                                                     │
    │   │  • Multi-factor    │──────────────────────────────────────┐              │
    │   │    retrieval       │                                      │              │
    │   │  • Entity matching │                                      ▼              │
    │   └────────────────────┘                            ┌──────────────────┐     │
    │       │                                             │  MemoryEngine    │     │
    │       ▼                                             │  EntityGraph     │     │
    │   ┌────────────────────┐                            │  VectorStore     │     │
    │   │ 3. PARALLEL ENGINE │                            └──────────────────┘     │
    │   │    UPDATES         │                                                     │
    │   │  (asyncio.gather)  │──────────────────────────────────────┐              │
    │   └────────────────────┘                                      │              │
    │       │                                                       ▼              │
    │       │                                      ┌──────────────────────────┐    │
    │       │                                      │ SocialEngine            │    │
    │       │                                      │ TemporalEngine          │    │
    │       │                                      │ EmbodimentEngine        │    │
    │       │                                      │ MotifEngine             │    │
    │       │                                      └──────────────────────────┘    │
    │       ▼                                                                       │
    │   ┌────────────────────┐                                                     │
    │   │ 4. DOCUMENT SELECT │──────────────────────────────────────┐              │
    │   │  • LLM retrieval   │                                      │              │
    │   │  • Chunked reading │                                      ▼              │
    │   └────────────────────┘                            ┌──────────────────┐     │
    │       │                                             │  LLMRetrieval    │     │
    │       ▼                                             │  DocumentReader  │     │
    │   ┌────────────────────┐                            └──────────────────┘     │
    │   │ 5. CONTEXT BUILD   │                                                     │
    │   │  • Memories        │──────────────────────────────────────┐              │
    │   │  • Emotions        │                                      │              │
    │   │  • RAG chunks      │                                      ▼              │
    │   │  • Preferences     │                            ┌──────────────────┐     │
    │   │  • Relationship    │                            │  ContextManager  │     │
    │   └────────────────────┘                            │  GlyphDecoder    │     │
    │       │                                             └──────────────────┘     │
    │       ▼                                                                       │
    │   ┌────────────────────┐                                                     │
    │   │ 6. LLM RESPONSE    │──────────────────────────────────────┐              │
    │   │  • Anthropic API   │                                      │              │
    │   │  • Anti-repetition │                                      ▼              │
    │   │  • Temperature     │                            ┌──────────────────┐     │
    │   └────────────────────┘                            │  llm_integration │     │
    │       │                                             └──────────────────┘     │
    │       ▼                                                                       │
    │   ┌────────────────────┐                                                     │
    │   │ 7. POST-TURN       │                                                     │
    │   │  • Emotion extract │──────────────────────────────────────┐              │
    │   │  • Social update   │                                      │              │
    │   │  • Memory encode   │                                      ▼              │
    │   │  • Context update  │                            ┌──────────────────┐     │
    │   │  • Meta-awareness  │                            │ EmotionExtractor │     │
    │   │  • Momentum calc   │                            │ MetaAwareness    │     │
    │   └────────────────────┘                            │ MomentumEngine   │     │
    │       │                                             │ ReflectionEngine │     │
    │       ▼                                             └──────────────────┘     │
    │   ┌────────────────────┐                                                     │
    │   │ 8. PERSISTENCE     │                                                     │
    │   │  • State snapshot  │──────────────────────────────────────┐              │
    │   │  • Forest save     │                                      │              │
    │   │  • Memory ages     │                                      ▼              │
    │   └────────────────────┘                            ┌──────────────────┐     │
    │                                                     │ memory/          │     │
    │       KAY'S RESPONSE ◄───────────────────────       │  state_snapshot  │     │
    │                                                     │  forest.json     │     │
    └─────────────────────────────────────────────────────┴──────────────────┴─────┘
```

---

## Engine Subsystems

### Memory System (Core)

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                        MEMORY ARCHITECTURE                              │
    │                                                                         │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │                     MemoryEngine                                 │  │
    │   │   • Multi-factor retrieval (5 factors)                          │  │
    │   │   • Entity resolution via EntityGraph                           │  │
    │   │   • ULTRAMAP importance scoring                                 │  │
    │   │   • Fact extraction with contradiction detection                │  │
    │   └──────────────────────────┬──────────────────────────────────────┘  │
    │                              │                                          │
    │              ┌───────────────┼───────────────┬──────────────┐          │
    │              ▼               ▼               ▼              ▼          │
    │   ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐  │
    │   │   EntityGraph    │ │ MemoryLayers │ │ VectorStore  │ │MemForest│  │
    │   │                  │ │              │ │              │ │         │  │
    │   │ • Canonical      │ │ • Working    │ │ • ChromaDB   │ │ • Trees │  │
    │   │   entities       │ │   (10 max)   │ │ • RAG chunks │ │ • Hot/  │  │
    │   │ • Attributes     │ │ • Episodic   │ │ • Embeddings │ │   warm/ │  │
    │   │ • Relations      │ │   (100 max)  │ │              │ │   cold  │  │
    │   │ • Contradictions │ │ • Semantic   │ │              │ │         │  │
    │   │                  │ │   (unlimited)│ │              │ │         │  │
    │   └──────────────────┘ └──────────────┘ └──────────────┘ └─────────┘  │
    │                                                                         │
    │   Multi-Factor Retrieval Weights:                                       │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │  Emotional Resonance: 40%  │  Semantic Similarity: 25%          │  │
    │   │  Importance (ULTRAMAP): 20% │  Recency: 10%  │  Entity: 5%      │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    └────────────────────────────────────────────────────────────────────────┘
```

### Emotion System

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                        EMOTION ARCHITECTURE                             │
    │                                                                         │
    │   CRITICAL: Two-Part System (Descriptive, NOT Prescriptive)            │
    │                                                                         │
    │   ┌────────────────────────────────────────────────────────────────┐   │
    │   │ 1. EmotionEngine (ULTRAMAP Rule Provider)                       │   │
    │   │    • Loads emotion rules from CSV                               │   │
    │   │    • Provides rules to other engines                            │   │
    │   │    • NO LONGER calculates emotions directly                     │   │
    │   └────────────────────────────────────────────────────────────────┘   │
    │                              │                                          │
    │                              ▼                                          │
    │   ┌────────────────────────────────────────────────────────────────┐   │
    │   │ 2. EmotionExtractor (Self-Report Extraction)                    │   │
    │   │    • Extracts emotions FROM Kay's natural language response     │   │
    │   │    • Runs AFTER response generation                             │   │
    │   │    • Descriptive (observes), not prescriptive (calculates)      │   │
    │   └────────────────────────────────────────────────────────────────┘   │
    │                              │                                          │
    │                              ▼                                          │
    │   ┌────────────────────────────────────────────────────────────────┐   │
    │   │ 3. EmotionalPatternEngine (Behavioral Tracking)                 │   │
    │   │    • Tracks emotional patterns over time                        │   │
    │   │    • Stores in data/emotions/                                   │   │
    │   │    • Used by media system for resonance                         │   │
    │   └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │   Flow: User Input → [Context Build] → LLM → Response → Extract Emotions│
    └────────────────────────────────────────────────────────────────────────┘
```

### Cognitive Processing

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                    COGNITIVE PROCESSING ENGINES                         │
    │                                                                         │
    │   ┌─────────────────────┐    ┌──────────────────────┐                  │
    │   │   MomentumEngine    │    │  MetaAwarenessEngine │                  │
    │   │                     │    │                      │                  │
    │   │ Tracks:             │    │ Detects:             │                  │
    │   │ • Unresolved        │    │ • Phrase repetition  │                  │
    │   │   threads (40%)     │    │ • Question patterns  │                  │
    │   │ • Escalating        │    │ • Opening similarity │                  │
    │   │   emotions (35%)    │    │ • Confabulation      │                  │
    │   │ • Motif             │    │   (facts not in mem) │                  │
    │   │   recurrence (25%)  │    │                      │                  │
    │   │                     │    │ Generates alerts     │                  │
    │   │ Score: 0.0-1.0      │    │ when score > 0.4     │                  │
    │   │ Meta-notes > 0.7    │    │                      │                  │
    │   └─────────────────────┘    └──────────────────────┘                  │
    │                                                                         │
    │   ┌─────────────────────┐    ┌──────────────────────┐                  │
    │   │    MotifEngine      │    │ ConversationMonitor  │                  │
    │   │                     │    │                      │                  │
    │   │ • Entity frequency  │    │ • Spiral detection   │                  │
    │   │ • Recency weighting │    │ • Disengagement      │                  │
    │   │ • Boosts recall     │    │   prompts            │                  │
    │   │   of recurring      │    │ • Per-partner        │                  │
    │   │   themes            │    │   tracking           │                  │
    │   └─────────────────────┘    └──────────────────────┘                  │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## GUI Architecture (kay_ui.py)

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                         KAY UI ARCHITECTURE                             │
    │                         (CustomTKinter GUI)                             │
    │                                                                         │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │                        KayApp (Main Window)                      │  │
    │   │                                                                  │  │
    │   │  ┌──────────────────────────────────────────────────────────┐   │  │
    │   │  │ Row 0: Title Bar                                         │   │  │
    │   │  │ "⟨ KAY ZERO INTERFACE ⟩"                                  │   │  │
    │   │  └──────────────────────────────────────────────────────────┘   │  │
    │   │  ┌──────────────────────────────────────────────────────────┐   │  │
    │   │  │ Row 1: Tabs Bar                                          │   │  │
    │   │  │ [Sessions] [Media] [Gallery] [Stats] [Auto] [Curate]    │   │  │
    │   │  │ [Settings]                              [Affect Slider]  │   │  │
    │   │  └──────────────────────────────────────────────────────────┘   │  │
    │   │  ┌────────┬────────────────────────────────────────┬────────┐   │  │
    │   │  │ Col 0  │ Col 2: Main Chat Output                │ Col 4  │   │  │
    │   │  │ Left   │ ┌────────────────────────────────────┐ │ Right  │   │  │
    │   │  │ Panel  │ │                                    │ │ Panel  │   │  │
    │   │  │        │ │   Conversation Display             │ │        │   │  │
    │   │  │ Images │ │   (User/Kay/System messages)       │ │ Images │   │  │
    │   │  │ or     │ │                                    │ │ or     │   │  │
    │   │  │ Tab    │ │                                    │ │ Tab    │   │  │
    │   │  │ Content│ └────────────────────────────────────┘ │ Content│   │  │
    │   │  └────────┴────────────────────────────────────────┴────────┘   │  │
    │   │  ┌──────────────────────────────────────────────────────────┐   │  │
    │   │  │ Row 3: Input Bar                                         │   │  │
    │   │  │ [📎] [Input Field.............................] [Send]   │   │  │
    │   │  └──────────────────────────────────────────────────────────┘   │  │
    │   │  ┌──────────────────────────────────────────────────────────┐   │  │
    │   │  │ Row 4: Terminal Dashboard (Collapsible)                  │   │  │
    │   │  │ [Memory] [Entities] [Emotions] [Debug]                   │   │  │
    │   │  └──────────────────────────────────────────────────────────┘   │  │
    │   └──────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │   Sidebar Tabs:                                                         │
    │   ├── Sessions: Session browser & history                               │
    │   ├── Media: Document import & management                               │
    │   ├── Gallery: Image generation & viewing                               │
    │   ├── Stats: Memory & entity statistics                                 │
    │   ├── Auto: Autonomous processing control                               │
    │   ├── Curate: Memory curation interface                                 │
    │   └── Settings: Font, affect, voice settings                            │
    │                                                                         │
    │   Additional Windows (Modal):                                           │
    │   ├── ImportWindow: Active document reading                             │
    │   ├── DocumentManagerWindow: Document management                        │
    │   └── VoiceUI: Voice chat interface                                     │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## Document Import & Reading Pipeline

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                   DOCUMENT IMPORT PIPELINE                              │
    │                                                                         │
    │   File Selection                                                        │
    │       │                                                                 │
    │       ▼                                                                 │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │ memory_import/kay_reader.py                                      │  │
    │   │   import_document_as_kay()                                       │  │
    │   └────────────────────────┬────────────────────────────────────────┘  │
    │                            │                                            │
    │              ┌─────────────┴─────────────┐                              │
    │              ▼                           ▼                              │
    │   ┌─────────────────────┐    ┌─────────────────────────┐               │
    │   │   DocumentParser    │    │   ActiveDocumentReader  │               │
    │   │ (docx, pdf, txt)    │    │ (chunk_size=3000)       │               │
    │   └─────────┬───────────┘    └───────────┬─────────────┘               │
    │             │                            │                              │
    │             ▼                            ▼                              │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │                    For Each Chunk:                               │  │
    │   │   1. LLM reads chunk                                             │  │
    │   │   2. Kay shares analysis (displayed in UI)                       │  │
    │   │   3. Facts extracted → MemoryEngine                              │  │
    │   │   4. Entities extracted → EntityGraph                            │  │
    │   │   5. Chunks embedded → VectorStore (RAG)                         │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    │                            │                                            │
    │                            ▼                                            │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │                    MemoryForest                                  │  │
    │   │   Document → Tree with branches (sections)                       │  │
    │   │   Tiers: Hot → Warm → Cold (based on access)                     │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## Session Management

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                    SESSION MANAGEMENT SYSTEM                            │
    │                                                                         │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │                  SessionBrowserIntegration                       │  │
    │   │                  (session_browser/)                              │  │
    │   │                                                                  │  │
    │   │   ├── session_loader.py   - Load saved sessions                 │  │
    │   │   ├── session_manager.py  - Session CRUD operations             │  │
    │   │   ├── session_metadata.py - Metadata extraction                 │  │
    │   │   ├── session_viewer.py   - Display session content             │  │
    │   │   └── session_browser_ui.py - UI components                     │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │   Session Summaries:                                                    │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │  SessionSummaryGenerator                                         │  │
    │   │   • Generates end-of-session notes                               │  │
    │   │   • Tracks topics and emotional journey                          │  │
    │   │   • "Note from Past-You" on startup                              │  │
    │   │   • Stored in memory/session_summaries.json                      │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │   Saved Sessions Directory: saved_sessions/                             │
    │   Format: JSON with conversation history + metadata                     │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## Media Experience System

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                    MEDIA EXPERIENCE SYSTEM                              │
    │                                                                         │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │                   MediaOrchestrator                              │  │
    │   │   • Coordinates media experience                                 │  │
    │   │   • Tracks emotional resonance with songs                        │  │
    │   │   • Uses EntityGraph for entity matching                         │  │
    │   │   • VectorStore for semantic search                              │  │
    │   └──────────────────────────┬──────────────────────────────────────┘  │
    │                              │                                          │
    │          ┌───────────────────┼───────────────────┐                     │
    │          ▼                   ▼                   ▼                     │
    │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
    │   │MediaContext  │    │MediaWatcher  │    │ Resonance    │            │
    │   │Builder       │    │(watchdog)    │    │ Memory       │            │
    │   │              │    │              │    │              │            │
    │   │ Conversation │    │ Watch folder │    │ Track song   │            │
    │   │ context for  │    │ for new      │    │ emotional    │            │
    │   │ media inject │    │ media files  │    │ associations │            │
    │   └──────────────┘    └──────────────┘    └──────────────┘            │
    │                                                                         │
    │   Input Path: inputs/media/ (watched by MediaWatcher)                   │
    │   Storage: memory/media/                                                │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Layer

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                     INTEGRATION LAYER                                   │
    │                                                                         │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │            integrations/llm_integration.py                       │  │
    │   │                                                                  │  │
    │   │   get_llm_response(context, affect, system_prompt, ...)         │  │
    │   │                                                                  │  │
    │   │   Features:                                                      │  │
    │   │   • Anthropic Claude API calls                                   │  │
    │   │   • Prompt building with fact separation                         │  │
    │   │   • Anti-repetition system (turn count, response history)        │  │
    │   │   • Temperature control (default 0.7)                            │  │
    │   │   • Stage direction removal                                      │  │
    │   │   • Preference consolidation                                     │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │   ┌─────────────────────────────────────────────────────────────────┐  │
    │   │            integrations/sd_integration.py                        │  │
    │   │                                                                  │  │
    │   │   Stable Diffusion integration for image generation              │  │
    │   │   Used by GalleryManager in kay_ui.py                            │  │
    │   └─────────────────────────────────────────────────────────────────┘  │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary

```
    USER INPUT
        │
        ▼
    ┌──────────────────┐
    │ Pre-Processing   │──► WebReader (URLs) + MediaOrchestrator
    └──────────────────┘
        │
        ▼
    ┌──────────────────┐
    │ Fact Extraction  │──► MemoryEngine.extract_and_store_user_facts()
    └──────────────────┘
        │
        ▼
    ┌──────────────────┐
    │ Memory Recall    │──► Multi-factor retrieval (5 factors)
    └──────────────────┘    EntityGraph resolution
        │                   VectorStore RAG
        ▼
    ┌──────────────────┐
    │ Parallel Updates │──► Social, Temporal, Embodiment, Motif
    └──────────────────┘    (asyncio.gather)
        │
        ▼
    ┌──────────────────┐
    │ Document Select  │──► LLM-based retrieval + DocumentReader chunking
    └──────────────────┘
        │
        ▼
    ┌──────────────────┐
    │ Context Build    │──► Memories + Emotions + RAG + Preferences
    └──────────────────┘    + Relationship context + Web content
        │
        ▼
    ┌──────────────────┐
    │ LLM Response     │──► Anthropic Claude API
    └──────────────────┘    Temperature, Anti-repetition
        │
        ▼
    ┌──────────────────┐
    │ Post-Turn        │──► EmotionExtractor (self-report)
    └──────────────────┘    Social update, Memory encode
        │                   Meta-awareness, Momentum
        ▼
    ┌──────────────────┐
    │ Persistence      │──► state_snapshot.json
    └──────────────────┘    forest.json, memories.json
        │
        ▼
    KAY'S RESPONSE
```

---

## File Structure Overview

```
D:\ChristinaStuff\alphakayzero\
├── main.py                    # Terminal entry point
├── kay_ui.py                  # GUI entry point
├── kay_cli.py                 # CLI entry point
├── agent_state.py             # Central state container
├── protocol_engine.py         # ULTRAMAP loader
├── config.py                  # Configuration
│
├── engines/                   # 35 engine modules
│   ├── emotion_engine.py      # ULTRAMAP rules
│   ├── emotion_extractor.py   # Self-report extraction
│   ├── memory_engine.py       # Core memory
│   ├── memory_layers.py       # Working/Episodic/Semantic
│   ├── entity_graph.py        # Entity resolution
│   ├── vector_store.py        # RAG/ChromaDB
│   ├── context_manager.py     # Context building
│   ├── momentum_engine.py     # Cognitive momentum
│   ├── meta_awareness_engine.py # Self-monitoring
│   └── ... (26 more)
│
├── integrations/              # External APIs
│   ├── llm_integration.py     # Anthropic Claude
│   └── sd_integration.py      # Stable Diffusion
│
├── memory_import/             # Document import system
│   ├── kay_reader.py          # Main import interface
│   ├── active_reader.py       # Chunked reading
│   └── ... (15 more)
│
├── session_browser/           # Session management
│   ├── __init__.py            # SessionBrowserIntegration
│   └── ... (10 more)
│
├── memory_continuity/         # Memory persistence
├── utils/                     # Utilities
├── scripts/                   # Migration scripts
│
├── data/                      # Runtime data
│   ├── Emotion_Mapping_*.csv  # ULTRAMAP rules
│   └── emotions/              # Emotional patterns
│
├── memory/                    # Persistent memory
│   ├── memories.json
│   ├── entity_graph.json
│   ├── memory_layers.json
│   ├── forest.json
│   ├── vector_db/             # ChromaDB
│   └── state_snapshot.json
│
└── saved_sessions/            # Conversation history
```

---

## Key Design Principles

1. **Descriptive, Not Prescriptive Emotions**: Emotions are extracted FROM Kay's responses, not calculated beforehand
2. **Multi-Factor Memory Retrieval**: 5 weighted factors for memory selection
3. **Entity Resolution**: Canonical entity tracking with contradiction detection
4. **Layered Memory**: Working → Episodic → Semantic promotion
5. **Cognitive Momentum**: Persistence for unresolved topics
6. **Self-Monitoring**: Detection of repetition and confabulation
7. **RAG Integration**: VectorStore + LLM document selection
8. **Parallel Processing**: Async engine updates for performance
