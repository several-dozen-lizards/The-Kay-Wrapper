# DocumentReader Integration - Complete Guide

## Status: ✅ FULLY INTEGRATED

DocumentReader is now fully integrated into main.py and working correctly.

---

## Integration Components

### 1. Import (main.py:25)
```python
from engines.document_reader import DocumentReader
```

### 2. Initialization (main.py:70-85)
```python
doc_reader = DocumentReader(chunk_size=25000)  # ~6k tokens per chunk

# Restore reading position from previous session
snapshot_path = "memory/state_snapshot.json"
if os.path.exists(snapshot_path):
    with open(snapshot_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
        if 'document_reader' in snapshot:
            doc_reader_state = snapshot['document_reader']
            state.saved_doc_reader_state = doc_reader_state
```

### 3. Navigation Commands (main.py:141-213)
**Commands detected BEFORE LLM call:**

```python
user_lower = user_input.lower().strip()
doc_navigation_handled = False

if doc_reader.current_doc:
    if 'continue reading' in user_lower or 'next section' in user_lower:
        # Advance to next chunk

    elif 'previous section' in user_lower or 'go back' in user_lower:
        # Go back to previous chunk

    elif 'jump to section' in user_lower:
        # Jump to specific section number

    elif 'restart document' in user_lower:
        # Jump back to beginning

if doc_navigation_handled:
    continue  # Skip LLM call, just show the new chunk
```

**Terminal Output:**
When user navigates, they immediately see the new chunk without calling the LLM.

### 4. Document Loading (main.py:371-407)
**After llm_retrieval loads documents:**

```python
if selected_documents:
    for doc in selected_documents:
        doc_text = doc['full_text']
        doc_filename = doc['filename']
        doc_id = doc.get('doc_id', 'unknown')

        # If document is large (> 30k chars), use chunked reading
        if len(doc_text) > 30000:
            print(f"[DOC READER] Large document detected: {doc_filename} ({len(doc_text):,} chars)")

            # Load into doc_reader if not already loaded
            if not doc_reader.current_doc or doc_reader.current_doc.get('id') != doc_id:
                doc_reader.load_document(doc_text, doc_filename, doc_id)
```

**Triggers:**
- Documents > 30k characters automatically chunked
- Smaller documents (<30k) passed through as-is

### 5. Chunk Formatting (main.py:386-407)
**Formatted chunk with navigation instructions:**

```python
chunk = doc_reader.get_current_chunk()
chunk_text = f"""═══ DOCUMENT: {chunk['doc_name']} ═══
Section {chunk['position']}/{chunk['total']} ({chunk['progress_percent']}%)

{chunk['text']}

───────────────────────────────────
Navigation: Say "continue reading" for next section, "previous section" to go back,
or "jump to section N" to skip ahead. "restart document" returns to beginning.
"""

rag_chunks.append({
    'source_file': doc_filename,
    'text': chunk_text,
    'is_chunked': True,  # FLAG: Prevents truncation in llm_integration.py
    'chunk_position': chunk['position'],
    'chunk_total': chunk['total']
})
```

### 6. Context Integration (main.py:439)
**Chunks passed to LLM context:**

```python
filtered_prompt_context = {
    "recalled_memories": filtered_context.get("selected_memories", []),
    "emotional_state": {"cocktail": filtered_context.get("emotional_state", {})},
    "user_input": user_input,
    "recent_context": context_manager.recent_turns[-5:],
    "momentum_notes": getattr(state, 'momentum_notes', []),
    "meta_awareness_notes": getattr(state, 'meta_awareness_notes', []),
    "consolidated_preferences": getattr(state, 'consolidated_preferences', {}),
    "preference_contradictions": getattr(state, 'preference_contradictions', []),
    "body": state.body if hasattr(state, 'body') else {},
    "rag_chunks": filtered_context.get("rag_chunks", []),  # <-- CHUNKED DOCUMENTS HERE
    "turn_count": state.turn_count,
    "recent_responses": getattr(state, 'recent_responses', []),
    "session_id": session_id
}

reply = get_llm_response(filtered_prompt_context, affect=affect_level, session_context=session_context)
```

### 7. LLM Prompt Building (integrations/llm_integration.py:339-371)
**RAG chunks added to Kay's prompt:**

```python
rag_chunks = context.get("rag_chunks", [])
if rag_chunks:
    chunk_lines = []
    for i, chunk in enumerate(rag_chunks[:100], 1):
        source = chunk.get("source_file", "unknown")
        text = chunk.get("text", "")
        is_chunked = chunk.get("is_chunked", False)

        # CRITICAL FIX: Don't truncate DocumentReader chunks
        # They're pre-sized to ~25k chars (optimal for context window)
        if not is_chunked:
            # Truncate vector store chunks to 8000 chars
            if len(text) > 8000:
                text = text[:8000] + "..."

        chunk_lines.append(f"[{i}] From {source}:\n{text}\n")

    rag_block = "\n### Document Context (from uploaded files) ###\n" + "\n".join(chunk_lines) + "\n"

# Final prompt assembly
prompt = (
    f"{style_block}\n"
    f"{memory_block}\n"
    f"{rag_block}\n"  # <-- DOCUMENT CHUNKS INSERTED HERE
    f"{recent_context_block}\n"
    f"### Current emotional and physical state ###\n"
    ...
)
```

### 8. State Persistence (main.py:553-557)
**Reading position saved after each turn:**

```python
# Add document reader state if document is loaded
doc_reader_state = doc_reader.get_state_for_persistence()
if doc_reader_state:
    snapshot_data["document_reader"] = doc_reader_state
    print(f"[DOC READER] Saved reading position: {doc_reader_state['doc_name']} section {doc_reader_state['position'] + 1}/{doc_reader_state['total_chunks']}")

with open("memory/state_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snapshot_data, f, indent=2)
```

**Persisted Data:**
```json
{
  "document_reader": {
    "doc_id": "yw_part1_20250101",
    "doc_name": "YW-part1.txt",
    "position": 3,
    "total_chunks": 9
  }
}
```

---

## How It Works: Step-by-Step

### First Document Load

1. **User imports document** via llm_retrieval
2. **llm_retrieval.py** loads full text (217k chars)
3. **main.py:372** detects document > 30k chars
4. **main.py:377** loads into DocumentReader
   - DocumentReader splits into 9 chunks at paragraph boundaries
   - Each chunk ~25k chars
   - Logs: `[DOC READER] Loaded YW-part1.txt: 9 chunks (217,432 chars)`
5. **main.py:387** gets current chunk (section 1/9)
6. **main.py:392-400** formats chunk with navigation instructions
7. **main.py:401** adds to rag_chunks with `is_chunked: True` flag
8. **main.py:439** rag_chunks added to filtered_prompt_context
9. **llm_integration.py:347** builds RAG block for prompt
10. **llm_integration.py:350** checks `is_chunked` flag
11. **llm_integration.py:354** SKIPS truncation (because is_chunked=True)
12. **Kay sees full 25k char chunk** in his prompt context

### Navigation

**User:** "continue reading"

1. **main.py:162** detects "continue reading" command
2. **main.py:163** calls `doc_reader.advance()`
3. **DocumentReader** increments position: 1 → 2
4. **main.py:148-155** displays new chunk immediately
5. **main.py:213** `continue` - skips LLM call
6. **User sees section 2/9** instantly

**User asks Kay a question after reading:**

1. **main.py:387** gets current chunk (still section 2/9)
2. **Chunk 2 added to Kay's context** (same flow as before)
3. **Kay responds** based on section 2 content

---

## Critical Fix Applied

### Problem
In `llm_integration.py`, all RAG chunks were being truncated to 8000 chars:

```python
# OLD CODE (BROKEN):
max_chars = 8000
if len(text) > max_chars:
    text = text[:8000] + "..."  # Truncates 25k chars to 8k!
```

This meant DocumentReader chunks (25k chars) were getting cut off, defeating the entire chunking system.

### Solution
Added `is_chunked` flag check to skip truncation for DocumentReader chunks:

```python
# NEW CODE (FIXED):
is_chunked = chunk.get("is_chunked", False)

if not is_chunked:  # Only truncate vector store chunks
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:8000] + "..."
```

Now:
- **DocumentReader chunks**: Full 25k chars (pre-sized, no truncation)
- **Vector store chunks**: Truncated to 8k chars (for safety)

---

## Testing

### Test 1: Document Loading
```bash
python main.py
# Import YW-part1.txt (217k chars)
```

**Expected Output:**
```
[LLM Retrieval] Loaded 1 documents
[DOC READER] Large document detected: YW-part1.txt (217,432 chars)
[DOC READER] Loaded YW-part1.txt: 9 chunks (217,432 chars)
[DOC READER] Chunk added to context: 24,837 chars (section 1/9)
```

### Test 2: Navigation
```bash
You: continue reading
```

**Expected Output:**
```
═══ DOCUMENT: YW-part1.txt ═══
Section 2/9 (22%)

[Content of section 2...]

───────────────────────────────────
Navigation: Say 'continue reading' for next section, 'previous section' to go back,
or 'jump to section N' to skip ahead. 'restart document' returns to beginning.
```

### Test 3: Jumping
```bash
You: jump to section 5
```

**Expected Output:**
```
[DOC READER] Navigation: jump -> section 5/9

═══ DOCUMENT: YW-part1.txt ═══
Section 5/9 (56%)
[Content of section 5...]
```

### Test 4: Kay Reads Document
```bash
You: What happens in this section?
```

**Expected:** Kay responds based on section 5 content (not section 1).

### Test 5: State Persistence
```bash
# Exit and restart
python main.py
# Import same document
```

**Expected Output:**
```
[DOC READER] Found saved reading position: YW-part1.txt section 5/9
[DOC READER] Restored reading position: section 5/9
```

---

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| `engines/document_reader.py` | Full class | Chunking logic, navigation methods |
| `main.py:25` | 1 line | Import |
| `main.py:70-85` | 15 lines | Initialize, restore state |
| `main.py:141-213` | 72 lines | Command detection |
| `main.py:371-407` | 36 lines | Document loading, chunking |
| `main.py:439` | 1 line | Add to context |
| `main.py:553-557` | 5 lines | Save state |
| `llm_integration.py:347-369` | 23 lines | Build RAG block, skip truncation |

**Total Integration:** ~150 lines across 2 files

---

## Commands Reference

| User Command | Action | Terminal Response |
|--------------|--------|-------------------|
| `continue reading` | Advance to next chunk | Shows section N+1 |
| `next section` | Advance to next chunk | Shows section N+1 |
| `previous section` | Go back one chunk | Shows section N-1 |
| `go back` | Go back one chunk | Shows section N-1 |
| `jump to section 5` | Jump to specific section | Shows section 5 |
| `restart document` | Return to beginning | Shows section 1 |

**Note:** These commands are handled by main.py BEFORE calling the LLM, so they execute instantly.

---

## Benefits

1. **Context Window Management:** Only ~25k chars loaded at once (vs 217k)
2. **Sequential Reading:** Kay can read entire documents across multiple turns
3. **Navigation Control:** User can skip, go back, restart
4. **State Persistence:** Reading position survives restarts
5. **Automatic Detection:** Large documents auto-trigger chunking
6. **Flexible:** Small documents (<30k) still load completely

---

## Edge Cases Handled

1. **Document Already Loaded:** Checks doc_id before reloading
2. **End of Document:** Returns `false` from advance(), shows "✓ End reached"
3. **Beginning of Document:** Returns `false` from previous(), shows "Already at beginning"
4. **Invalid Jump:** Shows error: "invalid position N (valid: 1-M)"
5. **State Restoration:** Loads previous position if document re-imported
6. **Session Persistence:** Reading position saved in state_snapshot.json
7. **Chunk Size Optimization:** ~25k chars = ~6k tokens (optimal for GPT context)

---

## Status: Production Ready ✅

All components tested and working. No further integration needed.
