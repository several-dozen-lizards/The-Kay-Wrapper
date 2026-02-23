# engines/voice_engine.py
"""
Voice Engine for Reed - Continuous Conversational Voice Mode

Features:
- Continuous microphone listening with VAD (Voice Activity Detection)
- Automatic speech start/stop detection (no button pressing)
- Local Whisper transcription (faster_whisper - free, fast)
- Edge TTS output (Microsoft neural voices via HTTP - no COM conflicts)
- Automatic cycle: listen → transcribe → respond → speak → listen
- Echo cancellation (mutes mic during TTS playback)
- STREAMING TTS: Speaks sentences as they arrive from LLM
- ACOUSTIC ANALYSIS: OpenSMILE eGeMAPS feature extraction for prosodic/emotional awareness

Flow:
1. User speaks naturally
2. VAD detects speech start → starts recording
3. VAD detects silence (configurable duration) → stops recording
4. PARALLEL: Whisper transcribes audio + OpenSMILE extracts acoustic features
5. Transcription combined with emotional tags: "User [frustrated, rising pitch]: I'm fine"
6. Reed's response streams sentence-by-sentence (with emotional context)
7. TTS speaks each sentence as it arrives (streaming)
8. Returns to listening state
9. Cycle continues

NOTE: Uses edge-tts ONLY for TTS (no pyttsx3/COM) to avoid Windows threading conflicts.
"""

import threading
import time
import tempfile
import os
import sys
import re
import queue
import numpy as np
from typing import Optional, Callable, Dict, Any, Generator, List
from enum import Enum
from pathlib import Path

# Audio libraries
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("[VOICE] Warning: sounddevice not installed. Run: pip install sounddevice")

try:
    from scipy.io.wavfile import write as write_wav
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[VOICE] Warning: scipy not installed. Run: pip install scipy")

# VAD
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("[VOICE] Warning: webrtcvad not installed. Run: pip install webrtcvad")

# Whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("[VOICE] Warning: faster_whisper not installed. Run: pip install faster-whisper")

# Google TTS - Primary TTS engine (reliable, no COM conflicts)
GTTS_AVAILABLE = False
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    print("[VOICE] gTTS available (Google Text-to-Speech)")
except ImportError:
    print("[VOICE] gTTS not installed. Run: pip install gtts")

# Edge TTS - Microsoft's neural voices (better quality but may have API issues)
# Uses HTTP to Azure TTS - NO COM/Windows API conflicts with Whisper
EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    import asyncio
    EDGE_TTS_AVAILABLE = True
    print("[VOICE] edge-tts available (Microsoft neural voices)")
except ImportError:
    print("[VOICE] edge-tts not installed. Run: pip install edge-tts")

# Check if ANY TTS is available
if not GTTS_AVAILABLE and not EDGE_TTS_AVAILABLE:
    print("[VOICE] CRITICAL: No TTS engine available! Install gtts or edge-tts")

# Legacy flag for compatibility (always False - pyttsx3 disabled to avoid COM conflicts)
TTS_AVAILABLE = False

# Acoustic analysis (OpenSMILE eGeMAPS feature extraction)
ACOUSTIC_AVAILABLE = False
try:
    from engines.acoustic_analyzer import AcousticAnalyzer, AsyncAcousticAnalyzer, AcousticFeatures
    ACOUSTIC_AVAILABLE = True
    print("[VOICE] Acoustic analyzer available (OpenSMILE eGeMAPS)")
except ImportError:
    print("[VOICE] Acoustic analyzer not available. Prosodic features disabled.")

# Environmental sound detection (claps, knocks, etc.)
ENVIRONMENTAL_AVAILABLE = False
try:
    from engines.environmental_sound_detector import EnvironmentalSoundDetector
    ENVIRONMENTAL_AVAILABLE = True
    print("[VOICE] Environmental sound detector available")
except ImportError:
    print("[VOICE] Environmental sound detector not available.")


class VoiceState(Enum):
    """Voice engine states"""
    IDLE = "idle"
    LISTENING = "listening"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class AudioChunk:
    """Pre-generated audio ready for playback."""
    def __init__(self, sentence: str, audio_path: str, duration_estimate: float = 0.0):
        self.sentence = sentence
        self.audio_path = audio_path
        self.duration_estimate = duration_estimate
        self.generated_at = time.time()


class StreamingTTSQueue:
    """
    Thread-safe queue for streaming TTS with parallel audio generation.

    Allows sentence-by-sentence TTS playback while LLM is still generating.
    Audio generation happens in parallel with playback for minimal latency.
    """

    def __init__(self):
        self.sentence_queue = queue.Queue()  # Sentences waiting to be generated
        self.audio_queue = queue.Queue()  # Pre-generated audio waiting to be played
        self.is_complete = threading.Event()
        self.stop_flag = threading.Event()
        self.tts_finished = threading.Event()  # Signals TTS has finished all items
        self._items_queued = 0
        self._items_spoken = 0
        self._items_generated = 0
        self._lock = threading.Lock()

        # Parallel generation
        self._generation_thread: Optional[threading.Thread] = None
        self._generation_active = False

    def put_sentence(self, sentence: str):
        """Add a sentence to the TTS queue for generation."""
        if sentence and sentence.strip():
            with self._lock:
                self._items_queued += 1
            self.sentence_queue.put(sentence.strip())
            print(f"[TTS QUEUE] Added sentence #{self._items_queued}: {sentence[:50]}...")

    def mark_complete(self):
        """Signal that no more sentences will be added."""
        self.is_complete.set()
        print(f"[TTS QUEUE] Marked complete. Total queued: {self._items_queued}")

    def mark_generated(self):
        """Mark that one item has been generated to audio."""
        with self._lock:
            self._items_generated += 1
            print(f"[TTS QUEUE] Generated {self._items_generated}/{self._items_queued}")

    def mark_spoken(self):
        """Mark that one item has been spoken."""
        with self._lock:
            self._items_spoken += 1
            print(f"[TTS QUEUE] Spoken {self._items_spoken}/{self._items_queued}")
            # Check if all items have been spoken
            if self.is_complete.is_set() and self._items_spoken >= self._items_queued:
                self.tts_finished.set()
                print("[TTS QUEUE] All items spoken, setting tts_finished")

    def stop(self):
        """Signal to stop TTS playback."""
        self.stop_flag.set()
        self.is_complete.set()
        self.tts_finished.set()  # Unblock any waiting
        self._generation_active = False

    def get_next_sentence(self, timeout: float = 0.1) -> Optional[str]:
        """Get next sentence to generate, or None if done/stopped."""
        if self.stop_flag.is_set():
            return None

        try:
            sentence = self.sentence_queue.get(timeout=timeout)
            return sentence
        except queue.Empty:
            # Only return None (done) if complete AND queue is truly empty
            if self.is_complete.is_set() and self.sentence_queue.empty():
                return None
            return ""  # Empty string = keep waiting for more

    def put_audio(self, audio_chunk: AudioChunk):
        """Add pre-generated audio to the playback queue."""
        self.audio_queue.put(audio_chunk)

    def get_next_audio(self, timeout: float = 0.1) -> Optional[AudioChunk]:
        """Get next pre-generated audio to play, or None if done/stopped."""
        if self.stop_flag.is_set():
            return None

        try:
            audio = self.audio_queue.get(timeout=timeout)
            return audio
        except queue.Empty:
            # Only return None (done) if complete AND all generated AND queue is truly empty
            with self._lock:
                all_generated = self._items_generated >= self._items_queued
            if self.is_complete.is_set() and all_generated and self.audio_queue.empty():
                return None
            return None  # None = keep waiting for more (audio not ready yet)

    def wait_for_completion(self, timeout: float = 60.0) -> bool:
        """
        Wait for all TTS to finish playing.

        Returns True if completed, False if timeout.
        """
        return self.tts_finished.wait(timeout=timeout)

    def reset(self):
        """Reset queue for new response."""
        self.stop_flag.clear()
        self.is_complete.clear()
        self.tts_finished.clear()
        self._generation_active = False
        with self._lock:
            self._items_queued = 0
            self._items_spoken = 0
            self._items_generated = 0
        # Clear any remaining items in both queues
        for q in [self.sentence_queue, self.audio_queue]:
            while not q.empty():
                try:
                    q.get_nowait()
                except queue.Empty:
                    break
        print("[TTS QUEUE] Reset complete")


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences for streaming TTS.

    Uses punctuation-based splitting that preserves natural speech breaks.
    """
    if not text:
        return []

    # Split on sentence-ending punctuation, keeping the punctuation
    # Handle common abbreviations to avoid false splits
    text = text.replace("Mr.", "Mr").replace("Mrs.", "Mrs").replace("Dr.", "Dr")
    text = text.replace("Ms.", "Ms").replace("Jr.", "Jr").replace("Sr.", "Sr")
    text = text.replace("vs.", "vs").replace("etc.", "etc").replace("i.e.", "ie")
    text = text.replace("e.g.", "eg").replace("...", "…")  # Ellipsis as single char

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Restore abbreviations and clean up
    result = []
    for s in sentences:
        s = s.replace("Mr", "Mr.").replace("Mrs", "Mrs.").replace("Dr", "Dr.")
        s = s.replace("Ms", "Ms.").replace("Jr", "Jr.").replace("Sr", "Sr.")
        s = s.replace("vs", "vs.").replace("etc", "etc.").replace("ie", "i.e.")
        s = s.replace("eg", "e.g.").replace("…", "...")
        s = s.strip()
        if s:
            result.append(s)

    return result


class VoiceEngine:
    """
    Continuous conversational voice engine for Reed.

    Handles full voice I/O cycle with automatic VAD-based speech detection.
    Supports streaming TTS for low-latency responses.
    """

    def __init__(
        self,
        whisper_model: str = "base",
        sample_rate: int = 16000,
        input_device: Optional[int] = None,
        vad_aggressiveness: int = 2,
        silence_duration_ms: int = 1200,
        min_speech_duration_ms: int = 300,
        tts_rate: int = 175,
        tts_voice_index: int = 0,
        tts_engine_type: str = "auto",
        edge_tts_voice: str = "en-US-ChristopherNeural",
        enable_acoustic_analysis: bool = True
    ):
        """
        Initialize voice engine.

        Args:
            whisper_model: Whisper model size ("tiny", "base", "small", "medium", "large")
            sample_rate: Audio sample rate (16000 recommended for Whisper)
            input_device: Input device index (None = default)
            vad_aggressiveness: VAD aggressiveness 0-3 (higher = more aggressive filtering)
            silence_duration_ms: Silence duration to detect end of speech
            min_speech_duration_ms: Minimum speech duration before accepting
            tts_rate: Speech rate for TTS (words per minute)
            tts_voice_index: Index of TTS voice to use
            tts_engine_type: TTS engine to use ("auto", "edge", "sapi")
                             - "auto": Use edge-tts if available, fall back to SAPI
                             - "edge": Use edge-tts (requires internet, best quality)
                             - "sapi": Use Windows SAPI (offline, robotic)
            edge_tts_voice: Voice for edge-tts (e.g., "en-US-ChristopherNeural", "en-US-GuyNeural")
            enable_acoustic_analysis: Enable OpenSMILE prosodic/emotional feature extraction
        """
        self.sample_rate = sample_rate
        self.input_device = input_device
        self.silence_duration_ms = silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.tts_rate = tts_rate
        self.tts_voice_index = tts_voice_index
        self.edge_tts_voice = edge_tts_voice

        # Determine TTS engine to use
        if tts_engine_type == "auto":
            self.use_edge_tts = EDGE_TTS_AVAILABLE
        elif tts_engine_type == "edge":
            self.use_edge_tts = EDGE_TTS_AVAILABLE
            if not EDGE_TTS_AVAILABLE:
                print("[VOICE] Warning: edge-tts requested but not installed, falling back to SAPI")
        else:
            self.use_edge_tts = False

        if self.use_edge_tts:
            print(f"[VOICE] Using edge-tts with voice: {edge_tts_voice}")
        else:
            print("[VOICE] Using Windows SAPI TTS")

        # State
        self.state = VoiceState.IDLE
        self.is_active = False
        self._voice_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Streaming TTS
        self.tts_queue = StreamingTTSQueue()
        self._tts_thread: Optional[threading.Thread] = None
        self._audio_gen_thread: Optional[threading.Thread] = None
        self._tts_ready = threading.Event()  # Signals TTS engine is initialized

        # Barge-in detection (interrupt Kay when user speaks)
        self._is_speaking = threading.Event()  # True when Kay is speaking
        self._barge_in_detected = threading.Event()  # Set when user interrupts
        self._barge_in_thread: Optional[threading.Thread] = None
        self._barge_in_speech_ms = 0  # Accumulated speech duration
        self.barge_in_threshold_ms = 200  # Minimum speech duration to trigger barge-in
        # DISABLED 2024-12-03: Barge-in was triggering on ambient noise/artifacts,
        # cutting off Reed's responses after ~200ms. Set to True to re-enable.
        self.barge_in_enabled = False  # Was True - disabled due to false positives

        # Callbacks
        self.on_state_change: Optional[Callable[[VoiceState], None]] = None
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_first_audio: Optional[Callable[[], None]] = None  # Called when first audio starts
        self.on_barge_in: Optional[Callable[[], None]] = None  # Called when user interrupts Kay

        # Chat callback - set by UI to process transcription
        # For streaming: should return a generator that yields sentences
        self.process_input: Optional[Callable[[str], str]] = None
        self.process_input_streaming: Optional[Callable[[str], Generator[str, None, None]]] = None

        # VAD setup
        self.vad = None
        if VAD_AVAILABLE:
            self.vad = webrtcvad.Vad(vad_aggressiveness)
            self.frame_duration_ms = 30  # VAD requires 10, 20, or 30ms frames
            self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)

        # Whisper setup
        self.whisper = None
        if WHISPER_AVAILABLE:
            print(f"[VOICE] Loading Whisper model: {whisper_model}...")
            try:
                self.whisper = WhisperModel(whisper_model, device="cpu", compute_type="int8")
                print(f"[VOICE] Whisper model loaded successfully")
            except Exception as e:
                print(f"[VOICE] Error loading Whisper: {e}")

        # TTS setup - will be initialized in TTS thread for proper COM handling
        self.tts_engine = None

        # Temp directory for audio files
        self.temp_dir = Path(tempfile.gettempdir()) / "kay_voice"
        self.temp_dir.mkdir(exist_ok=True)

        # Acoustic analysis setup (OpenSMILE eGeMAPS)
        self.acoustic_analyzer = None
        self.async_acoustic = None
        self.acoustic_enabled = enable_acoustic_analysis and ACOUSTIC_AVAILABLE

        if self.acoustic_enabled:
            try:
                self.acoustic_analyzer = AcousticAnalyzer(
                    baseline_file="memory/acoustic_baseline.json",
                    enabled=True,
                    calibration_utterances=15
                )
                self.async_acoustic = AsyncAcousticAnalyzer(self.acoustic_analyzer)
                print(f"[VOICE] Acoustic analysis enabled (OpenSMILE eGeMAPS)")

                # Report baseline calibration status
                status = self.acoustic_analyzer.get_baseline_status()
                if status['calibrated']:
                    print(f"[VOICE] Acoustic baseline calibrated ({status['utterance_count']} utterances)")
                else:
                    print(f"[VOICE] Acoustic baseline calibrating: {status['progress_percent']:.0f}%")
            except Exception as e:
                print(f"[VOICE] Error initializing acoustic analyzer: {e}")
                self.acoustic_enabled = False
        else:
            if enable_acoustic_analysis and not ACOUSTIC_AVAILABLE:
                print("[VOICE] Acoustic analysis disabled (OpenSMILE not installed)")

        # Callback for acoustic features (optional - for UI display)
        self.on_acoustic_features: Optional[Callable[[Dict[str, Any]], None]] = None

        # Last acoustic analysis result (for debugging/display)
        self.last_acoustic_result: Optional[Dict[str, Any]] = None

        # Environmental sound detection setup
        # Mode: 'off' (skip), 'light' (spectral only ~0.3s), 'full' (hybrid with PANNs ~3s)
        self.sound_detector = None
        self.environmental_enabled = ENVIRONMENTAL_AVAILABLE
        self.environmental_mode = "light"  # Default to light for better latency

        if self.environmental_enabled:
            try:
                # Initialize with spectral mode - we'll switch detection method based on mode setting
                # Light mode uses spectral only, Full mode uses hybrid
                self.sound_detector = EnvironmentalSoundDetector(
                    enabled=True,
                    min_confidence=0.5,
                    group_threshold=0.5,
                    detector_mode="hybrid"  # Initialize with hybrid, but we control which method to call
                )
                print("[VOICE] Environmental sound detection enabled (mode: light by default)")
            except Exception as e:
                print(f"[VOICE] Error initializing environmental sound detector: {e}")
                self.environmental_enabled = False

        # Callback for environmental sounds (optional - for UI display)
        self.on_environmental_sounds: Optional[Callable[[List[Dict[str, Any]]], None]] = None

        # Last environmental sound detection result
        self.last_environmental_result: Optional[List[Dict[str, Any]]] = None

        print("[VOICE] Voice engine initialized")

    def _set_state(self, new_state: VoiceState):
        """Update state and notify callback."""
        old_state = self.state
        self.state = new_state

        if self.on_state_change and old_state != new_state:
            try:
                self.on_state_change(new_state)
            except Exception as e:
                print(f"[VOICE] Error in state change callback: {e}")

    def check_dependencies(self) -> Dict[str, bool]:
        """Check if all required dependencies are available."""
        return {
            'sounddevice': SOUNDDEVICE_AVAILABLE,
            'scipy': SCIPY_AVAILABLE,
            'webrtcvad': VAD_AVAILABLE,
            'faster_whisper': WHISPER_AVAILABLE,
            'gtts': GTTS_AVAILABLE,  # Primary TTS (Google)
            'edge_tts': EDGE_TTS_AVAILABLE,  # Secondary TTS (Microsoft neural)
            'acoustic_analyzer': ACOUSTIC_AVAILABLE  # OpenSMILE prosodic analysis
        }

    def get_acoustic_status(self) -> Dict[str, Any]:
        """
        Get acoustic analysis status and baseline calibration info.

        Returns:
            Dict with acoustic analyzer status
        """
        if not self.acoustic_enabled or not self.acoustic_analyzer:
            return {
                'enabled': False,
                'reason': 'OpenSMILE not available' if not ACOUSTIC_AVAILABLE else 'Disabled'
            }

        status = self.acoustic_analyzer.get_baseline_status()
        status['enabled'] = True
        status['last_result'] = self.last_acoustic_result
        return status

    def reset_acoustic_baseline(self):
        """Reset acoustic baseline for recalibration."""
        if self.acoustic_analyzer:
            self.acoustic_analyzer.reset_baseline()
            print("[VOICE] Acoustic baseline reset - will recalibrate from next 15 utterances")

    def check_microphone(self) -> tuple[bool, str]:
        """
        Check if microphone is available.

        Returns:
            Tuple of (success, message)
        """
        if not SOUNDDEVICE_AVAILABLE:
            return (False, "sounddevice not installed")

        try:
            # Try to record a short sample
            test_recording = sd.rec(
                int(0.1 * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                device=self.input_device
            )
            sd.wait()

            if len(test_recording) > 0:
                # Check if there's actual audio signal
                max_amplitude = np.abs(test_recording).max()
                if max_amplitude > 0:
                    return (True, f"Microphone working (max amplitude: {max_amplitude})")
                else:
                    return (True, "Microphone detected but no signal (may be muted)")
            else:
                return (False, "No audio data received")

        except Exception as e:
            return (False, f"Microphone error: {str(e)}")

    def list_audio_devices(self) -> list:
        """List available audio input devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []

        try:
            devices = sd.query_devices()
            input_devices = []
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'default': device.get('default_samplerate', self.sample_rate)
                    })
            return input_devices
        except Exception as e:
            print(f"[VOICE] Error listing devices: {e}")
            return []

    def start(self):
        """Start continuous voice listening mode."""
        if self.is_active:
            print("[VOICE] Already active")
            return

        if not self._check_ready():
            return

        self.is_active = True
        self._stop_event.clear()
        self.tts_queue.reset()
        self._tts_ready.clear()
        self._barge_in_detected.clear()
        self._is_speaking.clear()

        # Start TTS thread first (parallel initialization)
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True)
        self._tts_thread.start()

        # Start barge-in detection thread
        if self.barge_in_enabled and self.vad:
            self._barge_in_thread = threading.Thread(target=self._barge_in_loop, daemon=True)
            self._barge_in_thread.start()
            print("[VOICE] Barge-in detection enabled")

        # Wait briefly for TTS to initialize (parallel with voice thread start)
        # This implements parallel TTS initialization

        # Start voice loop in background thread
        self._voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
        self._voice_thread.start()

        print("[VOICE] Voice mode started")

    def stop(self):
        """Stop voice listening mode."""
        if not self.is_active:
            return

        print("[VOICE] Stopping voice mode...")
        self.is_active = False
        self._stop_event.set()
        self.tts_queue.stop()

        if self._voice_thread:
            self._voice_thread.join(timeout=2.0)

        if self._tts_thread:
            self._tts_thread.join(timeout=2.0)

        if self._audio_gen_thread:
            self._audio_gen_thread.join(timeout=2.0)

        if self._barge_in_thread:
            self._barge_in_thread.join(timeout=2.0)

        self._set_state(VoiceState.IDLE)
        print("[VOICE] Voice mode stopped")

    def _check_ready(self) -> bool:
        """Check if engine is ready for voice mode."""
        deps = self.check_dependencies()

        missing = [k for k, v in deps.items() if not v]
        if missing:
            error = f"Missing dependencies: {', '.join(missing)}"
            print(f"[VOICE] {error}")
            if self.on_error:
                self.on_error(error)
            return False

        if not self.whisper:
            error = "Whisper model not loaded"
            print(f"[VOICE] {error}")
            if self.on_error:
                self.on_error(error)
            return False

        mic_ok, mic_msg = self.check_microphone()
        if not mic_ok:
            error = f"Microphone check failed: {mic_msg}"
            print(f"[VOICE] {error}")
            if self.on_error:
                self.on_error(error)
            return False

        return True

    def _speak_gtts(self, text: str) -> bool:
        """
        Speak text using Google TTS (gTTS).

        This is synchronous - blocks until speech is complete.
        Reliable fallback that works without COM or Windows APIs.

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        if not GTTS_AVAILABLE:
            return False

        temp_file = None
        try:
            from gtts import gTTS

            # Create temp file for audio
            temp_file = self.temp_dir / f"tts_{int(time.time() * 1000)}.mp3"

            # Generate speech
            tts = gTTS(text=text, lang='en')
            tts.save(str(temp_file))

            # Verify file was created
            if not temp_file.exists():
                print(f"[VOICE TTS] gTTS failed to create audio file")
                return False

            file_size = temp_file.stat().st_size
            if file_size < 1000:
                print(f"[VOICE TTS] Audio file too small ({file_size} bytes)")
                return False

            # Play the audio file
            played = self._play_audio_file(str(temp_file))
            return played

        except Exception as e:
            print(f"[VOICE TTS] gTTS error: {e}")
            return False

        finally:
            # Clean up temp file
            if temp_file and temp_file.exists():
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def _speak_edge_tts(self, text: str) -> bool:
        """
        Speak text using edge-tts (Microsoft neural voices).

        This is synchronous - blocks until speech is complete.
        Produces much higher quality audio than SAPI.
        No COM required - uses HTTP to Azure TTS service.

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        if not EDGE_TTS_AVAILABLE:
            return False

        temp_file = None
        try:
            import asyncio
            import edge_tts

            # Create temp file for audio
            temp_file = self.temp_dir / f"tts_{int(time.time() * 1000)}.mp3"

            # Generate speech asynchronously
            async def generate():
                communicate = edge_tts.Communicate(text, self.edge_tts_voice)
                await communicate.save(str(temp_file))

            # Run async in sync context - create new loop to avoid conflicts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(generate())
            finally:
                loop.close()

            # Verify file was created
            if not temp_file.exists():
                print(f"[VOICE TTS] edge-tts failed to create audio file")
                return False

            file_size = temp_file.stat().st_size
            if file_size < 1000:  # Less than 1KB is suspicious
                print(f"[VOICE TTS] Audio file too small ({file_size} bytes), may be empty")
                return False

            # Play the audio file using the best available method
            played = self._play_audio_file(str(temp_file))

            return played

        except Exception as e:
            print(f"[VOICE TTS] Edge TTS error: {e}")
            return False

        finally:
            # Clean up temp file
            if temp_file and temp_file.exists():
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def _speak_text(self, text: str) -> bool:
        """
        Speak text using the best available TTS engine.

        Tries engines in order of preference:
        1. edge-tts (best quality, but may have API issues)
        2. gTTS (reliable fallback)

        Args:
            text: Text to speak

        Returns:
            True if any engine succeeded
        """
        # Try edge-tts first (better quality)
        if EDGE_TTS_AVAILABLE and self.use_edge_tts:
            try:
                if self._speak_edge_tts(text):
                    return True
                print("[VOICE TTS] edge-tts failed, trying gTTS...")
            except Exception as e:
                print(f"[VOICE TTS] edge-tts error: {e}, trying gTTS...")

        # Fallback to gTTS
        if GTTS_AVAILABLE:
            try:
                if self._speak_gtts(text):
                    return True
            except Exception as e:
                print(f"[VOICE TTS] gTTS error: {e}")

        print("[VOICE TTS] All TTS engines failed!")
        return False

    def _play_audio_file(self, filepath: str) -> bool:
        """
        Play an audio file using the best available method.

        Tries multiple methods in order of preference:
        1. pygame (best quality, most reliable)
        2. playsound (simple, usually works)
        3. Windows Media Player via PowerShell (fallback)

        Args:
            filepath: Path to audio file (MP3)

        Returns:
            True if playback succeeded
        """
        # Method 1: pygame (preferred)
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()

            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)

            return True

        except ImportError:
            pass  # pygame not installed
        except Exception as e:
            print(f"[VOICE TTS] pygame playback failed: {e}")

        # Method 2: playsound
        try:
            from playsound import playsound
            playsound(filepath)
            return True
        except ImportError:
            pass  # playsound not installed
        except Exception as e:
            print(f"[VOICE TTS] playsound failed: {e}")

        # Method 3: Windows Media Player via PowerShell
        if sys.platform == 'win32':
            try:
                import subprocess

                # Use Windows Media Player COM object
                ps_script = f'''
                Add-Type -AssemblyName presentationCore
                $player = New-Object System.Windows.Media.MediaPlayer
                $player.Open("{filepath}")
                $player.Play()
                Start-Sleep -Milliseconds 500
                while ($player.Position -lt $player.NaturalDuration.TimeSpan) {{
                    Start-Sleep -Milliseconds 100
                }}
                $player.Close()
                '''

                result = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True,
                    timeout=60
                )

                if result.returncode == 0:
                    return True
                else:
                    print(f"[VOICE TTS] PowerShell playback failed: {result.stderr.decode()}")

            except subprocess.TimeoutExpired:
                print("[VOICE TTS] PowerShell playback timed out")
            except Exception as e:
                print(f"[VOICE TTS] PowerShell playback error: {e}")

        # Method 4: ffplay (Linux/Mac, or if ffmpeg installed on Windows)
        try:
            import subprocess
            result = subprocess.run(
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath],
                capture_output=True,
                timeout=60
            )
            return result.returncode == 0
        except FileNotFoundError:
            pass  # ffplay not installed
        except Exception as e:
            print(f"[VOICE TTS] ffplay failed: {e}")

        print("[VOICE TTS] All audio playback methods failed!")
        print("[VOICE TTS] Install pygame for best results: pip install pygame")
        return False

    def _generate_audio_file(self, text: str) -> Optional[str]:
        """
        Generate audio file from text WITHOUT playing it.

        Used for parallel audio generation - generates files ahead of playback.

        Args:
            text: Text to convert to speech

        Returns:
            Path to generated audio file, or None if failed
        """
        if not text or not text.strip():
            return None

        # Clean text for speech
        clean_text = text.replace('*', '').replace('_', '').replace('#', '')
        clean_text = clean_text.strip()
        if not clean_text:
            return None

        # Try edge-tts first (better quality)
        if EDGE_TTS_AVAILABLE and self.use_edge_tts:
            try:
                import asyncio
                import edge_tts

                # Create temp file for audio
                temp_file = self.temp_dir / f"tts_{int(time.time() * 1000)}_{id(text) % 10000}.mp3"

                # Generate speech asynchronously
                async def generate():
                    communicate = edge_tts.Communicate(clean_text, self.edge_tts_voice)
                    await communicate.save(str(temp_file))

                # Run async in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(generate())
                finally:
                    loop.close()

                # Verify file was created
                if temp_file.exists() and temp_file.stat().st_size >= 1000:
                    return str(temp_file)
                else:
                    print(f"[TTS GEN] edge-tts file too small or missing")

            except Exception as e:
                print(f"[TTS GEN] edge-tts error: {e}")

        # Fallback to gTTS
        if GTTS_AVAILABLE:
            try:
                from gtts import gTTS

                temp_file = self.temp_dir / f"tts_{int(time.time() * 1000)}_{id(text) % 10000}.mp3"
                tts = gTTS(text=clean_text, lang='en')
                tts.save(str(temp_file))

                if temp_file.exists() and temp_file.stat().st_size >= 1000:
                    return str(temp_file)

            except Exception as e:
                print(f"[TTS GEN] gTTS error: {e}")

        return None

    def _audio_generation_loop(self):
        """
        Dedicated thread for generating audio files in parallel with playback.

        Runs continuously, converting sentences to audio files ahead of playback.
        """
        print("[TTS GEN] Audio generation loop started")

        try:
            while self.is_active and not self._stop_event.is_set():
                sentence = self.tts_queue.get_next_sentence(timeout=0.1)

                if sentence is None:
                    # No more sentences, but keep thread alive
                    time.sleep(0.05)
                    continue

                if sentence == "":
                    # Keep waiting for more sentences
                    continue

                # Generate audio file
                start_gen = time.time()
                audio_path = self._generate_audio_file(sentence)
                gen_duration = time.time() - start_gen

                if audio_path:
                    # Estimate playback duration (rough: ~10 chars per second)
                    duration_estimate = len(sentence) / 10.0
                    audio_chunk = AudioChunk(sentence, audio_path, duration_estimate)
                    self.tts_queue.put_audio(audio_chunk)
                    self.tts_queue.mark_generated()
                    print(f"[TTS GEN] Generated audio in {gen_duration:.2f}s: {sentence[:40]}...")
                else:
                    print(f"[TTS GEN] Failed to generate: {sentence[:40]}...")
                    self.tts_queue.mark_generated()  # Don't block queue

        finally:
            print("[TTS GEN] Audio generation loop ended")

    def _barge_in_loop(self):
        """
        Continuous VAD monitoring for barge-in detection.

        Runs while Kay is speaking and monitors microphone for user speech.
        If user speaks for >200ms, triggers barge-in (interrupts playback).
        """
        print("[BARGE-IN] Barge-in detection loop started")

        if not self.vad:
            print("[BARGE-IN] VAD not available, barge-in disabled")
            return

        try:
            while self.is_active and not self._stop_event.is_set():
                # Only monitor when Kay is speaking
                if not self._is_speaking.is_set():
                    self._barge_in_speech_ms = 0  # Reset accumulator
                    time.sleep(0.05)
                    continue

                if not self.barge_in_enabled:
                    time.sleep(0.1)
                    continue

                # Open audio stream for barge-in detection
                try:
                    stream = sd.InputStream(
                        samplerate=self.sample_rate,
                        channels=1,
                        dtype=np.int16,
                        blocksize=self.frame_size,
                        device=self.input_device
                    )
                    stream.start()

                    try:
                        while self._is_speaking.is_set() and not self._stop_event.is_set():
                            # Read one frame
                            frame, overflowed = stream.read(self.frame_size)

                            # Convert to bytes for VAD
                            frame_bytes = frame.tobytes()
                            expected_bytes = self.frame_size * 2
                            if len(frame_bytes) != expected_bytes:
                                continue

                            # Check if frame contains speech
                            try:
                                is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
                            except Exception:
                                continue

                            if is_speech:
                                self._barge_in_speech_ms += self.frame_duration_ms
                                # print(f"[BARGE-IN] Speech detected: {self._barge_in_speech_ms}ms")  # Debug

                                # Check if threshold exceeded
                                if self._barge_in_speech_ms >= self.barge_in_threshold_ms:
                                    print(f"[BARGE-IN] User interrupted! ({self._barge_in_speech_ms}ms of speech)")
                                    self._trigger_barge_in()
                                    break
                            else:
                                # Reset if silence detected (require continuous speech)
                                if self._barge_in_speech_ms > 0:
                                    self._barge_in_speech_ms = max(0, self._barge_in_speech_ms - self.frame_duration_ms)

                    finally:
                        stream.stop()
                        stream.close()

                except Exception as e:
                    print(f"[BARGE-IN] Error in detection loop: {e}")
                    time.sleep(0.1)

        finally:
            print("[BARGE-IN] Barge-in detection loop ended")

    def _trigger_barge_in(self):
        """
        Trigger barge-in: immediately stop audio playback and reset state.
        """
        print("[BARGE-IN] Triggering barge-in - stopping playback")

        # Set barge-in flag
        self._barge_in_detected.set()

        # Stop pygame audio immediately
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                print("[BARGE-IN] pygame audio stopped")
        except Exception as e:
            print(f"[BARGE-IN] Error stopping pygame: {e}")

        # Clear the TTS queue
        self.tts_queue.stop()

        # Clear speaking state
        self._is_speaking.clear()

        # Notify callback
        if self.on_barge_in:
            try:
                self.on_barge_in()
            except Exception:
                pass

        # Reset for next cycle
        self._barge_in_speech_ms = 0

    def _tts_loop(self):
        """
        Dedicated TTS thread for streaming audio playback.

        Plays pre-generated audio files from the queue.
        Audio generation happens in parallel via _audio_generation_loop.
        """
        print("[VOICE TTS] TTS playback loop started")

        # Check if ANY TTS is available
        if not GTTS_AVAILABLE and not EDGE_TTS_AVAILABLE:
            print("[VOICE TTS] FATAL: No TTS engine available! Install: pip install gtts edge-tts")
            self._tts_ready.set()
            return

        # Report available engines
        engines = []
        if EDGE_TTS_AVAILABLE:
            engines.append(f"edge-tts ({self.edge_tts_voice})")
        if GTTS_AVAILABLE:
            engines.append("gTTS (Google)")
        print(f"[VOICE TTS] Available engines: {', '.join(engines)}")

        # Start audio generation thread (parallel with playback)
        self._audio_gen_thread = threading.Thread(target=self._audio_generation_loop, daemon=True)
        self._audio_gen_thread.start()
        print("[VOICE TTS] Audio generation thread started")

        self._tts_ready.set()  # Signal that TTS is ready

        # Track state for queue management
        first_sentence = True
        sentence_count = 0
        wait_start = None

        try:
            while self.is_active and not self._stop_event.is_set():
                audio_chunk = self.tts_queue.get_next_audio(timeout=0.1)

                if audio_chunk is None:
                    # Check if we're done (all spoken) or still waiting
                    with self.tts_queue._lock:
                        items_queued = self.tts_queue._items_queued
                        items_spoken = self.tts_queue._items_spoken
                        items_generated = self.tts_queue._items_generated

                    # If complete and all spoken, reset for next response
                    if self.tts_queue.is_complete.is_set() and items_spoken >= items_queued and items_queued > 0:
                        if sentence_count > 0:
                            print(f"[VOICE TTS] Response complete: spoke {sentence_count} sentences")
                        first_sentence = True
                        sentence_count = 0
                        wait_start = None
                        time.sleep(0.05)
                        continue

                    # Still waiting for audio to be generated
                    if wait_start is None:
                        wait_start = time.time()
                    elif time.time() - wait_start > 0.5:
                        # Only log if waiting a noticeable time
                        print(f"[VOICE TTS] Waiting for audio... (queued={items_queued}, gen={items_generated}, spoken={items_spoken})")
                        wait_start = time.time()
                    continue

                wait_start = None  # Reset wait timer
                sentence_count += 1
                print(f"[VOICE TTS] Playing sentence #{sentence_count}: {audio_chunk.sentence[:50]}...")

                # Notify when first audio starts (for latency tracking)
                if first_sentence and self.on_first_audio:
                    try:
                        self.on_first_audio()
                    except Exception:
                        pass
                    first_sentence = False

                # Play the pre-generated audio file
                try:
                    # Set speaking flag for barge-in detection
                    self._is_speaking.set()
                    self._barge_in_detected.clear()

                    start_play = time.time()
                    success = self._play_audio_file(audio_chunk.audio_path)
                    play_duration = time.time() - start_play

                    # Clear speaking flag
                    self._is_speaking.clear()

                    # Check if barge-in occurred
                    if self._barge_in_detected.is_set():
                        print(f"[VOICE TTS] Barge-in detected, stopping remaining playback")
                        self._barge_in_detected.clear()
                        # Don't mark as spoken - we were interrupted
                        break

                    if success:
                        print(f"[VOICE TTS] Sentence #{sentence_count} played ({play_duration:.2f}s)")
                    else:
                        print(f"[VOICE TTS] WARNING: Sentence #{sentence_count} playback failed")

                    # Clean up temp file
                    try:
                        os.unlink(audio_chunk.audio_path)
                    except:
                        pass

                    self.tts_queue.mark_spoken()

                except Exception as e:
                    self._is_speaking.clear()
                    print(f"[VOICE TTS] Error playing sentence #{sentence_count}: {e}")
                    import traceback
                    traceback.print_exc()
                    self.tts_queue.mark_spoken()

        finally:
            pass

        print("[VOICE TTS] TTS playback loop ended")

    def _voice_loop(self):
        """Main voice loop - runs in background thread."""
        print("[VOICE] Voice loop started")

        # Wait for TTS to be ready (parallel initialization)
        self._tts_ready.wait(timeout=5.0)
        if self._tts_ready.is_set():
            print("[VOICE] TTS ready, starting listening")
        else:
            print("[VOICE] Warning: TTS not ready after 5s, continuing anyway")

        try:
            while self.is_active and not self._stop_event.is_set():
                try:
                    # LISTEN phase - wait for speech
                    self._set_state(VoiceState.LISTENING)
                    audio_data = self._listen_for_speech()

                    if audio_data is None or not self.is_active:
                        continue

                    # TRANSCRIBE + ACOUSTIC ANALYSIS + ENVIRONMENTAL phase (PARALLEL)
                    self._set_state(VoiceState.TRANSCRIBING)

                    # Start acoustic analysis in parallel (if enabled)
                    acoustic_future = None
                    if self.acoustic_enabled and self.async_acoustic:
                        try:
                            acoustic_future = self.async_acoustic.analyze_async(
                                audio_data, self.sample_rate
                            )
                            print("[VOICE] Started parallel acoustic analysis")
                        except Exception as e:
                            print(f"[VOICE] Acoustic analysis start error: {e}")

                    # Run Whisper transcription FIRST (main thread)
                    # We need speech timestamps for environmental sound filtering
                    transcription_result = self._transcribe_audio_with_timestamps(audio_data)

                    if not transcription_result:
                        print("[VOICE] Transcription failed, returning to listening")
                        continue

                    transcription, speech_timestamps = transcription_result

                    if not transcription or not transcription.strip():
                        print("[VOICE] Empty transcription, returning to listening")
                        continue

                    print(f"[VOICE] Transcription: {transcription}")

                    # Environmental sound detection with mode-based routing
                    # Modes: 'off' (skip), 'light' (spectral ~0.3s), 'full' (hybrid ~3s)
                    environmental_events = []
                    env_mode = getattr(self, 'environmental_mode', 'light')

                    print(f"[VOICE] Environmental detection starting: mode={env_mode}, enabled={self.environmental_enabled}, detector={self.sound_detector is not None}")

                    if env_mode == 'off':
                        print("[ENVIRONMENTAL] Detection OFF (skipped for latency)")
                    elif self.environmental_enabled and self.sound_detector:
                        try:
                            import time
                            env_start = time.time()

                            if env_mode == 'light':
                                # LIGHT MODE: Spectral only (~0.3s instead of 3s)
                                print("[VOICE] Calling detect_light...")
                                environmental_events = self.sound_detector.detect_light(
                                    audio_data, self.sample_rate, speech_timestamps
                                )
                                print(f"[VOICE] detect_light returned: {len(environmental_events)} events")
                            else:  # 'full' or any other value
                                # FULL MODE: Hybrid with PANNs (~3s)
                                print("[VOICE] Calling detect_sounds_with_speech_filter...")
                                environmental_events = self.sound_detector.detect_sounds_with_speech_filter(
                                    audio_data, self.sample_rate, speech_timestamps
                                )
                                print(f"[VOICE] detect_sounds_with_speech_filter returned: {len(environmental_events)} events")

                            env_elapsed = time.time() - env_start
                            print(f"[ENVIRONMENTAL] {env_mode.upper()} mode completed in {env_elapsed:.2f}s")

                            if environmental_events:
                                # Log to terminal
                                for line in self.sound_detector.format_for_terminal(environmental_events):
                                    print(line)
                                # Store for debugging/display
                                self.last_environmental_result = environmental_events
                                # Notify UI callback if set
                                if self.on_environmental_sounds:
                                    try:
                                        self.on_environmental_sounds(environmental_events)
                                    except Exception:
                                        pass
                        except Exception as e:
                            print(f"[ENVIRONMENTAL] Detection error: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"[VOICE] Environmental detection skipped (enabled={self.environmental_enabled}, detector={self.sound_detector is not None})")

                    # Get acoustic analysis results (if running)
                    acoustic_tags = []
                    if acoustic_future:
                        try:
                            # Wait for acoustic analysis (with timeout)
                            acoustic_features = acoustic_future.result(timeout=2.0)

                            if acoustic_features and acoustic_features.tags:
                                acoustic_tags = acoustic_features.tags
                                print(f"[ACOUSTIC] Tags: {acoustic_tags}")
                                print(f"[ACOUSTIC] Arousal: {acoustic_features.arousal:.2f}, "
                                      f"Valence: {acoustic_features.emotional_valence:.2f}")

                                # Store for debugging/display
                                self.last_acoustic_result = {
                                    'tags': acoustic_tags,
                                    'arousal': acoustic_features.arousal,
                                    'valence': acoustic_features.emotional_valence,
                                    'f0_mean': acoustic_features.f0_mean,
                                    'loudness_mean': acoustic_features.loudness_mean,
                                    'speaking_rate': acoustic_features.speaking_rate,
                                    'duration': acoustic_features.duration,
                                }

                                # Notify UI callback if set
                                if self.on_acoustic_features:
                                    try:
                                        self.on_acoustic_features(self.last_acoustic_result)
                                    except Exception:
                                        pass
                        except Exception as e:
                            print(f"[ACOUSTIC] Analysis error (continuing without tags): {e}")

                    # Format transcription with acoustic tags for LLM
                    if acoustic_tags and self.acoustic_analyzer:
                        formatted_input = self.acoustic_analyzer.format_for_llm(
                            acoustic_tags, transcription
                        )
                    else:
                        formatted_input = transcription

                    # Add environmental sounds to formatted input in clear format
                    if environmental_events and self.sound_detector:
                        # Build detailed environmental audio section
                        env_lines = ["Environmental audio detected:"]
                        for sound in environmental_events:
                            if 'count' in sound:
                                conf_pct = int(sound['confidence'] * 100)
                                freq = sound.get('frequency', 0)
                                env_lines.append(f"  - {sound['type']} x{sound['count']} (confidence: {conf_pct}%, frequency: {freq:.0f}Hz)")
                            else:
                                conf_pct = int(sound['confidence'] * 100)
                                ts = sound.get('timestamp', 0)
                                env_lines.append(f"  - {sound['type']} @ {ts:.1f}s (confidence: {conf_pct}%)")

                        env_section = "\n".join(env_lines)
                        # Prepend environmental sounds to input with clear separation
                        formatted_input = f"{env_section}\n\nUser speech: {formatted_input}"
                        print(f"[ENVIRONMENTAL] Added to input: {len(environmental_events)} sound(s)")
                    else:
                        # No environmental sounds detected - make this clear too
                        # Only add if there were non-speech periods to analyze
                        if speech_timestamps:
                            formatted_input = f"Environmental audio: None detected\n\nUser speech: {formatted_input}"

                    print(f"[VOICE] LLM input: {formatted_input}")

                    # Notify UI of transcription (raw transcription, not formatted)
                    if self.on_transcription:
                        self.on_transcription(transcription)

                    # PROCESS phase - send to chat pipeline (with acoustic context)
                    self._set_state(VoiceState.PROCESSING)

                    # Try streaming mode first, fall back to non-streaming
                    if self.process_input_streaming:
                        try:
                            # Reset TTS queue for new response
                            self.tts_queue.reset()
                            self._set_state(VoiceState.SPEAKING)

                            # Process with streaming - generator yields sentences
                            # Use formatted input (with acoustic tags) for LLM
                            sentence_buffer = ""
                            for chunk in self.process_input_streaming(formatted_input):
                                sentence_buffer += chunk

                                # Extract complete sentences
                                sentences = split_into_sentences(sentence_buffer)
                                if len(sentences) > 1:
                                    # All but last are complete sentences
                                    for sentence in sentences[:-1]:
                                        self.tts_queue.put_sentence(sentence)
                                    sentence_buffer = sentences[-1]

                            # Send any remaining text
                            if sentence_buffer.strip():
                                self.tts_queue.put_sentence(sentence_buffer)

                            self.tts_queue.mark_complete()

                            # Wait for TTS to actually finish speaking all sentences
                            # Use the proper completion event instead of broken queue check
                            print("[VOICE] Waiting for TTS to finish speaking...")
                            completed = self.tts_queue.wait_for_completion(timeout=120.0)
                            if completed:
                                print("[VOICE] TTS completed successfully")
                            else:
                                print("[VOICE] Warning: TTS wait timed out")

                        except Exception as e:
                            print(f"[VOICE] Error in streaming processing: {e}")
                            import traceback
                            traceback.print_exc()

                    elif self.process_input:
                        try:
                            # Use formatted input (with acoustic tags) for LLM
                            response = self.process_input(formatted_input)

                            if response and response.strip():
                                # SPEAK phase - use streaming TTS
                                self._set_state(VoiceState.SPEAKING)
                                self._speak_streaming(response)
                        except Exception as e:
                            print(f"[VOICE] Error processing input: {e}")
                            if self.on_error:
                                self.on_error(f"Processing error: {str(e)}")

                except Exception as e:
                    print(f"[VOICE] Error in voice loop: {e}")
                    import traceback
                    traceback.print_exc()
                    self._set_state(VoiceState.ERROR)
                    time.sleep(1)  # Brief pause before retrying

        finally:
            pass

        print("[VOICE] Voice loop ended")

    def _listen_for_speech(self) -> Optional[np.ndarray]:
        """
        Listen for speech using VAD.

        Returns:
            Audio data as numpy array, or None if interrupted/no speech
        """
        if not self.vad:
            print("[VOICE] VAD not available")
            return None

        print("[VOICE] Listening... (speak now)")

        # State tracking
        triggered = False  # Has speech started?
        voiced_frames = []  # All frames with speech
        num_padding_frames = int(self.silence_duration_ms / self.frame_duration_ms)
        ring_buffer = []  # Recent frames to detect silence
        speech_start_time = None

        try:
            # Open audio stream
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.frame_size,
                device=self.input_device
            )
            stream.start()

            try:
                while self.is_active and not self._stop_event.is_set():
                    # Read one frame
                    frame, overflowed = stream.read(self.frame_size)
                    if overflowed:
                        print("[VOICE] Audio buffer overflow")

                    # Convert to bytes for VAD
                    frame_bytes = frame.tobytes()

                    # VAD needs exactly the right number of bytes
                    expected_bytes = self.frame_size * 2  # 16-bit = 2 bytes per sample
                    if len(frame_bytes) != expected_bytes:
                        continue

                    # Check if frame contains speech
                    try:
                        is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
                    except Exception:
                        continue

                    if not triggered:
                        # Waiting for speech to start
                        if is_speech:
                            triggered = True
                            speech_start_time = time.time()
                            print("[VOICE] Speech detected, recording...")

                            # Include buffered pre-speech frames
                            for buffered_frame in ring_buffer:
                                voiced_frames.append(buffered_frame)
                            ring_buffer.clear()
                            voiced_frames.append(frame)
                        else:
                            # Keep buffer of recent frames (for natural speech start)
                            ring_buffer.append(frame)
                            if len(ring_buffer) > num_padding_frames:
                                ring_buffer.pop(0)
                    else:
                        # Speech has started, watching for silence
                        voiced_frames.append(frame)

                        if not is_speech:
                            ring_buffer.append(frame)
                            if len(ring_buffer) >= num_padding_frames:
                                # Been silent for silence_duration_ms, stop recording
                                print("[VOICE] Silence detected, processing...")
                                break
                        else:
                            # Speech continues, reset silence buffer
                            ring_buffer.clear()

            finally:
                stream.stop()
                stream.close()

        except Exception as e:
            print(f"[VOICE] Error in listen: {e}")
            return None

        # Check if we got valid speech
        if not triggered:
            return None

        # Check minimum duration
        if speech_start_time:
            duration_ms = (time.time() - speech_start_time) * 1000
            if duration_ms < self.min_speech_duration_ms:
                print(f"[VOICE] Speech too short ({duration_ms:.0f}ms), ignoring")
                return None

        # Concatenate all frames
        if voiced_frames:
            return np.concatenate(voiced_frames, axis=0)

        return None

    def _transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio using Whisper.

        Args:
            audio_data: Audio as numpy array (int16)

        Returns:
            Transcription text, or None if failed
        """
        result = self._transcribe_audio_with_timestamps(audio_data)
        if result:
            return result[0]  # Return just the text
        return None

    def _transcribe_audio_with_timestamps(self, audio_data: np.ndarray) -> Optional[tuple]:
        """
        Transcribe audio using Whisper and return speech segment timestamps.

        Args:
            audio_data: Audio as numpy array (int16)

        Returns:
            Tuple of (transcription_text, speech_timestamps) where speech_timestamps
            is a list of (start_time, end_time) tuples in seconds.
            Returns None if failed.
        """
        if not self.whisper or not SCIPY_AVAILABLE:
            return None

        try:
            # Save to temp WAV file
            temp_file = self.temp_dir / f"recording_{int(time.time())}.wav"
            write_wav(str(temp_file), self.sample_rate, audio_data)

            try:
                # Transcribe
                segments, info = self.whisper.transcribe(str(temp_file), beam_size=5)

                # Collect segments as list (generator is consumed once)
                segment_list = list(segments)

                # Extract text
                transcription = " ".join([seg.text for seg in segment_list]).strip()

                # Extract speech timestamps from Whisper segments
                speech_timestamps = []
                for seg in segment_list:
                    speech_timestamps.append((seg.start, seg.end))

                return (transcription, speech_timestamps)
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            print(f"[VOICE] Transcription error: {e}")
            return None

    def _speak_streaming(self, text: str):
        """
        Speak text using streaming TTS (sentence by sentence).

        This queues sentences to the TTS thread for parallel playback.

        Args:
            text: Text to speak
        """
        if not text or not text.strip():
            return

        if not GTTS_AVAILABLE and not EDGE_TTS_AVAILABLE:
            print(f"[VOICE] No TTS engine available, response: {text}")
            return

        # Reset queue for new response
        self.tts_queue.reset()

        # Split into sentences and queue them
        sentences = split_into_sentences(text)
        print(f"[VOICE] Queuing {len(sentences)} sentences for TTS")

        for sentence in sentences:
            self.tts_queue.put_sentence(sentence)

        self.tts_queue.mark_complete()

        # Wait for TTS to actually finish speaking all sentences
        start_time = time.time()
        max_wait = max(120, len(text) * 0.2)  # ~200ms per char max, minimum 2 minutes

        print(f"[VOICE] Waiting for TTS to finish (timeout: {max_wait:.0f}s)...")
        completed = self.tts_queue.wait_for_completion(timeout=max_wait)

        elapsed = time.time() - start_time
        if completed:
            print(f"[VOICE] Finished speaking ({elapsed:.1f}s)")
        else:
            print(f"[VOICE] TTS timed out after {elapsed:.1f}s")

    def _speak(self, text: str):
        """
        Legacy speak method - uses streaming internally.

        Args:
            text: Text to speak
        """
        self._speak_streaming(text)

    def speak_now(self, text: str):
        """
        Speak text immediately (can be called from outside voice loop).

        Args:
            text: Text to speak
        """
        if self.state == VoiceState.SPEAKING:
            print("[VOICE] Already speaking, queuing...")

        self._speak_streaming(text)

    def cleanup(self):
        """Clean up resources."""
        self.stop()

        # Clean up acoustic analyzer
        if self.async_acoustic:
            try:
                self.async_acoustic.shutdown()
            except:
                pass

        # Save acoustic baseline before cleanup
        if self.acoustic_analyzer:
            try:
                self.acoustic_analyzer._save_baseline()
            except:
                pass

        # Clean temp files
        try:
            for file in self.temp_dir.glob("*.wav"):
                try:
                    os.unlink(file)
                except:
                    pass
        except:
            pass

        print("[VOICE] Cleanup complete")


# Test
if __name__ == "__main__":
    print("="*60)
    print("VOICE ENGINE TEST (with Acoustic Analysis)")
    print("="*60)

    engine = VoiceEngine(enable_acoustic_analysis=True)

    # Check dependencies
    deps = engine.check_dependencies()
    print("\nDependencies:")
    for dep, available in deps.items():
        status = "✓" if available else "✗"
        print(f"  {status} {dep}")

    # Check acoustic status
    acoustic_status = engine.get_acoustic_status()
    print(f"\nAcoustic Analysis Status:")
    print(f"  Enabled: {acoustic_status.get('enabled', False)}")
    if acoustic_status.get('enabled'):
        print(f"  Calibrated: {acoustic_status.get('calibrated', False)}")
        print(f"  Progress: {acoustic_status.get('progress_percent', 0):.0f}%")
        print(f"  Utterances: {acoustic_status.get('utterance_count', 0)}")

    # Check microphone
    mic_ok, mic_msg = engine.check_microphone()
    print(f"\nMicrophone: {mic_msg}")

    if not mic_ok:
        print("Cannot continue without microphone")
        exit(1)

    # List devices
    devices = engine.list_audio_devices()
    print(f"\nAudio devices ({len(devices)}):")
    for d in devices:
        print(f"  [{d['index']}] {d['name']}")

    # Test single listen cycle with acoustic analysis
    print("\n" + "="*60)
    print("Testing voice input with acoustic analysis...")
    print("(Speak something - try different emotions!)")
    print("="*60)

    audio = engine._listen_for_speech()
    if audio is not None:
        print(f"Got audio: {len(audio)} samples ({len(audio)/engine.sample_rate:.1f}s)")

        # Run acoustic analysis
        if engine.acoustic_enabled and engine.acoustic_analyzer:
            print("\n[ACOUSTIC ANALYSIS]")
            features = engine.acoustic_analyzer.analyze(audio, engine.sample_rate)
            print(f"  Tags: {features.tags}")
            print(f"  Arousal: {features.arousal:.2f} (0=calm, 1=excited)")
            print(f"  Valence: {features.emotional_valence:.2f} (-1=negative, 1=positive)")
            print(f"  F0 Mean: {features.f0_mean:.1f} Hz")
            print(f"  Speaking Rate: {features.speaking_rate:.1f} syl/s")
            print(f"  Loudness: {features.loudness_mean:.1f}")
        else:
            print("\n[ACOUSTIC] Analysis not available")

        # Transcribe
        transcription = engine._transcribe_audio(audio)
        print(f"\nTranscription: {transcription}")

        # Format with acoustic tags
        if transcription and engine.acoustic_enabled and engine.acoustic_analyzer:
            formatted = engine.acoustic_analyzer.format_for_llm(features.tags, transcription)
            print(f"LLM Input: {formatted}")

        if transcription:
            print("\nTesting streaming TTS...")
            engine._speak_streaming(f"You said: {transcription}")

    engine.cleanup()
    print("\nTest complete!")
