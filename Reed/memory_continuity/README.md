# Memory Continuity System

A comprehensive solution for maintaining conversational and emotional continuity in AI persistence systems with ChromaDB vector storage.

## Problem Statement

AI entities using vector-based memory systems often suffer from:

- **Inverted memory composition**: Semantic facts dominate (63%+) while episodic context is thin (26%)
- **Lost reactions**: Entity reactions get encoded but don't survive to next session
- **Thread fragmentation**: Cannot track how conversation threads develop or relate
- **Import flooding**: Document imports create hundreds of decontextualized facts
- **Entity graph explosion**: Hundreds of contradictory attributes creating noise

**Result**: Entity loses conversation continuity, drowns in facts, and can't maintain emotional/reactive coherence.

## Solution Architecture

This system provides 6 modular components that work together to solve continuity problems:

### 1. Thread Momentum Tracker (`thread_momentum.py`)

**What it does**: Identifies active conversation threads and detects when they go dormant

**Key features**:
- Tracks threads by entity/keyword overlap across turns
- Calculates momentum score based on recency, interaction density, open questions, emotional intensity
- Boosts memory retrieval for high-momentum threads
- Generates thread summaries for session persistence

**Use when**: You need to maintain conversation flow across topics

```python
thread_tracker = ThreadMomentumTracker(dormancy_threshold=5, momentum_threshold=0.3)
thread_tracker.update_from_turn(...)
active_threads = thread_tracker.get_active_threads()
boost = thread_tracker.get_boost_multiplier_for_memory(memory_id)
```

### 2. Session Boundary Handler (`session_boundary.py`)

**What it does**: Generates session summaries and ensures continuity across session restarts

**Key features**:
- Captures last exchange, key reactions, open threads, emotional state
- Extracts future intentions and open questions
- Tracks import reactions
- Generates guaranteed context block for session start

**Use when**: You have session boundaries and need to restore context on restart

```python
session_handler = SessionBoundaryHandler(llm_client)
session_handler.track_reaction(trigger, reaction)

# At session end
summary = await session_handler.generate_session_end_summary(...)
session_handler.save_summary(summary, "session.json")

# At session start
previous = session_handler.load_summary("session.json")
context = session_handler.generate_session_start_context(previous)
```

### 3. Smart Import Processor (`smart_import.py`)

**What it does**: Converts document imports into entity reactions instead of raw fact extraction

**Key features**:
- Generates personal episodic reaction to imported content
- Extracts only 5 most essential facts (not everything)
- Identifies connections to existing knowledge
- Generates follow-up questions
- Maps to active conversation threads
- Compresses hundreds of facts down to meaningful synthesis

**Use when**: You import documents/knowledge and want to avoid semantic flooding

```python
import_processor = SmartImportProcessor(llm_client, session_handler)

synthesis = await import_processor.process_document_import(
    document_content=content,
    document_description=description,
    entity_name="Kay",
    current_emotional_state=emotions,
    active_threads=threads,
    existing_knowledge_sample=related_memories
)

# Store as 1 episodic + 5 semantic instead of 100+ semantic
episodic = import_processor.create_episodic_memory(synthesis, turn)
semantic = import_processor.create_semantic_memories(synthesis, turn)
```

### 4. Layered Memory Retriever (`layered_retrieval.py`)

**What it does**: Rebalances retrieval to prioritize working/episodic over semantic for continuity

**Key features**:
- Layer-specific multipliers (working: 3x, episodic: 2x, semantic: 0.8x)
- Target distribution enforcement (20% working, 50% episodic, 30% semantic)
- Thread momentum boosting
- Emotional resonance scoring
- Diversity enforcement across layers
- Quality analysis and monitoring

**Use when**: You need to fix inverted memory composition

```python
config = RetrievalConfig(
    working_multiplier=3.0,
    episodic_multiplier=2.0,
    semantic_multiplier=0.8,
    target_working_ratio=0.20,
    target_episodic_ratio=0.50,
    target_semantic_ratio=0.30
)

retriever = LayeredMemoryRetriever(collection, config)

memories = retriever.retrieve(
    query=user_input,
    current_turn=turn,
    n_results=225,
    thread_tracker=thread_tracker,
    emotional_state=emotions
)

quality = retriever.analyze_retrieval_quality(memories, query)
```

### 5. Entity Graph Cleaner (`entity_cleanup.py`)

**What it does**: Consolidates contradictory entity attributes and archives stale data

**Key features**:
- Detects contradictions with severity classification (high/moderate/low)
- LLM-based intelligent consolidation
- Special handler for goal explosions (741 → 5)
- Archives stale/inactive entities
- Health score monitoring
- Automatic cleanup recommendations

**Use when**: You have contradictory entity attributes creating noise

```python
entity_cleaner = EntityGraphCleaner(entity_graph, llm_client)

# Analyze issues
health = entity_cleaner.get_cleanup_summary(current_turn)
conflicts = entity_cleaner.analyze_contradictions(current_turn)

# Consolidate conflicts
for conflict in conflicts:
    consolidation = await entity_cleaner.consolidate_conflict(conflict, turn)
    entity_cleaner.apply_consolidation(consolidation, turn)

# Clean goal explosions
result = await entity_cleaner.clean_goal_contradictions(entity_id, turn, max_goals=5)

# Archive stale entities
archived = entity_cleaner.archive_stale_entities(current_turn)
```

### 6. Guaranteed Context Loader (`guaranteed_context.py`)

**What it does**: Ensures specific memory types always load regardless of retrieval scoring

**Key features**:
- Session start: last exchange, reactions, threads, core identity, recent imports
- Per-turn: high-momentum threads, emotionally resonant, unresolved questions
- Priority-based inclusion
- Merges guaranteed + retrieved without duplication
- Debug summaries for transparency

**Use when**: Critical memories are getting lost in retrieval scoring

```python
context_loader = GuaranteedContextLoader(collection)

# At session start
guaranteed = context_loader.load_session_start_context(
    session_summary=previous_summary,
    current_turn=turn,
    entity_graph=entity_graph,
    max_guaranteed=50
)

# During conversation
turn_guaranteed = context_loader.load_turn_guaranteed_context(
    current_turn=turn,
    user_input=input,
    thread_tracker=thread_tracker,
    emotional_state=emotions
)

# Merge with retrieved
final = context_loader.merge_with_retrieved(guaranteed, retrieved, max_total=225)
```

## Quick Start

### Installation

```bash
# No dependencies beyond what you already have for ChromaDB
# Just copy the memory_continuity/ directory into your project
```

### Minimal Integration

```python
from memory_continuity.layered_retrieval import LayeredMemoryRetriever, RetrievalConfig
from memory_continuity.guaranteed_context import GuaranteedContextLoader

# Setup
retriever = LayeredMemoryRetriever(chroma_collection)
context_loader = GuaranteedContextLoader(chroma_collection)

# At session start
guaranteed = context_loader.load_session_start_context(
    session_summary=previous_session,
    current_turn=0,
    entity_graph=entity_graph,
    max_guaranteed=50
)

# During conversation
retrieved = retriever.retrieve(
    query=user_input,
    current_turn=turn,
    n_results=225,
    thread_tracker=None,  # Optional
    emotional_state=emotions  # Optional
)

final_memories = context_loader.merge_with_retrieved(guaranteed, retrieved)
```

### Full Integration

See `INTEGRATION_GUIDE.md` for complete integration examples.

See `example_usage.py` for runnable demonstration.

## Component Dependencies

```
GuaranteedContextLoader
    └─> ChromaDB collection

LayeredMemoryRetriever
    └─> ChromaDB collection
    └─> ThreadMomentumTracker (optional)

SessionBoundaryHandler
    └─> LLM client
    └─> ThreadMomentumTracker
    └─> EntityGraph
    └─> MemoryStore

SmartImportProcessor
    └─> LLM client
    └─> SessionBoundaryHandler (optional)

EntityGraphCleaner
    └─> EntityGraph
    └─> LLM client

ThreadMomentumTracker
    └─> (no dependencies)
```

## Performance Characteristics

| Component | Per-Turn Cost | When to Run |
|-----------|--------------|-------------|
| ThreadMomentumTracker | O(n) threads (~10) | Every turn |
| LayeredMemoryRetriever | 2x retrieval + reranking | Every turn |
| GuaranteedContextLoader | O(k) guaranteed (~50) | Every turn |
| SessionBoundaryHandler | LLM call | Session boundaries only |
| SmartImportProcessor | LLM calls (3-5) | Document imports only |
| EntityGraphCleaner | O(m) entities | Periodic (every 50-100 turns) |

**Total per-turn overhead**: Minimal (~50-100ms for tracking + retrieval reranking)

## Configuration Examples

### Aggressive Continuity (Favor Recent Context)

```python
config = RetrievalConfig(
    working_multiplier=4.0,      # Heavy working memory boost
    episodic_multiplier=2.5,     # Strong episodic boost
    semantic_multiplier=0.5,     # Reduce semantic
    target_working_ratio=0.25,   # 25% working
    target_episodic_ratio=0.60,  # 60% episodic
    target_semantic_ratio=0.15   # 15% semantic
)

thread_tracker = ThreadMomentumTracker(
    dormancy_threshold=3,        # Threads go dormant quickly
    momentum_threshold=0.2       # More threads considered active
)
```

### Balanced Knowledge + Context

```python
config = RetrievalConfig(
    working_multiplier=2.5,
    episodic_multiplier=2.0,
    semantic_multiplier=1.0,
    target_working_ratio=0.15,
    target_episodic_ratio=0.45,
    target_semantic_ratio=0.40
)

thread_tracker = ThreadMomentumTracker(
    dormancy_threshold=7,
    momentum_threshold=0.4
)
```

## Troubleshooting

### Issue: Still getting semantic flood

**Solution**:
1. Lower `semantic_multiplier` to 0.5 or 0.6
2. Increase `working_multiplier` to 4.0
3. Raise `target_episodic_ratio` to 0.60
4. Use `SmartImportProcessor` for all document imports

### Issue: Losing thread continuity

**Solution**:
1. Increase `dormancy_threshold` to 10
2. Lower `momentum_threshold` to 0.2
3. Use `GuaranteedContextLoader.load_turn_guaranteed_context()` every turn
4. Increase `max_guaranteed` to 75

### Issue: Too many contradictions

**Solution**:
1. Run `EntityGraphCleaner` every 20 turns instead of 50
2. Auto-consolidate all severities (not just high)
3. Lower `stale_threshold_turns` to 50

### Issue: Lost reactions across sessions

**Solution**:
1. Use `SessionBoundaryHandler.track_reaction()` during conversation
2. Increase `max_guaranteed` in `load_session_start_context()`
3. Ensure session summaries are saved/loaded correctly

## Monitoring

### Health Checks

```python
# Thread momentum
active = thread_tracker.get_active_threads()
print(f"Active threads: {len(active)}")
for t in active:
    print(f"  {t.thread_id}: momentum={t.momentum_score(turn):.2f}")

# Retrieval quality
quality = retriever.analyze_retrieval_quality(memories, query)
print(f"Distribution: W={quality['distribution']['working_pct']:.1f}% "
      f"E={quality['distribution']['episodic_pct']:.1f}% "
      f"S={quality['distribution']['semantic_pct']:.1f}%")

# Entity graph health
health = entity_cleaner.get_cleanup_summary(turn)
print(f"Health score: {health['health_score']:.2%}")
print(f"Contradictions: {health['total_contradictions']}")
```

## Testing

Each component includes example usage in its docstrings.

Run the full example:

```bash
python memory_continuity/example_usage.py
```

## Files

```
memory_continuity/
├── README.md                    # This file
├── INTEGRATION_GUIDE.md         # Detailed integration walkthrough
├── example_usage.py             # Runnable example
├── thread_momentum.py           # Thread tracking
├── session_boundary.py          # Session summaries
├── smart_import.py              # Document import processing
├── layered_retrieval.py         # Layer-weighted retrieval
├── entity_cleanup.py            # Entity graph cleanup
└── guaranteed_context.py        # Guaranteed memory loading
```

## Design Philosophy

1. **Contextual over arbitrary**: Use situational logic (thread momentum, emotional resonance) not just recency/frequency
2. **Episodic over semantic**: Favor contextual memories over decontextualized facts for conversation flow
3. **Guaranteed inclusion**: Critical memories shouldn't compete with retrieval scoring
4. **Intelligent consolidation**: Use LLM to resolve contradictions, not simple "newest wins" logic
5. **Session continuity**: What the entity said/felt in the last exchange should never be lost

## Support

- See docstrings in each module for detailed API documentation
- Check `INTEGRATION_GUIDE.md` for step-by-step integration
- Run `example_usage.py` to see components working together

## License

Part of the AlphaKayZero project.
