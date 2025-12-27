"""
Sentence-based audio segmentation into 2-12 second clips.
"""

import os
from typing import List, Dict, Optional, Any
from pathlib import Path


def _require_audio_deps():
    try:
        import librosa
        import soundfile as sf
    except ImportError as exc:
        raise ImportError(
            "librosa and soundfile are required for audio segmentation. "
            "Install with: pip install librosa soundfile"
        ) from exc
    return librosa, sf


def segment_audio(
    transcript: Dict[str, Any],
    diarization: List[Dict[str, Any]],
    audio_path: str,
    output_dir: str = "data/audio/clips",
    min_duration: float = 2.0,
    max_duration: float = 12.0
) -> List[Dict[str, Any]]:
    """
    Segment audio into clips based on sentence boundaries.
    
    Args:
        transcript: Transcript dict from ASR (with segments)
        diarization: List of speaker diarization segments
        audio_path: Path to source audio file
        output_dir: Directory to save clips
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        
    Returns:
        List of clip metadata dicts
    """
    os.makedirs(output_dir, exist_ok=True)
    
    librosa, sf = _require_audio_deps()

    # Load audio
    y, sr = librosa.load(audio_path, sr=None)
    
    segments = transcript.get('segments', [])
    if not segments:
        # Fallback: create single segment from full transcript
        duration = len(y) / sr
        segments = [{
            'text': transcript.get('text', ''),
            'start': 0.0,
            'end': duration,
        }]
    
    clips = []
    base_name = Path(audio_path).stem
    
    # Create speaker map for quick lookup
    speaker_map = {}
    for diar_seg in diarization:
        for t in [diar_seg['start'], diar_seg['end']]:
            if t not in speaker_map:
                speaker_map[t] = []
            speaker_map[t].append((diar_seg['start'], diar_seg['end'], diar_seg['speaker_id']))
    
    def get_speaker_at_time(time: float) -> Optional[str]:
        """Get speaker ID at given time."""
        for diar_seg in diarization:
            if diar_seg['start'] <= time <= diar_seg['end']:
                return diar_seg['speaker_id']
        return None
    
    # Process each segment
    for idx, seg in enumerate(segments):
        start_time = seg['start']
        end_time = seg['end']
        text = seg['text']
        
        # Check duration constraints
        duration = end_time - start_time
        
        if duration < min_duration:
            # Skip segments that are too short
            continue
        
        if duration > max_duration:
            # Split long segments (simple midpoint split)
            # Limit recursion depth to prevent deep recursion for extremely long segments
            mid_time = (start_time + end_time) / 2
            half_text = text[:len(text)//2]
            second_half_text = text[len(text)//2:]
            
            # Process first half
            if mid_time - start_time >= min_duration:
                first_half_clips = segment_audio(
                    {'segments': [{'text': half_text, 'start': start_time, 'end': mid_time}]},
                    diarization,
                    audio_path,
                    output_dir,
                    min_duration,
                    max_duration
                )
                clips.extend(first_half_clips)
            
            # Process second half
            if end_time - mid_time >= min_duration:
                second_half_clips = segment_audio(
                    {'segments': [{'text': second_half_text, 'start': mid_time, 'end': end_time}]},
                    diarization,
                    audio_path,
                    output_dir,
                    min_duration,
                    max_duration
                )
                clips.extend(second_half_clips)
            continue
        
        # Get speaker ID
        speaker_id = get_speaker_at_time(start_time)
        
        # Extract audio clip
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        clip_audio = y[start_sample:end_sample]
        
        # Generate clip filename
        clip_filename = f"{base_name}_clip_{idx:04d}.wav"
        clip_path = os.path.join(output_dir, clip_filename)
        
        # Save clip
        sf.write(clip_path, clip_audio, sr, format='WAV', subtype='PCM_16')
        
        # Determine granularity
        granularity = transcript.get('granularity', 'sentence')
        
        # Get alignment confidence from transcript if available
        alignment_confidence = None
        if 'words' in transcript and transcript['words']:
            # Use average word confidence if available
            word_confidences = [w.get('confidence', 1.0) for w in transcript['words'] 
                              if start_time <= w.get('start', 0) <= end_time]
            if word_confidences:
                alignment_confidence = sum(word_confidences) / len(word_confidences)
        
        # Get diarization confidence
        diarization_confidence = None
        for diar_seg in diarization:
            if diar_seg['start'] <= start_time <= diar_seg['end']:
                diarization_confidence = diar_seg.get('confidence', 1.0)
                break
        
        clips.append({
            'clip_path': clip_path,
            'start_time': start_time,
            'end_time': end_time,
            'speaker_id': speaker_id,
            'transcript': text,
            'granularity': granularity,
            'alignment_confidence': alignment_confidence,
            'diarization_confidence': diarization_confidence,
        })
    
    return clips
