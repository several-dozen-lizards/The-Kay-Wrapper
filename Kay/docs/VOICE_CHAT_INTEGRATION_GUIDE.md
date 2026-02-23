# Voice Chat Integration Guide

## Overview

This guide shows how to add voice chat functionality to Kay UI, including:
- 🎤 Voice input (speech-to-text via Whisper)
- 🔊 Voice output (text-to-speech for Kay's responses)
- Visual recording indicators
- Clean error handling

## Files Created

1. **`voice_handler.py`** - Core voice functionality (recording, Whisper API, TTS)
2. **`voice_ui_integration.py`** - UI components and integration code
3. **`VOICE_CHAT_INTEGRATION_GUIDE.md`** - This file

## Prerequisites

### 1. Install Dependencies

```bash
# Audio recording
pip install sounddevice numpy

# OpenAI API
pip install openai

# Audio playback
pip install pygame

# For WAV file handling (usually included)
# Already available: wave, tempfile
```

### 2. Set OpenAI API Key

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# Or add to .env file
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Microphone Permissions

Ensure your system allows microphone access for Python/terminal applications.

**Windows:**
- Settings → Privacy → Microphone → Allow desktop apps

**macOS:**
- System Preferences → Security & Privacy → Privacy → Microphone → Allow Terminal/Python

**Linux:**
- Usually works by default, check PulseAudio/ALSA permissions if issues

---

## Integration Steps

### Step 1: Add Import to kay_ui.py

At the top of `kay_ui.py`, add:

```python
from voice_ui_integration import VoiceUI
```

### Step 2: Initialize Voice UI

In your `__init__` method, **after creating your input widgets**, add:

```python
def __init__(self):
    # ... existing initialization ...

    # Create input frame and widgets (your existing code)
    self.input_frame = ctk.CTkFrame(self)
    self.user_input = ctk.CTkTextbox(self.input_frame, ...)
    self.send_button = ctk.CTkButton(self.input_frame, ...)

    # ADD THIS: Initialize voice UI
    self.voice_ui = VoiceUI(
        parent_frame=self.input_frame,  # Frame containing input widgets
        text_input_widget=self.user_input,  # Your text input widget
        on_transcription_callback=self._on_voice_transcription
    )

    # ... rest of initialization ...
```

### Step 3: Add Transcription Callback

Add this method to your class:

```python
def _on_voice_transcription(self, transcription):
    """
    Called when voice transcription completes.
    Text is already inserted into input field.
    """
    print(f"[KAY UI] Voice transcription received: {transcription}")
    # Text is already in self.user_input, user can edit before sending
```

### Step 4: Enable TTS for Responses

In your message sending/response method, **after Kay generates a response**, enable TTS:

```python
def send_message(self):
    # Get user message
    user_message = self.user_input.get("1.0", tk.END).strip()

    # ... your existing code to get Kay's response ...
    kay_response = self.get_kay_response(user_message)

    # Display Kay's response
    self.display_message("Kay", kay_response)

    # ADD THIS: Enable TTS playback for this response
    if hasattr(self, 'voice_ui') and self.voice_ui:
        self.voice_ui.set_response_for_tts(kay_response)
```

### Step 5: Add Cleanup

In your cleanup/on_closing method:

```python
def on_closing(self):
    # ... your existing cleanup ...

    # ADD THIS: Clean up voice handler
    if hasattr(self, 'voice_ui') and self.voice_ui:
        self.voice_ui.cleanup()

    self.destroy()
```

### Step 6: (Optional) Add Keyboard Shortcut

In `__init__`, add keyboard binding:

```python
def __init__(self):
    # ... after voice_ui initialization ...

    # Bind Ctrl+M to toggle recording
    self.bind('<Control-m>', self._toggle_voice_recording)

def _toggle_voice_recording(self, event=None):
    """Toggle voice recording on Ctrl+M"""
    if hasattr(self, 'voice_ui') and self.voice_ui:
        self.voice_ui._toggle_recording()
```

---

## Complete Integration Example

Here's a minimal complete example showing where everything goes:

```python
# kay_ui.py

import customtkinter as ctk
import tkinter as tk
from voice_ui_integration import VoiceUI

class KayUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Kay - AI Assistant")
        self.geometry("800x600")

        # Create input frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Text input
        self.user_input = ctk.CTkTextbox(
            self.input_frame,
            height=60,
            font=("Segoe UI", 12)
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Voice UI (adds voice button next to text input)
        self.voice_ui = VoiceUI(
            parent_frame=self.input_frame,
            text_input_widget=self.user_input,
            on_transcription_callback=self._on_voice_transcription
        )

        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            command=self.send_message,
            width=100
        )
        self.send_button.pack(side=tk.LEFT)

        # Keyboard shortcuts
        self.bind('<Control-m>', self._toggle_voice_recording)
        self.bind('<Return>', lambda e: self.send_message())

        # Cleanup on close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _on_voice_transcription(self, transcription):
        """Called when voice transcription completes"""
        print(f"Voice input: {transcription}")

    def _toggle_voice_recording(self, event=None):
        """Toggle voice recording"""
        if self.voice_ui:
            self.voice_ui._toggle_recording()

    def send_message(self):
        """Send message to Kay"""
        user_message = self.user_input.get("1.0", tk.END).strip()

        if not user_message:
            return

        # Clear input
        self.user_input.delete("1.0", tk.END)

        # Get Kay's response (your existing logic)
        kay_response = self.get_kay_response(user_message)

        # Display response (your existing logic)
        self.display_message("Kay", kay_response)

        # Enable TTS for response
        if self.voice_ui:
            self.voice_ui.set_response_for_tts(kay_response)

    def get_kay_response(self, message):
        """Get response from Kay (your existing implementation)"""
        # ... your code ...
        return "Kay's response"

    def display_message(self, sender, message):
        """Display message in chat (your existing implementation)"""
        # ... your code ...
        pass

    def on_closing(self):
        """Clean up on window close"""
        if self.voice_ui:
            self.voice_ui.cleanup()
        self.destroy()

if __name__ == "__main__":
    app = KayUI()
    app.mainloop()
```

---

## UI Layout

The voice button will appear next to your text input:

```
┌─────────────────────────────────────────────────┐
│  [Text Input Field              ] 🎤 [Send]     │
│                                                  │
│  Recording: [Text Input...] ⏺ Recording... 🎤  │
│                                                  │
│  With TTS:  [Text Input...] 🎤 🔊 [Send]        │
└─────────────────────────────────────────────────┘
```

**Button States:**
- **🎤 (gray)** - Click to start recording
- **⏺ (red)** - Recording in progress, click to stop
- **🔊** - Click to play Kay's response as audio
- **⏹** - Stop audio playback

**Indicators:**
- "⏺ Recording..." - Shows while recording
- "Transcribing..." - Shows while processing audio
- "Generating audio..." - Shows while creating TTS

---

## Usage Instructions

### For Voice Input:

1. **Click 🎤 button** or press **Ctrl+M** to start recording
2. **Speak your message** (max 60 seconds)
3. **Click again** (or Ctrl+M) to stop recording
4. **Wait for transcription** (shows "Transcribing...")
5. **Review transcription** in text field (edit if needed)
6. **Click Send** or press Enter

### For Voice Output:

1. **After Kay responds**, click **🔊 button**
2. **Audio generates** (shows "Generating audio...")
3. **Plays automatically** when ready
4. **Click ⏹** to stop playback early

---

## Features

### ✅ Implemented

- **Voice Input**
  - Push-to-talk style (click to record, click to stop)
  - Visual recording indicator
  - Max 60 second recordings
  - Automatic transcription via Whisper API
  - Transcription appears in text field for editing

- **Voice Output**
  - Text-to-speech for Kay's responses
  - Manual trigger (not auto-play)
  - Playback controls (stop button)
  - Multiple voice options available

- **Error Handling**
  - Microphone permission checks
  - API error messages
  - Empty recording detection
  - Timeout for long recordings

- **UI Integration**
  - Non-intrusive button placement
  - Visual feedback (colors, indicators)
  - Keyboard shortcuts
  - Clean resource cleanup

### 🎯 Optional Enhancements

You can customize these in the code:

1. **Voice Activity Detection** (auto-stop when silent)
   - Modify `voice_handler.py` to add VAD
   - Use `webrtcvad` library

2. **Waveform Visualization**
   - Add matplotlib widget to show audio levels
   - Update in recording callback

3. **Voice Selection for TTS**
   - Add dropdown menu in UI
   - Pass selected voice to `text_to_speech()`
   - Voices: alloy, echo, fable, onyx, nova, shimmer

4. **Auto-send After Transcription**
   - In `_on_transcription_complete()`, call `send_message()`
   - Add option toggle in UI

---

## Testing

### Test 1: Basic Voice Input

```bash
python test_voice.py
```

This will:
1. Check microphone
2. Record 5 seconds of audio
3. Transcribe with Whisper
4. Print result

### Test 2: UI Integration

```bash
python kay_ui.py
```

Then:
1. Click 🎤 button
2. Say "Hello Kay, how are you?"
3. Click 🎤 again to stop
4. Wait for transcription
5. Verify text appears in input field
6. Click Send
7. Click 🔊 to hear Kay's response

---

## Troubleshooting

### Issue: "Microphone check failed"

**Fix:**
- Check system microphone permissions
- Test with `python -c "import sounddevice; print(sounddevice.query_devices())"`
- Verify default input device is correct

### Issue: "Voice handler not initialized"

**Fix:**
- Check `OPENAI_API_KEY` environment variable
- Verify API key is valid
- Check console for import errors

### Issue: "Transcription failed: API error"

**Fix:**
- Verify OpenAI API key has Whisper access
- Check internet connection
- Ensure audio file is not empty
- Check OpenAI API status

### Issue: Audio quality is poor

**Fix:**
- Increase `sample_rate` in VoiceHandler (try 24000 or 44100)
- Check microphone quality in system settings
- Reduce background noise

### Issue: TTS playback doesn't work

**Fix:**
- Install pygame: `pip install pygame`
- Check system audio output
- Verify MP3 playback is supported
- Try restarting pygame mixer

### Issue: UI button doesn't appear

**Fix:**
- Check import statement is correct
- Verify `parent_frame` is the correct container
- Check for error messages in console
- Ensure frame is packed/gridded before adding voice UI

---

## Performance Considerations

### API Costs

**Whisper API:**
- $0.006 per minute of audio
- 60-second recording = $0.006

**TTS API:**
- $15 per 1M characters
- Average response ~200 chars = $0.003

**Total:** ~$0.01 per voice interaction (very affordable)

### Latency

- **Recording:** Real-time (no latency)
- **Transcription:** 1-3 seconds for 10-second audio
- **TTS generation:** 2-4 seconds for 200-word response
- **Total:** ~5-7 seconds for full voice cycle

### Optimization Tips

1. **Cache TTS audio** for repeated responses
2. **Use TTS-1-hd** model for better quality (slightly slower)
3. **Adjust sample rate** (16kHz is optimal for Whisper)
4. **Clean up temp files** regularly (done automatically)

---

## API Configuration

### Whisper API Settings

Edit in `voice_handler.py`:

```python
response = self.client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    language="en",  # Set to your language or remove for auto-detect
    # Optional parameters:
    # temperature=0.2,  # Lower = more deterministic
    # prompt="Context for better accuracy"  # Hint words/phrases
)
```

### TTS API Settings

Edit in `voice_handler.py`:

```python
response = self.client.audio.speech.create(
    model="tts-1",  # or "tts-1-hd" for better quality
    voice="nova",  # alloy, echo, fable, onyx, nova, shimmer
    input=text,
    # Optional:
    # speed=1.0,  # 0.25 to 4.0
)
```

---

## Security Notes

1. **API Key Storage**
   - Never commit API keys to git
   - Use environment variables or .env file
   - Add `.env` to `.gitignore`

2. **Audio Files**
   - Temporary files are auto-deleted
   - Stored in system temp directory
   - No audio is saved permanently (by default)

3. **Privacy**
   - Audio is sent to OpenAI for processing
   - OpenAI's data usage policy applies
   - Consider adding user consent prompt

---

## Customization

### Change Voice Button Appearance

In `voice_ui_integration.py`:

```python
self.voice_button = ctk.CTkButton(
    self.voice_frame,
    text="🎙️",  # Change icon
    width=60,  # Adjust size
    height=60,
    font=("Segoe UI", 28),  # Adjust font
    fg_color="#2c2c2c",  # Change color
    corner_radius=30,  # Make it circular
    command=self._toggle_recording
)
```

### Change TTS Voice

Modify `_play_response_tts()`:

```python
audio_file = self.voice_handler.text_to_speech(
    self.current_response_text,
    voice="echo"  # Try: alloy, echo, fable, onyx, nova, shimmer
)
```

### Add Auto-send After Transcription

In `_on_transcription_complete()`:

```python
def _on_transcription_complete(self, transcription: str):
    # ... existing code ...

    # Auto-send (optional)
    if self.auto_send_enabled:
        # Trigger parent's send_message
        self.parent.send_message()
```

---

## File Structure

```
F:\AlphaKayZero\
├── kay_ui.py                          # Your main UI (modify this)
├── voice_handler.py                   # Voice functionality ✅ NEW
├── voice_ui_integration.py            # UI components ✅ NEW
├── VOICE_CHAT_INTEGRATION_GUIDE.md    # This file ✅ NEW
└── temp/                              # Auto-created for audio files
    └── kay_voice/                     # Temp recordings/TTS
```

---

## Summary

**What you get:**
- ✅ Voice input with visual feedback
- ✅ Automatic transcription (Whisper API)
- ✅ Text-to-speech for responses (OpenAI TTS)
- ✅ Clean UI integration
- ✅ Keyboard shortcuts
- ✅ Error handling
- ✅ Resource cleanup

**Setup time:** ~10 minutes
**Integration complexity:** Low (5 small code additions)
**Cost:** ~$0.01 per voice interaction

---

**Ready to use!** Follow the integration steps above and test with `python kay_ui.py`.
