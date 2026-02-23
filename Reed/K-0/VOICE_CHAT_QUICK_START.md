# Voice Chat - Quick Start Guide

## 3-Minute Setup

### Step 1: Install Dependencies (1 minute)
```bash
python setup_voice_chat.py
```

This installs: sounddevice, numpy, openai, pygame

### Step 2: Set API Key (30 seconds)
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# Or create .env file
OPENAI_API_KEY=sk-your-api-key-here
```

### Step 3: Test (1 minute)
```bash
python test_voice.py
```

Should show:
- ✅ Microphone is working
- ✅ Recording saved
- ✅ Transcription successful
- ✅ TTS generated
- ✅ Playback complete

### Step 4: Integrate into kay_ui.py (30 seconds)

**Add import:**
```python
from voice_ui_integration import VoiceUI
```

**Add to __init__ (after creating input widgets):**
```python
self.voice_ui = VoiceUI(
    parent_frame=self.input_frame,
    text_input_widget=self.user_input,
    on_transcription_callback=self._on_voice_transcription
)
```

**Add callback:**
```python
def _on_voice_transcription(self, transcription):
    print(f"Voice: {transcription}")
```

**Enable TTS (after Kay responds):**
```python
if self.voice_ui:
    self.voice_ui.set_response_for_tts(kay_response)
```

**Add cleanup:**
```python
def on_closing(self):
    if self.voice_ui:
        self.voice_ui.cleanup()
    self.destroy()
```

---

## Usage

### Voice Input:
1. Click **🎤** (or press **Ctrl+M**)
2. Speak (max 60 seconds)
3. Click **🎤** again to stop
4. Wait for transcription
5. Edit text if needed
6. Click **Send**

### Voice Output:
1. After Kay responds, click **🔊**
2. Wait for audio generation
3. Audio plays automatically
4. Click **⏹** to stop early

---

## UI Components

```
┌──────────────────────────────────────┐
│  [Text Input...        ] 🎤 [Send]   │  ← Normal
│                                       │
│  [Text Input...] ⏺ Recording... 🎤   │  ← Recording
│                                       │
│  [Text Input...        ] 🎤 🔊 [Send] │  ← With TTS
└──────────────────────────────────────┘
```

**Icons:**
- 🎤 (gray) = Click to start recording
- ⏺ (red) = Recording, click to stop
- 🔊 = Play Kay's response
- ⏹ = Stop playback

**Status:**
- "⏺ Recording..." = Audio being captured
- "Transcribing..." = Sending to Whisper API
- "Generating audio..." = Creating TTS

---

## Files

| File | Purpose |
|------|---------|
| `voice_handler.py` | Core functionality |
| `voice_ui_integration.py` | UI components |
| `setup_voice_chat.py` | Automated setup |
| `test_voice.py` | Test script |
| `VOICE_CHAT_INTEGRATION_GUIDE.md` | Full docs |
| `VOICE_CHAT_QUICK_START.md` | This file |

---

## Troubleshooting

### "Microphone check failed"
```bash
# Check permissions
# Windows: Settings → Privacy → Microphone → Allow desktop apps

# Test manually
python -c "import sounddevice; print(sounddevice.query_devices())"
```

### "Voice handler not initialized"
```bash
# Check API key is set
echo $env:OPENAI_API_KEY  # Windows
echo $OPENAI_API_KEY      # Linux/Mac
```

### "Transcription failed"
```bash
# Verify API access
# Check: https://platform.openai.com/api-keys
# Ensure Whisper API is enabled
```

### Button doesn't appear
```python
# Check import
from voice_ui_integration import VoiceUI

# Verify parent_frame exists
# Make sure it's packed/gridded before adding voice_ui
```

---

## Customization

### Change Voice (TTS)

In `voice_ui_integration.py`, line ~150:

```python
audio_file = self.voice_handler.text_to_speech(
    text,
    voice="echo"  # Try: alloy, echo, fable, onyx, nova, shimmer
)
```

### Auto-send After Transcription

In `voice_ui_integration.py`, `_on_transcription_complete()`:

```python
# Add after inserting text
self.parent.send_message()  # Auto-send
```

### Change Recording Timeout

In `voice_handler.py`, line ~32:

```python
self.max_recording_seconds = 120  # 2 minutes
```

### Change Sample Rate (Quality)

In `voice_handler.py`, line ~21:

```python
VoiceHandler(api_key, sample_rate=24000)  # Higher quality
```

---

## Costs

**Per voice interaction:**
- Whisper (60s audio): $0.006
- TTS (200 chars): $0.003
- **Total: ~$0.01**

Very affordable for regular use!

---

## Performance

| Operation | Time |
|-----------|------|
| Recording | Real-time |
| Transcription | 1-3 seconds |
| TTS generation | 2-4 seconds |
| Total cycle | ~5-7 seconds |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Ctrl+M** | Toggle recording |
| **Enter** | Send message (if text input focused) |
| **Ctrl+Enter** | (Optional) Auto-send after transcription |

Add custom shortcuts in `kay_ui.py`:

```python
self.bind('<Control-m>', lambda e: self.voice_ui._toggle_recording())
self.bind('<Control-Return>', lambda e: self.send_message())
```

---

## Dependencies

```txt
sounddevice>=0.4.6   # Audio recording
numpy>=1.20.0        # Audio data
openai>=1.0.0        # Whisper + TTS APIs
pygame>=2.0.0        # Audio playback
```

Install all at once:
```bash
pip install sounddevice numpy openai pygame
```

---

## Security

**API Key:**
- Store in environment variable or .env file
- Never commit to git
- Add `.env` to `.gitignore`

**Audio Files:**
- Auto-deleted after use
- Stored in temp directory
- No permanent storage (by default)

**Privacy:**
- Audio sent to OpenAI for processing
- Subject to OpenAI's data usage policy
- Consider adding user consent prompt

---

## Support

**Full documentation:** `VOICE_CHAT_INTEGRATION_GUIDE.md`

**Common issues:**
1. Microphone permissions → Check system settings
2. API errors → Verify OPENAI_API_KEY
3. Import errors → Run `python setup_voice_chat.py`
4. Audio quality → Increase sample_rate to 24000

**Test command:**
```bash
python test_voice.py  # Runs full test suite
```

---

## Example Integration

Minimal working example:

```python
# kay_ui.py

from voice_ui_integration import VoiceUI

class KayUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ... existing setup ...

        # Input frame
        self.input_frame = ctk.CTkFrame(self)
        self.user_input = ctk.CTkTextbox(self.input_frame, ...)

        # ADD: Voice UI
        self.voice_ui = VoiceUI(
            self.input_frame,
            self.user_input,
            self._on_voice_transcription
        )

        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            command=self.send_message
        )

    def _on_voice_transcription(self, text):
        print(f"Transcribed: {text}")

    def send_message(self):
        # ... get Kay's response ...
        kay_response = self.get_kay_response(user_msg)

        # ADD: Enable TTS
        if self.voice_ui:
            self.voice_ui.set_response_for_tts(kay_response)

    def on_closing(self):
        # ADD: Cleanup
        if self.voice_ui:
            self.voice_ui.cleanup()
        self.destroy()
```

---

**Setup time:** 3 minutes
**Integration:** 5 code additions
**Cost:** $0.01 per interaction
**Status:** ✅ Ready to use

Run `python setup_voice_chat.py` to get started!
