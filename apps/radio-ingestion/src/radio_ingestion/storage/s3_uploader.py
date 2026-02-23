"""S3 upload and storage management for radio shards"""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Optional S3 support
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning(
        "boto3 not available. Install with: pip install boto3. " "S3 uploads will be disabled."
    )


class S3Uploader:
    """
    Upload audio files to S3 with structured path pattern.

    Path pattern: s3://{bucket}/{country}/{station}/{date}/{hour}/{filename}
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize S3 uploader.

        Args:
            bucket: S3 bucket name
            region: AWS region
            access_key_id: AWS access key (uses env or IAM role if None)
            secret_access_key: AWS secret key (uses env or IAM role if None)
            enabled: Whether S3 uploads are enabled (default: True)
        """
        self.bucket = bucket
        self.region = region
        self.enabled = enabled and BOTO3_AVAILABLE

        if not self.enabled:
            logger.info("S3 uploader disabled", reason="boto3 not available or explicitly disabled")
            self.client = None
            return

        # Initialize S3 client
        try:
            if access_key_id and secret_access_key:
                self.client = boto3.client(
                    "s3",
                    region_name=region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                )
            else:
                # Use default credentials (env vars, IAM role, etc.)
                self.client = boto3.client("s3", region_name=region)

            # Test connection
            self.client.head_bucket(Bucket=bucket)

            logger.info("S3 uploader initialized", bucket=bucket, region=region)
        except Exception as e:
            logger.error("Failed to initialize S3 client", bucket=bucket, error=str(e))
            self.enabled = False
            self.client = None

    def generate_s3_path(
        self, country: str, station_name: str, filename: str, date: Optional[datetime] = None
    ) -> str:
        """
        Generate S3 path for audio file.

        Args:
            country: Country code (e.g., 'SO' for Somalia)
            station_name: Station name (sanitized)
            filename: Original filename
            date: Date for path (defaults to now)

        Returns:
            S3 key (path within bucket)
        """
        if date is None:
            date = datetime.now(timezone.utc)

        # Sanitize station name for path
        safe_station = self._sanitize_for_path(station_name)

        # Path: {country}/{station}/{YYYY-MM-DD}/{HH}/{filename}
        date_str = date.strftime("%Y-%m-%d")
        hour_str = date.strftime("%H")

        s3_key = f"{country}/{safe_station}/{date_str}/{hour_str}/{filename}"

        return s3_key

    def _sanitize_for_path(self, name: str) -> str:
        """Sanitize name for use in file path"""
        # Replace spaces and special chars with underscores
        sanitized = name.lower()
        sanitized = sanitized.replace(" ", "_")
        sanitized = sanitized.replace("/", "_")
        sanitized = "".join(c if c.isalnum() or c in "._-" else "_" for c in sanitized)
        # Remove multiple underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_")

    def upload_file(
        self,
        local_path: str,
        country: str,
        station_name: str,
        metadata: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> Optional[str]:
        """
        Upload file to S3.

        Args:
            local_path: Local file path
            country: Country code
            station_name: Station name
            metadata: Optional metadata to attach
            max_retries: Maximum retry attempts

        Returns:
            S3 URL if successful, None otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("S3 upload skipped (disabled)", local_path=local_path)
            return None

        if not os.path.exists(local_path):
            logger.error("File not found for upload", local_path=local_path)
            return None

        file_path = Path(local_path)
        filename = file_path.name

        # Generate S3 key
        s3_key = self.generate_s3_path(country, station_name, filename)

        # Upload with retries
        for attempt in range(max_retries):
            try:
                logger.info(
                    "Uploading file to S3",
                    local_path=local_path,
                    s3_key=s3_key,
                    bucket=self.bucket,
                    attempt=attempt + 1,
                )

                extra_args = {}
                if metadata:
                    extra_args["Metadata"] = metadata

                # Upload file
                self.client.upload_file(local_path, self.bucket, s3_key, ExtraArgs=extra_args)

                # Generate S3 URL
                s3_url = f"s3://{self.bucket}/{s3_key}"

                logger.info(
                    "File uploaded successfully", s3_url=s3_url, file_size=file_path.stat().st_size
                )

                return s3_url

            except (ClientError, BotoCoreError) as e:
                logger.warning(
                    "S3 upload failed, retrying",
                    local_path=local_path,
                    s3_key=s3_key,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )

                if attempt == max_retries - 1:
                    logger.error(
                        "S3 upload failed after retries",
                        local_path=local_path,
                        s3_key=s3_key,
                        error=str(e),
                    )
                    return None

        return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3.

        Args:
            s3_key: S3 key (path within bucket)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info("File deleted from S3", s3_key=s3_key)
            return True
        except Exception as e:
            logger.error("Failed to delete from S3", s3_key=s3_key, error=str(e))
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3.

        Args:
            s3_key: S3 key (path within bucket)

        Returns:
            True if file exists, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.warning("Error checking S3 file existence", s3_key=s3_key, error=str(e))
            return False


class LocalStaging:
    """
    Local staging area for files when S3 is disabled.

    Mirrors S3 directory structure for easy migration later.
    """

    def __init__(self, staging_dir: str):
        """
        Initialize local staging.

        Args:
            staging_dir: Base directory for staged files
        """
        self.staging_dir = Path(staging_dir)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Local staging initialized", staging_dir=str(self.staging_dir))

    def stage_file(
        self, local_path: str, country: str, station_name: str, date: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Stage file locally (copy to staging directory).

        Args:
            local_path: Source file path
            country: Country code
            station_name: Station name
            date: Date for path structure

        Returns:
            Staged file path or None on error
        """
        if date is None:
            date = datetime.now(timezone.utc)

        file_path = Path(local_path)
        if not file_path.exists():
            logger.error("File not found for staging", local_path=local_path)
            return None

        # Sanitize station name
        sanitized_station = self._sanitize_for_path(station_name)

        # Create staging path: {staging_dir}/{country}/{station}/{YYYY-MM-DD}/{HH}/{filename}
        date_str = date.strftime("%Y-%m-%d")
        hour_str = date.strftime("%H")

        staging_path = (
            self.staging_dir / country / sanitized_station / date_str / hour_str / file_path.name
        )
        staging_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Copy file
            import shutil

            shutil.copy2(local_path, staging_path)

            logger.info(
                "File staged locally", local_path=local_path, staging_path=str(staging_path)
            )

            return str(staging_path)

        except Exception as e:
            logger.error(
                "Failed to stage file locally",
                local_path=local_path,
                staging_path=str(staging_path),
                error=str(e),
            )
            return None

    def _sanitize_for_path(self, name: str) -> str:
        """Sanitize name for use in file path"""
        sanitized = name.lower()
        sanitized = sanitized.replace(" ", "_")
        sanitized = sanitized.replace("/", "_")
        sanitized = "".join(c if c.isalnum() or c in "._-" else "_" for c in sanitized)
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_")


def create_uploader(config, enabled: Optional[bool] = None) -> Optional[S3Uploader]:
    """
    Factory function to create S3 uploader from config.

    Args:
        config: RadioIngestionConfig instance
        enabled: Override config.s3_enabled if provided

    Returns:
        S3Uploader instance or None if disabled
    """
    s3_enabled = enabled if enabled is not None else config.s3_enabled

    if not s3_enabled or not config.s3_bucket:
        logger.info("S3 uploader disabled or bucket not configured")
        return None

    return S3Uploader(
        bucket=config.s3_bucket,
        region=config.aws_region,
        access_key_id=config.aws_access_key_id,
        secret_access_key=config.aws_secret_access_key,
        enabled=s3_enabled,
    )
