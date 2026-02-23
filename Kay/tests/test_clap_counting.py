"""
Test clap counting with PANNs and spectral detection.

This script tests the clap counting functionality by:
1. Downloading a sample clap audio file (if not present)
2. Testing individual clap detection
3. Testing grouped clap reporting ("clap x3")
4. Comparing PANNs vs spectral detection

Usage:
    python test_clap_counting.py
    python test_clap_counting.py path/to/your/audio.wav
"""

import sys
import numpy as np
import os

# Test markers
PASS = "[OK]"
FAIL = "[FAIL]"
INFO = "[INFO]"


def download_sample_audio():
    """Download a sample clap audio file for testing."""
    import urllib.request

    # Use a free sample from freesound.org (CC0 license)
    # This is a simple hand clap sample
    sample_url = "https://cdn.freesound.org/previews/353/353194_5121236-lq.mp3"
    sample_path = "test_clap_sample.mp3"

    if os.path.exists(sample_path):
        print(f"{INFO} Using existing sample: {sample_path}")
        return sample_path

    print(f"{INFO} Downloading sample clap audio...")
    try:
        urllib.request.urlretrieve(sample_url, sample_path)
        print(f"{PASS} Downloaded: {sample_path}")
        return sample_path
    except Exception as e:
        print(f"{FAIL} Download failed: {e}")
        return None


def create_synthetic_claps(num_claps=3, spacing=0.4):
    """
    Create synthetic audio with multiple claps.

    Uses band-limited noise bursts that better approximate real claps.
    """
    from scipy.signal import butter, filtfilt

    sample_rate = 16000
    duration = 2.0 + (num_claps - 1) * spacing
    audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

    clap_times = []
    for i in range(num_claps):
        clap_time = 0.5 + i * spacing
        clap_times.append(clap_time)

        clap_center = int(clap_time * sample_rate)
        clap_len = int(0.04 * sample_rate)  # 40ms clap

        # Create noise burst with fast decay
        clap_noise = np.random.randn(clap_len).astype(np.float32)
        decay = np.exp(-np.arange(clap_len) / (0.004 * sample_rate))
        clap_noise = clap_noise * decay * 0.8

        # Band-pass filter (1-5 kHz for clap-like spectrum)
        try:
            b, a = butter(4, [1000, 5000], btype='band', fs=sample_rate)
            padded = np.pad(clap_noise, 500, mode='constant')
            clap_filtered = filtfilt(b, a, padded)
            clap_filtered = clap_filtered[500:500+clap_len]
        except:
            clap_filtered = clap_noise

        # Add to audio
        end_idx = min(clap_center + clap_len, len(audio))
        actual_len = end_idx - clap_center
        audio[clap_center:end_idx] = clap_filtered[:actual_len]

    return audio, sample_rate, clap_times


def test_with_synthetic_audio():
    """Test clap detection with synthetic audio."""
    print("\n" + "=" * 60)
    print("TEST: Synthetic Audio with Multiple Claps")
    print("=" * 60)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    # Create audio with 3 claps
    num_claps = 3
    spacing = 0.4  # 400ms between claps
    audio, sample_rate, clap_times = create_synthetic_claps(num_claps, spacing)

    print(f"\n{INFO} Created synthetic audio:")
    print(f"  Duration: {len(audio)/sample_rate:.2f}s")
    print(f"  Claps at: {[f'{t:.2f}s' for t in clap_times]}")
    print(f"  Max amplitude: {np.abs(audio).max():.3f}")

    # Test 1: Spectral mode with individual reporting
    print(f"\n--- Test 1: Spectral Mode (individual reporting) ---")
    detector_spectral = EnvironmentalSoundDetector(
        enabled=True,
        detector_mode="spectral",
        debug_mode=True,
        report_individual=True,
        min_confidence=0.5  # Lower for synthetic audio
    )

    events = detector_spectral.detect(audio, sample_rate)
    print(f"\n{INFO} Spectral detected {len(events)} event(s)")

    # Test 2: Spectral mode with grouped reporting
    print(f"\n--- Test 2: Spectral Mode (grouped reporting) ---")
    detector_grouped = EnvironmentalSoundDetector(
        enabled=True,
        detector_mode="spectral",
        debug_mode=True,
        report_individual=False,
        group_threshold=0.5,
        min_confidence=0.5
    )

    events_grouped = detector_grouped.detect(audio, sample_rate)
    print(f"\n{INFO} Grouped: {len(events_grouped)} event group(s)")
    for e in events_grouped:
        if 'count' in e:
            print(f"  {e['type']} x{e['count']}")
        else:
            print(f"  {e['type']} x1 @ {e.get('timestamp', 0):.2f}s")

    # Test 3: PANNs mode (if available)
    print(f"\n--- Test 3: PANNs Mode ---")
    try:
        detector_panns = EnvironmentalSoundDetector(
            enabled=True,
            detector_mode="panns",
            debug_mode=True,
            report_individual=True,
            panns_confidence=0.1  # Very low for synthetic
        )

        if detector_panns._use_panns:
            events_panns = detector_panns.detect(audio, sample_rate)
            print(f"\n{INFO} PANNs detected {len(events_panns)} event(s)")
            for e in events_panns:
                print(f"  {e.get('type')} @ {e.get('timestamp', 0):.2f}s [{e.get('confidence', 0):.0%}]")
        else:
            print(f"{INFO} PANNs not available, skipped")
    except Exception as e:
        print(f"{FAIL} PANNs test failed: {e}")

    # Test 4: HYBRID mode (best for clap counting)
    print(f"\n--- Test 4: HYBRID Mode (recommended for claps) ---")
    try:
        detector_hybrid = EnvironmentalSoundDetector(
            enabled=True,
            detector_mode="hybrid",
            debug_mode=True,
            report_individual=False,  # Grouped
            min_confidence=0.5,
            panns_confidence=0.1
        )

        if detector_hybrid._use_panns:
            events_hybrid = detector_hybrid.detect(audio, sample_rate)
            print(f"\n{INFO} Hybrid detected {len(events_hybrid)} event group(s)")
            for e in events_hybrid:
                detector_used = e.get('detector', 'unknown')
                if 'count' in e:
                    print(f"  {e['type']} x{e['count']} [{detector_used}]")
                else:
                    print(f"  {e['type']} x1 @ {e.get('timestamp', 0):.2f}s [{detector_used}]")
        else:
            print(f"{INFO} Hybrid not available (PANNs missing), skipped")
    except Exception as e:
        print(f"{FAIL} Hybrid test failed: {e}")

    return True


def test_with_audio_file(filepath):
    """Test clap detection with a real audio file."""
    print("\n" + "=" * 60)
    print(f"TEST: Real Audio File - {filepath}")
    print("=" * 60)

    try:
        import librosa
    except ImportError:
        print(f"{FAIL} librosa required for audio file loading")
        return False

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    # Load audio
    print(f"\n{INFO} Loading audio file...")
    try:
        audio, sr = librosa.load(filepath, sr=16000, mono=True)
        print(f"{PASS} Loaded: {len(audio)/sr:.2f}s at {sr}Hz")
    except Exception as e:
        print(f"{FAIL} Failed to load: {e}")
        return False

    # Test with individual reporting
    print(f"\n--- Spectral Detection (individual) ---")
    detector = EnvironmentalSoundDetector(
        enabled=True,
        detector_mode="spectral",
        debug_mode=True,
        report_individual=True
    )

    events = detector.detect(audio, sr)
    clap_events = [e for e in events if e.get('type') == 'clap']

    print(f"\n{INFO} Total events: {len(events)}")
    print(f"{INFO} Clap events: {len(clap_events)}")

    if clap_events:
        print(f"\nClap timestamps:")
        for i, e in enumerate(clap_events, 1):
            print(f"  #{i}: @ {e.get('timestamp', 0):.3f}s [{e.get('confidence', 0):.0%}]")

    # Test with PANNs
    print(f"\n--- PANNs Detection ---")
    try:
        detector_panns = EnvironmentalSoundDetector(
            enabled=True,
            detector_mode="panns",
            debug_mode=True,
            report_individual=True,
            panns_confidence=0.2
        )

        if detector_panns._use_panns:
            events_panns = detector_panns.detect(audio, sr)
            clap_panns = [e for e in events_panns if 'clap' in e.get('type', '').lower()]

            print(f"\n{INFO} PANNs total events: {len(events_panns)}")
            print(f"{INFO} PANNs clap events: {len(clap_panns)}")

            for e in events_panns:
                print(f"  {e.get('type')} @ {e.get('timestamp', 0):.2f}s [{e.get('confidence', 0):.0%}]")
    except Exception as e:
        print(f"{INFO} PANNs: {e}")

    return True


def test_grouped_vs_individual():
    """Compare grouped vs individual reporting."""
    print("\n" + "=" * 60)
    print("TEST: Grouped vs Individual Reporting Comparison")
    print("=" * 60)

    from engines.environmental_sound_detector import EnvironmentalSoundDetector

    # Create 5 claps in quick succession (should group)
    audio, sr, clap_times = create_synthetic_claps(num_claps=5, spacing=0.25)

    print(f"\n{INFO} Created 5 claps at 250ms intervals")
    print(f"  Times: {[f'{t:.2f}s' for t in clap_times]}")

    # Individual mode
    detector_ind = EnvironmentalSoundDetector(
        enabled=True, detector_mode="spectral",
        report_individual=True, debug_mode=False,
        min_confidence=0.5
    )
    events_ind = detector_ind.detect(audio, sr)

    # Grouped mode
    detector_grp = EnvironmentalSoundDetector(
        enabled=True, detector_mode="spectral",
        report_individual=False, debug_mode=False,
        group_threshold=0.5, min_confidence=0.5
    )
    events_grp = detector_grp.detect(audio, sr)

    print(f"\n{INFO} Individual mode: {len(events_ind)} separate events")
    print(f"{INFO} Grouped mode: {len(events_grp)} event group(s)")

    for e in events_grp:
        if 'count' in e:
            print(f"  -> {e['type']} x{e['count']}")
        else:
            print(f"  -> {e['type']} x1")

    return True


def main():
    print("\n" + "=" * 60)
    print("CLAP COUNTING TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Synthetic audio
    results.append(("Synthetic Audio", test_with_synthetic_audio()))

    # Test 2: Grouped vs Individual
    results.append(("Grouped vs Individual", test_grouped_vs_individual()))

    # Test 3: Real audio file (if provided or downloaded)
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        results.append(("Real Audio File", test_with_audio_file(filepath)))
    else:
        # Try to download sample
        sample = download_sample_audio()
        if sample:
            results.append(("Downloaded Sample", test_with_audio_file(sample)))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed

    for name, result in results:
        status = PASS if result else FAIL
        print(f"  {status} {name}")

    print(f"\nTotal: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
