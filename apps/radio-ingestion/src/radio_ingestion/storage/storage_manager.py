"""Unified storage manager coordinating S3 upload and cleanup"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from radio_ingestion.storage.cleanup import FileCleanup, create_cleanup
from radio_ingestion.storage.radio_repositories import RadioShardRepository
from radio_ingestion.storage.s3_uploader import LocalStaging, S3Uploader, create_uploader

logger = structlog.get_logger(__name__)


class StorageManager:
    """
    Manages storage operations: upload to S3 (or stage locally), update DB, cleanup.
    """

    def __init__(
        self,
        s3_uploader: Optional[S3Uploader] = None,
        local_staging: Optional[LocalStaging] = None,
        cleanup: Optional[FileCleanup] = None,
        db_conn=None,
    ):
        """
        Initialize storage manager.

        Args:
            s3_uploader: S3 uploader instance (None if S3 disabled)
            local_staging: Local staging instance (used when S3 disabled)
            cleanup: File cleanup instance
            db_conn: Database connection for updating shard records
        """
        self.s3_uploader = s3_uploader
        self.local_staging = local_staging
        self.cleanup = cleanup
        self.db_conn = db_conn

        logger.info(
            "Storage manager initialized",
            s3_enabled=s3_uploader is not None and s3_uploader.enabled,
            local_staging_enabled=local_staging is not None,
            cleanup_enabled=cleanup is not None and cleanup.cleanup_enabled,
        )

    def process_shard(
        self,
        shard_id: int,
        local_path: str,
        country: str,
        station_name: str,
        shard_timestamp: Optional[datetime] = None,
        cleanup_after_upload: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a shard: upload to S3 or stage locally, update DB, optionally cleanup.

        Args:
            shard_id: Shard database ID
            local_path: Local file path
            country: Country code
            station_name: Station name
            shard_timestamp: Timestamp for path organization (defaults to now)
            cleanup_after_upload: Whether to delete local file after upload

        Returns:
            Dictionary with:
                - success: Whether processing succeeded
                - storage_url: S3 URL or local staging path
                - storage_type: 's3' or 'local'
                - cleanup_done: Whether cleanup was performed
                - error: Error message if failed
        """
        if shard_timestamp is None:
            shard_timestamp = datetime.now(timezone.utc)

        result = {
            "success": False,
            "storage_url": None,
            "storage_type": None,
            "cleanup_done": False,
            "error": None,
        }

        try:
            # Try S3 upload first if enabled
            if self.s3_uploader and self.s3_uploader.enabled:
                s3_url = self.s3_uploader.upload_file(
                    local_path=local_path,
                    country=country,
                    station_name=station_name,
                    metadata={
                        "shard_id": str(shard_id),
                        "station": station_name,
                        "country": country,
                    },
                )

                if s3_url:
                    result["success"] = True
                    result["storage_url"] = s3_url
                    result["storage_type"] = "s3"

                    # Update database
                    if self.db_conn:
                        shard_repo = RadioShardRepository(self.db_conn)
                        shard_repo.update_s3_url(shard_id, s3_url)
                        logger.info(
                            "Shard uploaded to S3, DB updated", shard_id=shard_id, s3_url=s3_url
                        )

                    # Cleanup if requested
                    if cleanup_after_upload and self.cleanup:
                        cleanup_done = self.cleanup.cleanup_file(
                            local_path, require_s3_url=True, s3_url=s3_url
                        )
                        result["cleanup_done"] = cleanup_done

                    return result

            # Fallback to local staging
            if self.local_staging:
                staged_path = self.local_staging.stage_file(
                    local_path=local_path,
                    country=country,
                    station_name=station_name,
                    date=shard_timestamp,
                )

                if staged_path:
                    result["success"] = True
                    result["storage_url"] = staged_path
                    result["storage_type"] = "local"

                    # Update database (store local staging path)
                    if self.db_conn:
                        shard_repo = RadioShardRepository(self.db_conn)
                        # Store local staging path in s3_url field for now
                        # (could add separate local_url field later if needed)
                        shard_repo.update_s3_url(shard_id, staged_path)
                        logger.info(
                            "Shard staged locally, DB updated",
                            shard_id=shard_id,
                            staged_path=staged_path,
                        )

                    # Don't cleanup local files if staging locally
                    # (original file might still be needed)

                    return result

            # No storage backend available
            result["error"] = (
                "No storage backend available (S3 disabled and local staging not configured)"
            )
            logger.warning("No storage backend available", shard_id=shard_id)
            return result

        except Exception as e:
            result["error"] = str(e)
            logger.error(
                "Shard storage processing failed",
                shard_id=shard_id,
                local_path=local_path,
                error=str(e),
            )
            return result

    def batch_process_shards(
        self, shards: List[Dict[str, Any]], cleanup_after_upload: bool = True
    ) -> Dict[int, Dict[str, Any]]:
        """
        Process multiple shards in batch.

        Args:
            shards: List of shard dictionaries with:
                - shard_id: Database ID
                - local_path: Local file path
                - country: Country code
                - station_name: Station name
                - timestamp: Optional timestamp
            cleanup_after_upload: Whether to cleanup after upload

        Returns:
            Dictionary mapping shard_id to processing results
        """
        results = {}

        for shard in shards:
            shard_id = shard["shard_id"]

            result = self.process_shard(
                shard_id=shard_id,
                local_path=shard["local_path"],
                country=shard["country"],
                station_name=shard["station_name"],
                shard_timestamp=shard.get("timestamp"),
                cleanup_after_upload=cleanup_after_upload,
            )

            results[shard_id] = result

        success_count = sum(1 for r in results.values() if r["success"])
        logger.info("Batch processing complete", total=len(shards), successful=success_count)

        return results


def create_storage_manager(
    config, db_conn=None, staging_dir: Optional[str] = None
) -> StorageManager:
    """
    Factory function to create storage manager from config.

    Args:
        config: RadioIngestionConfig instance
        db_conn: Database connection (optional)
        staging_dir: Local staging directory (defaults to capture_dir/staging)

    Returns:
        StorageManager instance
    """
    # Create S3 uploader if enabled
    s3_uploader = create_uploader(config) if config.s3_enabled and config.s3_bucket else None

    # Create local staging (always available as fallback)
    if staging_dir is None:
        staging_dir = str(Path(config.capture_dir) / "staging")

    local_staging = LocalStaging(staging_dir=staging_dir)

    # Create cleanup
    cleanup = create_cleanup(cleanup_enabled=True, retention_days=7)

    return StorageManager(
        s3_uploader=s3_uploader, local_staging=local_staging, cleanup=cleanup, db_conn=db_conn
    )
