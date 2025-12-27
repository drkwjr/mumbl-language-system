"""Cleanup utilities for removing processed files"""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class FileCleanup:
    """Manage cleanup of processed audio files"""
    
    def __init__(
        self,
        cleanup_enabled: bool = True,
        retention_days: int = 7
    ):
        """
        Initialize file cleanup.
        
        Args:
            cleanup_enabled: Whether cleanup is enabled
            retention_days: Keep files for this many days before cleanup
        """
        self.cleanup_enabled = cleanup_enabled
        self.retention_days = retention_days
        
        logger.info(
            "File cleanup initialized",
            cleanup_enabled=cleanup_enabled,
            retention_days=retention_days
        )
    
    def cleanup_file(
        self,
        file_path: str,
        require_s3_url: bool = True,
        s3_url: Optional[str] = None
    ) -> bool:
        """
        Clean up a file after successful upload.
        
        Args:
            file_path: Local file path to delete
            require_s3_url: Only delete if S3 URL exists (default: True)
            s3_url: S3 URL if uploaded
        
        Returns:
            True if file was deleted, False otherwise
        """
        if not self.cleanup_enabled:
            logger.debug("Cleanup disabled, skipping file deletion", file_path=file_path)
            return False
        
        if require_s3_url and not s3_url:
            logger.debug(
                "Skipping cleanup (no S3 URL)",
                file_path=file_path,
                require_s3_url=require_s3_url
            )
            return False
        
        path = Path(file_path)
        if not path.exists():
            logger.debug("File does not exist, nothing to clean", file_path=file_path)
            return False
        
        try:
            file_size = path.stat().st_size
            path.unlink()
            
            logger.info(
                "File cleaned up",
                file_path=file_path,
                file_size=file_size,
                s3_url=s3_url
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to cleanup file",
                file_path=file_path,
                error=str(e)
            )
            return False
    
    def cleanup_old_files(
        self,
        directory: str,
        extension: Optional[str] = ".wav",
        older_than_days: Optional[int] = None
    ) -> List[str]:
        """
        Clean up old files in a directory.
        
        Args:
            directory: Directory to clean
            extension: File extension to match (None for all files)
            older_than_days: Delete files older than this (uses retention_days if None)
        
        Returns:
            List of deleted file paths
        """
        if not self.cleanup_enabled:
            return []
        
        if older_than_days is None:
            older_than_days = self.retention_days
        
        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning("Cleanup directory does not exist", directory=directory)
            return []
        
        deleted_files = []
        
        try:
            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                if extension and not file_path.suffix.lower() == extension.lower():
                    continue
                
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        
                        logger.debug(
                            "Deleted old file",
                            file_path=str(file_path),
                            age_days=(datetime.now() - file_mtime).days
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to delete old file",
                            file_path=str(file_path),
                            error=str(e)
                        )
            
            if deleted_files:
                logger.info(
                    "Cleanup completed",
                    directory=directory,
                    deleted_count=len(deleted_files),
                    older_than_days=older_than_days
                )
            
            return deleted_files
            
        except Exception as e:
            logger.error(
                "Cleanup directory scan failed",
                directory=directory,
                error=str(e)
            )
            return []
    
    def cleanup_shard_files(
        self,
        shard_paths: List[str],
        s3_urls: Optional[List[Optional[str]]] = None,
        require_s3: bool = True
    ) -> Dict[str, bool]:
        """
        Clean up multiple shard files.
        
        Args:
            shard_paths: List of shard file paths
            s3_urls: Optional list of S3 URLs (must match shard_paths length)
            require_s3: Only delete if S3 URL exists
        
        Returns:
            Dictionary mapping file paths to deletion success status
        """
        results = {}
        
        if s3_urls is None:
            s3_urls = [None] * len(shard_paths)
        
        for shard_path, s3_url in zip(shard_paths, s3_urls):
            success = self.cleanup_file(
                shard_path,
                require_s3_url=require_s3,
                s3_url=s3_url
            )
            results[shard_path] = success
        
        deleted_count = sum(1 for success in results.values() if success)
        
        if deleted_count > 0:
            logger.info(
                "Batch cleanup completed",
                total=len(shard_paths),
                deleted=deleted_count
            )
        
        return results


def create_cleanup(
    cleanup_enabled: bool = True,
    retention_days: int = 7
) -> FileCleanup:
    """Factory function to create cleanup instance"""
    return FileCleanup(cleanup_enabled=cleanup_enabled, retention_days=retention_days)

