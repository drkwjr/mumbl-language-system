"""
Integration tests for Audio Lane components.
Tests actual functionality to identify issues.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

# Test imports
def test_audio_lane_imports():
    """Test that all audio lane modules can be imported."""
    try:
        from audio_lane.youtube_downloader import download_audio
        from audio_lane.normalizer import normalize_audio
        from audio_lane.asr_whisper import transcribe_audio
        from audio_lane.diarization import diarize_speakers
        from audio_lane.segmenter import segment_audio
        from audio_lane.fingerprint import compute_fingerprint
        from audio_lane.processor import AudioLaneProcessor
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import audio lane modules: {e}")


def test_audio_lane_processor_init():
    """Test AudioLaneProcessor initialization."""
    try:
        from audio_lane.processor import AudioLaneProcessor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = AudioLaneProcessor(output_base_dir=tmpdir)
            assert processor is not None
            assert processor.sample_rate == 22050
            assert processor.min_clip_duration == 2.0
            assert processor.max_clip_duration == 12.0
    except Exception as e:
        pytest.fail(f"Failed to initialize AudioLaneProcessor: {e}")


def test_normalizer_function():
    """Test audio normalization function (requires librosa)."""
    try:
        from audio_lane.normalizer import normalize_audio
        import librosa
        import soundfile as sf
        import numpy as np
        
        # Create a dummy audio file
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "test_audio.wav")
            output_path = os.path.join(tmpdir, "normalized.wav")
            
            # Generate a simple sine wave (1 second at 22050 Hz)
            duration = 1.0
            sr = 44100
            t = np.linspace(0, duration, int(sr * duration))
            audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
            
            # Save test audio
            sf.write(input_path, audio, sr)
            
            # Normalize
            result_path = normalize_audio(
                input_path,
                output_path=output_path,
                sample_rate=22050
            )
            
            assert os.path.exists(result_path)
            
            # Load and verify
            y, sr_out = librosa.load(result_path, sr=None)
            assert sr_out == 22050
            
    except ImportError as e:
        pytest.skip(f"Skipping test - missing dependency: {e}")
    except Exception as e:
        pytest.fail(f"Audio normalization test failed: {e}")


def test_fingerprint_function():
    """Test audio fingerprinting."""
    try:
        from audio_lane.fingerprint import compute_fingerprint
        import librosa
        import soundfile as sf
        import numpy as np
        
        # Create a dummy audio file
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "test_audio.wav")
            
            # Generate test audio
            duration = 1.0
            sr = 22050
            t = np.linspace(0, duration, int(sr * duration))
            audio = np.sin(2 * np.pi * 440 * t)
            sf.write(audio_path, audio, sr)
            
            # Compute fingerprint
            fingerprint = compute_fingerprint(audio_path)
            
            assert isinstance(fingerprint, str)
            assert len(fingerprint) == 64  # SHA-256 hex digest
            assert fingerprint.isalnum() or 'a' <= fingerprint.lower() <= 'f'
            
    except ImportError as e:
        pytest.skip(f"Skipping test - missing dependency: {e}")
    except Exception as e:
        pytest.fail(f"Fingerprint test failed: {e}")


@pytest.mark.slow
def test_youtube_downloader_mock():
    """Test YouTube downloader (mocked to avoid actual download)."""
    # This would require mocking yt-dlp or using a test URL
    # For now, just test that the function signature is correct
    try:
        from audio_lane.youtube_downloader import download_audio
        import inspect
        
        sig = inspect.signature(download_audio)
        params = list(sig.parameters.keys())
        
        assert 'url' in params
        assert 'output_dir' in params
        assert 'language' in params
        
    except Exception as e:
        pytest.fail(f"YouTube downloader test failed: {e}")


@pytest.mark.skip(reason="Requires OpenAI API key and costs money")
def test_whisper_api_integration():
    """Test Whisper API integration (requires API key)."""
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OPENAI_API_KEY not set")
    
    try:
        from audio_lane.asr_whisper import transcribe_audio
        import librosa
        import soundfile as sf
        import numpy as np
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "test_audio.wav")
            
            # Create a short test audio (speech would be better, but sine wave will work)
            duration = 2.0
            sr = 22050
            t = np.linspace(0, duration, int(sr * duration))
            audio = np.sin(2 * np.pi * 440 * t)
            sf.write(audio_path, audio, sr)
            
            # This will fail because sine wave isn't speech, but tests the API connection
            result = transcribe_audio(audio_path, language="en")
            
            assert 'text' in result
            assert 'segments' in result
            assert 'language' in result
            
    except Exception as e:
        pytest.fail(f"Whisper API test failed: {e}")


@pytest.mark.skip(reason="Requires pyannote.audio models which are large")
def test_diarization_mock():
    """Test diarization (would require model download)."""
    try:
        from audio_lane.diarization import diarize_speakers
        import inspect
        
        sig = inspect.signature(diarize_speakers)
        params = list(sig.parameters.keys())
        
        assert 'audio_path' in params
        assert 'auth_token' in params
        
    except Exception as e:
        pytest.fail(f"Diarization test failed: {e}")

