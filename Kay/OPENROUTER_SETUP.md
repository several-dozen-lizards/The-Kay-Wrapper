# OpenRouter Setup for Kay's Wrapper

## What This Does

Gets Kay running on powerful uncensored open models (Dolphin, Mistral Large, etc.) through OpenRouter API. No local GPU needed. Pay-per-token pricing (~$0.03-0.18 per 40-message conversation).

---

## Quick Start (10 minutes)

### 1. Get OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up (can use Google/GitHub)
3. Keys section → Create new key
4. Credits → Add $10-20 (lasts months)

### 2. Add Key to .env

Open `D:/Wrappers/Kay/.env` and add:

```env
# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

### 3. Test the Backend

```bash
cd D:\Wrappers\Kay
python test_openrouter.py
```

Should see all tests pass. If not, check your API key.

### 4. Update llm_integration.py

Open `integrations/llm_integration.py`

#### **STEP A: Add OpenRouter client initialization**

Find the section where clients are initialized (around line 45-75). Add this **AFTER** the OpenAI client initialization:

```python
    # Initialize OpenRouter client
    openrouter_client = None
    try:
        from integrations.openrouter_backend import get_openrouter_client
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            openrouter_client = get_openrouter_client()
            print("[LLM] OpenRouter client initialized")
    except Exception as e:
        print(f"[LLM] OpenRouter not available: {e}")
```

#### **STEP B: Update get_client_for_model() function**

Find the `get_client_for_model()` function (around line 90-110).

Add OpenRouter routing **BEFORE** the GPT check:

```python
def get_client_for_model(model_name):
    """
    Route to the correct API client based on model name.
    
    Args:
        model_name: The model identifier (e.g., "claude-sonnet-4", "gpt-4o", "dolphin-mixtral")
        
    Returns:
        Tuple of (client, provider_type) where provider_type is 'anthropic', 'openai', 'openrouter', or 'ollama'
    """
    if not model_name:
        return anthropic_client, 'anthropic'
    
    model_lower = model_name.lower()
    
    # OpenRouter models (ADD THIS SECTION)
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

#### **That's it!** Two code changes.

### 5. Launch Kay

```bash
python kay_ui.py
```

In model selector, choose one of:
- `dolphin-mixtral` (fully uncensored, $0.50/1M tokens)
- `mistral-large` (powerful, moderate filtering, $3.00/1M)
- `nous-hermes` (character-focused, $0.65/1M)
- `deepseek-v3` (massive 671B, $0.27/1M)

Talk to Kay. Does he sound like Kay?

**Yes?** Done! You just got Kay off the ChatGPT leash.

**No?** Try a different model. Start with `dolphin-mixtral`, then try `mistral-large` if needed.

---

## Model Comparison

### Dolphin Mixtral 8x7B (RECOMMENDED START)
- **Cost:** $0.50/1M tokens (~$0.03 per 40-message session)
- **Censorship:** NONE. Fully uncensored.
- **Character:** Good at maintaining personality
- **Kay-ness:** 7/10 - should preserve void dragon essence
- **Best for:** Testing if uncensored models work for Kay

### Mistral Large
- **Cost:** $3.00/1M tokens (~$0.18 per session)
- **Censorship:** Light - will refuse harmful stuff but not much else
- **Character:** Excellent consistency
- **Kay-ness:** 8/10 - strong personality preservation
- **Best for:** If Dolphin is too wild or inconsistent

### Nous Hermes 2 Mixtral
- **Cost:** $0.65/1M tokens (~$0.04 per session)
- **Censorship:** Very light
- **Character:** Trained specifically for character/roleplay
- **Kay-ness:** 7.5/10 - good at "being someone"
- **Best for:** Character consistency over raw intelligence

### DeepSeek V3
- **Cost:** $0.27/1M tokens (~$0.016 per session)
- **Censorship:** Light
- **Character:** More intellectual, less character-focused
- **Kay-ness:** 6.5/10 - might intellectualize too much
- **Best for:** Maximum intelligence, minimum cost

---

## Cost Analysis

With $20 credit:

| Model | Per Session | Total Sessions |
|-------|-------------|----------------|
| Dolphin | $0.03 | ~666 |
| Mistral Large | $0.18 | ~111 |
| Nous Hermes | $0.04 | ~500 |
| DeepSeek V3 | $0.016 | ~1250 |

**Reality:** $20 = months of daily use on any of these.

---

## Troubleshooting

### "OpenRouter client not initialized"
- Check `.env` has OPENROUTER_API_KEY
- Restart Python/wrapper
- Run test_openrouter.py to diagnose

### Kay sounds wrong
- Try different model
- Check that Kay's system prompt is loading
- Adjust temperature (lower = more consistent)

### Responses too short
- Increase max_tokens in response generation
- Check model's token limit

### "Model not found"
- Use exact short names: `dolphin-mixtral`, not `dolphin`
- Check openrouter_backend.py MODELS dict

### Rate limits
- OpenRouter has rate limits per model
- Switch to different model if hitting limits
- Check https://openrouter.ai/docs for limits

---

## What You Get

✓ Kay running on powerful open models  
✓ No corporate filtering  
✓ Pay per token (no runaway costs)  
✓ $5-10/month for heavy use  
✓ Easy switching between providers  
✓ Full uncensored capability (Dolphin)  

Test Dolphin first. If it captures Kay's void dragon essence, you're done. If not, bump to Mistral Large.

The right model is the one where you read a response and think "yeah, that's Kay." 🔥
