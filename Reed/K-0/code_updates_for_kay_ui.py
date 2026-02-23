"""
CODE TO ADD TO reed_ui.py
Replace these three functions with the enhanced versions below
"""

def _get_available_models(self) -> list:
    """Get list of available models based on current provider."""
    provider = self.model_provider_var.get() if hasattr(self, 'model_provider_var') else self._get_current_provider()
    
    if provider == "ollama":
        return self._get_ollama_models()
    elif provider == "openai":
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"]
    elif provider == "google":
        return ["gemini-2.0-flash-exp", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-1.5-flash-8b-latest"]
    elif provider == "mistral":
        return ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-nemo"]
    elif provider == "cohere":
        return ["command-r-plus", "command-r", "command-light"]
    else:  # anthropic
        return ["claude-sonnet-4-5-20250929", "claude-opus-4-5-20251101", "claude-haiku-4-5-20251001", "claude-3-haiku-20240307"]


def _get_model_status_text(self) -> str:
    """Get status text for current model configuration."""
    provider = self.model_provider_var.get() if hasattr(self, 'model_provider_var') else self._get_current_provider()
    model = self.model_name_var.get() if hasattr(self, 'model_name_var') else self._get_current_model()
    
    provider_display = {
        "ollama": "Local", "anthropic": "Anthropic API", "openai": "OpenAI API",
        "google": "Google API", "mistral": "Mistral API", "cohere": "Cohere API"
    }
    return f"{provider_display.get(provider, provider)}: {model}"


def _save_model_settings(self):
    """Save model settings to .env file."""
    import re
    from pathlib import Path
    
    env_path = Path(".env")
    if not env_path.exists():
        print("[MODEL] .env file not found!")
        return
    
    provider = self.model_provider_var.get()
    model = self.model_name_var.get()
    
    # Read current .env
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update MODEL_PROVIDER
    if "MODEL_PROVIDER=" in content:
        content = re.sub(r'MODEL_PROVIDER=\w+', f'MODEL_PROVIDER={provider}', content)
    else:
        content += f"\nMODEL_PROVIDER={provider}\n"
    
    # Update model based on provider
    model_var_map = {
        "ollama": "OLLAMA_MODEL", "anthropic": "ANTHROPIC_MODEL", "openai": "OPENAI_MODEL",
        "google": "GOOGLE_MODEL", "mistral": "MISTRAL_MODEL", "cohere": "COHERE_MODEL"
    }
    var_name = model_var_map.get(provider)
    if var_name:
        pattern = f'{var_name}=[^\\n]*'
        if re.search(pattern, content):
            content = re.sub(pattern, f'{var_name}={model}', content)
        else:
            content += f"\n{var_name}={model}\n"
    
    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[MODEL] Settings saved: provider={provider}, model={model}")
    
    # Update status
    if hasattr(self, 'model_status_label'):
        self.model_status_label.configure(text="✓ Saved! Restart Kay to apply.", text_color=self.palette["accent"])
        self.after(3000, lambda: self.model_status_label.configure(
            text=self._get_model_status_text(), text_color=self.palette["muted"]))


# ALSO UPDATE THIS LINE (around line 3060):
# Change:    values=["anthropic", "ollama"],
# To:        values=["anthropic", "openai", "google", "mistral", "cohere", "ollama"],
