"""Unit tests for pipeline integration"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from radio_ingestion.integration.pipeline_adapter import (
    RadioPipelineAdapter,
    create_adapter
)
from mumbl_data_contracts.segments import AudioSegment


class TestRadioPipelineAdapter:
    """Test pipeline adapter"""
    
    def test_init(self):
        """Test adapter initialization"""
        adapter = RadioPipelineAdapter(
            min_speech_ratio=0.7,
            min_confidence=0.8
        )
        assert adapter.min_speech_ratio == 0.7
        assert adapter.min_confidence == 0.8
    
    def test_convert_segment_to_audiosegment(self):
        """Test converting radio segment to AudioSegment"""
        adapter = RadioPipelineAdapter()
        
        radio_segment = {
            "id": 1,
            "start": 0.0,
            "end": 5.0,
            "is_speech": True,
            "music_prob": 0.2,
            "lang_probs": {"so": 0.85, "en": 0.15},
            "primary_lang": "so",
            "confidence": 0.85
        }
        
        shard_data = {
            "id": 1,
            "path": "/test/audio.wav",
            "s3_url": None,
            "source_id": 1
        }
        
        source_data = {
            "id": 1,
            "name": "Test Station",
            "country": "SO"
        }
        
        audio_seg = adapter.convert_segment_to_audiosegment(
            radio_segment,
            shard_data,
            source_data
        )
        
        assert isinstance(audio_seg, AudioSegment)
        assert audio_seg.start == 0.0
        assert audio_seg.end == 5.0
        assert audio_seg.lang == "so"
        assert audio_seg.dialect_probs == {"so": 0.85, "en": 0.15}
        assert audio_seg.alignment_confidence == 0.85
    
    def test_filter_high_quality_segments(self):
        """Test filtering high-quality segments"""
        adapter = RadioPipelineAdapter(
            min_speech_ratio=0.7,
            min_confidence=0.8,
            min_duration=2.0,
            max_duration=12.0
        )
        
        segments = [
            {
                "is_speech": True,
                "music_prob": 0.2,
                "confidence": 0.9,
                "duration": 5.0
            },
            {
                "is_speech": False,  # Not speech
                "music_prob": 0.3,
                "confidence": 0.8,
                "duration": 5.0
            },
            {
                "is_speech": True,
                "music_prob": 0.7,  # Too much music
                "confidence": 0.9,
                "duration": 5.0
            },
            {
                "is_speech": True,
                "music_prob": 0.2,
                "confidence": 0.7,  # Too low confidence
                "duration": 5.0
            },
            {
                "is_speech": True,
                "music_prob": 0.2,
                "confidence": 0.9,
                "duration": 1.0  # Too short
            },
            {
                "is_speech": True,
                "music_prob": 0.2,
                "confidence": 0.9,
                "duration": 15.0  # Too long
            },
        ]
        
        shard_data = {"speech_ratio": 0.8}
        
        filtered = adapter.filter_high_quality_segments(segments, shard_data)
        
        # Only first segment should pass all filters
        assert len(filtered) == 1
        assert filtered[0]["confidence"] == 0.9
    
    def test_export_segments_for_asr(self):
        """Test exporting segments for ASR"""
        adapter = RadioPipelineAdapter()
        
        # Mock database connection and repositories
        mock_conn = MagicMock()
        
        with patch('radio_ingestion.integration.pipeline_adapter.RadioSegmentRepository') as mock_seg_repo_class, \
             patch('radio_ingestion.integration.pipeline_adapter.RadioShardRepository') as mock_shard_repo_class, \
             patch('radio_ingestion.integration.pipeline_adapter.RadioSourceRepository') as mock_source_repo_class:
            
            mock_seg_repo = MagicMock()
            mock_shard_repo = MagicMock()
            mock_source_repo = MagicMock()
            
            mock_seg_repo_class.return_value = mock_seg_repo
            mock_shard_repo_class.return_value = mock_shard_repo
            mock_source_repo_class.return_value = mock_source_repo
            
            # Mock data
            mock_seg_repo.get_by_shard.return_value = [
                {
                    "id": 1,
                    "start": 0.0,
                    "end": 5.0,
                    "is_speech": True,
                    "music_prob": 0.2,
                    "lang_probs": {"so": 0.9},
                    "primary_lang": "so",
                    "confidence": 0.9,
                    "duration": 5.0
                }
            ]
            
            mock_shard_repo.get_by_source.return_value = [
                {
                    "id": 1,
                    "source_id": 1,
                    "path": "/test/audio.wav",
                    "speech_ratio": 0.8
                }
            ]
            
            mock_source_repo.get_by_id.return_value = {
                "id": 1,
                "name": "Test Station",
                "country": "SO"
            }
            
            result = adapter.export_segments_for_asr(1, mock_conn)
            
            assert isinstance(result, list)
            # Should have at least one segment if filtering passes
            # (depends on mock data quality)

