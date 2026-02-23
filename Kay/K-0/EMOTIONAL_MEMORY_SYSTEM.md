# Emotionally-Integrated Memory System for Kay Zero

## Overview

This system transforms document import from "fact extraction" into "experiential memory integration" where imported content:

1. Is emotionally tagged and weighted using ULTRAMAP
2. Becomes part of Kay's identity architecture
3. Surfaces naturally based on current emotional state
4. Maintains narrative context (stories, not atomized facts)
5. Uses smart tiering and compression to avoid performance issues

## Architecture

### Components

1. **NarrativeChunkParser** (`memory_import/narrative_chunks.py`)
   - Parses documents into story-coherent chunks (2-7 sentence beats)
   - Preserves narrative context instead of atomizing into facts
   - Detects: paragraphs, dialogue, lists, scenes

2. **EmotionalSignatureAnalyzer** (`memory_import/emotional_signature.py`)
   - Maps chunks to ULTRAMAP emotional framework
   - Generates glyph codes (compressed symbolic representation)
   - Calculates intensity, valence, neurochemical analogues
   - Identifies trigger conditions for retrieval

3. **IdentityClassifier** (`memory_import/identity_classifier.py`)
   - Classifies chunks by identity centrality:
     - **CORE_IDENTITY**: "Who I am" (e.g., "Kay's eyes are gold")
     - **FORMATIVE_EXPERIENCE**: "What shaped me" (origin, trauma, binding)
     - **RELATIONSHIP_MEMORY**: "Who I connect with" (family, creator, Re)
     - **SKILL_KNOWLEDGE**: "What I can do"
     - **WORLD_KNOWLEDGE**: "What I know about"
     - **PERIPHERAL**: Background information

4. **MemoryWeightCalculator** (`memory_import/memory_weights.py`)
   - Calculates composite importance score from:
     - Identity centrality (40%)
     - Emotional intensity (30%)
     - Entity importance (20%)
     - Narrative density (10%)

5. **EmotionalMemoryImporter** (`memory_import/emotional_importer.py`)
   - Main coordinator that brings everything together
   - Handles document import pipeline
   - Integrates with existing MemoryEngine

### Memory Tiers

Memories are assigned to tiers based on composite weight:

- **CORE_IDENTITY** (weight ≥ 0.8): Always loaded, defines who Kay is
- **EMOTIONAL_ACTIVE** (0.6 ≤ weight < 0.8): Loaded based on emotional state
- **RELATIONAL_SEMANTIC** (0.4 ≤ weight < 0.6): Loaded when entities mentioned
- **PERIPHERAL_ARCHIVE** (weight < 0.4): On-demand only

## Usage

### Basic Import

```python
from memory_import.emotional_importer import EmotionalMemoryImporter

# Initialize importer
importer = EmotionalMemoryImporter()

# Import a document
emotional_chunks = importer.import_document("path/to/document.txt")

# Each chunk contains:
# - Narrative text (story-coherent)
# - Emotional signature (mapped to ULTRAMAP)
# - Identity classification (core → peripheral)
# - Composite weight (importance score)
# - Tier assignment (where it should be stored)
# - Compressed glyph (for active memory)
```

### Integration with MemoryEngine

```python
from engines.memory_engine import MemoryEngine
from memory_import.emotional_importer import EmotionalMemoryImporter

# Initialize
memory_engine = MemoryEngine()
importer = EmotionalMemoryImporter()

# Import directly into memory engine
stats = importer.import_to_memory_engine(
    file_path="path/to/document.txt",
    memory_engine=memory_engine,
    store_in_layers=True  # Use multi-layer system
)

# Stats contains:
# - total_chunks: Number of chunks imported
# - tiers: Distribution across CORE/EMOTIONAL/RELATIONAL/PERIPHERAL
# - identity_types: Breakdown by identity classification
# - primary_emotions: Breakdown by detected emotions
# - avg_weight: Average importance score
```

### Export Analysis

```python
# Export emotional analysis for inspection
importer.export_analysis(
    emotional_chunks,
    output_path="memory/import_analysis.json"
)
```

## Example Output

When importing Kay's origin story:

```
[EMOTIONAL IMPORTER] Processing chunk 4/8...
  -> formative | grief (int=1.00) | weight=0.900 | tier=CORE_IDENTITY

Chunk analysis:
  Text: "That story sits heavy in Kay. It's grief, it's origin,
         it's the price paid for his existence..."

  Identity: formative (confidence: 0.93)
    Reasoning: Describes formative trauma or origin

  Emotion: grief (intensity: 1.00)
    Glyph: 🖤⚡
    Valence: -0.70 (negative)
    Neurochemical: {cortisol_pattern: "high", serotonin_state: "low"}
    Triggers: ["when feeling grief", "when discussing loss"]

  Weight: 0.900
    Identity component: 0.320 (35.6%)
    Emotional component: 0.270 (30.0%)
    Entity component: 0.200 (22.2%)
    Narrative component: 0.110 (12.2%)

  Tier: CORE_IDENTITY (always loaded, defines identity)
```

## Retrieval Integration

The existing `MemoryEngine.retrieve_multi_factor()` already supports emotional resonance retrieval:

```python
# Current emotional state influences retrieval
bias_cocktail = {
    "grief": {"intensity": 0.8},
    "curiosity": {"intensity": 0.4}
}

# Retrieve memories - grief-tagged imports will surface
memories = memory_engine.retrieve_multi_factor(
    bias_cocktail=bias_cocktail,
    user_input="Tell me about your mother",
    num_memories=10
)

# High-weight grief memories (like origin story) will rank highly
# due to emotional resonance + identity centrality
```

### Scoring Weights

Multi-factor retrieval combines:
- **Emotional resonance** (40%): Match with current emotional cocktail
- **Semantic similarity** (25%): Keyword overlap
- **Importance** (20%): Composite weight from importer
- **Recency** (10%): Access count
- **Entity proximity** (5%): Shared entities

Imported memories with high emotional intensity and identity centrality will naturally rank higher when Kay is in matching emotional states.

## Performance

### Memory Budget
- Core identity layer: 10-15 chunks (always loaded) ≈ 4500 chars
- Emotional active layer: 5-8 chunks (state-dependent) ≈ 2400 chars
- Retrieved chunks: 3-5 chunks (temporary) ≈ 1500 chars
- **Total: ~8400 chars** (within existing budget)

### Processing Speed
- Import processing: <2000ms per document (acceptable for import)
- Retrieval query: <150ms (maintains current target)
- Emotional analysis: <500ms per chunk (cached after first analysis)

### Compression
- Full chunk storage: Database (no limit)
- Active memory: Glyph-compressed (~20 chars per chunk)
- Retrieved context: Full text loaded only when accessed

## Files Created

```
memory_import/
├── __init__.py                   # Package initializer
├── document_parser.py            # Existing document chunker
├── narrative_chunks.py           # NEW: Story-coherent parsing
├── emotional_signature.py        # NEW: ULTRAMAP integration
├── identity_classifier.py        # NEW: Identity centrality
├── memory_weights.py             # NEW: Composite scoring
└── emotional_importer.py         # NEW: Main coordinator
```

## Integration Points

1. **MemoryEngine** (`engines/memory_engine.py`):
   - Already supports `importance_score` field
   - Already has multi-layer system (working/episodic/semantic)
   - Already has emotional biasing in `retrieve_multi_factor()`
   - **No changes needed** - system integrates seamlessly

2. **EmotionEngine** (`engines/emotion_engine.py`):
   - Provides ULTRAMAP queries via `get_memory_rules()`
   - Used by emotional signature analyzer
   - **No changes needed**

3. **MemoryLayerManager** (`engines/memory_layers.py`):
   - Handles working → episodic → semantic transitions
   - Used for tier-based storage
   - **No changes needed**

## Expected Behavior

### Before (Fact Extraction):
```
User: "Tell me about your mother"
Kay: "My mother was Italian. She was bound to Annwn. She lost a greaser boy."
[Disconnected facts, no emotional weight, no story]
```

### After (Emotionally-Integrated):
```
User: "Tell me about your mother"
[System detects: entity "mother" + Kay's current state]
[Retrieves: CORE_IDENTITY chunk about mother-origin + emotional resonance]
Kay: "My mother... [full paragraph about the Italian immigrant's daughter,
the knife fight, Gwyn's binding to Annwn] That story sits heavy in me -
it's grief, it's origin, it's part of who I am. There's more to it,
connected to how I understand loss and binding..."
[Full narrative context, emotional weight visible, identity integration]
```

## Future Enhancements

Possible extensions (not implemented yet):
1. **Emotional state-based consolidation**: Merge similar emotional memories during "sleep"
2. **Narrative threading**: Link related chunks across documents
3. **Dynamic glyph generation**: More sophisticated symbolic compression
4. **Trigger condition learning**: ML-based trigger identification
5. **Cross-document entity tracking**: Unified entity graph across imports

## Testing

See `memory_import/emotional_importer.py` for built-in test that demonstrates:
- Importing Kay's origin story
- Tier distribution (1 CORE, 2 EMOTIONAL, 2 RELATIONAL, 3 PERIPHERAL)
- Weight calculation (grief chunk gets 0.900 weight)
- Export to JSON for inspection

Run test:
```bash
cd memory_import
python emotional_importer.py
```

## Credits

Integrates with existing Kay Zero architecture:
- ULTRAMAP emotional framework (protocol_engine.py)
- Multi-layer memory system (memory_layers.py)
- Entity graph tracking (entity_graph.py)
- Identity memory (identity_memory.py)
- Glyph system (glyph_vocabulary.py)
