"""
Diagnose PANNs clap detection - see what scores all clap-related classes get.

This helps understand why PANNs is classifying claps as "Animal" instead of "Clapping".
"""

import numpy as np
import sys

# Test with synthetic claps first
def create_synthetic_clap():
    """Create a synthetic clap sound."""
    from scipy.signal import butter, filtfilt

    sample_rate = 32000
    duration = 1.0
    audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

    # Clap at 0.5s
    clap_center = int(0.5 * sample_rate)
    clap_len = int(0.04 * sample_rate)  # 40ms

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

    return audio, sample_rate


def diagnose_panns():
    """Run PANNs and show scores for all clap-related classes."""
    print("=" * 60)
    print("PANNs CLAP DETECTION DIAGNOSTIC")
    print("=" * 60)

    # Import PANNs
    try:
        import torch
        from panns_inference import AudioTagging
        import librosa
    except ImportError as e:
        print(f"Missing dependency: {e}")
        return

    # Load AudioSet labels
    import os
    import csv
    labels_path = os.path.expanduser("~/panns_data/class_labels_indices.csv")

    labels = {}
    try:
        with open(labels_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 3:
                    idx = int(row[0])
                    label = row[2]
                    labels[idx] = label
    except Exception as e:
        print(f"Failed to load labels: {e}")
        return

    print(f"Loaded {len(labels)} AudioSet labels")

    # Find clap-related class indices
    clap_related_indices = []
    clap_keywords = ['clap', 'hands', 'applause', 'snap', 'slap', 'hit', 'impact', 'thump']

    for idx, label in labels.items():
        if any(kw in label.lower() for kw in clap_keywords):
            clap_related_indices.append((idx, label))

    print(f"\nClap-related classes found ({len(clap_related_indices)}):")
    for idx, label in sorted(clap_related_indices):
        print(f"  {idx}: {label}")

    # Also track animal-related (since that's what we're seeing)
    animal_related = []
    animal_keywords = ['animal', 'dog', 'bark', 'pet', 'domestic']
    for idx, label in labels.items():
        if any(kw in label.lower() for kw in animal_keywords):
            animal_related.append((idx, label))

    print(f"\nAnimal-related classes ({len(animal_related)}):")
    for idx, label in sorted(animal_related)[:10]:
        print(f"  {idx}: {label}")

    # Load PANNs model
    print("\nLoading PANNs model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AudioTagging(checkpoint_path=None, device=device)
    print(f"Model loaded on {device}")

    # Test with synthetic clap
    print("\n" + "=" * 60)
    print("TEST 1: Synthetic clap")
    print("=" * 60)

    audio, sr = create_synthetic_clap()
    print(f"Created synthetic clap: {len(audio)/sr:.2f}s at {sr}Hz")

    # Resample to 32kHz if needed
    if sr != 32000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=32000)

    # Run inference
    audio_batch = audio[np.newaxis, :]
    clipwise_output, _ = model.inference(audio_batch)
    predictions = clipwise_output[0]

    # Show clap-related scores
    print("\nClap-related class scores:")
    clap_scores = []
    for idx, label in clap_related_indices:
        score = predictions[idx]
        clap_scores.append((label, score))
        print(f"  {label}: {score:.4f} ({score:.1%})")

    # Show animal-related scores
    print("\nAnimal-related class scores:")
    for idx, label in animal_related[:10]:
        score = predictions[idx]
        print(f"  {label}: {score:.4f} ({score:.1%})")

    # Show top 10 overall
    print("\nTop 10 overall predictions:")
    top_indices = np.argsort(predictions)[::-1][:10]
    for idx in top_indices:
        label = labels.get(idx, f"Class_{idx}")
        score = predictions[idx]
        print(f"  {idx}: {label} = {score:.4f} ({score:.1%})")

    # Test with audio file if provided
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print("\n" + "=" * 60)
        print(f"TEST 2: Real audio file - {filepath}")
        print("=" * 60)

        try:
            audio, sr = librosa.load(filepath, sr=32000, mono=True)
            print(f"Loaded: {len(audio)/sr:.2f}s at {sr}Hz")

            audio_batch = audio[np.newaxis, :]
            clipwise_output, _ = model.inference(audio_batch)
            predictions = clipwise_output[0]

            print("\nClap-related class scores:")
            for idx, label in clap_related_indices:
                score = predictions[idx]
                if score > 0.01:  # Only show if > 1%
                    print(f"  {label}: {score:.4f} ({score:.1%})")

            print("\nAnimal-related class scores:")
            for idx, label in animal_related[:10]:
                score = predictions[idx]
                if score > 0.01:
                    print(f"  {label}: {score:.4f} ({score:.1%})")

            print("\nTop 10 overall predictions:")
            top_indices = np.argsort(predictions)[::-1][:10]
            for idx in top_indices:
                label = labels.get(idx, f"Class_{idx}")
                score = predictions[idx]
                print(f"  {idx}: {label} = {score:.4f} ({score:.1%})")

        except Exception as e:
            print(f"Error loading file: {e}")

    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print("""
If 'Clapping' score is low but 'Animal' is high, possible causes:
1. Microphone frequency response emphasizes bark-like frequencies
2. Room reverb adds characteristics similar to animal sounds
3. The model simply confuses sharp percussive sounds

SOLUTIONS:
1. Lower the PANNs threshold and check for Clapping explicitly
2. Use hybrid mode - spectral detector is tuned for claps
3. Add post-processing: if Animal detected with sharp onset + fast decay -> likely clap
4. Train a simple classifier on top of PANNs embeddings (future)
""")


if __name__ == "__main__":
    diagnose_panns()
