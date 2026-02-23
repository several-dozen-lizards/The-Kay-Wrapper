# Old Retrieval Systems DISABLED

## Changes Made

### ✅ 1. Disabled DocumentIndex in `engines/memory_engine.py`

**Before (lines 11, 43):**
```python
from engines.document_index import DocumentIndex
...
self.document_index = DocumentIndex()
```

**After:**
```python
# DEPRECATED: Old complex document index with entity extraction
# from engines.document_index import DocumentIndex

# NEW: Simple LLM-based document selection
from engines.llm_retrieval import select_relevant_documents, load_full_documents
...
# DEPRECATED: Old complex document index with entity extraction
# self.document_index = DocumentIndex()
# NOW: Use llm_retrieval functions instead
```

---

### ✅ 2. Disabled Semantic Knowledge in `context_filter.py`

**Before (lines 20, 55-56):**
```python
from engines.semantic_knowledge import get_semantic_knowledge
...
self.semantic_knowledge = get_semantic_knowledge()
print("[CONTEXT FILTER] Semantic knowledge integration ENABLED")
```

**After:**
```python
# DEPRECATED: Old semantic knowledge system (facts extracted from documents)
# from engines.semantic_knowledge import get_semantic_knowledge
# NOW: Documents are retrieved via llm_retrieval.py (simpler, more reliable)
...
# DEPRECATED: Old semantic knowledge system
# self.semantic_knowledge = get_semantic_knowledge()
# print("[CONTEXT FILTER] Semantic knowledge integration ENABLED")
# NOW: Documents retrieved via llm_retrieval.py in main.py
```

---

### ✅ 3. Made semantic_knowledge calls safe (line 838, 885-888)

**Added checks:**
```python
# Line 838-839: Safe check for entity extraction
if hasattr(self, 'semantic_knowledge') and self.semantic_knowledge:
    known_entities = self.semantic_knowledge.get_all_entity_names()

# Lines 885-888: Return empty list if semantic_knowledge not loaded
if not hasattr(self, 'semantic_knowledge') or not self.semantic_knowledge:
    print("[SEMANTIC QUERY] DEPRECATED: semantic_knowledge not loaded")
    print("[SEMANTIC QUERY] Documents now retrieved via llm_retrieval.py")
    return []
```

---

## What the Logs Will Now Show

### BEFORE (Old System Active):
```
[STARTUP] Initializing...
[SEMANTIC] Loaded 40 facts from memory/semantic_knowledge.json  ← OLD
[DOCUMENT INDEX] Found 66 tree files                             ← OLD
[DOCUMENT INDEX] Successfully indexed 66 documents               ← OLD
[CONTEXT FILTER] Semantic knowledge integration ENABLED         ← OLD
```

### AFTER (New System Ready):
```
[STARTUP] Initializing...
[SEMANTIC QUERY] DEPRECATED: semantic_knowledge not loaded       ← NEW
[SEMANTIC QUERY] Documents now retrieved via llm_retrieval.py   ← NEW
```

---

## Next Step: Integrate llm_retrieval into main.py

The old systems are now DISABLED, but the NEW system isn't integrated yet.

### Current main.py flow (lines 165-238):
```python
# User input received
user_input = input("You: ").strip()

# Extract and store facts
memory.extract_and_store_user_facts(state, user_input)

# Recall memories
memory.recall(state, user_input)

# Update engines
await update_all(state, [emotion, social, temporal, body, motif], user_input)

# CURRENT: Use glyph filter (now without semantic_knowledge)
glyph_output = context_filter.filter_context(filter_state, user_input)
filtered_context = glyph_decoder.decode(glyph_output, state.__dict__)
filtered_prompt_context = glyph_decoder.build_context_for_kay(...)

# Generate response
reply = get_llm_response(filtered_prompt_context, affect=affect_level, ...)
```

### Recommended NEW flow:
```python
# User input received
user_input = input("You: ").strip()

# Extract and store facts
memory.extract_and_store_user_facts(state, user_input)

# Recall memories
memory.recall(state, user_input)

# Update engines
await update_all(state, [emotion, social, temporal, body, motif], user_input)

# NEW: LLM selects relevant documents
from engines.llm_retrieval import select_relevant_documents, load_full_documents, format_context_for_prompt

emotional_state_str = format_emotional_state(state)
selected_doc_ids = select_relevant_documents(
    query=user_input,
    emotional_state=emotional_state_str,
    max_docs=3
)

# Load full documents
documents = load_full_documents(selected_doc_ids)

# Build simple context
context = {
    'query': user_input,
    'documents': documents,
    'recent_conversation': context_manager.recent_turns,
    'emotional_state': emotional_state_str,
    'core_identity': [static facts]
}

# Format for prompt
filtered_prompt_context = format_context_for_prompt(context)

# Generate response
reply = get_llm_response(filtered_prompt_context, affect=affect_level, ...)
```

---

## Testing

### Step 1: Run main.py and check logs

```bash
python main.py
```

**Expected logs:**
```
[SEMANTIC QUERY] DEPRECATED: semantic_knowledge not loaded
[SEMANTIC QUERY] Documents now retrieved via llm_retrieval.py
```

**You should NOT see:**
```
[SEMANTIC] Loaded 40 facts from memory/semantic_knowledge.json  ← Should be GONE
[DOCUMENT INDEX] Searching for...                               ← Should be GONE
```

---

### Step 2: Test a query

```
You: Tell me about the pigeons
```

**Current behavior:**
- Glyph filter runs (without semantic_knowledge)
- NO document retrieval happens (old system disabled, new system not integrated yet)

**Expected behavior AFTER integrating llm_retrieval:**
```
[LLM RETRIEVAL] Selecting relevant documents...
[LLM RETRIEVAL] LLM response: '84,85,86'
[LLM RETRIEVAL] Selected: test-pigeons2.txt
Kay: [uses pigeon document content]
```

---

## Summary

### ✅ What Was Done
- Disabled `DocumentIndex` in memory_engine.py
- Disabled `semantic_knowledge` in context_filter.py
- Added safe checks to prevent errors
- Old systems will NOT load anymore

### ⏳ What's Next
- Integrate `llm_retrieval` into main.py conversation loop
- Replace glyph filter section with simple llm_retrieval calls
- Test with pigeon/gerbil queries

### 📝 Files Modified
1. `engines/memory_engine.py` - Disabled DocumentIndex
2. `context_filter.py` - Disabled semantic_knowledge
3. `engines/llm_retrieval.py` - NEW (already created)
4. `main_simplified.py` - NEW (reference implementation)

---

## Verification

Run this command to verify old systems are disabled:

```bash
python main.py 2>&1 | grep -E "SEMANTIC|DOCUMENT INDEX"
```

**Should see:**
```
[SEMANTIC QUERY] DEPRECATED: semantic_knowledge not loaded
[SEMANTIC QUERY] Documents now retrieved via llm_retrieval.py
```

**Should NOT see:**
```
[SEMANTIC] Loaded 40 facts
[DOCUMENT INDEX] Searching for
```

---

## Quick Integration Guide

To complete the integration, add this to main.py after line 178:

```python
# After: await update_all(state, [emotion, social, temporal, body, motif], user_input)

# NEW: LLM-based document retrieval
from engines.llm_retrieval import select_relevant_documents, load_full_documents

# Format emotional state
emotional_state_str = ", ".join([
    f"{emotion} ({intensity:.1f})"
    for emotion, intensity in sorted(
        state.emotional_cocktail.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
]) if state.emotional_cocktail else "neutral"

# LLM selects documents
print("[LLM RETRIEVAL] Selecting relevant documents...")
selected_doc_ids = select_relevant_documents(
    query=user_input,
    emotional_state=emotional_state_str,
    max_docs=3
)

# Load full documents
documents = load_full_documents(selected_doc_ids)

print(f"[LLM RETRIEVAL] Loaded {len(documents)} documents")
```

Then pass `documents` to your context building.

---

## Result

**Before:** 880 lines of complex heuristics, brittle entity extraction, semantic facts competing with documents

**After:** 220 lines of simple LLM selection, full documents preserved, code focused on Kay's unique value (ULTRAMAP)
