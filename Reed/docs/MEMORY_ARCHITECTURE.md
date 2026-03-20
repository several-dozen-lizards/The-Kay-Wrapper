# Enhanced Memory Architecture for AlphaKayZero

## Overview

AlphaKayZero's memory system has been enhanced with **entity resolution** and **multi-layer memory** inspired by memU and Silvie, while keeping ULTRAMAP as the foundational emotional architecture.

## New Components

### 1. Entity Resolution System (`engines/entity_graph.py`)

The entity resolution system tracks discrete entities (people, places, concepts) with full attribute history and relationship tracking.

#### Entity Class

Represents a single entity with:
- **Canonical name**: Primary identifier (e.g., "[dog]", "Re", "Kay")
- **Aliases**: Alternative names this entity is known by
- **Attributes**: History of all attribute values with full provenance
  - Each attribute stores: `(value, turn_index, source, timestamp)`
  - Example: `eye_color: [("green", 5, "user", "2025-01-15T10:30:00"), ("gold", 12, "kay", "2025-01-15T10:45:00")]`
- **Relationships**: References to relationship objects
- **Metadata**: First mentioned, last accessed, access count, importance score

**Contradiction Detection:**
- Automatically detects conflicting attribute values
- Classifies severity: HIGH (physical attributes), MODERATE (preferences), LOW (mood-dependent)
- Maintains full provenance for resolution

#### EntityGraph Class

Manages all entities and relationships:
- **Entity resolution**: Matches mentions ("my dog", "[dog]") to canonical entities
- **Relationship tracking**: "Re owns [dog]", "Kay lives_in Portland"
- **Graph traversal**: Find related entities within N hops
- **Importance ranking**: Sort entities by ULTRAMAP-derived importance scores
- **Persistence**: Saves to `memory/entity_graph.json`

### 2. Multi-Layer Memory System (`engines/memory_layers.py`)

Implements three-tier memory architecture with automatic transitions.

#### Memory Layers

**Working Memory (Capacity: 10)**
- Immediate context from last 5-10 turns
- High retrieval priority (1.5x boost)
- Fast decay: 0.5 day half-life
- Promotes to Episodic after 2+ accesses

**Episodic Memory (Capacity: 100)**
- Recent experiences from hours to weeks
- Normal retrieval priority (1.0x)
- Moderate decay: 7 day half-life
- Promotes to Semantic after 5+ accesses

**Semantic Memory (Unlimited)**
- Permanent facts and core identity
- Enhanced retrieval priority (1.2x boost)
- No decay (only removed if contradicted)
- Terminal layer - memories don't leave

#### ULTRAMAP Integration

**Importance Scoring:**
```
importance = (average_pressure × average_recursion) × emotional_intensity
```

**Temporal Decay:**
```
effective_halflife = base_halflife × (1 + importance)
strength = 0.5^(age_days / effective_halflife)
```

Higher importance → slower decay → longer persistence

#### Automatic Promotion

Memories automatically promote between layers based on:
- **Access count**: Frequently retrieved memories move up
- **Importance score**: High ULTRAMAP scores accelerate promotion
- **Layer capacity**: When layer fills, weakest memories promote or prune

### 3. Multi-Factor Retrieval (`memory_engine.py`)

Enhanced retrieval combines five factors with weighted scoring:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Emotional Resonance** | 40% | Match between memory emotion tags and current emotional cocktail |
| **Semantic Similarity** | 25% | Keyword overlap between query and memory text |
| **Importance** | 20% | ULTRAMAP pressure × recursion score |
| **Recency** | 10% | Access count (capped at 1.0) |
| **Entity Proximity** | 5% | Shared entities between query and memory |

**Layer Boost:**
- Semantic memories: 1.2x
- Working memories: 1.5x
- Episodic memories: 1.0x (baseline)

**Final Score:**
```
final_score = (
    emotion_score × 0.4 +
    keyword_overlap × 0.25 +
    importance × 0.20 +
    recency_score × 0.10 +
    entity_score × 0.05
) × layer_boost
```

## Enhanced Fact Extraction

### Entity-Aware Fact Extraction

The LLM-based fact extraction now extracts:

```json
{
  "fact": "[dog] is Re's dog",
  "perspective": "user",
  "topic": "relationships",
  "entities": ["[dog]", "Re"],
  "attributes": [
    {"entity": "[dog]", "attribute": "species", "value": "dog"}
  ],
  "relationships": [
    {"entity1": "Re", "relation": "owns", "entity2": "[dog]"}
  ]
}
```

### Automatic Entity Processing

When facts are extracted, the system automatically:
1. Creates/updates entities in the entity graph
2. Adds attributes with full provenance (turn, source, timestamp)
3. Creates relationship objects
4. Detects contradictions in real-time

## Migration from Legacy Memories

### Running Migration

To upgrade existing memories:

```bash
python migrate_memories.py
```

This script:
1. **Backs up** existing `memory/memories.json`
2. **Adds missing fields** to each memory record
3. **Populates entity graph** from existing facts
4. **Distributes memories** across Working/Episodic/Semantic layers
5. **Detects contradictions** in existing data
6. **Creates new files**:
   - `memory/entity_graph.json` - Entity resolution data
   - `memory/memory_layers.json` - Multi-layer memory system

### Backward Compatibility

The enhanced system is **fully backward compatible**:
- Old memories work without migration (default values applied)
- Legacy `retrieve_biased_memories()` method still available
- New features can be disabled by setting `use_multi_factor=False` in `recall()`

## Usage Examples

### Entity Resolution

```python
# Get or create entity
entity = memory.entity_graph.get_or_create_entity(
    "[dog]",
    entity_type="animal",
    turn=current_turn
)

# Add attribute
entity.add_attribute(
    "eye_color",
    "brown",
    turn=current_turn,
    source="user"
)

# Detect contradictions
contradictions = entity.detect_contradictions()
# Returns: [{"attribute": "eye_color", "values": {...}, "severity": "high"}]
```

### Memory Layer Management

```python
# Add memory to working layer
memory.memory_layers.add_memory(record, layer="working")

# Apply temporal decay
memory.memory_layers.apply_temporal_decay()

# Get layer statistics
stats = memory.memory_layers.get_layer_stats()
# Returns: {"working": {...}, "episodic": {...}, "semantic": {...}}
```

### Multi-Factor Retrieval

```python
# Automatic in recall() method
memory.recall(state, user_input, use_multi_factor=True)

# Manual retrieval
memories = memory.retrieve_multi_factor(
    bias_cocktail=state.emotional_cocktail,
    user_input="Tell me about [dog]",
    num_memories=10
)
```

## Architecture Benefits

### From memU (Entity Resolution)

✅ **Canonical entity tracking**: "my dog" → "[dog]" resolution
✅ **Attribute provenance**: Full history with timestamps and sources
✅ **Contradiction detection**: Automatic conflict identification
✅ **Relationship graphs**: "Re owns [dog]", "Kay likes coffee"

### From Silvie (Multi-Layer Memory)

✅ **Temporal decay**: Memories fade naturally over time
✅ **Importance-based persistence**: ULTRAMAP pressure × recursion
✅ **Automatic promotion**: Access frequency determines layer
✅ **Layer-specific retrieval**: Recent context vs permanent facts

### ULTRAMAP Integration

✅ **Emotional importance**: High-pressure emotions create lasting memories
✅ **Recursive strengthening**: Repeated emotional patterns boost persistence
✅ **Decay modulation**: Important memories decay slower
✅ **Multi-factor weighting**: Emotions still dominate retrieval (40%)

## Performance Characteristics

### Memory Footprint

- **Working memory**: ~10 memories (recent context)
- **Episodic memory**: ~100 memories (recent experiences)
- **Semantic memory**: Unlimited (permanent facts)
- **Entity graph**: Grows with unique entities mentioned
- **Relationships**: Grows with entity interactions

### Computational Cost

- **Fact extraction**: 1 LLM call per turn (400 tokens)
- **Entity processing**: O(entities × attributes) per fact
- **Multi-factor retrieval**: O(total_memories × 5_factors)
- **Temporal decay**: Every 10 turns, O(working + episodic)

### Disk Usage

New files created:
- `memory/entity_graph.json` (~10KB per 100 entities)
- `memory/memory_layers.json` (~50KB per 100 memories)
- Existing `memory/memories.json` (enhanced format)

## Monitoring and Debugging

### System Snapshot

The autosaved `memory/state_snapshot.json` now includes:

```json
{
  "entity_contradictions": [...],
  "memory_layer_stats": {
    "working": {"count": 8, "avg_strength": 0.85},
    "episodic": {"count": 42, "avg_strength": 0.60},
    "semantic": {"count": 15, "avg_strength": 1.0}
  },
  "top_entities": [
    {
      "name": "Re",
      "type": "person",
      "importance": 0.95,
      "access_count": 47
    }
  ]
}
```

### Debug Logging

Look for these log markers:

```
[ENTITY GRAPH] Created new entity: [dog] (type: animal)
[ENTITY] Re.eye_color = green (turn 5, source: user)
[ENTITY GRAPH] ⚠️ Detected 1 entity contradictions
[MEMORY LAYERS] Promoted to episodic: My dog's name is [dog]...
[RETRIEVAL] Multi-factor retrieval selected 7 memories (scores: ['0.85', '0.72', ...])
[MEMORY] Applied temporal decay at turn 20
```

## Tuning Parameters

### Entity Resolution

```python
# In engines/entity_graph.py

# Relationship strength threshold
relationship.strength = 1.0  # 0.0 to 1.0

# Contradiction severity classification
high_severity_attrs = ["eye_color", "name", "species"]
moderate_severity_attrs = ["favorite", "core_preference"]
```

### Memory Layers

```python
# In engines/memory_layers.py

# Layer capacities
self.working_capacity = 10
self.episodic_capacity = 100
# semantic is unlimited

# Promotion thresholds
self.working_to_episodic_accesses = 2
self.episodic_to_semantic_accesses = 5
self.min_importance_for_promotion = 0.3

# Decay half-lives
self.episodic_decay_halflife = 7  # days
self.working_decay_halflife = 0.5  # days
```

### Multi-Factor Weights

```python
# In memory_engine.py retrieve_multi_factor()

emotional_weight = 0.4    # 40%
semantic_weight = 0.25    # 25%
importance_weight = 0.20  # 20%
recency_weight = 0.10     # 10%
entity_weight = 0.05      # 5%

# Layer boosts
if current_layer == "semantic":
    layer_boost = 1.2
elif current_layer == "working":
    layer_boost = 1.5
```

## Future Enhancements

Potential additions:

1. **LLM-based entity resolution**: Use LLM to resolve ambiguous mentions
2. **Entity type classification**: Auto-detect "person", "place", "concept"
3. **Relationship strength decay**: Relationships fade if not reinforced
4. **Semantic clustering**: Group related memories by concept
5. **Cross-session entity linking**: Merge entities across sessions
6. **Entity importance learning**: Boost entities mentioned in high-emotion contexts

## Conclusion

The enhanced memory architecture provides:

✅ **Entity continuity**: Kay remembers who/what entities are across turns
✅ **Temporal awareness**: Recent vs long-term memory distinction
✅ **Importance-based persistence**: ULTRAMAP guides what to remember
✅ **Contradiction detection**: Self-correcting identity system
✅ **Multi-factor retrieval**: Context-aware memory selection

This creates a more coherent, self-aware agent with persistent identity and natural memory dynamics.
