# Enhanced Memory Architecture - Quick Start Guide

## What Changed?

KayZero's memory system now has:

1. **Entity Resolution**: Tracks people, places, things with full attribute history
2. **Multi-Layer Memory**: Working → Episodic → Semantic automatic transitions
3. **Multi-Factor Retrieval**: Smarter memory selection combining 5 factors
4. **ULTRAMAP Integration**: Emotional importance determines memory persistence

## For Existing Users

### Do I Need to Migrate?

**No migration required!** The system is backward compatible:

- Existing `memory/memories.json` will work as-is
- New features are automatically enabled
- Old memories get default values for new fields

### Optional: Migrate for Full Benefits

To populate the entity graph and layer system from existing memories:

```bash
python migrate_memories.py
```

This creates:
- `memory/entity_graph.json` - Entity resolution data
- `memory/memory_layers.json` - Multi-layer memory
- Backup of original memories

## Using the New Features

### 1. Entity Resolution (Automatic)

When you mention entities, they're automatically tracked:

**Example conversation:**
```
User: My dog's name is Saga.
Kay: [Creates entity "Saga" with attribute species=dog]

User: Saga loves to play fetch.
Kay: [Links "Saga" to previous entity, adds attributes]

User: My dog is tired today.
Kay: [Resolves "my dog" → "Saga" automatically]
```

**View entities:**
```python
# In Python console or code
from engines.entity_graph import EntityGraph

graph = EntityGraph()
print(f"Tracked entities: {len(graph.entities)}")

# Get specific entity
saga = graph.entities.get("Saga")
if saga:
    print(f"Saga's attributes: {saga.attributes}")
    print(f"Contradictions: {saga.detect_contradictions()}")
```

### 2. Multi-Layer Memory (Automatic)

Memories automatically move between layers:

- **Working** (last 10): Recent conversation context
- **Episodic** (last 100): Recent experiences, hours to weeks
- **Semantic** (unlimited): Permanent facts

**Promotion happens automatically:**
```
Turn 1: "My name is Re" → Working memory
Turn 3: "My name is Re" retrieved again → Promoted to Episodic
Turn 10: "My name is Re" retrieved 5 times → Promoted to Semantic
```

**View layer distribution:**
```python
from engines.memory_engine import MemoryEngine

memory = MemoryEngine()
stats = memory.memory_layers.get_layer_stats()
print(stats)
# Output:
# {
#   "working": {"count": 8, "avg_strength": 0.85},
#   "episodic": {"count": 42, "avg_strength": 0.60},
#   "semantic": {"count": 15, "avg_strength": 1.0}
# }
```

### 3. Multi-Factor Retrieval (Enabled by Default)

Memories are now selected using:
- 40% Emotional resonance
- 25% Keyword match
- 20% Importance (from ULTRAMAP)
- 10% Recency
- 5% Shared entities

**To see retrieval scores:**
```
# Look for this in console output:
[RETRIEVAL] Multi-factor retrieval selected 7 memories (scores: ['0.85', '0.72', ...])
```

**To disable (use legacy retrieval):**
```python
# In main.py or kay_ui.py
memory.recall(state, user_input, use_multi_factor=False)  # Legacy mode
```

### 4. Entity Contradictions (Automatic Detection)

When Kay contradicts himself, the system detects it:

**Example:**
```
Turn 5: "My eyes are green" → Stored as Re.eye_color = green
Turn 12: Kay says "Your eyes are brown" → CONTRADICTION DETECTED

Console output:
[ENTITY GRAPH] ⚠️ Detected 1 entity contradictions
  - Re.eye_color: {'green': [(5, 'user', ...)], 'brown': [(12, 'kay', ...)]}
```

The contradiction is added to `agent_state.entity_contradictions` and can be:
- Shown to Kay in context
- Resolved by Kay in next response
- Logged for analysis

## Monitoring the System

### 1. Check State Snapshot

After each turn, `memory/state_snapshot.json` includes:

```json
{
  "entity_contradictions": [...],
  "memory_layer_stats": {...},
  "top_entities": [
    {"name": "Re", "importance": 0.95, "access_count": 47}
  ]
}
```

### 2. Console Logs

Look for these markers:

```
[ENTITY GRAPH] Created new entity: Saga (type: animal)
[ENTITY] Re.eye_color = green (turn 5, source: user)
[MEMORY LAYERS] Promoted to episodic: My dog's name is Saga...
[RETRIEVAL] Multi-factor retrieval selected 7 memories
[MEMORY] Applied temporal decay at turn 20
```

### 3. Inspect Memory Files

Three key files:

- `memory/memories.json` - All memories (enhanced format)
- `memory/entity_graph.json` - Entity resolution data
- `memory/memory_layers.json` - Layer distribution

## Tuning the System

### Adjust Layer Capacities

In `engines/memory_layers.py`:

```python
self.working_capacity = 10      # Change to 5 or 15
self.episodic_capacity = 100    # Change to 50 or 200
```

### Adjust Promotion Thresholds

In `engines/memory_layers.py`:

```python
self.working_to_episodic_accesses = 2   # Promote faster: 1, slower: 3
self.episodic_to_semantic_accesses = 5  # Promote faster: 3, slower: 10
```

### Adjust Retrieval Weights

In `memory_engine.py` → `retrieve_multi_factor()`:

```python
emotional_weight = 0.4    # Increase for more emotion-driven recall
semantic_weight = 0.25    # Increase for more keyword-driven recall
importance_weight = 0.20  # Increase to favor important memories
recency_weight = 0.10     # Increase to favor recently accessed
entity_weight = 0.05      # Increase to favor shared entities
```

### Adjust Decay Rates

In `engines/memory_layers.py`:

```python
self.episodic_decay_halflife = 7   # Days until episodic fades (default: 7)
self.working_decay_halflife = 0.5  # Days until working fades (default: 0.5)
```

## Common Questions

### Q: Will this slow down Kay?

**A:** Minimal impact. Fact extraction adds 1 LLM call per turn (~200ms). Entity processing and retrieval are fast in-memory operations.

### Q: How much disk space does this use?

**A:** Small increase:
- Entity graph: ~10KB per 100 entities
- Memory layers: ~50KB per 100 memories
- Total for typical session: +50-100KB

### Q: Can I disable the new features?

**A:** Yes, partially:
- Multi-factor retrieval: Set `use_multi_factor=False` in `recall()`
- Entity extraction: Skip by removing entity processing in `_extract_facts()`
- Memory layers: Old flat memories still work

### Q: What if entity resolution makes mistakes?

**A:** The system maintains full provenance:
- All attribute values are kept with timestamps
- You can manually edit `memory/entity_graph.json`
- Future: Add LLM-based resolution for ambiguous cases

### Q: How does ULTRAMAP integrate?

**A:** ULTRAMAP pressure × recursion creates importance scores:
- High importance → slower decay
- High importance → faster promotion
- High importance → retrieval boost

### Q: What happens to old memories after migration?

**A:** They're preserved:
- Original backed up with timestamp
- Enhanced with new fields (entities, importance, etc.)
- Distributed across layers based on estimated age/importance

## Troubleshooting

### Issue: Migration fails

**Solution:**
```bash
# Check for backup
ls memory/*backup*.json

# If backup exists, restore it
cp memory/memories_backup_<timestamp>.json memory/memories.json

# Run migration with debug
python migrate_memories.py 2>&1 | tee migration_log.txt
```

### Issue: Too many contradictions detected

**Solution:**
Contradictions are normal! They represent:
- Preferences evolving over time
- Kay learning more accurate information
- User correcting Kay's misunderstandings

To resolve:
- Kay will see contradictions in context
- Kay can address them in responses
- Edit `memory/entity_graph.json` to fix persistent errors

### Issue: Memory layers not filling

**Solution:**
Layers fill slowly by design:
- Working: Fills in ~10 turns
- Episodic: Fills over weeks
- Semantic: Only highly-accessed memories

To check promotion:
```python
# Lower access thresholds in memory_layers.py
self.working_to_episodic_accesses = 1  # Promote after 1 access
```

### Issue: Retrieval seems off

**Solution:**
Multi-factor retrieval balances 5 factors:
- Check console: `[RETRIEVAL] ... scores: [...]`
- Adjust weights in `retrieve_multi_factor()`
- Try legacy mode: `use_multi_factor=False`

## Next Steps

1. **Run migration** (optional but recommended):
   ```bash
   python migrate_memories.py
   ```

2. **Have a conversation** and watch the logs:
   - Entity creation
   - Memory promotion
   - Contradiction detection

3. **Inspect snapshot** after a few turns:
   ```bash
   cat memory/state_snapshot.json
   ```

4. **Read full docs** for advanced usage:
   - `MEMORY_ARCHITECTURE.md` - Complete technical reference
   - `CLAUDE.md` - Overall system architecture

5. **Experiment with tuning** to match your preferences

## Summary

The enhanced memory architecture makes Kay:

✅ **More coherent**: Entities tracked with full history
✅ **More adaptive**: Memories persist based on importance
✅ **More self-aware**: Detects his own contradictions
✅ **More context-aware**: Smarter retrieval balances multiple factors

Everything works automatically - just start using Kay normally and the new features will activate!
