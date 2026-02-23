"""
Test Voice Handler
Quick test to verify voice functionality before UI integration
"""

import os
import time
from voice_handler import VoiceHandler


def test_microphone():
    """Test 1: Check if microphone is working"""
    print("\n" + "="*70)
    print("TEST 1: MICROPHONE CHECK")
    print("="*70)

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        print("   Set it with: $env:OPENAI_API_KEY = 'sk-your-key'")
        return False

    # Create handler
    handler = VoiceHandler(api_key)

    # Check mic
    success, message = handler.check_microphone()
    print(f"\nMicrophone status: {message}")

    if success:
        print("✅ Microphone is working!")
        return handler
    else:
        print("❌ Microphone check failed")
        print("\nTroubleshooting:")
        print("1. Check system microphone permissions")
        print("2. Verify default input device in system settings")
        print("3. Test with: python -c \"import sounddevice; print(sounddevice.query_devices())\"")
        return None


def test_recording(handler):
    """Test 2: Record audio"""
    print("\n" + "="*70)
    print("TEST 2: AUDIO RECORDING")
    print("="*70)

    print("\nPress Enter to start recording...")
    input()

    # Start recording
    print("\n🎤 Recording started...")
    print("Speak for 3-5 seconds, then press Enter to stop")

    handler.start_recording()

    # Wait for Enter
    input()

    # Stop recording
    print("\n⏹️ Stopping recording...")
    audio_file = handler.stop_recording()

    if audio_file:
        print(f"✅ Recording saved: {audio_file}")
        return audio_file
    else:
        print("❌ Recording failed (no audio data)")
        return None


def test_transcription(handler, audio_file):
    """Test 3: Transcribe audio"""
    print("\n" + "="*70)
    print("TEST 3: TRANSCRIPTION (Whisper API)")
    print("="*70)

    print("\nTranscribing audio...")

    transcription = handler.transcribe_audio(audio_file)

    if transcription:
        print(f"\n✅ Transcription successful!")
        print(f"\n📝 You said: \"{transcription}\"")
        return transcription
    else:
        print("❌ Transcription failed")
        print("\nPossible issues:")
        print("1. Check OPENAI_API_KEY is valid")
        print("2. Verify you have Whisper API access")
        print("3. Check internet connection")
        return None


def test_tts(handler, text):
    """Test 4: Text-to-speech"""
    print("\n" + "="*70)
    print("TEST 4: TEXT-TO-SPEECH (OpenAI TTS)")
    print("="*70)

    print(f"\nGenerating speech for: \"{text[:50]}...\"")

    tts_file = handler.text_to_speech(text)

    if tts_file:
        print(f"✅ TTS generated: {tts_file}")
        return tts_file
    else:
        print("❌ TTS generation failed")
        return None


def test_playback(handler, audio_file):
    """Test 5: Audio playback"""
    print("\n" + "="*70)
    print("TEST 5: AUDIO PLAYBACK")
    print("="*70)

    print("\nPress Enter to play audio...")
    input()

    print("\n🔊 Playing audio...")
    handler.play_audio(audio_file)

    # Wait for playback to finish
    while handler.is_playing:
        time.sleep(0.1)

    print("✅ Playback complete!")


def run_all_tests():
    """Run all voice tests"""
    print("\n" + "="*70)
    print("VOICE HANDLER TEST SUITE")
    print("="*70)
    print("\nThis will test:")
    print("1. Microphone access")
    print("2. Audio recording")
    print("3. Whisper transcription")
    print("4. TTS generation")
    print("5. Audio playback")
    print()

    # Test 1: Microphone
    handler = test_microphone()
    if not handler:
        return

    # Test 2: Recording
    audio_file = test_recording(handler)
    if not audio_file:
        handler.cleanup()
        return

    # Test 3: Transcription
    transcription = test_transcription(handler, audio_file)
    if not transcription:
        handler.cleanup()
        return

    # Test 4: TTS
    test_text = transcription or "Hello, this is a test of the text to speech system."
    tts_file = test_tts(handler, test_text)

    if tts_file:
        # Test 5: Playback
        test_playback(handler, tts_file)

    # Cleanup
    print("\n" + "="*70)
    print("CLEANUP")
    print("="*70)
    print("\nCleaning up temporary files...")
    handler.cleanup()

    print("\n" + "="*70)
    print("ALL TESTS COMPLETE!")
    print("="*70)
    print("\n✅ Voice functionality is working correctly")
    print("\nYou can now integrate into Kay UI:")
    print("1. Follow VOICE_CHAT_INTEGRATION_GUIDE.md")
    print("2. Add voice_ui_integration.py to reed_ui.py")
    print("3. Test with your UI")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
