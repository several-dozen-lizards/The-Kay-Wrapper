# Semantic Knowledge System - Quick Start Guide

**Last Updated:** 2025-01-04

---

## What Is It?

Semantic Knowledge is a new system that stores **facts Kay knows** separately from **events that happened** (episodic memory) and **who Kay is** (identity).

### Example:
- **Semantic fact:** "Gimpy is a one-legged pigeon" ← Stored in semantic knowledge
- **Episodic event:** "Re uploaded pigeon document yesterday" ← Stored in memory layers
- **Core identity:** "Kay is a guy in his 30s" ← Will move to system prompt (Phase 4)

---

## How It Works

### 1. Document Import (Automatic)

When you import a document:

```
User uploads pigeon_facts.txt
  ↓
PARALLEL PROCESSING:

  Path A: Emotional Importer (existing)
  - Creates narrative chunks
  - Stores in episodic memory

  Path B: Semantic Extractor (NEW)
  - LLM extracts discrete facts
  - Stores in semantic knowledge base
  ↓
Both saved to disk
```

**Files:**
- Episodic: `memory/memory_layers.json`
- Semantic: `memory/semantic_knowledge.json`

---

### 2. Query Time (Automatic)

When user asks a question:

```
User: "What pigeons do you know?"
  ↓
Context Filter:
  1. Query semantic knowledge → retrieves pigeon facts
  2. Query episodic memory → retrieves upload events
  3. Combine both
  ↓
Kay gets complete context
  ↓
Kay: "Gimpy, Bob, Fork, and Zebra"
```

---

## Usage

### Import Documents

Just import normally through the UI - semantic extraction happens automatically:

```python
# Through UI:
1. Click "Import Memory"
2. Select file (pigeon_facts.txt)
3. Click "Import"

# Or programmatically:
from memory_import.import_manager import ImportManager

manager = ImportManager(
    memory_engine=memory_engine,
    entity_graph=entity_graph,
    use_emotional_integration=True  # Default
)

await manager.import_files(["path/to/document.txt"])
```

**What happens:**
- Document parsed into chunks
- Emotional importer creates narrative memories
- **Semantic extractor extracts facts** (NEW)
- Both saved to respective stores

---

### Query Semantic Knowledge

Querying is automatic during conversation, but you can also query directly:

```python
from engines.semantic_knowledge import get_semantic_knowledge

# Get semantic knowledge instance
sk = get_semantic_knowledge()

# Query for facts
facts = sk.query(
    query_text="What pigeons do I know?",
    entities=["pigeon"],  # Optional: explicit entities
    top_k=20  # Max facts to return
)

# Results:
# [
#   {
#     "text": "Gimpy is a one-legged pigeon",
#     "entities": ["gimpy", "pigeon"],
#     "category": "animals",
#     "relevance_score": 100.0
#   },
#   ...
# ]
```

---

### Add Facts Manually

For testing or programmatic fact addition:

```python
from engines.semantic_knowledge import get_semantic_knowledge

sk = get_semantic_knowledge()

sk.add_fact(
    text="Chrome is a cat who steals burritos",
    entities=["Chrome", "cat", "burritos"],
    source="manual_entry",
    category="animals",
    metadata={"confidence": 0.95}
)

# Save to disk
sk.save()
```

---

### Get Facts by Entity

```python
sk = get_semantic_knowledge()

# Get all facts about a specific entity
gimpy_facts = sk.get_facts_by_entity("Gimpy")

# Returns:
# [
#   {
#     "text": "Gimpy is a one-legged pigeon",
#     "entities": ["gimpy", "pigeon"],
#     "fact_id": "fact_0",
#     "access_count": 5
#   }
# ]
```

---

### Get Facts by Category

```python
sk = get_semantic_knowledge()

# Get all animal facts
animal_facts = sk.get_facts_by_category("animals")

# Get all people facts
people_facts = sk.get_facts_by_category("people")
```

---

### Check Statistics

```python
sk = get_semantic_knowledge()

stats = sk.get_stats()

# Returns:
# {
#   "total_facts": 50,
#   "total_entities": 120,
#   "total_categories": 5,
#   "categories": {
#     "animals": 25,
#     "people": 10,
#     "concepts": 8,
#     "places": 5,
#     "objects": 2
#   },
#   "most_accessed_facts": [...],
#   "newest_facts": [...]
# }
```

---

## Debug Output

When semantic knowledge is used, you'll see:

```
[SEMANTIC QUERY] Query: 'What pigeons do you know?...'
[SEMANTIC QUERY] Extracted entities: ['pigeon', 'pigeons']
[SEMANTIC QUERY] Retrieved 5 semantic facts
[SEMANTIC QUERY] Top fact: All four pigeons visit the park daily...

[COMBINED CONTEXT] Total: 7 memories
[COMBINED CONTEXT]   Semantic facts: 5
[COMBINED CONTEXT]   Episodic memories: 2
```

**What this means:**
- Entities automatically extracted from query
- Semantic knowledge queried
- Facts retrieved based on entity matching
- Combined with episodic memories

---

## File Locations

### Semantic Knowledge
```
memory/semantic_knowledge.json
```

**Format:**
```json
{
  "facts": {
    "fact_0": {
      "text": "Gimpy is a one-legged pigeon",
      "entities": ["gimpy", "pigeon"],
      "source": "pigeon_facts.txt",
      "category": "animals",
      "timestamp": 1704384000.0,
      "access_count": 5,
      "metadata": {"confidence": 0.95}
    }
  },
  "entity_index": {
    "gimpy": ["fact_0"],
    "pigeon": ["fact_0", "fact_1", "fact_2", "fact_3"]
  },
  "category_index": {
    "animals": ["fact_0", "fact_1", "fact_2", "fact_3"]
  }
}
```

### Episodic Memory (Unchanged)
```
memory/memory_layers.json
memory/memories.json
```

---

## Categories

Default categories for semantic facts:

- **people** - Facts about humans
- **animals** - Facts about animals
- **objects** - Facts about things
- **places** - Facts about locations
- **concepts** - Facts about abstract ideas
- **relationships** - Facts about connections between entities
- **general** - Catch-all category

Categories are assigned automatically by the LLM during extraction.

---

## Scoring

Semantic facts are scored based on:

1. **Entity exact match:** 100 points per matching entity (highest priority)
2. **Keyword overlap:** 10 points per matching keyword
3. **Recency bonus:** Up to 5 points for recent facts
4. **Access frequency:** Up to 10 points for frequently accessed facts

**Example:**
```
Query: "Tell me about Gimpy the pigeon"
Entities: ["gimpy", "pigeon"]

Fact: "Gimpy is a one-legged pigeon"
Score: 100 (gimpy) + 100 (pigeon) + 10 (keyword matches) = 210
```

High scores ensure semantic facts appear first in combined context.

---

## Troubleshooting

### Facts Not Retrieving

**Problem:** Query doesn't return expected facts

**Check:**
1. Verify facts exist: `sk.get_stats()`
2. Check entity spelling: Entities are lowercase
3. Try explicit entities: `sk.query(query, entities=["pigeon"])`
4. Check debug output: `[SEMANTIC QUERY]` messages

### Facts Not Persisting

**Problem:** Facts disappear after restart

**Solution:**
- Ensure `sk.save()` is called
- Check file exists: `memory/semantic_knowledge.json`
- Import manager auto-saves after document import

### Duplicate Facts

**Problem:** Same fact appears multiple times

**Solution:**
- Semantic extractor has deduplication
- But might extract slight variations
- Can manually delete: `sk.delete_fact(fact_id)`

### Entity Not Recognized

**Problem:** Entity extraction misses capitalized words

**Solution:**
- Entity extraction is heuristic-based
- Looks for capitalized words + category keywords
- Can pass explicit entities: `entities=["SpecificName"]`
- Future: Will use NER for better accuracy

---

## Testing

### Unit Tests
```bash
# Test semantic knowledge store
python test_semantic_knowledge.py

# Test retrieval integration
python test_semantic_retrieval.py
```

### Manual Testing
```python
# 1. Add test facts
from engines.semantic_knowledge import get_semantic_knowledge

sk = get_semantic_knowledge()
sk.add_fact(
    text="Test fact about X",
    entities=["X", "test"],
    source="manual_test",
    category="general"
)
sk.save()

# 2. Query in conversation
User: "What do you know about X?"

# 3. Check debug output
# Should see: [SEMANTIC QUERY] Retrieved 1 semantic facts
```

---

## Best Practices

### DO:
✅ Let document import handle fact extraction automatically
✅ Use entity-based queries for best results
✅ Check debug output to verify facts are retrieved
✅ Rely on scoring system for relevance

### DON'T:
❌ Manually add facts unless testing (use document import)
❌ Duplicate facts across semantic + episodic
❌ Store events as semantic facts (use episodic memory)
❌ Store core identity as semantic facts (will move to system prompt)

---

## Architecture Summary

```
┌─────────────────────────────────────────┐
│ User Query: "What pigeons do I know?"   │
└──────────────┬──────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────┐
│ Context Filter (context_filter.py)          │
│                                              │
│  STEP 0: Query Semantic Knowledge (NEW)     │
│  ├─ Extract entities: ["pigeon"]            │
│  ├─ Query knowledge base                    │
│  └─ Returns: 5 pigeon facts                 │
│                                              │
│  STEP 1: Get Episodic Memories              │
│  └─ Returns: Upload events, conversations   │
│                                              │
│  STEP 2: Combine                            │
│  ├─ Semantic facts (5) FIRST                │
│  └─ Episodic memories (2) SECOND            │
│                                              │
│  STEP 3: Filter through Glyph Filter        │
│  └─ LLM selects most relevant               │
└──────────────┬───────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────┐
│ Kay receives combined context:              │
│  - Gimpy (one-legged pigeon)                │
│  - Bob (speckled pigeon)                    │
│  - Fork (split tail pigeon)                 │
│  - Zebra (striped pigeon)                   │
│  - Upload event context                     │
└──────────────┬───────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────┐
│ Kay's Response:                              │
│ "I know Gimpy (one-legged), Bob (speckled), │
│  Fork (split tail), and Zebra (striped)"    │
└──────────────────────────────────────────────┘
```

---

## Related Documentation

- **SEMANTIC_KNOWLEDGE_PHASES_1_2_COMPLETE.md** - Phases 1 & 2 implementation
- **SEMANTIC_KNOWLEDGE_PHASE_3_COMPLETE.md** - Phase 3 retrieval integration
- **engines/semantic_knowledge.py** - Core implementation
- **memory_import/semantic_extractor.py** - LLM fact extraction
- **context_filter.py** - Retrieval integration

---

## Future Enhancements

### Planned:
- Phase 4: Move core identity to system prompt
- Phase 5: Migrate existing memories to semantic knowledge

### Possible:
- Better entity extraction (NER)
- Fact decay over time (optional)
- Semantic-first query routing (bypass glyph filter)
- Fact contradiction detection
- Multi-language support

---

## Quick Reference Commands

```python
# Get semantic knowledge instance
from engines.semantic_knowledge import get_semantic_knowledge
sk = get_semantic_knowledge()

# Query facts
facts = sk.query("What pigeons do I know?", top_k=20)

# Get by entity
gimpy_facts = sk.get_facts_by_entity("Gimpy")

# Get by category
animal_facts = sk.get_facts_by_category("animals")

# Add fact manually
sk.add_fact(
    text="Chrome steals burritos",
    entities=["Chrome", "burritos"],
    source="manual",
    category="animals"
)

# Save
sk.save()

# Get stats
stats = sk.get_stats()
print(f"Total facts: {stats['total_facts']}")
```

---

**System is ready for production use. Import documents and ask questions!**
