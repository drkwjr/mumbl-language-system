"""Music vs speech classifier using mel spectrogram features"""

from typing import List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available. Install with: pip install librosa")


class MusicClassifier:
    """
    Simple music vs speech classifier using mel spectrogram features.

    Uses heuristics based on spectral characteristics:
    - Music: more harmonic content, more consistent energy across frequencies
    - Speech: more formants, more variable energy
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        n_mels: int = 128,
        hop_length: int = 512,
        n_fft: int = 2048,
        threshold: float = 0.6,
    ):
        """
        Initialize music classifier.

        Args:
            sample_rate: Audio sample rate
            n_mels: Number of mel bands
            hop_length: Hop length for STFT
            n_fft: FFT window size
            threshold: Probability threshold for music classification (0-1)
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa is not installed. Install with: pip install librosa")

        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.hop_length = hop_length
        self.n_fft = n_fft
        self.threshold = threshold

        logger.info(
            "Music classifier initialized",
            sample_rate=sample_rate,
            n_mels=n_mels,
            threshold=threshold,
        )

    def classify_segment(self, audio_data: np.ndarray) -> Tuple[float, bool]:
        """
        Classify a segment as music or speech.

        Args:
            audio_data: Audio samples as numpy array (float32, -1 to 1)

        Returns:
            Tuple of (music_probability, is_music) where is_music = music_prob > threshold
        """
        try:
            # Ensure float32 and mono
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            if len(audio_data.shape) > 1:
                audio_data = librosa.to_mono(audio_data)

            # Compute mel spectrogram
            mel_spec = librosa.feature.melspectrogram(
                y=audio_data,
                sr=self.sample_rate,
                n_mels=self.n_mels,
                hop_length=self.hop_length,
                n_fft=self.n_fft,
            )

            # Convert to dB
            mel_db = librosa.power_to_db(mel_spec, ref=np.max)

            # Extract features for classification
            features = self._extract_features(mel_db)

            # Compute music probability using heuristics
            music_prob = self._compute_music_probability(features)

            is_music = music_prob >= self.threshold

            return music_prob, is_music

        except Exception as e:
            logger.warning("Music classification failed", error=str(e))
            # Default to speech on error
            return 0.0, False

    def _extract_features(self, mel_db: np.ndarray) -> dict:
        """
        Extract features from mel spectrogram.

        Args:
            mel_db: Mel spectrogram in dB

        Returns:
            Dictionary of features
        """
        # Energy statistics
        mean_energy = np.mean(mel_db)
        std_energy = np.std(mel_db)
        max_energy = np.max(mel_db)

        # Spectral centroid (brightness)
        spectral_centroid = np.mean([np.mean(frame) for frame in mel_db.T])

        # Harmonic content (energy concentration)
        # Music tends to have more concentrated energy in harmonic bands
        energy_variance = np.var(mel_db)

        # Temporal stability (music is more stable)
        temporal_variance = np.var([np.mean(frame) for frame in mel_db.T])

        # Zero crossing rate (speech has more ZCR)
        # Approximate from mel bands
        band_std = np.std(mel_db, axis=1)
        zcr_approx = np.mean(band_std)

        return {
            "mean_energy": mean_energy,
            "std_energy": std_energy,
            "max_energy": max_energy,
            "spectral_centroid": spectral_centroid,
            "energy_variance": energy_variance,
            "temporal_variance": temporal_variance,
            "zcr_approx": zcr_approx,
        }

    def _compute_music_probability(self, features: dict) -> float:
        """
        Compute music probability from features using heuristics.

        Args:
            features: Dictionary of extracted features

        Returns:
            Music probability (0-1)
        """
        prob = 0.0

        # Music tends to have:
        # 1. Lower temporal variance (more stable)
        if features["temporal_variance"] < 5.0:
            prob += 0.3
        elif features["temporal_variance"] < 10.0:
            prob += 0.15

        # 2. Higher energy variance (more harmonic content across bands)
        if features["energy_variance"] > 20.0:
            prob += 0.3
        elif features["energy_variance"] > 10.0:
            prob += 0.15

        # 3. Lower ZCR approximation (less variation in spectral bands)
        if features["zcr_approx"] < 2.0:
            prob += 0.2
        elif features["zcr_approx"] < 4.0:
            prob += 0.1

        # 4. Higher spectral centroid (brighter/more full spectrum)
        if features["spectral_centroid"] > -20.0:
            prob += 0.2

        # Clamp to [0, 1]
        prob = max(0.0, min(1.0, prob))

        return prob

    def classify_audio_regions(
        self, audio_data: np.ndarray, regions: list, sample_rate: int
    ) -> List[Tuple[float, float, float]]:
        """
        Classify multiple audio regions.

        Args:
            audio_data: Full audio as numpy array
            regions: List of (start_time, end_time) tuples in seconds
            sample_rate: Audio sample rate

        Returns:
            List of (start_time, end_time, music_prob) tuples
        """
        results = []

        for start_time, end_time in regions:
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)

            segment = audio_data[start_sample:end_sample]

            if len(segment) < self.hop_length:
                # Too short, default to speech
                results.append((start_time, end_time, 0.0))
                continue

            music_prob, _ = self.classify_segment(segment)
            results.append((start_time, end_time, music_prob))

        return results
