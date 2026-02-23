"""
Environmental Sound Detector for Reed's Voice System

Detects non-speech sounds (claps, knocks, door slams, footsteps) in audio
so Kay can hear what HAPPENS in the environment, not just what is SAID.

Architecture:
    Audio Recording
        ├─→ Whisper → Speech transcription
        ├─→ OpenSMILE → Vocal features
        └─→ THIS → Environmental sound events

Sound detection uses:
- Onset detection (librosa) to find transient events
- Spectral analysis to classify sound type
- Amplitude envelope for decay rate
- Event grouping for counting (clap × 3)

Usage:
    detector = EnvironmentalSoundDetector()
    events = detector.detect_sounds(audio_waveform, sample_rate=16000)
    # Returns: [{'type': 'clap', 'count': 3, 'timestamps': [1.2, 1.5, 1.8], 'confidence': 0.9}]
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import warnings

# Try to import audio processing libraries
LIBROSA_AVAILABLE = False
SCIPY_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    print("[ENVIRONMENTAL] Warning: librosa not installed. Run: pip install librosa")

try:
    from scipy import signal
    from scipy.signal import butter, sosfilt
    from scipy.ndimage import maximum_filter1d
    SCIPY_AVAILABLE = True
except ImportError:
    print("[ENVIRONMENTAL] Warning: scipy not installed. Run: pip install scipy")

# Try to import PANNs classifier
PANNS_AVAILABLE = False
try:
    from engines.panns_classifier import PANNsClassifier, AudioEvent, PANNS_AVAILABLE as _PANNS_OK
    PANNS_AVAILABLE = _PANNS_OK
except ImportError:
    print("[ENVIRONMENTAL] PANNs classifier not available - using spectral-only mode")


@dataclass
class SoundPattern:
    """Pattern definition for a sound type."""
    name: str
    freq_range: Tuple[float, float]  # Hz (low, high) - dominant frequency range
    duration_range: Tuple[float, float]  # seconds (min, max)
    decay_rate: str  # 'fast', 'medium', 'slow'
    min_amplitude: float  # 0-1 normalized
    max_amplitude: Optional[float] = None  # Optional max amplitude (for quiet sounds like taps)
    centroid_range: Tuple[float, float] = (0, 10000)  # Hz (low, high) - spectral centroid (brightness)
    description: str = ""


@dataclass
class SoundEvent:
    """Detected sound event."""
    type: str
    timestamp: float  # seconds into audio
    confidence: float  # 0-1
    frequency: float  # dominant Hz
    amplitude: float  # 0-1 normalized
    duration: float  # seconds
    decay_rate: float  # higher = faster decay


# Sound pattern library
# Each pattern has:
# - freq_range: Dominant frequency range (Hz)
# - centroid_range: Spectral centroid range (Hz) - measures "brightness"
# - min_amplitude: Minimum peak amplitude to detect
# - max_amplitude: Optional maximum (for quiet-only sounds like taps)
# - decay_rate: Expected decay speed (fast/medium/slow)
#
# CENTROID RANGES (with safety gaps to prevent misclassification):
#   200-800:   Footstep (dull thuds)
#   200-1000:  Door slam (heavy impacts)
#   500-1500:  Knock (wood/door sounds)
#   [SAFETY GAP: 1500-1600 Hz - ambiguous sounds rejected]
#   1600-6000: Clap (bright snap component) - WIDE RANGE to capture variation
#   5500-8000: Tap (very high-frequency clicks only)
#
# Key insight: Claps have both "thud" (low freq) and "snap" (high freq) components.
# We detect ONLY the snap for better separation from footsteps/knocks.
# IMPORTANT: Claps are prioritized over taps - if amplitude is high, it's a clap.
SOUND_PATTERNS = {
    'clap': SoundPattern(
        name='clap',
        freq_range=(800, 12000),  # Focus on "snap" not "thud" - high frequency
        duration_range=(0.01, 0.15),  # Short, percussive
        decay_rate='fast',  # Claps decay quickly (the snap fades fast)
        min_amplitude=0.20,  # Lowered slightly to catch softer claps
        centroid_range=(1600, 6000),  # WIDENED - captures more clap variation
        description="Sharp percussive hand clap (snap component)"
    ),
    'knock': SoundPattern(
        name='knock',
        freq_range=(400, 3500),  # Mid-range wood/door sounds
        duration_range=(0.05, 0.25),
        decay_rate='medium',
        min_amplitude=0.15,
        centroid_range=(500, 1500),  # Kept muddy (below clap's 1600)
        description="Knocking on surface"
    ),
    'door_slam': SoundPattern(
        name='door_slam',
        freq_range=(100, 500),  # Heavy low-frequency impacts
        duration_range=(0.1, 0.5),
        decay_rate='slow',
        min_amplitude=0.40,  # Must be loud
        centroid_range=(200, 1000),  # Must be dull/heavy sounding
        description="Heavy door closing"
    ),
    'footstep': SoundPattern(
        name='footstep',
        freq_range=(100, 350),  # Low thuds (>100Hz to avoid fish tank, HVAC noise)
        duration_range=(0.05, 0.3),
        decay_rate='medium',
        min_amplitude=0.15,
        centroid_range=(200, 800),  # Must be dull/muddy sounding
        description="Footstep on floor"
    ),
    'tap': SoundPattern(
        name='tap',
        freq_range=(4000, 10000),  # RAISED minimum - only very high freq clicks
        duration_range=(0.005, 0.06),  # SHORTER - taps are very brief
        decay_rate='fast',
        min_amplitude=0.05,  # Can be very quiet
        max_amplitude=0.25,  # LOWERED - louder sounds should be claps
        centroid_range=(5500, 8000),  # RAISED - no overlap with clap (1600-6000)
        description="Light tap or click (fingernail, pen)"
    ),
}

# Decay rate thresholds (energy drop per 10ms)
DECAY_THRESHOLDS = {
    'fast': 0.7,    # >70% drop in 10ms
    'medium': 0.4,  # 40-70% drop
    'slow': 0.2,    # <40% drop
}


class EnvironmentalSoundDetector:
    """
    Detects non-speech environmental sounds in audio.

    Uses onset detection + spectral analysis to identify:
    - Claps (percussive, high freq, fast decay)
    - Knocks (percussive, mid freq, medium decay)
    - Door slams (heavy, low freq, slow decay)
    - Footsteps (rhythmic, low-mid freq)
    """

    def __init__(
        self,
        enabled: bool = True,
        min_confidence: float = 0.75,  # Raised from 0.5 to reduce false positives
        group_threshold: float = 0.5,  # Group events within 0.5s
        debug_mode: bool = True,  # SET TO TRUE FOR DEBUGGING - shows why detections are rejected
        detector_mode: str = "auto",  # "spectral", "panns", "hybrid", or "auto"
        panns_confidence: float = 0.3,  # Lower threshold for PANNs (more sensitive)
        report_individual: bool = False,  # If True, report each event separately instead of "clap x3"
    ):
        """
        Initialize environmental sound detector.

        Args:
            enabled: Whether detection is active
            min_confidence: Minimum confidence to report event (default 0.75 to reduce false positives)
            group_threshold: Time window (seconds) to group similar events
            debug_mode: If True, prints detailed logging about why detections are accepted/rejected
            detector_mode: Detection algorithm:
                - "spectral": Original spectral analysis (fast, tuned for specific patterns)
                - "panns": PANNs neural network (multi-label, handles co-occurring sounds)
                - "hybrid": Run both, combine results (best accuracy, slower)
                - "auto": Use PANNs if available, fall back to spectral
            panns_confidence: Minimum confidence for PANNs detections (default 0.3)
            report_individual: If True, report each event separately (clap @ 1.2s, clap @ 1.5s)
                              If False, group nearby events (clap x3)
        """
        self.enabled = enabled and LIBROSA_AVAILABLE and SCIPY_AVAILABLE
        self.min_confidence = min_confidence
        self.group_threshold = group_threshold
        self.DEBUG_MODE = debug_mode
        self.detector_mode = detector_mode
        self.panns_confidence = panns_confidence
        self.report_individual = report_individual

        if not LIBROSA_AVAILABLE:
            print("[ENVIRONMENTAL] Librosa not available - detection disabled")
        if not SCIPY_AVAILABLE:
            print("[ENVIRONMENTAL] Scipy not available - detection disabled")

        # Store sample rate for use in speech filtering
        self.sample_rate = 16000  # Default, updated when detect is called

        # Track rejection stats for debugging
        self._rejection_stats = {
            'low_spectral_centroid': 0,  # Sustained low-freq noise like fish tank bubbling
            'speech_artifact': 0,  # Speech phonemes detected during speech (low flatness, harmonic)
            'high_freq': 0,
            'freq_mismatch': 0,
            'low_confidence': 0,
            'low_amplitude': 0,
            'no_pattern': 0,
        }

        # Initialize PANNs classifier if available and requested
        self.panns_classifier = None
        self._use_panns = False

        if detector_mode in ("panns", "hybrid", "auto"):
            if PANNS_AVAILABLE:
                try:
                    self.panns_classifier = PANNsClassifier(
                        confidence_threshold=panns_confidence,
                        filter_speech=True,
                        filter_music=True,
                        debug=debug_mode
                    )
                    if self.panns_classifier.enabled:
                        self._use_panns = True
                        print(f"[ENVIRONMENTAL] PANNs classifier loaded (threshold={panns_confidence})")
                    else:
                        print("[ENVIRONMENTAL] PANNs failed to initialize - using spectral")
                except Exception as e:
                    print(f"[ENVIRONMENTAL] PANNs initialization error: {e} - using spectral")
            elif detector_mode == "panns":
                print("[ENVIRONMENTAL] PANNs requested but not available - using spectral")

        # Determine effective mode
        if detector_mode == "auto":
            self._effective_mode = "panns" if self._use_panns else "spectral"
        elif detector_mode == "hybrid" and not self._use_panns:
            self._effective_mode = "spectral"
        else:
            self._effective_mode = detector_mode if self._use_panns or detector_mode == "spectral" else "spectral"

        if self.enabled:
            print(f"[ENVIRONMENTAL] Sound detector initialized (mode: {self._effective_mode})")
            if self.DEBUG_MODE:
                print("[ENV DEBUG] Debug mode ENABLED - will show detailed rejection reasons")
                if self._effective_mode in ("spectral", "hybrid"):
                    print("[ENV DEBUG] Sound patterns loaded:")
                    for name, pattern in SOUND_PATTERNS.items():
                        print(f"  {name}: freq={pattern.freq_range}, amp>={pattern.min_amplitude}, decay={pattern.decay_rate}")

    def detect(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        speech_regions: List[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Unified detection entry point - routes to appropriate detector based on mode.

        This is the preferred method to call. It automatically uses:
        - PANNs if available and mode is "panns" or "auto"
        - Spectral if mode is "spectral"
        - Both combined if mode is "hybrid"

        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            speech_regions: Speech timestamps (for context/logging)

        Returns:
            List of detected events
        """
        if not self.enabled:
            return []

        if self._effective_mode == "panns":
            return self.detect_sounds_panns(audio, sample_rate, speech_regions)
        elif self._effective_mode == "hybrid":
            return self.detect_sounds_hybrid(audio, sample_rate, speech_regions)
        else:  # spectral
            return self.detect_sounds(audio, sample_rate, speech_regions)

    def detect_light(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        speech_regions: List[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        LIGHT mode detection - fast spectral analysis only, no PANNs.

        ~10x faster than hybrid mode (~0.3s vs 3s).
        Good for detecting obvious sounds (claps, knocks) but may miss subtle sounds.

        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            speech_regions: Speech timestamps (for context/logging)

        Returns:
            List of detected events with high confidence threshold
        """
        import time
        start_time = time.time()

        print(f"[ENVIRONMENTAL] LIGHT mode starting (enabled={self.enabled})")

        if not self.enabled:
            print("[ENVIRONMENTAL] LIGHT mode: detector not enabled, returning []")
            return []

        # Use spectral-only detection with HIGHER confidence threshold
        # to reduce false positives without PANNs verification
        old_min_confidence = self.min_confidence
        self.min_confidence = max(0.85, self.min_confidence)  # Require 85%+ confidence

        try:
            print(f"[ENVIRONMENTAL] LIGHT mode: calling detect_sounds with audio shape {audio.shape if hasattr(audio, 'shape') else len(audio)}")

            # Add timeout protection - light mode should NEVER take more than 2 seconds
            import threading
            result = []
            error_holder = [None]

            def detect_with_timeout():
                try:
                    nonlocal result
                    result = self.detect_sounds(audio, sample_rate, speech_regions)
                except Exception as e:
                    error_holder[0] = e

            detect_thread = threading.Thread(target=detect_with_timeout)
            detect_thread.start()
            detect_thread.join(timeout=2.0)  # 2 second timeout

            if detect_thread.is_alive():
                print("[ENVIRONMENTAL] LIGHT mode: TIMEOUT after 2s - returning empty")
                # Can't really kill the thread, but we return immediately
                return []

            if error_holder[0]:
                print(f"[ENVIRONMENTAL] LIGHT mode: error in detect_sounds: {error_holder[0]}")
                return []

            elapsed = time.time() - start_time
            print(f"[ENVIRONMENTAL] Light detection complete in {elapsed:.2f}s "
                  f"(found {len(result)} events)")

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[ENVIRONMENTAL] LIGHT mode ERROR after {elapsed:.2f}s: {e}")
            import traceback
            traceback.print_exc()
            return []

        finally:
            self.min_confidence = old_min_confidence  # Restore original threshold

    def detect_sounds_with_speech_filter(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        speech_timestamps: List[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect environmental sounds in FULL audio, marking sounds that occur during speech.

        IMPROVED: Now routes to PANNs when in panns or hybrid mode.
        PANNs performs multi-label classification, detecting co-occurring sounds
        (e.g., clapping DURING speech) that spectral analysis misses.

        Args:
            audio: Audio waveform as numpy array (full audio)
            sample_rate: Sample rate of audio
            speech_timestamps: List of (start_time, end_time) tuples indicating when speech occurs.
                              For spectral mode: sounds during these periods get reduced confidence.
                              For PANNs mode: used for logging only (PANNs handles co-occurrence natively).

        Returns:
            List of detected environmental sound events with 'during_speech' flag
        """
        if not self.enabled:
            return []

        # Convert speech_timestamps to speech_regions format
        speech_regions = speech_timestamps if speech_timestamps else []

        # ROUTE TO PANNS OR HYBRID IF CONFIGURED
        # This is the key fix - use PANNs when available instead of always using spectral
        if self._effective_mode == "panns":
            print(f"[ENVIRONMENTAL] Using PANNs detection (mode: {self._effective_mode})")
            return self.detect_sounds_panns(audio, sample_rate, speech_regions)
        elif self._effective_mode == "hybrid":
            print(f"[ENVIRONMENTAL] Using hybrid detection (mode: {self._effective_mode})")
            return self.detect_sounds_hybrid(audio, sample_rate, speech_regions)

        # SPECTRAL MODE - original implementation
        self.sample_rate = sample_rate

        # Calculate total audio duration
        total_duration = len(audio) / sample_rate

        # Log analysis info
        if speech_timestamps and len(speech_timestamps) > 0:
            speech_duration = sum(end - start for start, end in speech_timestamps)
            non_speech_duration = total_duration - speech_duration
            print(f"[ENVIRONMENTAL] Analyzing FULL audio ({total_duration:.1f}s) [spectral mode]")
            print(f"[ENVIRONMENTAL]   Speech: {speech_duration:.1f}s, Silence: {non_speech_duration:.1f}s")
            print(f"[ENVIRONMENTAL]   Sounds during speech will have reduced confidence")
        else:
            print(f"[ENVIRONMENTAL] Analyzing full audio ({total_duration:.1f}s) - no speech regions [spectral mode]")
            speech_timestamps = []  # Ensure it's an empty list, not None

        # Reset rejection stats for this analysis
        self._rejection_stats = {k: 0 for k in self._rejection_stats}

        if self.DEBUG_MODE:
            print(f"\n[ENV DEBUG] === Analyzing full audio ({total_duration:.2f}s) [SPECTRAL] ===")

        # Detect sounds in FULL audio, passing speech regions for confidence adjustment
        all_detections, total_onsets_found = self._detect_sounds_with_debug(
            audio, sample_rate, time_offset=0.0, speech_regions=speech_timestamps
        )

        # Debug summary
        if self.DEBUG_MODE:
            total_rejected = sum(self._rejection_stats.values())
            during_speech_count = sum(1 for d in all_detections if d.get('during_speech', False))
            during_silence_count = len(all_detections) - during_speech_count

            print(f"\n[ENV DEBUG] ========== ANALYSIS SUMMARY ==========")
            print(f"[ENV DEBUG] Total onsets detected: {total_onsets_found}")
            print(f"[ENV DEBUG] Accepted: {len(all_detections)}, Rejected: {total_rejected}")
            if len(all_detections) > 0:
                print(f"[ENV DEBUG]   - During silence: {during_silence_count}")
                print(f"[ENV DEBUG]   - During speech: {during_speech_count} (reduced confidence)")
            if total_rejected > 0:
                print(f"[ENV DEBUG] Rejection breakdown:")
                for reason, count in self._rejection_stats.items():
                    if count > 0:
                        print(f"[ENV DEBUG]   - {reason}: {count}")
            print(f"[ENV DEBUG] =====================================\n")

        if all_detections:
            # Separate by speech context for logging
            during_silence = [d for d in all_detections if not d.get('during_speech', False)]
            during_speech = [d for d in all_detections if d.get('during_speech', False)]

            print(f"[ENVIRONMENTAL] Found {len(all_detections)} event(s):")
            if during_silence:
                print(f"[ENVIRONMENTAL]   {len(during_silence)} during silence")
            if during_speech:
                print(f"[ENVIRONMENTAL]   {len(during_speech)} during speech (reduced confidence)")

            for detection in all_detections[:5]:  # Show first 5
                speech_marker = " [during speech]" if detection.get('during_speech', False) else ""
                if 'count' in detection:
                    print(f"[ENVIRONMENTAL]   {detection['type']} x{detection['count']} "
                          f"[{detection['confidence']:.0%} conf]{speech_marker}")
                else:
                    print(f"[ENVIRONMENTAL]   {detection['type']} @ {detection.get('timestamp', 0):.1f}s "
                          f"[{detection['confidence']:.0%} conf]{speech_marker}")
            if len(all_detections) > 5:
                print(f"[ENVIRONMENTAL]   ... and {len(all_detections) - 5} more")
        else:
            total_rejected = sum(self._rejection_stats.values())
            if total_rejected > 0:
                print(f"[ENVIRONMENTAL] No sounds passed filters ({total_rejected} rejected: "
                      f"low_centroid={self._rejection_stats['low_spectral_centroid']}, "
                      f"low_conf={self._rejection_stats['low_confidence']}, "
                      f"freq_mismatch={self._rejection_stats['freq_mismatch']})")
            elif total_onsets_found == 0:
                print("[ENVIRONMENTAL] No onsets detected - audio may be too quiet or no transients")
            else:
                print("[ENVIRONMENTAL] No environmental sounds detected")

        return all_detections

    def _get_non_speech_segments(
        self,
        total_duration: float,
        speech_segments: List[tuple]
    ) -> List[tuple]:
        """
        Calculate time periods where no speech is occurring.
        Adds small buffer around speech to avoid edge artifacts.

        Args:
            total_duration: Total audio length in seconds
            speech_segments: List of (start, end) tuples for speech periods

        Returns:
            List of (start, end) tuples for non-speech periods
        """
        # Add buffer around speech (50ms before/after) to avoid detecting
        # speech attack/decay as environmental sounds
        SPEECH_BUFFER = 0.05

        # Apply buffer to all speech segments
        buffered_speech = []
        for start, end in speech_segments:
            buffered_start = max(0, start - SPEECH_BUFFER)
            buffered_end = min(total_duration, end + SPEECH_BUFFER)
            buffered_speech.append((buffered_start, buffered_end))

        # Merge overlapping speech segments
        merged_speech = self._merge_overlapping_segments(buffered_speech)

        # Find gaps between speech segments
        non_speech = []
        current_position = 0

        for speech_start, speech_end in merged_speech:
            # If there's a gap before this speech segment, add it
            if current_position < speech_start:
                non_speech.append((current_position, speech_start))

            # Move position to end of this speech segment
            current_position = max(current_position, speech_end)

        # Add final segment if audio continues after last speech
        if current_position < total_duration:
            non_speech.append((current_position, total_duration))

        return non_speech

    def _merge_overlapping_segments(self, segments: List[tuple]) -> List[tuple]:
        """
        Merge overlapping time segments into continuous periods.
        Example: [(0, 2), (1.5, 3), (5, 6)] -> [(0, 3), (5, 6)]
        """
        if not segments:
            return []

        # Sort by start time
        sorted_segments = sorted(segments, key=lambda x: x[0])

        merged = [sorted_segments[0]]

        for current_start, current_end in sorted_segments[1:]:
            last_start, last_end = merged[-1]

            # If current segment overlaps with last, merge them
            if current_start <= last_end:
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                # No overlap, add as separate segment
                merged.append((current_start, current_end))

        return merged

    def _detect_sounds_with_debug(
        self,
        audio: np.ndarray,
        sample_rate: int,
        time_offset: float = 0.0,
        speech_regions: List[Tuple[float, float]] = None
    ) -> tuple:
        """
        Detect sounds with debug output. Returns (detections, onsets_count).

        IMPROVED: Now accepts speech_regions to mark sounds occurring during speech.

        Args:
            audio: Audio waveform as numpy array
            sample_rate: Sample rate of audio
            time_offset: Time offset to add to timestamps (for segment-relative to absolute)
            speech_regions: List of (start_time, end_time) tuples for speech segments

        Returns:
            Tuple of (list of detections, number of onsets found)
        """
        if not self.enabled:
            return [], 0

        try:
            # Normalize audio
            audio = self._normalize_audio(audio)

            # Check audio amplitude
            max_amp = np.max(np.abs(audio))
            if self.DEBUG_MODE:
                print(f"[ENV DEBUG] Audio max amplitude: {max_amp:.3f}")
                if max_amp < 0.1:
                    print(f"[ENV DEBUG] WARNING: Audio is very quiet (max={max_amp:.3f})")

            # Detect onsets (transient events)
            onsets = self._detect_onsets(audio, sample_rate)

            if self.DEBUG_MODE:
                print(f"[ENV DEBUG] Onset detection found {len(onsets)} potential events")
                if len(onsets) > 0:
                    onset_times_str = ", ".join([f"{t:.2f}s" for t in onsets[:10]])
                    if len(onsets) > 10:
                        onset_times_str += f" ... (+{len(onsets) - 10} more)"
                    print(f"[ENV DEBUG] Onset times: [{onset_times_str}]")
                else:
                    print(f"[ENV DEBUG] NO ONSETS - check if audio contains transients or adjust sensitivity")

            if not onsets:
                return [], 0

            # Classify each onset with detailed debugging
            events = []
            for onset_time in onsets:
                # Calculate absolute timestamp for speech region checking
                abs_timestamp = onset_time + time_offset

                # Check if this onset is during speech BEFORE classification
                # This enables stricter filtering for sounds during speech
                during_speech = False
                if speech_regions:
                    for speech_start, speech_end in speech_regions:
                        # Allow 0.1s buffer on each side for Whisper timing inaccuracy
                        if (speech_start - 0.1) <= abs_timestamp <= (speech_end + 0.1):
                            during_speech = True
                            break

                # Classify with speech context - applies stricter filters during speech
                event = self._classify_onset_debug(audio, sample_rate, onset_time, during_speech=during_speech)

                if event:
                    # Apply additional confidence penalty for sounds during speech
                    confidence = event.confidence
                    if during_speech:
                        confidence *= 0.85  # 15% penalty
                        if self.DEBUG_MODE:
                            print(f"  [DURING SPEECH] Confidence reduced: {event.confidence:.2f} -> {confidence:.2f}")

                    event_dict = {
                        'type': event.type,
                        'timestamp': abs_timestamp,
                        'confidence': confidence,
                        'frequency': event.frequency,
                        'amplitude': event.amplitude,
                        'during_speech': during_speech
                    }
                    events.append(event_dict)

            return events, len(onsets)

        except Exception as e:
            print(f"[ENVIRONMENTAL] Detection error: {e}")
            import traceback
            traceback.print_exc()
            return [], 0

    def detect_sounds(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        speech_regions: List[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect environmental sounds in audio.

        IMPROVED: Now analyzes FULL audio and marks sounds that occur during speech.
        Sounds during speech get a confidence penalty but are still reported.
        This allows detection of claps/knocks even when they overlap with speech.

        Args:
            audio: Audio waveform as numpy array (analyze ALL of it)
            sample_rate: Sample rate of audio
            speech_regions: List of (start_time, end_time) tuples indicating speech segments.
                           Sounds occurring during these regions get 15% confidence penalty.
                           If None, all audio is treated as non-speech.

        Returns:
            List of detected sound events, grouped by type:
            [{'type': 'clap', 'count': 3, 'timestamps': [1.2, 1.5, 1.8], 'confidence': 0.9, 'during_speech': False}, ...]
        """
        if not self.enabled:
            return []

        try:
            self.sample_rate = sample_rate

            # Normalize audio
            audio = self._normalize_audio(audio)

            # Detect onsets (transient events) in FULL audio
            onsets = self._detect_onsets(audio, sample_rate)

            if not onsets:
                return []

            # Classify each onset
            events = []
            for onset_time in onsets:
                # Check if this onset is during speech BEFORE classification
                # This enables stricter filtering for sounds during speech
                during_speech = False
                if speech_regions:
                    for speech_start, speech_end in speech_regions:
                        # Sound overlaps if it's within or near a speech segment
                        # Allow 0.1s buffer on each side for Whisper timing inaccuracy
                        if (speech_start - 0.1) <= onset_time <= (speech_end + 0.1):
                            during_speech = True
                            break

                # Classify with speech context - applies stricter filters during speech
                event = self._classify_onset(audio, sample_rate, onset_time, during_speech=during_speech)

                if event and event.confidence >= self.min_confidence:
                    # Apply additional confidence penalty for sounds during speech
                    if during_speech:
                        event = SoundEvent(
                            type=event.type,
                            timestamp=event.timestamp,
                            confidence=event.confidence * 0.85,  # 15% penalty
                            frequency=event.frequency,
                            amplitude=event.amplitude,
                            duration=event.duration,
                            decay_rate=event.decay_rate
                        )

                    # Store during_speech flag for output formatting
                    events.append((event, during_speech))

            # Group similar events that occur close together
            # Extract just the events for grouping
            events_only = [e[0] for e in events]
            during_speech_map = {e[0].timestamp: e[1] for e in events}

            grouped = self._group_events(events_only)

            # Convert to output format with during_speech flag
            return self._format_output_with_speech_flag(grouped, during_speech_map)

        except Exception as e:
            print(f"[ENVIRONMENTAL] Detection error: {e}")
            return []

    def _format_output_with_speech_flag(
        self,
        grouped_events: Dict[str, List[List[SoundEvent]]],
        during_speech_map: Dict[float, bool]
    ) -> List[Dict[str, Any]]:
        """
        Format grouped events for output, including during_speech flag.
        """
        output = []

        for sound_type, groups in grouped_events.items():
            for group in groups:
                if len(group) == 1:
                    # Single event
                    event = group[0]
                    during_speech = during_speech_map.get(event.timestamp, False)
                    output.append({
                        'type': sound_type,
                        'timestamp': event.timestamp,
                        'confidence': event.confidence,
                        'frequency': event.frequency,
                        'amplitude': event.amplitude,
                        'during_speech': during_speech
                    })
                else:
                    # Multiple events - count them
                    avg_confidence = sum(e.confidence for e in group) / len(group)
                    timestamps = [e.timestamp for e in group]
                    avg_freq = sum(e.frequency for e in group) / len(group)
                    # Mark as during_speech if ANY of the events were during speech
                    any_during_speech = any(during_speech_map.get(e.timestamp, False) for e in group)

                    output.append({
                        'type': sound_type,
                        'count': len(group),
                        'timestamps': timestamps,
                        'confidence': avg_confidence,
                        'frequency': avg_freq,
                        'during_speech': any_during_speech
                    })

        # Sort by first timestamp
        output.sort(key=lambda x: x.get('timestamp', x.get('timestamps', [0])[0]))

        return output

    def detect_sounds_panns(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        speech_regions: List[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect environmental sounds using PANNs neural network.

        PANNs (Pre-trained Audio Neural Networks) performs multi-label classification,
        meaning it can detect co-occurring sounds (e.g., clapping DURING speech).
        This is the key advantage over spectral analysis which treats sounds as mutually exclusive.

        Uses onset detection to find candidate timestamps, then runs PANNs on
        short segments around each onset for efficient processing.

        Args:
            audio: Audio waveform as numpy array
            sample_rate: Sample rate of audio
            speech_regions: List of (start, end) tuples for speech (used for logging only,
                           PANNs handles co-occurring sounds natively)

        Returns:
            List of detected events in standard format
        """
        if not self._use_panns or self.panns_classifier is None:
            if self.DEBUG_MODE:
                print("[PANNS] PANNs not available, falling back to spectral")
            return self.detect_sounds(audio, sample_rate, speech_regions)

        try:
            self.sample_rate = sample_rate
            audio = self._normalize_audio(audio)
            total_duration = len(audio) / sample_rate

            if self.DEBUG_MODE:
                print(f"\n[PANNS] === Analyzing {total_duration:.2f}s of audio ===")

            # Strategy: Use onset detection to find candidate timestamps,
            # then run PANNs on 1-second segments around each onset
            onsets = self._detect_onsets(audio, sample_rate)

            if self.DEBUG_MODE:
                print(f"[PANNS] Found {len(onsets)} onset candidates")

            if not onsets:
                # No onsets - run PANNs on full audio as fallback
                if self.DEBUG_MODE:
                    print("[PANNS] No onsets detected, running on full audio")
                result = self.panns_classifier.classify(audio, sample_rate)
                if result:
                    return [self._panns_event_to_dict(result, 0.0, speech_regions)]
                return []

            # Pre-filter onsets AGGRESSIVELY to reduce PANNs inference time
            # OPTIMIZED: Increased gap (0.8s vs 0.5s) and reduced max (10 vs 20)
            MIN_ONSET_GAP = 0.8  # seconds - more aggressive filtering
            MAX_ONSETS = 10  # REDUCED for performance - max 10 PANNs calls

            filtered_onsets = []
            last_onset = -999
            for onset_time in sorted(onsets):
                if onset_time - last_onset >= MIN_ONSET_GAP:
                    filtered_onsets.append(onset_time)
                    last_onset = onset_time

            # Limit number of onsets to process
            if len(filtered_onsets) > MAX_ONSETS:
                # OPTIMIZED: Sort by amplitude and keep strongest onsets
                # This ensures we process the most likely sound events
                onset_amplitudes = []
                for onset_time in filtered_onsets:
                    start_sample = max(0, int((onset_time - 0.025) * sample_rate))
                    end_sample = min(len(audio), int((onset_time + 0.025) * sample_rate))
                    amp = np.max(np.abs(audio[start_sample:end_sample]))
                    onset_amplitudes.append((onset_time, amp))

                # Sort by amplitude (descending) and take top MAX_ONSETS
                onset_amplitudes.sort(key=lambda x: x[1], reverse=True)
                filtered_onsets = sorted([t for t, _ in onset_amplitudes[:MAX_ONSETS]])

            if self.DEBUG_MODE and len(onsets) != len(filtered_onsets):
                print(f"[PANNS] Filtered {len(onsets)} onsets down to {len(filtered_onsets)} (gap={MIN_ONSET_GAP}s, max={MAX_ONSETS}, by amplitude)")

            # Run PANNs on segments around each filtered onset
            events = []

            for onset_time in filtered_onsets:
                # Extract 1-second segment centered on onset
                segment_duration = 1.0
                start_time = max(0, onset_time - segment_duration / 2)
                end_time = min(total_duration, onset_time + segment_duration / 2)

                start_sample = int(start_time * sample_rate)
                end_sample = int(end_time * sample_rate)

                segment = audio[start_sample:end_sample]

                if len(segment) < sample_rate * 0.1:  # Minimum 100ms
                    continue

                # Run PANNs inference
                result = self.panns_classifier.classify(segment, sample_rate)

                if result:
                    event_dict = self._panns_event_to_dict(result, onset_time, speech_regions)
                    events.append(event_dict)

                    if self.DEBUG_MODE:
                        during_speech = event_dict.get('during_speech', False)
                        speech_marker = " [during speech]" if during_speech else ""
                        alt_str = ", ".join([f"{l}({s:.0%})" for l, s in result.alternatives[:2]])
                        print(f"[PANNS] @ {onset_time:.2f}s: {result.event_type} ({result.confidence:.0%}){speech_marker}")
                        if alt_str:
                            print(f"[PANNS]   alternatives: {alt_str}")

            # Merge nearby events of the same type
            events = self._merge_nearby_events(events)

            if self.DEBUG_MODE:
                print(f"[PANNS] === Final: {len(events)} event(s) detected ===\n")

            return events

        except Exception as e:
            print(f"[PANNS] Detection error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def detect_sounds_hybrid(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        speech_regions: List[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid detection: Run both PANNs and spectral analysis, combine results.

        This provides the best of both approaches:
        - PANNs: Better at detecting sounds during speech (multi-label)
        - Spectral: Better at detecting specific percussive patterns (tuned thresholds)

        When both agree, confidence is boosted. When they disagree, higher confidence wins.

        PERFORMANCE: Runs PANNs and spectral in PARALLEL using threads.

        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            speech_regions: Speech timestamps for context

        Returns:
            Combined list of detected events
        """
        if not self._use_panns:
            return self.detect_sounds(audio, sample_rate, speech_regions)

        import concurrent.futures
        import time

        start_time = time.time()

        # Run both detectors IN PARALLEL for better performance
        panns_events = []
        spectral_events = []

        def run_panns():
            return self.detect_sounds_panns(audio, sample_rate, speech_regions)

        def run_spectral():
            return self.detect_sounds(audio, sample_rate, speech_regions)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            panns_future = executor.submit(run_panns)
            spectral_future = executor.submit(run_spectral)

            panns_events = panns_future.result()
            spectral_events = spectral_future.result()

        if self.DEBUG_MODE:
            elapsed = time.time() - start_time
            print(f"[HYBRID] Parallel detection completed in {elapsed:.2f}s")

        if self.DEBUG_MODE:
            print(f"[HYBRID] PANNs: {len(panns_events)}, Spectral: {len(spectral_events)}")

        # Combine results with voting
        combined = self._combine_detection_results(panns_events, spectral_events)

        if self.DEBUG_MODE:
            print(f"[HYBRID] Combined: {len(combined)} events")

        return combined

    def _panns_event_to_dict(
        self,
        event: 'AudioEvent',
        timestamp: float,
        speech_regions: List[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """Convert PANNs AudioEvent to standard dict format."""
        # Check if during speech
        during_speech = False
        if speech_regions:
            for start, end in speech_regions:
                if start - 0.1 <= timestamp <= end + 0.1:
                    during_speech = True
                    break

        # Normalize event type name to match spectral detector
        event_type = event.event_type.lower()
        type_mapping = {
            'clapping': 'clap',
            'finger snapping': 'snap',
            'hands': 'clap',
            'walk, footsteps': 'footstep',
            'knock': 'knock',
            'tap': 'tap',
            'door': 'door_slam',
            'thump, thud': 'thud',
        }
        normalized_type = type_mapping.get(event_type, event_type)

        return {
            'type': normalized_type,
            'timestamp': timestamp,
            'confidence': event.confidence,
            'frequency': 0,  # PANNs doesn't report frequency
            'amplitude': 0,  # PANNs doesn't report amplitude
            'during_speech': during_speech,
            'detector': 'panns',
            'alternatives': [(type_mapping.get(l.lower(), l.lower()), s)
                           for l, s in event.alternatives[:3]]
        }

    def _merge_nearby_events(
        self,
        events: List[Dict[str, Any]],
        time_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Merge events of the same type that occur within time_threshold seconds.

        If report_individual is True, returns all events separately.
        If report_individual is False, groups nearby events (e.g., "clap x3").
        """
        if not events:
            return []

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.get('timestamp', 0))

        # If report_individual is True, return all events separately with detailed logging
        if self.report_individual:
            if self.DEBUG_MODE:
                print(f"\n[CLAP COUNT] Individual event reporting enabled")
                print(f"[CLAP COUNT] Found {len(sorted_events)} individual event(s):")
                for i, event in enumerate(sorted_events, 1):
                    event_type = event.get('type', 'unknown')
                    timestamp = event.get('timestamp', 0)
                    confidence = event.get('confidence', 0)
                    print(f"[CLAP COUNT]   #{i}: {event_type} @ {timestamp:.3f}s [{confidence:.0%}]")
            return sorted_events

        # Group by type and merge nearby
        merged = []
        current_group = [sorted_events[0]]

        for event in sorted_events[1:]:
            last_event = current_group[-1]

            # Check if same type and close in time
            if (event.get('type') == last_event.get('type') and
                abs(event.get('timestamp', 0) - last_event.get('timestamp', 0)) <= time_threshold):
                current_group.append(event)
            else:
                # Different type or too far apart - finalize current group
                merged.append(self._finalize_event_group(current_group))
                current_group = [event]

        # Don't forget last group
        merged.append(self._finalize_event_group(current_group))

        # Detailed logging for grouped events
        if self.DEBUG_MODE:
            print(f"\n[CLAP COUNT] Grouped event reporting (threshold: {time_threshold}s)")
            for event in merged:
                event_type = event.get('type', 'unknown')
                count = event.get('count', 1)
                if count > 1:
                    timestamps = event.get('timestamps', [])
                    timestamps_str = ", ".join([f"{t:.3f}s" for t in timestamps])
                    print(f"[CLAP COUNT]   {event_type} x{count} at [{timestamps_str}]")
                else:
                    timestamp = event.get('timestamp', 0)
                    print(f"[CLAP COUNT]   {event_type} x1 @ {timestamp:.3f}s")

        return merged

    def _finalize_event_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Finalize a group of events into a single event (possibly with count)."""
        if len(group) == 1:
            return group[0]

        # Multiple events of same type - create counted event
        avg_confidence = sum(e.get('confidence', 0) for e in group) / len(group)
        timestamps = [e.get('timestamp', 0) for e in group]
        any_during_speech = any(e.get('during_speech', False) for e in group)

        return {
            'type': group[0].get('type'),
            'count': len(group),
            'timestamps': timestamps,
            'confidence': avg_confidence,
            'frequency': 0,
            'during_speech': any_during_speech,
            'detector': group[0].get('detector', 'unknown')
        }

    def _combine_detection_results(
        self,
        panns_events: List[Dict[str, Any]],
        spectral_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine PANNs and spectral detection results.

        IMPORTANT: PANNs is NOT good at detecting single hand claps (trained on applause).
        For claps specifically, we PREFER spectral detection.

        Strategy:
        - For CLAPS: Prefer spectral detection, override PANNs if spectral detects clap
        - For other sounds: If both detect same type at similar time, boost confidence
        - If PANNs detects "animal" but spectral detects "clap" at same time -> use clap
        - If only one detects: include if above threshold
        """
        combined = []
        used_spectral = set()
        used_panns = set()

        # PANNs types that are often misclassified claps
        # (PANNs confuses single claps with animal/impact sounds)
        clap_confusion_types = {'animal', 'dog', 'domestic animals, pets', 'chop', 'thud', 'slap, smack'}

        # FIRST PASS: Process spectral events, looking for claps
        # Spectral is AUTHORITATIVE for claps since PANNs can't detect single hand claps well
        for i, spectral_event in enumerate(spectral_events):
            spectral_time = spectral_event.get('timestamp', 0)
            spectral_type = spectral_event.get('type', '')

            # For claps, spectral is authoritative - check if PANNs detected anything at same time
            if spectral_type == 'clap':
                # Look for any PANNs event at same time (might be misclassified as animal/chop)
                panns_match = None
                for j, panns_event in enumerate(panns_events):
                    if j in used_panns:
                        continue
                    panns_time = panns_event.get('timestamp', 0)
                    if abs(panns_time - spectral_time) < 0.4:  # Within 400ms
                        panns_match = (j, panns_event)
                        break

                if panns_match:
                    j, panns_event = panns_match
                    panns_type = panns_event.get('type', '').lower()
                    used_panns.add(j)
                    used_spectral.add(i)

                    # If PANNs detected something (even if wrong type), boost clap confidence
                    # because PANNs confirms there WAS a sound at that time
                    if panns_type in clap_confusion_types:
                        # PANNs detected animal/chop but spectral says clap -> trust spectral
                        boosted_conf = min(1.0, spectral_event.get('confidence', 0) * 1.3)
                        if self.DEBUG_MODE:
                            print(f"[HYBRID] Reclassified '{panns_type}' as 'clap' @ {spectral_time:.2f}s "
                                  f"(spectral detected clap, boosted to {boosted_conf:.0%})")
                    else:
                        # PANNs detected something else - still use spectral clap but lower boost
                        boosted_conf = min(1.0, spectral_event.get('confidence', 0) * 1.1)

                    combined.append({
                        'type': 'clap',
                        'timestamp': spectral_time,
                        'confidence': boosted_conf,
                        'frequency': spectral_event.get('frequency', 0),
                        'amplitude': spectral_event.get('amplitude', 0),
                        'during_speech': panns_event.get('during_speech', False),
                        'detector': 'hybrid_clap_override'
                    })
                else:
                    # Spectral detected clap but PANNs missed it - still trust spectral for claps
                    used_spectral.add(i)
                    spectral_event['detector'] = 'spectral_clap'
                    combined.append(spectral_event)
                continue

        # SECOND PASS: Process remaining PANNs events
        for j, panns_event in enumerate(panns_events):
            if j in used_panns:
                continue

            panns_time = panns_event.get('timestamp', 0)
            panns_type = panns_event.get('type', '').lower()

            # Look for matching spectral event (non-clap)
            matching_spectral = None
            for i, spectral_event in enumerate(spectral_events):
                if i in used_spectral:
                    continue

                spectral_time = spectral_event.get('timestamp', 0)
                spectral_type = spectral_event.get('type', '')

                # Check for match (same type, within 0.3s)
                if spectral_type == panns_type and abs(spectral_time - panns_time) < 0.3:
                    matching_spectral = (i, spectral_event)
                    break

            if matching_spectral:
                # Both detected - boost confidence
                i, spectral_event = matching_spectral
                used_spectral.add(i)

                boosted_confidence = min(1.0,
                    (panns_event.get('confidence', 0) + spectral_event.get('confidence', 0)) / 2 * 1.2)

                combined_event = {
                    'type': panns_type,
                    'timestamp': panns_time,
                    'confidence': boosted_confidence,
                    'frequency': spectral_event.get('frequency', 0),
                    'amplitude': spectral_event.get('amplitude', 0),
                    'during_speech': panns_event.get('during_speech', False),
                    'detector': 'hybrid_both'
                }
                combined.append(combined_event)
            else:
                # Only PANNs detected
                # If it's a potential clap misclassified as animal, skip it
                # (we'll only include if spectral also detected something)
                if panns_type in clap_confusion_types:
                    if self.DEBUG_MODE:
                        print(f"[HYBRID] Skipping PANNs-only '{panns_type}' @ {panns_time:.2f}s "
                              f"(possible clap misclassification, no spectral confirmation)")
                    continue

                panns_event['detector'] = 'panns'
                combined.append(panns_event)

        # Add remaining spectral-only events (non-claps)
        for i, spectral_event in enumerate(spectral_events):
            if i not in used_spectral:
                spectral_event['detector'] = 'spectral'
                combined.append(spectral_event)

        # Sort by timestamp
        combined.sort(key=lambda e: e.get('timestamp', e.get('timestamps', [0])[0]))

        return combined

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to float32 in range [-1, 1]."""
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Normalize amplitude
        max_val = np.abs(audio).max()
        if max_val > 0:
            audio = audio / max_val

        return audio

    def _detect_onsets(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> List[float]:
        """
        Detect onset times (transient events) in audio.

        Uses librosa's onset detection with spectral flux.
        Returns list of onset times in seconds.
        """
        try:
            # Suppress librosa warnings about empty audio
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                # Use smaller hop_length for more sensitive detection
                hop_length = 256  # Was 512 - smaller = more sensitive

                # Compute onset strength envelope
                onset_env = librosa.onset.onset_strength(
                    y=audio,
                    sr=sample_rate,
                    hop_length=hop_length
                )

                # Pick peaks (onset times) with more sensitive settings
                onset_frames = librosa.onset.onset_detect(
                    onset_envelope=onset_env,
                    sr=sample_rate,
                    hop_length=hop_length,
                    backtrack=True,  # Changed to True for better onset alignment
                    units='frames',
                    pre_max=3,       # Look ahead frames
                    post_max=3,      # Look back frames
                    pre_avg=3,       # Average window before
                    post_avg=5,      # Average window after
                    delta=0.05,      # Lower delta = more sensitive (default ~0.07)
                    wait=10          # Minimum frames between onsets (prevent duplicates)
                )

                # Convert frames to times
                onset_times = librosa.frames_to_time(
                    onset_frames,
                    sr=sample_rate,
                    hop_length=hop_length
                )

                return onset_times.tolist()

        except Exception as e:
            print(f"[ENVIRONMENTAL] Onset detection error: {e}")
            return []

    def _classify_onset(
        self,
        audio: np.ndarray,
        sample_rate: int,
        onset_time: float,
        during_speech: bool = False
    ) -> Optional[SoundEvent]:
        """
        Classify a detected onset as a specific sound type.

        IMPROVED: Uses short 50ms window + high-pass filter + spectral centroid + spectral flatness
        to distinguish percussive sounds from both:
        - Sustained background noise (fish tank bubbling, HVAC hum)
        - Speech artifacts (phonemes, consonants, syllable attacks)

        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            onset_time: Time of onset in seconds
            during_speech: Whether this onset occurs during a speech segment (apply stricter filters)

        Returns SoundEvent or None if not classifiable.
        """
        try:
            # Extract SHORT segment for percussive sound analysis
            # Use 50ms window instead of 350ms to avoid background noise contamination
            window_duration = 0.05  # 50ms - captures transient without sustained noise
            start = max(0, int((onset_time - window_duration/2) * sample_rate))
            end = min(len(audio), int((onset_time + window_duration/2) * sample_rate))

            if end - start < int(sample_rate * 0.01):  # Minimum 10ms
                return None

            window = audio[start:end]

            # Calculate amplitude BEFORE filtering
            amplitude = np.abs(window).max()

            # FILTER: Amplitude threshold - require higher amplitude during speech
            min_amplitude = 0.15 if during_speech else 0.05
            if amplitude < min_amplitude:
                return None

            # Apply high-pass filter to remove low-frequency background noise
            try:
                sos = butter(4, 100, 'hp', fs=sample_rate, output='sos')
                window_filtered = sosfilt(sos, window)
            except Exception:
                window_filtered = window

            # Analyze frequency content on FILTERED signal
            fft = np.fft.rfft(window_filtered)
            freqs = np.fft.rfftfreq(len(window_filtered), 1/sample_rate)
            magnitudes = np.abs(fft)

            # Find dominant frequency
            if np.max(magnitudes) > 0:
                dominant_freq = freqs[np.argmax(magnitudes)]
            else:
                return None

            # Calculate spectral centroid
            if np.sum(magnitudes) > 0:
                spectral_centroid = np.sum(freqs * magnitudes) / np.sum(magnitudes)
            else:
                spectral_centroid = 0

            # Calculate spectral flatness (measure of noise vs. tonal content)
            magnitudes_positive = magnitudes + 1e-10  # Avoid log(0)
            geometric_mean = np.exp(np.mean(np.log(magnitudes_positive)))
            arithmetic_mean = np.mean(magnitudes_positive)
            spectral_flatness = geometric_mean / arithmetic_mean if arithmetic_mean > 0 else 0

            # FILTER 1: Spectral flatness during speech (reject harmonic/tonal sounds)
            if during_speech and spectral_flatness < 0.4:
                return None

            # FILTER 2: Reject very high frequencies (electrical interference, aliasing)
            if dominant_freq > 12000:
                return None

            # Calculate decay rate
            decay_rate = self._calculate_decay_rate(window, sample_rate)

            # Estimate duration (time until amplitude drops to 10%)
            duration = self._estimate_duration(window, sample_rate)

            # SPECIAL CASE: Spectral signature detection for claps
            # Physical reality: Claps have low-frequency "thud" (dominant freq 200-700Hz)
            # BUT also high-frequency "snap" revealed by spectral centroid (2000-4000Hz)
            # If flatness is high (noise-like) AND centroid is bright → it's a clap
            clap_pattern = SOUND_PATTERNS.get('clap')
            if (spectral_flatness > 0.5 and
                spectral_centroid > 1600 and
                clap_pattern is not None and
                amplitude >= clap_pattern.min_amplitude):
                return SoundEvent(
                    type='clap',
                    timestamp=onset_time,
                    confidence=0.90,  # High confidence based on spectral characteristics
                    frequency=dominant_freq,
                    amplitude=amplitude,
                    duration=duration,
                    decay_rate=decay_rate
                )

            # Match against patterns with PATTERN-SPECIFIC validation
            best_match = None
            best_score = 0.0

            for pattern_name, pattern in SOUND_PATTERNS.items():
                # PATTERN-SPECIFIC CENTROID CHECK
                centroid_min, centroid_max = pattern.centroid_range
                if not (centroid_min <= spectral_centroid <= centroid_max):
                    continue  # Skip - centroid outside pattern's brightness range

                # PATTERN-SPECIFIC FREQUENCY CHECK
                freq_low, freq_high = pattern.freq_range
                if not (freq_low <= dominant_freq <= freq_high):
                    continue  # Skip - frequency outside pattern's range

                # PATTERN-SPECIFIC AMPLITUDE CHECK (minimum)
                if amplitude < pattern.min_amplitude:
                    continue  # Skip - too quiet for this pattern

                # PATTERN-SPECIFIC AMPLITUDE CHECK (maximum - for quiet sounds like taps)
                if pattern.max_amplitude is not None and amplitude > pattern.max_amplitude:
                    continue  # Skip - too loud for this pattern (e.g., clap detected as tap)

                # All checks passed - calculate score
                score = self._score_pattern_match(
                    pattern, dominant_freq, amplitude, decay_rate, duration
                )
                if score > best_score:
                    best_score = score
                    best_match = pattern_name

            # Use STRICT confidence threshold - max of instance setting or 0.80
            # This prevents false positives from speech consonants and ambient noise
            effective_threshold = max(self.min_confidence, 0.80)

            if best_match and best_score >= effective_threshold:
                return SoundEvent(
                    type=best_match,
                    timestamp=onset_time,
                    confidence=best_score,
                    frequency=dominant_freq,
                    amplitude=amplitude,
                    duration=duration,
                    decay_rate=decay_rate
                )

            return None

        except Exception as e:
            print(f"[ENVIRONMENTAL] Classification error at {onset_time:.2f}s: {e}")
            return None

    def _classify_onset_debug(
        self,
        audio: np.ndarray,
        sample_rate: int,
        onset_time: float,
        during_speech: bool = False
    ) -> Optional[SoundEvent]:
        """
        Classify onset with detailed debug output showing why detections are accepted/rejected.

        IMPROVED: Uses short 50ms window + high-pass filter + spectral centroid + spectral flatness
        to distinguish percussive sounds from both:
        - Sustained background noise (fish tank bubbling, HVAC hum)
        - Speech artifacts (phonemes, consonants, syllable attacks)

        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            onset_time: Time of onset in seconds
            during_speech: Whether this onset occurs during a speech segment (apply stricter filters)
        """
        try:
            # Extract SHORT segment for percussive sound analysis
            # Use 50ms window instead of 350ms to avoid background noise contamination
            # Claps are 10-50ms, so 50ms captures the transient without the sustained noise
            window_duration = 0.05  # 50ms - captures transient without sustained noise
            onset_sample = int(onset_time * sample_rate)
            start = max(0, int((onset_time - window_duration/2) * sample_rate))
            end = min(len(audio), int((onset_time + window_duration/2) * sample_rate))

            if end - start < int(sample_rate * 0.01):  # Minimum 10ms
                if self.DEBUG_MODE:
                    print(f"[ENV DEBUG] Onset @ {onset_time:.2f}s - window too short, skipping")
                return None

            window = audio[start:end]

            # Calculate amplitude BEFORE filtering (to check if signal exists)
            amplitude = np.abs(window).max()

            # FILTER: Global minimum amplitude threshold
            # Filters fish tank bubbles, ambient noise, and weak speech artifacts
            # Higher threshold during speech to filter out phonemes
            min_amplitude = 0.20 if during_speech else 0.10
            if amplitude < min_amplitude:
                self._rejection_stats['low_amplitude'] += 1
                if self.DEBUG_MODE:
                    context = " [DURING SPEECH]" if during_speech else ""
                    print(f"[ENV DEBUG] Onset @ {onset_time:.2f}s{context} - amplitude too low ({amplitude:.3f} < {min_amplitude}) - ambient noise")
                return None

            # Apply high-pass filter to remove low-frequency background noise
            # This removes fish tank bubbling (80Hz), HVAC hum, electrical interference
            # while preserving percussive transients which have energy at higher frequencies
            try:
                sos = butter(4, 100, 'hp', fs=sample_rate, output='sos')
                window_filtered = sosfilt(sos, window)
            except Exception as e:
                if self.DEBUG_MODE:
                    print(f"[ENV DEBUG] Filter failed: {e}, using unfiltered segment")
                window_filtered = window

            # Analyze frequency content on FILTERED signal
            fft = np.fft.rfft(window_filtered)
            freqs = np.fft.rfftfreq(len(window_filtered), 1/sample_rate)
            magnitudes = np.abs(fft)

            # Find dominant frequency
            if np.max(magnitudes) > 0:
                dominant_freq = freqs[np.argmax(magnitudes)]
            else:
                if self.DEBUG_MODE:
                    print(f"[ENV DEBUG] Onset @ {onset_time:.2f}s - no frequency content after filtering")
                return None

            # Calculate spectral centroid (center of mass of spectrum)
            # High centroid = energy at higher frequencies (percussive sounds like claps)
            # Low centroid = energy at lower frequencies (sustained sounds like bubbling)
            if np.sum(magnitudes) > 0:
                spectral_centroid = np.sum(freqs * magnitudes) / np.sum(magnitudes)
            else:
                spectral_centroid = 0

            # Calculate spectral flatness (measure of noise vs. tonal content)
            # High flatness (close to 1.0) = noise-like (percussion, claps, knocks)
            # Low flatness (close to 0.0) = harmonic/tonal (speech, vowels, resonances)
            # Uses geometric mean / arithmetic mean of magnitudes
            magnitudes_positive = magnitudes + 1e-10  # Avoid log(0)
            geometric_mean = np.exp(np.mean(np.log(magnitudes_positive)))
            arithmetic_mean = np.mean(magnitudes_positive)
            spectral_flatness = geometric_mean / arithmetic_mean if arithmetic_mean > 0 else 0

            # Calculate decay rate using the original (unfiltered) window for accurate envelope
            decay_rate = self._calculate_decay_rate(window, sample_rate)

            # Estimate duration
            duration = self._estimate_duration(window, sample_rate)

            if self.DEBUG_MODE:
                context = " [DURING SPEECH]" if during_speech else ""
                print(f"\n[ENV DEBUG] Analyzing onset @ {onset_time:.2f}s{context}:")
                print(f"  Dominant frequency: {dominant_freq:.0f} Hz")
                print(f"  Spectral centroid: {spectral_centroid:.0f} Hz (brightness)")
                print(f"  Spectral flatness: {spectral_flatness:.2f}")
                print(f"  Peak amplitude: {amplitude:.3f}")
                print(f"  Decay rate: {decay_rate:.3f}")
                print(f"  Duration: {duration:.3f}s")

            # FILTER 1: Spectral flatness during speech
            # Speech is harmonic (low flatness ~0.1-0.3)
            # Percussion is noise-like (high flatness ~0.6-0.9)
            if during_speech and spectral_flatness < 0.4:
                self._rejection_stats['speech_artifact'] += 1
                if self.DEBUG_MODE:
                    print(f"  X REJECTED: Low spectral flatness ({spectral_flatness:.2f} < 0.4) - too harmonic, likely speech")
                return None

            # FILTER 2: Reject very high frequencies (electrical interference, aliasing)
            if dominant_freq > 12000:
                self._rejection_stats['high_freq'] += 1
                if self.DEBUG_MODE:
                    print(f"  X REJECTED: Frequency too high ({dominant_freq:.0f}Hz > 12000Hz) - likely interference")
                return None

            # SPECIAL CASE: Spectral signature detection for claps
            # Physical reality: Claps have low-frequency "thud" (dominant freq 200-700Hz)
            # BUT also high-frequency "snap" revealed by spectral centroid (2000-4000Hz)
            # If flatness is high (noise-like) AND centroid is bright → it's a clap
            # regardless of dominant frequency
            clap_pattern = SOUND_PATTERNS.get('clap')
            if (spectral_flatness > 0.5 and
                spectral_centroid > 1600 and
                clap_pattern is not None and
                amplitude >= clap_pattern.min_amplitude):

                if self.DEBUG_MODE:
                    print(f"  [SPECTRAL SIGNATURE MATCH]")
                    print(f"    High flatness ({spectral_flatness:.2f} > 0.5) = noise-like/percussive")
                    print(f"    Bright centroid ({spectral_centroid:.0f}Hz > 1600Hz) = snap energy")
                    print(f"    → Acoustic signature matches clap (thud + snap)")
                    print(f"  >> ACCEPTED: clap with confidence 0.90 (spectral_signature)")

                return SoundEvent(
                    type='clap',
                    timestamp=onset_time,
                    confidence=0.90,  # High confidence based on spectral characteristics
                    frequency=dominant_freq,
                    amplitude=amplitude,
                    duration=duration,
                    decay_rate=decay_rate
                )

            # Match against patterns with PATTERN-SPECIFIC centroid validation
            best_match = None
            best_score = 0.0

            if self.DEBUG_MODE:
                print(f"  Pattern matching:")

            for pattern_name, pattern in SOUND_PATTERNS.items():
                # PATTERN-SPECIFIC CENTROID CHECK
                # Each sound type has a required "brightness" range
                centroid_min, centroid_max = pattern.centroid_range
                if not (centroid_min <= spectral_centroid <= centroid_max):
                    if self.DEBUG_MODE:
                        if spectral_centroid < centroid_min:
                            print(f"    {pattern_name}: SKIP (too dull: centroid {spectral_centroid:.0f}Hz < {centroid_min}Hz)")
                        else:
                            print(f"    {pattern_name}: SKIP (too bright: centroid {spectral_centroid:.0f}Hz > {centroid_max}Hz)")
                    continue  # Skip this pattern, try next one

                # PATTERN-SPECIFIC FREQUENCY CHECK
                freq_low, freq_high = pattern.freq_range
                if not (freq_low <= dominant_freq <= freq_high):
                    if self.DEBUG_MODE:
                        print(f"    {pattern_name}: SKIP (freq {dominant_freq:.0f}Hz not in {pattern.freq_range})")
                    continue  # Skip this pattern

                # PATTERN-SPECIFIC AMPLITUDE CHECK (minimum)
                if amplitude < pattern.min_amplitude:
                    if self.DEBUG_MODE:
                        print(f"    {pattern_name}: SKIP (too quiet: amplitude {amplitude:.2f} < {pattern.min_amplitude})")
                    continue  # Skip this pattern

                # PATTERN-SPECIFIC AMPLITUDE CHECK (maximum - for quiet sounds like taps)
                if pattern.max_amplitude is not None and amplitude > pattern.max_amplitude:
                    if self.DEBUG_MODE:
                        print(f"    {pattern_name}: SKIP (too loud: amplitude {amplitude:.2f} > {pattern.max_amplitude})")
                    continue  # Skip this pattern

                # All checks passed - calculate score
                score = self._score_pattern_match(
                    pattern, dominant_freq, amplitude, decay_rate, duration
                )

                if self.DEBUG_MODE:
                    print(f"    {pattern_name}: score={score:.2f} (freq=OK, centroid=OK, amp=OK)")

                if score > best_score:
                    best_score = score
                    best_match = pattern_name

            # FILTER 3: Confidence threshold
            effective_threshold = max(self.min_confidence, 0.80)

            if best_match and best_score >= effective_threshold:
                if self.DEBUG_MODE:
                    print(f"  >> ACCEPTED: {best_match} with confidence {best_score:.2f} >= {effective_threshold}")
                return SoundEvent(
                    type=best_match,
                    timestamp=onset_time,
                    confidence=best_score,
                    frequency=dominant_freq,
                    amplitude=amplitude,
                    duration=duration,
                    decay_rate=decay_rate
                )
            else:
                self._rejection_stats['low_confidence'] += 1
                if self.DEBUG_MODE:
                    if best_match:
                        print(f"  X REJECTED: {best_match} confidence too low ({best_score:.2f} < {effective_threshold})")
                    else:
                        print(f"  X REJECTED: No pattern matched well enough")
                return None

        except Exception as e:
            print(f"[ENVIRONMENTAL] Classification error at {onset_time:.2f}s: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_decay_rate(
        self,
        window: np.ndarray,
        sample_rate: int
    ) -> float:
        """
        Calculate amplitude decay rate.

        Returns decay rate as fraction of amplitude lost per 10ms.
        Higher = faster decay.
        """
        try:
            # Calculate envelope using Hilbert transform
            analytic_signal = signal.hilbert(window)
            envelope = np.abs(analytic_signal)

            # Smooth envelope
            window_len = int(0.005 * sample_rate)  # 5ms smoothing
            if window_len > 1:
                envelope = np.convolve(
                    envelope,
                    np.ones(window_len) / window_len,
                    mode='same'
                )

            # Find peak
            peak_idx = np.argmax(envelope)
            peak_val = envelope[peak_idx]

            if peak_val < 0.01:
                return 0.0

            # Measure decay over 10ms after peak
            decay_samples = int(0.01 * sample_rate)
            end_idx = min(len(envelope), peak_idx + decay_samples)

            if end_idx > peak_idx:
                end_val = envelope[end_idx]
                decay_rate = 1.0 - (end_val / peak_val)
                return max(0.0, min(1.0, decay_rate))

            return 0.5  # Default

        except Exception:
            return 0.5

    def _estimate_duration(
        self,
        window: np.ndarray,
        sample_rate: int
    ) -> float:
        """
        Estimate sound duration (time until amplitude drops to 10% of peak).
        """
        try:
            envelope = np.abs(window)
            peak_val = envelope.max()
            threshold = peak_val * 0.1

            # Find where envelope drops below threshold
            peak_idx = np.argmax(envelope)
            below_threshold = np.where(envelope[peak_idx:] < threshold)[0]

            if len(below_threshold) > 0:
                duration_samples = below_threshold[0]
                return duration_samples / sample_rate

            return len(window[peak_idx:]) / sample_rate

        except Exception:
            return 0.1  # Default 100ms

    def _score_pattern_match(
        self,
        pattern: SoundPattern,
        frequency: float,
        amplitude: float,
        decay_rate: float,
        duration: float
    ) -> float:
        """
        Score how well observed features match a sound pattern.

        Returns confidence score 0-1.

        FIXED: Changed weights and scoring to not over-penalize edge frequencies
        or short duration percussive sounds like claps.
        """
        score = 0.0
        # Rebalanced weights: freq and amplitude more important, duration less critical
        weights = {'freq': 0.40, 'decay': 0.25, 'amplitude': 0.25, 'duration': 0.10}

        # Frequency match - FIXED to give full credit for being in valid range
        freq_low, freq_high = pattern.freq_range
        if freq_low <= frequency <= freq_high:
            # Full credit for being in valid range
            # Small bonus for being near center (max 10% bonus)
            center_freq = (freq_low + freq_high) / 2
            freq_span = freq_high - freq_low
            distance_from_center = abs(frequency - center_freq)
            # Score is 0.9 at edges, 1.0 at center
            freq_score = 0.9 + 0.1 * (1.0 - distance_from_center / (freq_span / 2))
        elif frequency < freq_low:
            # Below range - penalize by distance
            freq_score = max(0, 1 - (freq_low - frequency) / freq_low)
        else:
            # Above range
            freq_score = max(0, 1 - (frequency - freq_high) / freq_high)
        score += weights['freq'] * freq_score

        # Decay rate match - FIXED with clearer thresholds
        # decay_rate is 0-1 where higher = faster decay (more energy lost quickly)
        if pattern.decay_rate == 'fast':
            # Fast decay: want high decay_rate (> 0.6)
            if decay_rate > 0.6:
                decay_score = 1.0
            elif decay_rate > 0.3:
                decay_score = 0.7  # Medium decay, partial credit
            else:
                decay_score = 0.3  # Slow decay, poor match
        elif pattern.decay_rate == 'slow':
            # Slow decay: want low decay_rate (< 0.3)
            if decay_rate < 0.3:
                decay_score = 1.0
            elif decay_rate < 0.6:
                decay_score = 0.7  # Medium decay, partial credit
            else:
                decay_score = 0.3  # Fast decay, poor match
        else:  # medium
            # Medium decay: want decay_rate between 0.3-0.6
            if 0.3 <= decay_rate <= 0.6:
                decay_score = 1.0
            elif 0.2 <= decay_rate <= 0.7:
                decay_score = 0.8  # Close to medium
            else:
                decay_score = 0.5  # Far from medium
        score += weights['decay'] * decay_score

        # Duration match - FIXED to be more lenient for short percussive sounds
        dur_low, dur_high = pattern.duration_range
        if dur_low <= duration <= dur_high:
            duration_score = 1.0
        elif duration < dur_low:
            # Very short sounds (like quick claps) still get partial credit
            # Instead of penalizing heavily, give 0.7 credit for sounds that are
            # at least half the minimum duration
            if duration >= dur_low * 0.5:
                duration_score = 0.8
            elif duration > 0:
                duration_score = 0.5
            else:
                duration_score = 0.3  # Zero duration, something's off
        else:
            # Too long
            duration_score = max(0.3, 1 - (duration - dur_high) / dur_high)
        score += weights['duration'] * duration_score

        # Amplitude check - FIXED to give graduated score, not binary
        if amplitude >= pattern.min_amplitude:
            # Above threshold, full credit
            # Bonus for louder sounds (up to 1.0 at 2x threshold)
            amp_score = min(1.0, 0.8 + 0.2 * (amplitude / pattern.min_amplitude - 1))
        else:
            # Below threshold - partial credit for being close
            amp_score = max(0, amplitude / pattern.min_amplitude * 0.5)
        score += weights['amplitude'] * amp_score

        return min(1.0, score)

    def _group_events(
        self,
        events: List[SoundEvent]
    ) -> Dict[str, List[SoundEvent]]:
        """
        Group similar events that occur close together.

        E.g., three claps within 2 seconds become one group.
        """
        if not events:
            return {}

        # Sort by timestamp
        events = sorted(events, key=lambda e: e.timestamp)

        # Group by type and temporal proximity
        groups: Dict[str, List[List[SoundEvent]]] = {}

        for event in events:
            if event.type not in groups:
                groups[event.type] = [[event]]
            else:
                # Check if event belongs to last group
                last_group = groups[event.type][-1]
                last_event = last_group[-1]

                if event.timestamp - last_event.timestamp <= self.group_threshold:
                    # Add to existing group
                    last_group.append(event)
                else:
                    # Start new group
                    groups[event.type].append([event])

        return groups

    def _format_output(
        self,
        grouped_events: Dict[str, List[List[SoundEvent]]]
    ) -> List[Dict[str, Any]]:
        """
        Format grouped events for output.

        Returns list of event dictionaries ready for Reed.
        """
        output = []

        for sound_type, groups in grouped_events.items():
            for group in groups:
                if len(group) == 1:
                    # Single event
                    event = group[0]
                    output.append({
                        'type': sound_type,
                        'timestamp': event.timestamp,
                        'confidence': event.confidence,
                        'frequency': event.frequency,
                        'amplitude': event.amplitude
                    })
                else:
                    # Multiple events - count them
                    avg_confidence = sum(e.confidence for e in group) / len(group)
                    timestamps = [e.timestamp for e in group]
                    avg_freq = sum(e.frequency for e in group) / len(group)

                    output.append({
                        'type': sound_type,
                        'count': len(group),
                        'timestamps': timestamps,
                        'confidence': avg_confidence,
                        'frequency': avg_freq
                    })

        # Sort by first timestamp
        output.sort(key=lambda x: x.get('timestamp', x.get('timestamps', [0])[0]))

        return output

    def format_for_display(self, events: List[Dict[str, Any]]) -> str:
        """
        Format events for display in Reed's context.

        Returns string like "clap × 3, knock"
        """
        if not events:
            return ""

        descriptions = []
        for event in events:
            if 'count' in event:
                descriptions.append(f"{event['type']} x{event['count']}")
            else:
                descriptions.append(event['type'])

        return ", ".join(descriptions)

    def format_for_terminal(self, events: List[Dict[str, Any]]) -> List[str]:
        """
        Format events for terminal logging.

        Returns list of log lines.
        """
        lines = []

        for event in events:
            if 'count' in event:
                lines.append(
                    f"[ENVIRONMENTAL] Detected: {event['type']} x{event['count']} "
                    f"[{event['confidence']:.2f} confidence]"
                )
                timestamps = ", ".join([f"{t:.1f}s" for t in event['timestamps']])
                lines.append(f"  -> Timestamps: {timestamps}")
                lines.append(f"  -> Frequency: {event['frequency']:.0f}Hz (avg)")
            else:
                lines.append(
                    f"[ENVIRONMENTAL] Detected: {event['type']} @ {event['timestamp']:.1f}s "
                    f"[{event['confidence']:.2f} confidence]"
                )

        return lines


# Sound icons for UI display
SOUND_ICONS = {
    'clap': '👏',
    'knock': '🚪',
    'door_slam': '🚪💥',
    'footstep': '👣',
    'tap': '👆',
    'unknown': '🔊'
}


def get_sound_icon(sound_type: str) -> str:
    """Get emoji icon for sound type."""
    return SOUND_ICONS.get(sound_type, SOUND_ICONS['unknown'])


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("ENVIRONMENTAL SOUND DETECTOR TEST")
    print("=" * 60)

    detector = EnvironmentalSoundDetector()

    if not detector.enabled:
        print("\nDetector not available - install librosa and scipy:")
        print("  pip install librosa scipy")
    else:
        print("\n[TEST] Creating synthetic clap audio...")

        # Create synthetic clap-like sound
        sample_rate = 16000
        duration = 1.0

        # Generate clap: burst of noise that decays quickly
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Three claps at different times
        claps = np.zeros_like(t)
        clap_times = [0.2, 0.5, 0.8]

        for clap_time in clap_times:
            clap_center = int(clap_time * sample_rate)
            clap_duration = int(0.05 * sample_rate)  # 50ms

            # Noise burst with exponential decay
            for i in range(clap_duration):
                if clap_center + i < len(claps):
                    decay = np.exp(-i / (0.01 * sample_rate))  # Fast decay
                    claps[clap_center + i] = np.random.randn() * 0.5 * decay

        # Band-pass filter to clap frequencies (1-4 kHz)
        from scipy.signal import butter, filtfilt
        b, a = butter(4, [1000, 4000], btype='band', fs=sample_rate)
        claps = filtfilt(b, a, claps)

        # Normalize
        claps = claps / np.abs(claps).max() * 0.8

        print(f"[TEST] Generated {len(clap_times)} synthetic claps")
        print(f"[TEST] Audio length: {duration}s, sample rate: {sample_rate}Hz")

        # Detect sounds
        events = detector.detect_sounds(claps, sample_rate)

        print(f"\n[RESULTS] Detected {len(events)} event(s):")
        for line in detector.format_for_terminal(events):
            print(line)

        if events:
            display = detector.format_for_display(events)
            print(f"\n[DISPLAY] {display}")

            for event in events:
                icon = get_sound_icon(event['type'])
                if 'count' in event:
                    print(f"[UI] {icon} × {event['count']}")
                else:
                    print(f"[UI] {icon}")

    print("\n" + "=" * 60)
    print("Test complete!")
