# integrations/together_backend.py
"""
Together.ai LLM Backend for Kay Zero Wrapper
Integrates with existing multi-provider architecture

Together.ai uses OpenAI-compatible API format.
"""

import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class TogetherBackend:
    """
    Together.ai API integration.
    Matches interface of Anthropic/OpenAI clients for Kay's multi-provider system.
    """

    # Model ID mapping - use short names in config
    # Updated Feb 2026 with current Together.ai models
    MODELS = {
        # RECOMMENDED STARTER
        "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-Turbo",

        # LLAMA 4 SERIES
        "llama-4-maverick": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "llama-4-scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",

        # LLAMA 3.1 SERIES
        "llama-3.1-405b": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",

        # DEEPSEEK
        "deepseek-r1": "deepseek-ai/DeepSeek-R1",
        "deepseek-v3.1": "deepseek-ai/DeepSeek-V3.1",
        "deepseek-v3": "deepseek-ai/DeepSeek-V3",

        # QWEN MODELS
        "qwen-3-235b": "Qwen/Qwen3-235B-A22B-fp8-tput",
        "qwen-2.5-72b": "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "qwen-coder": "Qwen/Qwen2.5-Coder-32B-Instruct",

        # MISTRAL MODELS
        "mistral-small": "mistralai/Mistral-Small-24B-Instruct-2501",
        "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.2",
        "ministral-8b": "mistralai/Ministral-8B-Instruct-2410",

        # GEMMA
        "gemma-2-27b": "google/gemma-2-27b-it",
        "gemma-2-9b": "google/gemma-2-9b-it",
    }

    def __init__(self, api_key: str = None):
        """Initialize Together.ai client."""
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY not found in environment")

        self.api_url = "https://api.together.xyz/v1/chat/completions"
        self.models_url = "https://api.together.xyz/v1/models"
        self.total_tokens = 0
        self.request_count = 0

        # Add .messages wrapper to match Anthropic interface
        # Kay's code calls client.messages.create() not client.create()
        class MessagesWrapper:
            def __init__(self, parent):
                self.parent = parent

            def create(self, **kwargs):
                return self.parent.create(**kwargs)

        self.messages = MessagesWrapper(self)

    def resolve_model_id(self, model_name: str) -> str:
        """Convert short name to full Together.ai model ID."""
        if "/" in model_name:
            return model_name  # Already full ID
        return self.MODELS.get(model_name, model_name)

    def list_models(self) -> List[Dict]:
        """Fetch available models from Together.ai API."""
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

            # Filter to chat/instruct models
            chat_models = []
            for model in data:
                model_id = model.get("id", "")
                model_type = model.get("type", "")
                # Include chat and language models
                if model_type in ["chat", "language"] or "instruct" in model_id.lower() or "chat" in model_id.lower():
                    chat_models.append({
                        "id": model_id,
                        "name": model.get("display_name", model_id),
                        "context_length": model.get("context_length", 4096),
                        "pricing": model.get("pricing", {})
                    })

            return chat_models

        except Exception as e:
            print(f"[TOGETHER ERROR] Failed to list models: {e}")
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
               **kwargs):  # Catch any other Anthropic-specific params
        """
        Main API call - matches Anthropic Messages.create() interface.

        Args:
            tools: Tool definitions (Together.ai supports function calling on some models)
            tool_choice: Tool selection strategy
            **kwargs: Other params like cache_control, metadata (ignored)

        Returns:
            Response object with .content[0].text attribute
        """
        model_id = self.resolve_model_id(model)

        # Strip cache_control blocks from messages (Together.ai doesn't support them)
        clean_messages = []
        for msg in messages:
            clean_msg = {"role": msg["role"], "content": msg["content"]}

            # If content is a list of blocks, convert to string or strip cache_control
            if isinstance(clean_msg["content"], list):
                # Convert list of content blocks to single string
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

        # Together.ai supports function calling on some models
        # But we disable it for compatibility with Kay's current architecture
        if False:  # Disabled for now
            if tools:
                payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            # Capture error details before raising
            if response.status_code != 200:
                error_detail = "No detail available"
                try:
                    error_json = response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    error_detail = response.text

                print(f"[TOGETHER ERROR] Status {response.status_code}")
                print(f"[TOGETHER ERROR] Detail: {error_detail}")
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

                    # Map Together.ai finish_reason to Anthropic stop_reason
                    if finish_reason == "stop" or finish_reason == "eos":
                        self.stop_reason = "end_turn"
                    elif finish_reason == "length":
                        self.stop_reason = "max_tokens"
                    else:
                        self.stop_reason = "end_turn"  # Default

                    self.stop_sequence = None
                    self.model = model_id
                    self.id = data.get("id")
                    self.type = "message"
                    self.role = "assistant"

            # Get finish_reason from response
            finish_reason = data["choices"][0].get("finish_reason", "stop")

            return ResponseWrapper(text, data.get("usage", {}), finish_reason)

        except Exception as e:
            print(f"[TOGETHER ERROR] {e}")
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
                # Convert system to string if it's a list
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
                print(f"[TOGETHER STREAM ERROR] {e}")
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


def get_together_client():
    """Get or create Together.ai client singleton."""
    global _together_client
    if _together_client is None:
        try:
            _together_client = TogetherBackend()
            print("[LLM] Together.ai client initialized")
        except Exception as e:
            print(f"[LLM] Together.ai init failed: {e}")
            return None
    return _together_client

_together_client = None
