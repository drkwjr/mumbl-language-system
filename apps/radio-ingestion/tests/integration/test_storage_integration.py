"""Integration tests for storage module"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from mumbl_storage.db import DatabaseConfig, get_connection
from radio_ingestion.config import RadioIngestionConfig
from radio_ingestion.storage.cleanup import FileCleanup
from radio_ingestion.storage.radio_repositories import RadioShardRepository
from radio_ingestion.storage.s3_uploader import LocalStaging
from radio_ingestion.storage.storage_manager import StorageManager, create_storage_manager


@pytest.mark.integration
def test_local_staging_and_db_update(tmp_path):
    """Test local staging and database update"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    staging = LocalStaging(staging_dir=str(tmp_path / "staging"))

    # Create test file
    test_file = tmp_path / "test_shard.wav"
    test_file.write_bytes(b"fake audio data")

    # Stage file
    staged_path = staging.stage_file(
        local_path=str(test_file),
        country="SO",
        station_name="Test Radio",
        date=datetime.now(timezone.utc),
    )

    assert staged_path is not None
    assert Path(staged_path).exists()

    # Test database update (would need actual shard ID)
    with get_connection() as conn:
        shard_repo = RadioShardRepository(conn)

        # Get a test shard to update
        from radio_ingestion.storage.radio_repositories import RadioSourceRepository

        source_repo = RadioSourceRepository(conn)
        sources = source_repo.list_active()

        if sources:
            test_source = sources[0]
            shards = shard_repo.get_by_source(test_source["id"], limit=1)

            if shards:
                shard_id = shards[0]["id"]

                # Update with staging path
                shard_repo.update_s3_url(shard_id, staged_path)

                # Verify update
                updated_shards = shard_repo.get_by_source(test_source["id"], limit=1)
                assert updated_shards[0]["s3_url"] == staged_path


@pytest.mark.integration
def test_cleanup_with_retention(tmp_path):
    """Test cleanup with retention policy"""
    cleanup = FileCleanup(cleanup_enabled=True, retention_days=0)  # Delete immediately

    # Create test files
    old_file = tmp_path / "old.wav"
    old_file.write_bytes(b"old data")

    new_file = tmp_path / "new.wav"
    new_file.write_bytes(b"new data")

    # Cleanup old file
    deleted = cleanup.cleanup_old_files(str(tmp_path), extension=".wav", older_than_days=0)

    # Both files should be deleted (older_than_days=0 means any age)
    assert len(deleted) >= 1
    assert not old_file.exists()


@pytest.mark.integration
def test_storage_manager_local_mode(tmp_path):
    """Test storage manager in local-only mode"""
    # Create config with S3 disabled
    config = RadioIngestionConfig.from_env()
    config.s3_enabled = False
    config.capture_dir = str(tmp_path)

    # Create storage manager
    manager = create_storage_manager(config, staging_dir=str(tmp_path / "staging"))

    # Create test file
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"test audio")

    result = manager.process_shard(
        shard_id=999,  # Mock ID
        local_path=str(test_file),
        country="SO",
        station_name="Test Station",
    )

    assert result["success"] is True
    assert result["storage_type"] == "local"
    assert result["storage_url"] is not None


@pytest.mark.integration
def test_batch_process_shards(tmp_path):
    """Test batch processing of shards"""
    staging = LocalStaging(staging_dir=str(tmp_path / "staging"))
    cleanup = FileCleanup(cleanup_enabled=False)  # Don't cleanup in test

    manager = StorageManager(s3_uploader=None, local_staging=staging, cleanup=cleanup)

    # Create multiple test files
    shards = []
    for i in range(3):
        test_file = tmp_path / f"test_{i}.wav"
        test_file.write_bytes(f"test data {i}".encode())

        shards.append(
            {
                "shard_id": i + 1,
                "local_path": str(test_file),
                "country": "SO",
                "station_name": f"Station {i}",
                "timestamp": datetime.now(timezone.utc),
            }
        )

    results = manager.batch_process_shards(shards, cleanup_after_upload=False)

    assert len(results) == 3
    assert all(r["success"] for r in results.values())
    assert all(r["storage_type"] == "local" for r in results.values())
