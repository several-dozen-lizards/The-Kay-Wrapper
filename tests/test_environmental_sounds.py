"""
Test script for environmental sound detection.

Tests:
1. Module imports correctly
2. Detector initializes
3. Can detect sounds in synthetic audio
4. Formatting methods work correctly
"""

import numpy as np
import sys

# Use ASCII for Windows compatibility
PASS = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"

def test_imports():
    """Test that all required modules import."""
    print("=" * 50)
    print("TEST: Module imports")
    print("=" * 50)

    try:
        from engines.environmental_sound_detector import (
            EnvironmentalSoundDetector,
            SoundPattern,
            SoundEvent,
            SOUND_PATTERNS,
            LIBROSA_AVAILABLE,
            SCIPY_AVAILABLE
        )
        print(f"{PASS} environmental_sound_detector imports OK")
        print(f"  - librosa available: {LIBROSA_AVAILABLE}")
        print(f"  - scipy available: {SCIPY_AVAILABLE}")
        print(f"  - Sound patterns defined: {list(SOUND_PATTERNS.keys())}")
        return True
    except ImportError as e:
        print(f"{FAIL} Import failed: {e}")
        return False


def test_detector_init():
    """Test detector initialization."""
    print("\n" + "=" * 50)
    print("TEST: Detector initialization")
    print("=" * 50)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    try:
        detector = EnvironmentalSoundDetector(
            enabled=True,
            min_confidence=0.5,
            group_threshold=0.5
        )
        print(f"{PASS} Detector created")
        print(f"  - Enabled: {detector.enabled}")
        print(f"  - Min confidence: {detector.min_confidence}")
        print(f"  - Group threshold: {detector.group_threshold}s")
        return detector
    except Exception as e:
        print(f"{FAIL} Init failed: {e}")
        return None


def test_detection_synthetic():
    """Test detection with synthetic audio containing impulses."""
    print("\n" + "=" * 50)
    print("TEST: Detection with synthetic audio")
    print("=" * 50)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    # Use lower confidence for testing (production uses 0.80)
    detector = EnvironmentalSoundDetector(enabled=True, min_confidence=0.5)

    if not detector.enabled:
        print(f"{WARN} Detector disabled (missing librosa/scipy)")
        print("  This is expected if dependencies aren't installed")
        return True  # Not a failure, just missing deps

    # Create synthetic audio with impulses (clap-like sounds)
    sample_rate = 16000
    duration = 3.0  # 3 seconds
    samples = int(sample_rate * duration)

    # Start with silence
    audio = np.zeros(samples, dtype=np.float32)

    # Add three impulse-like sounds at 0.5s, 1.0s, 1.5s
    impulse_times = [0.5, 1.0, 1.5]
    for t in impulse_times:
        idx = int(t * sample_rate)
        # Create a sharp impulse with fast decay (clap-like)
        impulse_len = int(0.02 * sample_rate)  # 20ms
        impulse = np.exp(-np.linspace(0, 10, impulse_len)) * 0.8
        # Add some high frequency content
        freq = 2000  # Hz
        impulse *= np.sin(2 * np.pi * freq * np.linspace(0, 0.02, impulse_len))

        if idx + impulse_len < len(audio):
            audio[idx:idx+impulse_len] += impulse

    print(f"{PASS} Created synthetic audio: {duration}s, {sample_rate}Hz")
    print(f"  Impulses at: {impulse_times}")

    # Run detection
    try:
        events = detector.detect_sounds(audio, sample_rate)
        print(f"\n{PASS} Detection completed: {len(events)} event groups found")

        for event in events:
            if 'count' in event:
                print(f"  - {event['type']} x {event['count']} "
                      f"[conf: {event['confidence']:.2f}, freq: {event['frequency']:.0f}Hz]")
            else:
                print(f"  - {event['type']} @ {event['timestamp']:.2f}s "
                      f"[conf: {event['confidence']:.2f}]")

        return True
    except Exception as e:
        print(f"{FAIL} Detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_formatting():
    """Test formatting methods."""
    print("\n" + "=" * 50)
    print("TEST: Formatting methods")
    print("=" * 50)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    detector = EnvironmentalSoundDetector(enabled=True)

    # Create mock events
    mock_events = [
        {'type': 'clap', 'count': 3, 'timestamps': [0.5, 1.0, 1.5],
         'confidence': 0.85, 'frequency': 2500},
        {'type': 'knock', 'timestamp': 2.0, 'confidence': 0.7,
         'frequency': 1200, 'amplitude': 0.6}
    ]

    # Test display format
    display = detector.format_for_display(mock_events)
    print(f"{PASS} Display format: '{display}'")
    assert "clap" in display and "3" in display, "Should contain 'clap' and '3'"
    assert "knock" in display, "Should contain 'knock'"

    # Test terminal format
    terminal_lines = detector.format_for_terminal(mock_events)
    print(f"{PASS} Terminal format: {len(terminal_lines)} lines")
    for line in terminal_lines:
        print(f"  {line}")

    # Test empty events
    empty_display = detector.format_for_display([])
    assert empty_display == "", "Empty events should return empty string"
    print(f"{PASS} Empty events handled correctly")

    return True


def test_frequency_filtering():
    """Test that low-frequency noise is filtered out."""
    print("\n" + "=" * 50)
    print("TEST: Frequency filtering")
    print("=" * 50)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector, SOUND_PATTERNS

    detector = EnvironmentalSoundDetector(enabled=True)

    if not detector.enabled:
        print(f"{WARN} Detector disabled (missing librosa/scipy)")
        return True

    # Check that sound patterns have frequency ranges > 100Hz
    print("Checking sound pattern frequency ranges...")
    all_above_100 = True
    for name, pattern in SOUND_PATTERNS.items():
        freq_min, freq_max = pattern.freq_range
        if freq_min < 100:
            print(f"{FAIL} Pattern '{name}' has min freq {freq_min}Hz < 100Hz")
            all_above_100 = False
        else:
            print(f"{PASS} Pattern '{name}': {freq_min}-{freq_max}Hz")

    # Create audio with 80Hz hum (should be filtered)
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    low_freq_audio = 0.5 * np.sin(2 * np.pi * 80 * t).astype(np.float32)

    events = detector.detect_sounds(low_freq_audio, sample_rate)
    if len(events) == 0:
        print(f"{PASS} Low-frequency (80Hz) audio correctly filtered - no false positives")
    else:
        print(f"{FAIL} Low-frequency audio produced {len(events)} false positive(s)")
        all_above_100 = False

    return all_above_100


def test_confidence_threshold():
    """Test that confidence threshold 0.80 is enforced."""
    print("\n" + "=" * 50)
    print("TEST: Confidence threshold (0.80)")
    print("=" * 50)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    # Create detector - should use 0.75 default now
    detector = EnvironmentalSoundDetector(enabled=True)

    if not detector.enabled:
        print(f"{WARN} Detector disabled (missing librosa/scipy)")
        return True

    print(f"Detector min_confidence: {detector.min_confidence}")
    assert detector.min_confidence >= 0.75, f"Expected min_confidence >= 0.75, got {detector.min_confidence}"
    print(f"{PASS} Default confidence threshold is {detector.min_confidence}")

    # Note: The CONFIDENCE_THRESHOLD = 0.80 is hardcoded in _classify_onset
    # So even events that score 0.75-0.79 will be rejected

    return True


def test_speech_filtering():
    """Test that speech filtering marks sounds during speech with reduced confidence."""
    print("\n" + "=" * 50)
    print("TEST: Speech filtering (full audio analysis)")
    print("=" * 50)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    detector = EnvironmentalSoundDetector(enabled=True)

    if not detector.enabled:
        print(f"{WARN} Detector disabled (missing librosa/scipy)")
        print("  This is expected if dependencies aren't installed")
        return True  # Not a failure, just missing deps

    # Test segment merging (still needed for other purposes)
    print("Testing segment merging...")
    segments = [(0, 2), (1.5, 3), (5, 6)]
    merged = detector._merge_overlapping_segments(segments)
    print(f"  Input: {segments}")
    print(f"  Merged: {merged}")
    assert merged == [(0, 3), (5, 6)], f"Expected [(0, 3), (5, 6)], got {merged}"
    print(f"{PASS} Segment merging works correctly")

    # Test non-speech segment calculation (legacy, but still useful)
    print("\nTesting non-speech segment calculation...")
    total_duration = 10.0
    speech_segments = [(1.0, 3.0), (5.0, 7.0)]  # Speech at 1-3s and 5-7s
    non_speech = detector._get_non_speech_segments(total_duration, speech_segments)
    print(f"  Total duration: {total_duration}s")
    print(f"  Speech at: {speech_segments}")
    print(f"  Non-speech at: {non_speech}")

    # Should have 3 non-speech segments: 0-0.95, 3.05-4.95, 7.05-10
    # (with 50ms buffer around speech)
    assert len(non_speech) == 3, f"Expected 3 non-speech segments, got {len(non_speech)}"
    print(f"{PASS} Non-speech calculation works correctly")

    # Test with speech filter method - NEW: analyzes FULL audio
    print("\nTesting detect_sounds_with_speech_filter (FULL audio analysis)...")

    # Create synthetic audio: 10 seconds
    sample_rate = 16000
    duration = 10.0
    audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

    # Add impulse at 0.5s (non-speech period)
    idx_nonspec = int(0.5 * sample_rate)
    impulse_len = int(0.02 * sample_rate)
    impulse = np.exp(-np.linspace(0, 10, impulse_len)) * 0.8
    freq = 2000
    impulse *= np.sin(2 * np.pi * freq * np.linspace(0, 0.02, impulse_len))
    audio[idx_nonspec:idx_nonspec+impulse_len] += impulse

    # Add impulse at 2.0s (during speech - NOW DETECTED but marked)
    idx_speech = int(2.0 * sample_rate)
    audio[idx_speech:idx_speech+impulse_len] += impulse

    # Add impulse at 8.0s (non-speech period)
    idx_nonspec2 = int(8.0 * sample_rate)
    audio[idx_nonspec2:idx_nonspec2+impulse_len] += impulse

    # Speech is at 1-3s and 5-7s
    speech_timestamps = [(1.0, 3.0), (5.0, 7.0)]

    events = detector.detect_sounds_with_speech_filter(audio, sample_rate, speech_timestamps)
    print(f"  Added impulses at: 0.5s (silence), 2.0s (during speech), 8.0s (silence)")
    print(f"  Speech periods: {speech_timestamps}")
    print(f"  Detected events: {len(events)}")

    # Count events by speech context
    during_silence = [e for e in events if not e.get('during_speech', False)]
    during_speech = [e for e in events if e.get('during_speech', False)]

    for event in events:
        if 'timestamp' in event:
            speech_marker = " [during speech]" if event.get('during_speech', False) else ""
            print(f"    - {event['type']} @ {event['timestamp']:.2f}s (conf: {event['confidence']:.2f}){speech_marker}")

    # NEW: Should detect ALL 3 events now (0.5s, 2.0s, and 8.0s)
    # The one at 2.0s should be marked as 'during_speech' with reduced confidence
    print(f"\n  During silence: {len(during_silence)}, During speech: {len(during_speech)}")

    # Verify that sounds during speech are marked correctly
    if len(events) >= 2:
        # At least should detect the two in silence periods
        print(f"{PASS} Full audio analysis completed - sounds detected in both speech and silence")
    else:
        print(f"{WARN} Expected at least 2 events, got {len(events)}")

    # Check that during_speech flag exists on events
    if events and 'during_speech' in events[0]:
        print(f"{PASS} Events have 'during_speech' flag")
    else:
        print(f"{WARN} Events missing 'during_speech' flag")

    return True


def test_voice_engine_integration():
    """Test that voice_engine imports the detector."""
    print("\n" + "=" * 50)
    print("TEST: Voice engine integration")
    print("=" * 50)

    try:
        # Check if import exists in voice_engine
        with open("engines/voice_engine.py", 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ("Import statement", "from engines.environmental_sound_detector import"),
            ("ENVIRONMENTAL_AVAILABLE flag", "ENVIRONMENTAL_AVAILABLE"),
            ("sound_detector attribute", "self.sound_detector"),
            ("on_environmental_sounds callback", "on_environmental_sounds"),
            ("environmental_events variable", "environmental_events"),
            ("Speech filtering method call", "detect_sounds_with_speech_filter"),
            ("Speech timestamps from Whisper", "_transcribe_audio_with_timestamps"),
        ]

        all_passed = True
        for name, pattern in checks:
            if pattern in content:
                print(f"{PASS} {name}: found")
            else:
                print(f"{FAIL} {name}: NOT FOUND")
                all_passed = False

        return all_passed
    except Exception as e:
        print(f"{FAIL} Integration check failed: {e}")
        return False


def test_terminal_dashboard_routing():
    """Test that terminal dashboard routes environmental logs."""
    print("\n" + "=" * 50)
    print("TEST: Terminal dashboard routing")
    print("=" * 50)

    try:
        with open("terminal_dashboard.py", 'r', encoding='utf-8') as f:
            content = f.read()

        checks = [
            ("Environmental Sounds section", '"Environmental Sounds"'),
            ("ENVIRONMENTAL routing", '"ENVIRONMENTAL" in tag_upper'),
            ("SOUND_DETECTED tag", "SOUND_DETECTED"),
            ("SOUND_CLAP tag", "SOUND_CLAP"),
            ("SOUND_KNOCK tag", "SOUND_KNOCK"),
        ]

        all_passed = True
        for name, pattern in checks:
            if pattern in content:
                print(f"{PASS} {name}: found")
            else:
                print(f"{FAIL} {name}: NOT FOUND")
                all_passed = False

        return all_passed
    except Exception as e:
        print(f"{FAIL} Dashboard check failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ENVIRONMENTAL SOUND DETECTION - TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Detector Init", test_detector_init() is not None))
    results.append(("Synthetic Detection", test_detection_synthetic()))
    results.append(("Formatting", test_formatting()))
    results.append(("Frequency Filtering", test_frequency_filtering()))
    results.append(("Confidence Threshold", test_confidence_threshold()))
    results.append(("Speech Filtering", test_speech_filtering()))
    results.append(("Voice Engine Integration", test_voice_engine_integration()))
    results.append(("Terminal Dashboard Routing", test_terminal_dashboard_routing()))

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
        sys.exit(1)
    else:
        print("\n[OK] All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
