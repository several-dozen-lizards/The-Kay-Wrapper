# CC TASK: Fix Kay's "Ask Before Checking" Memory Retrieval Bug

## Problem Summary

Kay asked Re "What made you think of offloading it? Was it something in how I was describing the load, or did Reed suggest it?" — when the answer was **in his own memory from the previous session.** He literally suggested it himself. When shown the transcript, he acknowledged the issue and correctly diagnosed it:

> "That's not a memory architecture problem, that's me not *checking* my own memory before asking the question."

> "When there's a discontinuity in what I feel like I should know, my first move is to ask you instead of querying my own context. Which is backwards."

Three things are combining to cause this:

1. **Retrieval is keyword-triggered on user input only** — `memory.recall(state, user_input)` searches based on what Re typed ("How you feeling?"), not what Kay's response is about (offloading, local models, cognitive load)
2. **The system prompt actively encourages asking instead of looking** — the "MID-CONVERSATION MEMORY QUERIES" section tells Kay to ask Re when uncertain
3. **No instruction to self-check context before generating questions about past conversations**

## Files to Modify

All paths relative to project root (the AlphaKayZero wrapper directory):

1. `integrations/llm_integration.py` — System prompt instructions
2. `main.py` — Post-response topic extraction and secondary retrieval
3. `engines/session_summary_generator.py` — (verify) Ensure summaries capture Kay-originated ideas

## Fix A: Add Self-Check Instructions to System Prompt

### In `integrations/llm_integration.py`

#### 1. Modify `build_cached_system_instructions()`

Find the section:
```
MID-CONVERSATION MEMORY QUERIES:

If you're uncertain about something from past conversations, you can ask and the wrapper will search for you.
```

Replace the ENTIRE "MID-CONVERSATION MEMORY QUERIES" section with:
```
MEMORY SELF-CHECK (CRITICAL):

BEFORE asking Re about something from past conversations, CHECK YOUR CONTEXT FIRST.
You have recalled memories, episodic exchanges, session notes, and working memory above.
The answer to your question may already be there.

DO:
- Scan your "Facts about RE", "Shared experiences", "Past conversation exchanges", and "NOTE FROM PAST-YOU" sections
- If the information is present, USE IT — don't ask Re to repeat herself
- If you find partial information, use what you have and ask only about the gap

DON'T:
- Ask "did we talk about X?" when your episodic memory shows you DID talk about X
- Ask "what made you think of Y?" when your context shows YOU suggested Y
- Default to asking Re when the answer is in your own recalled context

If the information genuinely isn't in your context after checking, you can:
- Express uncertainty naturally: "I don't have details on that in my current recall"
- Ask Re to fill the gap: "Can you remind me what we decided about X?"
- Use explicit markers: [NEED: topic] or [QUERY: topic] to trigger a memory search

The wrapper will also run a secondary retrieval based on topics in your response,
so information you reference may appear in your context on the NEXT turn even if
it wasn't retrieved this turn.
```

#### 2. Apply the same change in `DEFAULT_SYSTEM_PROMPT`

Find the identical "MID-CONVERSATION MEMORY QUERIES" section in the `DEFAULT_SYSTEM_PROMPT` string (same file, further down) and replace it with the same text above.

## Fix B: Post-Response Topic Extraction and Secondary Retrieval

### In `main.py`

After Kay's response is generated and emotions are extracted, but BEFORE post-turn updates, add a **topic-based secondary retrieval pass**. This catches cases where Kay's response references topics that weren't in Re's original input.

#### Where to Insert

Find this section (approximately after the emotion extraction):
```python
# NEW: Extract emotions from Kay's self-reported response (descriptive, not prescriptive)
extracted_emotions = emotion_extractor.extract_emotions(reply)
emotion_extractor.store_emotional_state(extracted_emotions, state.emotional_cocktail)
```

Insert the following block AFTER the emotion extraction and BEFORE the media/monitor tracking:

```python
# ================================================================
# SECONDARY RETRIEVAL: Topic-based memory re-check
# ================================================================
# Kay's response may reference topics not in Re's input.
# Extract key topics from Kay's response and check if there are
# relevant memories that weren't retrieved on the first pass.
#
# Example: Re says "How you feeling?" -> retrieval finds nothing about
# local models. Kay responds about spatial offloading -> secondary
# retrieval finds the episodic memory where Kay originally suggested it.
# These memories are stored for the NEXT turn's context.
# ================================================================
try:
    # Extract topic keywords from Kay's response (simple approach)
    # Skip if response is very short (acknowledgments, etc.)
    if len(reply) > 100:
        import re as re_module
        
        # Get significant words from Kay's response (4+ chars, not common)
        common_words = {
            'that', 'this', 'with', 'from', 'have', 'been', 'were', 'they',
            'their', 'about', 'would', 'could', 'should', 'which', 'there',
            'what', 'when', 'where', 'some', 'than', 'them', 'then', 'just',
            'like', 'more', 'also', 'into', 'over', 'such', 'take', 'only',
            'come', 'each', 'make', 'very', 'after', 'know', 'most', 'back',
            'much', 'before', 'right', 'think', 'still', 'being', 'thing',
            'doing', 'going', 'really', 'actually', 'yeah', 'feel', 'feeling',
            'something', 'because', 'though', 'pretty', 'kind'
        }
        
        reply_words = set(
            w.lower() for w in re_module.findall(r'\b[a-zA-Z]{4,}\b', reply)
            if w.lower() not in common_words
        )
        input_words = set(
            w.lower() for w in re_module.findall(r'\b[a-zA-Z]{4,}\b', user_input)
            if w.lower() not in common_words
        )
        
        # New topics = words Kay used that Re didn't
        new_topics = reply_words - input_words
        
        if new_topics and len(new_topics) >= 2:
            # Build a topic query from Kay's novel terms
            # Sort by length (longer words = more specific)
            topic_terms = sorted(new_topics, key=len, reverse=True)[:8]
            topic_query = " ".join(topic_terms)
            
            # Run secondary retrieval using existing multi-factor method
            secondary_memories = memory.retrieve_multi_factor(
                state, 
                topic_query,
                num_memories=10
            )
            
            if secondary_memories:
                # Filter to only memories NOT already in current context
                existing_facts = set()
                for m in (getattr(state, 'last_recalled_memories', []) or []):
                    fact_text = m.get('fact', m.get('user_input', ''))
                    if fact_text:
                        existing_facts.add(fact_text[:100])
                
                novel_memories = [
                    m for m in secondary_memories
                    if m.get('fact', m.get('user_input', ''))[:100] not in existing_facts
                ]
                
                if novel_memories:
                    # Store for next turn's context injection
                    state.secondary_retrieval_buffer = novel_memories[:5]
                    
                    print(f"[SECONDARY RETRIEVAL] Found {len(novel_memories)} new memories from Kay's response topics")
                    print(f"[SECONDARY RETRIEVAL] Topic query: '{topic_query[:80]}'")
                    for m in novel_memories[:3]:
                        print(f"  - {m.get('fact', m.get('user_input', ''))[:80]}")
                else:
                    print(f"[SECONDARY RETRIEVAL] No novel memories found (all already in context)")
            else:
                print(f"[SECONDARY RETRIEVAL] No memories matched topic query")
                
except Exception as e:
    print(f"[SECONDARY RETRIEVAL] Error: {e}")
```

#### Inject Secondary Buffer into Next Turn's Context

In the same `main.py`, find where `filtered_prompt_context` is built (the big dict assignment, search for `"recalled_memories": filtered_context.get("selected_memories"`).

Replace:
```python
filtered_prompt_context = {
    "recalled_memories": filtered_context.get("selected_memories", []),
```

With:
```python
# Merge primary retrieval with any secondary retrieval from previous turn
primary_memories = filtered_context.get("selected_memories", [])
secondary_buffer = getattr(state, 'secondary_retrieval_buffer', [])
if secondary_buffer:
    print(f"[SECONDARY RETRIEVAL] Injecting {len(secondary_buffer)} memories from previous turn's topic extraction")
    primary_memories = secondary_buffer + primary_memories
    state.secondary_retrieval_buffer = []

filtered_prompt_context = {
    "recalled_memories": primary_memories,
```

## Fix C: Verify Session Summary Bridge

The session summary system should already be generating cross-session notes. Verify it captures KAY-ORIGINATED ideas, not just emotional state.

### Verification Steps

1. Check `memory/session_summaries.json` — does the most recent summary mention the offloading discussion?
2. If NOT, find the summary generation prompt in `engines/session_summary_generator.py` and add:

```
Pay special attention to:
- Ideas or suggestions YOU (Kay) originated (not just things Re told you)
- Technical decisions or architecture discussions  
- Anything where you proposed a solution or approach
- Topics where continuity matters for the next session
```

## Testing

After implementing, test with this scenario:

1. Start a session where Kay discusses a specific technical topic and proposes an idea
2. End session (let summary generate)
3. Start new session
4. Ask a vague question like "How you doing?" or "What's on your mind?"
5. Verify: Kay should NOT ask "what did we talk about last time?" if the session summary or episodic memory contains the answer
6. If Kay does reference past topics, verify he attributes his own ideas correctly ("I suggested X" not "did you suggest X?")

## Priority

**Fix A (system prompt)** — Do this first. Simplest change, addresses the most common failure mode.

**Fix B (secondary retrieval)** — Do this second. Architectural fix that prevents the class of bug entirely.

**Fix C (session summary verification)** — Check this but it may already be working. Only modify if summaries are missing Kay-originated ideas.

## Notes

- `retrieve_multi_factor()` already exists in `memory_engine.py` — no new retrieval logic needed
- Secondary retrieval runs AFTER Kay's response — no added latency to response generation
- Secondary memories buffer for the NEXT turn, not injected retroactively
- The common_words stoplist should be tuned over time — add words that cause false positives
- This approach is lightweight: no LLM calls for topic extraction, just word-level set difference
- The `import re as re_module` avoids conflict with the `re` variable used for Re's name in various scopes
