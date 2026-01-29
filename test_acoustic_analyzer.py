"""
Test script for the Acoustic Analyzer

Tests the OpenSMILE-based acoustic feature extraction without requiring
voice input - uses synthetic audio to verify the system works.

Run: python test_acoustic_analyzer.py
"""

import numpy as np
import sys

def test_acoustic_analyzer():
    """Test the acoustic analyzer with synthetic audio."""
    print("=" * 60)
    print("ACOUSTIC ANALYZER TEST")
    print("=" * 60)

    # Try to import the analyzer
    try:
        from engines.acoustic_analyzer import (
            AcousticAnalyzer,
            AsyncAcousticAnalyzer,
            AcousticFeatures,
            OPENSMILE_AVAILABLE
        )
        print("[OK] Acoustic analyzer module imported successfully")
    except ImportError as e:
        print(f"[ERROR] Failed to import acoustic analyzer: {e}")
        print("\nMake sure you're running from the project root directory")
        return False

    # Check OpenSMILE availability
    print(f"\n[INFO] OpenSMILE available: {OPENSMILE_AVAILABLE}")

    if not OPENSMILE_AVAILABLE:
        print("\n[WARNING] OpenSMILE not installed!")
        print("Install with: pip install opensmile")
        print("\nThe acoustic analyzer will work but won't extract prosodic features.")
        print("Testing basic functionality anyway...")

    # Create analyzer (with a test baseline file to not affect real baseline)
    analyzer = AcousticAnalyzer(
        baseline_file="memory/test_acoustic_baseline.json",
        enabled=True,
        calibration_utterances=5
    )

    print(f"\n[INFO] Analyzer created (enabled={analyzer.enabled})")

    # Get baseline status
    status = analyzer.get_baseline_status()
    print(f"[INFO] Baseline status:")
    print(f"  - Calibrated: {status['calibrated']}")
    print(f"  - Progress: {status['progress_percent']:.0f}%")
    print(f"  - Utterances: {status['utterance_count']}")

    # Generate synthetic test audio
    print("\n[TEST] Creating synthetic audio samples...")

    sample_rate = 16000

    def create_test_audio(duration, frequency, amplitude, noise_level=0.1):
        """Create synthetic audio with specified characteristics."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        # Base tone with harmonics
        audio = np.sin(2 * np.pi * frequency * t) * amplitude
        audio += np.sin(2 * np.pi * frequency * 2 * t) * amplitude * 0.3
        audio += np.sin(2 * np.pi * frequency * 3 * t) * amplitude * 0.1
        # Add noise
        audio += np.random.randn(len(audio)) * noise_level * amplitude
        # Convert to int16
        audio = (audio * 32767 / np.max(np.abs(audio))).astype(np.int16)
        return audio

    # Test 1: Normal speech (baseline)
    print("\n[TEST 1] Normal speech simulation (for baseline)")
    audio_normal = create_test_audio(2.0, 150, 0.5)  # 150Hz, medium volume
    features_normal = analyzer.analyze(audio_normal, sample_rate)
    print(f"  Tags: {features_normal.tags}")
    print(f"  Arousal: {features_normal.arousal:.2f}")
    print(f"  Valence: {features_normal.emotional_valence:.2f}")

    # Test 2: Excited speech (higher pitch, more variation)
    print("\n[TEST 2] Excited speech simulation (high pitch, loud)")
    audio_excited = create_test_audio(2.0, 250, 0.9)  # Higher pitch, louder
    features_excited = analyzer.analyze(audio_excited, sample_rate)
    print(f"  Tags: {features_excited.tags}")
    print(f"  Arousal: {features_excited.arousal:.2f}")
    print(f"  Valence: {features_excited.emotional_valence:.2f}")

    # Test 3: Subdued speech (lower pitch, quieter)
    print("\n[TEST 3] Subdued speech simulation (low pitch, quiet)")
    audio_subdued = create_test_audio(2.0, 100, 0.2)  # Lower pitch, quieter
    features_subdued = analyzer.analyze(audio_subdued, sample_rate)
    print(f"  Tags: {features_subdued.tags}")
    print(f"  Arousal: {features_subdued.arousal:.2f}")
    print(f"  Valence: {features_subdued.emotional_valence:.2f}")

    # Test 4: Stressed speech (high noise = high jitter/shimmer simulation)
    print("\n[TEST 4] Stressed speech simulation (high noise/tension)")
    audio_stressed = create_test_audio(2.0, 180, 0.7, noise_level=0.4)  # High noise
    features_stressed = analyzer.analyze(audio_stressed, sample_rate)
    print(f"  Tags: {features_stressed.tags}")
    print(f"  Arousal: {features_stressed.arousal:.2f}")
    print(f"  Valence: {features_stressed.emotional_valence:.2f}")

    # Test LLM formatting
    print("\n[TEST 5] LLM formatting")
    test_cases = [
        (["frustrated", "speaking quickly", "rising pitch"], "I'm fine."),
        (["tired", "quiet", "slow speech"], "Yeah, I'm okay."),
        (["excited", "loud", "fast rate"], "Guess what happened!"),
        ([], "Hello there."),
    ]

    for tags, text in test_cases:
        formatted = analyzer.format_for_llm(tags, text)
        print(f"  {formatted}")

    # Test async analysis
    print("\n[TEST 6] Async analysis")
    async_analyzer = AsyncAcousticAnalyzer(analyzer)
    future = async_analyzer.analyze_async(audio_normal, sample_rate, update_baseline=False)
    try:
        result = future.result(timeout=5.0)
        print(f"  Async result tags: {result.tags}")
        print(f"  Async completed successfully")
    except Exception as e:
        print(f"  Async error: {e}")
    finally:
        async_analyzer.shutdown()

    # Get final baseline status
    status = analyzer.get_baseline_status()
    print(f"\n[INFO] Final baseline status:")
    print(f"  - Calibrated: {status['calibrated']}")
    print(f"  - Progress: {status['progress_percent']:.0f}%")
    print(f"  - Utterances: {status['utterance_count']}")

    # Clean up test baseline file
    import os
    test_baseline = "memory/test_acoustic_baseline.json"
    if os.path.exists(test_baseline):
        os.remove(test_baseline)
        print(f"\n[CLEANUP] Removed test baseline file")

    print("\n" + "=" * 60)
    print("TEST COMPLETE!")
    print("=" * 60)

    if OPENSMILE_AVAILABLE:
        print("\n[OK] OpenSMILE is working - full prosodic feature extraction available")
    else:
        print("\n[WARNING] OpenSMILE not installed - install for full functionality:")
        print("  pip install opensmile")

    print("\nTo test with real voice input, run:")
    print("  python engines/voice_engine.py")

    return True


if __name__ == "__main__":
    success = test_acoustic_analyzer()
    sys.exit(0 if success else 1)
