# Memory Continuity System - Integration Guide

This guide shows how to integrate the memory continuity components into your AI persistence wrapper.

## Architecture Overview

The system consists of 6 interconnected components that work together to maintain conversation continuity:

1. **ThreadMomentumTracker** - Identifies active conversation threads and boosts related memories
2. **SessionBoundaryHandler** - Generates session summaries and ensures session-to-session continuity
3. **SmartImportProcessor** - Converts document imports into entity reactions instead of raw facts
4. **LayeredMemoryRetriever** - Rebalances retrieval to favor episodic/working over semantic
5. **EntityGraphCleaner** - Consolidates contradictory entity attributes
6. **GuaranteedContextLoader** - Ensures critical memories always load

## Installation

All components are in the `memory_continuity/` directory:

```
memory_continuity/
├── thread_momentum.py
├── session_boundary.py
├── smart_import.py
├── layered_retrieval.py
├── entity_cleanup.py
├── guaranteed_context.py
└── INTEGRATION_GUIDE.md (this file)
```

## Quick Start Integration

### 1. Initialize Components

```python
from memory_continuity.thread_momentum import ThreadMomentumTracker
from memory_continuity.session_boundary import SessionBoundaryHandler
from memory_continuity.smart_import import SmartImportProcessor
from memory_continuity.layered_retrieval import LayeredMemoryRetriever, RetrievalConfig
from memory_continuity.entity_cleanup import EntityGraphCleaner
from memory_continuity.guaranteed_context import GuaranteedContextLoader

# Your existing setup
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("memories")
llm_client = YourLLMClient()  # Your LLM integration
entity_graph = YourEntityGraph()  # Your entity graph

# Initialize continuity components
thread_tracker = ThreadMomentumTracker(
    dormancy_threshold=5,
    momentum_threshold=0.3
)

session_handler = SessionBoundaryHandler(llm_client)

import_processor = SmartImportProcessor(llm_client, session_handler)

retrieval_config = RetrievalConfig(
    working_multiplier=3.0,
    episodic_multiplier=2.0,
    semantic_multiplier=0.8,
    target_working_ratio=0.20,
    target_episodic_ratio=0.50,
    target_semantic_ratio=0.30
)

retriever = LayeredMemoryRetriever(collection, retrieval_config)

entity_cleaner = EntityGraphCleaner(
    entity_graph,
    llm_client,
    stale_threshold_turns=100,
    inactive_threshold_turns=50
)

context_loader = GuaranteedContextLoader(collection)
```

### 2. Session Start Flow

```python
async def start_session(session_id: str):
    """Start a new conversation session"""

    # Load previous session summary if exists
    previous_summary = session_handler.load_summary(f"sessions/{session_id}_summary.json")

    # Load guaranteed context from previous session
    guaranteed_memories = context_loader.load_session_start_context(
        session_summary=previous_summary,
        current_turn=0,
        entity_graph=entity_graph,
        max_guaranteed=50
    )

    # Restore thread tracker state
    if previous_summary:
        thread_tracker.restore_from_summary(
            previous_summary.open_threads if hasattr(previous_summary, 'open_threads') else {}
        )

    # Generate session start context for LLM
    if previous_summary:
        session_context = session_handler.generate_session_start_context(
            previous_summary,
            max_length=1000
        )
        print("=== SESSION CONTINUITY CONTEXT ===")
        print(session_context)

    return guaranteed_memories
```

### 3. Turn Processing Flow

```python
async def process_turn(user_input: str, current_turn: int, emotional_state: dict):
    """Process a single conversation turn"""

    # Extract entities and keywords from user input
    entities = extract_entities(user_input)  # Your entity extraction
    keywords = extract_keywords(user_input)  # Your keyword extraction

    # Update thread tracker
    thread_tracker.update_from_turn(
        user_input=user_input,
        agent_response="",  # Fill after generation
        extracted_entities=entities,
        extracted_keywords=keywords,
        memory_ids_referenced=[],  # Fill after retrieval
        open_questions=[],  # Extract from agent response
        emotional_intensity=max(emotional_state.values()) if emotional_state else 0.0
    )

    # Retrieve memories with layer weighting and thread momentum
    guaranteed_turn_context = context_loader.load_turn_guaranteed_context(
        current_turn=current_turn,
        user_input=user_input,
        thread_tracker=thread_tracker,
        emotional_state=emotional_state
    )

    retrieved_memories = retriever.retrieve(
        query=user_input,
        current_turn=current_turn,
        n_results=225,
        thread_tracker=thread_tracker,
        emotional_state=emotional_state,
        guaranteed_ids=[m.memory_id for m in guaranteed_turn_context]
    )

    # Merge guaranteed + retrieved
    final_memories = context_loader.merge_with_retrieved(
        guaranteed_memories=guaranteed_turn_context,
        retrieved_memories=retrieved_memories,
        max_total=225
    )

    # Analyze retrieval quality (for debugging)
    quality_report = retriever.analyze_retrieval_quality(final_memories, user_input)
    print(f"Retrieval quality: {quality_report}")

    # Generate LLM response with memories
    agent_response = await generate_llm_response(
        user_input=user_input,
        memories=final_memories,
        emotional_state=emotional_state
    )

    # Update thread tracker with agent response
    open_questions = extract_questions(agent_response)
    thread_tracker.update_from_turn(
        user_input=user_input,
        agent_response=agent_response,
        extracted_entities=entities,
        extracted_keywords=keywords,
        memory_ids_referenced=[m["id"] for m in final_memories],
        open_questions=open_questions,
        emotional_intensity=max(emotional_state.values()) if emotional_state else 0.0
    )

    # Track reactions if significant
    if is_significant_reaction(agent_response):
        session_handler.track_reaction(
            trigger=user_input[:100],
            reaction=agent_response[:200]
        )

    return agent_response, final_memories
```

### 4. Document Import Flow

```python
async def import_document(document_content: str, document_description: str, current_turn: int):
    """Import a document using smart processing"""

    # Get current state
    emotional_state = get_current_emotional_state()
    active_threads = thread_tracker.get_active_threads()

    # Get sample of related existing knowledge
    existing_knowledge = retriever.retrieve(
        query=document_description,
        current_turn=current_turn,
        n_results=10,
        thread_tracker=None,
        emotional_state=None
    )
    existing_knowledge_text = [m["content"] for m in existing_knowledge[:5]]

    # Process through entity's perspective
    synthesis = await import_processor.process_document_import(
        document_content=document_content,
        document_description=document_description,
        entity_name="Kay",  # Your entity name
        current_emotional_state=emotional_state,
        active_threads=[
            {
                "thread_id": t.thread_id,
                "entities": list(t.entities),
                "keywords": list(t.keywords)
            }
            for t in active_threads
        ],
        existing_knowledge_sample=existing_knowledge_text
    )

    # Store synthesis as episodic memory (NOT semantic flood)
    episodic_memory = import_processor.create_episodic_memory(synthesis, current_turn)
    collection.add(
        ids=[episodic_memory["id"]],
        documents=[episodic_memory["content"]],
        metadatas=[episodic_memory["metadata"]]
    )

    # Store only essential facts as semantic
    semantic_memories = import_processor.create_semantic_memories(synthesis, current_turn)
    if semantic_memories:
        collection.add(
            ids=[m["id"] for m in semantic_memories],
            documents=[m["content"] for m in semantic_memories],
            metadatas=[m["metadata"] for m in semantic_memories]
        )

    print(f"Import complete: {len(semantic_memories)} facts vs {synthesis.original_fact_count} original")
    print(f"Compression: {synthesis.compression_ratio:.1%}")
    print(f"Reaction: {synthesis.personal_reaction}")

    return synthesis
```

### 5. Session End Flow

```python
async def end_session(session_id: str, conversation_history: list, current_turn: int):
    """End session and generate summary"""

    # Generate comprehensive session summary
    summary = await session_handler.generate_session_end_summary(
        session_id=session_id,
        conversation_history=conversation_history,
        thread_tracker=thread_tracker,
        emotional_state=get_current_emotional_state(),
        memory_store=MemoryStoreAdapter(collection),  # Adapter for your memory store
        entity_graph=entity_graph
    )

    # Save summary for next session
    session_handler.save_summary(summary, f"sessions/{session_id}_summary.json")

    print(f"\n=== SESSION SUMMARY ===")
    print(f"Turns: {summary.total_turns}")
    print(f"Active threads: {len(summary.open_threads)}")
    print(f"Key reactions: {len(summary.key_reactions)}")
    print(f"Cognitive state: {summary.cognitive_state}")

    return summary
```

### 6. Periodic Maintenance

```python
async def run_periodic_cleanup(current_turn: int):
    """Run periodic entity graph cleanup and rebalancing"""

    # Every 50 turns, analyze and clean entity graph
    if current_turn % 50 == 0:
        print("\n=== RUNNING ENTITY CLEANUP ===")

        # Get cleanup summary
        health = entity_cleaner.get_cleanup_summary(current_turn)
        print(f"Entity graph health: {health['health_score']:.2f}")
        print(f"Contradictions: {health['total_contradictions']}")
        print(f"Stale entities: {health['stale_entities']}")

        # Analyze contradictions
        conflicts = entity_cleaner.analyze_contradictions(current_turn)

        # Consolidate high-severity conflicts
        for entity_id, entity_conflicts in conflicts.items():
            for conflict in entity_conflicts:
                if conflict.severity == "high":
                    consolidation = await entity_cleaner.consolidate_conflict(
                        conflict,
                        current_turn,
                        recent_context=get_recent_conversation()
                    )
                    entity_cleaner.apply_consolidation(consolidation, current_turn)
                    print(f"Consolidated {entity_id}.{conflict.attribute_name}: {consolidation.reasoning}")

        # Special handling for goal explosions
        for entity_id in entity_graph.get_all_entity_ids():
            entity = entity_graph.get_entity(entity_id)
            goal_count = sum(1 for k in entity.attributes.keys() if "goal" in k.lower())

            if goal_count > 10:  # Too many goals!
                result = await entity_cleaner.clean_goal_contradictions(
                    entity_id,
                    current_turn,
                    max_goals=5
                )
                print(f"Cleaned {entity_id} goals: {result['original_goal_count']} → {result['consolidated_to']}")

        # Archive stale entities
        archived = entity_cleaner.archive_stale_entities(current_turn)
        print(f"Archived {len(archived['stale'])} stale entities")

    # Every 100 turns, analyze layer distribution
    if current_turn % 100 == 0:
        print("\n=== LAYER DISTRIBUTION ANALYSIS ===")

        from memory_continuity.layered_retrieval import LayerBalancer
        balancer = LayerBalancer()

        storage_analysis = balancer.analyze_storage(collection)
        print(f"Working: {storage_analysis['working_pct']:.1f}%")
        print(f"Episodic: {storage_analysis['episodic_pct']:.1f}%")
        print(f"Semantic: {storage_analysis['semantic_pct']:.1f}%")
        print(f"Imbalance score: {storage_analysis['imbalance_score']:.2f}")

        # Get recommendations
        recommendations = balancer.recommend_promotions_demotions(collection, current_turn)
        print(f"Recommend promoting {len(recommendations['promote_to_episodic'])} to episodic")
        print(f"Recommend promoting {len(recommendations['promote_to_semantic'])} to semantic")
```

## Key Integration Points

### With Existing Memory System

```python
# Wrap your existing memory retrieval
def retrieve_memories_enhanced(query, turn, emotional_state):
    # Old way:
    # memories = collection.query(query, n_results=225)

    # New way:
    guaranteed = context_loader.load_turn_guaranteed_context(
        current_turn=turn,
        user_input=query,
        thread_tracker=thread_tracker,
        emotional_state=emotional_state
    )

    retrieved = retriever.retrieve(
        query=query,
        current_turn=turn,
        n_results=225,
        thread_tracker=thread_tracker,
        emotional_state=emotional_state,
        guaranteed_ids=[m.memory_id for m in guaranteed]
    )

    return context_loader.merge_with_retrieved(guaranteed, retrieved, max_total=225)
```

### With Existing Entity Graph

```python
# Add periodic cleanup to your entity graph updates
def update_entity_attribute(entity_id, attr_name, value, turn):
    # Your existing update logic
    entity_graph.update_attribute(entity_id, attr_name, value, turn)

    # Periodic conflict check
    if turn % 20 == 0:  # Every 20 turns
        conflicts = entity_cleaner.analyze_contradictions(
            turn,
            focus_entities=[entity_id]
        )

        # Auto-consolidate moderate/low severity
        for conflict in conflicts.get(entity_id, []):
            if conflict.severity != "high":
                consolidation = await entity_cleaner.consolidate_conflict(
                    conflict,
                    turn
                )
                entity_cleaner.apply_consolidation(consolidation, turn)
```

## Configuration Tuning

### Thread Momentum Sensitivity

```python
# More sensitive to thread changes
thread_tracker = ThreadMomentumTracker(
    dormancy_threshold=3,  # Lower = threads go dormant faster
    momentum_threshold=0.2  # Lower = more threads considered "active"
)

# Less sensitive (more stable threads)
thread_tracker = ThreadMomentumTracker(
    dormancy_threshold=10,  # Higher = threads stay active longer
    momentum_threshold=0.5  # Higher = fewer threads considered "active"
)
```

### Layer Distribution Targets

```python
# More episodic-heavy (better for conversation flow)
config = RetrievalConfig(
    target_working_ratio=0.15,
    target_episodic_ratio=0.65,  # 65% episodic
    target_semantic_ratio=0.20
)

# More balanced
config = RetrievalConfig(
    target_working_ratio=0.20,
    target_episodic_ratio=0.50,
    target_semantic_ratio=0.30
)
```

### Guaranteed Context Amount

```python
# Minimal guaranteed context (rely more on retrieval)
guaranteed = context_loader.load_session_start_context(
    session_summary=summary,
    current_turn=turn,
    entity_graph=entity_graph,
    max_guaranteed=20  # Only 20 guaranteed
)

# Heavy guaranteed context (ensure continuity)
guaranteed = context_loader.load_session_start_context(
    session_summary=summary,
    current_turn=turn,
    entity_graph=entity_graph,
    max_guaranteed=75  # 75 guaranteed
)
```

## Monitoring and Debugging

### Thread Momentum Monitoring

```python
# Check active threads
active = thread_tracker.get_active_threads()
for thread in active:
    print(f"Thread: {thread.thread_id}")
    print(f"  Momentum: {thread.momentum_score(current_turn):.2f}")
    print(f"  Entities: {', '.join(list(thread.entities)[:3])}")
    print(f"  Open questions: {len(thread.open_questions)}")
```

### Retrieval Quality Monitoring

```python
# After each retrieval
quality = retriever.analyze_retrieval_quality(memories, query)
print(f"Layer distribution: W={quality['distribution']['working_pct']:.1f}% "
      f"E={quality['distribution']['episodic_pct']:.1f}% "
      f"S={quality['distribution']['semantic_pct']:.1f}%")
print(f"Avg age: {quality['avg_age_turns']:.1f} turns")
print(f"Thread coverage: {quality['thread_coverage']} threads")
```

### Entity Graph Health Monitoring

```python
# Periodic health checks
health = entity_cleaner.get_cleanup_summary(current_turn)
print(f"Entity graph health: {health['health_score']:.2%}")
if health['health_score'] < 0.7:
    print("⚠️ Entity graph needs cleanup!")
```

## Troubleshooting

### Problem: Still getting semantic flood

**Solution**: Lower semantic multiplier and increase layer promotion thresholds

```python
config = RetrievalConfig(
    semantic_multiplier=0.5,  # Lower
    working_multiplier=4.0,   # Higher
    episodic_multiplier=2.5   # Higher
)
```

### Problem: Losing thread continuity

**Solution**: Increase thread dormancy threshold and guaranteed context

```python
thread_tracker = ThreadMomentumTracker(
    dormancy_threshold=10,  # Keep threads active longer
)

guaranteed = context_loader.load_turn_guaranteed_context(...)  # Use this every turn
```

### Problem: Too many contradictions

**Solution**: Run cleanup more frequently and lower severity thresholds

```python
# Clean every 20 turns instead of 50
if current_turn % 20 == 0:
    await run_periodic_cleanup(current_turn)

# Auto-resolve all contradictions, not just high-severity
for conflict in all_conflicts:
    consolidation = await entity_cleaner.consolidate_conflict(conflict, current_turn)
    entity_cleaner.apply_consolidation(consolidation, current_turn)
```

## Performance Considerations

- **Thread tracking**: O(n) per turn where n = number of active threads (typically 3-10)
- **Layer retrieval**: 2x over-retrieval + reranking (manageable for 225 target)
- **Entity cleanup**: Only run periodically (every 50-100 turns)
- **Session summaries**: Only at session boundaries, can be async

## Next Steps

1. Start with just `LayeredMemoryRetriever` to fix distribution
2. Add `GuaranteedContextLoader` for session continuity
3. Add `ThreadMomentumTracker` for thread awareness
4. Add `SessionBoundaryHandler` for session summaries
5. Add `SmartImportProcessor` if you have document imports
6. Add `EntityGraphCleaner` if contradictions are a problem

## Support

For issues or questions, check the docstrings in each module. Each class has detailed documentation.
