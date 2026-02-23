from faster_whisper import WhisperModel
import pyttsx3
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tempfile
import os

# Initialize Whisper (this stays persistent)
print("Loading Whisper...")
whisper = WhisperModel("base", device="cpu", compute_type="int8")

print("\n🎙️ VOICE CONVERSATION MODE ACTIVE\n")

def listen(duration=5):
    """Record and transcribe"""
    print("🎤 Listening...")
    audio = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype=np.int16, device=1)
    sd.wait()
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        write(temp_path, 16000, audio)
    
    try:
        segments, _ = whisper.transcribe(temp_path, beam_size=5)
        return " ".join([seg.text for seg in segments]).strip()
    finally:
        os.unlink(temp_path)

def speak(text):
    """Say something - reinitialize engine each time to avoid stuck state"""
    if text:
        print(f"🔊 Kay: {text}")
        
        # Create fresh engine each time (pyttsx3 bug workaround)
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
        engine.stop()  # Clean shutdown
        del engine  # Force cleanup

# BASIC CONVERSATION LOOP
try:
    while True:
        user_input = listen(duration=5)
        
        if not user_input:
            continue
            
        print(f"You: {user_input}")
        
        response = f"I heard you say: {user_input}. This is strange and wonderful, Re."
        
        speak(response)
        
except KeyboardInterrupt:
    print("\n\nVoice mode ended.")