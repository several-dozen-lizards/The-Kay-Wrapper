"""
Voice Handler for Reed UI
Handles audio recording, transcription (Whisper), and text-to-speech (OpenAI TTS)
"""

import sounddevice as sd
import numpy as np
import wave
import tempfile
import os
import threading
import time
from pathlib import Path
from typing import Optional, Callable
from openai import OpenAI


class VoiceHandler:
    """
    Manages voice input/output for Reed UI.

    Features:
    - Audio recording with sounddevice
    - Whisper API transcription
    - OpenAI TTS for response playback
    - Thread-safe operation
    """

    def __init__(self, api_key: str, sample_rate: int = 16000):
        """
        Initialize voice handler.

        Args:
            api_key: OpenAI API key
            sample_rate: Audio sample rate (16kHz recommended for Whisper)
        """
        self.client = OpenAI(api_key=api_key)
        self.sample_rate = sample_rate

        # Recording state
        self.is_recording = False
        self.audio_data = []
        self.recording_thread: Optional[threading.Thread] = None
        self.stream: Optional[sd.InputStream] = None

        # Playback state
        self.is_playing = False
        self.playback_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_recording_start: Optional[Callable] = None
        self.on_recording_stop: Optional[Callable] = None
        self.on_transcription_start: Optional[Callable] = None
        self.on_transcription_complete: Optional[Callable[[str], None]] = None
        self.on_transcription_error: Optional[Callable[[str], None]] = None
        self.on_tts_start: Optional[Callable] = None
        self.on_tts_complete: Optional[Callable] = None
        self.on_tts_error: Optional[Callable[[str], None]] = None

        # Temp file management
        self.temp_dir = Path(tempfile.gettempdir()) / "kay_voice"
        self.temp_dir.mkdir(exist_ok=True)

        # Recording settings
        self.max_recording_seconds = 60
        self.recording_start_time = None

    def check_microphone(self) -> tuple[bool, str]:
        """
        Check if microphone is available.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Test recording for 0.1 seconds
            test_recording = sd.rec(
                int(0.1 * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16
            )
            sd.wait()

            # Check if we got any audio
            if len(test_recording) > 0:
                return (True, "Microphone is working")
            else:
                return (False, "No audio input detected")

        except Exception as e:
            return (False, f"Microphone error: {str(e)}")

    def start_recording(self) -> bool:
        """
        Start recording audio from microphone.

        Returns:
            True if recording started successfully
        """
        if self.is_recording:
            return False

        try:
            # Reset audio buffer
            self.audio_data = []
            self.is_recording = True
            self.recording_start_time = time.time()

            # Create audio stream
            def audio_callback(indata, frames, time_info, status):
                """Callback to collect audio data"""
                if status:
                    print(f"[VOICE] Audio callback status: {status}")

                if self.is_recording:
                    # Check max duration
                    if self.recording_start_time:
                        elapsed = time.time() - self.recording_start_time
                        if elapsed > self.max_recording_seconds:
                            print(f"[VOICE] Max recording time ({self.max_recording_seconds}s) reached")
                            self.stop_recording()
                            return

                    # Append audio data
                    self.audio_data.append(indata.copy())

            # Start stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
                callback=audio_callback
            )
            self.stream.start()

            # Notify callback
            if self.on_recording_start:
                self.on_recording_start()

            print(f"[VOICE] Recording started (max {self.max_recording_seconds}s)")
            return True

        except Exception as e:
            print(f"[VOICE] Error starting recording: {e}")
            self.is_recording = False
            return False

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save to temp file.

        Returns:
            Path to saved audio file, or None if failed
        """
        if not self.is_recording:
            return None

        try:
            self.is_recording = False

            # Stop stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Notify callback
            if self.on_recording_stop:
                self.on_recording_stop()

            # Check if we have audio data
            if not self.audio_data:
                print("[VOICE] No audio data recorded")
                return None

            # Concatenate all audio chunks
            audio_array = np.concatenate(self.audio_data, axis=0)

            # Save to temp WAV file
            temp_file = self.temp_dir / f"recording_{int(time.time())}.wav"

            with wave.open(str(temp_file), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_array.tobytes())

            duration = len(audio_array) / self.sample_rate
            print(f"[VOICE] Recording stopped. Duration: {duration:.1f}s, File: {temp_file.name}")

            return str(temp_file)

        except Exception as e:
            print(f"[VOICE] Error stopping recording: {e}")
            return None

    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file using OpenAI Whisper API.

        Args:
            audio_file_path: Path to audio file

        Returns:
            Transcribed text, or None if failed
        """
        try:
            # Notify callback
            if self.on_transcription_start:
                self.on_transcription_start()

            print(f"[VOICE] Transcribing audio: {audio_file_path}")

            # Open audio file
            with open(audio_file_path, 'rb') as audio_file:
                # Call Whisper API
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # Set to your language or remove for auto-detect
                )

            transcription = response.text
            print(f"[VOICE] Transcription: '{transcription}'")

            # Notify callback
            if self.on_transcription_complete:
                self.on_transcription_complete(transcription)

            # Clean up temp file
            try:
                os.remove(audio_file_path)
                print(f"[VOICE] Cleaned up temp file: {audio_file_path}")
            except:
                pass

            return transcription

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            print(f"[VOICE] {error_msg}")

            # Notify error callback
            if self.on_transcription_error:
                self.on_transcription_error(error_msg)

            return None

    def transcribe_async(self, audio_file_path: str):
        """
        Transcribe audio in background thread (non-blocking).

        Args:
            audio_file_path: Path to audio file
        """
        def transcribe_thread():
            self.transcribe_audio(audio_file_path)

        thread = threading.Thread(target=transcribe_thread, daemon=True)
        thread.start()

    def text_to_speech(self, text: str, voice: str = "nova") -> Optional[str]:
        """
        Convert text to speech using OpenAI TTS API.

        Args:
            text: Text to convert
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)

        Returns:
            Path to generated audio file, or None if failed
        """
        try:
            # Notify callback
            if self.on_tts_start:
                self.on_tts_start()

            print(f"[VOICE] Generating TTS for: '{text[:50]}...'")

            # Generate speech
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )

            # Save to temp file
            temp_file = self.temp_dir / f"tts_{int(time.time())}.mp3"
            response.stream_to_file(str(temp_file))

            print(f"[VOICE] TTS generated: {temp_file.name}")

            # Notify callback
            if self.on_tts_complete:
                self.on_tts_complete()

            return str(temp_file)

        except Exception as e:
            error_msg = f"TTS failed: {str(e)}"
            print(f"[VOICE] {error_msg}")

            # Notify error callback
            if self.on_tts_error:
                self.on_tts_error(error_msg)

            return None

    def play_audio(self, audio_file_path: str):
        """
        Play audio file using pygame.

        Args:
            audio_file_path: Path to audio file (WAV or MP3)
        """
        import pygame

        try:
            if self.is_playing:
                self.stop_audio()

            self.is_playing = True

            # Initialize pygame mixer
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()

            print(f"[VOICE] Playing audio: {audio_file_path}")

            # Wait for playback to finish in background thread
            def wait_for_playback():
                while pygame.mixer.music.get_busy() and self.is_playing:
                    time.sleep(0.1)

                self.is_playing = False

                # Clean up temp file
                try:
                    os.remove(audio_file_path)
                    print(f"[VOICE] Cleaned up audio file: {audio_file_path}")
                except:
                    pass

            self.playback_thread = threading.Thread(target=wait_for_playback, daemon=True)
            self.playback_thread.start()

        except Exception as e:
            print(f"[VOICE] Error playing audio: {e}")
            self.is_playing = False

    def stop_audio(self):
        """Stop audio playback."""
        import pygame

        try:
            if self.is_playing:
                pygame.mixer.music.stop()
                self.is_playing = False
                print("[VOICE] Audio playback stopped")
        except Exception as e:
            print(f"[VOICE] Error stopping audio: {e}")

    def cleanup(self):
        """Clean up resources and temp files."""
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()

        # Stop playback if active
        if self.is_playing:
            self.stop_audio()

        # Clean up temp directory
        try:
            for file in self.temp_dir.glob("*"):
                try:
                    os.remove(file)
                except:
                    pass
            print("[VOICE] Cleaned up temp files")
        except Exception as e:
            print(f"[VOICE] Error cleaning up: {e}")


# Example usage
if __name__ == "__main__":
    import os

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        exit(1)

    # Create handler
    handler = VoiceHandler(api_key)

    # Check microphone
    success, message = handler.check_microphone()
    print(f"Microphone check: {message}")

    if not success:
        exit(1)

    # Test recording
    print("\nPress Enter to start recording...")
    input()

    handler.start_recording()

    print("Recording... Press Enter to stop")
    input()

    audio_file = handler.stop_recording()

    if audio_file:
        print(f"\nTranscribing...")
        transcription = handler.transcribe_audio(audio_file)

        if transcription:
            print(f"\nTranscription: {transcription}")

            print("\nGenerating TTS...")
            tts_file = handler.text_to_speech(transcription)

            if tts_file:
                print(f"Playing audio...")
                handler.play_audio(tts_file)

                # Wait for playback to finish
                while handler.is_playing:
                    time.sleep(0.1)

    handler.cleanup()
    print("\nDone!")
