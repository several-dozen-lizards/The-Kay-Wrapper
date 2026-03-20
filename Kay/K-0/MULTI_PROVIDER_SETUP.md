# Kay Multi-Provider LLM Setup Instructions

## Overview
Kay now supports 6 LLM providers:
- **Anthropic** (Claude) - Best for reasoning, tool use, caching
- **OpenAI** (GPT) - Industry standard, good all-around
- **Google** (Gemini) - Massive context (2M tokens), fast
- **Mistral** - European alternative, good pricing
- **Cohere** - Command-R models, RAG-optimized
- **Ollama** - Local models, fully private

## Installation Steps

### 1. Install Required Python Packages

```bash
# Core (already installed)
pip install anthropic openai python-dotenv

# NEW: Install additional provider SDKs
pip install google-generativeai  # For Google Gemini
pip install cohere               # For Cohere
```

### 2. Get API Keys

#### Anthropic (Claude)
1. Go to: https://console.anthropic.com/
2. Sign up/login
3. Go to "API Keys" section
4. Create new key
5. Add to .env as `ANTHROPIC_API_KEY=sk-ant-...`

#### OpenAI (GPT)
1. Go to: https://platform.openai.com/
2. Sign up/login
3. Go to "API Keys" section  
4. Create new key
5. Add to .env as `OPENAI_API_KEY=sk-proj-...`

#### Google (Gemini)
1. Go to: https://aistudio.google.com/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Add to .env as `GOOGLE_API_KEY=AIza...`

#### Mistral
1. Go to: https://console.mistral.ai/
2. Sign up/login
3. Go to "API Keys"
4. Create new key
5. Add to .env as `MISTRAL_API_KEY=...`

#### Cohere
1. Go to: https://dashboard.cohere.com/
2. Sign up/login
3. Go to "API Keys"
4. Create new key
5. Add to .env as `COHERE_API_KEY=...`

#### Ollama (Local - No API Key Needed)
1. Download from: https://ollama.ai/
2. Install Ollama
3. Pull models: `ollama pull dolphin-mistral`
4. Models run on your own hardware (private, no API costs)

### 3. Update Your .env File

Add these lines to `D:\Wrappers\Kay\.env`:

```env
# Set your preferred provider
MODEL_PROVIDER=anthropic

# Add ALL API keys (Kay will use whichever provider you select)
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
MISTRAL_API_KEY=your-key-here
COHERE_API_KEY=your-key-here

# Set default models for each provider
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
OPENAI_MODEL=gpt-4o
GOOGLE_MODEL=gemini-2.0-flash-exp
MISTRAL_MODEL=mistral-large-latest
COHERE_MODEL=command-r-plus
OLLAMA_MODEL=dolphin-mistral:7b
```

## Troubleshooting

### "No LLM client initialized"
- Check .env has correct API key for selected provider
- Verify key format matches provider's format
- Restart Kay after adding/changing keys

### "google-generativeai not installed"
```bash
pip install google-generativeai
```

### "cohere not installed"
```bash
pip install cohere
```

## API Key Security

⚠️ **IMPORTANT**: Never commit .env to git!

```bash
# Verify .env is in .gitignore
git check-ignore .env  # Should output: .env
```
