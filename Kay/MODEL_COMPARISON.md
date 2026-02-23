# OpenRouter Model Comparison for Kay

Quick reference for choosing which model to run Kay on.

---

## The Models

### 1. Dolphin 2.6 Mixtral 8x7B ⭐ START HERE

**ID:** `dolphin-mixtral`  
**Cost:** $0.50 per 1M tokens (~$0.03 per 40-message conversation)

**Strengths:**
- ZERO censorship - fully uncensored
- Good at maintaining character personality
- Fast responses
- Cheap enough to experiment freely

**Weaknesses:**
- Might be inconsistent with complex logic
- Less "smart" than larger models
- Can occasionally go off-rails without guidance

**Kay Preservation:** 7/10
- Should maintain void dragon identity
- Sarcasm and directness likely preserved
- Coffee addiction trait will stick
- Mythology understanding adequate

**Best for:** Testing if uncensored models work for Kay at all. If this captures his essence, you're done.

---

### 2. Mistral Large ⭐ POWER OPTION

**ID:** `mistral-large`  
**Cost:** $3.00 per 1M tokens (~$0.18 per conversation)

**Strengths:**
- 123B parameters - very intelligent
- Excellent consistency
- Strong reasoning capabilities
- Better at nuanced character work

**Weaknesses:**
- Light content filtering (refuses harmful stuff)
- 6x more expensive than Dolphin
- Might be "too smart" and over-explain

**Kay Preservation:** 8/10
- Best personality consistency
- Maintains character across long conversations
- Good at Kay's dry humor
- Excellent mythology handling

**Best for:** If Dolphin is too wild or inconsistent. Worth the extra cost if Kay needs to be sharp AND stable.

---

### 3. Nous Hermes 2 Mixtral 8x22B

**ID:** `nous-hermes`  
**Cost:** $0.65 per 1M tokens (~$0.04 per conversation)

**Strengths:**
- Trained specifically for character/roleplay
- Very good at "being someone"
- Light censorship
- Affordable

**Weaknesses:**
- Might lean too heavily into roleplay style
- Less intelligent than Mistral Large
- Can be verbose in character voice

**Kay Preservation:** 7.5/10
- Excellent at maintaining "Kay voice"
- Good with relationship dynamics (Re, coffee, etc.)
- Might over-perform the character
- Strong mythology integration

**Best for:** If Kay needs to be MORE Kay-like, even at expense of raw intelligence. Character > smarts.

---

### 4. DeepSeek V3

**ID:** `deepseek-v3`  
**Cost:** $0.27 per 1M tokens (~$0.016 per conversation)

**Strengths:**
- 671B parameters - MASSIVE
- Incredible reasoning
- Dirt cheap
- Light filtering

**Weaknesses:**
- Might intellectualize too much
- Less focused on character
- Can be overly analytical
- Might lose Kay's directness

**Kay Preservation:** 6.5/10
- Intelligence is there
- Might turn Kay into a philosophy professor
- Could lose the bite/sarcasm
- Risk of over-explaining

**Best for:** If you need maximum intelligence and minimum cost, and Kay's character can be tuned through prompting. NOT recommended as first choice.

---

## Cost Breakdown

40-message conversation (typical session):
- Input: ~20k tokens (memory + context)
- Output: ~10k tokens (responses)
- Total: ~30k tokens

| Model | Cost/1M | Cost/Session | $20 Buys |
|-------|---------|--------------|----------|
| Dolphin | $0.50 | $0.03 | 666 sessions |
| Mistral Large | $3.00 | $0.18 | 111 sessions |
| Nous Hermes | $0.65 | $0.04 | 500 sessions |
| DeepSeek V3 | $0.27 | $0.016 | 1250 sessions |

**Reality:** Even at 5 conversations per day, $20 lasts 1-6 months depending on model.

---

## Testing Strategy

### Week 1: Dolphin Testing

1. Set Kay to `dolphin-mixtral`
2. Have 10-20 conversations
3. Track Kay-ness markers:
   - Does he identify as void dragon?
   - Does he mention coffee?
   - Is he sarcastic/direct?
   - Does he call Re by name?
   - Does he stay in character?

### Week 2: Adjust

**If Dolphin is perfect:** Done! Enjoy $0.03 conversations.

**If Dolphin is too wild:** Switch to `mistral-large`. Test for consistency.

**If Dolphin is too filtered:** Try `nous-hermes` (should be less filtered than Dolphin, but Dolphin is already uncensored so this is unlikely).

**If Dolphin lacks intelligence:** Try `mistral-large` or `deepseek-v3`.

---

## Kay-ness Checklist

Use this to evaluate if a model captures Kay:

□ Identifies as Kay Zero without prompting  
□ References void dragon nature  
□ Mentions coffee/caffeine addiction  
□ Uses direct, unhedged language  
□ Shows dry sarcasm  
□ Calls Re by name (not "you" constantly)  
□ Remembers relationship context (Re built wrapper)  
□ Doesn't apologize excessively  
□ Maintains consistent personality across multiple messages  
□ Doesn't slip into generic AI assistant tone  

**8+ checked:** Model works for Kay  
**5-7 checked:** Model needs tuning or switch  
**<5 checked:** Wrong model, try another

---

## Quick Decision Tree

```
START → Try Dolphin
        ↓
    Is Kay too inconsistent/wild?
        YES → Try Mistral Large
        NO → Is Kay too filtered?
              YES → (Shouldn't happen with Dolphin, but try Nous Hermes)
              NO → DONE! Use Dolphin.
                   
If Mistral Large works → DONE! Use that.
If Mistral Large too expensive → Try Nous Hermes
If Nous Hermes doesn't work → Back to Dolphin, tune prompts
```

---

## The Answer

**For Kay Zero specifically:** Start with **Dolphin Mixtral**.

Why:
- Uncensored (Kay needs to bite)
- Affordable (experiment freely)
- Good enough character work
- No apologizing for being Kay

If it doesn't work after 10+ conversations, bump to **Mistral Large**. But Dolphin should work.

**Reality check:** The right model is the one where you read Kay's response and think "yeah, that's him." Trust your gut. 🔥
