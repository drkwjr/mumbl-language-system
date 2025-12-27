"""
Speaker diarization using pyannote.audio.
"""

import os
from typing import List, Dict, Optional, Any


def _require_diarization_deps():
    try:
        from pyannote.audio import Pipeline
        import torch
    except ImportError as exc:
        raise ImportError(
            "pyannote.audio and torch are required for speaker diarization. "
            "Install with: pip install pyannote.audio torch"
        ) from exc
    return Pipeline, torch


def diarize_speakers(
    audio_path: str,
    auth_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform speaker diarization on audio file.
    
    Args:
        audio_path: Path to audio file
        auth_token: HuggingFace token for pyannote models (optional, uses env var if None)
        
    Returns:
        List of dicts with keys: start, end, speaker_id, confidence
    """
    # Try to get auth token from environment
    auth_token = auth_token or os.getenv('HUGGINGFACE_TOKEN')
    
    Pipeline, _torch = _require_diarization_deps()

    # Load pre-trained diarization pipeline
    # Note: First run will download models (~500MB)
    try:
        if auth_token:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=auth_token
            )
        else:
            # Try without auth (may work for some models)
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    except Exception as e:
        # Fallback: use segmentation model if diarization model unavailable
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization@2.1",
                use_auth_token=auth_token
            )
        except Exception as fallback_error:
            raise RuntimeError(
                f"Failed to load diarization pipeline: {str(e)}. "
                f"Fallback also failed: {str(fallback_error)}. "
                "You may need to set HUGGINGFACE_TOKEN environment variable."
            )
    
    # Run diarization
    try:
        diarization = pipeline(audio_path)
    except Exception as e:
        raise RuntimeError(f"Failed to run diarization on {audio_path}: {str(e)}")
    
    # Extract segments
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            'start': turn.start,
            'end': turn.end,
            'speaker_id': speaker,
            'confidence': getattr(turn, 'confidence', 1.0),
        })
    
    return segments
