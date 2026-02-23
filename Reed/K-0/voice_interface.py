"""
Voice interface for Reed
Handles STT (Whisper) and TTS (pyttsx3)
"""

from faster_whisper import WhisperModel
import pyttsx3
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tempfile
import os
import webrtcvad

class VoiceInterface:
    def __init__(self, whisper_model="base", input_device=1, sample_rate=16000):
        """Initialize voice interface"""
        print("🎙️ Initializing voice interface...")
        print(f"   Loading Whisper model: {whisper_model}")
        
        self.whisper = WhisperModel(whisper_model, device="cpu", compute_type="int8")
        self.sample_rate = sample_rate
        self.input_device = input_device

        # VAD setup
        self.vad = webrtcvad.Vad(2)  # Aggressiveness 0-3 (2 is balanced)
        self.frame_duration_ms = 30  # ms per frame
        self.padding_duration_ms = 900  # Wait 900ms of silence before stopping
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)

        # Test TTS on init
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        print(f"   TTS voices available: {len(voices)}")
        engine.stop()
        del engine
        
        print("✓ Voice interface ready!\n")
    
    def listen(self):
        """
        Record audio using VAD - stops automatically when you stop talking
        Continuously streams audio, detects speech, and stops after 900ms silence
        """
        print("🎤 Listening... (speak now)")

        # State tracking
        triggered = False  # Has speech started?
        voiced_frames = []  # All frames with speech
        num_padding_frames = int(self.padding_duration_ms / self.frame_duration_ms)
        ring_buffer = []  # Recent frames to detect silence

        # Audio stream setup
        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.int16,
            blocksize=self.frame_size,
            device=self.input_device
        )

        stream.start()

        try:
            while True:
                # Read one frame
                frame, overflowed = stream.read(self.frame_size)
                if overflowed:
                    print("[Warning] Audio buffer overflow - may miss audio")

                # Convert to bytes for VAD (VAD needs 16-bit PCM bytes)
                frame_bytes = frame.tobytes()

                # VAD needs exactly the right number of bytes
                # For 16kHz, 30ms frame = 480 samples * 2 bytes = 960 bytes
                expected_bytes = self.frame_size * 2
                if len(frame_bytes) != expected_bytes:
                    continue  # Skip incomplete frames

                # Check if this frame contains speech
                is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)

                if not triggered:
                    # Waiting for speech to start
                    if is_speech:
                        triggered = True
                        print("🗣️ Speech detected, recording...")
                        # Include buffered frames that led to trigger
                        for buffered_frame in ring_buffer:
                            voiced_frames.append(buffered_frame)
                        ring_buffer.clear()
                        voiced_frames.append(frame)
                    else:
                        # Keep a buffer of recent frames
                        ring_buffer.append(frame)
                        if len(ring_buffer) > num_padding_frames:
                            ring_buffer.pop(0)
                else:
                    # Speech has started, now watching for silence
                    voiced_frames.append(frame)

                    if not is_speech:
                        ring_buffer.append(frame)
                        if len(ring_buffer) > num_padding_frames:
                            # Been silent for padding_duration_ms, stop recording
                            print("🤐 Silence detected, processing...")
                            break
                    else:
                        # Speech continues, reset silence buffer
                        ring_buffer.clear()

        finally:
            stream.stop()
            stream.close()

        # If no speech was detected at all
        if not triggered:
            print("(no speech detected)")
            return ""

        # Concatenate all voiced frames
        audio_data = np.concatenate(voiced_frames, axis=0)

        # Transcribe
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            write(temp_path, self.sample_rate, audio_data)

        try:
            segments, _ = self.whisper.transcribe(temp_path, beam_size=5)
            transcription = " ".join([seg.text for seg in segments]).strip()
            return transcription
        finally:
            os.unlink(temp_path)
    
    def speak(self, text):
        """
        Convert text to speech
        Creates new engine each time to avoid pyttsx3 bugs
        """
        if not text or text.strip() == "":
            return
        
        print(f"🔊 Kay: {text}")
        
        # Fresh engine each time (pyttsx3 bug workaround)
        engine = pyttsx3.init()
        
        # Voice settings - adjust these based on what sounds best
        engine.setProperty('rate', 175)  # Speed
        # voices = engine.getProperty('voices')
        # engine.setProperty('voice', voices[0].id)  # Try different indices
        
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine
    
    def close(self):
        """Cleanup"""
        print("\n🎙️ Voice interface closing...")