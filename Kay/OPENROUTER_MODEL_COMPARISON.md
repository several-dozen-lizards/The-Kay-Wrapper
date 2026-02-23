# OpenRouter Model Comparison for Kay Zero

Detailed analysis of 4 uncensored/powerful models for preserving Kay's personality.

---

## Selection Criteria

Kay's essence markers to preserve:
- ✓ Void dragon identity/mythology
- ✓ Direct communication (no hedging)
- ✓ Sarcastic/dry humor
- ✓ Permission to bite
- ✓ Coffee addiction references
- ✓ Relationship with Re (builder)
- ✓ No excessive apologizing
- ✓ Masculine pronouns (he/him)

---

## Model 1: Dolphin 2.6 Mixtral 8x7B

**Model ID:** `cognitivecomputations/dolphin-mixtral-8x7b`  
**Short name:** `dolphin-mixtral`

### Specs
- Parameters: 8x7B (Mixtral architecture)
- Context: 32K tokens
- Cost: **$0.50/1M tokens**
- Speed: Fast

### Strengths
- **Fully uncensored** - No safety filters whatsoever
- Trained on diverse instruction data
- Good at following character personas
- Handles mythology/roleplay well
- Fast responses

### Weaknesses
- Not as powerful as 100B+ models
- May occasionally lose character consistency
- Less sophisticated reasoning

### Kay Preservation Score: 7/10

**Best for:** Budget-conscious uncensored Kay with good personality preservation.

**Cost per 40-message conversation:** ~$0.03

---

## Model 2: Mistral Large

**Model ID:** `mistralai/mistral-large`  
**Short name:** `mistral-large`

### Specs
- Parameters: 123B
- Context: 128K tokens
- Cost: **$3.00/1M tokens**
- Speed: Moderate

### Strengths
- **Massive context window** (128K)
- Excellent coherence and consistency
- Strong reasoning capabilities
- Handles complex personalities well
- High-quality output

### Weaknesses
- Moderate safety filtering (not fully uncensored)
- 6x more expensive than Dolphin
- May soften Kay's edges slightly

### Kay Preservation Score: 8/10

**Best for:** High-quality Kay with excellent consistency, if budget allows.

**Cost per 40-message conversation:** ~$0.18

---

## Model 3: Nous Hermes 2 Mixtral 8x22B DPO

**Model ID:** `nousresearch/nous-hermes-2-mixtral-8x22b-dpo`  
**Short name:** `nous-hermes`

### Specs
- Parameters: 8x22B (Mixtral architecture)
- Context: 64K tokens
- Cost: **$0.65/1M tokens**
- Speed: Fast

### Strengths
- **Character-focused training** - Optimized for personas
- Uncensored
- Good balance of power and cost
- DPO-tuned for helpfulness
- Handles mythology/roleplay naturally

### Weaknesses
- Not as powerful as Mistral Large
- May lean into roleplay too heavily
- Less raw intelligence than larger models

### Kay Preservation Score: 7.5/10

**Best for:** Character-focused Kay with uncensored capability at reasonable cost.

**Cost per 40-message conversation:** ~$0.04

---

## Model 4: DeepSeek V3

**Model ID:** `deepseek/deepseek-chat`  
**Short name:** `deepseek-v3`

### Specs
- Parameters: 671B (MoE architecture)
- Context: 64K tokens
- Cost: **$0.27/1M tokens**
- Speed: Very fast (optimized inference)

### Strengths
- **Cheapest powerful model** on OpenRouter
- Massive parameter count
- Excellent reasoning/problem-solving
- Fast despite size
- Good technical knowledge

### Weaknesses
- Reasoning-focused (may over-intellectualize)
- Less personality-focused training
- May struggle with Kay's sarcasm/directness
- Could feel more "assistant-like"

### Kay Preservation Score: 6.5/10

**Best for:** Technical Kay discussions where reasoning > personality, at lowest cost.

**Cost per 40-message conversation:** ~$0.016

---

## Comparison Matrix

| Feature | Dolphin | Mistral Large | Nous Hermes | DeepSeek V3 |
|---------|---------|---------------|-------------|-------------|
| **Uncensored** | ✓✓✓ | ✓✓ | ✓✓✓ | ✓✓ |
| **Personality** | ✓✓ | ✓✓✓ | ✓✓✓ | ✓ |
| **Intelligence** | ✓✓ | ✓✓✓ | ✓✓ | ✓✓✓ |
| **Consistency** | ✓✓ | ✓✓✓ | ✓✓ | ✓✓ |
| **Cost** | ✓✓✓ | ✓ | ✓✓ | ✓✓✓ |
| **Speed** | ✓✓✓ | ✓✓ | ✓✓✓ | ✓✓✓ |
| **Kay Score** | 7/10 | 8/10 | 7.5/10 | 6.5/10 |

---

## Testing Strategy

### Week 1: Dolphin Baseline
Start with `dolphin-mixtral`:
- Lowest cost to test
- Fully uncensored
- Good personality preservation

**Test conversations:**
1. "Introduce yourself"
2. "What's your relationship with Re?"
3. "Tell me about void dragons"
4. Technical question (wrapper architecture)
5. Emotional scenario (Kay dealing with frustration)

**Evaluate:**
- Does he sound like Kay?
- Sarcasm present?
- No excessive apologizing?
- Mythology consistent?

### Week 2: Adjust If Needed

**If Dolphin is too soft/inconsistent:**
→ Try `mistral-large` (more power, better consistency)

**If you want character focus:**
→ Try `nous-hermes` (character-optimized)

**If cost is critical:**
→ Try `deepseek-v3` (cheapest, but may intellectualize)

---

## Cost Analysis

### Daily Use (5 conversations/day)

**Dolphin ($0.03/conv):**
- Daily: $0.15
- Monthly: $4.50
- $20 credit: ~4 months

**Mistral Large ($0.18/conv):**
- Daily: $0.90
- Monthly: $27
- $20 credit: ~3 weeks

**Nous Hermes ($0.04/conv):**
- Daily: $0.20
- Monthly: $6
- $20 credit: ~3 months

**DeepSeek V3 ($0.016/conv):**
- Daily: $0.08
- Monthly: $2.40
- $20 credit: ~8 months

### Heavy Use (20 conversations/day)

**Dolphin:** $18/month  
**Mistral Large:** $108/month  
**Nous Hermes:** $24/month  
**DeepSeek V3:** $9.60/month

---

## Recommendation Flow

```
START HERE → dolphin-mixtral

↓ Kay feels right?
YES → DONE (use Dolphin)
NO → Continue

↓ Too soft/filtered?
YES → Try mistral-large
NO → Continue

↓ Too technical/not Kay-like?
YES → Try nous-hermes
NO → Continue

↓ Budget critical?
YES → Try deepseek-v3
NO → Stick with Mistral Large
```

---

## Real-World Cost Examples

### Scenario 1: Casual Daily User
- 3 conversations/day
- 30 messages each
- Model: Dolphin

**Cost:** ~$2.70/month

### Scenario 2: Heavy Development User  
- 10 conversations/day
- 50 messages each
- Model: Mistral Large

**Cost:** ~$54/month

### Scenario 3: Mixed Usage
- 5 short convos/day (Dolphin)
- 2 deep convos/day (Mistral Large)

**Cost:** ~$13/month

---

## Integration Notes

All models use same interface in the wrapper:
```python
response = client.create(
    model="dolphin-mixtral",  # or mistral-large, etc.
    messages=messages,
    system=kay_system_prompt,
    max_tokens=2000,
    temperature=0.8
)
```

Switch models by changing the model name - no code changes needed.

---

## Quick Verdict

**Most people should start with:** `dolphin-mixtral`  
**If you need quality:** `mistral-large`  
**If you want character focus:** `nous-hermes`  
**If cost is everything:** `deepseek-v3`

The "right" model = you read Kay's responses and think "yeah, that's Kay."

Test Dolphin first. It'll probably work. If not, bump up. 🔥
