"""
Integration tests for Curator components.
Tests actual functionality to identify issues.
"""

import os
import tempfile
from typing import List

import pytest


def test_curator_imports():
    """Test that all curator modules can be imported."""
    try:
        from curator.deduplicator import Deduplicator
        from curator.policy_gates import PolicyGate
        from curator.processor import CuratorProcessor
        from curator.scorer import SegmentScorer
        from curator.snapshot import DatasetSnapshot

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import curator modules: {e}")


def test_scorer_initialization():
    """Test SegmentScorer initialization and basic scoring."""
    try:
        from curator.scorer import SegmentScorer
        from mumbl_data_contracts.segments import AudioSegment, Labels, SourceRef, TextSegment

        scorer = SegmentScorer()
        assert scorer is not None

        # Test text segment scoring
        text_segment = TextSegment(
            text="This is a test sentence with proper structure.",
            lang="en",
            labels=Labels(
                is_dialogue=False,
                topic="general",
                register_type="neutral",
            ),
            source_ref=SourceRef(doc_id="test_doc", start=0, end=50),
        )

        score = scorer.score_text_segment(text_segment)

        assert score is not None
        assert score.clarity is not None
        assert score.validity is not None
        assert score.shape is not None
        assert score.total is not None
        assert 0 <= score.clarity <= 100
        assert 0 <= score.total <= 100

        # Test audio segment scoring
        audio_segment = AudioSegment(
            audio_file="test.wav",
            start=0.0,
            end=5.0,
            speaker_id="spk_1",
            transcript_text="This is a test.",
            lang="en",
            alignment_confidence=0.9,
            diarization_confidence=0.85,
        )

        score = scorer.score_audio_segment(audio_segment)

        assert score is not None
        assert score.clarity is not None
        assert score.alignment is not None
        assert score.diarization is not None
        assert score.transcript_accuracy is not None
        assert score.validity is not None
        assert score.shape is not None
        assert score.total is not None
        assert all(
            0 <= getattr(score, dim) <= 100
            for dim in [
                "clarity",
                "alignment",
                "diarization",
                "transcript_accuracy",
                "validity",
                "shape",
                "total",
            ]
        )

    except Exception as e:
        pytest.fail(f"Scorer test failed: {e}")


def test_deduplicator_basic():
    """Test deduplicator with simple cases."""
    try:
        from curator.deduplicator import Deduplicator
        from mumbl_data_contracts.segments import Labels, SourceRef, TextSegment

        deduplicator = Deduplicator()

        # Create duplicate text segments
        text_segments = [
            TextSegment(
                text="Hello world",
                lang="en",
                labels=Labels(is_dialogue=False),
                source_ref=SourceRef(doc_id="doc1", start=0, end=11),
            ),
            TextSegment(
                text="Hello world",  # Duplicate
                lang="en",
                labels=Labels(is_dialogue=False),
                source_ref=SourceRef(doc_id="doc2", start=0, end=11),
            ),
            TextSegment(
                text="Different text",
                lang="en",
                labels=Labels(is_dialogue=False),
                source_ref=SourceRef(doc_id="doc3", start=0, end=13),
            ),
        ]

        # Find exact duplicates
        result = deduplicator.find_exact_duplicates(text_segments=text_segments)

        assert "text_duplicates" in result
        assert len(result["text_duplicates"]) > 0  # Should find the duplicate

    except Exception as e:
        pytest.fail(f"Deduplicator test failed: {e}")


def test_policy_gates():
    """Test policy gates filtering."""
    try:
        from curator.policy_gates import PolicyGate
        from curator.scorer import SegmentScorer
        from mumbl_data_contracts.segments import Labels, SourceRef, TextSegment

        policy_gate = PolicyGate(min_training_score=70.0, min_learner_score=90.0)
        scorer = SegmentScorer()

        # Create segments with different quality
        segments = [
            TextSegment(
                text="High quality text with proper structure and clear meaning.",
                lang="en",
                labels=Labels(is_dialogue=False, topic="test", register_type="formal"),
                source_ref=SourceRef(doc_id="doc1", start=0, end=60),
            ),
            TextSegment(
                text="Low quality",
                lang="en",
                labels=Labels(is_dialogue=False),
                source_ref=SourceRef(doc_id="doc2", start=0, end=11),
            ),
        ]

        # Score segments
        scored = [(seg, scorer.score_text_segment(seg)) for seg in segments]

        # Apply thresholds
        eligible = policy_gate.apply_thresholds(scored, min_score=70.0)

        assert len(eligible) <= len(scored)
        assert all(score.total >= 70.0 for seg, score in eligible)

    except Exception as e:
        pytest.fail(f"Policy gates test failed: {e}")


def test_snapshot_creation():
    """Test dataset snapshot creation."""
    try:
        from curator.snapshot import DatasetSnapshot

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot = DatasetSnapshot(output_dir=tmpdir)

            segment_ids = [1, 2, 3, 4, 5]
            result = snapshot.create_snapshot(
                segment_ids=segment_ids,
                language="en",
                dialect="en-US",
                version="1.0.0",
                metadata={"test": True},
            )

            assert result["version"] == "1.0.0"
            assert result["language"] == "en"
            assert result["dialect"] == "en-US"
            assert result["segment_count"] == len(segment_ids)
            assert "snapshot_path" in result
            assert os.path.exists(result["snapshot_path"])

    except Exception as e:
        pytest.fail(f"Snapshot test failed: {e}")


def test_curator_processor_integration():
    """Test full curator processor pipeline."""
    try:
        from curator.processor import CuratorProcessor
        from mumbl_data_contracts.segments import Labels, SourceRef, TextSegment

        processor = CuratorProcessor()

        # Create test segments
        text_segments = [
            TextSegment(
                text="This is a good quality segment for training.",
                lang="en",
                labels=Labels(is_dialogue=False, topic="test", register_type="neutral"),
                source_ref=SourceRef(doc_id="doc1", start=0, end=50),
            ),
            TextSegment(
                text="Another good segment with proper structure.",
                lang="en",
                labels=Labels(is_dialogue=False, topic="test"),
                source_ref=SourceRef(doc_id="doc2", start=0, end=45),
            ),
        ]

        # Process segments
        result = processor.process_segments(
            text_segments=text_segments,
            audio_segments=None,
            batch_id="test_batch",
            language="en",
            dialect="en-US",
            target="training",
        )

        assert "snapshot" in result
        assert "stats" in result
        assert result["stats"]["text_segments_scored"] == len(text_segments)

    except Exception as e:
        pytest.fail(f"Curator processor test failed: {e}")
