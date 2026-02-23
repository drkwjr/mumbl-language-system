"""Voice Activity Detection using WebRTC VAD"""

from typing import List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

try:
    import webrtcvad

    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    logger.warning("webrtcvad not available. Install with: pip install webrtcvad")


class VADProcessor:
    """Voice Activity Detection using WebRTC VAD"""

    # Frame sizes for different sample rates (30ms frames)
    FRAME_SIZE_MS = 30
    FRAME_SIZES = {
        8000: 240,  # 30ms at 8kHz
        16000: 480,  # 30ms at 16kHz
        32000: 960,  # 30ms at 32kHz
        48000: 1440,  # 30ms at 48kHz
    }

    def __init__(
        self, aggressiveness: int = 2, sample_rate: int = 16000, merge_collar_ms: int = 200
    ):
        """
        Initialize VAD processor.

        Args:
            aggressiveness: VAD aggressiveness mode 0-3 (0=least aggressive, 3=most aggressive)
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            merge_collar_ms: Merge speech frames within this collar (ms) to avoid fragmentation
        """
        if not WEBRTC_VAD_AVAILABLE:
            raise ImportError("webrtcvad is not installed. Install with: pip install webrtcvad")

        if sample_rate not in self.FRAME_SIZES:
            raise ValueError(
                f"Sample rate {sample_rate} not supported. Must be one of {list(self.FRAME_SIZES.keys())}"
            )

        if aggressiveness < 0 or aggressiveness > 3:
            raise ValueError("Aggressiveness must be between 0 and 3")

        self.aggressiveness = aggressiveness
        self.sample_rate = sample_rate
        self.merge_collar_ms = merge_collar_ms
        self.frame_size = self.FRAME_SIZES[sample_rate]
        self.frame_duration_ms = self.FRAME_SIZE_MS

        self.vad = webrtcvad.Vad(aggressiveness)

        logger.info(
            "VAD processor initialized",
            aggressiveness=aggressiveness,
            sample_rate=sample_rate,
            frame_size=self.frame_size,
            merge_collar_ms=merge_collar_ms,
        )

    def process_audio(self, audio_data: np.ndarray) -> List[Tuple[float, float]]:
        """
        Detect speech regions in audio.

        Args:
            audio_data: Audio samples as numpy array (int16 format)

        Returns:
            List of (start_time, end_time) tuples in seconds
        """
        # Ensure int16 format
        if audio_data.dtype != np.int16:
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                # Convert float to int16
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)

        # Ensure mono
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        num_samples = len(audio_data)
        num_frames = num_samples // self.frame_size

        speech_frames = []

        # Process frames
        for i in range(num_frames):
            frame_start = i * self.frame_size
            frame_end = frame_start + self.frame_size
            frame = audio_data[frame_start:frame_end]

            # WebRTC VAD requires exactly frame_size samples
            if len(frame) < self.frame_size:
                # Pad last frame
                frame = np.pad(frame, (0, self.frame_size - len(frame)), mode="constant")

            try:
                is_speech = self.vad.is_speech(frame.tobytes(), self.sample_rate)
                if is_speech:
                    frame_time = (i * self.FRAME_SIZE_MS) / 1000.0
                    speech_frames.append(frame_time)
            except Exception as e:
                logger.warning("VAD frame processing failed", frame_idx=i, error=str(e))
                continue

        # Merge speech frames within collar
        if not speech_frames:
            return []

        merged_regions = self._merge_frames(speech_frames)

        logger.debug(
            "VAD processing complete",
            total_frames=num_frames,
            speech_frames=len(speech_frames),
            merged_regions=len(merged_regions),
        )

        return merged_regions

    def _merge_frames(self, speech_frames: List[float]) -> List[Tuple[float, float]]:
        """
        Merge consecutive speech frames within collar.

        Args:
            speech_frames: List of frame start times (seconds)

        Returns:
            List of (start, end) tuples
        """
        if not speech_frames:
            return []

        collar_seconds = self.merge_collar_ms / 1000.0
        frame_duration = self.FRAME_SIZE_MS / 1000.0

        regions = []
        current_start = speech_frames[0]
        current_end = speech_frames[0] + frame_duration

        for frame_time in speech_frames[1:]:
            expected_next = current_end + collar_seconds

            if frame_time <= expected_next:
                # Merge: extend current region
                current_end = frame_time + frame_duration
            else:
                # Gap too large: start new region
                regions.append((current_start, current_end))
                current_start = frame_time
                current_end = frame_time + frame_duration

        # Add final region
        regions.append((current_start, current_end))

        return regions

    def filter_by_min_duration(
        self, regions: List[Tuple[float, float]], min_duration: float = 0.5
    ) -> List[Tuple[float, float]]:
        """
        Filter out regions shorter than minimum duration.

        Args:
            regions: List of (start, end) tuples
            min_duration: Minimum duration in seconds

        Returns:
            Filtered list of regions
        """
        filtered = [(start, end) for start, end in regions if (end - start) >= min_duration]

        return filtered
