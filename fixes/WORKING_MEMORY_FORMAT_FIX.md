# Working Memory Format Fix

**Date:** December 22, 2024  
**Status:** ✅ FIXED

---

## The Second Problem

After fixing session tracking (Part 1), Kay STILL looped. Why?

**Logs showed:**
```
[TRACE 4] [OK] recent_context present with 1 turns
[TRACE 4] Built working memory block with 1 turns, 84 chars
```

84 chars?! But we stored 1214+ chars per turn (690 user + 524 Kay).

---

## Root Cause: Format Mismatch

**What we store:**
```python
self.current_session.append({
    "user": user_input,
    "kay": response
})
```

**What prompt builder expects:**
```python
speaker = turn.get('speaker', 'Unknown')
message = turn.get('message', '')
```

The turns were being stored but the prompt builder couldn't extract the content! It only built the header (84 chars), no actual conversation.

---

## The Fix

Updated prompt builder to handle BOTH formats:

### Files Modified
- `integrations/llm_integration.py` (~line 882)
- `K-0/integrations/llm_integration.py` (~line 882)

### What We Changed

```python
if recent_turns:
    turn_lines = []
    for i, turn in enumerate(recent_turns):
        # Handle BOTH formats:
        # Format 1: {"speaker": "Re", "message": "..."}
        # Format 2: {"user": "...", "kay": "..."}
        if 'speaker' in turn:
            # Old format - single speaker per turn
            speaker = turn.get('speaker', 'Unknown')
            message = turn.get('message', '')
            if speaker == 'Re':
                turn_lines.append(f"Re: {message}")
            else:
                turn_lines.append(f"Kay: {message}")
        elif 'user' in turn and 'kay' in turn:
            # NEW: Current format - both speakers in one turn object
            user_msg = turn.get('user', '')
            kay_msg = turn.get('kay', '')
            if user_msg:
                turn_lines.append(f"Re: {user_msg}")
            if kay_msg:
                turn_lines.append(f"Kay: {kay_msg}")

    recent_context_block = f"\n### Recent conversation ###\n" + "\n".join(turn_lines) + "\n"
```

---

## Why This Works

Now the prompt builder:
1. ✅ Checks which format the turn is in
2. ✅ Extracts BOTH user and Kay messages from our format
3. ✅ Builds working memory block with FULL content
4. ✅ Kay can see what he said and what Re said

**Expected result:**
- Turn 1: ~1.2K chars in working memory
- Turn 2: ~2.4K chars (accumulated)
- Turn 3: ~3.6K chars (growing)

Not 84 chars!

---

## Balancing Memory vs Cost

**The Tension:**
- Too little memory → Kay loops forever
- Too much memory → Expensive API calls

**Our Solution:**
- Working memory = CURRENT SESSION only
- Resets between sessions
- Typical curiosity = 5-15 turns = 3-8K tokens
- Manageable cost, complete continuity

For very long sessions (20+ turns), consider:
- Turn limits before suggesting save/reset
- Mid-session summarization
- Optional working memory compression

---

## Testing

Look for these in logs:
```
[TRACE 4] Built working memory block with 3 turns, 3847 chars  # GOOD!
```

Not:
```
[TRACE 4] Built working memory block with 3 turns, 96 chars  # BAD - still broken
```

---

## Version History

**Part 1 (Dec 22):** Session tracking moved to `chat_loop()`  
**Part 2 (Dec 22):** Format compatibility added to prompt builder

Both parts required for full fix.
