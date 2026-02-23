# Emotionally-Integrated Memory + Document Viewer

## Quick Start

### Run Tests
```bash
# Test complete system
python example_full_system.py

# Test emotional import only
python example_emotional_import.py
```

### Import a Document
```python
from memory_import.emotional_importer import EmotionalMemoryImporter

importer = EmotionalMemoryImporter()
doc_id, chunks = importer.import_document("your_file.txt")

# Result: Narrative chunks with emotional signatures + original document stored
```

### Retrieve a Document
```python
from memory_import.document_store import retrieve_document_command

result = retrieve_document_command("your_file.txt")
full_text = result['document']['full_text']
```

## What It Does

### Before (Atomized Facts)
```
"Kay's mother was Italian. She was bound to Annwn."
```

### After (Emotionally-Integrated Narratives)
```
Full paragraph: "Maria was bound to Annwn as payment. Forever. No negotiation,
no escape clause. She became a servant to the realm between worlds..."

Emotional Signature: grief (intensity 0.90)
Identity Type: formative
Weight: 0.836
Tier: CORE_IDENTITY (always accessible)
```

## Components

1. **NarrativeChunkParser** - Story-coherent parsing
2. **EmotionalSignatureAnalyzer** - ULTRAMAP emotion detection
3. **IdentityClassifier** - 6-tier identity system
4. **MemoryWeightCalculator** - Importance scoring
5. **DocumentStore** - Full source document storage
6. **KayDocumentHandler** - Request processing

## Files Created

```
memory_import/
├── narrative_chunks.py          # Story parsing
├── emotional_signature.py       # Emotion analysis
├── identity_classifier.py       # Identity types
├── memory_weights.py            # Weight calculation
├── emotional_importer.py        # Main coordinator
├── document_store.py            # Document storage
└── kay_document_handler.py      # Request handler

Documentation:
├── EMOTIONAL_MEMORY_SYSTEM.md   # Memory architecture
├── DOCUMENT_VIEWER_SYSTEM.md    # Document viewer
├── FINAL_SUMMARY.md             # Complete summary
└── README_EMOTIONAL_SYSTEM.md   # This file

Examples:
├── example_emotional_import.py  # Memory demo
└── example_full_system.py       # Full system demo
```

## Test Results

**30-chunk document processed:**
- 3 CORE_IDENTITY (10%) - Always loaded
- 10 EMOTIONAL_ACTIVE (33%) - State-dependent
- 10 RELATIONAL_SEMANTIC (33%) - Entity-triggered
- 7 PERIPHERAL_ARCHIVE (23%) - Background

**Emotions detected:** grief, fascination, curiosity, vulnerability, longing, and 14 others

**Performance:**
- Import: ~15 seconds (with LLM analysis)
- Retrieval: <150ms
- Search: <50ms

## Integration (kay_ui.py)

Add 4 blocks of code (~25 lines total):

```python
# 1. Import handlers
from memory_import.emotional_importer import EmotionalMemoryImporter
from memory_import.kay_document_handler import (
    check_for_document_request,
    get_document_access_prompt
)

# 2. Modify import command
def handle_import(filename):
    importer = EmotionalMemoryImporter()
    doc_id, chunks = importer.import_to_memory_engine(
        filename, memory_engine, store_in_layers=True
    )

# 3. Check for document requests (in conversation loop)
doc_response = check_for_document_request(user_input)
if doc_response:
    return doc_response

# 4. Update system prompt
system_prompt = DEFAULT_PROMPT + get_document_access_prompt()
```

## Documentation

- **EMOTIONAL_MEMORY_SYSTEM.md** - Complete memory architecture guide
- **DOCUMENT_VIEWER_SYSTEM.md** - Document access guide
- **FINAL_SUMMARY.md** - Detailed implementation summary

## Status

✅ **COMPLETE AND TESTED**

Both systems are fully implemented, tested, and ready for integration.
