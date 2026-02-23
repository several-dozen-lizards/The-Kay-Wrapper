"""
Voice Chat Setup Script
Automated installation and configuration for voice chat features
"""

import subprocess
import sys
import os
from pathlib import Path


def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info

    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python 3.7+ required (you have {version.major}.{version.minor})")
        return False

    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install required packages"""
    print("\n" + "="*70)
    print("INSTALLING DEPENDENCIES")
    print("="*70)

    packages = [
        ("sounddevice", "Audio recording"),
        ("numpy", "Audio data handling"),
        ("openai", "OpenAI API (Whisper, TTS)"),
        ("pygame", "Audio playback"),
    ]

    failed = []

    for package, description in packages:
        print(f"\nInstalling {package} ({description})...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ])
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            failed.append(package)

    return len(failed) == 0


def check_api_key():
    """Check if OpenAI API key is set"""
    print("\n" + "="*70)
    print("CHECKING API KEY")
    print("="*70)

    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        # Mask key for display
        masked = api_key[:7] + "..." + api_key[-4:]
        print(f"✅ API key found: {masked}")
        return True
    else:
        print("❌ OPENAI_API_KEY not set")
        print("\nSet it with:")
        print("  Windows (PowerShell): $env:OPENAI_API_KEY = 'sk-your-key'")
        print("  Linux/Mac: export OPENAI_API_KEY='sk-your-key'")
        print("\nOr create a .env file with:")
        print("  OPENAI_API_KEY=sk-your-key")
        return False


def verify_files():
    """Check if required files exist"""
    print("\n" + "="*70)
    print("VERIFYING FILES")
    print("="*70)

    required_files = [
        "voice_handler.py",
        "voice_ui_integration.py",
        "VOICE_CHAT_INTEGRATION_GUIDE.md",
        "test_voice.py"
    ]

    all_exist = True

    for filename in required_files:
        filepath = Path(filename)
        if filepath.exists():
            print(f"✅ {filename}")
        else:
            print(f"❌ {filename} - MISSING")
            all_exist = False

    return all_exist


def test_microphone():
    """Test microphone access"""
    print("\n" + "="*70)
    print("TESTING MICROPHONE")
    print("="*70)

    try:
        import sounddevice as sd

        # List devices
        devices = sd.query_devices()
        print("\nAvailable audio devices:")
        for i, device in enumerate(devices):
            device_type = ""
            if device['max_input_channels'] > 0:
                device_type = " [INPUT]"
            if device['max_output_channels'] > 0:
                device_type += " [OUTPUT]"

            print(f"  {i}: {device['name']}{device_type}")

        # Get default input device
        default_input = sd.query_devices(kind='input')
        print(f"\nDefault input device: {default_input['name']}")

        # Quick test
        print("\nTesting microphone (0.1 second)...")
        test_recording = sd.rec(
            int(0.1 * 16000),
            samplerate=16000,
            channels=1,
            dtype='int16'
        )
        sd.wait()

        if len(test_recording) > 0:
            print("✅ Microphone is working!")
            return True
        else:
            print("❌ No audio input detected")
            return False

    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check system microphone permissions")
        print("2. Verify microphone is connected")
        print("3. Test microphone in system settings")
        return False


def create_env_file():
    """Create .env file template"""
    print("\n" + "="*70)
    print("CREATING .ENV FILE")
    print("="*70)

    env_file = Path(".env")

    if env_file.exists():
        print("⚠️  .env file already exists")
        return

    env_template = """# OpenAI API Configuration
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Custom model settings
# OPENAI_WHISPER_MODEL=whisper-1
# OPENAI_TTS_MODEL=tts-1
# OPENAI_TTS_VOICE=nova
"""

    env_file.write_text(env_template)
    print("✅ Created .env file template")
    print("\nEdit .env and add your OpenAI API key")


def main():
    """Run setup"""
    print("\n" + "="*70)
    print("VOICE CHAT SETUP")
    print("="*70)
    print()

    # Check Python version
    if not check_python_version():
        return False

    # Install dependencies
    if not install_dependencies():
        print("\n❌ Dependency installation failed")
        return False

    # Verify files
    if not verify_files():
        print("\n❌ Some required files are missing")
        return False

    # Create .env template
    create_env_file()

    # Check API key
    api_key_ok = check_api_key()

    # Test microphone
    mic_ok = test_microphone()

    # Summary
    print("\n" + "="*70)
    print("SETUP SUMMARY")
    print("="*70)

    print("\n✅ Dependencies installed")
    print("✅ Files verified")

    if api_key_ok:
        print("✅ API key configured")
    else:
        print("⚠️  API key not set (required for voice features)")

    if mic_ok:
        print("✅ Microphone working")
    else:
        print("⚠️  Microphone test failed")

    # Next steps
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)

    if not api_key_ok:
        print("\n1. Set your OpenAI API key:")
        print("   $env:OPENAI_API_KEY = 'sk-your-key'")
        print()

    print(f"{'2' if not api_key_ok else '1'}. Test voice functionality:")
    print("   python test_voice.py")
    print()

    print(f"{'3' if not api_key_ok else '2'}. Integrate into Kay UI:")
    print("   Follow VOICE_CHAT_INTEGRATION_GUIDE.md")
    print()

    if api_key_ok and mic_ok:
        print("="*70)
        print("✅ SETUP COMPLETE! Ready to integrate voice chat.")
        print("="*70)
        return True
    else:
        print("="*70)
        print("⚠️  SETUP INCOMPLETE - Fix issues above before continuing")
        print("="*70)
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
