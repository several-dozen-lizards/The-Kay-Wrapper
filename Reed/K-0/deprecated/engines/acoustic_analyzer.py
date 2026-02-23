"""
Acoustic Feature Analyzer for Reed's Voice System

Extracts prosodic and emotional features from user voice using OpenSMILE's eGeMAPS feature set.
Converts acoustic features into natural language tags that provide emotional context to the LLM.

Architecture:
    User speaks → Audio captured
                ↓
                → Whisper STT → "I'm fine"
                ↓
                → OpenSMILE eGeMAPS → Feature analysis → Interpreter
                ↓
    Combined output: "User [frustrated, speaking quickly, rising pitch, tense voice]: I'm fine"
                ↓
                → LLM processes with full emotional context

Usage:
    analyzer = AcousticAnalyzer()

    # Analyze audio file or numpy array
    tags = analyzer.analyze(audio_data, sample_rate=16000)
    # Returns: ['frustrated', 'speaking quickly', 'rising pitch', 'tense voice']

    # Format for LLM
    formatted = analyzer.format_for_llm(tags, "I'm fine")
    # Returns: "User [frustrated, speaking quickly, rising pitch, tense voice]: I'm fine"
"""

import numpy as np
import json
import os
import time
import tempfile
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Try to import OpenSMILE
OPENSMILE_AVAILABLE = False
try:
    import opensmile
    OPENSMILE_AVAILABLE = True
    print("[ACOUSTIC] OpenSMILE available")
except ImportError:
    print("[ACOUSTIC] Warning: opensmile not installed. Run: pip install opensmile")

# Try to import scipy for audio file handling
try:
    from scipy.io.wavfile import write as write_wav, read as read_wav
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[ACOUSTIC] Warning: scipy not installed for WAV handling")


@dataclass
class AcousticFeatures:
    """Container for extracted acoustic features with interpretations."""

    # Raw feature values
    f0_mean: float = 0.0           # Mean fundamental frequency (Hz)
    f0_std: float = 0.0            # F0 standard deviation
    f0_range: float = 0.0          # F0 range (max - min)
    f0_slope: float = 0.0          # Overall pitch contour slope

    loudness_mean: float = 0.0     # Mean loudness (dB)
    loudness_std: float = 0.0      # Loudness variation
    loudness_range: float = 0.0    # Dynamic range

    speaking_rate: float = 0.0     # Estimated syllables per second

    jitter: float = 0.0            # Pitch stability (higher = more unstable)
    shimmer: float = 0.0           # Amplitude stability (higher = more unstable)
    hnr: float = 0.0               # Harmonics-to-noise ratio (voice clarity)

    spectral_flux: float = 0.0     # How quickly the spectrum changes

    # Analysis metadata
    duration: float = 0.0          # Audio duration in seconds
    timestamp: str = ""            # When analyzed
    confidence: float = 1.0        # Overall confidence in analysis

    # Interpretation results
    tags: List[str] = field(default_factory=list)
    emotional_valence: float = 0.0  # -1 (negative) to 1 (positive)
    arousal: float = 0.0            # 0 (calm) to 1 (excited/agitated)


@dataclass
class BaselineProfile:
    """User's baseline acoustic profile for personalized analysis."""

    # Pitch baseline
    f0_mean_baseline: float = 150.0      # Average speaker is ~150Hz
    f0_std_baseline: float = 30.0

    # Loudness baseline
    loudness_mean_baseline: float = 50.0
    loudness_std_baseline: float = 10.0

    # Speaking rate baseline
    speaking_rate_baseline: float = 4.0  # ~4 syllables/second is average

    # Voice quality baseline
    jitter_baseline: float = 0.02        # ~2% is normal
    shimmer_baseline: float = 0.03       # ~3% is normal
    hnr_baseline: float = 15.0           # ~15dB is normal

    # Calibration metadata
    utterance_count: int = 0
    last_updated: str = ""

    # Running totals for incremental updates
    f0_sum: float = 0.0
    f0_count: int = 0
    loudness_sum: float = 0.0
    loudness_count: int = 0
    rate_sum: float = 0.0
    rate_count: int = 0
    jitter_sum: float = 0.0
    shimmer_sum: float = 0.0
    hnr_sum: float = 0.0
    quality_count: int = 0


class AcousticAnalyzer:
    """
    Extracts and interprets acoustic features from voice audio.

    Uses OpenSMILE's eGeMAPS feature set (88 features) for prosodic/emotional analysis.
    Converts numeric features into natural language tags for LLM context.
    """

    def __init__(
        self,
        baseline_file: str = "memory/acoustic_baseline.json",
        enabled: bool = True,
        calibration_utterances: int = 15
    ):
        """
        Initialize acoustic analyzer.

        Args:
            baseline_file: Path to save/load user baseline profile
            enabled: Whether acoustic analysis is active
            calibration_utterances: Number of utterances for baseline calibration
        """
        self.enabled = enabled and OPENSMILE_AVAILABLE
        self.baseline_file = Path(baseline_file)
        self.calibration_utterances = calibration_utterances

        # OpenSMILE extractor
        self.smile = None
        if OPENSMILE_AVAILABLE and self.enabled:
            try:
                # Use eGeMAPS feature set (88 features, balanced speed/accuracy)
                self.smile = opensmile.Smile(
                    feature_set=opensmile.FeatureSet.eGeMAPSv02,
                    feature_level=opensmile.FeatureLevel.Functionals
                )
                print(f"[ACOUSTIC] Loaded eGeMAPS v02 feature extractor")
            except Exception as e:
                print(f"[ACOUSTIC] Error loading OpenSMILE: {e}")
                self.enabled = False

        # Baseline profile
        self.baseline = BaselineProfile()
        self._load_baseline()

        # Temp directory for audio processing
        self.temp_dir = Path(tempfile.gettempdir()) / "kay_acoustic"
        self.temp_dir.mkdir(exist_ok=True)

        # Thread safety
        self._lock = threading.Lock()

        # Feature name mappings from eGeMAPS
        self._feature_map = {
            # Pitch features
            'F0semitoneFrom27.5Hz_sma3nz_amean': 'f0_mean',
            'F0semitoneFrom27.5Hz_sma3nz_stddevNorm': 'f0_std',
            'F0semitoneFrom27.5Hz_sma3nz_pctlrange0-2': 'f0_range',

            # Loudness features
            'loudness_sma3_amean': 'loudness_mean',
            'loudness_sma3_stddevNorm': 'loudness_std',
            'loudness_sma3_pctlrange0-2': 'loudness_range',

            # Voice quality
            'jitterLocal_sma3nz_amean': 'jitter',
            'shimmerLocaldB_sma3nz_amean': 'shimmer',
            'HNRdBACF_sma3nz_amean': 'hnr',

            # Spectral features
            'spectralFlux_sma3_amean': 'spectral_flux',
        }

        print(f"[ACOUSTIC] Analyzer initialized (enabled={self.enabled})")

    def _load_baseline(self):
        """Load baseline profile from disk."""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    self.baseline = BaselineProfile(**data)
                    print(f"[ACOUSTIC] Loaded baseline from {self.baseline_file} "
                          f"({self.baseline.utterance_count} utterances)")
        except Exception as e:
            print(f"[ACOUSTIC] Error loading baseline: {e}")
            self.baseline = BaselineProfile()

    def _save_baseline(self):
        """Save baseline profile to disk."""
        try:
            self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_file, 'w') as f:
                # Convert dataclass to dict
                data = {
                    'f0_mean_baseline': self.baseline.f0_mean_baseline,
                    'f0_std_baseline': self.baseline.f0_std_baseline,
                    'loudness_mean_baseline': self.baseline.loudness_mean_baseline,
                    'loudness_std_baseline': self.baseline.loudness_std_baseline,
                    'speaking_rate_baseline': self.baseline.speaking_rate_baseline,
                    'jitter_baseline': self.baseline.jitter_baseline,
                    'shimmer_baseline': self.baseline.shimmer_baseline,
                    'hnr_baseline': self.baseline.hnr_baseline,
                    'utterance_count': self.baseline.utterance_count,
                    'last_updated': self.baseline.last_updated,
                    'f0_sum': self.baseline.f0_sum,
                    'f0_count': self.baseline.f0_count,
                    'loudness_sum': self.baseline.loudness_sum,
                    'loudness_count': self.baseline.loudness_count,
                    'rate_sum': self.baseline.rate_sum,
                    'rate_count': self.baseline.rate_count,
                    'jitter_sum': self.baseline.jitter_sum,
                    'shimmer_sum': self.baseline.shimmer_sum,
                    'hnr_sum': self.baseline.hnr_sum,
                    'quality_count': self.baseline.quality_count,
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ACOUSTIC] Error saving baseline: {e}")

    def _update_baseline(self, features: AcousticFeatures):
        """
        Update baseline profile with new utterance features.

        Uses incremental averaging to build personalized baseline.
        """
        with self._lock:
            # Update pitch baseline
            if features.f0_mean > 0:
                self.baseline.f0_sum += features.f0_mean
                self.baseline.f0_count += 1
                self.baseline.f0_mean_baseline = self.baseline.f0_sum / self.baseline.f0_count

                if features.f0_std > 0:
                    # Simple exponential moving average for std
                    alpha = 0.1
                    self.baseline.f0_std_baseline = (
                        alpha * features.f0_std +
                        (1 - alpha) * self.baseline.f0_std_baseline
                    )

            # Update loudness baseline
            if features.loudness_mean > 0:
                self.baseline.loudness_sum += features.loudness_mean
                self.baseline.loudness_count += 1
                self.baseline.loudness_mean_baseline = (
                    self.baseline.loudness_sum / self.baseline.loudness_count
                )

            # Update speaking rate baseline
            if features.speaking_rate > 0:
                self.baseline.rate_sum += features.speaking_rate
                self.baseline.rate_count += 1
                self.baseline.speaking_rate_baseline = (
                    self.baseline.rate_sum / self.baseline.rate_count
                )

            # Update voice quality baselines
            if features.jitter > 0 and features.shimmer > 0:
                self.baseline.jitter_sum += features.jitter
                self.baseline.shimmer_sum += features.shimmer
                self.baseline.hnr_sum += features.hnr
                self.baseline.quality_count += 1

                self.baseline.jitter_baseline = (
                    self.baseline.jitter_sum / self.baseline.quality_count
                )
                self.baseline.shimmer_baseline = (
                    self.baseline.shimmer_sum / self.baseline.quality_count
                )
                self.baseline.hnr_baseline = (
                    self.baseline.hnr_sum / self.baseline.quality_count
                )

            # Update metadata
            self.baseline.utterance_count += 1
            self.baseline.last_updated = datetime.now().isoformat()

            # Save periodically (every 5 utterances)
            if self.baseline.utterance_count % 5 == 0:
                self._save_baseline()
                print(f"[ACOUSTIC] Baseline updated ({self.baseline.utterance_count} utterances)")

    def _extract_raw_features(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> Optional[Dict[str, float]]:
        """
        Extract raw acoustic features using OpenSMILE.

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate of audio

        Returns:
            Dictionary of feature names to values, or None if failed
        """
        if not self.smile:
            return None

        try:
            # Ensure audio is float32 and normalized
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Ensure mono
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)

            # MEMORY SAFETY: Limit audio length to prevent memory explosion
            # OpenSMILE's eGeMAPS creates correlation matrices that scale O(n^2)
            # For safety, limit to 30 seconds max (480,000 samples at 16kHz)
            MAX_SAMPLES = 30 * sample_rate  # 30 seconds
            if len(audio) > MAX_SAMPLES:
                print(f"[ACOUSTIC] Audio too long ({len(audio)/sample_rate:.1f}s), truncating to 30s for memory safety")
                audio = audio[:MAX_SAMPLES]

            # MEMORY SAFETY: Check estimated memory requirement
            # eGeMAPS worst case: ~88 features with slope calculations
            # Correlation matrix could be samples x features
            estimated_memory_mb = (len(audio) * 88 * 8) / (1024 * 1024)  # 8 bytes per float64
            if estimated_memory_mb > 500:  # More than 500MB estimated
                print(f"[ACOUSTIC] Estimated memory ({estimated_memory_mb:.0f}MB) too high, downsampling")
                # Downsample by factor of 2
                audio = audio[::2]

            # Extract features
            features_df = self.smile.process_signal(audio, sample_rate)

            # Convert to dict
            if len(features_df) > 0:
                return features_df.iloc[0].to_dict()

            return None

        except MemoryError as e:
            print(f"[ACOUSTIC] Memory allocation failed - audio too long or complex: {e}")
            return None
        except Exception as e:
            error_msg = str(e)
            # Check for numpy allocation errors
            if "Unable to allocate" in error_msg or "memory" in error_msg.lower():
                print(f"[ACOUSTIC] Memory allocation error (OpenSMILE bug with long audio): {e}")
                print("[ACOUSTIC] Skipping acoustic analysis for this utterance")
            else:
                print(f"[ACOUSTIC] Feature extraction error: {e}")
            return None

    def _estimate_speaking_rate(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> float:
        """
        Estimate speaking rate from audio energy patterns.

        Uses simple syllable nuclei detection based on energy peaks.
        Returns estimated syllables per second.
        """
        try:
            # Convert to float if needed
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0

            # Calculate short-time energy
            frame_size = int(0.025 * sample_rate)  # 25ms frames
            hop_size = int(0.010 * sample_rate)    # 10ms hop

            energy = []
            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i:i + frame_size]
                energy.append(np.sum(frame ** 2))

            if not energy:
                return 0.0

            energy = np.array(energy)

            # Normalize energy
            energy = (energy - energy.min()) / (energy.max() - energy.min() + 1e-10)

            # Find peaks (potential syllable nuclei)
            threshold = 0.3  # Energy threshold for peak detection
            peaks = []
            for i in range(1, len(energy) - 1):
                if energy[i] > threshold and energy[i] > energy[i-1] and energy[i] > energy[i+1]:
                    peaks.append(i)

            # Calculate speaking rate
            duration = len(audio) / sample_rate
            if duration > 0:
                syllable_rate = len(peaks) / duration
                return syllable_rate

            return 0.0

        except Exception as e:
            print(f"[ACOUSTIC] Speaking rate estimation error: {e}")
            return 0.0

    def _estimate_pitch_slope(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> float:
        """
        Estimate overall pitch contour slope.

        Positive = rising pitch (questioning, uncertain)
        Negative = falling pitch (assertive, finishing)
        Near zero = flat

        MEMORY-SAFE: Uses windowed analysis to avoid large FFT allocations.
        """
        try:
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0

            # MEMORY SAFETY: Limit sample size for FFT operations
            # Large FFTs can cause memory issues - limit to 2 seconds of audio
            MAX_SAMPLES_FOR_FFT = 2 * sample_rate
            if len(audio) > MAX_SAMPLES_FOR_FFT:
                # Take first and last second instead of halves
                first_half = audio[:sample_rate]
                second_half = audio[-sample_rate:]
            else:
                # Split into first and second half
                mid = len(audio) // 2
                first_half = audio[:mid]
                second_half = audio[mid:]

            # MEMORY SAFETY: Use smaller FFT window if needed
            MAX_FFT_SIZE = 8192  # Safe FFT size
            if len(first_half) > MAX_FFT_SIZE:
                first_half = first_half[:MAX_FFT_SIZE]
            if len(second_half) > MAX_FFT_SIZE:
                second_half = second_half[:MAX_FFT_SIZE]

            # Calculate spectral centroid for each half
            def spectral_centroid(signal):
                fft = np.fft.rfft(signal)
                magnitude = np.abs(fft)
                freqs = np.fft.rfftfreq(len(signal), 1/sample_rate)
                if np.sum(magnitude) > 0:
                    return np.sum(freqs * magnitude) / np.sum(magnitude)
                return 0

            centroid_first = spectral_centroid(first_half)
            centroid_second = spectral_centroid(second_half)

            # Normalize slope to -1 to 1 range
            if centroid_first > 0:
                slope = (centroid_second - centroid_first) / centroid_first
                return np.clip(slope, -1, 1)

            return 0.0

        except MemoryError:
            print(f"[ACOUSTIC] Pitch slope estimation: memory error, skipping")
            return 0.0
        except Exception as e:
            error_msg = str(e)
            if "Unable to allocate" in error_msg or "memory" in error_msg.lower():
                print(f"[ACOUSTIC] Pitch slope estimation: memory allocation failed, skipping")
            else:
                print(f"[ACOUSTIC] Pitch slope estimation error: {e}")
            return 0.0

    def analyze(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        update_baseline: bool = True
    ) -> AcousticFeatures:
        """
        Analyze audio and extract acoustic features.

        Args:
            audio: Audio data as numpy array (int16 or float32)
            sample_rate: Sample rate of audio
            update_baseline: Whether to update baseline profile

        Returns:
            AcousticFeatures object with extracted features and interpretation tags
        """
        features = AcousticFeatures()
        features.timestamp = datetime.now().isoformat()
        features.duration = len(audio) / sample_rate

        if not self.enabled:
            features.confidence = 0.0
            return features

        # Minimum audio length check (0.5 seconds)
        if features.duration < 0.5:
            print(f"[ACOUSTIC] Audio too short ({features.duration:.2f}s), skipping analysis")
            features.confidence = 0.0
            return features

        # MEMORY SAFETY: Maximum audio length check (60 seconds)
        # OpenSMILE can crash with very long audio due to O(n^2) correlation matrices
        MAX_DURATION = 60.0  # seconds
        if features.duration > MAX_DURATION:
            print(f"[ACOUSTIC] Audio too long ({features.duration:.1f}s), limiting to {MAX_DURATION}s for memory safety")
            max_samples = int(MAX_DURATION * sample_rate)
            audio = audio[:max_samples]
            features.duration = MAX_DURATION

        try:
            # Extract raw features using OpenSMILE
            raw_features = self._extract_raw_features(audio, sample_rate)

            if raw_features:
                # Map OpenSMILE features to our feature names
                for opensmile_name, our_name in self._feature_map.items():
                    if opensmile_name in raw_features:
                        value = raw_features[opensmile_name]
                        if not np.isnan(value):
                            setattr(features, our_name, float(value))

            # Additional feature estimation
            features.speaking_rate = self._estimate_speaking_rate(audio, sample_rate)
            features.f0_slope = self._estimate_pitch_slope(audio, sample_rate)

            # Update baseline if in calibration phase
            if update_baseline:
                self._update_baseline(features)

            # Interpret features into natural language tags
            features.tags = self._interpret_features(features)

            # Calculate emotional dimensions
            features.arousal, features.emotional_valence = self._calculate_emotion_dimensions(features)

        except MemoryError:
            print(f"[ACOUSTIC] Memory error during analysis - skipping this utterance")
            features.confidence = 0.0
        except Exception as e:
            error_msg = str(e)
            if "Unable to allocate" in error_msg or "memory" in error_msg.lower() or "mkl_malloc" in error_msg.lower():
                print(f"[ACOUSTIC] Memory allocation failed during analysis - skipping")
                features.confidence = 0.0
            else:
                print(f"[ACOUSTIC] Analysis error: {e}")
                features.confidence = 0.5  # Partial confidence

        return features

    def analyze_file(
        self,
        audio_path: str,
        update_baseline: bool = True
    ) -> AcousticFeatures:
        """
        Analyze audio from file.

        Args:
            audio_path: Path to audio file (WAV format)
            update_baseline: Whether to update baseline profile

        Returns:
            AcousticFeatures object
        """
        if not SCIPY_AVAILABLE:
            return AcousticFeatures()

        try:
            sample_rate, audio = read_wav(audio_path)
            return self.analyze(audio, sample_rate, update_baseline)
        except Exception as e:
            print(f"[ACOUSTIC] Error reading audio file: {e}")
            return AcousticFeatures()

    def _interpret_features(self, features: AcousticFeatures) -> List[str]:
        """
        Convert numeric features into natural language tags.

        Uses baseline comparison for personalized interpretation.
        """
        tags = []
        baseline = self.baseline

        # Only interpret if we have valid features
        if features.confidence == 0.0:
            return tags

        # === PITCH VARIANCE (agitation/excitement vs flat affect) ===
        if features.f0_std > 0:
            f0_ratio = features.f0_std / max(baseline.f0_std_baseline, 1)

            if f0_ratio > 1.5:
                # High pitch variance
                if features.arousal > 0.5:
                    tags.append("excited")
                else:
                    tags.append("agitated")
            elif f0_ratio < 0.5:
                tags.append("flat affect")

        # === SPEAKING RATE ===
        if features.speaking_rate > 0 and baseline.speaking_rate_baseline > 0:
            rate_ratio = features.speaking_rate / baseline.speaking_rate_baseline

            if rate_ratio > 1.3:
                tags.append("speaking quickly")
            elif rate_ratio < 0.7:
                tags.append("speaking slowly")

        # === LOUDNESS ===
        if features.loudness_mean > 0 and baseline.loudness_mean_baseline > 0:
            loudness_ratio = features.loudness_mean / baseline.loudness_mean_baseline

            if loudness_ratio > 1.4:
                if features.loudness_std > baseline.loudness_std_baseline * 1.5:
                    tags.append("emphatic")
                else:
                    tags.append("loud")
            elif loudness_ratio < 0.6:
                tags.append("quiet")

        # === VOICE QUALITY (tension/fatigue) ===
        if features.jitter > 0:
            jitter_ratio = features.jitter / max(baseline.jitter_baseline, 0.01)

            if jitter_ratio > 1.8:
                tags.append("tense voice")

        if features.shimmer > 0:
            shimmer_ratio = features.shimmer / max(baseline.shimmer_baseline, 0.01)

            if shimmer_ratio > 2.0:
                if features.loudness_mean < baseline.loudness_mean_baseline:
                    tags.append("tired")
                else:
                    tags.append("breathy")

        # === PITCH CONTOUR (questioning vs assertive) ===
        if abs(features.f0_slope) > 0.1:
            if features.f0_slope > 0.3:
                tags.append("rising pitch")
            elif features.f0_slope < -0.3:
                tags.append("falling pitch")

        # === COMBINED PATTERNS (emotional states) ===
        # Frustration: high jitter + fast rate + high variance
        if (features.jitter > baseline.jitter_baseline * 1.3 and
            features.speaking_rate > baseline.speaking_rate_baseline * 1.2 and
            features.f0_std > baseline.f0_std_baseline * 1.2):
            if "tense voice" not in tags:
                tags.append("frustrated")

        # Sadness: slow rate + quiet + low pitch
        if (features.speaking_rate < baseline.speaking_rate_baseline * 0.8 and
            features.loudness_mean < baseline.loudness_mean_baseline * 0.7):
            if "tired" not in tags and "quiet" not in tags:
                tags.append("subdued")

        # Enthusiasm: fast rate + loud + high variance
        if (features.speaking_rate > baseline.speaking_rate_baseline * 1.2 and
            features.loudness_mean > baseline.loudness_mean_baseline * 1.2 and
            features.f0_std > baseline.f0_std_baseline * 1.3):
            if "excited" not in tags:
                tags.append("enthusiastic")

        # Uncertainty: many pauses + rising pitch + moderate jitter
        if features.f0_slope > 0.2 and features.speaking_rate < baseline.speaking_rate_baseline:
            tags.append("uncertain")

        # Confidence: falling pitch + steady rate + clear voice
        if (features.f0_slope < -0.2 and
            abs(features.speaking_rate - baseline.speaking_rate_baseline) < baseline.speaking_rate_baseline * 0.2 and
            features.hnr > baseline.hnr_baseline):
            tags.append("confident")

        return tags

    def _calculate_emotion_dimensions(
        self,
        features: AcousticFeatures
    ) -> Tuple[float, float]:
        """
        Calculate arousal and valence from acoustic features.

        Returns:
            Tuple of (arousal, valence) where:
            - arousal: 0 (calm) to 1 (excited/agitated)
            - valence: -1 (negative) to 1 (positive)
        """
        baseline = self.baseline

        # === AROUSAL ===
        # High arousal indicators: fast speech, loud, high pitch variance, high jitter
        arousal_factors = []

        if features.speaking_rate > 0 and baseline.speaking_rate_baseline > 0:
            rate_factor = (features.speaking_rate / baseline.speaking_rate_baseline - 1) * 0.5
            arousal_factors.append(np.clip(rate_factor, -0.5, 0.5))

        if features.loudness_mean > 0 and baseline.loudness_mean_baseline > 0:
            loudness_factor = (features.loudness_mean / baseline.loudness_mean_baseline - 1) * 0.3
            arousal_factors.append(np.clip(loudness_factor, -0.3, 0.3))

        if features.f0_std > 0 and baseline.f0_std_baseline > 0:
            variance_factor = (features.f0_std / baseline.f0_std_baseline - 1) * 0.4
            arousal_factors.append(np.clip(variance_factor, -0.4, 0.4))

        if features.jitter > 0 and baseline.jitter_baseline > 0:
            jitter_factor = (features.jitter / baseline.jitter_baseline - 1) * 0.2
            arousal_factors.append(np.clip(jitter_factor, -0.2, 0.3))

        arousal = 0.5 + sum(arousal_factors)  # Base at 0.5
        arousal = np.clip(arousal, 0, 1)

        # === VALENCE ===
        # Harder to determine from acoustics alone
        # Higher HNR and moderate arousal tend to be more positive
        # High jitter and shimmer with low HNR tend to be negative
        valence_factors = []

        if features.hnr > 0 and baseline.hnr_baseline > 0:
            hnr_factor = (features.hnr / baseline.hnr_baseline - 1) * 0.3
            valence_factors.append(np.clip(hnr_factor, -0.3, 0.3))

        # Falling pitch is often more positive (confident, assertive)
        if features.f0_slope < -0.2:
            valence_factors.append(0.2)
        elif features.f0_slope > 0.3:
            valence_factors.append(-0.1)  # Rising pitch can indicate uncertainty

        # Very high jitter and shimmer indicate distress (negative)
        if features.jitter > baseline.jitter_baseline * 2:
            valence_factors.append(-0.3)
        if features.shimmer > baseline.shimmer_baseline * 2:
            valence_factors.append(-0.2)

        valence = sum(valence_factors)
        valence = np.clip(valence, -1, 1)

        return arousal, valence

    def format_for_llm(
        self,
        tags: List[str],
        transcription: str,
        include_empty: bool = False
    ) -> str:
        """
        Format acoustic tags with transcription for LLM context.

        Args:
            tags: List of acoustic interpretation tags
            transcription: The transcribed text
            include_empty: Whether to include brackets even if no tags

        Returns:
            Formatted string like "User [frustrated, rising pitch]: I'm fine"
        """
        transcription = transcription.strip()

        if not tags:
            if include_empty:
                return f"User [neutral tone]: {transcription}"
            return f"User: {transcription}"

        # Sort tags for consistency (emotional states first, then descriptive)
        emotional_states = ['frustrated', 'excited', 'enthusiastic', 'uncertain',
                          'confident', 'subdued', 'tired']
        descriptive = ['speaking quickly', 'speaking slowly', 'loud', 'quiet',
                      'emphatic', 'rising pitch', 'falling pitch', 'tense voice',
                      'breathy', 'flat affect', 'agitated']

        sorted_tags = []
        for tag in emotional_states:
            if tag in tags:
                sorted_tags.append(tag)
        for tag in descriptive:
            if tag in tags:
                sorted_tags.append(tag)

        # Add any remaining tags not in our predefined lists
        for tag in tags:
            if tag not in sorted_tags:
                sorted_tags.append(tag)

        tag_string = ", ".join(sorted_tags)
        return f"User [{tag_string}]: {transcription}"

    def get_baseline_status(self) -> Dict[str, Any]:
        """
        Get current baseline calibration status.

        Returns:
            Dict with baseline info and calibration progress
        """
        progress = min(
            self.baseline.utterance_count / self.calibration_utterances * 100,
            100
        )

        return {
            'calibrated': self.baseline.utterance_count >= self.calibration_utterances,
            'progress_percent': progress,
            'utterance_count': self.baseline.utterance_count,
            'target_utterances': self.calibration_utterances,
            'last_updated': self.baseline.last_updated,
            'baseline_values': {
                'f0_mean': self.baseline.f0_mean_baseline,
                'loudness_mean': self.baseline.loudness_mean_baseline,
                'speaking_rate': self.baseline.speaking_rate_baseline,
                'jitter': self.baseline.jitter_baseline,
                'shimmer': self.baseline.shimmer_baseline,
                'hnr': self.baseline.hnr_baseline,
            }
        }

    def reset_baseline(self):
        """Reset baseline to defaults (for new user or recalibration)."""
        self.baseline = BaselineProfile()
        self._save_baseline()
        print("[ACOUSTIC] Baseline reset to defaults")


# Async wrapper for parallel processing
class AsyncAcousticAnalyzer:
    """
    Async wrapper for acoustic analysis that can run in parallel with Whisper.

    Usage:
        async_analyzer = AsyncAcousticAnalyzer(analyzer)

        # Start analysis in background
        future = async_analyzer.analyze_async(audio_data, sample_rate)

        # Do other work (e.g., Whisper transcription)
        transcription = whisper.transcribe(audio)

        # Get analysis results
        features = future.result(timeout=2.0)
        tags = features.tags
    """

    def __init__(self, analyzer: AcousticAnalyzer):
        self.analyzer = analyzer
        self._executor = None

    def analyze_async(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        update_baseline: bool = True
    ):
        """
        Start acoustic analysis in background thread.

        Returns:
            concurrent.futures.Future that will contain AcousticFeatures
        """
        from concurrent.futures import ThreadPoolExecutor

        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="acoustic")

        return self._executor.submit(
            self.analyzer.analyze,
            audio,
            sample_rate,
            update_baseline
        )

    def shutdown(self):
        """Shutdown the thread pool."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("ACOUSTIC ANALYZER TEST")
    print("=" * 60)

    analyzer = AcousticAnalyzer()

    # Check status
    status = analyzer.get_baseline_status()
    print(f"\nBaseline status: {json.dumps(status, indent=2)}")

    if not OPENSMILE_AVAILABLE:
        print("\nOpenSMILE not available - install with: pip install opensmile")
        print("Test cannot continue without OpenSMILE")
    else:
        print("\n[TEST] OpenSMILE is available and ready for acoustic analysis")

        # Create synthetic test audio (1 second of sine wave)
        sample_rate = 16000
        duration = 2.0
        frequency = 200  # Hz

        t = np.linspace(0, duration, int(sample_rate * duration))
        # Add some variation to simulate speech
        audio = np.sin(2 * np.pi * frequency * t) * 0.5
        audio += np.sin(2 * np.pi * frequency * 1.5 * t) * 0.3
        audio = (audio * 32767).astype(np.int16)

        print(f"\n[TEST] Analyzing synthetic audio ({duration}s, {sample_rate}Hz)")

        features = analyzer.analyze(audio, sample_rate)

        print(f"\nExtracted features:")
        print(f"  F0 mean: {features.f0_mean:.2f}")
        print(f"  F0 std: {features.f0_std:.2f}")
        print(f"  Loudness mean: {features.loudness_mean:.2f}")
        print(f"  Speaking rate: {features.speaking_rate:.2f} syl/s")
        print(f"  Jitter: {features.jitter:.4f}")
        print(f"  Shimmer: {features.shimmer:.4f}")
        print(f"  HNR: {features.hnr:.2f} dB")
        print(f"  F0 slope: {features.f0_slope:.3f}")

        print(f"\nInterpretation tags: {features.tags}")
        print(f"Arousal: {features.arousal:.2f}")
        print(f"Valence: {features.emotional_valence:.2f}")

        # Test formatting
        formatted = analyzer.format_for_llm(features.tags, "This is a test.")
        print(f"\nFormatted for LLM: {formatted}")

    print("\n" + "=" * 60)
    print("Test complete!")
