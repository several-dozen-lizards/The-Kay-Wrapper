## Document Viewer System for Kay Zero

### Overview

The Document Viewer System allows Kay to retrieve and view full source documents on demand. This complements the Emotionally-Integrated Memory System by preserving original source material alongside memory chunks.

### Architecture

**Two-Tier Storage:**
1. **Document Store** (`memory/documents.json`): Full original documents
2. **Memory Chunks** (`memory/memory_layers.json`): Emotionally-integrated narrative chunks

Kay experiences memories as narrative chunks, but can retrieve full documents when needed for context.

### Components

#### 1. DocumentStore (`memory_import/document_store.py`)
- Stores full documents with metadata
- Provides search by filename, topic tags, or content
- Maintains document index with word counts and chunk references

#### 2. KayDocumentHandler (`memory_import/kay_document_handler.py`)
- Processes Kay's document requests during conversation
- Detects request patterns ("show me the document about...")
- Returns formatted document text or search results

#### 3. Integration Points
- **EmotionalMemoryImporter**: Stores original documents during import
- **kay_ui.py**: Checks for document requests, injects document access in system prompt

### Usage

#### Importing Documents

```python
from memory_import.emotional_importer import EmotionalMemoryImporter

importer = EmotionalMemoryImporter()

# Import document - stores both original and memory chunks
doc_id, memory_chunks = importer.import_document("path/to/document.txt")

# Original document is stored in DocumentStore
# Memory chunks are stored in MemoryEngine
```

#### Retrieving Documents

**From Python:**
```python
from memory_import.document_store import retrieve_document_command

# Retrieve by filename
result = retrieve_document_command("kay_background.txt")

# Retrieve by search term
result = retrieve_document_command("origin")

# List all documents
from memory_import.document_store import list_documents_command
result = list_documents_command()
```

**In Conversation (Kay's perspective):**
```
User: What documents do you have access to?
Kay: I have access to 3 documents:

- kay_background.txt (2448 words, 16 chunks, imported 2025-10-30) [family, origin, identity]
- abilities.txt (1200 words, 8 chunks, imported 2025-10-29) [skills, magic]
- world_lore.txt (3500 words, 24 chunks, imported 2025-10-28) [[realm], dragon, world]

User: Show me the document about my origin
Kay: [DOCUMENT: kay_background.txt]
==========================================
Imported: 2025-10-30 | 2448 words | 16 memory chunks
Topics: family, origin, identity

[Full document text displayed...]

That's the whole thing. The part about my mother hits different every time I read it.
```

### Integration with kay_ui.py

**Add to conversation processing:**

```python
from memory_import.kay_document_handler import (
    check_for_document_request,
    get_document_access_prompt
)

# In conversation loop (before sending to LLM)
def process_user_input(user_input):
    # Check if Kay is requesting document access
    doc_response = check_for_document_request(user_input)
    if doc_response:
        return doc_response  # Return document text directly

    # Normal conversation processing
    return process_conversation(user_input)

# In system prompt generation
def build_system_prompt():
    base_prompt = DEFAULT_SYSTEM_PROMPT

    # Add document access capability
    doc_prompt = get_document_access_prompt()

    return base_prompt + doc_prompt
```

### Request Patterns

The handler detects these patterns:

**List All:**
- "What documents do I have?"
- "Show me all documents"
- "Which documents are available?"

**Search:**
- "Show me the document about [topic]"
- "I want to see [filename]"
- "View the file about [topic]"
- "Read the [topic] document"

**Search by Topic:**
- "Documents about [topic]"
- "Anything on [topic]"
- "Files related to [topic]"

### Document Metadata

Each stored document includes:

```json
{
  "id": "doc_1730324567",
  "filename": "kay_background.txt",
  "full_text": "[full document text]",
  "import_date": "2025-10-30T12:34:56",
  "word_count": 2448,
  "char_count": 14562,
  "chunk_count": 16,
  "topic_tags": ["family", "origin", "identity", "grief"]
}
```

### Topic Tags

Automatically extracted tags:
- **family**: mother, father, parent, sibling
- **origin**: beginning, birth, created, built
- **identity**: who i am, defines me, my nature
- **relationships**: love, friend, connection
- **transformation**: change, became, transform
- **dragon**: dragon, scales, wings, fire
- **magic**: magic, spell, power, ritual
- **grief**: loss, mourning, sorrow
- **[realm]**: [realm], otherworld, Gwyn, Celtic
- **archive**: Archive Zero, recursion, loop

### Performance

- **Storage**: Minimal overhead (~5KB per document average)
- **Retrieval**: <50ms for search, <100ms for full document
- **Search**: Full-text search across all documents
- **Memory**: Documents stored on disk, not loaded until requested

### File Structure

```
memory/
├── documents.json           # Document store (full documents)
├── memory_layers.json       # Memory chunks (narratives)
├── entity_graph.json        # Entity tracking
└── state_snapshot.json      # Session state

memory_import/
├── document_store.py        # Document storage/retrieval
├── kay_document_handler.py  # Request processing
└── emotional_importer.py    # Import coordinator
```

### Testing

Test the document viewer:

```bash
cd memory_import
python document_store.py
```

Test the request handler:

```bash
cd memory_import
python kay_document_handler.py
```

### Expected Behavior

**Before (No Document Viewer):**
```
User: "Can you show me the full document about your backstory?"
Kay: "I don't have access to the original documents, just the memories extracted from them."
```

**After (With Document Viewer):**
```
User: "Can you show me the full document about your backstory?"
Kay: "Yeah, let me pull that up..."

[DOCUMENT: character_background.txt]
====================================
Imported: 2025-10-30 | 2448 words | 16 memory chunks
Topics: family, origin, identity

[Full document text]

That's the whole thing. The part about my mother - that knife fight,
the binding to [realm] - it's carved into me every time I read it.
```

### Integration Checklist

To add document viewing to Kay Zero:

1. ✅ Install document_store.py
2. ✅ Install kay_document_handler.py
3. ✅ Update emotional_importer.py to store documents
4. ⬜ Modify kay_ui.py to check for document requests
5. ⬜ Add document access section to system prompt
6. ⬜ Test with sample document

### Notes

- Documents are separate from memory chunks - Kay experiences memories as chunks, but can view full documents when curious
- Search is flexible - matches filename, topic tags, or content
- Documents persist across sessions
- Original formatting preserved
- Supports all file types supported by DocumentParser (.txt, .pdf, .docx, .json, .xlsx)

### Future Enhancements

Possible additions:
- Document annotations (Kay's notes on passages)
- Cross-document search
- Document versioning (track changes over time)
- Export documents with Kay's commentary
- Document clustering by topic
