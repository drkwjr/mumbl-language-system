"""Extract speech windows and compute features"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa/soundfile not available. Install with: pip install librosa soundfile")

from radio_ingestion.prefilter.vad import VADProcessor
from radio_ingestion.prefilter.music_classifier import MusicClassifier


class WindowExtractor:
    """Extract speech windows from audio with VAD and music filtering"""
    
    def __init__(
        self,
        sample_rate: int = 22050,
        vad_aggressiveness: int = 2,
        music_threshold: float = 0.6,
        min_speech_duration: float = 0.5,
        max_window_duration: float = 30.0
    ):
        """
        Initialize window extractor.
        
        Args:
            sample_rate: Audio sample rate
            vad_aggressiveness: VAD aggressiveness (0-3)
            music_threshold: Music probability threshold (0-1)
            min_speech_duration: Minimum speech segment duration (seconds)
            max_window_duration: Maximum window duration for processing (seconds)
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError(
                "librosa and soundfile are required. Install with: pip install librosa soundfile"
            )
        
        self.sample_rate = sample_rate
        self.music_threshold = music_threshold
        self.min_speech_duration = min_speech_duration
        self.max_window_duration = max_window_duration
        
        # Initialize VAD (WebRTC VAD works at 8/16/32/48kHz, resample if needed)
        self.vad_rate = 16000  # Use 16kHz for VAD
        self.vad = VADProcessor(
            aggressiveness=vad_aggressiveness,
            sample_rate=self.vad_rate
        )
        
        # Initialize music classifier
        self.music_classifier = MusicClassifier(
            sample_rate=sample_rate,
            threshold=music_threshold
        )
        
        logger.info(
            "Window extractor initialized",
            sample_rate=sample_rate,
            vad_aggressiveness=vad_aggressiveness,
            music_threshold=music_threshold,
            min_speech_duration=min_speech_duration
        )
    
    def extract_speech_windows(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Extract speech windows from audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            List of segment dictionaries with:
                - start: Start time (seconds)
                - end: End time (seconds)
                - is_speech: Whether segment contains speech
                - music_prob: Music probability (0-1)
                - duration: Segment duration (seconds)
        """
        try:
            # Load audio
            audio_data, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            
            logger.info(
                "Processing audio file",
                audio_path=audio_path,
                duration=len(audio_data) / sr,
                sample_rate=sr
            )
            
            # Resample for VAD if needed
            if sr != self.vad_rate:
                audio_vad = librosa.resample(audio_data, orig_sr=sr, target_sr=self.vad_rate)
            else:
                audio_vad = audio_data
            
            # Convert to int16 for VAD
            audio_vad_int16 = (audio_vad * 32767).astype(np.int16)
            
            # Run VAD
            speech_regions = self.vad.process_audio(audio_vad_int16)
            
            # Filter by minimum duration
            speech_regions = self.vad.filter_by_min_duration(
                speech_regions,
                self.min_speech_duration
            )
            
            if not speech_regions:
                logger.warning("No speech regions detected", audio_path=audio_path)
                return []
            
            # Classify regions as music or speech
            # Convert regions back to original sample rate timing
            regions_with_music = []
            for start_time, end_time in speech_regions:
                # Load segment for music classification
                start_sample = int(start_time * self.sample_rate)
                end_sample = int(end_time * self.sample_rate)
                segment = audio_data[start_sample:end_sample]
                
                if len(segment) < 512:  # Too short for meaningful classification
                    music_prob = 0.0
                else:
                    music_prob, _ = self.music_classifier.classify_segment(segment)
                
                regions_with_music.append((start_time, end_time, music_prob))
            
            # Filter out music segments
            speech_segments = [
                (start, end, music_prob) for start, end, music_prob in regions_with_music
                if music_prob < self.music_threshold
            ]
            
            # Build segment dictionaries
            segments = []
            for start_time, end_time, music_prob in speech_segments:
                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "duration": end_time - start_time,
                    "is_speech": True,
                    "music_prob": music_prob
                })
            
            logger.info(
                "Speech window extraction complete",
                audio_path=audio_path,
                total_regions=len(speech_regions),
                speech_segments=len(speech_segments),
                filtered_by_music=len(speech_regions) - len(speech_segments)
            )
            
            return segments
            
        except Exception as e:
            logger.error(
                "Failed to extract speech windows",
                audio_path=audio_path,
                error=str(e)
            )
            return []
    
    def compute_mfcc_features(
        self,
        audio_data: np.ndarray,
        n_mfcc: int = 13,
        n_fft: int = 2048,
        hop_length: int = 512
    ) -> Optional[np.ndarray]:
        """
        Compute MFCC features for a segment.
        
        Args:
            audio_data: Audio samples
            n_mfcc: Number of MFCC coefficients
            n_fft: FFT window size
            hop_length: Hop length
        
        Returns:
            MFCC features as numpy array or None on error
        """
        try:
            mfccs = librosa.feature.mfcc(
                y=audio_data,
                sr=self.sample_rate,
                n_mfcc=n_mfcc,
                n_fft=n_fft,
                hop_length=hop_length
            )
            
            # Return mean MFCC across time
            return np.mean(mfccs, axis=1).tolist()
            
        except Exception as e:
            logger.warning(
                "MFCC computation failed",
                error=str(e)
            )
            return None
    
    def process_shard(self, shard_path: str) -> Dict[str, Any]:
        """
        Process a captured shard and extract speech segments.
        
        Args:
            shard_path: Path to audio shard file
        
        Returns:
            Dictionary with:
                - segments: List of segment dicts
                - speech_ratio: Ratio of speech to total duration
                - total_segments: Total number of segments
                - speech_segments: Number of speech segments
        """
        segments = self.extract_speech_windows(shard_path)
        
        # Load audio to compute total duration
        try:
            audio_data, sr = librosa.load(shard_path, sr=None, mono=True)
            total_duration = len(audio_data) / sr
        except Exception as e:
            logger.warning(
                "Failed to compute total duration",
                shard_path=shard_path,
                error=str(e)
            )
            total_duration = sum(s["duration"] for s in segments) if segments else 0.0
        
        # Compute speech ratio
        speech_duration = sum(s["duration"] for s in segments)
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0
        
        return {
            "segments": segments,
            "speech_ratio": speech_ratio,
            "total_segments": len(segments),
            "speech_segments": len([s for s in segments if s["is_speech"]]),
            "total_duration": total_duration
        }

