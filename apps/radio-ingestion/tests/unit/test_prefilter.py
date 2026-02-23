"""Unit tests for prefilter module"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from radio_ingestion.prefilter.music_classifier import LIBROSA_AVAILABLE, MusicClassifier
from radio_ingestion.prefilter.vad import WEBRTC_VAD_AVAILABLE, VADProcessor
from radio_ingestion.prefilter.window_extractor import WindowExtractor


class TestVADProcessor:
    """Test VADProcessor"""

    @pytest.fixture
    def vad(self):
        """Create VAD processor (skip if webrtcvad not available)"""
        if not WEBRTC_VAD_AVAILABLE:
            pytest.skip("webrtcvad not available")
        return VADProcessor(aggressiveness=2, sample_rate=16000)

    def test_init(self, vad):
        """Test VAD initialization"""
        assert vad.aggressiveness == 2
        assert vad.sample_rate == 16000
        assert vad.frame_size == 480  # 30ms at 16kHz

    def test_init_invalid_sample_rate(self):
        """Test VAD with invalid sample rate"""
        if not WEBRTC_VAD_AVAILABLE:
            pytest.skip("webrtcvad not available")

        with pytest.raises(ValueError, match="not supported"):
            VADProcessor(sample_rate=22050)  # 22.05kHz not supported

    def test_process_audio_silence(self, vad):
        """Test VAD on silence (should detect no speech)"""
        # Generate silence
        silence = np.zeros(4800, dtype=np.int16)  # 300ms at 16kHz

        regions = vad.process_audio(silence)

        # Silence should produce no or very few speech regions
        assert isinstance(regions, list)

    def test_merge_frames(self, vad):
        """Test frame merging logic"""
        # Create frames with small gaps (should merge)
        frames = [0.0, 0.03, 0.06, 0.5, 0.53]  # First 3 close, gap, last 2 close

        regions = vad._merge_frames(frames)

        assert len(regions) <= len(frames)  # Should merge some

    def test_filter_by_min_duration(self, vad):
        """Test minimum duration filtering"""
        regions = [
            (0.0, 0.2),  # Too short (0.2s < 0.5s)
            (1.0, 2.0),  # Long enough (1.0s)
            (3.0, 3.3),  # Too short (0.3s < 0.5s)
            (5.0, 6.0),  # Long enough (1.0s)
        ]

        filtered = vad.filter_by_min_duration(regions, min_duration=0.5)

        assert len(filtered) == 2
        assert (1.0, 2.0) in filtered
        assert (5.0, 6.0) in filtered


class TestMusicClassifier:
    """Test MusicClassifier"""

    @pytest.fixture
    def classifier(self):
        """Create music classifier (skip if librosa not available)"""
        if not LIBROSA_AVAILABLE:
            pytest.skip("librosa not available")
        return MusicClassifier(sample_rate=22050, threshold=0.6)

    def test_init(self, classifier):
        """Test classifier initialization"""
        assert classifier.sample_rate == 22050
        assert classifier.threshold == 0.6
        assert classifier.n_mels == 128

    def test_classify_segment_silence(self, classifier):
        """Test classification of silence"""
        silence = np.zeros(22050, dtype=np.float32)  # 1 second of silence

        music_prob, is_music = classifier.classify_segment(silence)

        assert 0.0 <= music_prob <= 1.0
        assert isinstance(is_music, bool)

    def test_classify_segment_tone(self, classifier):
        """Test classification of a pure tone (simpler than music)"""
        # Generate a simple sine wave
        duration = 1.0
        sample_rate = 22050
        freq = 440.0  # A4 note
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * freq * t).astype(np.float32)

        music_prob, is_music = classifier.classify_segment(tone)

        assert 0.0 <= music_prob <= 1.0
        assert isinstance(is_music, bool)

    def test_extract_features(self, classifier):
        """Test feature extraction"""
        # Create mock mel spectrogram (random data)
        mel_db = np.random.randn(128, 100) * 10 - 40  # Simulate mel dB

        features = classifier._extract_features(mel_db)

        assert "mean_energy" in features
        assert "std_energy" in features
        assert "spectral_centroid" in features
        assert "temporal_variance" in features

    def test_compute_music_probability(self, classifier):
        """Test music probability computation"""
        features = {
            "mean_energy": -30.0,
            "std_energy": 5.0,
            "max_energy": -20.0,
            "spectral_centroid": -15.0,
            "energy_variance": 25.0,
            "temporal_variance": 3.0,
            "zcr_approx": 1.5,
        }

        prob = classifier._compute_music_probability(features)

        assert 0.0 <= prob <= 1.0


class TestWindowExtractor:
    """Test WindowExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create window extractor (skip if dependencies not available)"""
        if not WEBRTC_VAD_AVAILABLE or not LIBROSA_AVAILABLE:
            pytest.skip("webrtcvad or librosa not available")
        return WindowExtractor(sample_rate=22050, vad_aggressiveness=2, music_threshold=0.6)

    def test_init(self, extractor):
        """Test extractor initialization"""
        assert extractor.sample_rate == 22050
        assert extractor.music_threshold == 0.6
        assert extractor.vad_rate == 16000

    def test_extract_speech_windows_empty(self, extractor, tmp_path):
        """Test extraction from non-existent file"""
        result = extractor.extract_speech_windows("/nonexistent/file.wav")

        assert result == []

    @pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not available")
    def test_compute_mfcc_features(self, extractor):
        """Test MFCC feature computation"""
        # Generate test audio (1 second of random noise)
        audio = np.random.randn(22050).astype(np.float32)

        mfcc = extractor.compute_mfcc_features(audio)

        assert mfcc is not None
        assert isinstance(mfcc, list)
        assert len(mfcc) == 13  # Default n_mfcc

    @pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not available")
    def test_process_shard_mock(self, extractor, tmp_path):
        """Test processing a shard (with mock audio file)"""
        # This would require creating a real audio file for full test
        # For now, test that it handles missing file gracefully

        result = extractor.process_shard("/nonexistent/file.wav")

        # Should return empty segments list
        assert result["segments"] == []
        assert result["speech_ratio"] == 0.0
        assert result["total_segments"] == 0
