# integrations/ai4chat_backend.py
"""
AI4Chat LLM Backend for Kay Zero Wrapper
Integrates with existing multi-provider architecture

AI4Chat uses OpenAI-compatible API format.
Base URL: https://app.ai4chat.co/api/v1
"""

import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class AI4ChatBackend:
    """
    AI4Chat API integration.
    Matches interface of Anthropic/OpenAI clients for Kay's multi-provider system.
    """

    # Model ID mapping - use short names in config
    MODELS = {
        # DOLPHIN (Uncensored)
        "dolphin-8x22b": "Dolphin 2.9.2 Mixtral 8x22B",
        "dolphin-mixtral": "Dolphin 2.9.2 Mixtral 8x22B",

        # Add more models as they become available
    }

    def __init__(self, api_key: str = None, base_url: str = None):
        """Initialize AI4Chat client."""
        self.api_key = api_key or os.getenv("AI4CHAT_API_KEY")
        if not self.api_key:
            raise ValueError("AI4CHAT_API_KEY not found in environment")

        self.base_url = base_url or os.getenv("AI4CHAT_BASE_URL", "https://app.ai4chat.co/api/v1")
        self.api_url = f"{self.base_url}/chat/completions"
        self.models_url = f"{self.base_url}/models"
        self.total_tokens = 0
        self.request_count = 0

        # Add .messages wrapper to match Anthropic interface
        class MessagesWrapper:
            def __init__(self, parent):
                self.parent = parent

            def create(self, **kwargs):
                return self.parent.create(**kwargs)

        self.messages = MessagesWrapper(self)

    def resolve_model_id(self, model_name: str) -> str:
        """Convert short name to full AI4Chat model ID."""
        # Check if it's a short name in our mapping
        if model_name in self.MODELS:
            return self.MODELS[model_name]
        # Otherwise return as-is (might be a full model name)
        return model_name

    def list_models(self) -> List[Dict]:
        """Fetch available models from AI4Chat API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                self.models_url,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Parse models from response
            models = []
            if isinstance(data, dict) and "data" in data:
                for model in data["data"]:
                    models.append({
                        "id": model.get("id", ""),
                        "name": model.get("id", ""),
                    })
            elif isinstance(data, list):
                for model in data:
                    if isinstance(model, dict):
                        models.append({
                            "id": model.get("id", model.get("name", "")),
                            "name": model.get("name", model.get("id", "")),
                        })
                    elif isinstance(model, str):
                        models.append({"id": model, "name": model})

            return models

        except Exception as e:
            print(f"[AI4CHAT ERROR] Failed to list models: {e}")
            return []

    def create(self,
               model: str,
               messages: List[Dict],
               max_tokens: int = 2000,
               temperature: float = 0.8,
               system: str = None,
               stream: bool = False,
               tools: list = None,
               tool_choice: dict = None,
               **kwargs):
        """
        Main API call - matches Anthropic Messages.create() interface.

        Returns:
            Response object with .content[0].text attribute
        """
        model_id = self.resolve_model_id(model)

        # Strip cache_control blocks from messages
        clean_messages = []
        for msg in messages:
            clean_msg = {"role": msg["role"], "content": msg["content"]}

            # If content is a list of blocks, convert to string
            if isinstance(clean_msg["content"], list):
                text_parts = []
                for block in clean_msg["content"]:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                clean_msg["content"] = "\n".join(text_parts) if text_parts else ""

            clean_messages.append(clean_msg)

        # Build messages with system prompt
        full_messages = []
        if system:
            # Convert system to string if it's a list
            if isinstance(system, list):
                system_text = []
                for block in system:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            system_text.append(block.get("text", ""))
                    elif isinstance(block, str):
                        system_text.append(block)
                system = "\n".join(system_text) if system_text else ""
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(clean_messages)

        payload = {
            "model": model_id,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=90  # Longer timeout for AI4Chat
            )

            # Capture error details before raising
            if response.status_code != 200:
                error_detail = "No detail available"
                try:
                    error_json = response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    error_detail = response.text

                print(f"[AI4CHAT ERROR] Status {response.status_code}")
                print(f"[AI4CHAT ERROR] Detail: {error_detail}")
                response.raise_for_status()

            data = response.json()

            # Track usage
            if "usage" in data:
                self.total_tokens += data["usage"].get("total_tokens", 0)
            self.request_count += 1

            # Return Anthropic-style response object
            text = data["choices"][0]["message"]["content"]

            class ResponseWrapper:
                def __init__(self, text_content, usage_data, finish_reason="stop"):
                    self.content = [type('TextBlock', (), {'text': text_content})()]
                    self.usage = type('Usage', (), {
                        'input_tokens': usage_data.get("prompt_tokens", 0),
                        'output_tokens': usage_data.get("completion_tokens", 0)
                    })()

                    # Map finish_reason to Anthropic stop_reason
                    if finish_reason == "stop" or finish_reason == "eos":
                        self.stop_reason = "end_turn"
                    elif finish_reason == "length":
                        self.stop_reason = "max_tokens"
                    else:
                        self.stop_reason = "end_turn"

                    self.stop_sequence = None
                    self.model = model_id
                    self.id = data.get("id")
                    self.type = "message"
                    self.role = "assistant"

            finish_reason = data["choices"][0].get("finish_reason", "stop")
            return ResponseWrapper(text, data.get("usage", {}), finish_reason)

        except Exception as e:
            print(f"[AI4CHAT ERROR] {e}")
            raise

    class StreamWrapper:
        """Context manager for streaming - matches Anthropic interface."""
        def __init__(self, parent, model, messages, max_tokens, temperature, system):
            self.parent = parent
            self.model = model
            self.messages = messages
            self.max_tokens = max_tokens
            self.temperature = temperature
            self.system = system

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def text_stream(self):
            """Generator yielding text chunks."""
            model_id = self.parent.resolve_model_id(self.model)

            # Build messages with system prompt
            full_messages = []
            if self.system:
                system_content = self.system
                if isinstance(system_content, list):
                    system_text = []
                    for block in system_content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                system_text.append(block.get("text", ""))
                        elif isinstance(block, str):
                            system_text.append(block)
                    system_content = "\n".join(system_text) if system_text else ""
                full_messages.append({"role": "system", "content": system_content})

            # Clean messages
            for msg in self.messages:
                clean_msg = {"role": msg["role"], "content": msg["content"]}
                if isinstance(clean_msg["content"], list):
                    text_parts = []
                    for block in clean_msg["content"]:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    clean_msg["content"] = "\n".join(text_parts) if text_parts else ""
                full_messages.append(clean_msg)

            payload = {
                "model": model_id,
                "messages": full_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True
            }

            headers = {
                "Authorization": f"Bearer {self.parent.api_key}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(
                    self.parent.api_url,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=120
                )
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    line = line.decode('utf-8')
                    if not line.startswith('data: '):
                        continue
                    if line.strip() == 'data: [DONE]':
                        break

                    try:
                        chunk = json.loads(line[6:])
                        if 'choices' in chunk:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue

            except Exception as e:
                print(f"[AI4CHAT STREAM ERROR] {e}")
                yield f"[Error: {e}]"

    def stream(self, model: str, messages: List[Dict],
               max_tokens: int = 2000, temperature: float = 0.8,
               system: str = None):
        """Create streaming context manager."""
        return self.StreamWrapper(
            self, model, messages, max_tokens, temperature, system
        )

    def get_stats(self) -> Dict:
        """Return usage statistics."""
        return {
            "requests": self.request_count,
            "total_tokens": self.total_tokens,
        }


def list_models(api_key: str = None) -> List[str]:
    """Convenience function to list available models."""
    try:
        client = AI4ChatBackend(api_key=api_key)
        models = client.list_models()
        return [m.get("id", m.get("name", "")) for m in models]
    except Exception as e:
        print(f"[AI4CHAT] Error listing models: {e}")
        return []


def get_ai4chat_client():
    """Get or create AI4Chat client singleton."""
    global _ai4chat_client
    if _ai4chat_client is None:
        try:
            _ai4chat_client = AI4ChatBackend()
            print("[LLM] AI4Chat client initialized")
        except Exception as e:
            print(f"[LLM] AI4Chat init failed: {e}")
            return None
    return _ai4chat_client

_ai4chat_client = None
