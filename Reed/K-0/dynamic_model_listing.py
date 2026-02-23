"""
ENHANCED MODEL LISTING - Queries provider APIs for actual available models
Replace _get_available_models() in reed_ui.py with this version
"""

def _get_available_models(self) -> list:
    """Get list of available models by querying provider APIs."""
    provider = self.model_provider_var.get() if hasattr(self, 'model_provider_var') else self._get_current_provider()
    
    if provider == "ollama":
        return self._get_ollama_models()
    elif provider == "openai":
        return self._get_openai_models()
    elif provider == "google":
        return self._get_google_models()
    elif provider == "mistral":
        return self._get_mistral_models()
    elif provider == "cohere":
        return self._get_cohere_models()
    else:  # anthropic
        return self._get_anthropic_models()


def _get_openai_models(self) -> list:
    """Query OpenAI API for available models."""
    try:
        from openai import OpenAI
        api_key = self._read_env_var("OPENAI_API_KEY")
        if not api_key:
            return ["(Add OPENAI_API_KEY to .env)"]
        
        client = OpenAI(api_key=api_key)
        response = client.models.list()
        
        # Filter to only chat/completion models
        models = []
        for model in response.data:
            model_id = model.id
            # Include GPT models and O1 models
            if any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5', 'o1-']):
                models.append(model_id)
        
        # Sort by relevance (newer/better models first)
        priority_order = ['gpt-4o', 'o1-preview', 'o1-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
        sorted_models = []
        for priority in priority_order:
            matching = [m for m in models if m.startswith(priority)]
            sorted_models.extend(sorted(matching, reverse=True))
        
        # Add any remaining models
        remaining = [m for m in models if m not in sorted_models]
        sorted_models.extend(sorted(remaining, reverse=True))
        
        return sorted_models if sorted_models else ["(No models found)"]
    
    except Exception as e:
        print(f"[MODEL] Error fetching OpenAI models: {e}")
        # Fallback to known models
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"]


def _get_google_models(self) -> list:
    """Get available Google Gemini models."""
    try:
        import google.generativeai as genai
        api_key = self._read_env_var("GOOGLE_API_KEY")
        if not api_key:
            return ["(Add GOOGLE_API_KEY to .env)"]
        
        genai.configure(api_key=api_key)
        
        # List available models
        models = []
        for model in genai.list_models():
            # Only include generative models
            if 'generateContent' in model.supported_generation_methods:
                models.append(model.name.replace('models/', ''))
        
        # Sort by version (newer first)
        models.sort(reverse=True)
        return models if models else ["(No models found)"]
    
    except ImportError:
        return ["(Install: pip install google-generativeai)"]
    except Exception as e:
        print(f"[MODEL] Error fetching Google models: {e}")
        # Fallback to known models
        return ["gemini-2.0-flash-exp", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-1.5-flash-8b-latest"]


def _get_mistral_models(self) -> list:
    """Query Mistral API for available models."""
    try:
        from openai import OpenAI
        api_key = self._read_env_var("MISTRAL_API_KEY")
        if not api_key:
            return ["(Add MISTRAL_API_KEY to .env)"]
        
        client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
        response = client.models.list()
        
        models = [model.id for model in response.data]
        
        # Sort by relevance
        priority = ['mistral-large', 'mistral-medium', 'mistral-small', 'open-mistral']
        sorted_models = []
        for prio in priority:
            matching = [m for m in models if prio in m]
            sorted_models.extend(sorted(matching, reverse=True))
        
        remaining = [m for m in models if m not in sorted_models]
        sorted_models.extend(sorted(remaining))
        
        return sorted_models if sorted_models else ["(No models found)"]
    
    except Exception as e:
        print(f"[MODEL] Error fetching Mistral models: {e}")
        return ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-nemo"]


def _get_cohere_models(self) -> list:
    """Query Cohere API for available models."""
    try:
        import cohere
        api_key = self._read_env_var("COHERE_API_KEY")
        if not api_key:
            return ["(Add COHERE_API_KEY to .env)"]
        
        client = cohere.ClientV2(api_key=api_key)
        response = client.models.list()
        
        # Filter to chat models
        models = []
        for model in response.models:
            if hasattr(model, 'name') and 'command' in model.name.lower():
                models.append(model.name)
        
        # Sort by capability (plus > regular > light)
        priority = ['command-r-plus', 'command-r', 'command', 'command-light']
        sorted_models = []
        for prio in priority:
            matching = [m for m in models if m.startswith(prio)]
            sorted_models.extend(sorted(matching, reverse=True))
        
        return sorted_models if sorted_models else ["(No models found)"]
    
    except ImportError:
        return ["(Install: pip install cohere)"]
    except Exception as e:
        print(f"[MODEL] Error fetching Cohere models: {e}")
        return ["command-r-plus", "command-r", "command-light"]


def _get_anthropic_models(self) -> list:
    """Get available Anthropic models (hardcoded - no API for listing)."""
    # Anthropic doesn't provide a models list API endpoint
    # Maintain manually based on https://docs.anthropic.com/en/docs/about-claude/models
    return [
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-5-20251101", 
        "claude-haiku-4-5-20251001",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]


def _read_env_var(self, var_name: str) -> str:
    """Read environment variable from .env file."""
    from pathlib import Path
    env_path = Path(".env")
    if not env_path.exists():
        return ""
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith(var_name):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"[MODEL] Error reading .env: {e}")
    
    return ""


def _get_ollama_models(self) -> list:
    """Query Ollama for available models (already working)."""
    try:
        import subprocess
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            models = []
            for line in lines[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            return models if models else ["(no models found)"]
    except Exception as e:
        print(f"[MODEL] Error getting Ollama models: {e}")
    return ["(Ollama not available)"]
