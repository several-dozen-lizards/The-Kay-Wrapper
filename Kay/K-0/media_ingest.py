"""
Media Ingest - Audio Analysis for Kay Zero

Uses librosa for audio feature extraction (BPM, key, energy, etc.)
Optionally uses CLAP for vibe descriptions if available.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

import librosa
import numpy as np

# Optional CLAP for vibe descriptions
CLAP_AVAILABLE = False
try:
    from msclap import CLAP
    CLAP_AVAILABLE = True
except ImportError:
    print("[MEDIA INGEST] msclap not available - vibe descriptions disabled")


class MediaAnalyzer:
    """Analyzes audio files and extracts their technical DNA."""

    def __init__(self):
        self._clap_model = None  # Lazy load

    @property
    def clap_model(self):
        """Lazy load CLAP model."""
        if self._clap_model is None and CLAP_AVAILABLE:
            print("[MEDIA INGEST] Loading CLAP model...")
            self._clap_model = CLAP(version='2023', use_cuda=False)
            print("[MEDIA INGEST] CLAP model ready")
        return self._clap_model

    def analyze_audio(self, filepath: str) -> Dict[str, Any]:
        """
        Returns the immutable SKELETON of a song.

        Args:
            filepath: Path to audio file (mp3, wav, flac, etc.)

        Returns:
            Dict with entity_id, technical_DNA, and empty resonance_log
        """
        print(f"[MEDIA INGEST] Analyzing: {filepath}")

        # Load audio with librosa
        y, sr = librosa.load(filepath, sr=22050, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)

        # Extract BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo) if not hasattr(tempo, '__len__') else float(tempo[0])

        # Extract key and scale using chroma features
        key, scale = self._estimate_key(y, sr)

        # Calculate energy (RMS-based)
        rms = librosa.feature.rms(y=y)[0]
        energy = float(np.mean(rms))

        # Calculate danceability proxy (beat strength + tempo regularity)
        danceability = self._estimate_danceability(y, sr, bpm)

        # Get vibe description from CLAP if available
        vibe = self._get_vibe_description(filepath)

        # Build the artifact
        artifact = {
            "entity_id": self._generate_id(filepath),
            "type": "media_audio",
            "filepath": filepath,
            "technical_DNA": {
                "bpm": round(bpm, 1),
                "key": key,
                "scale": scale,
                "danceability": round(danceability, 3),
                "energy": round(energy, 4),
                "duration_seconds": round(duration, 2),
                "vibe_description": vibe
            },
            "first_analyzed": datetime.now().isoformat(),
            "resonance_log": []  # Empty at birth
        }

        print(f"[MEDIA INGEST] Analysis complete: {key} {scale}, {bpm:.1f} BPM")
        return artifact

    def _estimate_key(self, y: np.ndarray, sr: int) -> tuple:
        """
        Estimate musical key and scale using chroma features.

        Returns:
            Tuple of (key_name, scale) e.g. ("C", "major") or ("A", "minor")
        """
        # Compute chroma features
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        # Key names
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        # Major and minor profiles (Krumhansl-Schmuckler)
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

        # Correlate with all possible keys
        major_corrs = []
        minor_corrs = []

        for i in range(12):
            major_rotated = np.roll(major_profile, i)
            minor_rotated = np.roll(minor_profile, i)
            major_corrs.append(np.corrcoef(chroma_mean, major_rotated)[0, 1])
            minor_corrs.append(np.corrcoef(chroma_mean, minor_rotated)[0, 1])

        # Find best match
        best_major_idx = np.argmax(major_corrs)
        best_minor_idx = np.argmax(minor_corrs)

        if major_corrs[best_major_idx] > minor_corrs[best_minor_idx]:
            return keys[best_major_idx], "major"
        else:
            return keys[best_minor_idx], "minor"

    def _estimate_danceability(self, y: np.ndarray, sr: int, bpm: float) -> float:
        """
        Estimate danceability based on beat strength and tempo.

        Returns:
            Float 0.0-1.0 where higher = more danceable
        """
        # Onset strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_strength = float(np.mean(onset_env))

        # Tempo factor (danceable range ~100-130 BPM)
        tempo_factor = 1.0 - abs(bpm - 115) / 115
        tempo_factor = max(0.0, min(1.0, tempo_factor))

        # Beat regularity (lower variance = more regular)
        _, beats = librosa.beat.beat_track(y=y, sr=sr)
        if len(beats) > 1:
            beat_intervals = np.diff(beats)
            regularity = 1.0 / (1.0 + np.std(beat_intervals) / np.mean(beat_intervals))
        else:
            regularity = 0.5

        # Combine factors
        danceability = (onset_strength * 0.3 + tempo_factor * 0.4 + regularity * 0.3)
        return max(0.0, min(1.0, danceability))

    def _get_vibe_description(self, filepath: str) -> str:
        """Get AI-generated vibe description using CLAP if available."""
        if self.clap_model is not None:
            try:
                vibe = self.clap_model.generate_caption([filepath])[0]
                return vibe
            except Exception as e:
                print(f"[MEDIA INGEST] CLAP caption failed: {e}")

        return "Audio track (CLAP unavailable for vibe description)"

    def _generate_id(self, filepath: str) -> str:
        """Create stable ID from filepath."""
        filename = os.path.basename(filepath)
        # Remove extension and clean up
        name = os.path.splitext(filename)[0]
        clean_name = name.replace(" ", "_").lower()
        # Add short hash for uniqueness
        file_hash = hashlib.md5(filepath.encode()).hexdigest()[:8]
        return f"{clean_name}_{file_hash}"


# Testing
if __name__ == "__main__":
    print("MediaAnalyzer Test (librosa-based)")
    print("=" * 50)

    analyzer = MediaAnalyzer()

    # Test with a sample file if available
    test_files = [
        "inputs/media/test.mp3",
        "inputs/media/test.wav",
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\nAnalyzing: {test_file}")
            result = analyzer.analyze_audio(test_file)
            print(json.dumps(result, indent=2))
            break
    else:
        print("\nNo test audio files found. Place an audio file in inputs/media/ to test.")
        print(f"CLAP available: {CLAP_AVAILABLE}")
