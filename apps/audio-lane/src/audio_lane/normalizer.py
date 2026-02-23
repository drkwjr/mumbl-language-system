"""
Audio normalization: mono conversion, resampling, silence trimming.
"""

import os
from typing import Optional, Tuple

import numpy as np


def _require_audio_deps():
    try:
        import librosa
        import soundfile as sf
    except ImportError as exc:
        raise ImportError(
            "librosa and soundfile are required for audio normalization. "
            "Install with: pip install librosa soundfile"
        ) from exc
    return librosa, sf


def normalize_audio(
    input_path: str,
    output_path: Optional[str] = None,
    sample_rate: int = 22050,
    target_channels: int = 1,
    trim_silence: bool = True,
    trim_db: float = 30.0,
) -> str:
    """
    Normalize audio file: convert to mono, resample, trim silence.

    Args:
        input_path: Path to input audio file
        output_path: Path to save normalized audio (auto-generated if None)
        sample_rate: Target sample rate (22050 or 24000)
        target_channels: Target channels (1 for mono)
        trim_silence: Whether to trim leading/trailing silence
        trim_db: Silence threshold in dB

    Returns:
        Path to normalized audio file
    """
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.join(os.path.dirname(input_path), "../normalized")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base_name}_normalized.wav")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    librosa, sf = _require_audio_deps()

    # Load audio
    y, sr = librosa.load(input_path, sr=None, mono=False)

    # Convert to mono if needed
    if len(y.shape) > 1:
        if target_channels == 1:
            y = librosa.to_mono(y)
        else:
            # Keep stereo
            pass

    # Resample if needed
    if sr != sample_rate:
        y = librosa.resample(y, orig_sr=sr, target_sr=sample_rate)

    # Trim silence
    if trim_silence:
        y_trimmed, _ = librosa.effects.trim(y, top_db=trim_db)
        y = y_trimmed

    # Save normalized audio
    sf.write(output_path, y, sample_rate, format="WAV", subtype="PCM_16")

    return output_path
