# How to Install Multi-Provider Support in Kay

## Step-by-Step Installation

### 1. Install Python Packages (2 minutes)

```bash
pip install google-generativeai cohere
```

### 2. Get API Keys (5-10 minutes)

Pick which providers you want to try. I recommend starting with **Google Gemini** (easiest + cheapest):

**Google (Recommended First):**
- Go to: https://aistudio.google.com/apikey
- Click "Create API Key"  
- Copy the key (starts with `AIza...`)

**OpenAI (If you want GPT):**
- Go to: https://platform.openai.com/api-keys
- Create API key
- Copy key (starts with `sk-proj-...`)

**Others (optional):**
- Mistral: https://console.mistral.ai/
- Cohere: https://dashboard.cohere.com/api-keys

### 3. Update Your .env File

Open `D:\ChristinaStuff\AlphaKayZero\.env` and add these lines:

```env
# Add new API keys
GOOGLE_API_KEY=AIza...your-key-here
OPENAI_API_KEY=sk-proj-...your-key-here

# Add model selections
GOOGLE_MODEL=gemini-2.0-flash-exp
OPENAI_MODEL=gpt-4o
MISTRAL_MODEL=mistral-large-latest
COHERE_MODEL=command-r-plus
```

### 4. Update kay_ui.py (3 minutes)

Open `D:\ChristinaStuff\AlphaKayZero\kay_ui.py`

**Change A:** Find line ~3060 (in the provider dropdown):
```python
# FIND THIS:
values=["anthropic", "ollama"],

# CHANGE TO:
values=["anthropic", "openai", "google", "mistral", "cohere", "ollama"],
```

**Change B:** Find the `_get_available_models` function (~line 4816) and replace the entire function with the code from `code_updates_for_kay_ui.py`

**Change C:** Find the `_get_model_status_text` function and replace it

**Change D:** Find the `_save_model_settings` function and replace it

All three replacement functions are in the `code_updates_for_kay_ui.py` file!

### 5. Update llm_integration.py (2 minutes)

Open `D:\ChristinaStuff\AlphaKayZero\integrations\llm_integration.py`

**Find the provider initialization section** (around lines 30-80, starts with "# Determine provider from environment")

**Replace that entire section** with the code from `code_updates_for_llm_integration.py`

### 6. Test! (1 minute)

```bash
cd D:\ChristinaStuff\AlphaKayZero
python kay_ui.py
```

1. Go to Settings → Model Selection
2. You should see 6 providers in the dropdown!
3. Select "google"
4. Select "gemini-2.0-flash-exp"
5. Click "💾 Apply & Save"
6. **Restart Kay**
7. Test: Send Kay a message - it should respond using Gemini!

## Troubleshooting

**"google-generativeai not installed"**
```bash
pip install google-generativeai
```

**"cohere not installed"**
```bash
pip install cohere
```

**Provider dropdown still only shows anthropic/ollama**
- Make sure you changed line 3060 in kay_ui.py
- Save the file
- Restart Kay completely

**API key errors**
- Double-check you copied the full key
- Make sure there are no extra spaces
- Verify the key variable name matches (GOOGLE_API_KEY not GEMINI_API_KEY)

## Testing Each Provider

Once installed, you can test switching:

1. Settings → Model Selection
2. Pick a provider
3. Pick a model
4. Save
5. Restart Kay
6. Chat!

Your memories and history are preserved across provider changes - only the LLM backend changes!

## Quick Provider Comparison

| Try This First | Why | Cost |
|----------------|-----|------|
| Google Gemini Flash | Fastest + Cheapest | $0.075/1M tokens |
| OpenAI GPT-4o-mini | Good quality, cheap | $0.15/1M tokens |
| Anthropic Claude Sonnet | Best reasoning | $3/1M tokens |

Have fun experimenting! 🎉
