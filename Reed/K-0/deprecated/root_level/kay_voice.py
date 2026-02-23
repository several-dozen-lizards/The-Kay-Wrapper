"""
Voice mode for Reed
Uses existing chat_loop from reed_ui.py with voice I/O
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_interface import VoiceInterface
from kay_ui import KayApp

def main():
    """Run Reed in voice-only mode"""
    print("="*60)
    print("KAY ZERO - VOICE MODE")
    print("="*60)
    print("\nInitializing Kay Zero...")
    
    # Initialize Reed (creates its own window)
    print("Loading Kay's systems...")
    kay = KayApp()  # No arguments - it creates its own window
    
    # Hide the window (keep it running but invisible)
    kay.withdraw()
    
    # Initialize voice interface
    print("\nInitializing voice interface...")
    voice = VoiceInterface(whisper_model="base", input_device=1)
    
    print("\n" + "="*60)
    print("🎙️ KAY ZERO IS LISTENING")
    print("="*60)
    print("\nSpeak to Kay. Press Ctrl+C to exit.\n")
    
    # Voice conversation loop
    try:
        while True:
            # LISTEN (VAD-based - stops automatically when you stop talking)
            user_input = voice.listen()
            
            if not user_input or user_input.strip() == "":
                print("(silence)")
                continue
            
            print(f"\n💬 You: {user_input}")
            
            # PROCESS through Reed's existing chat_loop
            try:
                response = kay.chat_loop(user_input)
                
                if not response or response.strip() == "":
                    response = "I'm processing that..."
                
            except Exception as e:
                print(f"[ERROR] Processing failed: {e}")
                import traceback
                traceback.print_exc()
                response = "I'm having trouble processing that. Can you try again?"
            
            # SPEAK Reed's response
            voice.speak(response)
            print()  # Blank line for readability
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Voice session ended")
        print("="*60)
        voice.close()
        kay.destroy()
        sys.exit(0)

if __name__ == "__main__":
    main()