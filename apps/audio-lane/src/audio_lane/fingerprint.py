"""
Audio fingerprinting for deduplication.
"""

import hashlib
from typing import Optional
import numpy as np


def _require_audio_deps():
    try:
        import librosa
    except ImportError as exc:
        raise ImportError(
            "librosa is required for audio fingerprinting. Install with: pip install librosa"
        ) from exc
    return librosa


def compute_fingerprint(audio_path: str) -> str:
    """
    Compute acoustic fingerprint (hash) for audio file.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        SHA-256 hash string
    """
    librosa = _require_audio_deps()

    # Load audio
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    
    # Extract chroma features (12-dimensional)
    chroma = librosa.feature.chroma(y=y, sr=sr)
    
    # Compute MFCC features (13 coefficients)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    
    # Combine features
    features = np.concatenate([
        chroma.mean(axis=1),
        mfccs.mean(axis=1),
    ])
    
    # Convert to bytes and hash
    feature_bytes = features.tobytes()
    fingerprint = hashlib.sha256(feature_bytes).hexdigest()
    
    return fingerprint
