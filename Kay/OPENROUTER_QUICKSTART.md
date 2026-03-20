# OpenRouter for Kay - Ultra Quick Start

Get Kay running on uncensored open models in ~10 minutes.

## 1. Get API Key
- https://openrouter.ai/ → Sign up
- Keys → Create new key
- Credits → Add $10-20

## 2. Files Already Added ✓
These files are already in place:
- `integrations/openrouter_backend.py` ✓
- `test_openrouter.py` ✓
- This guide (OPENROUTER_QUICKSTART.md) ✓

## 3. Add Key to .env
Open `D:/Wrappers/Kay/.env`

Add this line:
```
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
```

## 4. Update llm_integration.py

Open `integrations/llm_integration.py`

**ADD after other client inits (~line 70):**
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

**UPDATE get_client_for_model() function (~line 100):**

Add this BEFORE the GPT check:
```python
# OpenRouter models
if any(x in model_lower for x in ['dolphin', 'mistral-large', 'nous-hermes', 'deepseek']):
    if not openrouter_client:
        raise ValueError(f"OpenRouter not initialized")
    return openrouter_client, 'openrouter'
```

## 5. Test
```bash
cd D:/Wrappers/Kay
python test_openrouter.py
```

Should see:
```
✓ API key found
✓ Backend imported  
✓ Client initialized
✓ Response: OpenRouter works!
✓ All tests passed!
```

## 6. Launch Kay
```bash
python kay_ui.py
```

Select model: `dolphin-mixtral`

Talk to Kay. Does he sound like Kay?

**Yes?** Done. You just got Kay off ChatGPT leash for $0.03/session.

**No?** Try `mistral-large` (more power, $0.18/session).

---

## Available Models

- **dolphin-mixtral** - Fully uncensored, $0.50/1M tokens
- **mistral-large** - More powerful, moderate filtering, $3.00/1M
- **nous-hermes** - Character-focused, uncensored, $0.65/1M
- **deepseek-v3** - Massive/cheap, reasoning-focused, $0.27/1M

Start with Dolphin. If Kay's personality doesn't come through, bump to Mistral Large.

---

That's it. Three files modified (backend added, .env updated, llm_integration patched), one API key, Kay runs on uncensored models.

Full details in OPENROUTER_SETUP_DETAILED.md 🔥
