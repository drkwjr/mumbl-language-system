"""
Main Audio Lane processor orchestrating the full pipeline.
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from mumbl_data_contracts.segments import AudioSegment
from .youtube_downloader import download_audio
from .normalizer import normalize_audio
from .asr_whisper import transcribe_audio
from .diarization import diarize_speakers
from .segmenter import segment_audio
from .fingerprint import compute_fingerprint


class AudioLaneProcessor:
    """
    Main processor for Audio Lane pipeline.
    
    Orchestrates: download → normalize → ASR → diarization → segment → store
    """
    
    def __init__(
        self,
        output_base_dir: str = "data/audio",
        sample_rate: int = 22050,
        min_clip_duration: float = 2.0,
        max_clip_duration: float = 12.0
    ):
        """
        Initialize processor.
        
        Args:
            output_base_dir: Base directory for audio outputs
            sample_rate: Target sample rate (22050 or 24000)
            min_clip_duration: Minimum clip duration in seconds
            max_clip_duration: Maximum clip duration in seconds
        """
        self.output_base_dir = output_base_dir
        self.sample_rate = sample_rate
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        
        # Ensure directories exist
        os.makedirs(os.path.join(output_base_dir, 'raw'), exist_ok=True)
        os.makedirs(os.path.join(output_base_dir, 'normalized'), exist_ok=True)
        os.makedirs(os.path.join(output_base_dir, 'clips'), exist_ok=True)
    
    def process_youtube(
        self,
        url: str,
        language: str,
        batch_id: Optional[str] = None,
        dialect: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process YouTube URL through full Audio Lane pipeline.
        
        Args:
            url: YouTube URL
            language: Language code (e.g., 'en', 'so', 'ak')
            batch_id: Optional batch ID for tracking
            dialect: Optional dialect code
            
        Returns:
            Dict with segments, stats, and outputs
        """
        # Step 1: Download audio
        download_result = download_audio(
            url,
            output_dir=os.path.join(self.output_base_dir, 'raw'),
            language=language
        )
        raw_audio_path = download_result['audio_path']
        duration = download_result['duration']
        
        # Step 2: Normalize audio
        normalized_path = normalize_audio(
            raw_audio_path,
            sample_rate=self.sample_rate
        )
        
        # Step 3: ASR transcription
        transcript = transcribe_audio(normalized_path, language=language)
        detected_language = transcript.get('language')
        
        # Step 4: Speaker diarization
        diarization = diarize_speakers(normalized_path)
        
        # Step 5: Segment audio into clips
        clips = segment_audio(
            transcript,
            diarization,
            normalized_path,
            output_dir=os.path.join(self.output_base_dir, 'clips'),
            min_duration=self.min_clip_duration,
            max_duration=self.max_clip_duration
        )
        
        # Step 6: Convert clips to AudioSegment contracts
        audio_segments = []
        for clip in clips:
            # Compute fingerprint for deduplication
            audio_hash = compute_fingerprint(clip['clip_path'])
            
            segment = AudioSegment(
                audio_file=clip['clip_path'],
                start=clip['start_time'],
                end=clip['end_time'],
                speaker_id=clip.get('speaker_id'),
                transcript_text=clip['transcript'],
                lang=language,
                dialect=dialect,
                alignment_confidence=clip.get('alignment_confidence'),
                diarization_confidence=clip.get('diarization_confidence'),
            )
            
            audio_segments.append({
                'segment': segment,
                'audio_hash': audio_hash,
                'granularity': clip.get('granularity', 'sentence'),
                'sample_rate': self.sample_rate,
            })
        
        # Step 7: Generate CSV output path
        csv_path = os.path.join(
            self.output_base_dir,
            f"paired_speech_corpus_{batch_id or 'default'}.csv"
        )
        
        return {
            'segments': audio_segments,
            'stats': {
                'total_clips': len(audio_segments),
                'duration_seconds': duration,
                'language': language,
                'dialect': dialect,
                'detected_language': detected_language,
            },
            'outputs': {
                'csv': csv_path,
                'clips_dir': os.path.join(self.output_base_dir, 'clips'),
            },
            'raw_audio_path': raw_audio_path,
            'normalized_audio_path': normalized_path,
            'detected_language': detected_language,
        }
