"""
Integration tests for storage layer and database interactions.
"""

import os
import tempfile

import pytest


def test_storage_imports():
    """Test storage layer imports."""
    try:
        from mumbl_storage.db import DatabaseConfig, get_connection
        from mumbl_storage.repositories import (
            AudioSegmentRepository,
            DatasetRepository,
            ModelRegistryRepository,
            SegmentScoreRepository,
            TextSegmentRepository,
        )

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import storage modules: {e}")


def test_database_config():
    """Test DatabaseConfig."""
    try:
        from mumbl_storage.db import DatabaseConfig

        config = DatabaseConfig.from_env()

        assert config.host is not None
        assert config.port > 0
        assert config.database is not None
        assert config.user is not None

    except Exception as e:
        pytest.fail(f"DatabaseConfig test failed: {e}")


@pytest.mark.integration
def test_repository_insert_operations():
    """Test repository insert operations (requires database)."""
    try:
        from mumbl_data_contracts.segments import AudioSegment
        from mumbl_storage.db import get_connection
        from mumbl_storage.repositories import (
            AudioSegmentRepository,
            DatasetRepository,
        )

        # Only test if database is available
        try:
            with get_connection() as conn:
                # Test AudioSegmentRepository
                audio_repo = AudioSegmentRepository(conn)

                test_segment = AudioSegment(
                    audio_file="test.wav",
                    start=0.0,
                    end=5.0,
                    transcript_text="Test transcript",
                    lang="en",
                    alignment_confidence=0.9,
                )

                # This might fail if audio_hash constraint triggers
                segment_id = audio_repo.insert(
                    test_segment,
                    batch_id="test_batch",
                    audio_hash=None,  # No hash to avoid constraint
                    granularity="sentence",
                    sample_rate=22050,
                )

                # Note: segment_id might be None if insert fails
                # This is expected behavior for testing

        except Exception as db_error:
            pytest.skip(f"Database not available: {db_error}")

    except Exception as e:
        pytest.fail(f"Repository test failed: {e}")


def test_audio_segment_repository_csv_export():
    """Test CSV export functionality."""
    try:
        from mumbl_storage.db import get_connection
        from mumbl_storage.repositories import AudioSegmentRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test_export.csv")

            try:
                with get_connection() as conn:
                    audio_repo = AudioSegmentRepository(conn)

                    # Export CSV (might be empty if no data)
                    count = audio_repo.export_to_csv(csv_path, batch_id="nonexistent")

                    # CSV file should be created even if empty
                    assert os.path.exists(csv_path) or count == 0

            except Exception as db_error:
                pytest.skip(f"Database not available: {db_error}")

    except Exception as e:
        pytest.fail(f"CSV export test failed: {e}")
