# integrations/openrouter_backend.py
"""
OpenRouter LLM Backend for Reed Wrapper
Integrates with existing multi-provider architecture
"""

import os
import json
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class OpenRouterBackend:
    """
    OpenRouter API integration.
    Matches interface of Anthropic/OpenAI clients for Reed's multi-provider system.
    """
    
    # Model ID mapping - use short names in config
    # Updated Feb 2026 with current OpenRouter models
    MODELS = {
        # FREE UNCENSORED MODELS (great for testing!)
        "dolphin-venice-free": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "dolphin-r1-free": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        
        # PAID UNCENSORED MODELS
        "dolphin-3.0": "cognitivecomputations/dolphin3.0-mistral-24b",
        "dolphin-3.0-8x22b": "cognitivecomputations/dolphin-mixtral-8x22b",
        "dolphin-8x22b": "cognitivecomputations/dolphin-mixtral-8x22b",
        
        # OTHER UNCENSORED/GOOD MODELS
        "nous-hermes": "nousresearch/hermes-3-llama-3.1-405b",
        "mistral-large": "mistralai/mistral-large-2407",
        "deepseek-v3": "deepseek/deepseek-chat",
        "llama-70b": "meta-llama/llama-3-70b-instruct",
    }
    
    def __init__(self, api_key: str = None):
        """Initialize OpenRouter client."""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.total_tokens = 0
        self.request_count = 0
        
        # Add .messages wrapper to match Anthropic interface
        # Reed's code calls client.messages.create() not client.create()
        class MessagesWrapper:
            def __init__(self, parent):
                self.parent = parent
            
            def create(self, **kwargs):
                return self.parent.create(**kwargs)
        
        self.messages = MessagesWrapper(self)
    
    def resolve_model_id(self, model_name: str) -> str:
        """Convert short name to full OpenRouter model ID."""
        if "/" in model_name:
            return model_name  # Already full ID
        return self.MODELS.get(model_name, model_name)
    
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
            tools: Tool definitions (ignored - OpenRouter doesn't support native tool use)
            tool_choice: Tool selection strategy (ignored)
            **kwargs: Other params like cache_control, metadata (ignored)
        
        Returns:
            Response object with .content[0].text attribute
        """
        model_id = self.resolve_model_id(model)
        
        # Reduce max_tokens for free models with small context windows
        if "free" in model_id.lower() and max_tokens > 2000:
            print(f"[OPENROUTER] Reducing max_tokens from {max_tokens} to 2000 for free model")
            max_tokens = 2000
        
        # Strip cache_control blocks from messages (OpenRouter doesn't support them)
        clean_messages = []
        for msg in messages:
            clean_msg = {"role": msg["role"], "content": msg["content"]}
            
            # If content is a list of blocks, strip cache_control from each
            if isinstance(clean_msg["content"], list):
                clean_content = []
                for block in clean_msg["content"]:
                    if isinstance(block, dict):
                        # Copy block without cache_control
                        clean_block = {k: v for k, v in block.items() if k != "cache_control"}
                        clean_content.append(clean_block)
                    else:
                        clean_content.append(block)
                clean_msg["content"] = clean_content
            
            clean_messages.append(clean_msg)
        
        # Build messages
        full_messages = []
        if system:
            # Strip cache_control from system message too
            if isinstance(system, list):
                clean_system = []
                for block in system:
                    if isinstance(block, dict):
                        clean_block = {k: v for k, v in block.items() if k != "cache_control"}
                        clean_system.append(clean_block)
                    else:
                        clean_system.append(block)
                full_messages.append({"role": "system", "content": clean_system})
            else:
                full_messages.append({"role": "system", "content": system})
        full_messages.extend(clean_messages)
        
        payload = {
            "model": model_id,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # NOTE: Most OpenRouter models don't support Anthropic-style tool use
        # Tools are stripped to avoid 404 errors
        # Kay will still work - he just responds in text instead of calling functions
        if False:  # Disabled - tools cause 404 on most OpenRouter models
            if tools:
                payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/ariluscristatus/ReedWrapper",
            "X-Title": "Reed Wrapper",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Capture error details before raising
            if response.status_code != 200:
                error_detail = "No detail available"
                try:
                    error_json = response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    error_detail = response.text
                
                print(f"[OPENROUTER ERROR] Status {response.status_code}")
                print(f"[OPENROUTER ERROR] Detail: {error_detail}")
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

                    # Map OpenRouter finish_reason to Anthropic stop_reason
                    # OpenRouter: "stop", "length", "content_filter", "tool_calls"
                    # Anthropic: "end_turn", "max_tokens", "stop_sequence"
                    if finish_reason == "stop":
                        self.stop_reason = "end_turn"
                    elif finish_reason == "length":
                        self.stop_reason = "max_tokens"
                    else:
                        self.stop_reason = "end_turn"  # Default

                    self.stop_sequence = None
                    self.model = None
                    self.id = None
                    self.type = "message"
                    self.role = "assistant"

            # Get finish_reason from response
            finish_reason = data["choices"][0].get("finish_reason", "stop")

            return ResponseWrapper(text, data.get("usage", {}), finish_reason)
            
        except Exception as e:
            print(f"[OPENROUTER ERROR] {e}")
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
            
            full_messages = []
            if self.system:
                full_messages.append({"role": "system", "content": self.system})
            full_messages.extend(self.messages)
            
            payload = {
                "model": model_id,
                "messages": full_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.parent.api_key}",
                "HTTP-Referer": "https://github.com/ariluscristatus/ReedWrapper",
                "X-Title": "Reed Wrapper",
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
                print(f"[OPENROUTER STREAM ERROR] {e}")
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


def get_openrouter_client():
    """Get or create OpenRouter client singleton."""
    global _openrouter_client
    if _openrouter_client is None:
        try:
            _openrouter_client = OpenRouterBackend()
            print("[LLM] OpenRouter client initialized")
        except Exception as e:
            print(f"[LLM] OpenRouter init failed: {e}")
            return None
    return _openrouter_client

_openrouter_client = None
