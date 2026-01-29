"""
Voice UI Integration for Kay
Add this code to kay_ui.py to enable voice chat functionality
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
from voice_handler import VoiceHandler


class VoiceUI:
    """
    Voice UI components for Kay.
    Handles voice input button, recording indicator, and TTS playback.
    """

    def __init__(self, parent_frame, text_input_widget, on_transcription_callback):
        """
        Initialize voice UI components.

        Args:
            parent_frame: Parent frame to add voice controls to
            text_input_widget: The text input widget to populate with transcriptions
            on_transcription_callback: Callback function when transcription completes
        """
        self.parent_frame = parent_frame
        self.text_input = text_input_widget
        self.on_transcription_callback = on_transcription_callback

        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[VOICE UI] Warning: OPENAI_API_KEY not set. Voice features disabled.")
            self.voice_handler = None
            return

        # Initialize voice handler
        self.voice_handler = VoiceHandler(api_key)

        # Setup callbacks
        self.voice_handler.on_recording_start = self._on_recording_start
        self.voice_handler.on_recording_stop = self._on_recording_stop
        self.voice_handler.on_transcription_start = self._on_transcription_start
        self.voice_handler.on_transcription_complete = self._on_transcription_complete
        self.voice_handler.on_transcription_error = self._on_transcription_error
        self.voice_handler.on_tts_start = self._on_tts_start
        self.voice_handler.on_tts_complete = self._on_tts_complete
        self.voice_handler.on_tts_error = self._on_tts_error

        # UI state
        self.recording_mode = "toggle"  # or "push-to-talk"
        self.current_response_text = None  # For TTS playback

        # Check microphone on init
        success, message = self.voice_handler.check_microphone()
        if not success:
            print(f"[VOICE UI] Microphone check failed: {message}")
            messagebox.showwarning("Microphone Check", f"Microphone issue: {message}\n\nVoice input may not work.")

        # Build UI components
        self._build_ui()

    def _build_ui(self):
        """Build voice UI components."""
        if not self.voice_handler:
            return

        # Voice control frame (horizontal layout)
        self.voice_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        self.voice_frame.grid(row=0, column=1, padx=5, sticky='w')

        # Voice input button (microphone)
        self.voice_button = ctk.CTkButton(
            self.voice_frame,
            text="🎤",
            width=50,
            height=50,
            font=("Segoe UI", 24),
            fg_color="#3c3c3c",
            hover_color="#4c4c4c",
            command=self._toggle_recording
        )
        self.voice_button.grid(row=0, column=0, padx=2)

        # Recording indicator (hidden by default)
        self.recording_indicator = ctk.CTkLabel(
            self.voice_frame,
            text="⏺ Recording...",
            font=("Segoe UI", 10),
            text_color="#ff4444"
        )
        # Don't pack yet - show only when recording

        # Status label (for transcription, TTS, etc.)
        self.status_label = ctk.CTkLabel(
            self.voice_frame,
            text="",
            font=("Segoe UI", 9),
            text_color="#888888"
        )
        # Don't pack yet - show only when needed

        # TTS playback button (hidden by default)
        self.tts_button = ctk.CTkButton(
            self.voice_frame,
            text="🔊",
            width=40,
            height=40,
            font=("Segoe UI", 18),
            fg_color="#3c3c3c",
            hover_color="#4c4c4c",
            command=self._play_response_tts
        )
        # Don't pack yet - show only when response available

        # Stop TTS button (hidden by default)
        self.stop_tts_button = ctk.CTkButton(
            self.voice_frame,
            text="⏹",
            width=40,
            height=40,
            font=("Segoe UI", 18),
            fg_color="#5c3030",
            hover_color="#6c4040",
            command=self._stop_tts
        )
        # Don't pack yet - show only when playing

    def _toggle_recording(self):
        """Toggle recording on/off."""
        if not self.voice_handler:
            messagebox.showerror("Voice Input", "Voice handler not initialized. Check API key.")
            return

        if self.voice_handler.is_recording:
            # Stop recording
            self._stop_recording()
        else:
            # Start recording
            self._start_recording()

    def _start_recording(self):
        """Start recording."""
        success = self.voice_handler.start_recording()
        if not success:
            messagebox.showerror("Recording Error", "Failed to start recording. Check microphone permissions.")

    def _stop_recording(self):
        """Stop recording and transcribe."""
        audio_file = self.voice_handler.stop_recording()

        if audio_file:
            # Transcribe in background
            self.voice_handler.transcribe_async(audio_file)
        else:
            messagebox.showwarning("Recording", "No audio recorded. Try again.")

    def _on_recording_start(self):
        """Callback when recording starts."""
        # Update button appearance
        self.voice_button.configure(
            fg_color="#ff4444",
            hover_color="#ff5555",
            text="⏺"
        )

        # Show recording indicator
        self.recording_indicator.grid(row=0, column=1, padx=5)

    def _on_recording_stop(self):
        """Callback when recording stops."""
        # Reset button appearance
        self.voice_button.configure(
            fg_color="#3c3c3c",
            hover_color="#4c4c4c",
            text="🎤"
        )

        # Hide recording indicator
        self.recording_indicator.grid_forget()

    def _on_transcription_start(self):
        """Callback when transcription starts."""
        # Show status
        self.status_label.configure(text="Transcribing...")
        self.status_label.grid(row=0, column=2, padx=5)

    def _on_transcription_complete(self, transcription: str):
        """Callback when transcription completes."""
        # Hide status
        self.status_label.grid_forget()

        # Insert transcription into text input
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", transcription)

        # Focus text input so user can edit/send
        self.text_input.focus_set()

        # Notify parent callback
        if self.on_transcription_callback:
            self.on_transcription_callback(transcription)

        print(f"[VOICE UI] Transcription complete: '{transcription}'")

    def _on_transcription_error(self, error_message: str):
        """Callback when transcription fails."""
        # Hide status
        self.status_label.grid_forget()

        # Show error
        messagebox.showerror("Transcription Error", error_message)

    def set_response_for_tts(self, response_text: str):
        """
        Set the latest response text for TTS playback.

        Call this after Kay generates a response.

        Args:
            response_text: Kay's response text
        """
        self.current_response_text = response_text

        # Show TTS button
        if not self.tts_button.winfo_ismapped():
            self.tts_button.grid(row=0, column=3, padx=2)

    def _play_response_tts(self):
        """Play current response as audio."""
        if not self.current_response_text:
            messagebox.showwarning("TTS", "No response to play")
            return

        if not self.voice_handler:
            messagebox.showerror("TTS", "Voice handler not initialized")
            return

        # Generate TTS in background
        def generate_and_play():
            audio_file = self.voice_handler.text_to_speech(self.current_response_text)
            if audio_file:
                self.voice_handler.play_audio(audio_file)

        import threading
        threading.Thread(target=generate_and_play, daemon=True).start()

    def _stop_tts(self):
        """Stop TTS playback."""
        if self.voice_handler:
            self.voice_handler.stop_audio()

    def _on_tts_start(self):
        """Callback when TTS starts."""
        # Show status
        self.status_label.configure(text="Generating audio...")
        self.status_label.grid(row=0, column=2, padx=5)

        # Hide TTS button, show stop button
        self.tts_button.grid_forget()
        self.stop_tts_button.grid(row=0, column=3, padx=2)

    def _on_tts_complete(self):
        """Callback when TTS completes."""
        # Hide status
        self.status_label.grid_forget()

        # Keep stop button visible while playing
        # (will be hidden when playback finishes)

    def _on_tts_error(self, error_message: str):
        """Callback when TTS fails."""
        # Hide status
        self.status_label.grid_forget()

        # Show TTS button again
        self.stop_tts_button.grid_forget()
        self.tts_button.grid(row=0, column=3, padx=2)

        # Show error
        messagebox.showerror("TTS Error", error_message)

    def cleanup(self):
        """Clean up voice handler resources."""
        if self.voice_handler:
            self.voice_handler.cleanup()


# ============================================================================
# INTEGRATION INSTRUCTIONS FOR kay_ui.py
# ============================================================================

"""
Add this to your kay_ui.py:

1. Import at the top:
   from voice_ui_integration import VoiceUI

2. In __init__, after creating your text input widget:

   # Initialize voice UI
   self.voice_ui = VoiceUI(
       parent_frame=self.input_frame,  # Frame containing your input widgets
       text_input_widget=self.user_input,  # Your text input widget
       on_transcription_callback=self._on_voice_transcription
   )

3. Add callback method:

   def _on_voice_transcription(self, transcription):
       '''Called when voice transcription completes'''
       print(f"[KAY UI] Voice transcription: {transcription}")
       # Text is already in input field, user can edit/send

4. After Kay generates a response, enable TTS:

   def send_message(self):
       # ... your existing code ...

       # Get Kay's response
       kay_response = self.get_kay_response(user_message)

       # Display in UI
       self.display_message("Kay", kay_response)

       # Enable TTS playback for this response
       if self.voice_ui:
           self.voice_ui.set_response_for_tts(kay_response)

5. In cleanup/on_closing:

   def on_closing(self):
       # ... your existing cleanup ...

       # Clean up voice handler
       if hasattr(self, 'voice_ui') and self.voice_ui:
           self.voice_ui.cleanup()

       self.destroy()

6. (Optional) Add keyboard shortcut:

   def __init__(self):
       # ... existing code ...

       # Bind Ctrl+M to toggle recording
       self.bind('<Control-m>', lambda e: self.voice_ui._toggle_recording() if self.voice_ui else None)
"""
