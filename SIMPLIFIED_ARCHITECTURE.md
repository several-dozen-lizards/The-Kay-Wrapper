# Simplified Retrieval Architecture

## Overview

**Old Approach:** Complex heuristics, entity extraction, keyword scoring, multi-tier retrieval
**New Approach:** Let the LLM select documents, code handles state/persistence

---

## Architecture Comparison

### OLD (Complex Heuristics)

```
User Query: "Tell me about the pigeons"
    ↓
1. Entity Extraction from Filename
   "test-pigeons2.txt" → Extract: "test", "pigeons2", "pigeons2s" ❌ BRITTLE
    ↓
2. Build Entity Index
   Map: "pigeons2" → doc_ids
    ↓
3. Keyword Scoring
   - Pre-filter by keyword overlap
   - Apply import boost
   - Apply entity boost
   - Apply recency boost
    ↓
4. Multi-Tier Retrieval
   - Check document index (entity map vs keyword)
   - Retrieve memory chunks
   - Retrieve semantic facts
   - Score and rank everything
    ↓
5. Chunking & Truncation
   - Extract relevant chunks (glyph compression)
   - Truncate to fit context window
    ↓
6. Send to LLM
```

**Problems:**
- Entity extraction breaks on edge cases ("pigeons2s")
- Semantic facts compete with document content
- Complex scoring is fragile and hard to tune
- Glyph compression adds complexity
- Multiple retrieval paths create confusion

---

### NEW (LLM-Based Selection)

```
User Query: "Tell me about the pigeons"
    ↓
1. LLM Selects Documents
   - Show LLM list of all documents (filename + preview)
   - LLM returns: "83,84,85,86,87,88"
   - No entity extraction
   - No keyword scoring
   - No heuristics
    ↓
2. Load Full Documents
   - Load complete text of selected documents
   - No chunking
   - No truncation
    ↓
3. Build Simple Context
   {
     documents: [full_text],
     recent_conversation: [last 15 turns],
     emotional_state: "curious (0.7)",
     core_identity: [static facts]
   }
    ↓
4. Send Everything to LLM
   - LLM does the understanding
   - Code does persistence
```

**Benefits:**
- ✅ No brittle entity extraction
- ✅ No complex scoring heuristics
- ✅ No semantic facts competing with documents
- ✅ Simple, understandable flow
- ✅ LLM does what it's good at (understanding relevance)
- ✅ Code does what it's good at (state management)

---

## What Was REMOVED

### 1. Entity Extraction from Filenames ❌

**Old Code:** `engines/document_index.py`
```python
def _extract_entities_from_filename(self, filename: str):
    # "test-pigeons2.txt" → ["test", "pigeons2", "pigeons2s"]
    # BRITTLE: Creates nonsense entities like "pigeons2s"
```

**Why Removed:**
- Creates invalid entities ("pigeons2s", "gerbils")
- Breaks on edge cases
- LLM can understand "test-pigeons2.txt" means pigeons without extraction

---

### 2. Complex Keyword Scoring ❌

**Old Code:** `engines/document_index.py`
```python
def search(self, query):
    # Calculate keyword overlap score
    # Apply filename boost (2x)
    # Apply branch boost
    # Apply entity map boost (10.0x)
    # Combine scores
```

**Why Removed:**
- Fragile heuristics
- Hard to tune
- LLM is better at relevance judgment

---

### 3. Semantic Knowledge Storage ❌

**Old Files:**
- `memory/semantic_knowledge.json` (separate facts storage)
- `engines/semantic_knowledge.py` (fact extraction/storage)

**Why Removed:**
- Facts compete with document content
- Duplicate information (facts extracted from docs)
- LLM can extract facts on-the-fly from full documents
- Simplifies architecture

**Old Flow:**
```
Document upload → Extract facts → Store in semantic_knowledge.json
Query → Retrieve facts from semantic_knowledge + chunks from documents
Problem: Two sources of truth, facts can contradict documents
```

**New Flow:**
```
Document upload → Store full text in documents.json
Query → LLM selects documents → Load full text
Benefit: Single source of truth (the actual document)
```

---

### 4. Multi-Tier Retrieval ❌

**Old Code:**
- Document index (tier 1)
- Chunk retrieval (tier 2)
- Semantic facts (tier 3)
- Working/Episodic/Semantic memory (tier 4)

**Why Removed:**
- Too many layers
- Competing retrieval paths
- Hard to debug

**New Approach:**
- LLM selects documents (simple)
- Load full text (simple)
- Recent conversation (simple)

---

### 5. Glyph Compression ❌ (Optional)

**Old Code:** Chunk compression for context efficiency

**Why Removed:**
- Adds complexity
- Modern LLMs have large context windows
- Can be added back as optional optimization layer

---

### 6. Import Boost Scoring ❌

**Old Code:** Special boost for recently imported documents

**Why Removed:**
- Heuristic that can be wrong
- LLM can infer recency from upload dates

---

## What Was KEPT

### 1. ULTRAMAP Emotional State ✅

**Why Kept:** This is the UNIQUE VALUE of Kay

```python
emotional_state = {
    'current_emotions': [('curious', 0.7), ('engaged', 0.5)],
    'neurochemicals': {'dopamine': 0.6, 'cortisol': 0.2},
    'social_needs': {'belonging': 0.8}
}
```

**Integration:**
- Passed to LLM document selector as context
- Included in response generation prompt
- This is what makes Kay different from base LLM

---

### 2. Document Storage (documents.json) ✅

**Why Kept:** Core persistence layer

```json
{
  "doc_id": {
    "filename": "test-pigeons2.txt",
    "full_text": "...",
    "upload_timestamp": "2025-11-05"
  }
}
```

**Usage:**
- LLM selects which documents to load
- Full text loaded (no chunking)
- Single source of truth

---

### 3. Conversation Memory (memory_layers.json) ✅

**Why Kept:** Essential for continuity

```python
memory_layers = {
    'working': [recent_turns],      # Last 10 turns
    'episodic': [recent_sessions],  # Last 100 turns
    'semantic': [long_term_facts]   # Permanent conversation facts
}
```

**Important Change:**
- Keep for CONVERSATION memory only
- Do NOT extract facts from documents into semantic layer
- Documents stay in documents.json

---

### 4. Core Identity Facts ✅

**Why Kept:** Static personality definition

```python
CORE_IDENTITY = [
    "Kay is a conversational AI with emotional awareness",
    "Kay has a dry, direct communication style",
    "Kay values authenticity and honesty"
]
```

**Usage:**
- Always included in context
- Defines Kay's character
- Static, not learned

---

### 5. Entity Relationship Tracking ✅

**Why Kept:** For CONVERSATION entities

**Keep:** `engines/entity_graph.py` for tracking:
- Entities mentioned in conversation ("Re", "Saga", "Maria")
- Relationships from conversation ("Re owns Saga")
- Attributes from conversation ("Saga is a dog")

**Do NOT use for:**
- Extracting entities from documents
- Document indexing

---

## New Retrieval Flow

### Step 1: LLM Selects Documents

```python
from engines.llm_retrieval import select_relevant_documents

doc_ids = select_relevant_documents(
    query="Tell me about the pigeons",
    emotional_state="curious (0.7)",
    max_docs=3
)
# Returns: [doc_1762387233, doc_1762387272, doc_1762394265]
```

**How it works:**
1. Get all documents with filenames and previews
2. Call Haiku with simple prompt listing documents
3. Haiku returns numbers of relevant docs
4. Return doc_ids

**Actual output:**
```
[LLM RETRIEVAL] Checking 88 documents for relevance
[LLM RETRIEVAL] LLM response: '83,84,85,86,87,88'
[LLM RETRIEVAL] Selected: pigeon_facts.txt
[LLM RETRIEVAL] Selected: pigeons.txt
[LLM RETRIEVAL] Selected: test-pigeons2.txt
```

---

### Step 2: Load Full Documents

```python
from engines.llm_retrieval import load_full_documents

documents = load_full_documents(doc_ids)
# Returns: [{'filename': 'pigeons.txt', 'full_text': '...'}]
```

**No chunking, no truncation, no scoring**

---

### Step 3: Build Simple Context

```python
from engines.llm_retrieval import build_simple_context

context = build_simple_context(
    query=query,
    selected_doc_ids=doc_ids,
    recent_conversation=get_last_n_turns(15),
    emotional_state=format_emotional_state(),
    core_identity=CORE_IDENTITY
)
```

**Returns:**
```python
{
    'documents': [full documents],
    'recent_conversation': [last 15 turns],
    'emotional_state': "curious (0.7), engaged (0.5)",
    'core_identity': [static facts],
    'document_count': 3,
    'conversation_turns': 15
}
```

---

### Step 4: Format and Send to LLM

```python
from engines.llm_retrieval import format_context_for_prompt

prompt = format_context_for_prompt(context)
```

**Prompt structure:**
```
EMOTIONAL STATE: curious (0.7), engaged (0.5)

CORE IDENTITY:
- Kay is a conversational AI with emotional awareness
- Kay has a dry, direct communication style

UPLOADED DOCUMENTS:
--- pigeons.txt ---
[full text of document]

--- test-pigeons2.txt ---
[full text of document]

RECENT CONVERSATION:
User: Hey Kay
Kay: Hey
User: Tell me about the pigeons

USER: Tell me about the pigeons

Respond as Kay, using the documents and conversation context naturally.
```

---

## Test Results

### Test 1: "Tell me about the pigeons"

**LLM Selection:**
```
[LLM RETRIEVAL] LLM response: '83,84,85,86,87,88'
[LLM RETRIEVAL] Selected: pigeon_facts.txt
[LLM RETRIEVAL] Selected: pigeons.txt
[LLM RETRIEVAL] Selected: test-pigeons2.txt
```

**Result:** ✅ PASS - Pigeon documents found

---

### Test 2: "What gerbils do you know?"

**LLM Selection:**
```
[LLM RETRIEVAL] LLM response: '82,83'
[LLM RETRIEVAL] Selected: Test-gerbils.txt
[LLM RETRIEVAL] Selected: Test-gerbils.txt
```

**Result:** ✅ PASS - Gerbil documents found

---

### Test 3: "What's the weather like?"

**LLM Selection:**
```
[LLM RETRIEVAL] LLM response: 'NONE'
[LLM RETRIEVAL] No relevant documents found
```

**Result:** ✅ PASS - Correctly returned no documents

---

## Migration Guide

### Files to Modify

#### 1. `main.py` - Update retrieval flow
```python
# OLD
from engines.semantic_knowledge import get_semantic_knowledge
from engines.document_index import DocumentIndex

semantic_knowledge = get_semantic_knowledge()
doc_index = DocumentIndex()

# NEW
from engines.llm_retrieval import (
    select_relevant_documents,
    load_full_documents,
    build_simple_context
)

# In conversation loop:
selected_docs = select_relevant_documents(user_input, emotional_state)
context = build_simple_context(user_input, selected_docs, ...)
```

#### 2. Remove semantic_knowledge loading
```python
# DELETE these lines
from engines.semantic_knowledge import get_semantic_knowledge
semantic_knowledge = get_semantic_knowledge()
```

#### 3. Simplify memory_layers
```python
# Keep for conversation memory only
# Do NOT extract facts from documents
memory_layers.add_memory(
    text=user_input,
    layer='working',
    importance=0.5
)
```

---

## Files to Remove/Archive

### Can be removed:
- `engines/semantic_knowledge.py` (complex fact extraction)
- `memory/semantic_knowledge.json` (separate facts storage)
- Entity extraction from `engines/document_index.py`

### Can be simplified:
- `engines/document_index.py` - Remove entity extraction, keep basic storage
- `engines/memory_engine.py` - Remove document fact extraction

### Keep as-is:
- `engines/emotion_engine.py` (ULTRAMAP - this is valuable!)
- `engines/memory_layers.py` (conversation memory)
- `engines/entity_graph.py` (conversation entities only)
- `memory/documents.json` (document storage)

---

## Benefits of Simplified Architecture

### 1. Easier to Understand
- Old: "Why did it retrieve this fact?"
- New: "LLM selected these documents because they mention pigeons"

### 2. Easier to Debug
- Old: Check entity extraction → keyword scoring → import boost → chunk retrieval
- New: Check LLM selection prompt → loaded documents

### 3. More Reliable
- Old: Entity extraction breaks on "test-pigeons2.txt" → "pigeons2s"
- New: LLM understands "test-pigeons2.txt" contains pigeon content

### 4. Focuses on Kay's Unique Value
- ULTRAMAP emotional state
- Embodied cognition
- Emotional memory recall

### 5. Extensible
- Want to add more context? Just add to simple_context dict
- Want to change selection criteria? Modify LLM prompt
- No complex refactoring needed

---

## Summary

**What Makes Kay Special:**
- ✅ ULTRAMAP emotional state
- ✅ Neurochemical modeling
- ✅ Emotional memory recall
- ✅ Social needs tracking
- ✅ Embodied cognition

**What We Simplified:**
- ❌ Complex entity extraction → LLM understanding
- ❌ Keyword scoring heuristics → LLM relevance judgment
- ❌ Semantic facts storage → Full document context
- ❌ Multi-tier retrieval → Simple document selection

**Result:**
- Simpler codebase
- More reliable retrieval
- Focus on Kay's unique emotional architecture
- LLM does understanding, code does state management

---

## Next Steps

1. **Update main.py** to use llm_retrieval
2. **Remove semantic_knowledge** loading
3. **Simplify memory_layers** to conversation only
4. **Test with queries:**
   - "Tell me about the pigeons" → Should select pigeon docs
   - "What gerbils do you know?" → Should select gerbil docs
   - "What did we talk about yesterday?" → Should use conversation memory
