"""
Voice Service - STT (Speech-to-Text) and TTS (Text-to-Speech) for Nexus.

STT: Uses faster_whisper with base model
TTS: Pluggable backend system (Piper local or OpenAI API fallback)
"""
import asyncio
import io
import logging
import os
import wave
from abc import ABC, abstractmethod
from typing import Optional

log = logging.getLogger("nexus.voice")

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

    async def synthesize(self, text: str, voice: str) -> bytes:
        if not self._available:
            return b""
        try:
            voice_map = {
                "kay": "en-US-GuyNeural",
                "reed": "en-US-JennyNeural",
                "default": "en-US-GuyNeural",
            }
            voice_name = voice_map.get(voice.lower(), voice_map["default"])
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

        # Priority: ElevenLabs > Edge (free, reliable) > Piper (local) > OpenAI (dead)
        backends = [
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
