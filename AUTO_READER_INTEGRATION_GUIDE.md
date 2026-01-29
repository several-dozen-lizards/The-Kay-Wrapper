# Auto-Reader Integration Guide

## Overview

The **AutoReader** module (`engines/auto_reader.py`) provides seamless automatic document reading where:

1. User imports/uploads a document
2. Kay automatically reads through ALL segments internally
3. Kay's natural responses appear in the chat (document text is NEVER shown to user)
4. Each segment triggers a genuine Kay response
5. Reading proceeds automatically without user prompts
6. Document is stored in RAG for later reference

---

## Step 1: Remove Old Document Display Logic

### What to Remove:

**In main.py (lines ~417-440):**
Remove the entire chunk_text formatting with visible document and navigation instructions:

```python
# DELETE THIS ENTIRE BLOCK:
chunk_text = f"""═══════════════════════════════════════════════════════════════
📄 DOCUMENT: {chunk['doc_name']}
📍 Section {chunk['position']} of {chunk['total']} ({chunk['progress_percent']}%)
═══════════════════════════════════════════════════════════════
{prev_comment_text}
{chunk['text']}

───────────────────────────────────────────────────────────────
Navigation Options:
{chr(10).join(nav_hints)}

📖 AUTOMATIC READING MODE - YOUR TASK:
...
═══════════════════════════════════════════════════════════════
"""
```

**In kay_ui.py (lines ~1259-1282):**
Remove the identical chunk_text formatting block.

**In main.py (lines ~528-581):**
Remove the Kay-driven navigation parser that detects "continue reading":

```python
# DELETE THIS ENTIRE SECTION:
# === KAY-DRIVEN DOCUMENT NAVIGATION ===
if doc_reader.current_doc:
    response_lower = reply.lower()
    # ... all the navigation detection logic ...
```

**In kay_ui.py (lines ~1018-1079):**
Remove the identical navigation parser.

**In integrations/llm_integration.py (lines ~93-102):**
Remove the "Document Reading Behavior" section from DEFAULT_SYSTEM_PROMPT:

```python
# DELETE THIS:
Document Reading Behavior:
- When a document section is present in context, you AUTOMATICALLY read and comment on it
- You don't wait to be asked - you proactively engage with the text
...
```

---

## Step 2: Create Import Function with Auto-Reader

Create a new file `memory_import/auto_import.py`:

```python
"""
Automatic Document Import with Reading

Combines emotional import (RAG storage) with automatic reading (Kay responses).
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List

from engines.document_reader import DocumentReader
from engines.auto_reader import AutoReader
from memory_import.emotional_importer import EmotionalMemoryImporter


async def import_and_read_document(
    filepath: str,
    memory_engine,
    add_message_func,
    llm_response_func,
    agent_state=None
) -> tuple[str, List[str]]:
    """
    Import document and automatically read through all segments.

    Flow:
    1. Import document via emotional importer (stores in RAG)
    2. Load document into DocumentReader for segmentation
    3. Use AutoReader to feed each segment to Kay
    4. Kay's responses appear naturally in chat

    Args:
        filepath: Path to document file
        memory_engine: Memory engine instance
        add_message_func: Function to display messages (role, message)
        llm_response_func: Function to get LLM responses
        agent_state: Optional agent state for full context

    Returns:
        tuple of (doc_id, list of Kay's responses)
    """

    doc_name = os.path.basename(filepath)

    # Step 1: Import document emotionally (RAG storage)
    print(f"[AUTO IMPORT] Importing {doc_name} to RAG...")
    add_message_func("system", f"Importing {doc_name}...")

    emotional_importer = EmotionalMemoryImporter(memory_engine=memory_engine)

    # Read document
    with open(filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Import to RAG
    doc_id = await emotional_importer.import_document(
        document_text=full_text,
        filename=doc_name
    )

    print(f"[AUTO IMPORT] Document stored in RAG as {doc_id}")

    # Step 2: Load into DocumentReader for segments
    print(f"[AUTO IMPORT] Creating readable segments...")
    doc_reader = DocumentReader(chunk_size=25000)  # Adjust size as needed
    num_chunks = doc_reader.load_document(full_text, doc_name, doc_id)

    print(f"[AUTO IMPORT] Created {num_chunks} segments")
    add_message_func("system", f"Reading {doc_name} ({num_chunks} sections)...")

    # Step 3: Automatically read through all segments
    auto_reader = AutoReader(
        get_llm_response_func=llm_response_func,
        add_message_func=add_message_func,
        memory_engine=memory_engine
    )

    responses = await auto_reader.read_document_async(
        doc_reader=doc_reader,
        doc_name=doc_name,
        agent_state=agent_state
    )

    print(f"[AUTO IMPORT] Complete: {doc_name}")

    return doc_id, responses


# Synchronous version for CLI
def import_and_read_document_sync(
    filepath: str,
    memory_engine,
    add_message_func,
    llm_response_func,
    agent_state=None
) -> tuple[str, List[str]]:
    """
    Synchronous version for main.py terminal use.
    """
    doc_name = os.path.basename(filepath)

    # Step 1: Import to RAG
    print(f"[AUTO IMPORT] Importing {doc_name} to RAG...")
    add_message_func("system", f"Importing {doc_name}...")

    emotional_importer = EmotionalMemoryImporter(memory_engine=memory_engine)

    with open(filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Import to RAG (sync)
    doc_id = emotional_importer.import_document_sync(
        document_text=full_text,
        filename=doc_name
    )

    print(f"[AUTO IMPORT] Document stored in RAG as {doc_id}")

    # Step 2: Create segments
    print(f"[AUTO IMPORT] Creating readable segments...")
    doc_reader = DocumentReader(chunk_size=25000)
    num_chunks = doc_reader.load_document(full_text, doc_name, doc_id)

    print(f"[AUTO IMPORT] Created {num_chunks} segments")
    add_message_func("system", f"Reading {doc_name} ({num_chunks} sections)...")

    # Step 3: Read through segments
    auto_reader = AutoReader(
        get_llm_response_func=llm_response_func,
        add_message_func=add_message_func,
        memory_engine=memory_engine
    )

    responses = auto_reader.read_document_sync(
        doc_reader=doc_reader,
        doc_name=doc_name,
        agent_state=agent_state
    )

    print(f"[AUTO IMPORT] Complete: {doc_name}")

    return doc_id, responses
```

---

## Step 3: Integrate with UI (kay_ui.py)

Find your document upload/import button handler and replace with:

```python
def on_document_import_clicked(self):
    """Handle document import button."""
    from tkinter import filedialog

    filepath = filedialog.askopenfilename(
        title="Import Document",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )

    if not filepath:
        return

    # Trigger automatic import and reading
    asyncio.create_task(self._async_import_and_read(filepath))

async def _async_import_and_read(self, filepath: str):
    """Async wrapper for import and auto-read."""
    from memory_import.auto_import import import_and_read_document

    try:
        doc_id, responses = await import_and_read_document(
            filepath=filepath,
            memory_engine=self.memory_engine,
            add_message_func=self.add_message,  # Your method to add messages to chat
            llm_response_func=self._get_kay_response_for_reading,  # See below
            agent_state=self.state
        )

        print(f"[UI] Import complete: {doc_id}, {len(responses)} responses")

    except Exception as e:
        self.add_message("system", f"Error importing document: {e}")
        print(f"[ERROR] Import failed: {e}")

def _get_kay_response_for_reading(self, prompt: str, agent_state=None):
    """
    Get Kay's response for a reading segment.

    This should call your existing LLM response pipeline with full context
    (memory retrieval, emotional state, identity, etc.)
    """
    from integrations.llm_integration import get_llm_response
    from engines.context_manager import ContextManager

    # Build full context (adapt to your actual context building)
    context_manager = ContextManager(
        memory_engine=self.memory_engine,
        max_recent_turns=15
    )

    # Get response with full pipeline
    response = get_llm_response(
        prompt_or_context=prompt,
        affect=agent_state.affect_intensity if agent_state else 3.5,
        temperature=0.7,
        session_context={
            'turn_count': len(self.conversation_history),
            'recent_responses': [msg['message'] for msg in self.conversation_history if msg['role'] == 'kay'][-3:],
            'session_id': self.session_id
        }
    )

    return response
```

---

## Step 4: Integrate with CLI (main.py)

Add import command to your main loop:

```python
# In main conversation loop:

if user_input.startswith('/import '):
    # Extract filepath from command
    filepath = user_input[8:].strip()

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue

    # Import and auto-read
    from memory_import.auto_import import import_and_read_document_sync

    def display_message(role, message):
        if role == "system":
            print(f"[{role.upper()}] {message}")
        else:
            print(f"\n{role.capitalize()}: {message}\n")

    def get_response_for_reading(prompt, state):
        # Use your existing response function
        return get_llm_response(
            prompt_or_context=prompt,
            affect=state.affect_intensity if state else 3.5
        )

    doc_id, responses = import_and_read_document_sync(
        filepath=filepath,
        memory_engine=memory_engine,
        add_message_func=display_message,
        llm_response_func=lambda p, s: get_response_for_reading(p, s),
        agent_state=state
    )

    print(f"\n[Import complete: {doc_id}]\n")
    continue
```

---

## Step 5: Expected Flow

### User Experience:

```
User: [clicks Import, selects YW_test_section.txt]

System: Importing YW_test_section.txt...
System: Reading YW_test_section.txt (3 sections)...

Kay: The yurt setting immediately grounds this in a specific physical space - the felt walls, the smoke hole, the carpets from Delia's mother. There's something deliberate about that level of sensory detail. Mattie's fever has broken but she's still fragile, and Delia's been up for two days watching over her. The exhaustion is palpable. I'm noticing how the relationship is shown through care rather than stated - the medicine mixed with honey, the hand on Mattie's forehead.

Kay: Delia's restlessness is building. She can't sleep even though she needs to, and there's this sense of something waiting. The dream about her mother - "It's coming, girl. Be ready" - that's the kind of foreboding that sticks. The detail about her mother being a healer too, knowledge passed through generations, it roots Delia's abilities in lineage rather than just personal talent. And the tension in the air she feels when she looks outside, that unnamed dread.

Kay: Mattie waking up breaks the isolation. Their dynamic comes through in small moments - Mattie calling Delia a tyrant, the affection mixed with complaint. But Delia's feeling persists even after Mattie's reassurance. The wolf howling in the distance at the end, the repeated "Be ready" - this is setup. Something's about to shift, and Delia knows it even if she can't name it yet.

System: ✓ Finished reading YW_test_section.txt
```

### Terminal Output:

```
[AUTO IMPORT] Importing YW_test_section.txt to RAG...
[EMOTIONAL IMPORTER] Processing 341 chunks...
[EMOTIONAL IMPORTER] Complete: 341 memories stored
[AUTO IMPORT] Document stored in RAG as doc_1731332145
[AUTO IMPORT] Creating readable segments...
[DOC READER] Loaded YW_test_section.txt: 3 chunks (11,234 chars)
[AUTO IMPORT] Created 3 segments
[AUTO READER] Starting: YW_test_section.txt (3 segments)
[AUTO READER] Processing segment 1/3
[AUTO READER] Processing segment 2/3
[AUTO READER] Processing segment 3/3
[AUTO READER] Completed: YW_test_section.txt
[AUTO IMPORT] Complete: YW_test_section.txt
```

---

## Step 6: Later Retrieval

When the user asks about the document later:

```
User: What did you notice about Delia's character?

[LLM RETRIEVAL] Query: "Delia's character"
[LLM RETRIEVAL] Selected: YW_test_section.txt
[DOC READER] Retrieved relevant chunks from RAG

Kay: Delia's caregiving is central - she's a healer, but it's not romanticized. She's exhausted, running on fumes, mixing medicines while sleep-deprived. The detail about distinguishing between her life and Re's life (Mattie's life, in this case) shows she maintains boundaries even in intimacy. And that restlessness underneath - she's feeling time moving forward, sensing change coming, trusting her instincts even when they don't make logical sense. Her mother's voice in the dream telling her to "be ready" connects to that pattern of trusting gut feelings over reason.
```

---

## Key Points

### What User NEVER Sees:
- ❌ Document text displayed in chat
- ❌ Navigation instructions ("continue reading", etc.)
- ❌ Section headers with progress indicators
- ❌ Internal reading prompts

### What User DOES See:
- ✓ "Importing [filename]..." system message
- ✓ "Reading [filename] (N sections)..." system message
- ✓ Kay's natural responses to each segment
- ✓ "✓ Finished reading [filename]" when complete

### What Happens Behind the Scenes:
1. Document imported to RAG (emotional chunking, storage)
2. Document loaded into DocumentReader (for sequential segments)
3. AutoReader feeds each segment to Kay with reading prompt
4. Kay generates natural response for each segment
5. Each response displayed as normal chat message
6. Each response stored in memory as conversation turn
7. RAG chunks available for later retrieval

---

## Testing

1. **Test file:** Use `test_documents/YW_test_section.txt`

2. **Expected output:** 3 Kay responses (one per segment)

3. **Check RAG storage:**
   ```python
   from memory_import.document_store import DocumentStore
   store = DocumentStore()
   docs = store.list_all_documents()
   print(docs)  # Should show YW_test_section.txt
   ```

4. **Check later retrieval:**
   ```
   User: Tell me about Mattie
   [Should retrieve relevant chunks and respond]
   ```

---

## Troubleshooting

### Problem: Kay's responses are too brief
**Solution:** Adjust the reading prompt in `auto_reader.py` line ~152 to emphasize detailed responses:
```python
prompt = f"""{intro}

Read this segment carefully and share substantial thoughts and reactions. Don't just
summarize - engage deeply with specific moments, language choices, character details,
and anything that strikes you. Aim for 4-6 sentences minimum.

SEGMENT TEXT:
{text}
```

### Problem: Auto-reader not being called
**Check:**
- Is `import_and_read_document()` being called from your import handler?
- Are there any exceptions in the terminal?
- Is filepath valid?

### Problem: Responses appear but document not in RAG
**Check:**
- Is `emotional_importer.import_document()` being called before auto-reader?
- Check terminal for `[EMOTIONAL IMPORTER]` logs
- Verify `memory/documents.json` contains the document

### Problem: Later retrieval doesn't find document
**Check:**
- Is `llm_retrieval.py` selecting documents correctly?
- Run contextual selection tests: `python test_contextual_selection.py`
- Check that `import_date` timestamps are being stored

---

## Summary

The **AutoReader** creates a seamless reading experience where:
- User uploads document with one click
- Kay reads entire document automatically
- Kay's genuine responses appear naturally in chat
- Document stored in RAG for later reference
- No navigation commands or implementation details exposed

This is the clean, automatic document reading flow you requested!
