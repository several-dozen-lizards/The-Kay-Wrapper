"""
PANNs Audio Classifier for Kay Zero

Uses Pre-trained Audio Neural Networks (PANNs) for robust audio event classification.
Replaces hand-tuned amplitude/spectral detection with neural network inference.

PANNs Architecture Overview:
- Trained on AudioSet (2 million 10-second clips, 527 event classes)
- CNN14 model: 14-layer CNN with ~80M parameters
- Input: 32kHz audio → mel spectrogram (64 mel bins, 10ms hop)
- Output: 527 class probabilities (sigmoid, multi-label)

Key AudioSet classes for environmental detection:
- Clapping (ID 57): "Clap"
- Finger snapping (ID 58): "Finger snapping"
- Knock (ID 73): "Knock"
- Door slam (ID 75): "Door slam"
- Footsteps (ID 78): "Footsteps"
- Tap (ID 74): "Tap"

Usage:
    classifier = PANNsClassifier()
    result = classifier.classify(audio_waveform, sample_rate=16000)
    # Returns: {
    #     'event_type': 'Clapping',
    #     'confidence': 0.87,
    #     'alternatives': [('Finger snapping', 0.12), ...],
    #     'timestamp': datetime
    # }

References:
- PANNs paper: https://arxiv.org/abs/1912.10211
- AudioSet ontology: https://research.google.com/audioset/ontology/index.html
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import warnings

# Suppress librosa warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Check for required dependencies
TORCH_AVAILABLE = False
PANNS_AVAILABLE = False
LIBROSA_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    print("[PANNS] Warning: PyTorch not installed. Run: pip install torch")

try:
    from panns_inference import AudioTagging
    PANNS_AVAILABLE = True
except ImportError:
    print("[PANNS] Warning: panns_inference not installed. Run: pip install panns-inference")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    print("[PANNS] Warning: librosa not installed. Run: pip install librosa")


@dataclass
class AudioEvent:
    """Classified audio event from PANNs."""
    event_type: str           # Top classification label
    confidence: float         # Confidence score (0-1)
    alternatives: List[Tuple[str, float]]  # Alternative classifications
    timestamp: datetime       # When this was detected
    audio_duration: float     # Duration of analyzed audio (seconds)
    all_scores: Optional[Dict[str, float]] = None  # Full score dict (debugging)


# AudioSet class labels we care about for environmental detection
# Format: class_index -> (display_label, our_category)
# Full list: https://github.com/qiuqiangkong/audioset_tagging_cnn/blob/master/metadata/class_labels_indices.csv
#
# Verified against class_labels_indices.csv - these are the ACTUAL indices
ENVIRONMENTAL_CLASSES = {
    # Percussive/Impact sounds (what Kay should notice)
    61: ("Hands", "hands"),
    62: ("Finger snapping", "snap"),
    63: ("Clapping", "clap"),

    # Door/knock sounds
    354: ("Door", "door"),
    355: ("Doorbell", "doorbell"),
    357: ("Sliding door", "door"),
    359: ("Knock", "knock"),
    360: ("Tap", "tap"),

    # Footsteps/movement
    51: ("Run", "footsteps"),
    53: ("Walk, footsteps", "footsteps"),

    # Impact sounds
    460: ("Thump, thud", "thud"),

    # Things to filter out (but track for context)
    0: ("Speech", "speech"),
    1: ("Male speech", "speech"),
    2: ("Female speech", "speech"),
    3: ("Child speech", "speech"),
    7: ("Speech synthesizer", "speech"),
    70: ("Hubbub, speech noise", "speech"),

    137: ("Music", "music"),
    138: ("Musical instrument", "music"),
}

# Classes we actively want to detect and report
TARGET_CATEGORIES = {
    "clap", "snap", "knock", "tap", "thud",
    "door", "door_slam", "doorbell", "footsteps",
    "alarm", "phone"
}

# Classes to ignore (don't report even if high confidence)
IGNORE_CATEGORIES = {"speech", "music"}


class PANNsClassifier:
    """
    Audio event classifier using PANNs (Pre-trained Audio Neural Networks).

    This wraps the panns_inference library to provide a simple interface
    for classifying audio chunks into environmental sound events.

    The model runs on CPU by default (fast enough for real-time on modern hardware).
    GPU acceleration available if CUDA is present.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.3,
        device: str = "auto",
        model_type: str = "Cnn14",
        top_k: int = 5,
        filter_speech: bool = True,
        filter_music: bool = True,
        debug: bool = False
    ):
        """
        Initialize PANNs classifier.

        Args:
            confidence_threshold: Minimum confidence to report a detection (0-1)
            device: "cpu", "cuda", or "auto" (auto-detect GPU)
            model_type: PANNs model variant ("Cnn14" recommended)
            top_k: Number of top classifications to return
            filter_speech: Ignore speech-related classes
            filter_music: Ignore music-related classes
            debug: Print detailed classification info
        """
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        self.filter_speech = filter_speech
        self.filter_music = filter_music
        self.debug = debug

        # Check dependencies
        self.enabled = TORCH_AVAILABLE and PANNS_AVAILABLE and LIBROSA_AVAILABLE

        if not self.enabled:
            missing = []
            if not TORCH_AVAILABLE:
                missing.append("torch")
            if not PANNS_AVAILABLE:
                missing.append("panns-inference")
            if not LIBROSA_AVAILABLE:
                missing.append("librosa")
            print(f"[PANNS] Disabled - missing dependencies: {', '.join(missing)}")
            self.model = None
            return

        # Determine device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Load AudioSet labels from CSV
        self.audioset_labels = self._load_audioset_labels()

        # Load model (this downloads weights on first run, ~300MB)
        print(f"[PANNS] Loading {model_type} model on {self.device}...")
        try:
            # AudioTagging handles model loading and provides inference interface
            self.model = AudioTagging(
                checkpoint_path=None,  # Uses default Cnn14 checkpoint
                device=self.device
            )
            print(f"[PANNS] Model loaded successfully")
            print(f"[PANNS] Config: threshold={confidence_threshold}, top_k={top_k}")
            print(f"[PANNS] Labels loaded: {len(self.audioset_labels)} classes")
        except Exception as e:
            print(f"[PANNS] Failed to load model: {e}")
            self.model = None
            self.enabled = False

    def _load_audioset_labels(self) -> Dict[int, str]:
        """Load AudioSet class labels from CSV file."""
        import os
        import csv

        # Standard location for panns_data
        labels_path = os.path.expanduser("~/panns_data/class_labels_indices.csv")

        if not os.path.exists(labels_path):
            print(f"[PANNS] Warning: Labels file not found at {labels_path}")
            return {}

        try:
            labels = {}
            with open(labels_path, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 3:
                        idx = int(row[0])
                        label = row[2]  # display_name column
                        labels[idx] = label
            return labels
        except Exception as e:
            print(f"[PANNS] Warning: Failed to load labels: {e}")
            return {}

    def classify(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[AudioEvent]:
        """
        Classify an audio chunk using PANNs.

        Args:
            audio: Audio waveform as numpy array (mono, float32, -1 to 1)
            sample_rate: Sample rate of the audio

        Returns:
            AudioEvent with classification results, or None if disabled/error
        """
        if not self.enabled or self.model is None:
            return None

        try:
            start_time = datetime.now()
            audio_duration = len(audio) / sample_rate

            # Ensure audio is correct format
            audio = np.array(audio, dtype=np.float32)

            # Resample to 32kHz if needed (PANNs expects 32kHz)
            if sample_rate != 32000:
                audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=32000)

            # Ensure audio is 2D (batch, samples) as expected by model
            if audio.ndim == 1:
                audio = audio[np.newaxis, :]

            # Run inference
            # Returns: (clipwise_output, embedding)
            # clipwise_output shape: (batch_size, 527) - probabilities for each class
            clipwise_output, _ = self.model.inference(audio)

            # Get predictions (first batch item)
            predictions = clipwise_output[0]  # Shape: (527,)

            # Get top-k predictions across ALL classes
            top_indices = np.argsort(predictions)[::-1][:self.top_k * 2]  # Get extra for filtering

            # Build results, filtering as needed
            results = []
            all_scores = {}

            for idx in top_indices:
                score = float(predictions[idx])
                label = self._get_label(idx)
                category = self._get_category(idx)

                # Store all scores for debugging
                all_scores[label] = score

                # Apply filters
                if self.filter_speech and category == "speech":
                    continue
                if self.filter_music and category == "music":
                    continue

                # Only include if above threshold
                if score >= self.confidence_threshold:
                    results.append((label, score, category))

                # Stop once we have enough
                if len(results) >= self.top_k:
                    break

            # If no results passed filters, return None
            if not results:
                if self.debug:
                    print(f"[PANNS] No events above threshold {self.confidence_threshold}")
                return None

            # Build AudioEvent
            top_label, top_score, top_category = results[0]
            alternatives = [(label, score) for label, score, _ in results[1:]]

            event = AudioEvent(
                event_type=top_label,
                confidence=top_score,
                alternatives=alternatives,
                timestamp=start_time,
                audio_duration=audio_duration,
                all_scores=all_scores if self.debug else None
            )

            if self.debug:
                self._log_detection(event)

            return event

        except Exception as e:
            print(f"[PANNS] Classification error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def classify_with_spectral(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        spectral_result: Optional[Dict] = None
    ) -> Optional[AudioEvent]:
        """
        Classify audio with optional spectral detector result for hybrid detection.

        This allows combining PANNs neural classification with the existing
        spectral-based detector for better accuracy.

        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            spectral_result: Result from EnvironmentalSoundDetector (optional)

        Returns:
            AudioEvent combining both detection methods
        """
        panns_result = self.classify(audio, sample_rate)

        if panns_result is None and spectral_result is None:
            return None

        # If only one succeeded, return that
        if panns_result is None:
            return self._convert_spectral_result(spectral_result)
        if spectral_result is None:
            return panns_result

        # Both succeeded - combine with voting
        # If both agree on event type, boost confidence
        spectral_type = spectral_result.get('type', '').lower()
        panns_type = panns_result.event_type.lower()

        # Map spectral types to PANNs labels
        type_mapping = {
            'clap': ['clapping', 'clap', 'applause'],
            'knock': ['knock', 'knocking'],
            'tap': ['tap', 'tapping'],
            'door_slam': ['slam', 'door'],
            'footstep': ['footsteps', 'walk', 'run'],
        }

        # Check if types match
        types_match = False
        for spectral_key, panns_variants in type_mapping.items():
            if spectral_type == spectral_key and any(v in panns_type for v in panns_variants):
                types_match = True
                break

        if types_match:
            # Boost confidence when both agree
            combined_confidence = min(1.0, panns_result.confidence * 1.2)
            return AudioEvent(
                event_type=panns_result.event_type,
                confidence=combined_confidence,
                alternatives=panns_result.alternatives,
                timestamp=panns_result.timestamp,
                audio_duration=panns_result.audio_duration,
                all_scores=panns_result.all_scores
            )
        else:
            # Disagree - return higher confidence one
            spectral_conf = spectral_result.get('confidence', 0)
            if spectral_conf > panns_result.confidence:
                return self._convert_spectral_result(spectral_result)
            else:
                return panns_result

    def _convert_spectral_result(self, spectral_result: Dict) -> AudioEvent:
        """Convert spectral detector result to AudioEvent format."""
        return AudioEvent(
            event_type=spectral_result.get('type', 'unknown'),
            confidence=spectral_result.get('confidence', 0.0),
            alternatives=[],
            timestamp=datetime.now(),
            audio_duration=0.0,
            all_scores=None
        )

    def _get_label(self, class_idx: int) -> str:
        """Get human-readable label for AudioSet class index."""
        # First check our environmental classes mapping
        if class_idx in ENVIRONMENTAL_CLASSES:
            return ENVIRONMENTAL_CLASSES[class_idx][0]
        # Then check the full AudioSet labels
        if hasattr(self, 'audioset_labels') and class_idx in self.audioset_labels:
            return self.audioset_labels[class_idx]
        # Fallback to generic label
        return f"Class_{class_idx}"

    def _get_category(self, class_idx: int) -> str:
        """Get our category mapping for AudioSet class index."""
        if class_idx in ENVIRONMENTAL_CLASSES:
            return ENVIRONMENTAL_CLASSES[class_idx][1]
        return "unknown"

    def _log_detection(self, event: AudioEvent):
        """Log detection to console in debug format."""
        alt_str = " | ".join([f"{label} ({score:.2f})" for label, score in event.alternatives[:3]])
        print(f"[PANNS] Detected: {event.event_type} ({event.confidence:.2f})")
        if alt_str:
            print(f"[PANNS]   Alternatives: {alt_str}")

    def format_for_display(self, event: AudioEvent) -> str:
        """Format detection for terminal display."""
        if event is None:
            return ""

        alt_str = ", ".join([f"{label}({score:.0%})" for label, score in event.alternatives[:2]])
        main = f"{event.event_type} ({event.confidence:.0%})"

        if alt_str:
            return f"{main} | alt: {alt_str}"
        return main

    def format_for_kay(self, event: AudioEvent) -> str:
        """Format detection for Kay's context/prompt."""
        if event is None:
            return ""

        return f"[Environmental sound: {event.event_type} detected with {event.confidence:.0%} confidence]"


# Convenience function for quick testing
def classify_audio_file(filepath: str, **kwargs) -> Optional[AudioEvent]:
    """
    Classify an audio file using PANNs.

    Args:
        filepath: Path to audio file (wav, mp3, etc.)
        **kwargs: Additional arguments to PANNsClassifier

    Returns:
        AudioEvent with classification results
    """
    if not LIBROSA_AVAILABLE:
        print("[PANNS] librosa required for file loading")
        return None

    # Load audio file
    audio, sr = librosa.load(filepath, sr=32000, mono=True)

    # Classify
    classifier = PANNsClassifier(**kwargs)
    return classifier.classify(audio, sample_rate=32000)


# AudioSet label lookup (first 100 most common classes)
# Full list: https://github.com/qiuqiangkong/audioset_tagging_cnn/blob/master/metadata/class_labels_indices.csv
AUDIOSET_LABELS = {
    0: "Speech",
    1: "Male speech, man speaking",
    2: "Female speech, woman speaking",
    3: "Child speech, kid speaking",
    4: "Conversation",
    5: "Narration, monologue",
    6: "Babbling",
    7: "Speech synthesizer",
    8: "Shout",
    9: "Bellow",
    10: "Whoop",
    11: "Yell",
    12: "Battle cry",
    13: "Children shouting",
    14: "Screaming",
    15: "Whispering",
    16: "Laughter",
    17: "Baby laughter",
    18: "Giggle",
    19: "Snicker",
    20: "Belly laugh",
    21: "Chuckle, chortle",
    22: "Crying, sobbing",
    23: "Baby cry, infant cry",
    24: "Whimper",
    25: "Wail, moan",
    26: "Sigh",
    27: "Singing",
    28: "Choir",
    29: "Yodeling",
    30: "Chant",
    31: "Mantra",
    32: "Male singing",
    33: "Female singing",
    34: "Child singing",
    35: "Synthetic singing",
    36: "Rapping",
    37: "Humming",
    38: "Groan",
    39: "Grunt",
    40: "Whistling",
    41: "Breathing",
    42: "Wheeze",
    43: "Snoring",
    44: "Gasp",
    45: "Pant",
    46: "Snort",
    47: "Cough",
    48: "Throat clearing",
    49: "Sneeze",
    50: "Sniff",
    51: "Run",
    52: "Shuffle",
    53: "Walk, footsteps",
    54: "Chewing, mastication",
    55: "Biting",
    56: "Gargling",
    57: "Stomach rumble",
    58: "Burping, eructation",
    59: "Hiccup",
    60: "Fart",
    61: "Hands",
    62: "Finger snapping",
    63: "Clapping",
    64: "Heart sounds, heartbeat",
    65: "Heart murmur",
    66: "Cheering",
    67: "Applause",
    68: "Chatter",
    69: "Crowd",
    70: "Hubbub, speech noise, speech babble",
    71: "Children playing",
    72: "Animal",
    73: "Domestic animals, pets",
    74: "Dog",
    75: "Bark",
    76: "Yip",
    77: "Howl",
    78: "Bow-wow",
    79: "Growling",
    80: "Whimper (dog)",
    81: "Cat",
    82: "Purr",
    83: "Meow",
    84: "Hiss",
    85: "Caterwaul",
    86: "Livestock, farm animals, working animals",
    87: "Horse",
    88: "Clip-clop",
    89: "Neigh, whinny",
    90: "Cattle, bovinae",
    91: "Moo",
    92: "Cowbell",
    93: "Pig",
    94: "Oink",
    95: "Goat",
    96: "Bleat",
    97: "Sheep",
    98: "Fowl",
    99: "Chicken, rooster",
}
