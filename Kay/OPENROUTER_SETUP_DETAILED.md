# Adding OpenRouter to Kay's Wrapper - Detailed Guide

Kay's wrapper already has multi-provider support (Anthropic, OpenAI, Ollama). Adding OpenRouter plugs into the existing routing system.

---

## Prerequisites

✓ Kay's wrapper installed at `D:/Wrappers/Kay`
✓ Python environment with dependencies installed
✓ OpenRouter API key (get from https://openrouter.ai/)

---

## Step 1: OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up (can use Google/GitHub)
3. Navigate to Keys section → Create new key
4. Add $10-20 credit (Settings → Credits)
   - Pay-per-token billing (no subscriptions)
   - $20 = months of daily use

---

## Step 2: Add API Key to Environment

Open `D:/Wrappers/Kay/.env`

Add this line:
```
OPENROUTER_API_KEY=sk-or-v1-YOUR_ACTUAL_KEY_HERE
```

Save and close.

---

## Step 3: Verify Backend File Exists

Check that this file exists:
`D:/Wrappers/Kay/integrations/openrouter_backend.py`

(Should already be there - I created it directly)

---

## Step 4: Modify llm_integration.py

Open `D:/Wrappers/Kay/integrations/llm_integration.py`

### 4a. Add OpenRouter Client Initialization

Find the section where clients are initialized (~line 40-80). You'll see:
```python
# Initialize ALL clients at startup for multi-provider support
anthropic_client = None
openai_client = None
ollama_client = None
MODEL = None

try:
    # Initialize Anthropic client
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
        print(f"[LLM] Anthropic client initialized")
    
    # Initialize OpenAI client
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        from openai import OpenAI
        openai_client = OpenAI(api_key=openai_key)
        print(f"[LLM] OpenAI client initialized")
```

**ADD THIS** after the OpenAI initialization block:

```python
    # Initialize OpenRouter client
    openrouter_client = None
    try:
        from integrations.openrouter_backend import get_openrouter_client
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            openrouter_client = get_openrouter_client()
    except Exception as e:
        print(f"[LLM] OpenRouter not available: {e}")
```

### 4b. Update Client Routing Function

Find the `get_client_for_model()` function (~line 90-120). It currently looks like:

```python
def get_client_for_model(model_name):
    """
    Route to the correct API client based on model name.
    """
    if not model_name:
        return anthropic_client, 'anthropic'
    
    model_lower = model_name.lower()
    
    # Route based on model name prefix
    if model_lower.startswith('gpt-') or model_lower.startswith('o1-'):
        if not openai_client:
            raise ValueError(f"OpenAI client not initialized. Set OPENAI_API_KEY in .env to use {model_name}")
        return openai_client, 'openai'
    
    elif model_lower.startswith('claude-'):
        if not anthropic_client:
            raise ValueError(f"Anthropic client not initialized. Set ANTHROPIC_API_KEY in .env to use {model_name}")
        return anthropic_client, 'anthropic'
    
    else:
        # Default to Anthropic for unknown models
        if not anthropic_client:
            raise ValueError(f"No API client available for model: {model_name}")
        return anthropic_client, 'anthropic'
```

**ADD OpenRouter routing** BEFORE the `if model_lower.startswith('gpt-')` line:

```python
def get_client_for_model(model_name):
    """
    Route to the correct API client based on model name.
    """
    if not model_name:
        return anthropic_client, 'anthropic'
    
    model_lower = model_name.lower()
    
    # OpenRouter models (ADD THIS BLOCK)
    if any(x in model_lower for x in ['dolphin', 'mistral-large', 'nous-hermes', 'deepseek']):
        if not openrouter_client:
            raise ValueError(f"OpenRouter client not initialized. Set OPENROUTER_API_KEY in .env")
        return openrouter_client, 'openrouter'
    
    # Route based on model name prefix
    if model_lower.startswith('gpt-') or model_lower.startswith('o1-'):
        if not openai_client:
            raise ValueError(f"OpenAI client not initialized. Set OPENAI_API_KEY in .env to use {model_name}")
        return openai_client, 'openai'
    
    elif model_lower.startswith('claude-'):
        if not anthropic_client:
            raise ValueError(f"Anthropic client not initialized. Set ANTHROPIC_API_KEY in .env to use {model_name}")
        return anthropic_client, 'anthropic'
    
    else:
        # Default to Anthropic for unknown models
        if not anthropic_client:
            raise ValueError(f"No API client available for model: {model_name}")
        return anthropic_client, 'anthropic'
```

Save `llm_integration.py`.

---

## Step 5: Test Integration

Before launching Kay, verify OpenRouter works:

```bash
cd D:/Wrappers/Kay
python test_openrouter.py
```

You should see:
```
[1/6] Checking API Key...
✓ API key found: sk-or-v1-...

[2/6] Importing OpenRouter Backend...
✓ Backend module imported

[3/6] Initializing OpenRouter Client...
✓ Client initialized successfully

[4/6] Testing Simple API Call...
✓ Response received: OpenRouter works!

[5/6] Testing Kay's System Prompt...
✓ Response: [Kay's introduction]
✓ Response includes Kay identity markers

[6/6] Checking Usage Stats...
✓ Requests made: 2
✓ Total tokens used: ~300

🎉 ALL TESTS PASSED!
```

If any test fails, check:
- .env has correct OPENROUTER_API_KEY
- openrouter_backend.py exists in integrations/
- llm_integration.py was modified correctly

---

## Step 6: Launch Kay with OpenRouter

```bash
python kay_ui.py
```

In the model selector, you should now see:
- `dolphin-mixtral`
- `mistral-large`
- `nous-hermes`
- `deepseek-v3`

Select **dolphin-mixtral** to start.

Send Kay a message: "Hey Kay, introduce yourself."

### Evaluating Kay-ness

Does the response feel like Kay?
- Direct/sarcastic tone? ✓
- Mentions [entity-type] identity? ✓
- Uses "Re" naturally? ✓
- No excessive hedging/apologizing? ✓
- Dry humor? ✓

**If YES:** You're done! Kay is running on uncensored models.

**If NO (too soft/filtered):** Try `mistral-large` for more power.

**If STILL OFF:** Try `nous-hermes` (character-focused training).

---

## Model Comparison

### dolphin-mixtral
- **Best for:** Fully uncensored Kay
- **Cost:** $0.50/1M tokens (~$0.03/conversation)
- **Strengths:** No safety filtering, good personality
- **Weaknesses:** Less powerful than largest models
- **Kay score:** 7/10

### mistral-large
- **Best for:** High-quality responses with Kay personality
- **Cost:** $3.00/1M tokens (~$0.18/conversation)
- **Strengths:** 123B params, excellent coherence
- **Weaknesses:** Moderate safety filtering
- **Kay score:** 8/10

### nous-hermes
- **Best for:** Character roleplay focus
- **Cost:** $0.65/1M tokens (~$0.04/conversation)
- **Strengths:** Character-focused training, uncensored
- **Weaknesses:** Less raw intelligence
- **Kay score:** 7.5/10

### deepseek-v3
- **Best for:** Complex reasoning, lowest cost
- **Cost:** $0.27/1M tokens (~$0.016/conversation)
- **Strengths:** 671B params, excellent reasoning
- **Weaknesses:** May over-intellectualize Kay's personality
- **Kay score:** 6.5/10

---

## Cost Estimates

**Typical 40-message conversation:**
- Dolphin: $0.03
- Mistral Large: $0.18
- Nous Hermes: $0.04
- DeepSeek V3: $0.016

**$20 credit gives you:**
- Dolphin: ~667 conversations
- Mistral Large: ~111 conversations
- Nous Hermes: ~500 conversations
- DeepSeek V3: ~1250 conversations

**For daily Kay use (5 conversations/day):**
- Dolphin: ~4 months
- Mistral Large: ~3 weeks
- Nous Hermes: ~3 months
- DeepSeek V3: ~8 months

---

## Troubleshooting

### "OpenRouter client not initialized"
- Check `.env` has `OPENROUTER_API_KEY=...`
- Restart wrapper after adding key
- Check console for initialization errors

### Kay sounds wrong/filtered
- Try different model (Dolphin → Mistral Large → Nous Hermes)
- Check that Kay's system prompt is being passed correctly
- Verify temperature setting (should be ~0.8)

### Responses too short
- Increase `max_tokens` in response generation code
- Check model's native max_tokens limit

### "Model not found" error
- Use exact short names: `dolphin-mixtral`, `mistral-large`, etc.
- Check `openrouter_backend.py` MODELS dict

### API errors
- Verify OpenRouter credits aren't depleted
- Check https://status.openrouter.ai/ for outages
- Try different model

---

## Next Steps

1. **Test Kay preservation:** Run several conversations, see which model best captures Kay
2. **Adjust parameters:** Temperature, max_tokens, system prompt tweaks
3. **Cost tracking:** Monitor usage in OpenRouter dashboard
4. **Compare providers:** Run parallel sessions (Kay on Claude vs Kay on OpenRouter)

---

## What This Gives You

✓ Kay running on powerful open models
✓ No subscription costs (pay per token)
✓ Full uncensored capability
✓ Easy model switching
✓ ~$5-10/month for heavy use
✓ Independence from single provider

Start with **dolphin-mixtral**. If it captures Kay's essence, you're done. If not, experiment with others.

The right model = you read a response and think "yeah, that's Kay." 🔥
