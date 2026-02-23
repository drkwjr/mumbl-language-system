"""Database connection and configuration"""

import os
from contextlib import contextmanager
from typing import Optional

import psycopg
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration from environment"""

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="mumbl_lang_system")
    user: str = Field(default="mumbl_user")
    password: str = Field(default="mumbl_dev_password")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables"""
        # Try DATABASE_URL first
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return cls.from_url(db_url)

        # Otherwise use individual env vars
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "mumbl_lang_system"),
            user=os.getenv("DB_USER", "mumbl_user"),
            password=os.getenv("DB_PASSWORD", "mumbl_dev_password"),
        )

    @classmethod
    def from_url(cls, url: str) -> "DatabaseConfig":
        """Parse postgresql:// connection string"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") if parsed.path else "mumbl_lang_system",
            user=parsed.username or "mumbl_user",
            password=parsed.password or "",
        )

    def to_connection_string(self) -> str:
        """Generate psycopg connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@contextmanager
def get_connection(config: Optional[DatabaseConfig] = None):
    """
    Context manager for database connections.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM text_segments LIMIT 1")
    """
    if config is None:
        config = DatabaseConfig.from_env()

    conn = psycopg.connect(config.to_connection_string())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def test_connection(config: Optional[DatabaseConfig] = None) -> bool:
    """Test database connection"""
    try:
        with get_connection(config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False
