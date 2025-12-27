"""Integration tests for prefilter module"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

from radio_ingestion.prefilter.window_extractor import WindowExtractor
from radio_ingestion.storage.radio_repositories import RadioSegmentRepository, RadioShardRepository
from mumbl_storage.db import get_connection, DatabaseConfig

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not available")
def test_extract_and_store_segments(tmp_path):
    """Test extracting speech windows and storing in database"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
    
    # Create a synthetic audio file for testing
    sample_rate = 22050
    duration = 2.0  # 2 seconds
    samples = int(sample_rate * duration)
    
    # Generate test audio (mix of tones that VAD might detect as speech)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Save as WAV file
    test_audio_path = tmp_path / "test_audio.wav"
    sf.write(str(test_audio_path), audio, sample_rate)
    
    # Initialize extractor
    extractor = WindowExtractor(
        sample_rate=sample_rate,
        vad_aggressiveness=2,
        music_threshold=0.6
    )
    
    # Extract speech windows
    result = extractor.process_shard(str(test_audio_path))
    
    assert "segments" in result
    assert "speech_ratio" in result
    assert isinstance(result["segments"], list)
    assert 0.0 <= result["speech_ratio"] <= 1.0
    
    # Store in database if we have a shard
    with get_connection() as conn:
        shard_repo = RadioShardRepository(conn)
        segment_repo = RadioSegmentRepository(conn)
        
        # Create a test shard record first
        # Note: This requires an existing source_id, so we'll skip if no sources exist
        from radio_ingestion.storage.radio_repositories import RadioSourceRepository
        source_repo = RadioSourceRepository(conn)
        sources = source_repo.list_active()
        
        if not sources:
            pytest.skip("No active sources to test with")
        
        test_source = sources[0]
        
        # Create shard
        shard_data = {
            "source_id": test_source["id"],
            "start_ts": datetime.now(timezone.utc),
            "end_ts": datetime.now(timezone.utc),
            "duration": duration,
            "path": str(test_audio_path),
            "capture_status": "captured",
            "sample_rate": sample_rate,
            "channels": 1
        }
        
        shard_id = shard_repo.insert(shard_data)
        
        # Store segments
        segment_ids = []
        for segment in result["segments"]:
            segment_data = {
                "shard_id": shard_id,
                "start": segment["start"],
                "end": segment["end"],
                "is_speech": segment["is_speech"],
                "music_prob": segment["music_prob"],
                "lang_probs": {},  # Will be filled by LID later
                "primary_lang": None,
                "confidence": None
            }
            
            segment_id = segment_repo.insert(segment_data)
            segment_ids.append(segment_id)
        
        # Verify segments were stored
        stored_segments = segment_repo.get_by_shard(shard_id)
        assert len(stored_segments) == len(segment_ids)
        
        # Update shard status
        shard_repo.update_status(
            shard_id,
            "prefiltered",
            speech_ratio=result["speech_ratio"],
            total_segments=result["total_segments"],
            speech_segments=result["speech_segments"]
        )


@pytest.mark.integration
@pytest.mark.skipif(not LIBROSA_AVAILABLE, reason="librosa not available")
def test_speech_ratio_calculation(tmp_path):
    """Test that speech ratio is calculated correctly"""
    sample_rate = 22050
    duration = 5.0
    
    # Create audio with known characteristics
    # (In a real test, you'd use actual speech/music samples)
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.random.randn(len(t)).astype(np.float32) * 0.1
    
    test_audio_path = tmp_path / "test_speech_ratio.wav"
    sf.write(str(test_audio_path), audio, sample_rate)
    
    extractor = WindowExtractor(sample_rate=sample_rate)
    
    result = extractor.process_shard(str(test_audio_path))
    
    # Verify speech ratio is in valid range
    assert 0.0 <= result["speech_ratio"] <= 1.0
    assert result["total_duration"] > 0.0
    
    # Speech ratio should be: speech_duration / total_duration
    calculated_speech_duration = sum(s["duration"] for s in result["segments"])
    expected_ratio = calculated_speech_duration / result["total_duration"]
    
    assert abs(result["speech_ratio"] - expected_ratio) < 0.01  # Allow small floating point error

