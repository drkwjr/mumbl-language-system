"""Configuration management for radio ingestion service"""

import os
from typing import Optional, List
from pydantic import BaseModel, Field


class RadioIngestionConfig(BaseModel):
    """Radio ingestion configuration from environment variables"""
    
    # Radio Browser API
    radio_browser_api: str = Field(
        default="https://de1.api.radio-browser.info/json",
        description="Radio Browser API endpoint"
    )
    
    # Storage paths
    capture_dir: str = Field(
        default="data/radio_shards",
        description="Local directory for captured audio shards"
    )
    
    # Database (use existing DATABASE_URL or individual vars)
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL"
    )
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="mumbl_lang_system", description="Database name")
    db_user: str = Field(default="mumbl_user", description="Database user")
    db_password: str = Field(default="mumbl_dev_password", description="Database password")
    
    # S3 storage (optional for MVP)
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket name")
    s3_enabled: bool = Field(default=False, description="Enable S3 uploads")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    # Capture settings
    capture_duration: int = Field(default=180, description="Capture duration in seconds")
    window_size: int = Field(default=30, description="Language window size in seconds")
    capture_countries: List[str] = Field(default_factory=lambda: ["GHA", "SOM"], description="Country codes to capture")
    listening_timezone_strategy: str = Field(
        default="station",
        description="station or local; controls daypart aggregation",
    )
    listening_timezone: Optional[str] = Field(
        default=None,
        description="Fallback timezone (IANA) when using local strategy",
    )
    
    # VAD and prefilter settings
    vad_aggressiveness: int = Field(default=2, ge=0, le=3, description="WebRTC VAD aggressiveness 0-3")
    music_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Music filter cutoff")
    
    # Queue and orchestration
    max_concurrent_captures: int = Field(default=5, description="Max concurrent stream captures")
    station_refresh_interval_hours: int = Field(default=24, description="Hours between station refresh")
    capture_interval_minutes: int = Field(default=60, description="Minutes between captures per station")
    capture_source_limit: Optional[int] = Field(
        default=None,
        description="Limit number of sources per capture cycle",
    )
    hard_failure_threshold: int = Field(
        default=3,
        description="Hard failures within window before marking station inactive",
    )
    hard_failure_window_hours: int = Field(
        default=24,
        description="Window (hours) to count hard failures",
    )
    failure_cooldown_minutes: int = Field(
        default=30,
        description="Minutes to cool down after a capture failure",
    )
    max_consecutive_failures: int = Field(
        default=3,
        description="Failures before marking a station down",
    )
    
    @classmethod
    def from_env(cls) -> "RadioIngestionConfig":
        """Load configuration from environment variables"""
        # Try DATABASE_URL first
        database_url = os.getenv("DATABASE_URL")
        
        # Parse database URL if provided
        db_host = "localhost"
        db_port = 5432
        db_name = "mumbl_lang_system"
        db_user = "mumbl_user"
        db_password = "mumbl_dev_password"
        
        if database_url:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            db_host = parsed.hostname or "localhost"
            db_port = parsed.port or 5432
            db_name = parsed.path.lstrip("/") if parsed.path else "mumbl_lang_system"
            db_user = parsed.username or "mumbl_user"
            db_password = parsed.password or ""
        
        return cls(
            radio_browser_api=os.getenv("RADIO_BROWSER_API", "https://de1.api.radio-browser.info/json"),
            capture_dir=os.getenv("CAPTURE_DIR", "data/radio_shards"),
            database_url=database_url,
            db_host=os.getenv("DB_HOST", db_host),
            db_port=int(os.getenv("DB_PORT", str(db_port))),
            db_name=os.getenv("DB_NAME", db_name),
            db_user=os.getenv("DB_USER", db_user),
            db_password=os.getenv("DB_PASSWORD", db_password),
            s3_bucket=os.getenv("S3_BUCKET"),
            s3_enabled=os.getenv("S3_ENABLED", "false").lower() == "true",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            capture_duration=int(os.getenv("CAPTURE_DURATION", "180")),
            window_size=int(os.getenv("WINDOW_SIZE", "30")),
            capture_countries=[
                code.strip().upper()
                for code in os.getenv("CAPTURE_COUNTRIES", "GHA,SOM").split(",")
                if code.strip()
            ],
            listening_timezone_strategy=os.getenv("LISTENING_TIMEZONE_STRATEGY", "station"),
            listening_timezone=os.getenv("LISTENING_TIMEZONE"),
            vad_aggressiveness=int(os.getenv("VAD_AGGRESSIVENESS", "2")),
            music_threshold=float(os.getenv("MUSIC_THRESHOLD", "0.6")),
            max_concurrent_captures=int(os.getenv("MAX_CONCURRENT_CAPTURES", "5")),
            station_refresh_interval_hours=int(os.getenv("STATION_REFRESH_INTERVAL_HOURS", "24")),
            capture_interval_minutes=int(os.getenv("CAPTURE_INTERVAL_MINUTES", "60")),
            capture_source_limit=(
                int(os.getenv("CAPTURE_SOURCE_LIMIT"))
                if os.getenv("CAPTURE_SOURCE_LIMIT")
                else None
            ),
            hard_failure_threshold=int(os.getenv("HARD_FAILURE_THRESHOLD", "3")),
            hard_failure_window_hours=int(os.getenv("HARD_FAILURE_WINDOW_HOURS", "24")),
            failure_cooldown_minutes=int(os.getenv("FAILURE_COOLDOWN_MINUTES", "30")),
            max_consecutive_failures=int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3")),
        )
    
    @property
    def database_url_final(self) -> str:
        """Get final database URL, preferring DATABASE_URL env var"""
        if self.database_url:
            return self.database_url
        
        # Fall back to individual components
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


def get_config() -> RadioIngestionConfig:
    """Get configuration instance"""
    return RadioIngestionConfig.from_env()
