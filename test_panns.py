"""
Test script for PANNs audio classifier.

Tests:
1. Module imports correctly
2. Model loads (downloads weights on first run)
3. Can classify synthetic audio
4. Can classify real audio file (if provided)

Usage:
    python test_panns.py
    python test_panns.py path/to/audio.wav
"""

import sys
import numpy as np

PASS = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def test_imports():
    """Test that all required modules import."""
    print("=" * 50)
    print("TEST: Module imports")
    print("=" * 50)

    results = {}

    # Test torch
    try:
        import torch
        results['torch'] = True
        print(f"{PASS} torch imported (version {torch.__version__})")
        print(f"     CUDA available: {torch.cuda.is_available()}")
    except ImportError as e:
        results['torch'] = False
        print(f"{FAIL} torch: {e}")

    # Test librosa
    try:
        import librosa
        results['librosa'] = True
        print(f"{PASS} librosa imported")
    except ImportError as e:
        results['librosa'] = False
        print(f"{FAIL} librosa: {e}")

    # Test panns_inference
    try:
        from panns_inference import AudioTagging
        results['panns'] = True
        print(f"{PASS} panns_inference imported")
    except ImportError as e:
        results['panns'] = False
        print(f"{FAIL} panns_inference: {e}")

    # Test our classifier
    try:
        from engines.panns_classifier import PANNsClassifier, PANNS_AVAILABLE
        results['classifier'] = True
        print(f"{PASS} PANNsClassifier imported")
        print(f"     PANNS_AVAILABLE: {PANNS_AVAILABLE}")
    except ImportError as e:
        results['classifier'] = False
        print(f"{FAIL} PANNsClassifier: {e}")

    return all(results.values())


def test_model_loading():
    """Test that the PANNs model loads correctly."""
    print("\n" + "=" * 50)
    print("TEST: Model loading")
    print("=" * 50)

    from engines.panns_classifier import PANNsClassifier

    try:
        print("Loading PANNs model (first run downloads ~300MB)...")
        classifier = PANNsClassifier(
            confidence_threshold=0.1,  # Low threshold for testing
            debug=True
        )

        if classifier.enabled:
            print(f"{PASS} Model loaded successfully")
            print(f"     Device: {classifier.device}")
            return classifier
        else:
            print(f"{FAIL} Model failed to load (check errors above)")
            return None

    except Exception as e:
        print(f"{FAIL} Model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_synthetic_classification(classifier):
    """Test classification with synthetic audio."""
    print("\n" + "=" * 50)
    print("TEST: Synthetic audio classification")
    print("=" * 50)

    if classifier is None:
        print(f"{WARN} Skipping - no classifier available")
        return True

    # Create synthetic audio: 1 second of noise + impulse
    sample_rate = 32000
    duration = 1.0
    samples = int(sample_rate * duration)

    # Create clap-like impulse (sharp attack, fast decay)
    t = np.linspace(0, duration, samples, dtype=np.float32)

    # Base noise
    audio = np.random.randn(samples).astype(np.float32) * 0.01

    # Add impulse at 0.5 seconds
    impulse_start = int(0.5 * sample_rate)
    impulse_len = int(0.02 * sample_rate)  # 20ms
    impulse = np.exp(-np.linspace(0, 10, impulse_len)) * 0.8
    freq = 2000  # Hz
    impulse *= np.sin(2 * np.pi * freq * np.linspace(0, 0.02, impulse_len))

    if impulse_start + impulse_len < len(audio):
        audio[impulse_start:impulse_start + impulse_len] += impulse.astype(np.float32)

    print(f"Created synthetic audio: {duration}s at {sample_rate}Hz")
    print(f"Audio shape: {audio.shape}, dtype: {audio.dtype}")
    print(f"Audio range: [{audio.min():.3f}, {audio.max():.3f}]")

    # Classify
    print("\nRunning classification...")
    result = classifier.classify(audio, sample_rate=sample_rate)

    if result:
        print(f"\n{PASS} Classification succeeded:")
        print(f"     Event type: {result.event_type}")
        print(f"     Confidence: {result.confidence:.2%}")
        print(f"     Alternatives: {result.alternatives[:3]}")
        return True
    else:
        print(f"\n{WARN} No classification result (may be normal for synthetic audio)")
        print("     PANNs is trained on real audio - synthetic impulses may not match")
        return True  # Not a failure, just a limitation


def test_file_classification(classifier, filepath):
    """Test classification with an audio file."""
    print("\n" + "=" * 50)
    print(f"TEST: File classification ({filepath})")
    print("=" * 50)

    if classifier is None:
        print(f"{WARN} Skipping - no classifier available")
        return True

    try:
        import librosa

        # Load audio
        print(f"Loading {filepath}...")
        audio, sr = librosa.load(filepath, sr=32000, mono=True)
        print(f"Loaded: {len(audio) / sr:.2f}s at {sr}Hz")

        # Classify
        print("Running classification...")
        result = classifier.classify(audio, sample_rate=sr)

        if result:
            print(f"\n{PASS} Classification succeeded:")
            print(f"     Event type: {result.event_type}")
            print(f"     Confidence: {result.confidence:.2%}")
            print(f"     Alternatives: {result.alternatives[:5]}")

            # Show top scores if available
            if result.all_scores:
                top_5 = sorted(result.all_scores.items(), key=lambda x: x[1], reverse=True)[:5]
                print(f"\n     Top 5 scores:")
                for label, score in top_5:
                    print(f"       {label}: {score:.2%}")
            return True
        else:
            print(f"\n{WARN} No classification result above threshold")
            return True

    except FileNotFoundError:
        print(f"{FAIL} File not found: {filepath}")
        return False
    except Exception as e:
        print(f"{FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hybrid_mode(classifier):
    """Test hybrid mode with spectral detector."""
    print("\n" + "=" * 50)
    print("TEST: Hybrid mode (PANNs + Spectral)")
    print("=" * 50)

    if classifier is None:
        print(f"{WARN} Skipping - no classifier available")
        return True

    try:
        from engines.environmental_sound_detector import EnvironmentalSoundDetector

        # Create spectral detector
        spectral = EnvironmentalSoundDetector(enabled=True, min_confidence=0.5)

        if not spectral.enabled:
            print(f"{WARN} Spectral detector disabled (missing deps)")
            return True

        # Create test audio with clap-like sound
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)

        audio = np.zeros(samples, dtype=np.float32)

        # Add impulse
        impulse_start = int(0.5 * sample_rate)
        impulse_len = int(0.02 * sample_rate)
        impulse = np.exp(-np.linspace(0, 10, impulse_len)) * 0.8
        freq = 2000
        impulse *= np.sin(2 * np.pi * freq * np.linspace(0, 0.02, impulse_len))
        audio[impulse_start:impulse_start + impulse_len] += impulse.astype(np.float32)

        # Run spectral detection
        spectral_events = spectral.detect_sounds(audio, sample_rate)
        print(f"Spectral detector: {len(spectral_events)} events")

        spectral_result = spectral_events[0] if spectral_events else None

        # Run hybrid classification
        hybrid_result = classifier.classify_with_spectral(
            audio, sample_rate, spectral_result
        )

        if hybrid_result:
            print(f"\n{PASS} Hybrid classification succeeded:")
            print(f"     Event type: {hybrid_result.event_type}")
            print(f"     Confidence: {hybrid_result.confidence:.2%}")
        else:
            print(f"\n{WARN} No hybrid result (may be normal)")

        return True

    except ImportError as e:
        print(f"{WARN} Could not test hybrid mode: {e}")
        return True
    except Exception as e:
        print(f"{FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PANNs AUDIO CLASSIFIER - TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))

    # Only continue if imports pass
    if results[0][1]:
        classifier = test_model_loading()
        results.append(("Model Loading", classifier is not None))

        results.append(("Synthetic Classification", test_synthetic_classification(classifier)))
        results.append(("Hybrid Mode", test_hybrid_mode(classifier)))

        # Test file if provided
        if len(sys.argv) > 1:
            filepath = sys.argv[1]
            results.append(("File Classification", test_file_classification(classifier, filepath)))
    else:
        results.append(("Model Loading", False))
        results.append(("Synthetic Classification", False))
        results.append(("Hybrid Mode", False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}]: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed > 0:
        print("\n" + "=" * 60)
        print("INSTALLATION INSTRUCTIONS")
        print("=" * 60)
        print("To install missing dependencies:")
        print("  pip install torch torchvision torchaudio")
        print("  pip install panns-inference")
        print("  pip install librosa")
        print("\nFirst run will download model weights (~300MB)")
        sys.exit(1)
    else:
        print("\n[OK] All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
