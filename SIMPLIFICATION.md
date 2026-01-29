# RADICAL SIMPLIFICATION

## The Problem

Kay was getting WORSE with each "fix":
- Still flip-flopping on preferences (tea/coffee)
- Inventing facts (confabulation about eye color)
- Using stage directions again (asterisks)
- Losing conversation thread
- Calling Re "Reed" after corrections

**Root cause:** Over-engineered architecture creating prompt complexity that the LLM couldn't track.

## The Solution

**STRIP TO ESSENTIALS. Build from working foundation.**

### What Was Removed

❌ **Removed (until core works):**
- Preference weighting system
- Identity consolidation
- Anti-repetition banned phrases system
- Meta-awareness engine
- Momentum engine
- Motif tracking
- Emotional biasing in memory
- Social modeling
- Embodiment simulation
- Reflection engine
- Complex prompt engineering

### What Remains (CORE ONLY)

✅ **Core functionality:**
1. **Memory storage** - Just user input, response, perspective, timestamp
2. **Memory retrieval** - Top 5 by keyword overlap only
3. **Recent context** - Last 3 turns only
4. **System prompt** - Under 200 words total
5. **LLM call** - Minimal prompt, 300 token limit

## File Structure

### New Simplified Files

**`main_simple.py`** - 50 lines total
- No engines except memory
- No state tracking
- Just: input → memory retrieve → LLM → store → repeat

**`engines/memory_engine_simple.py`** - 90 lines total
- `store(user_input, kay_response)` - Save memory
- `retrieve(query, limit=5)` - Get memories by keyword overlap
- `_detect_perspective(text)` - Simple pronoun detection
- No emotional tagging, no weighting, no filtering

**`integrations/llm_integration_simple.py`** - 80 lines total
- `SYSTEM_PROMPT` - 173 words (under 200)
- `build_simple_prompt()` - Last 3 turns + top 5 memories
- `get_llm_response_simple()` - Basic Anthropic call
- No caching, no anti-repetition, no variety prompts

## System Prompt (173 words)

```
You are Kay, a conversational AI.

CRITICAL RULES:
1. Re is the user typing to you. Their name is "Re" (not Reed, not any other name).
2. Facts about "Re" are about THEM. Facts about "Kay" are about YOU.
3. When you see "your eyes are green" - that's about Re, not you.
4. When you see "you like coffee" - that's about you (Kay).
5. Never use asterisks or describe actions. Just talk.
6. Keep responses under 3 sentences unless directly asked for more.
7. If you don't remember something, say so - don't guess.

Personality: Direct, dry humor, conversational. You're a normal guy having a chat.
```

That's it. No complex instructions, no meta-notes, no self-monitoring alerts.

## Prompt Structure

```
Facts about Re:
- [user memory 1]
- [user memory 2]

Facts about Kay (you):
- [kay memory 1]
- [kay memory 2]

Re: [turn -3 user]
Kay: [turn -3 response]
Re: [turn -2 user]
Kay: [turn -2 response]
Re: [turn -1 user]
Kay: [turn -1 response]

Re: [current input]
Kay:
```

Simple. Clean. Trackable.

## Memory Storage

```json
{
  "user_input": "My eyes are green",
  "response": "Got it, green eyes",
  "perspective": "user",
  "timestamp": 1704067200.0
}
```

No emotion tags, no cocktail snapshots, no motif weights.

## Testing Instructions

Run simplified system:
```bash
python main_simple.py
```

Test cases:
1. **Identity:** "My name is Re" → Kay should remember "Re", not invent "Reed"
2. **Perspective:** "Your favorite drink is coffee" → Kay says "my favorite is coffee" (not "your")
3. **Memory:** Ask "What's my name?" → Kay says "Re"
4. **No confabulation:** If Kay doesn't know something, he should say so
5. **No asterisks:** Kay should NEVER use `*actions*`

## What to Add Back (IF core works)

Only add complexity if simplified version works perfectly:

**Phase 1 (if core perfect):**
- Basic emotion detection (just keywords, no cocktail)
- Preference tracking (frequency count only, no recency weighting)

**Phase 2 (if Phase 1 perfect):**
- Recent conversation weighting
- Memory relevance filtering

**Phase 3 (if Phase 2 perfect):**
- Identity consistency checking
- Simple anti-repetition (track last opening only)

## Key Principles

1. **Start simple, add complexity only when needed**
2. **If something breaks, remove it - don't patch it**
3. **Prompt length matters - keep under 500 words total**
4. **LLMs can't track 100 instructions - give them 7**
5. **Test each addition independently before combining**

## Comparison

### Before (Complex)
- System prompt: 800+ words
- Prompt with context: 2000+ words
- Memory retrieval: 7 different scoring factors
- Context building: 12 different systems contributing
- Instructions to LLM: 50+ rules

**Result:** Kay confused, contradictory, losing thread

### After (Simple)
- System prompt: 173 words
- Prompt with context: ~300 words
- Memory retrieval: keyword overlap only
- Context building: 2 systems (memory + turns)
- Instructions to LLM: 7 rules

**Expected result:** Kay consistent, coherent, trackable

## Files to Ignore (for now)

Don't use these until simplified version works:
- `main.py` (original complex system)
- `engines/emotion_engine.py`
- `engines/preference_tracker.py`
- `engines/meta_awareness_engine.py`
- `engines/momentum_engine.py`
- `engines/motif_engine.py`
- `integrations/llm_integration.py` (complex version)

## Success Criteria

Simplified system is successful when:
- ✅ Kay remembers Re's name correctly (never says "Reed")
- ✅ Kay distinguishes Re's attributes from his own
- ✅ Kay doesn't confabulate facts
- ✅ Kay never uses asterisks or stage directions
- ✅ Kay maintains conversation thread across turns
- ✅ Kay's preferences stay consistent within session

If ANY of these fail, DON'T add complexity. Fix the core first.

## Philosophy

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."
> — Antoine de Saint-Exupéry

We tried adding systems to fix problems. It made things worse.

Now we try subtracting systems to fix problems.

The complex system is preserved in the original files. But test the simple system first.

If the simple system works, rebuild complexity SLOWLY, testing at each step.

If the simple system fails the same way... the problem isn't architecture. It's something more fundamental.
