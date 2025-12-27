"""Integration tests for pipeline integration"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from radio_ingestion.integration.pipeline_adapter import RadioPipelineAdapter
from radio_ingestion.storage.radio_repositories import (
    RadioSegmentRepository,
    RadioShardRepository,
    RadioSourceRepository
)
from mumbl_storage.db import get_connection, DatabaseConfig
from mumbl_storage.repositories import AudioSegmentRepository
from mumbl_data_contracts.segments import AudioSegment


@pytest.mark.integration
def test_convert_and_store_in_audio_segments(tmp_path):
    """Test converting radio segments and storing in audio_segments table"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
    
    adapter = RadioPipelineAdapter(min_confidence=0.7)
    
    with get_connection() as conn:
        # Get or create test data
        source_repo = RadioSourceRepository(conn)
        shard_repo = RadioShardRepository(conn)
        segment_repo = RadioSegmentRepository(conn)
        audio_repo = AudioSegmentRepository(conn)
        
        sources = source_repo.list_active()
        if not sources:
            pytest.skip("No active sources to test with")
        
        test_source = sources[0]
        
        # Get or create test shard
        shards = shard_repo.get_by_source(test_source["id"], limit=1)
        if not shards:
            pytest.skip("No shards to test with")
        
        test_shard = shards[0]
        
        # Get segments
        segments = segment_repo.get_by_shard(test_shard["id"])
        if not segments:
            pytest.skip("No segments to test with")
        
        # Convert to AudioSegment
        audio_segments = []
        for seg in segments:
            try:
                audio_seg = adapter.convert_segment_to_audiosegment(
                    seg,
                    test_shard,
                    test_source
                )
                
                # Store in audio_segments table
                segment_id = audio_repo.insert(
                    audio_seg,
                    batch_id="radio_test",
                    granularity="sentence",
                    sample_rate=22050
                )
                
                if segment_id:
                    audio_segments.append(audio_seg)
            except Exception as e:
                pytest.fail(f"Conversion or storage failed: {e}")
        
        assert len(audio_segments) > 0, "Should have stored at least one segment"
        
        # Verify segments are in audio_segments table
        stored = audio_repo.get_by_batch("radio_test")
        assert len(stored) > 0, "Segments should be retrievable from audio_segments"


@pytest.mark.integration
def test_batch_export_with_filters(tmp_path):
    """Test batch export with quality filters"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
    
    adapter = RadioPipelineAdapter(
        min_speech_ratio=0.5,  # Lower threshold for test
        min_confidence=0.6,     # Lower threshold for test
        min_duration=1.0,       # Allow shorter segments
        max_duration=30.0       # Allow longer segments
    )
    
    with get_connection() as conn:
        exported = adapter.batch_export_for_asr(
            db_conn=conn,
            min_confidence=0.6,
            limit=10
        )
        
        # Verify export format
        assert isinstance(exported, list)
        
        if exported:
            item = exported[0]
            assert "segment" in item
            assert isinstance(item["segment"], AudioSegment)
            assert "audio_hash" in item
            assert "granularity" in item
            assert item["granularity"] == "sentence"


@pytest.mark.integration
def test_filter_quality_segments():
    """Test quality filtering logic"""
    adapter = RadioPipelineAdapter(
        min_confidence=0.8,
        min_duration=2.0,
        max_duration=12.0
    )
    
    segments = [
        {
            "is_speech": True,
            "music_prob": 0.1,
            "confidence": 0.9,
            "duration": 5.0
        },
        {
            "is_speech": True,
            "music_prob": 0.1,
            "confidence": 0.7,  # Below threshold
            "duration": 5.0
        }
    ]
    
    shard_data = {"speech_ratio": 0.8}
    
    filtered = adapter.filter_high_quality_segments(segments, shard_data)
    
    # First segment should pass, second should be filtered
    assert len(filtered) == 1
    assert filtered[0]["confidence"] == 0.9

