"""
CODE TO ADD TO integrations/llm_integration.py
Replace the provider initialization section (around lines 30-80)
"""

import anthropic
from openai import OpenAI  # Used for OpenAI, Mistral, and Ollama

# Determine provider from environment
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "anthropic").lower()

# Initialize ALL clients
anthropic_client = None
openai_client = None
google_client = None
mistral_client = None
cohere_client = None
ollama_client = None
MODEL = None

try:
    # ANTHROPIC
    if MODEL_PROVIDER == "anthropic" or os.getenv("ANTHROPIC_API_KEY"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            anthropic_client = anthropic.Anthropic(api_key=api_key)
            if MODEL_PROVIDER == "anthropic":
                MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
                print(f"[LLM] Anthropic client initialized with model {MODEL}")
    
    # OPENAI
    if MODEL_PROVIDER == "openai" or os.getenv("OPENAI_API_KEY"):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            openai_client = OpenAI(api_key=api_key)
            if MODEL_PROVIDER == "openai":
                MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
                print(f"[LLM] OpenAI client initialized with model {MODEL}")
    
    # GOOGLE GEMINI
    if MODEL_PROVIDER == "google" or os.getenv("GOOGLE_API_KEY"):
        try:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                if MODEL_PROVIDER == "google":
                    MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")
                    google_client = genai.GenerativeModel(MODEL)
                    print(f"[LLM] Google Gemini client initialized with model {MODEL}")
        except ImportError:
            print("[LLM] Google Generative AI not installed. Run: pip install google-generativeai")
    
    # MISTRAL (uses OpenAI-compatible API)
    if MODEL_PROVIDER == "mistral" or os.getenv("MISTRAL_API_KEY"):
        api_key = os.getenv("MISTRAL_API_KEY")
        if api_key:
            mistral_client = OpenAI(
                api_key=api_key,
                base_url="https://api.mistral.ai/v1"
            )
            if MODEL_PROVIDER == "mistral":
                MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
                print(f"[LLM] Mistral client initialized with model {MODEL}")
    
    # COHERE
    if MODEL_PROVIDER == "cohere" or os.getenv("COHERE_API_KEY"):
        try:
            import cohere
            api_key = os.getenv("COHERE_API_KEY")
            if api_key:
                cohere_client = cohere.ClientV2(api_key=api_key)
                if MODEL_PROVIDER == "cohere":
                    MODEL = os.getenv("COHERE_MODEL", "command-r-plus")
                    print(f"[LLM] Cohere client initialized with model {MODEL}")
        except ImportError:
            print("[LLM] Cohere not installed. Run: pip install cohere")
    
    # OLLAMA (local)
    if MODEL_PROVIDER == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_client = OpenAI(
            base_url=f"{base_url}/v1",
            api_key="ollama"  # Dummy key
        )
        MODEL = os.getenv("OLLAMA_MODEL", "dolphin-mistral:7b")
        print(f"[LLM] Ollama client initialized with model {MODEL} at {base_url}")

except Exception as e:
    print(f"[LLM INIT ERROR] {e}")

# Set active client
if MODEL_PROVIDER == "anthropic":
    client = anthropic_client
elif MODEL_PROVIDER == "openai":
    client = openai_client
elif MODEL_PROVIDER == "google":
    client = google_client
elif MODEL_PROVIDER == "mistral":
    client = mistral_client
elif MODEL_PROVIDER == "cohere":
    client = cohere_client
elif MODEL_PROVIDER == "ollama":
    client = ollama_client
else:
    client = None
