"""
Voice Service - STT (Speech-to-Text) and TTS (Text-to-Speech) for Nexus.

STT: Uses faster_whisper with base model
TTS: Pluggable backend system (Piper local or OpenAI API fallback)
"""
import asyncio
import io
import json
import logging
import os
import wave
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any

log = logging.getLogger("nexus.voice")

# ---------------------------------------------------------------------------
# Voice Configuration
# ---------------------------------------------------------------------------

VOICE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "voice_config.json")
VOICE_REFERENCES_DIR = os.path.join(os.path.dirname(__file__), "voice_references")

# Available preset voices per backend
VOXTRAL_PRESET_VOICES = [
    "af_sky", "af_adam", "af_bella", "af_sarah", "af_nicole", "af_emma", "af_isabella",
    "am_michael", "am_william", "am_james", "am_charles", "am_alex",
    "bf_jessica", "bf_emma", "bf_alice",
    "bm_george", "bm_lewis", "bm_daniel",
]

EDGE_TTS_VOICES = [
    "en-US-GuyNeural", "en-US-ChristopherNeural", "en-US-EricNeural",
    "en-US-JennyNeural", "en-US-AriaNeural", "en-US-SaraNeural",
    "en-GB-RyanNeural", "en-GB-SoniaNeural", "en-GB-LibbyNeural",
    "en-AU-WilliamNeural", "en-AU-NatashaNeural",
]

ELEVENLABS_VOICES = {
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Bella": "EXAVITQu4vr4xnSDxMaL",
}

OPENAI_TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

PIPER_VOICES = ["en_US-lessac-medium", "en_US-amy-medium", "en_US-ryan-medium"]

# Default voice selections
DEFAULT_VOICE_CONFIG = {
    "kay": {"voice": "af_sky", "backend_preference": None},
    "reed": {"voice": "af_bella", "backend_preference": None},
}


def load_voice_config() -> Dict[str, Any]:
    """Load voice configuration from disk."""
    if os.path.exists(VOICE_CONFIG_PATH):
        try:
            with open(VOICE_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                for entity in DEFAULT_VOICE_CONFIG:
                    if entity not in config:
                        config[entity] = DEFAULT_VOICE_CONFIG[entity].copy()
                return config
        except Exception as e:
            log.warning(f"[VOICE] Could not load voice config: {e}")
    return DEFAULT_VOICE_CONFIG.copy()


# ═══════════════════════════════════════════════════════════════
# OSCILLATOR VOICE PARAMETERS (System E)
# Band affects speech rate and pitch for Edge TTS SSML
# ═══════════════════════════════════════════════════════════════
BAND_VOICE_PARAMS = {
    "delta": {"rate": "-25%", "pitch": "-2st"},   # Slow, low
    "theta": {"rate": "-15%", "pitch": "-1st"},   # Relaxed, soft
    "alpha": {"rate": "+0%", "pitch": "+0st"},    # Normal
    "beta": {"rate": "+10%", "pitch": "+1st"},    # Alert, crisp
    "gamma": {"rate": "+15%", "pitch": "+2st"},   # Fast, energetic
}


def get_oscillator_voice_params(osc_state: dict) -> dict:
    """Get SSML voice parameters based on oscillator state (System E).

    Args:
        osc_state: Dict with keys: band, tension, reward

    Returns:
        Dict with 'rate' and 'pitch' SSML values
    """
    if not osc_state:
        return {"rate": "+0%", "pitch": "+0st"}

    band = osc_state.get("band", "alpha")
    tension = osc_state.get("tension", 0.0)
    reward = osc_state.get("reward", 0.0)

    # Start with band-based params
    params = BAND_VOICE_PARAMS.get(band, BAND_VOICE_PARAMS["alpha"]).copy()

    # Parse the rate value to modify it
    base_rate_str = params["rate"]
    try:
        # Extract numeric part (e.g., "+10%" -> 10)
        rate_val = int(base_rate_str.replace("%", "").replace("+", ""))
    except ValueError:
        rate_val = 0

    # Tension adds urgency (+5% rate per 0.5 tension)
    if tension > 0.3:
        rate_val += int(tension * 10)  # +10% at max tension

    # Reward slows down slightly (-5% rate, warmer)
    if reward > 0.3:
        rate_val -= int(reward * 10)  # -10% at max reward

    # Clamp rate
    rate_val = max(-50, min(50, rate_val))
    params["rate"] = f"{'+' if rate_val >= 0 else ''}{rate_val}%"

    return params


def wrap_ssml_prosody(text: str, rate: str, pitch: str) -> str:
    """Wrap text in SSML prosody tags for Edge TTS.

    Args:
        text: Plain text to speak
        rate: Rate modifier (e.g., "+10%", "-15%")
        pitch: Pitch modifier (e.g., "+2st", "-1st")

    Returns:
        SSML-wrapped text
    """
    # Escape special characters for SSML
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<speak><prosody rate="{rate}" pitch="{pitch}">{text}</prosody></speak>'


def save_voice_config(config: Dict[str, Any]) -> bool:
    """Save voice configuration to disk."""
    try:
        with open(VOICE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        log.error(f"[VOICE] Could not save voice config: {e}")
        return False


def has_custom_reference(entity: str) -> bool:
    """Check if entity has a custom voice reference WAV."""
    ref_path = os.path.join(VOICE_REFERENCES_DIR, f"{entity.lower()}_ref.wav")
    return os.path.exists(ref_path)

# ---------------------------------------------------------------------------
# TTS Backend System
# ---------------------------------------------------------------------------

class TTSBackend(ABC):
    """Abstract base class for TTS backends."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> bytes:
        """Synthesize text to WAV audio bytes."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return backend name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is usable."""
        pass


class PiperTTSBackend(TTSBackend):
    """Piper TTS backend - fast local synthesis."""

    def __init__(self):
        self._available = False
        self._piper = None
        try:
            import piper
            self._piper = piper
            self._available = True
            log.info("[TTS] Piper TTS backend available")
        except ImportError:
            log.warning("[TTS] piper-tts not installed, skipping Piper backend")

    def get_name(self) -> str:
        return "piper"

    def is_available(self) -> bool:
        return self._available

    async def synthesize(self, text: str, voice: str) -> bytes:
        if not self._available:
            return b""
        # Run in executor since Piper is blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text, voice)

    def _synthesize_sync(self, text: str, voice: str) -> bytes:
        try:
            from piper.voice import PiperVoice

            # Voice selection per entity — using HuggingFace model URLs
            voice_map = {
                "kay": ("en_US-lessac-medium", "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"),
                "reed": ("en_US-amy-medium", "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx"),
                "default": ("en_US-lessac-medium", "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"),
            }
            voice_name, model_url = voice_map.get(voice.lower(), voice_map["default"])

            # Model directory
            models_dir = os.path.join(os.path.dirname(__file__), "voice_models")
            os.makedirs(models_dir, exist_ok=True)

            onnx_path = os.path.join(models_dir, f"{voice_name}.onnx")
            config_path = os.path.join(models_dir, f"{voice_name}.onnx.json")

            # Auto-download model files if missing
            if not os.path.exists(onnx_path):
                import urllib.request
                log.info(f"[TTS] Downloading Piper model: {voice_name} (~60MB)...")
                urllib.request.urlretrieve(model_url, onnx_path)
                urllib.request.urlretrieve(model_url + ".json", config_path)
                log.info(f"[TTS] Model downloaded: {voice_name}")

            # Load and synthesize
            pv = PiperVoice.load(onnx_path, config_path=config_path)
            log.info(f"[TTS] Piper model loaded, sample_rate={pv.config.sample_rate}")

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(pv.config.sample_rate)
                # synthesize() may be a generator — consume it
                result = pv.synthesize(text, wav_file)
                if result is not None:
                    try:
                        for chunk in result:
                            pass  # pv writes to wav_file internally
                    except TypeError:
                        pass  # Not iterable, already wrote directly

            total = wav_buffer.tell()
            log.info(f"[TTS] Piper synthesized {len(text)} chars -> {total} bytes")
            if total <= 44:
                log.error(f"[TTS] Piper produced empty audio! Model may need onnxruntime. Try: pip install onnxruntime")
            return wav_buffer.getvalue()
        except Exception as e:
            log.error(f"[TTS] Piper synthesis error: {e}")
            return b""

    async def synthesize_with_voice(self, text: str, voice_name: str) -> bytes:
        """Synthesize with a specific Piper voice model."""
        if not self._available:
            return b""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_with_voice_sync, text, voice_name)

    def _synthesize_with_voice_sync(self, text: str, voice_name: str) -> bytes:
        """Synchronous Piper synthesis with specific voice."""
        try:
            from piper.voice import PiperVoice

            # Map voice name to model URL
            voice_models = {
                "en_US-lessac-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
                "en_US-amy-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
                "en_US-ryan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
            }
            model_url = voice_models.get(voice_name, voice_models["en_US-lessac-medium"])

            models_dir = os.path.join(os.path.dirname(__file__), "voice_models")
            os.makedirs(models_dir, exist_ok=True)

            onnx_path = os.path.join(models_dir, f"{voice_name}.onnx")
            config_path = os.path.join(models_dir, f"{voice_name}.onnx.json")

            if not os.path.exists(onnx_path):
                import urllib.request
                log.info(f"[TTS] Downloading Piper model: {voice_name}...")
                urllib.request.urlretrieve(model_url, onnx_path)
                urllib.request.urlretrieve(model_url + ".json", config_path)

            pv = PiperVoice.load(onnx_path, config_path=config_path)
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(pv.config.sample_rate)
                result = pv.synthesize(text, wav_file)
                if result is not None:
                    try:
                        for _ in result:
                            pass
                    except TypeError:
                        pass

            log.info(f"[TTS] Piper synthesized with '{voice_name}': {len(text)} chars -> {wav_buffer.tell()} bytes")
            return wav_buffer.getvalue()
        except Exception as e:
            log.error(f"[TTS] Piper synthesis error: {e}")
            return b""


class EdgeTTSBackend(TTSBackend):
    """Microsoft Edge TTS - free, high quality, no API key needed."""

    def __init__(self):
        self._available = False
        try:
            import edge_tts
            self._edge_tts = edge_tts
            self._available = True
            log.info("[TTS] Edge TTS backend available (free, no key needed)")
        except ImportError:
            log.warning("[TTS] edge-tts not installed — pip install edge-tts")

    def get_name(self) -> str:
        return "edge"

    def is_available(self) -> bool:
        return self._available

    async def synthesize(self, text: str, voice: str, osc_state: dict = None) -> bytes:
        """Synthesize speech with optional oscillator-based prosody (System E).

        Args:
            text: Text to speak
            voice: Voice identifier ("kay", "reed", etc.)
            osc_state: Optional oscillator state for SSML prosody modulation
        """
        if not self._available:
            return b""
        try:
            voice_map = {
                "kay": "en-US-GuyNeural",
                "reed": "en-US-JennyNeural",
                "default": "en-US-GuyNeural",
            }
            voice_name = voice_map.get(voice.lower(), voice_map["default"])

            # Apply SSML prosody if oscillator state provided (System E)
            if osc_state:
                params = get_oscillator_voice_params(osc_state)
                text = wrap_ssml_prosody(text, params["rate"], params["pitch"])
                log.debug(f"[TTS] SSML prosody: rate={params['rate']}, pitch={params['pitch']}")

            communicate = self._edge_tts.Communicate(text, voice_name)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            log.info(f"[TTS] Edge synthesized {len(text)} chars -> {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            log.error(f"[TTS] Edge synthesis error: {e}")
            return b""

    async def synthesize_with_voice(self, text: str, voice_name: str, osc_state: dict = None) -> bytes:
        """Synthesize with a specific Edge voice name and optional prosody.

        Args:
            text: Text to speak
            voice_name: Specific Edge voice name
            osc_state: Optional oscillator state for SSML prosody modulation
        """
        if not self._available:
            return b""
        try:
            # Apply SSML prosody if oscillator state provided (System E)
            if osc_state:
                params = get_oscillator_voice_params(osc_state)
                text = wrap_ssml_prosody(text, params["rate"], params["pitch"])
                log.debug(f"[TTS] SSML prosody: rate={params['rate']}, pitch={params['pitch']}")

            communicate = self._edge_tts.Communicate(text, voice_name)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            log.info(f"[TTS] Edge synthesized with '{voice_name}': {len(text)} chars -> {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            log.error(f"[TTS] Edge synthesis error: {e}")
            return b""


class OpenAITTSBackend(TTSBackend):
    """OpenAI TTS API backend - higher quality, requires API key."""

    def __init__(self):
        self._available = False
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        if self._api_key:
            try:
                import openai
                self._openai = openai
                self._available = True
                log.info("[TTS] OpenAI TTS backend available")
            except ImportError:
                log.warning("[TTS] openai package not installed")
        else:
            log.warning("[TTS] OPENAI_API_KEY not set, OpenAI TTS unavailable")

    def get_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return self._available

    async def synthesize(self, text: str, voice: str) -> bytes:
        if not self._available:
            return b""
        try:
            # Voice selection based on entity
            voice_map = {
                "kay": "onyx",      # Male, deep
                "reed": "nova",     # Female
                "default": "alloy", # Neutral
            }
            voice_name = voice_map.get(voice.lower(), voice_map["default"])

            client = self._openai.AsyncOpenAI(api_key=self._api_key)
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice_name,
                input=text,
                response_format="wav"
            )
            return response.content
        except Exception as e:
            log.error(f"[TTS] OpenAI synthesis error: {e}")
            return b""

    async def synthesize_with_voice(self, text: str, voice_name: str) -> bytes:
        """Synthesize with a specific OpenAI voice name."""
        if not self._available:
            return b""
        try:
            client = self._openai.AsyncOpenAI(api_key=self._api_key)
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice_name,
                input=text,
                response_format="wav"
            )
            log.info(f"[TTS] OpenAI synthesized with '{voice_name}': {len(text)} chars")
            return response.content
        except Exception as e:
            log.error(f"[TTS] OpenAI synthesis error: {e}")
            return b""


class ElevenLabsTTSBackend(TTSBackend):
    """ElevenLabs TTS API backend - excellent quality, free tier available."""

    def __init__(self):
        self._available = False
        self._api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if self._api_key:
            self._available = True
            log.info("[TTS] ElevenLabs TTS backend available")
        else:
            log.warning("[TTS] ELEVENLABS_API_KEY not set, ElevenLabs TTS unavailable")

    def get_name(self) -> str:
        return "elevenlabs"

    def is_available(self) -> bool:
        return self._available

    async def synthesize(self, text: str, voice: str) -> bytes:
        if not self._available:
            return b""
        try:
            import aiohttp

            # Voice IDs — pick ones that fit each entity
            voice_map = {
                "kay": "TxGEqnHWrfWFTfGW9XjX",    # Josh — male, deep, warm
                "reed": "21m00Tcm4TlvDq8ikWAM",    # Rachel — female, clear
                "default": "ErXwobaYiN019PkySvjV",  # Antoni — neutral
            }
            voice_id = voice_map.get(voice.lower(), voice_map["default"])

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        log.error(f"[TTS] ElevenLabs error {resp.status}: {error_text[:200]}")
                        return b""
                    audio_data = await resp.read()
                    log.info(f"[TTS] ElevenLabs synthesized {len(text)} chars -> {len(audio_data)} bytes")
                    return audio_data
        except ImportError:
            log.error("[TTS] aiohttp not installed — pip install aiohttp")
            return b""
        except Exception as e:
            log.error(f"[TTS] ElevenLabs synthesis error: {e}")
            return b""

    async def synthesize_with_voice(self, text: str, voice_id: str) -> bytes:
        """Synthesize with a specific ElevenLabs voice ID."""
        if not self._available:
            return b""
        try:
            import aiohttp

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        log.error(f"[TTS] ElevenLabs error {resp.status}: {error_text[:200]}")
                        return b""
                    audio_data = await resp.read()
                    log.info(f"[TTS] ElevenLabs synthesized with voice '{voice_id}': {len(text)} chars -> {len(audio_data)} bytes")
                    return audio_data
        except ImportError:
            log.error("[TTS] aiohttp not installed — pip install aiohttp")
            return b""
        except Exception as e:
            log.error(f"[TTS] ElevenLabs synthesis error: {e}")
            return b""


class VoxtralTTSBackend(TTSBackend):
    """
    Voxtral TTS backend - Mistral's expressive TTS model.
    
    Two modes:
    1. API mode (default): Uses Mistral's API at $0.016/1k chars
       Requires MISTRAL_API_KEY in environment or Kay's .env
    2. Local mode: Runs via vLLM-Omni server (needs >=16GB VRAM)
    
    Voice references go in D:/Wrappers/nexus/voice_references/
    """

    # Mistral preset voice IDs
    VOICE_MAP = {
        "kay": "af_sky",       # Male, warm, steady
        "reed": "af_bella",    # Female, clear
        "default": "af_sky",
    }

    def __init__(self):
        self._available = False
        self._mode = None  # "api" or "local"
        self._api_key = ""
        self._local_url = "http://localhost:8200"
        self._check_availability()

    def _check_availability(self):
        """Check for API key first (cheaper, easier), then local server."""
        # Check for Mistral API key
        self._api_key = os.environ.get("MISTRAL_API_KEY", "")
        if not self._api_key:
            # Try loading from Kay's .env
            env_path = os.path.join(os.path.dirname(__file__), "..", "Kay", ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("MISTRAL_API_KEY="):
                            self._api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break

        if self._api_key:
            self._available = True
            self._mode = "api"
            log.info("[TTS] Voxtral TTS available via Mistral API ($0.016/1k chars)")
            return

        # Fall back to local server
        try:
            import httpx
            resp = httpx.get(f"{self._local_url}/health", timeout=3.0)
            if resp.status_code == 200:
                self._available = True
                self._mode = "local"
                log.info("[TTS] Voxtral TTS available via local server")
                return
        except Exception:
            pass

        log.info("[TTS] Voxtral TTS not available (no MISTRAL_API_KEY and no local server)")

    def get_name(self) -> str:
        return f"voxtral-{self._mode}" if self._mode else "voxtral"

    def is_available(self) -> bool:
        return self._available

    async def synthesize(self, text: str, voice: str) -> bytes:
        if not self._available:
            return b""
        if self._mode == "api":
            return await self._synthesize_api(text, voice)
        else:
            return await self._synthesize_local(text, voice)

    async def _synthesize_api(self, text: str, voice: str) -> bytes:
        """Synthesize via Mistral's hosted API."""
        try:
            import httpx

            voice_id = self.VOICE_MAP.get(voice.lower(), self.VOICE_MAP["default"])

            # Check for custom voice reference
            ref_dir = os.path.join(os.path.dirname(__file__), "voice_references")
            ref_file = os.path.join(ref_dir, f"{voice.lower()}_ref.wav")

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            }

            payload = {
                "model": "voxtral-mini-tts-2603",
                "input": text,
                "response_format": "wav",
            }

            # Use voice reference if available, otherwise preset
            if os.path.exists(ref_file):
                import base64
                with open(ref_file, "rb") as f:
                    ref_b64 = base64.b64encode(f.read()).decode()
                payload["voice"] = {
                    "type": "base64",
                    "base64": ref_b64,
                    "media_type": "audio/wav",
                }
                log.info(f"[TTS] Voxtral API using custom voice reference for {voice}")
            else:
                payload["voice"] = voice_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.mistral.ai/v1/audio/speech",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    audio_data = resp.content
                    chars = len(text)
                    cost = chars * 0.016 / 1000
                    log.info(f"[TTS] Voxtral API: {chars} chars -> {len(audio_data)} bytes (~${cost:.4f})")
                    return audio_data
                else:
                    log.warning(f"[TTS] Voxtral API error {resp.status_code}: {resp.text[:200]}")
                    return b""
        except Exception as e:
            log.error(f"[TTS] Voxtral API synthesis error: {e}")
            return b""

    async def _synthesize_local(self, text: str, voice: str) -> bytes:
        """Synthesize via local vLLM-Omni server."""
        try:
            import httpx

            voice_id = self.VOICE_MAP.get(voice.lower(), self.VOICE_MAP["default"])

            ref_dir = os.path.join(os.path.dirname(__file__), "voice_references")
            ref_file = os.path.join(ref_dir, f"{voice.lower()}_ref.wav")

            payload = {
                "input": text,
                "model": "mistralai/Voxtral-4B-TTS-2603",
                "response_format": "wav",
                "voice": voice_id,
            }

            if os.path.exists(ref_file):
                import base64
                with open(ref_file, "rb") as f:
                    ref_b64 = base64.b64encode(f.read()).decode()
                payload["voice"] = {
                    "type": "base64",
                    "base64": ref_b64,
                    "media_type": "audio/wav",
                }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._local_url}/v1/audio/speech",
                    json=payload,
                )
                if resp.status_code == 200:
                    audio_data = resp.content
                    log.info(f"[TTS] Voxtral local: {len(text)} chars -> {len(audio_data)} bytes (free)")
                    return audio_data
                else:
                    log.warning(f"[TTS] Voxtral local error {resp.status_code}: {resp.text[:200]}")
                    return b""
        except Exception as e:
            log.error(f"[TTS] Voxtral local synthesis error: {e}")
            return b""

    async def synthesize_with_voice(self, text: str, entity: str, voice_id: str) -> bytes:
        """Synthesize with a specific voice preset (for voice testing)."""
        if not self._available:
            return b""
        if self._mode == "api":
            return await self._synthesize_api_with_voice(text, voice_id)
        else:
            return await self._synthesize_local_with_voice(text, voice_id)

    async def _synthesize_api_with_voice(self, text: str, voice_id: str) -> bytes:
        """Synthesize via Mistral API with specific voice preset."""
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            }

            payload = {
                "model": "voxtral-mini-tts-2603",
                "input": text,
                "response_format": "wav",
                "voice": voice_id,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.mistral.ai/v1/audio/speech",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    audio_data = resp.content
                    chars = len(text)
                    cost = chars * 0.016 / 1000
                    log.info(f"[TTS] Voxtral API with voice '{voice_id}': {chars} chars -> {len(audio_data)} bytes (~${cost:.4f})")
                    return audio_data
                else:
                    log.warning(f"[TTS] Voxtral API error {resp.status_code}: {resp.text[:200]}")
                    return b""
        except Exception as e:
            log.error(f"[TTS] Voxtral API synthesis error: {e}")
            return b""

    async def _synthesize_local_with_voice(self, text: str, voice_id: str) -> bytes:
        """Synthesize via local server with specific voice preset."""
        try:
            import httpx

            payload = {
                "input": text,
                "model": "mistralai/Voxtral-4B-TTS-2603",
                "response_format": "wav",
                "voice": voice_id,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._local_url}/v1/audio/speech",
                    json=payload,
                )
                if resp.status_code == 200:
                    audio_data = resp.content
                    log.info(f"[TTS] Voxtral local with voice '{voice_id}': {len(text)} chars -> {len(audio_data)} bytes (free)")
                    return audio_data
                else:
                    log.warning(f"[TTS] Voxtral local error {resp.status_code}: {resp.text[:200]}")
                    return b""
        except Exception as e:
            log.error(f"[TTS] Voxtral local synthesis error: {e}")
            return b""


# ---------------------------------------------------------------------------
# Voice Service
# ---------------------------------------------------------------------------

class VoiceService:
    """
    Voice service providing STT and TTS capabilities.

    STT: Uses faster_whisper with base model (lazy loaded)
    TTS: Uses best available backend (Piper > OpenAI)
    """

    def __init__(self):
        self.stt_model = None
        self.stt_available = False
        self.stt_device = "cpu"
        self.stt_compute_type = "int8"
        self.tts_backend: Optional[TTSBackend] = None
        self._stt_loading = False

        self._init_stt()
        self._init_tts()

    def _init_stt(self):
        """Initialize STT (faster_whisper)."""
        try:
            import torch
            if torch.cuda.is_available():
                self.stt_device = "cuda"
                self.stt_compute_type = "float16"
                log.info("[STT] CUDA available, will use GPU")
            else:
                log.info("[STT] CUDA not available, will use CPU")
        except ImportError:
            log.info("[STT] torch not found, will use CPU")

        try:
            from faster_whisper import WhisperModel
            self.stt_available = True
            log.info("[STT] faster_whisper available (model will load on first use)")
        except ImportError:
            log.warning("[STT] faster_whisper not installed - pip install faster-whisper")
            self.stt_available = False

    def _load_stt_model(self):
        """Lazy load the STT model on first use."""
        if self.stt_model is not None:
            return
        if self._stt_loading:
            return
        if not self.stt_available:
            return

        self._stt_loading = True
        log.info("[STT] Loading Whisper base model (first use may download ~150MB)...")
        try:
            from faster_whisper import WhisperModel
            self.stt_model = WhisperModel(
                "base",
                device=self.stt_device,
                compute_type=self.stt_compute_type
            )
            log.info(f"[STT] Model loaded on {self.stt_device}")
        except Exception as e:
            log.error(f"[STT] Failed to load model: {e}")
            self.stt_available = False
        finally:
            self._stt_loading = False

    def _init_tts(self):
        """Initialize TTS with best available backend."""
        # Load API keys from Kay's .env if not already in environment
        if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("ELEVENLABS_API_KEY"):
            env_path = os.path.join(os.path.dirname(__file__), "..", "Kay", ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("OPENAI_API_KEY=") and not os.environ.get("OPENAI_API_KEY"):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            os.environ["OPENAI_API_KEY"] = key
                            log.info("[TTS] Loaded OPENAI_API_KEY from Kay's .env")
                        elif line.startswith("ELEVENLABS_API_KEY=") and not os.environ.get("ELEVENLABS_API_KEY"):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            os.environ["ELEVENLABS_API_KEY"] = key
                            log.info("[TTS] Loaded ELEVENLABS_API_KEY from Kay's .env")

        # Priority: Voxtral (local, free, expressive) > ElevenLabs > Edge (free) > Piper > OpenAI
        backends = [
            VoxtralTTSBackend(),
            ElevenLabsTTSBackend(),
            EdgeTTSBackend(),
            PiperTTSBackend(),
            OpenAITTSBackend(),
        ]
        self.tts_backends = [b for b in backends if b.is_available()]
        if self.tts_backends:
            self.tts_backend = self.tts_backends[0]
            log.info(f"[TTS] Using {self.tts_backend.get_name()} backend (+ {len(self.tts_backends)-1} fallbacks)")
        else:
            log.warning("[TTS] No TTS backend available - voice output disabled")

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribe WAV audio to text.

        Args:
            audio_bytes: Raw WAV file bytes
            sample_rate: Expected sample rate (default 16000)

        Returns:
            Transcribed text string, or error message
        """
        if not self.stt_available:
            return "[STT not available - install faster-whisper]"

        # Lazy load model
        if self.stt_model is None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_stt_model)

        if self.stt_model is None:
            return "[STT model failed to load]"

        # Run transcription in executor (blocking operation)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._transcribe_sync, audio_bytes, sample_rate
        )

    def _transcribe_sync(self, audio_bytes: bytes, sample_rate: int) -> str:
        """Synchronous transcription."""
        try:
            # Parse WAV to get audio data
            wav_buffer = io.BytesIO(audio_bytes)
            with wave.open(wav_buffer, 'rb') as wav_file:
                # Read audio frames
                n_frames = wav_file.getnframes()
                audio_data = wav_file.readframes(n_frames)
                actual_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()

            # Convert to numpy array for faster_whisper
            import numpy as np
            if sample_width == 2:
                dtype = np.int16
            elif sample_width == 4:
                dtype = np.int32
            else:
                dtype = np.int16

            audio_array = np.frombuffer(audio_data, dtype=dtype)

            # Convert to mono if stereo
            if n_channels == 2:
                audio_array = audio_array.reshape(-1, 2).mean(axis=1)

            # Normalize to float32 [-1, 1]
            audio_array = audio_array.astype(np.float32) / 32768.0

            # Resample to 16kHz if needed
            if actual_rate != 16000:
                # Simple linear resampling
                ratio = 16000 / actual_rate
                new_length = int(len(audio_array) * ratio)
                indices = np.linspace(0, len(audio_array) - 1, new_length)
                audio_array = np.interp(indices, np.arange(len(audio_array)), audio_array)

            # Transcribe
            segments, info = self.stt_model.transcribe(
                audio_array,
                language="en",
                vad_filter=False
            )

            # Collect all segment text
            text_parts = [segment.text for segment in segments]
            result = " ".join(text_parts).strip()

            log.info(f"[STT] Transcribed {len(audio_bytes)} bytes -> {len(result)} chars")
            return result

        except Exception as e:
            log.error(f"[STT] Transcription error: {e}")
            return f"[STT error: {e}]"

    async def synthesize(self, text: str, entity: str = "default") -> bytes:
        """
        Synthesize text to WAV audio bytes.
        Falls through to next backend on failure.
        """
        if not self.tts_backends:
            log.warning("[TTS] No backend available for synthesis")
            return b""

        if not text.strip():
            return b""

        for backend in self.tts_backends:
            try:
                audio_bytes = await backend.synthesize(text, entity)
                if audio_bytes and len(audio_bytes) > 100:
                    log.info(f"[TTS] {backend.get_name()} synthesized {len(text)} chars -> {len(audio_bytes)} bytes")
                    return audio_bytes
                else:
                    log.warning(f"[TTS] {backend.get_name()} returned empty, trying next...")
            except Exception as e:
                log.warning(f"[TTS] {backend.get_name()} failed: {e}, trying next...")

        log.error("[TTS] All backends failed")
        return b""

    def get_status(self) -> dict:
        """Return STT/TTS backend status."""
        return {
            "stt": {
                "available": self.stt_available,
                "model_loaded": self.stt_model is not None,
                "device": self.stt_device,
                "compute_type": self.stt_compute_type,
            },
            "tts": {
                "available": len(self.tts_backends) > 0,
                "backends": [b.get_name() for b in self.tts_backends],
                "primary": self.tts_backends[0].get_name() if self.tts_backends else None,
            }
        }

    def get_config(self) -> Dict[str, Any]:
        """Get current voice configuration for settings panel."""
        config = load_voice_config()

        # Determine active backend name
        active_backend = "none"
        if self.tts_backend:
            active_backend = self.tts_backend.get_name()

        # Build available backends list
        available_backends = [b.get_name() for b in self.tts_backends]

        # Get available voices for the active backend
        available_voices = self.get_available_voices()

        return {
            "active_backend": active_backend,
            "available_backends": available_backends,
            "entities": {
                "kay": {
                    "current_voice": config.get("kay", {}).get("voice", "af_sky"),
                    "available_voices": available_voices,
                    "has_custom_reference": has_custom_reference("kay"),
                },
                "reed": {
                    "current_voice": config.get("reed", {}).get("voice", "af_bella"),
                    "available_voices": available_voices,
                    "has_custom_reference": has_custom_reference("reed"),
                }
            }
        }

    def set_voice(self, entity: str, voice_id: str) -> bool:
        """Set voice preference for an entity and save to config."""
        config = load_voice_config()
        entity_lower = entity.lower()

        if entity_lower not in config:
            config[entity_lower] = {}

        config[entity_lower]["voice"] = voice_id
        log.info(f"[VOICE] Set {entity}'s voice to: {voice_id}")
        return save_voice_config(config)

    def get_available_voices(self) -> List[str]:
        """Get available preset voices for the active TTS backend."""
        if not self.tts_backend:
            return []

        backend_name = self.tts_backend.get_name()

        if "voxtral" in backend_name:
            # Voxtral API has no preset voice names — it uses voice_id from
            # created profiles or ref_audio. Show Edge voices as presets instead,
            # since Edge is available as fallback and has real presets.
            return EDGE_TTS_VOICES
        elif backend_name == "edge":
            return EDGE_TTS_VOICES
        elif backend_name == "elevenlabs":
            return list(ELEVENLABS_VOICES.keys())
        elif backend_name == "openai":
            return OPENAI_TTS_VOICES
        elif backend_name == "piper":
            return PIPER_VOICES

        return []

    def get_voice_for_entity(self, entity: str) -> str:
        """Get the configured voice for an entity."""
        config = load_voice_config()
        entity_config = config.get(entity.lower(), {})
        return entity_config.get("voice", self._get_default_voice(entity))

    def _get_default_voice(self, entity: str) -> str:
        """Get default voice for entity based on active backend."""
        if not self.tts_backend:
            return ""

        backend_name = self.tts_backend.get_name()
        entity_lower = entity.lower()

        if "voxtral" in backend_name:
            # Voxtral has no presets — default to Edge voices for fallback
            return "en-US-GuyNeural" if entity_lower == "kay" else "en-US-JennyNeural"
        elif backend_name == "edge":
            return "en-US-GuyNeural" if entity_lower == "kay" else "en-US-JennyNeural"
        elif backend_name == "elevenlabs":
            return "TxGEqnHWrfWFTfGW9XjX" if entity_lower == "kay" else "21m00Tcm4TlvDq8ikWAM"
        elif backend_name == "openai":
            return "onyx" if entity_lower == "kay" else "nova"
        elif backend_name == "piper":
            return "en_US-lessac-medium" if entity_lower == "kay" else "en_US-amy-medium"

        return ""

    async def synthesize_with_voice(
        self, text: str, entity: str, voice_override: Optional[str] = None
    ) -> bytes:
        """
        Synthesize text with a specific voice override.
        Used for voice testing - doesn't change saved config.
        """
        if not self.tts_backends:
            log.warning("[TTS] No backend available for synthesis")
            return b""

        if not text.strip():
            return b""

        # Determine which voice to use
        voice_to_use = voice_override if voice_override else self.get_voice_for_entity(entity)

        # Smart routing: if voice name matches a specific backend format, try that first
        is_edge_voice = "Neural" in (voice_to_use or "")
        
        for backend in self.tts_backends:
            try:
                # Skip backends that clearly don't match the voice format
                bname = backend.get_name()
                if is_edge_voice and bname != "edge" and "voxtral" not in bname:
                    continue  # Skip non-Edge backends for Edge voice names
                if is_edge_voice and "voxtral" in bname:
                    continue  # Voxtral can't use Edge voice names
                    
                # Pass the voice directly to the backend
                audio_bytes = await self._synthesize_with_backend_voice(
                    backend, text, entity, voice_to_use
                )
                if audio_bytes and len(audio_bytes) > 100:
                    log.info(f"[TTS] {backend.get_name()} synthesized with voice '{voice_to_use}': {len(text)} chars -> {len(audio_bytes)} bytes")
                    return audio_bytes
                else:
                    log.warning(f"[TTS] {backend.get_name()} returned empty, trying next...")
            except Exception as e:
                log.warning(f"[TTS] {backend.get_name()} failed: {e}, trying next...")

        log.error("[TTS] All backends failed")
        return b""

    async def _synthesize_with_backend_voice(
        self, backend: 'TTSBackend', text: str, entity: str, voice: str
    ) -> bytes:
        """Synthesize using a specific backend with a specific voice."""
        backend_name = backend.get_name()

        # For Voxtral, we need to handle voice differently
        if isinstance(backend, VoxtralTTSBackend):
            return await backend.synthesize_with_voice(text, entity, voice)
        elif isinstance(backend, EdgeTTSBackend):
            return await backend.synthesize_with_voice(text, voice)
        elif isinstance(backend, ElevenLabsTTSBackend):
            # Map friendly name to voice ID if needed
            voice_id = ELEVENLABS_VOICES.get(voice, voice)
            return await backend.synthesize_with_voice(text, voice_id)
        elif isinstance(backend, OpenAITTSBackend):
            return await backend.synthesize_with_voice(text, voice)
        elif isinstance(backend, PiperTTSBackend):
            return await backend.synthesize_with_voice(text, voice)
        else:
            # Fallback: use entity-based synthesis
            return await backend.synthesize(text, entity)
