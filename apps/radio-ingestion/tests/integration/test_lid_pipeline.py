"""Integration tests for LID pipeline"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from mumbl_storage.db import DatabaseConfig, get_connection
from radio_ingestion.lid.aggregator import StationAggregator
from radio_ingestion.lid.fusion import LIDFusion
from radio_ingestion.storage.radio_repositories import (
    RadioSegmentRepository,
    RadioStationHourlyRepository,
)

try:
    import librosa
    import soundfile as sf

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


@pytest.mark.integration
def test_fusion_produces_valid_distribution():
    """Test that fusion produces valid probability distribution"""
    fusion = LIDFusion()

    audio_preds = [("so", 0.85), ("en", 0.10), ("ar", 0.05)]
    text_preds = [("so", 0.70), ("en", 0.25), ("ar", 0.05)]

    fused = fusion.fuse_predictions(audio_predictions=audio_preds, text_predictions=text_preds)

    # Verify it's a valid distribution
    assert sum(fused.values()) <= 1.0 + 1e-6  # Allow floating point error
    assert all(0.0 <= prob <= 1.0 for prob in fused.values())

    # Verify primary language
    primary, confidence = fusion.get_primary_language(fused)
    assert primary is not None
    assert 0.0 <= confidence <= 1.0


@pytest.mark.integration
def test_aggregate_and_store_hourly(tmp_path):
    """Test aggregating segments and storing hourly stats"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    with get_connection() as conn:
        segment_repo = RadioSegmentRepository(conn)
        hourly_repo = RadioStationHourlyRepository(conn)

        # Get or create test segments
        # We need a shard_id first - create a minimal test case
        from radio_ingestion.storage.radio_repositories import (
            RadioShardRepository,
            RadioSourceRepository,
        )

        source_repo = RadioSourceRepository(conn)
        shard_repo = RadioShardRepository(conn)

        sources = source_repo.list_active()
        if not sources:
            pytest.skip("No active sources to test with")

        test_source = sources[0]

        # Create test shard
        shard_data = {
            "source_id": test_source["id"],
            "start_ts": datetime.now(timezone.utc),
            "end_ts": datetime.now(timezone.utc),
            "duration": 180.0,
            "path": str(tmp_path / "test.wav"),
            "capture_status": "prefiltered",
            "sample_rate": 22050,
        }
        shard_id = shard_repo.insert(shard_data)

        # Create test segments with language probabilities
        segment_data = [
            {
                "shard_id": shard_id,
                "start": 0.0,
                "end": 10.0,
                "is_speech": True,
                "music_prob": 0.1,
                "lang_probs": {"so": 0.85, "en": 0.10, "ar": 0.05},
                "primary_lang": "so",
                "confidence": 0.85,
            },
            {
                "shard_id": shard_id,
                "start": 10.0,
                "end": 20.0,
                "is_speech": True,
                "music_prob": 0.2,
                "lang_probs": {"so": 0.90, "en": 0.05, "ar": 0.05},
                "primary_lang": "so",
                "confidence": 0.90,
            },
            {
                "shard_id": shard_id,
                "start": 20.0,
                "end": 30.0,
                "is_speech": True,
                "music_prob": 0.15,
                "lang_probs": {"en": 0.80, "so": 0.15, "ar": 0.05},
                "primary_lang": "en",
                "confidence": 0.80,
            },
        ]

        segment_ids = []
        for seg_data in segment_data:
            segment_id = segment_repo.insert(seg_data)
            segment_ids.append(segment_id)

        # Retrieve segments
        stored_segments = segment_repo.get_by_shard(shard_id)

        # Aggregate
        agg = StationAggregator()
        hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        # Convert to format expected by aggregator
        segments_for_agg = [
            {
                "primary_lang": seg["primary_lang"],
                "lang_probs": seg["lang_probs"],
                "confidence": seg["confidence"],
                "duration": seg["end"] - seg["start"],
                "is_speech": seg["is_speech"],
            }
            for seg in stored_segments
        ]

        aggregated = agg.aggregate_hourly(segments_for_agg, hour=hour)

        # Verify aggregation results
        assert aggregated["primary_lang"] is not None
        assert "so" in aggregated["lang_mix"]
        assert aggregated["switch_rate"] >= 0.0
        assert aggregated["total_segments"] == 3

        # Store hourly aggregate
        hourly_data = {
            "source_id": test_source["id"],
            "hour": hour,
            "primary_lang": aggregated["primary_lang"],
            "lang_mix": aggregated["lang_mix"],
            "switch_rate": aggregated["switch_rate"],
            "total_segments": aggregated["total_segments"],
            "speech_segments": aggregated["speech_segments"],
            "speech_ratio": aggregated["speech_ratio"],
            "avg_confidence": aggregated["avg_confidence"],
            "min_confidence": aggregated["min_confidence"],
            "max_confidence": aggregated["max_confidence"],
        }

        hourly_id = hourly_repo.upsert(hourly_data)
        assert hourly_id is not None


@pytest.mark.integration
def test_lang_probs_jsonb_structure(tmp_path):
    """Test that lang_probs are stored correctly as JSONB"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    with get_connection() as conn:
        segment_repo = RadioSegmentRepository(conn)

        from radio_ingestion.storage.radio_repositories import (
            RadioShardRepository,
            RadioSourceRepository,
        )

        source_repo = RadioSourceRepository(conn)
        shard_repo = RadioShardRepository(conn)

        sources = source_repo.list_active()
        if not sources:
            pytest.skip("No active sources to test with")

        test_source = sources[0]

        # Create test shard
        shard_data = {
            "source_id": test_source["id"],
            "start_ts": datetime.now(timezone.utc),
            "end_ts": datetime.now(timezone.utc),
            "duration": 60.0,
            "path": str(tmp_path / "test_lid.wav"),
            "capture_status": "prefiltered",
            "sample_rate": 22050,
        }
        shard_id = shard_repo.insert(shard_data)

        # Create segment with complex lang_probs
        lang_probs = {"so": 0.75, "en": 0.15, "ar": 0.08, "sw": 0.02}

        segment_data = {
            "shard_id": shard_id,
            "start": 0.0,
            "end": 30.0,
            "is_speech": True,
            "music_prob": 0.1,
            "lang_probs": lang_probs,
            "primary_lang": "so",
            "confidence": 0.75,
        }

        segment_id = segment_repo.insert(segment_data)

        # Retrieve and verify
        stored_segments = segment_repo.get_by_shard(shard_id)
        assert len(stored_segments) == 1

        stored_seg = stored_segments[0]

        # Verify lang_probs structure
        assert stored_seg["lang_probs"] == lang_probs
        assert isinstance(stored_seg["lang_probs"], dict)
        assert stored_seg["lang_probs"]["so"] == 0.75
        assert sum(stored_seg["lang_probs"].values()) <= 1.0 + 1e-6
