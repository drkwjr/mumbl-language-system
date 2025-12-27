#!/usr/bin/env python3
"""Run a single radio ingestion capture cycle."""

import asyncio
import os
from pathlib import Path

from radio_ingestion.config import get_config
from radio_ingestion.service import RadioIngestionService

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def main() -> None:
    ensure_database_url()
    config = get_config()
    service = RadioIngestionService(config)

    async def _run():
        await service.capture_stations()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
