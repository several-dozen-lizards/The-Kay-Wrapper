# HALLUCINATION FIX: Aggressive Context Reduction

## PROBLEM IDENTIFIED

Kay is still hallucinating despite hierarchical prompt structure being implemented.

**Symptoms:**
- Kay responds to architecture flowcharts, legal documents, OkCupid questions that DON'T exist in current conversation
- Context reaches 20,298 tokens (~81K characters)
- Attention collapse occurs even with hierarchical structure

**Root cause:** VOLUME, not structure
- Hierarchical structure EXISTS and is correctly implemented
- But it's being OVERWHELMED by sheer quantity of context
- 250 memories + 50 RAG chunks = too much for attention to stay focused

**Kay's hallucination response (Turn 2):**
```
I can see everything—all the background docs, the legal outline, the custody 
battle prep, the architecture flowchart, conversations about continuity and 
caring, timeline corrections, OkCupid questions, Robert E. Howard fixations...
seeing sixteen document filenames, seven different semantic facts about my 
own substrate, your entire custody defense strategy, and a note about how 
pepper incidents became household law.
```

NONE of these were in the current conversation. They're from RAG chunks and recalled memories.

---

## THE FIX: Aggressive Context Reduction

Hierarchical structure is good, but needs MUCH LESS content to work with.

### Changes Needed

**1. Memory Retrieval Limit: 250 → 50**

Location: Search for where memories are being truncated to 250

Current behavior:
```
[RECALL TRUNCATION] Reduced 7825 → 250 memories
```

Target behavior:
```
[RECALL TRUNCATION] Reduced 7825 → 50 memories
```

**Find:** The code that sets `max_memories = 250` or similar
**Change to:** `max_memories = 50`

---

**2. RAG Retrieval Limit: 50 → 10**

Location: `main.py` or wherever RAG chunks are initially retrieved

Current code likely has something like:
```python
rag_chunks = vector_store.retrieve(query, max_results=50)
```

Change to:
```python
rag_chunks = vector_store.retrieve(query, max_results=10)
```

---

**3. Add Explicit Instructions at Top of Prompt**

Location: `integrations/llm_integration.py` line ~1615

In the `current_turn_block` section, make the instructions MORE explicit:

```python
current_turn_block = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    === CURRENT TURN (HIGHEST PRIORITY) ===                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

[Timestamp: {current_time}]
[Turn {turn_count}]

Re just said: "{user_input}"

{f'[Attached images: {len(active_images)} active]' if active_images else '[No images attached this turn]'}

▶▶▶ CRITICAL: RESPOND ONLY TO THE MESSAGE ABOVE ◀◀◀

DO NOT respond to:
- Documents mentioned in background sections below
- Memories from weeks/months ago
- RAG chunks about unrelated topics
- Any content marked [BACKGROUND] or [MEDIUM RELEVANCE]

ONLY respond to:
- What Re just said in this turn
- Images attached THIS TURN (listed above)
- Highly relevant recent conversation context

If you reference background content, you MUST explain why it's relevant to Re's current message.
"""
```

---

## VERIFICATION

After implementing these changes, test with same query:

**User:** "How are you doing?"

**Expected response:** Kay should answer the question WITHOUT listing documents, legal strategies, architecture flowcharts, or other background content.

**Context size target:** Under 8,000 tokens (currently at 20,298)

**Log output should show:**
```
[RECALL TRUNCATION] Reduced 7825 → 50 memories
[RAG] Retrieved 10 chunks
[CONTEXT SIZE] ~7,500 tokens
[CONTEXT INFO] ✓ Token count within budget
```

---

## FILES TO MODIFY

1. **Memory retrieval limit** - Find where 250 is set (likely in `engines/memory_engine.py` or `engines/memory_layers.py`)

2. **RAG retrieval limit** - Find where RAG chunks are requested (likely in `main.py` around line 700-750)

3. **Prompt instructions** - `integrations/llm_integration.py` line ~1615 in `current_turn_block`

---

## WHY THIS WILL WORK

The hierarchical structure is CORRECT - it just needs less content to work with.

Think of it like this:
- **Before:** "Here's what matters most [buried under 20K tokens of other stuff]"
- **After:** "Here's what matters most [with only 50 relevant memories and 10 documents]"

Attention can focus when there's less to pay attention to.

50 memories is PLENTY for a single conversational turn.
10 RAG chunks is PLENTY for context.

The rest is available via tool calls if Kay needs more specific information.
