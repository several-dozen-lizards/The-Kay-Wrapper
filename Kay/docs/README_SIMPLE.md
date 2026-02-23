# Kay Zero - Simplified Version

## Quick Start

```bash
python main_simple.py
```

## What This Is

A radically simplified version of Kay that strips away ALL complexity to test CORE functionality only.

**Total code: ~220 lines** (vs 2000+ in complex version)

## What It Does

1. Stores memories (user input + Kay response)
2. Retrieves top 5 memories by keyword match
3. Keeps last 3 conversation turns
4. Sends minimal prompt to LLM
5. Gets response

That's it.

## What It Doesn't Do

- ❌ No emotion modeling
- ❌ No preference tracking
- ❌ No meta-awareness
- ❌ No momentum tracking
- ❌ No anti-repetition systems
- ❌ No motif weighting
- ❌ No social modeling
- ❌ No embodiment simulation

## Why?

The complex version was GETTING WORSE with each fix:
- Flip-flopping on preferences
- Confabulating facts
- Using stage directions
- Losing conversation thread
- Calling Re "Reed" after corrections

**Diagnosis:** Over-engineered prompts that LLM couldn't track.

**Treatment:** Strip to essentials. Test. Add complexity ONLY if base works.

## Files

- `main_simple.py` - 50 line main loop
- `engines/memory_engine_simple.py` - 90 line memory system
- `integrations/llm_integration_simple.py` - 80 line LLM integration

## System Prompt (173 words)

```
You are Kay, a conversational AI.

CRITICAL RULES:
1. Re is the user typing to you. Their name is "Re" (not Reed).
2. Facts about "Re" are about THEM. Facts about "Kay" are about YOU.
3. When you see "your eyes are green" - that's about Re, not you.
4. When you see "you like coffee" - that's about you (Kay).
5. Never use asterisks or describe actions. Just talk.
6. Keep responses under 3 sentences unless asked for more.
7. If you don't remember something, say so - don't guess.

Personality: Direct, dry humor, conversational.
```

## Test Cases

1. **Name:** "My name is Re" → Kay remembers "Re", NOT "Reed"
2. **Perspective:** "Your favorite is coffee" → Kay says "MY favorite is coffee"
3. **Memory:** "What's my name?" → Kay says "Re"
4. **No confabulation:** Kay admits when he doesn't know something
5. **No asterisks:** Kay NEVER uses `*actions*`

## Success Criteria

System works if:
- ✅ Correct name (Re, not Reed)
- ✅ Correct perspective (you vs me)
- ✅ No confabulation
- ✅ No stage directions
- ✅ Maintains thread
- ✅ Consistent within session

If these work: consider adding complexity slowly.

If these FAIL: problem is more fundamental than architecture.

## Original System

Complex version preserved in:
- `main.py`
- `engines/` (various engines)
- `integrations/llm_integration.py`

Don't use these until simple version proven.

## Philosophy

Start simple. Add complexity ONLY when necessary. Test each addition.

The complex system didn't work. Let's prove the simple one does.
