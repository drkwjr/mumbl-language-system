"""Unit tests for storage module"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from radio_ingestion.storage.cleanup import FileCleanup
from radio_ingestion.storage.s3_uploader import LocalStaging, S3Uploader
from radio_ingestion.storage.storage_manager import StorageManager


class TestS3Uploader:
    """Test S3 uploader"""

    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        with patch("boto3.client") as mock_client:
            mock_s3 = MagicMock()
            mock_client.return_value = mock_s3
            mock_s3.head_bucket.return_value = None  # Success
            yield mock_s3

    def test_init_disabled(self):
        """Test uploader initialization when disabled"""
        uploader = S3Uploader(bucket="test-bucket", enabled=False)
        assert uploader.enabled is False
        assert uploader.client is None

    @patch("boto3.client")
    def test_init_enabled(self, mock_client):
        """Test uploader initialization when enabled"""
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = None

        uploader = S3Uploader(bucket="test-bucket", enabled=True)
        assert uploader.enabled is True
        assert uploader.client is not None

    def test_generate_s3_path(self):
        """Test S3 path generation"""
        uploader = S3Uploader(bucket="test", enabled=False)

        path = uploader.generate_s3_path(
            country="SO", station_name="Radio Muqdisho", filename="stream_20250101_120000.wav"
        )

        assert "SO" in path
        assert "radio_muqdisho" in path.lower()
        assert "stream_20250101_120000.wav" in path

    def test_sanitize_for_path(self):
        """Test path sanitization"""
        uploader = S3Uploader(bucket="test", enabled=False)

        sanitized = uploader._sanitize_for_path("Radio Muqdisho / FM")
        assert "radio_muqdisho" in sanitized.lower()
        assert "/" not in sanitized
        assert "__" not in sanitized

    @patch("boto3.client")
    def test_upload_file_success(self, mock_client, tmp_path):
        """Test successful file upload"""
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = None
        mock_s3.upload_file.return_value = None  # Success

        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"test audio data")

        uploader = S3Uploader(bucket="test-bucket", enabled=True)

        s3_url = uploader.upload_file(
            local_path=str(test_file), country="SO", station_name="Test Station"
        )

        assert s3_url is not None
        assert "test-bucket" in s3_url
        mock_s3.upload_file.assert_called_once()

    @patch("boto3.client")
    def test_upload_file_not_found(self, mock_client):
        """Test upload when file doesn't exist"""
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = None

        uploader = S3Uploader(bucket="test-bucket", enabled=True)

        s3_url = uploader.upload_file(
            local_path="/nonexistent/file.wav", country="SO", station_name="Test"
        )

        assert s3_url is None


class TestLocalStaging:
    """Test local staging"""

    def test_init(self, tmp_path):
        """Test staging initialization"""
        staging = LocalStaging(staging_dir=str(tmp_path / "staging"))
        assert staging.staging_dir.exists()

    def test_stage_file(self, tmp_path):
        """Test staging a file"""
        staging = LocalStaging(staging_dir=str(tmp_path / "staging"))

        source_file = tmp_path / "source.wav"
        source_file.write_bytes(b"test data")

        staged_path = staging.stage_file(
            local_path=str(source_file), country="SO", station_name="Test Station"
        )

        assert staged_path is not None
        assert Path(staged_path).exists()
        assert "SO" in staged_path
        assert "test_station" in staged_path.lower()

    def test_stage_file_not_found(self, tmp_path):
        """Test staging when file doesn't exist"""
        staging = LocalStaging(staging_dir=str(tmp_path / "staging"))

        staged_path = staging.stage_file(
            local_path="/nonexistent/file.wav", country="SO", station_name="Test"
        )

        assert staged_path is None


class TestFileCleanup:
    """Test file cleanup"""

    def test_init(self):
        """Test cleanup initialization"""
        cleanup = FileCleanup(cleanup_enabled=True, retention_days=7)
        assert cleanup.cleanup_enabled is True
        assert cleanup.retention_days == 7

    def test_cleanup_file_enabled(self, tmp_path):
        """Test file cleanup when enabled"""
        cleanup = FileCleanup(cleanup_enabled=True)

        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"test data")

        result = cleanup.cleanup_file(str(test_file), require_s3_url=False)

        assert result is True
        assert not test_file.exists()

    def test_cleanup_file_disabled(self, tmp_path):
        """Test cleanup when disabled"""
        cleanup = FileCleanup(cleanup_enabled=False)

        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"test data")

        result = cleanup.cleanup_file(str(test_file), require_s3_url=False)

        assert result is False
        assert test_file.exists()  # File should still exist

    def test_cleanup_file_requires_s3(self, tmp_path):
        """Test cleanup requires S3 URL"""
        cleanup = FileCleanup(cleanup_enabled=True)

        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"test data")

        result = cleanup.cleanup_file(str(test_file), require_s3_url=True, s3_url=None)

        assert result is False
        assert test_file.exists()  # Not deleted without S3 URL

    def test_cleanup_old_files(self, tmp_path):
        """Test cleanup of old files"""
        cleanup = FileCleanup(cleanup_enabled=True, retention_days=1)

        # Create old file (mock old timestamp)
        old_file = tmp_path / "old.wav"
        old_file.write_bytes(b"old data")

        # Set file mtime to 2 days ago
        import time

        old_time = time.time() - (2 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))

        # Create new file
        new_file = tmp_path / "new.wav"
        new_file.write_bytes(b"new data")

        deleted = cleanup.cleanup_old_files(str(tmp_path), extension=".wav", older_than_days=1)

        assert len(deleted) == 1
        assert str(old_file) in deleted
        assert not old_file.exists()
        assert new_file.exists()  # New file should remain


class TestStorageManager:
    """Test storage manager"""

    def test_process_shard_s3(self, tmp_path):
        """Test processing shard with S3 upload"""
        # Mock S3 uploader
        mock_uploader = MagicMock()
        mock_uploader.enabled = True
        mock_uploader.upload_file.return_value = "s3://bucket/test.wav"

        # Mock cleanup
        mock_cleanup = MagicMock()
        mock_cleanup.cleanup_enabled = True
        mock_cleanup.cleanup_file.return_value = True

        manager = StorageManager(s3_uploader=mock_uploader, cleanup=mock_cleanup)

        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"test data")

        result = manager.process_shard(
            shard_id=1, local_path=str(test_file), country="SO", station_name="Test Station"
        )

        assert result["success"] is True
        assert result["storage_type"] == "s3"
        assert "s3://" in result["storage_url"]

    def test_process_shard_local_staging(self, tmp_path):
        """Test processing shard with local staging"""
        # No S3 uploader
        staging = LocalStaging(staging_dir=str(tmp_path / "staging"))

        manager = StorageManager(s3_uploader=None, local_staging=staging)

        source_file = tmp_path / "source.wav"
        source_file.write_bytes(b"test data")

        result = manager.process_shard(
            shard_id=1, local_path=str(source_file), country="SO", station_name="Test Station"
        )

        assert result["success"] is True
        assert result["storage_type"] == "local"
        assert Path(result["storage_url"]).exists()
