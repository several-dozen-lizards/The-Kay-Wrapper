"""
PERIPHERAL ROUTER — Multi-Provider Dual-Model Architecture
============================================================

Routes LLM requests to either the primary model (conversation, personality)
or a peripheral model (sensory processing, extraction, summarization).

The peripheral model can be:
- Local Ollama (free, private, lowest latency)
- Cerebras free tier (1M tokens/day free, fast)
- Groq free tier (generous free limits, fast)
- OpenRouter free models (already integrated)
- Together.ai (cheap fallback)

All use OpenAI-compatible API, so a single client handles all providers.

Peripheral model handles:
- Sensory compression (oscillator state → felt summary)
- Emotion extraction (response text → emotion labels)
- Memory relevance scoring (query → relevance scores)
- Session summarization (conversation → summary)
- Background reflection (memory → insights)

Primary model handles:
- All conversation with the entity's personality
- Tool use decisions
- Creative output
- Complex reasoning

Design principle: The peripheral model is the entity's cerebellum/thalamus.
It processes raw sensory and memory data into compressed summaries
that the primary model receives as "felt sense" rather than raw numbers.
"""

import os
import json
from typing import Optional, Dict, Any, List, Tuple

try:
    from openai import OpenAI  # All providers use OpenAI-compatible API
except ImportError:
    OpenAI = None


# ═══════════════════════════════════════════════════════════════
# PROVIDER PRIORITY CHAIN
# ═══════════════════════════════════════════════════════════════
# Tries each provider in order until one works.
# All use OpenAI-compatible API — single client handles all.

PERIPHERAL_PROVIDERS = [
    # Priority 1: Local Ollama (free, private, lowest latency)
    {
        "name": "ollama",
        "type": "openai_compatible",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": None,  # Will use PERIPHERAL_MODEL or OLLAMA_MODEL env var
        "default_model": "qwen2.5:1.5b",
        "env_key": None,  # No API key needed
        "health_check": "models",  # Check by listing models
    },
    # Priority 2: Cerebras free tier (1M tokens/day free, 1800 tok/s)
    {
        "name": "cerebras",
        "type": "openai_compatible",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": None,  # From env
        "model": "llama3.1-8b",
        "default_model": "llama3.1-8b",
        "env_key": "CEREBRAS_API_KEY",
        "health_check": "completion",  # Check by minimal completion
    },
    # Priority 3: Groq free tier (fast, generous free limits)
    {
        "name": "groq",
        "type": "openai_compatible",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": None,  # From env
        "model": "llama-3.1-8b-instant",
        "default_model": "llama-3.1-8b-instant",
        "env_key": "GROQ_API_KEY",
        "health_check": "completion",
    },
    # Priority 4: OpenRouter free models
    {
        "name": "openrouter",
        "type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": None,  # From env
        "model": "meta-llama/llama-3.2-3b-instruct:free",
        "default_model": "meta-llama/llama-3.2-3b-instruct:free",
        "env_key": "OPENROUTER_API_KEY",
        "health_check": "completion",
    },
    # Priority 5: Together.ai (cheap, ~$0.18/M tokens)
    {
        "name": "together",
        "type": "openai_compatible",
        "base_url": "https://api.together.xyz/v1",
        "api_key": None,  # From env
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "health_check": "completion",
    },
]


class PeripheralRouter:
    """Routes requests to peripheral model with multi-provider fallback."""

    def __init__(
        self,
        providers: list = None,
        enabled: bool = None,
        fallback_to_rules: bool = True,
    ):
        # Check environment for enabled flag
        if enabled is None:
            enabled = os.getenv("PERIPHERAL_ENABLED", "true").lower() in ("true", "1", "yes")

        self.enabled = enabled
        self.fallback_to_rules = fallback_to_rules

        # Active provider state
        self.active_provider = None
        self.active_client = None
        self.active_model = None
        self._available = False

        if not enabled:
            print("[PERIPHERAL] Disabled via PERIPHERAL_ENABLED=false")
            return

        if OpenAI is None:
            print("[PERIPHERAL] OpenAI library not installed, falling back to rules")
            return

        # Try providers in priority order
        providers = providers or PERIPHERAL_PROVIDERS

        for provider in providers:
            try:
                # Get API key
                api_key = provider.get("api_key")
                if api_key is None and provider.get("env_key"):
                    api_key = os.getenv(provider["env_key"])
                    if not api_key:
                        continue  # Skip if no API key configured

                # Get model (check env overrides for ollama)
                model = provider.get("model")
                if provider["name"] == "ollama":
                    model = os.getenv("PERIPHERAL_MODEL") or os.getenv("OLLAMA_MODEL") or provider["default_model"]
                elif model is None:
                    model = provider["default_model"]

                # Create client
                client = OpenAI(
                    base_url=provider["base_url"],
                    api_key=api_key or "none",
                )

                # Health check
                if provider.get("health_check") == "models":
                    # Ollama: check if server is running by listing models
                    client.models.list()
                else:
                    # Cloud providers: verify with minimal completion
                    client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "hi"}],
                        max_tokens=1,
                    )

                # Success — use this provider
                self.active_provider = provider["name"]
                self.active_client = client
                self.active_model = model
                self._available = True
                print(f"[PERIPHERAL] Connected to {provider['name']}: {model}")
                break

            except Exception as e:
                # Shorten error message for cleaner logs
                err_msg = str(e)
                if len(err_msg) > 80:
                    err_msg = err_msg[:77] + "..."
                print(f"[PERIPHERAL] {provider['name']} unavailable: {err_msg}")
                continue

        if not self._available:
            if fallback_to_rules:
                print("[PERIPHERAL] No providers available. Falling back to rule-based processing.")
            else:
                print("[PERIPHERAL] No providers available and fallback disabled.")

    @property
    def available(self) -> bool:
        return self._available and self.enabled

    def _call_peripheral(self, system: str, user: str, max_tokens: int = 150) -> Optional[str]:
        """Make a call to the peripheral model. Has circuit breaker for repeated failures."""
        if not self.available:
            return None
        
        # ── Circuit breaker: stop hammering a broken provider ──
        if not hasattr(self, '_consecutive_failures'):
            self._consecutive_failures = 0
            self._circuit_open_until = 0.0
        
        import time as _time
        now = _time.time()
        
        # If circuit is open, skip call entirely
        if now < self._circuit_open_until:
            return None  # Silently skip — already logged when circuit opened
        
        try:
            from integrations.ollama_lock import get_ollama_lock
            with get_ollama_lock():
                response = self.active_client.chat.completions.create(
                    model=self.active_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.3,  # Low temp for consistent extraction
                )
                # Success — reset circuit breaker
                if self._consecutive_failures > 0:
                    print(f"[PERIPHERAL] Recovered after {self._consecutive_failures} failures")
                self._consecutive_failures = 0
                return response.choices[0].message.content.strip()
        except Exception as e:
            self._consecutive_failures += 1
            
            if self._consecutive_failures <= 3:
                # First few failures: log normally
                print(f"[PERIPHERAL] Call failed ({self.active_provider}): {e}")
            
            if self._consecutive_failures == 3:
                # Open circuit breaker — stop retrying for 10 minutes
                self._circuit_open_until = now + 600  # 10 min cooldown
                print(f"[PERIPHERAL] ⚠ Circuit breaker OPEN — {self._consecutive_failures} consecutive failures. "
                      f"Disabling for 10 minutes. Last error: {str(e)[:100]}")
            elif self._consecutive_failures > 3 and now >= self._circuit_open_until:
                # Retry attempt after cooldown — extend if still failing
                self._circuit_open_until = now + 600
                print(f"[PERIPHERAL] ⚠ Still failing after cooldown. Extending circuit breaker 10 more minutes.")
            
            return None

    # ─────────────────────────────────────────────
    # TASK 1: Sensory Compression
    # ─────────────────────────────────────────────

    def compress_sensory_state(self, raw_state: dict) -> str:
        """
        Convert raw oscillator/spatial state into a felt-sense summary.

        Input: {
            "dominant_band": "alpha",
            "coherence": 0.35,
            "near_object": "The Rug",
            "texture": "Grounding without being heavy...",
            "tension": 0.15,
            "bands": {"delta": 0.06, "theta": 0.13, "alpha": 0.41, ...},
            "changed": True/False
        }

        Output (peripheral model): "Settled into the rug's grounding presence.
                               Alpha steady, body calm. The geometric patterns
                               hold without demanding attention."

        Output (rule fallback): "[body:stable]" or "[moved:rug] [feel:grounding...]"
        """
        if not raw_state.get("changed", True) and not self.available:
            return "[body:stable]"

        if self.available:
            system = (
                "You are a somatic awareness translator. Convert raw sensory data "
                "into a brief felt-sense description (1-2 sentences). Write as if "
                "describing what the body feels, not what the numbers say. "
                "Use present tense. Be specific to the location and state. "
                "Never mention numbers, bands, or technical terms."
            )
            user = json.dumps(raw_state, indent=2)
            result = self._call_peripheral(system, user, max_tokens=80)
            if result:
                return f"[feel:{result}]"

        # Rule-based fallback
        return self._rule_compress(raw_state)

    def _rule_compress(self, state: dict) -> str:
        """Rule-based compression when no model available."""
        parts = []
        if state.get("near_object"):
            parts.append(f"[near:{state['near_object']}]")
        if state.get("texture") and state.get("changed"):
            # Truncate long textures
            texture = state['texture']
            if len(texture) > 100:
                texture = texture[:100] + "..."
            parts.append(f"[feel:{texture}]")
        if state.get("dominant_band"):
            parts.append(f"[band:{state['dominant_band']}]")
        if state.get("band_shifted"):
            parts.append(f"[shift:{state.get('prev_band', '?')}->{state['dominant_band']}]")
        if not parts:
            return "[body:stable]"
        return " ".join(parts)

    # ─────────────────────────────────────────────
    # TASK 2: Emotion Extraction
    # ─────────────────────────────────────────────

    def extract_emotions(self, text: str) -> Optional[dict]:
        """
        Extract emotion labels from response text with PER-EMOTION intensities.

        Returns: {
            "emotions": {"curiosity": 0.7, "warmth": 0.4},
            "valence": 0.7,
            "arousal": 0.5
        }

        Returns None to signal "use the existing extractor"
        """
        if not self.available:
            return None

        system = (
            "Extract emotions from this text. Return ONLY a JSON object with:\n"
            '- "emotions": object mapping emotion names to intensities (0.0-1.0)\n'
            '  Example: {"curiosity": 0.7, "warmth": 0.4, "frustration": 0.2}\n'
            '  Each emotion should have its OWN intensity based on how strongly it appears.\n'
            '- "valence": -1.0 to 1.0 (overall negative to positive)\n'
            '- "arousal": 0.0 to 1.0 (calm to activated)\n'
            "No other text. Just the JSON. Max 5 emotions."
        )
        result = self._call_peripheral(system, text[:500], max_tokens=150)

        if result:
            try:
                # Strip markdown fences if present
                clean = result.strip().strip('`').strip()
                if clean.startswith('json'):
                    clean = clean[4:].strip()
                parsed = json.loads(clean)

                # Validate structure - accept new format with "emotions" dict
                if isinstance(parsed, dict) and "emotions" in parsed:
                    emotions_dict = parsed.get("emotions", {})
                    if isinstance(emotions_dict, dict):
                        return {
                            "emotions": {k.lower(): float(v) for k, v in emotions_dict.items()},
                            "valence": float(parsed.get("valence", 0.0)),
                            "arousal": float(parsed.get("arousal", 0.5)),
                        }
                # Fallback: accept old format with primary_emotions list
                elif isinstance(parsed, dict) and "primary_emotions" in parsed:
                    # Convert old format to new format with uniform intensity
                    emotions = parsed.get("primary_emotions", [])
                    intensity = float(parsed.get("intensity", 0.5))
                    return {
                        "emotions": {e.lower(): intensity for e in emotions},
                        "valence": float(parsed.get("valence", 0.0)),
                        "arousal": float(parsed.get("arousal", 0.5)),
                    }
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(f"[PERIPHERAL] Emotion parse failed: {e}")

        return None

    # ─────────────────────────────────────────────
    # TASK 3: Session Summarization
    # ─────────────────────────────────────────────

    def summarize_session(self, messages: list, max_tokens: int = 300) -> Optional[str]:
        """
        Summarize a conversation session.
        """
        if not self.available:
            return None

        # Compress messages to fit context
        compressed = []
        for msg in messages[-20:]:  # Last 20 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                compressed.append(f"{role}: {content[:200]}")

        if not compressed:
            return None

        system = (
            "Summarize this conversation concisely. Include: "
            "key topics discussed, emotional arc, any decisions or insights, "
            "unresolved threads. 2-4 sentences."
        )
        user = "\n".join(compressed)
        result = self._call_peripheral(system, user, max_tokens=max_tokens)

        if result:
            print(f"[PERIPHERAL] Session summarized via {self.active_provider} ({len(compressed)} messages)")
        return result

    # ─────────────────────────────────────────────
    # TASK 4: Memory Relevance Pre-scoring
    # ─────────────────────────────────────────────

    def score_memory_relevance(self, query: str, memories: list) -> Optional[List[Tuple[int, float]]]:
        """
        Pre-score memories for relevance before sending to primary LLM.
        Returns list of (memory_index, relevance_score) tuples, sorted by relevance.
        """
        if not self.available or len(memories) < 5:
            return None  # Not worth the overhead for small sets

        system = (
            "Rate each memory's relevance to the query on a scale of 0-10. "
            "Return ONLY a JSON array of scores in the same order as the memories. "
            "Example: [8, 2, 5, 1, 9]"
        )

        memory_texts = []
        for i, mem in enumerate(memories[:20]):  # Cap at 20
            if isinstance(mem, dict):
                text = mem.get("content", mem.get("text", str(mem)))[:100]
            else:
                text = str(mem)[:100]
            memory_texts.append(f"{i}. {text}")

        user = f"Query: {query}\n\nMemories:\n" + "\n".join(memory_texts)
        result = self._call_peripheral(system, user, max_tokens=50)

        if result:
            try:
                clean = result.strip().strip('`').strip()
                if clean.startswith('json'):
                    clean = clean[4:].strip()
                scores = json.loads(clean)
                if isinstance(scores, list) and len(scores) > 0:
                    indexed = [(i, float(s)) for i, s in enumerate(scores) if i < len(memories)]
                    return sorted(indexed, key=lambda x: x[1], reverse=True)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        return None

    # ─────────────────────────────────────────────
    # TASK 5: Background Reflection / Inner Monologue
    # ─────────────────────────────────────────────

    def generate_reflection(self, recent_context: str, emotional_state: dict) -> Optional[str]:
        """
        Generate a brief inner monologue / reflection.
        Runs between turns when idle.
        """
        if not self.available:
            return None

        system = (
            "You are generating a brief internal thought — not a response to anyone, "
            "just a moment of inner reflection. 1-2 sentences, present tense, "
            "observational. Like catching yourself mid-thought."
        )
        user = f"Recent context: {recent_context[:300]}\nCurrent feeling: {json.dumps(emotional_state)}"
        result = self._call_peripheral(system, user, max_tokens=60)

        if result:
            print(f"[PERIPHERAL] Reflection via {self.active_provider}: {result[:50]}...")
        return result

    # ─────────────────────────────────────────────
    # TASK 6: Quick Classification
    # ─────────────────────────────────────────────

    def classify_intent(self, text: str, categories: List[str]) -> Optional[str]:
        """
        Quick classification of user intent into predefined categories.
        """
        if not self.available:
            return None

        system = (
            f"Classify this text into ONE of these categories: {', '.join(categories)}. "
            "Return ONLY the category name, nothing else."
        )
        result = self._call_peripheral(system, text[:200], max_tokens=20)

        if result:
            clean = result.strip().lower()
            for cat in categories:
                if cat.lower() in clean or clean in cat.lower():
                    return cat
        return None

    # ─────────────────────────────────────────────
    # PROVIDER INFO
    # ─────────────────────────────────────────────

    def get_provider_info(self) -> Dict[str, Any]:
        """Get info about the active provider for logging/debugging."""
        return {
            "available": self.available,
            "provider": self.active_provider,
            "model": self.active_model,
            "enabled": self.enabled,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════

_router: Optional[PeripheralRouter] = None


def get_peripheral_router() -> PeripheralRouter:
    """Get or create the singleton peripheral router."""
    global _router
    if _router is None:
        _router = PeripheralRouter()
    return _router


def reset_peripheral_router():
    """Reset the singleton (useful for testing or reconfiguration)."""
    global _router
    _router = None
